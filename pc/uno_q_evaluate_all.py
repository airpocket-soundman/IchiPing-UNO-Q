"""Evaluate every packaged model on every UNO Q evaluation set (one table).

usage: python pc/uno_q_evaluate_all.py [--out pc/runs/eval_all_YYYYMMDD.json]
Models: pc/runs/*/uno_q_model (manifest.json + ONNX) plus the original and the
first UNO Q packaged model.  Accuracy is reported for 32 states and for the
14 observable classes (training.dataset.class_of).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

PC = Path(__file__).resolve().parent
REPO = PC.parent
sys.path.insert(0, str(PC))
from training.dataset import class_of  # noqa: E402

EVAL_SETS = {
    "morning": PC / "captures" / "uno_q_eval_20260912_gray_s32",      # ~09:00, stable
    "evening": PC / "captures" / "uno_q_eval_20260912_evening_s32",   # 19:35, -2.15 % warp
    "survey": PC / "captures" / "uno_q_eval_20260912_survey_s32",     # 20:44, -1.05 % warp
    "crowd": PC / "captures" / "uno_q_eval_20260912_crowd_s32",       # 21:28, -0.80 %, crowd noise
}
EXTRA_MODELS = {
    "original_XL": PC / "runs" / "original_neutron_v21_25_XL_uno_q",
    "uno_q_representative_160": REPO / "uno_q" / "app" / "models",
}
BITS = ("a", "b", "c", "AB", "BC")


def bits(state: int) -> np.ndarray:
    return np.array([state >> i & 1 for i in range(5)])


def models() -> dict[str, Path]:
    found = dict(EXTRA_MODELS)
    for manifest in sorted((PC / "runs").glob("*/uno_q_model/manifest.json")):
        found[manifest.parent.parent.name] = manifest.parent
    return {k: v for k, v in found.items() if (v / "manifest.json").is_file()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=PC / "runs" / "eval_all.json")
    args = parser.parse_args()
    results = {}
    for name, model in models().items():
        results[name] = {}
        for set_name, data in EVAL_SETS.items():
            if not (data / "records.jsonl").is_file():
                continue
            report = PC / "runs" / f"_eval_{name}_{set_name}.json"
            subprocess.run([sys.executable, str(PC / "uno_q_evaluate.py"), str(data), str(model),
                            "--out", str(report)], check=True, capture_output=True)
            rows = json.loads(report.read_text(encoding="utf-8"))["rows"]
            report.unlink()
            true = np.array([r["true"] for r in rows])
            pred = np.array([r["pred"] for r in rows])
            acc14 = float(np.mean([class_of(bits(t)) == class_of(bits(p)) for t, p in zip(true, pred)]))
            results[name][set_name] = {
                "n": len(rows),
                "acc32": float(np.mean(true == pred)),
                "acc14": acc14,
                "bits": {b: float(np.mean((true >> i & 1) == (pred >> i & 1))) for i, b in enumerate(BITS)},
            }
            print(f"{name:40s} {set_name:8s} n={len(rows):4d} acc32={results[name][set_name]['acc32']:.3f} "
                  f"acc14={acc14:.3f} " + " ".join(f"{b}={v:.2f}" for b, v in results[name][set_name]["bits"].items()),
                  flush=True)
    args.out.write_text(json.dumps(results, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
