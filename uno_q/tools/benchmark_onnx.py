"""Measure an ONNX candidate on the UNO Q Linux CPU.

The script intentionally keeps deployment benchmarking independent from the
training environment. It reports machine-readable JSON for model comparisons.
"""
from __future__ import annotations

import argparse
import json
import platform
import resource
import statistics
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def parse_shape(value: str) -> tuple[int, ...]:
    shape = tuple(int(part) for part in value.split(","))
    if not shape or any(size <= 0 for size in shape):
        raise argparse.ArgumentTypeError("shape must contain positive integers")
    return shape


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--shape", type=parse_shape, default=(1, 1, 1024))
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--max-p95-ms", type=float, default=1000.0)
    parser.add_argument("--max-rss-mib", type=float, default=1536.0)
    args = parser.parse_args()

    if args.warmup < 0 or args.runs < 1 or args.threads < 1:
        parser.error("warmup must be >= 0; runs and threads must be >= 1")
    if not args.model.is_file():
        parser.error(f"model not found: {args.model}")

    options = ort.SessionOptions()
    options.intra_op_num_threads = args.threads
    options.inter_op_num_threads = 1
    started = time.perf_counter()
    session = ort.InferenceSession(
        str(args.model), options, providers=["CPUExecutionProvider"]
    )
    load_ms = (time.perf_counter() - started) * 1000.0
    input_meta = session.get_inputs()[0]
    sample = np.random.default_rng(0).standard_normal(args.shape).astype(np.float32)

    for _ in range(args.warmup):
        session.run(None, {input_meta.name: sample})

    timings_ms: list[float] = []
    for _ in range(args.runs):
        started = time.perf_counter_ns()
        session.run(None, {input_meta.name: sample})
        timings_ms.append((time.perf_counter_ns() - started) / 1_000_000.0)

    # Linux reports ru_maxrss in KiB. This utility is intended for UNO Q Linux.
    peak_rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    result = {
        "model": str(args.model),
        "model_mib": args.model.stat().st_size / (1024.0 * 1024.0),
        "input_name": input_meta.name,
        "input_shape": args.shape,
        "runs": args.runs,
        "threads": args.threads,
        "load_ms": load_ms,
        "mean_ms": statistics.fmean(timings_ms),
        "p50_ms": percentile(timings_ms, 0.50),
        "p95_ms": percentile(timings_ms, 0.95),
        "p99_ms": percentile(timings_ms, 0.99),
        "peak_rss_mib": peak_rss_mib,
        "machine": platform.machine(),
        "onnxruntime": ort.__version__,
    }
    result["within_budget"] = (
        result["p95_ms"] <= args.max_p95_ms
        and result["peak_rss_mib"] <= args.max_rss_mib
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["within_budget"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
