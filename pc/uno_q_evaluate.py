"""Offline inference over collected UNO Q evaluation captures.

usage: python pc/uno_q_evaluate.py DATA_DIR MODEL_DIR [--quantize int16|float] [--out report.json]
MODEL_DIR holds manifest.json + the ONNX named in it (same contract as the app).
The baseline is the mean log-PSD of the 'baseline' group (all closed).
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "uno_q" / "app" / "python"))
import ichiping_inference as ii  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "cal", REPO / "uno_q" / "audio" / "analyze-white-noise-calibration.py")
cal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cal)
BITS = ("a", "b", "c", "AB", "BC")


def label(state: int) -> str:
    """Dataset directory convention: s<a><b><c><AB><BC>, class bit0 = window a."""
    return "s" + "".join(str(state >> i & 1) for i in range(5))


def load_frames(data: Path, quantize: str) -> list[dict]:
    records = [json.loads(line) for line in (data / "records.jsonl").read_text().splitlines()]
    batches: dict[str, list] = {}
    for record in records:
        if record.get("frame_index") is not None:
            # Batch capture: one raw file holds `repeats` frames at a fixed pitch.
            if record["file"] not in batches:
                raw = (data / record["file"]).read_bytes()
                batches[record["file"]] = cal.align_prbs_frames(
                    raw, record["prbs_seed"], record["repeats"], record["gap"],
                    record["capture_format"], quantize)
            frame, info = batches[record["file"]][record["frame_index"]]
        else:
            raw = (data / record["file"]).read_bytes()
            frame, info = cal.align_prbs_frame(raw, record["prbs_seed"], record["capture_format"], quantize)
        record["frame"] = frame
        record["rms"] = float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)))
        record["clipped"] = info["clipped_samples"]
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("--quantize", default="int16", choices=("int16", "float"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--gain", type=float, default=None,
                        help="capture gain instead of x16 (e.g. ~2.7 for 4.8%%FS PRBS sessions)")
    args = parser.parse_args()
    if args.gain is not None:
        ii.ORIGINAL_CAPTURE_GAIN = args.gain  # to_original_scale reads it at call time
    manifest = json.loads((args.model / "manifest.json").read_text(encoding="utf-8"))
    predictor = ii.OnnxPredictor(args.model / manifest["model_file"], manifest["model_sha256"], manifest)
    records = load_frames(args.data, args.quantize)
    base = [r["frame"] for r in records if r["group"] == "baseline"]
    baseline = ii.calibrate_baseline(base)
    tests = [r for r in records if r["group"] != "baseline"]
    rows = []
    for r in tests:
        p = predictor.predict_audio(r["frame"], baseline)
        rows.append({"group": r["group"], "true": r["state"], "pred": int(p.state_mask),
                     "confidence": float(p.confidence), "rms": r["rms"], "clipped": r["clipped"]})
    true = np.array([x["true"] for x in rows])
    pred = np.array([x["pred"] for x in rows])
    bit_acc = {name: float(np.mean((true >> i & 1) == (pred >> i & 1))) for i, name in enumerate(BITS)}
    by_group = collections.defaultdict(list)
    for x in rows:
        by_group[x["group"]].append(x["true"] == x["pred"])
    errors = collections.Counter((label(x["true"]), label(x["pred"])) for x in rows if x["true"] != x["pred"])
    per_state = collections.defaultdict(list)
    for x in rows:
        per_state[label(x["true"])].append(x["true"] == x["pred"])
    report = {
        "model": manifest["model_file"], "model_sha256": manifest["model_sha256"],
        "data": str(args.data), "quantize": args.quantize,
        "n_test": len(rows), "n_baseline": len(base),
        "accuracy_32cls": float(np.mean(true == pred)),
        "per_bit_accuracy": bit_acc,
        "per_group_accuracy": {g: float(np.mean(v)) for g, v in sorted(by_group.items())},
        "mean_confidence_correct": float(np.mean([x["confidence"] for x in rows if x["true"] == x["pred"]] or [np.nan])),
        "mean_confidence_wrong": float(np.mean([x["confidence"] for x in rows if x["true"] != x["pred"]] or [np.nan])),
        "frame_rms_range": [float(min(x["rms"] for x in rows)), float(max(x["rms"] for x in rows))],
        "clipped_frames": int(sum(1 for x in rows if x["clipped"])),
        "top_errors": errors.most_common(12),
        "states_never_correct": sorted(k for k, v in per_state.items() if not any(v)),
        "rows": rows,
    }
    if args.out:
        args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    summary = {k: v for k, v in report.items() if k != "rows"}
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
