"""Build the UNO Q model comparison table (Markdown) from evaluation results.

usage: python pc/uno_q_model_table.py EVAL_ALL_JSON [--extra NAME=RUN_DIR ...] [--out FILE]
EVAL_ALL_JSON is the output of pc/uno_q_evaluate_all.py.  --extra adds models
evaluated afterwards from their per-set reports (eval_<set>.json in RUN_DIR,
or eval_report.json for the evening set written by export_eval.sh).
Training descriptions are recorded here because config.json does not store
the augmentation flags.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

PC = Path(__file__).resolve().parent
sys.path.insert(0, str(PC))
from training.dataset import class_of  # noqa: E402

# name -> (label, training data, augmentation, ambient overlay, start)
# recipe = --aug-strong + --spike-fix + --feature-aug; CBn = cross-baseline over n sessions
META = {
    "original_XL": ("Original XL", "original v21-v25 (FRDM)", "recipe, CB5", "original passive", "scratch"),
    "uno_q_representative_160": ("UNO Q provisional", "original 160 WAVs", "feature-aug", "none", "scratch"),
    "uno_q_s1_xl": ("A", "UNO Q s1", "feature-aug", "none", "scratch"),
    "uno_q_s2_xl": ("B", "UNO Q s2", "feature-aug", "none", "scratch"),
    "uno_q_s1_plus_orig_xl": ("C", "s1 + original", "feature-aug", "none", "scratch"),
    "uno_q_s12_xl": ("D", "s1-2", "feature-aug", "none", "scratch"),
    "uno_q_s12_plus_orig_xl": ("E", "s1-2 + original", "feature-aug", "none", "scratch"),
    "uno_q_s12_origrecipe_xl": ("F", "s1-2", "recipe, CB2", "none", "scratch"),
    "uno_q_s12_origrecipe_ambient_xl": ("G", "s1-2", "recipe, CB2", "original passive", "scratch"),
    "uno_q_s12_plus_orig_origrecipe_xl": ("H", "s1-2 + original", "recipe, CB7", "none", "scratch"),
    "uno_q_s123_origrecipe_xl": ("J", "s1-3", "recipe, CB3", "none", "scratch"),
    "uno_q_s1234_origrecipe_xl": ("K", "s1-4", "recipe, CB4", "none", "scratch"),
    "uno_q_s12345_origrecipe_amb_xl": ("N", "s1-5", "recipe, CB5", "UNO Q room", "scratch"),
    "uno_q_s123456_origrecipe_amb_xl": ("M", "s1-6", "recipe, CB6", "UNO Q room", "scratch"),
    "uno_q_s1to8_origrecipe_amb_xl": ("P", "s1-8 (s7/8 at 4.8%FS, x2.72)", "recipe, CB8", "UNO Q room", "scratch"),
    "uno_q_s12345_7loud_origrecipe_amb_xl": ("Q", "s1-5 + s7 (4.8%FS)", "recipe, CB6", "UNO Q room", "scratch"),
    "uno_q_s5normal_origrecipe_xl": ("s5 only", "s5", "recipe, CB1", "UNO Q room", "scratch"),
    "uno_q_s7loud_origrecipe_xl": ("s7 loud only", "s7 (4.8%FS)", "recipe, CB1", "UNO Q room", "scratch"),
    "uno_q_K_ft_crowd_xl": ("K+ambient", "s1-4", "recipe, CB4", "UNO Q room + crowd", "K, 20 ep"),
    "uno_q_K_ft_warp3_xl": ("W", "s1-4", "recipe, CB4, warp +-3%", "UNO Q room + crowd", "K+ambient, 20 ep"),
    "uno_q_K_ft_warp5_xl": ("W5", "s1-4", "recipe, CB4, warp +-5%", "UNO Q room + crowd", "K+ambient, 20 ep"),
    "uno_q_M_ft_warp3_xl": ("MW", "s1-6", "recipe, CB6, warp +-3%", "UNO Q room + crowd", "M, 20 ep"),
    "uno_q_P_ft_warp3_xl": ("PW", "s1-8", "recipe, CB8, warp +-3%", "UNO Q room + crowd", "P, 20 ep"),
}
SETS = (("morning", "09:00 stable"), ("evening", "19:35 -2.15%"),
        ("survey", "20:44 -1.05%"), ("crowd", "21:28 crowd -0.80%"))
FILES = {"morning": "eval_gray_s32.json", "evening": "eval_report.json",
         "survey": "eval_survey_s32.json", "crowd": "eval_crowd_s32.json"}


def bits(state: int) -> np.ndarray:
    return np.array([state >> i & 1 for i in range(5)])


def from_rows(path: Path) -> dict:
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    t = np.array([r["true"] for r in rows])
    p = np.array([r["pred"] for r in rows])
    return {"acc32": float(np.mean(t == p)),
            "acc14": float(np.mean([class_of(bits(a)) == class_of(bits(b)) for a, b in zip(t, p)]))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_all", type=Path)
    parser.add_argument("--extra", nargs="*", default=[])
    parser.add_argument("--out", type=Path, default=PC / "runs" / "model_comparison_20260912.md")
    args = parser.parse_args()
    results = json.loads(args.eval_all.read_text(encoding="utf-8"))
    for item in args.extra:
        name, run_dir = item.split("=", 1)
        results[name] = {s: from_rows(Path(run_dir) / f) for s, f in FILES.items()
                         if (Path(run_dir) / f).is_file()}
    order = [k for k in META if k in results] + [k for k in results if k not in META]
    head = ("| model | training data | augmentation | ambient | start | "
            + " | ".join(f"{s} ({d})" for s, d in SETS) + " | mean 32 |")
    lines = [head, "|" + "---|" * (6 + len(SETS))]
    for name in order:
        label, data, aug, amb, start = META.get(name, (name, "?", "?", "?", "?"))
        cells, means = [], []
        for s, _ in SETS:
            r = results[name].get(s)
            if r:
                cells.append(f"{r['acc32'] * 100:.1f} / {r['acc14'] * 100:.1f}")
                means.append(r["acc32"])
            else:
                cells.append("-")
        mean = f"{np.mean(means) * 100:.1f}" if len(means) == len(SETS) else "-"
        lines.append(f"| {label} | {data} | {aug} | {amb} | {start} | " + " | ".join(cells) + f" | {mean} |")
    note = ("\nValues: 32-state / 14-class (observable) accuracy in %. recipe = --aug-strong "
            "--spike-fix --feature-aug; CBn = cross-baseline over n sessions; warp = --freq-warp "
            "(temperature). Evaluation sets are never used for training.\n")
    text = "# UNO Q model comparison (2026-09-12)\n\n" + "\n".join(lines) + note
    args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
