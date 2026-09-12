"""Validated, atomic live-baseline persistence for the UNO Q runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
import time

import numpy as np


BASELINE_FORMAT_VERSION = 1
MIN_BASELINE_CAPTURES = 3


def save_baseline(
    directory: Path,
    baseline: np.ndarray,
    *,
    model_sha256: str,
    capture_ids: list[str],
    playback_rms_fs: float,
) -> None:
    if len(capture_ids) < MIN_BASELINE_CAPTURES:
        raise ValueError(f"at least {MIN_BASELINE_CAPTURES} captures are required")
    values = np.asarray(baseline, dtype=np.float32)
    if values.shape != (1024,) or not np.isfinite(values).all():
        raise ValueError("invalid baseline array")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    array_tmp = directory / ".baseline.npy.tmp"
    with array_tmp.open("wb") as stream:
        np.save(stream, values, allow_pickle=False)
        stream.flush()
        os.fsync(stream.fileno())
    metadata = {
        "format_version": BASELINE_FORMAT_VERSION,
        "model_sha256": model_sha256,
        "capture_ids": capture_ids,
        "capture_count": len(capture_ids),
        "playback_rms_fs": playback_rms_fs,
        "created_unix_seconds": time.time(),
    }
    metadata_tmp = directory / ".baseline.json.tmp"
    metadata_tmp.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(array_tmp, directory / "baseline.npy")
    os.replace(metadata_tmp, directory / "baseline.json")


def load_baseline(directory: Path, *, model_sha256: str) -> tuple[np.ndarray, dict]:
    directory = Path(directory)
    metadata = json.loads((directory / "baseline.json").read_text(encoding="utf-8"))
    if metadata.get("format_version") != BASELINE_FORMAT_VERSION:
        raise ValueError("unsupported baseline format")
    if metadata.get("model_sha256") != model_sha256:
        raise ValueError("baseline belongs to a different model")
    if int(metadata.get("capture_count", 0)) < MIN_BASELINE_CAPTURES:
        raise ValueError("baseline has too few independent captures")
    baseline = np.load(directory / "baseline.npy", allow_pickle=False)
    if baseline.shape != (1024,) or baseline.dtype != np.float32:
        raise ValueError("invalid baseline array shape or dtype")
    if not np.isfinite(baseline).all():
        raise ValueError("baseline contains non-finite values")
    return baseline, metadata

