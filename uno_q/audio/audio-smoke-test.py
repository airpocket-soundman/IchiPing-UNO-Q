#!/usr/bin/env python3
"""Low-level, deliberately quiet MI2S0 smoke tests for IchiPing UNO Q."""

from __future__ import annotations

import argparse
import math
import pathlib
import struct
import subprocess
import tempfile


RATE = 48_000
CHANNELS = 2
SAMPLE_BYTES = 2
FORMAT = "S16_LE"
FULL_SCALE = 2**15 - 1
MAX_PLAYBACK_SECONDS = 0.5


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def tone_data(duration: float, amplitude: float, pcm_format: str = "S16_LE",
              lead_silence: float = 0, tail_silence: float = 0,
              fade: float = 0) -> bytes:
    if not 0 < duration <= MAX_PLAYBACK_SECONDS:
        raise ValueError("speaker duration must be > 0 and <= 0.5 seconds")
    if not 0 <= amplitude <= 0.001:
        raise ValueError("speaker amplitude must be >= 0 and <= 0.001")
    if pcm_format not in ("S16_LE", "S24_LE", "S32_LE"):
        raise ValueError("unsupported diagnostic format")
    if (min(lead_silence, tail_silence, fade) < 0 or
            lead_silence + tail_silence + 2 * fade >= duration):
        raise ValueError("invalid silence/fade timing")
    frames = bytearray()
    peak = round((2**23 - 1 if pcm_format != "S16_LE" else FULL_SCALE) * amplitude)
    for index in range(round(RATE * duration)):
        t = index / RATE - lead_silence
        tone_duration = duration - lead_silence - tail_silence
        envelope = 0 if t < 0 or t >= tone_duration else 1
        if envelope and fade:
            envelope = min(1, t / fade, (tone_duration - t) / fade)
        sample = round(peak * envelope * math.sin(2 * math.pi * 440 * t))
        if pcm_format == "S32_LE":
            sample <<= 8  # Native DSP PCM v2: 24 significant MSBs, Q31 container.
        # ALSA S24_LE is signed low 24 bits in a FOUR-byte container, not packed.
        packed = struct.pack("<h" if pcm_format == "S16_LE" else "<i", sample)
        frames.extend(packed + packed)
    return bytes(frames)


def speaker(device: str, duration: float, amplitude: float) -> None:
    frames = tone_data(duration, amplitude)
    with tempfile.NamedTemporaryFile(suffix=".raw") as audio_file:
        audio_file.write(frames)
        audio_file.flush()
        run(
            "aplay", "-D", device, "-t", "raw", "-f", FORMAT,
            "-c", str(CHANNELS), "-r", str(RATE),
            "--period-size=480", "--buffer-size=1920", audio_file.name,
        )
    print(f"PCM transfer completed (acoustic quality unverified): {duration:.2f} s, 440 Hz, {amplitude:.3%} FS")


def microphone(device: str, duration: float, output: pathlib.Path) -> None:
    if not 0 < duration <= 4.0:
        raise ValueError("microphone duration must be > 0 and <= 4.0 seconds")
    run(
        "arecord",
        "-D",
        device,
        "-c",
        "1",
        "-r",
        str(RATE),
        "-f",
        FORMAT,
        "--period-size=3840",
        "--buffer-size=30720",
        "-d",
        str(math.ceil(duration)),
        "-t",
        "raw",
        str(output),
    )
    data = output.read_bytes()
    if len(data) % SAMPLE_BYTES:
        raise RuntimeError(f"capture byte count is not S16_LE aligned: {len(data)}")
    samples = []
    for offset in range(0, len(data), SAMPLE_BYTES):
        sample = int.from_bytes(
            data[offset : offset + SAMPLE_BYTES], "little", signed=True
        )
        samples.append(sample)
    if not samples:
        raise RuntimeError("capture returned no samples")
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    peak = max(abs(sample) for sample in samples)
    print(
        f"capture transfer completed (signal unverified): mono frames={len(samples)} "
        f"rms={rms / FULL_SCALE:.6%} FS peak={peak / FULL_SCALE:.6%} FS"
    )


def prepare_replay(input_path: pathlib.Path, output: pathlib.Path, amplitude: float) -> None:
    if not 0 < amplitude <= 0.001:
        raise ValueError("replay amplitude must be > 0 and <= 0.001")
    data = input_path.read_bytes()
    frame_bytes = SAMPLE_BYTES  # Capture frontend is mono; output duplicates to stereo.
    if not data or len(data) % frame_bytes:
        raise RuntimeError(f"capture byte count is not mono S16_LE aligned: {len(data)}")

    left = []
    for offset in range(0, len(data), frame_bytes):
        sample = int.from_bytes(
            data[offset : offset + SAMPLE_BYTES], "little", signed=True
        )
        left.append(sample)

    source_peak = max(abs(sample) for sample in left)
    if source_peak == 0:
        raise RuntimeError("capture contains only digital silence")
    source_rms = math.sqrt(sum(sample * sample for sample in left) / len(left))
    target_peak = round(FULL_SCALE * amplitude)
    replay = bytearray()
    for sample in left[:round(RATE * MAX_PLAYBACK_SECONDS)]:
        scaled = round(sample * target_peak / source_peak)
        packed = struct.pack("<h", scaled)
        replay.extend(packed + packed)
    output.write_bytes(replay)
    print(
        f"capture statistics (quality unverified): frames={len(left)} "
        f"rms={source_rms / FULL_SCALE:.6%} FS "
        f"peak={source_peak / FULL_SCALE:.6%} FS; "
        f"replay limited to {amplitude:.3%} FS"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("speaker", "microphone", "prepare-replay", "prepare-tone", "validate-native-replay"))
    parser.add_argument("--device", default="hw:0,0")
    parser.add_argument("--duration", type=float, default=MAX_PLAYBACK_SECONDS)
    parser.add_argument("--amplitude", type=float, default=0.0001)
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("mic-test.raw"))
    parser.add_argument("--input", type=pathlib.Path)
    parser.add_argument("--format", choices=("S16_LE", "S32_LE"), default="S16_LE",
                        help="prepare-tone format; other modes remain S16_LE")
    parser.add_argument("--lead-silence", type=float, default=0)
    parser.add_argument("--tail-silence", type=float, default=0)
    parser.add_argument("--fade", type=float, default=0)
    args = parser.parse_args()
    if args.mode == "validate-native-replay":
        data = args.input.read_bytes() if args.input else b""
        if len(data) != 192000 or any(data[:38400]) or any(data[-38400:]):
            raise ValueError("replay must be 500 ms S32 stereo with >=100 ms zero at both ends")
        samples = [v[0] for v in struct.iter_unpack('<i', data)]
        if any(v % 256 or abs(v) > math.floor(2**23 * .0001) * 256 for v in samples):
            raise ValueError("replay exceeds 0.01%FS or is not native 24-MSB PCM")
        print("native replay byte layout and peak limit verified; no audio opened")
    elif args.mode == "prepare-tone":
        args.output.write_bytes(tone_data(args.duration, args.amplitude, args.format,
                                         args.lead_silence, args.tail_silence, args.fade))
    elif args.mode == "speaker":
        speaker(args.device, args.duration, args.amplitude)
    elif args.mode == "microphone":
        microphone(args.device, args.duration, args.output)
    else:
        if args.input is None:
            parser.error("prepare-replay requires --input")
        prepare_replay(args.input, args.output, args.amplitude)


if __name__ == "__main__":
    main()
