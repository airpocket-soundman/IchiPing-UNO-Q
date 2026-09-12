#!/usr/bin/env python3
"""Offline capture-to-baseline and capture-to-prediction commands for UNO Q."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ichiping_inference import (
    OnnxPredictor,
    calibrate_baseline,
    capture_health,
    capture_to_model_audio,
    load_manifest,
)


HERE = Path(__file__).resolve().parent
DEFAULT_MODEL_DIR = HERE.parent / "models"


def build_predictor(model_dir: Path) -> tuple[OnnxPredictor, dict]:
    manifest = load_manifest(model_dir / "manifest.json")
    predictor = OnnxPredictor(
        model_dir / manifest["model_file"], manifest["model_sha256"], manifest
    )
    return predictor, manifest


def create_baseline(captures: list[Path], output: Path) -> dict:
    if len(captures) < 3:
        raise ValueError("at least three independent all-closed captures are required")
    raw_captures = [path.read_bytes() for path in captures]
    health = [capture_health(raw) for raw in raw_captures]
    frames = [capture_to_model_audio(raw) for raw in raw_captures]
    baseline = calibrate_baseline(frames)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        np.save(stream, baseline, allow_pickle=False)
    return {
        "mode": "all-closed-baseline",
        "captures": [str(path) for path in captures],
        "count": len(captures),
        "output": str(output),
        "shape": list(baseline.shape),
        "capture_health": health,
    }


def predict_capture(
    capture: Path, baseline_path: Path, model_dir: Path
) -> dict:
    predictor, manifest = build_predictor(model_dir)
    baseline = np.load(baseline_path, allow_pickle=False)
    audio = capture_to_model_audio(capture.read_bytes())
    prediction = predictor.predict_audio(audio, baseline)
    return {
        "mode": "model",
        "capture": str(capture),
        "model": manifest["model_file"],
        "model_sha256": manifest["model_sha256"],
        "state_mask": prediction.state_mask,
        "state_bits": f"{prediction.state_mask:05b}",
        "confidence": prediction.confidence,
        "confidence_percent": prediction.confidence_percent,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    baseline = subparsers.add_parser("calibrate-baseline")
    baseline.add_argument("captures", nargs="+", type=Path)
    baseline.add_argument("--output", required=True, type=Path)

    predict = subparsers.add_parser("predict")
    predict.add_argument("capture", type=Path)
    predict.add_argument("--baseline", required=True, type=Path)
    predict.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)

    args = parser.parse_args()
    if args.command == "calibrate-baseline":
        result = create_baseline(args.captures, args.output)
    else:
        result = predict_capture(args.capture, args.baseline, args.model_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
