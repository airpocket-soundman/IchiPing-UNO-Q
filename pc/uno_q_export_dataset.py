"""Export UNO Q PRBS captures to the original training dataset layout.

usage: python pc/uno_q_export_dataset.py DATA_DIR OUT_CAPTURES_DIR [--quantize int16|float]

DATA_DIR is a pc/uno_q_collect.py output (records.jsonl + raw S16/S32 files).
OUT_CAPTURES_DIR receives s<a><b><c><AB><BC>/frame_NNNNNN.wav (16 kHz mono
int16), i.e. the layout pc/training/dataset.py already reads.  With the
default int16 mode each sample equals the original collector's
clip(I2S word >> 12), so the result can be mixed with the original WAVs.
'float' keeps sub-LSB bits and is written as 32-bit float WAV for
UNO Q-only experiments.  The all-closed 'baseline' group is written to
s00000 as well (it is the per-run baseline source).
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import sys
import wave
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "uno_q" / "app" / "python"))
spec = importlib.util.spec_from_file_location(
    "cal", REPO / "uno_q" / "audio" / "analyze-white-noise-calibration.py")
cal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cal)


def label(state: int) -> str:
    return "s" + "".join(str(state >> i & 1) for i in range(5))


def write_wav(path: Path, frame: np.ndarray, quantize: str) -> None:
    if quantize == "int16":
        pcm = np.round(frame.astype(np.float64) * 32768.0).astype("<i2")
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16_000)
            handle.writeframes(pcm.tobytes())
    else:
        import soundfile  # float WAV needs soundfile; int16 path stays stdlib-only
        soundfile.write(str(path), frame.astype(np.float32), 16_000, subtype="FLOAT")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--quantize", choices=("int16", "float"), default="int16")
    parser.add_argument("--gain", type=float, default=None,
                        help="capture gain instead of the collector's x16 (e.g. ~2.7 for 4.8%%FS "
                             "PRBS sessions so the level matches the original dataset without clipping)")
    args = parser.parse_args()
    if args.gain is not None:
        import ichiping_inference as ii
        ii.ORIGINAL_CAPTURE_GAIN = args.gain  # to_original_scale reads it at call time
    records = [json.loads(line) for line in (args.data / "records.jsonl").read_text().splitlines()]
    by_file = collections.defaultdict(list)
    for record in records:
        by_file[record["file"]].append(record)
    counters: dict[str, int] = collections.Counter()
    rows = collections.defaultdict(list)
    for name, group in by_file.items():
        raw = (args.data / name).read_bytes()
        first = group[0]
        if first.get("excitation") == "silence":
            # Ambient (speaker silent) capture: fixed frame grid, no PRBS to align.
            frames = cal.split_fixed_frames(raw, first.get("repeats") or 1, first.get("gap") or 0.3,
                                            first["capture_format"], args.quantize)
        elif first.get("frame_index") is not None:
            frames = cal.align_prbs_frames(raw, first["prbs_seed"], first["repeats"], first["gap"],
                                           first["capture_format"], args.quantize)
        else:
            frames = [cal.align_prbs_frame(raw, first["prbs_seed"], first["capture_format"], args.quantize)]
        for record in group:
            index = record.get("frame_index") or 0
            frame, info = frames[index]
            state_label = label(record["state"])
            directory = args.out / state_label
            directory.mkdir(parents=True, exist_ok=True)
            wav_name = f"frame_{counters[state_label]:06d}.wav"
            counters[state_label] += 1
            write_wav(directory / wav_name, frame, args.quantize)
            rows[state_label].append({
                "wav": wav_name, "group": record["group"], "source_file": name,
                "frame_index": index, "time": record["time"],
                "clipped_samples": info["clipped_samples"],
                "rms": float(np.sqrt(np.mean(frame.astype(np.float64) ** 2))),
            })
    for state_label, entries in rows.items():
        meta = {"label": state_label, "source": str(args.data), "quantize": args.quantize,
                "capture": "UNO Q MI2S0 PRBS16k, x16 original scale (word >> 12)",
                "frames": entries}
        (args.out / state_label / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    total = sum(counters.values())
    print(json.dumps({"out": str(args.out), "states": len(counters), "frames": total,
                      "per_state": dict(sorted(counters.items()))}))


if __name__ == "__main__":
    main()
