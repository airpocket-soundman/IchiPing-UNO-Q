#!/usr/bin/env python3
"""Analyze one UNO Q white-noise level trial without replaying any audio."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
# Repository layout is uno_q/audio + uno_q/app/python.  Deployed layout keeps
# this tool at app/audio + app/python.
APP_PYTHON = next(
    path for path in (HERE.parent / "app" / "python", HERE.parent / "python")
    if path.is_dir()
)
sys.path.insert(0, str(APP_PYTHON))

from ichiping_inference import capture_to_model_audio  # noqa: E402


TARGET_RMS_LOW = 0.18
TARGET_RMS_HIGH = 0.19
MAX_RECOMMENDED_PLAYBACK_RMS = 0.10


def analyze(raw: bytes, playback_rms: float) -> dict:
    if not 0 < playback_rms <= MAX_RECOMMENDED_PLAYBACK_RMS:
        raise ValueError("playback RMS must be > 0 and <= 0.10 FS")
    samples = capture_to_model_audio(raw, crop_seconds=2.0)
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
    peak = float(np.max(np.abs(samples)))
    if rms == 0:
        recommendation = None
        status = "digital-silence"
    elif peak >= 0.90:
        recommendation = max(0.0001, playback_rms * 0.5)
        status = "clipping-risk"
    elif TARGET_RMS_LOW <= rms <= TARGET_RMS_HIGH:
        recommendation = playback_rms
        status = "target"
    else:
        target = (TARGET_RMS_LOW + TARGET_RMS_HIGH) / 2
        proportional = playback_rms * target / rms
        # Never jump by more than 2x between user-audible trials.
        recommendation = min(
            MAX_RECOMMENDED_PLAYBACK_RMS,
            max(playback_rms / 2, min(playback_rms * 2, proportional)),
        )
        status = "below-target" if rms < TARGET_RMS_LOW else "above-target"
    return {
        "status": status,
        "playback_rms_fs": playback_rms,
        "capture_center_crop_seconds": 2.0,
        "capture_rms_fs": rms,
        "capture_peak_fs": peak,
        "target_capture_rms_fs": [TARGET_RMS_LOW, TARGET_RMS_HIGH],
        "target_capture_peak_fs_max": 0.90,
        "recommended_next_playback_rms_fs": recommendation,
        "safe_step_policy": "analyze each run; maximum 2x increase; never exceed 0.10 FS RMS",
    }


PRBS_FRAME_SAMPLES = 32_000          # original collector: 2.0 s at 16 kHz
PRBS_FLOOR_GUARD_SAMPLES = 800       # exclude 50 ms before the onset
PRBS_MAX_RECOMMENDED_AMPLITUDE = 0.45  # band-limited PRBS peaks ~2.1x; stay < 1 FS


def _load_smoke():
    import importlib.util
    spec = importlib.util.spec_from_file_location("smoke", HERE / "audio-smoke-test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def align_prbs_frame(raw: bytes, seed: int, capture_format: str = "S16_LE",
                     quantize: str = "int16") -> tuple[np.ndarray, dict]:
    """Return the 2.0 s 16 kHz frame starting at the acoustic PRBS onset.

    The original collector captured exactly the 2 s playback window.  Here the
    capture is longer and not sample-synchronous, so the onset is located by
    cross-correlation with the deterministic 16 kHz PRBS source.  The frame is
    returned on the original collector's int16 scale (see to_original_scale);
    levels in the report are on that scale too.
    """
    from ichiping_inference import (
        ORIGINAL_CAPTURE_GAIN, decimate_48k_to_16k, left_capture_to_float,
        to_original_scale,
    )

    word = decimate_48k_to_16k(left_capture_to_float(raw, capture_format))
    mono = word.astype(np.float64) * ORIGINAL_CAPTURE_GAIN
    mono -= mono.mean()
    reference = np.asarray(_load_smoke().prbs_source(seed), dtype=np.float64)
    if mono.size < reference.size + PRBS_FLOOR_GUARD_SAMPLES:
        raise ValueError("capture is too short for the 2 s PRBS frame")
    size = 1 << int(np.ceil(np.log2(mono.size + reference.size)))
    corr = np.fft.irfft(np.fft.rfft(mono, size) * np.conj(np.fft.rfft(reference, size)), size)
    lags = corr[: mono.size - reference.size + 1]
    lag = int(np.argmax(np.abs(lags)))
    frame = mono[lag: lag + reference.size]
    model_frame = to_original_scale(word[lag: lag + reference.size], quantize)
    # The lead window also contains the amplifier SD_MODE turn-on transient, so
    # the ambient floor is taken after the PRBS and its room decay (100 ms).
    lead_end = lag - PRBS_FLOOR_GUARD_SAMPLES
    lead = mono[:lead_end] if lead_end >= 1600 else np.empty(0)
    tail_start = lag + reference.size + 1600
    tail = mono[tail_start:] if mono.size - tail_start >= 1600 else np.empty(0)
    rms_of = lambda values: float(np.sqrt(np.mean(values * values))) if values.size else None
    energy = float(np.sqrt(np.sum(frame * frame) * reference.size))
    info = {
        "onset_sample_16k": lag,
        "onset_seconds": lag / 16_000,
        "alignment_correlation": float(abs(lags[lag]) / energy) if energy else 0.0,
        "lead_rms_fs": rms_of(lead),
        "floor_rms_fs": rms_of(tail),
        "capture_format": capture_format,
        "quantize": quantize,
        "capture_gain": ORIGINAL_CAPTURE_GAIN,
        "clipped_samples": int(np.sum(np.abs(model_frame) >= 32767 / 32768)),
    }
    return model_frame, info


def align_prbs_frames(raw: bytes, seed: int, repeats: int, gap: float,
                      capture_format: str = "S16_LE",
                      quantize: str = "int16") -> list[tuple[np.ndarray, dict]]:
    """Split one batch capture into ``repeats`` aligned 2.0 s frames.

    Playback and capture share the MI2S bit clock, so frame k starts exactly
    k * (2.0 s + gap) after the first onset; each onset is still refined by
    +-1 ms of correlation so a skipped period would be detected, not hidden.
    """
    from ichiping_inference import (
        ORIGINAL_CAPTURE_GAIN, decimate_48k_to_16k, left_capture_to_float,
        to_original_scale,
    )

    word = decimate_48k_to_16k(left_capture_to_float(raw, capture_format))
    mono = word.astype(np.float64) * ORIGINAL_CAPTURE_GAIN
    mono -= mono.mean()
    reference = np.asarray(_load_smoke().prbs_source(seed), dtype=np.float64)
    n = reference.size
    pitch = round((2.0 + gap) * 16_000)
    search = mono[: min(mono.size, n + 2 * 16_000)]
    size = 1 << int(np.ceil(np.log2(search.size + n)))
    corr = np.fft.irfft(np.fft.rfft(search, size) * np.conj(np.fft.rfft(reference, size)), size)
    first = int(np.argmax(np.abs(corr[: search.size - n + 1])))
    frames = []
    for index in range(repeats):
        expected = first + index * pitch
        candidates = [s for s in range(expected - 16, expected + 17) if 0 <= s and s + n <= mono.size]
        if not candidates:
            raise ValueError(f"capture ends before PRBS frame {index}")
        scores = [abs(float(np.dot(mono[s:s + n], reference))) for s in candidates]
        start = candidates[int(np.argmax(scores))]
        frame = to_original_scale(word[start:start + n], quantize)
        segment = mono[start:start + n]
        energy = float(np.sqrt(np.sum(segment * segment) * n))
        frames.append((frame, {
            "frame_index": index,
            "onset_sample_16k": start,
            "pitch_error_samples": start - expected,
            "alignment_correlation": max(scores) / energy if energy else 0.0,
            "clipped_samples": int(np.sum(np.abs(frame) >= 32767 / 32768)),
        }))
    return frames


# Measured PRBS onset inside the capture (0.376-0.385 s over every UNO Q run):
# capture starts 0.1 s after playback RUNNING, the PCM has 0.5 s lead silence.
SILENCE_ONSET_SECONDS = 0.38


def split_fixed_frames(raw: bytes, repeats: int, gap: float,
                       capture_format: str = "S16_LE", quantize: str = "int16",
                       onset_seconds: float = SILENCE_ONSET_SECONDS) -> list[tuple[np.ndarray, dict]]:
    """Frames of a silent (ambient) capture at the prbs16k timing.

    There is no excitation to correlate with, so the frame grid uses the
    measured onset; alignment does not matter for ambient noise overlays.
    """
    from ichiping_inference import decimate_48k_to_16k, left_capture_to_float, to_original_scale

    word = decimate_48k_to_16k(left_capture_to_float(raw, capture_format))
    first = round(onset_seconds * 16_000)
    pitch = round((2.0 + gap) * 16_000)
    frames = []
    for index in range(repeats):
        start = first + index * pitch
        if start + PRBS_FRAME_SAMPLES > word.size:
            raise ValueError(f"capture ends before silent frame {index}")
        frame = to_original_scale(word[start:start + PRBS_FRAME_SAMPLES], quantize)
        frames.append((frame, {"frame_index": index, "onset_sample_16k": start,
                               "clipped_samples": int(np.sum(np.abs(frame) >= 32767 / 32768))}))
    return frames


def analyze_prbs(raw: bytes, amplitude: float, seed: int,
                 capture_format: str = "S16_LE",
                 quantize: str = "int16") -> tuple[dict, np.ndarray]:
    if not 0 < amplitude < 1:
        raise ValueError("PRBS amplitude must be > 0 and < 1 FS")
    frame, info = align_prbs_frame(raw, seed, capture_format, quantize)
    centred = frame.astype(np.float64) - float(np.mean(frame))
    rms = float(np.sqrt(np.mean(centred ** 2)))
    peak = float(np.max(np.abs(frame)))
    target = (TARGET_RMS_LOW + TARGET_RMS_HIGH) / 2
    if rms == 0:
        status, recommendation = "digital-silence", None
    elif peak >= 0.90:
        status, recommendation = "clipping-risk", amplitude * 0.5
    elif TARGET_RMS_LOW <= rms <= TARGET_RMS_HIGH:
        status, recommendation = "target", amplitude
    else:
        status = "below-target" if rms < TARGET_RMS_LOW else "above-target"
        proportional = amplitude * target / rms
        # Never jump by more than 2x between audible trials.
        recommendation = min(PRBS_MAX_RECOMMENDED_AMPLITUDE,
                             max(amplitude / 2, min(amplitude * 2, proportional)))
    floor = info["floor_rms_fs"]
    report = {
        "excitation": "prbs16k",
        "status": status,
        "prbs_amplitude_fs": amplitude,
        "prbs_seed": seed,
        "frame_seconds": PRBS_FRAME_SAMPLES / 16_000,
        "capture_rms_fs": rms,
        "capture_peak_fs": peak,
        "snr_db": float(20 * np.log10(rms / floor)) if floor and rms else None,
        "target_capture_rms_fs": [TARGET_RMS_LOW, TARGET_RMS_HIGH],
        "target_capture_peak_fs_max": 0.90,
        "recommended_next_prbs_amplitude_fs": recommendation,
        "safe_step_policy": "analyze each run; maximum 2x increase",
        **info,
    }
    return report, frame


def write_frame_wav(path: Path, frame: np.ndarray) -> None:
    import wave
    pcm = np.clip(np.round(frame * 32768.0), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16_000)
        handle.writeframes(pcm.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--excitation", choices=("white", "prbs16k"), default="white")
    parser.add_argument("--playback-rms", type=float, help="white excitation level")
    parser.add_argument("--prbs-amplitude", type=float, help="prbs16k ± level")
    parser.add_argument("--seed", type=int, default=20260912)
    parser.add_argument("--capture-format", choices=("S16_LE", "S32_LE"), default="S16_LE")
    parser.add_argument("--quantize", choices=("int16", "float"), default="int16",
                        help="int16: original dataset compatible; float: keep all bits")
    parser.add_argument("--frame-wav", type=Path, help="write the aligned 16 kHz frame")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw = args.capture.read_bytes()
    if args.excitation == "prbs16k":
        if args.prbs_amplitude is None:
            parser.error("--prbs-amplitude is required for prbs16k")
        report, frame = analyze_prbs(raw, args.prbs_amplitude, args.seed,
                                     args.capture_format, args.quantize)
        if args.frame_wav:
            write_frame_wav(args.frame_wav, frame)
    else:
        if args.playback_rms is None:
            parser.error("--playback-rms is required for white")
        report = analyze(raw, args.playback_rms)
    report["capture_file"] = str(args.capture)
    report["capture_sha256"] = hashlib.sha256(raw).hexdigest()
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
