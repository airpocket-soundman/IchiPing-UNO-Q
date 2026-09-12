#!/usr/bin/env python3
"""Low-level, deliberately quiet MI2S0 smoke tests for IchiPing UNO Q."""

from __future__ import annotations

import argparse
import math
import pathlib
import random
import struct
import subprocess
import tempfile


RATE = 48_000
CHANNELS = 2
SAMPLE_BYTES = 2
FORMAT = "S16_LE"
FULL_SCALE = 2**15 - 1
MAX_PLAYBACK_SECONDS = 0.5
MAX_PLAYBACK_AMPLITUDE = 0.012
MAX_EXTERNAL_CLOCK_SECONDS = 6.5
MAX_CALIBRATION_SECONDS = 5.0
MAX_CALIBRATION_RMS = 0.10


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def tone_data(duration: float, amplitude: float, pcm_format: str = "S16_LE",
              lead_silence: float = 0, tail_silence: float = 0,
              fade: float = 0) -> bytes:
    if not 0 < duration <= MAX_PLAYBACK_SECONDS:
        raise ValueError("speaker duration must be > 0 and <= 0.5 seconds")
    if not 0 <= amplitude <= MAX_PLAYBACK_AMPLITUDE:
        raise ValueError(
            f"speaker amplitude must be >= 0 and <= {MAX_PLAYBACK_AMPLITUDE}"
        )
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


def clock_silence_data(duration: float) -> bytes:
    """Bounded S32_LE stereo zeros used only to clock external-reference capture."""
    if not 0 < duration <= MAX_EXTERNAL_CLOCK_SECONDS:
        raise ValueError(
            f"external clock duration must be > 0 and <= {MAX_EXTERNAL_CLOCK_SECONDS}"
        )
    return bytes(round(RATE * duration) * 8)


def white_noise_data(active_seconds: float, rms_amplitude: float, seed: int,
                     lead_silence: float = 0.5,
                     tail_silence: float = 1.0,
                     fade: float = 0.02) -> bytes:
    """Deterministic bounded S32_LE stereo white noise for level calibration.

    ``rms_amplitude`` is the RMS of the active uniform-noise source.  Silent
    padding keeps MI2S clocks alive before and after the five-second acoustic
    interval so a longer microphone capture can start and finish cleanly.
    """
    if not 0 < active_seconds <= MAX_CALIBRATION_SECONDS:
        raise ValueError(
            f"active noise duration must be > 0 and <= {MAX_CALIBRATION_SECONDS}"
        )
    if not 0 < rms_amplitude <= MAX_CALIBRATION_RMS:
        raise ValueError(
            f"noise RMS must be > 0 and <= {MAX_CALIBRATION_RMS}"
        )
    if min(lead_silence, tail_silence, fade) < 0 or 2 * fade >= active_seconds:
        raise ValueError("invalid white-noise padding/fade")
    total_seconds = lead_silence + active_seconds + tail_silence
    if total_seconds > MAX_EXTERNAL_CLOCK_SECONDS:
        raise ValueError("white-noise PCM including padding exceeds clock limit")

    rng = random.Random(seed)
    active_frames = round(RATE * active_seconds)
    fade_frames = round(RATE * fade)
    peak24 = 2**23 - 1
    # Uniform(-sqrt(3), sqrt(3)) has unit RMS before the short fade envelope.
    scale = peak24 * rms_amplitude * math.sqrt(3.0)
    frames = bytearray(round(RATE * lead_silence) * 8)
    for index in range(active_frames):
        envelope = 1.0
        if fade_frames:
            envelope = min(1.0, (index + 1) / fade_frames,
                           (active_frames - index) / fade_frames)
        sample = round(rng.uniform(-1.0, 1.0) * scale * envelope)
        packed = struct.pack("<i", sample << 8)
        frames.extend(packed + packed)
    frames.extend(bytes(round(RATE * tail_silence) * 8))
    return bytes(frames)


PRBS_SOURCE_RATE = 16_000
PRBS_ACTIVE_SECONDS = 2.0
PRBS_LEAD_SILENCE = 0.5
PRBS_TAIL_SILENCE = 1.0
PRBS_TAPS_PER_PHASE = 24


def prbs_source(seed: int, frames: int = round(PRBS_SOURCE_RATE * PRBS_ACTIVE_SECONDS)) -> list[int]:
    """The original collector excitation: ±1 binary noise at 16 kHz."""
    rng = random.Random(seed)
    return [1 if rng.getrandbits(1) else -1 for _ in range(frames)]


def _interpolation_kernel() -> list[float]:
    # Windowed-sinc 3x interpolator with a 7.6 kHz cutoff, emulating the
    # original 16 kHz DAC stream band limit (0-8 kHz) on the 48 kHz MI2S link.
    length = 3 * PRBS_TAPS_PER_PHASE
    centre = (length - 1) / 2
    cutoff = 7_600 / RATE
    kernel = []
    for index in range(length):
        x = index - centre
        sinc = 2 * cutoff if x == 0 else math.sin(2 * math.pi * cutoff * x) / (math.pi * x)
        window = 0.5 - 0.5 * math.cos(2 * math.pi * index / (length - 1))
        kernel.append(3 * sinc * window)
    return kernel


PRBS_MAX_REPEATS = 100


def prbs16k_data(amplitude: float, seed: int, repeats: int = 1, gap: float = 0.3) -> bytes:
    """Deterministic S32_LE stereo PCM of the original 2 s PRBS excitation.

    ``amplitude`` is the ±level of the 16 kHz binary source as a fraction of
    full scale (the original collector used ±0.009 before speaker gain).  The
    source is band-limited to 8 kHz and resampled 3x; silent padding keeps
    MI2S clocks alive while the capture starts and finishes.  ``repeats``
    back-to-back frames (the same sequence each time, like the original
    collector) are separated by ``gap`` seconds of silence for room decay.
    """
    if not 0 < amplitude < 1:
        raise ValueError("PRBS amplitude must be > 0 and < 1 FS")
    if not 1 <= repeats <= PRBS_MAX_REPEATS:
        raise ValueError(f"PRBS repeats must be 1..{PRBS_MAX_REPEATS}")
    if repeats > 1 and not 0.1 <= gap <= 2.0:
        raise ValueError("PRBS gap must be 0.1..2.0 s")
    source = prbs_source(seed)
    kernel = _interpolation_kernel()
    upsampled = [0.0] * (len(source) * 3 + len(kernel) - 1)
    for index, value in enumerate(source):
        base = index * 3
        for tap, weight in enumerate(kernel):
            upsampled[base + tap] += value * weight
    delay = (len(kernel) - 1) // 2
    active = upsampled[delay:delay + len(source) * 3]
    peak24 = 2**23 - 1
    samples = [round(value * amplitude * peak24) for value in active]
    if max(map(abs, samples)) > peak24:
        raise ValueError("PRBS amplitude clips after band limiting")
    active = bytearray()
    for sample in samples:
        packed = struct.pack("<i", sample << 8)
        active.extend(packed + packed)
    silence_gap = bytes(round(RATE * gap) * 8)
    frames = bytearray(round(RATE * PRBS_LEAD_SILENCE) * 8)
    for index in range(repeats):
        if index:
            frames.extend(silence_gap)
        frames.extend(active)
    frames.extend(bytes(round(RATE * PRBS_TAIL_SILENCE) * 8))
    return bytes(frames)


def silence_data(repeats: int = 1, gap: float = 0.3) -> bytes:
    """All-zero S32_LE stereo PCM with the prbs16k timing (ambient capture).

    The speaker stays silent while MI2S clocks run, so the capture records
    the room/ambient noise that the training NoiseOverlay mixes in.
    """
    if not 1 <= repeats <= PRBS_MAX_REPEATS:
        raise ValueError(f"silence repeats must be 1..{PRBS_MAX_REPEATS}")
    return bytes(round(RATE * prbs16k_seconds(repeats, gap)) * 8)


def prbs16k_seconds(repeats: int = 1, gap: float = 0.3) -> float:
    """Total PCM duration produced by prbs16k_data."""
    return (PRBS_LEAD_SILENCE + repeats * PRBS_ACTIVE_SECONDS
            + (repeats - 1) * gap + PRBS_TAIL_SILENCE)


CHIME_FREQUENCY = 880.0
CHIME_PEAK = 0.02
CHIME_ON_SECONDS = 0.25
CHIME_PERIOD_SECONDS = 0.5
CHIME_COUNT = 3


def chime_data() -> bytes:
    """Operator call: three 880 Hz beeps inside 3.5 s of clocked S32_LE PCM.

    Same padding as prbs16k (0.5 s lead) so the fixed 3 s capture ends
    before the PCM does.
    """
    total = round(RATE * (PRBS_LEAD_SILENCE + PRBS_ACTIVE_SECONDS + PRBS_TAIL_SILENCE))
    lead = round(RATE * PRBS_LEAD_SILENCE)
    on = round(RATE * CHIME_ON_SECONDS)
    period = round(RATE * CHIME_PERIOD_SECONDS)
    fade = round(RATE * 0.01)
    peak24 = 2**23 - 1
    frames = bytearray()
    for index in range(total):
        offset = index - lead
        sample = 0
        if offset >= 0 and offset // period < CHIME_COUNT and offset % period < on:
            t = offset % period
            envelope = min(1.0, (t + 1) / fade, (on - t) / fade)
            sample = round(peak24 * CHIME_PEAK * envelope *
                           math.sin(2 * math.pi * CHIME_FREQUENCY * t / RATE))
        packed = struct.pack("<i", sample << 8)
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
    parser.add_argument("mode", choices=("speaker", "microphone", "prepare-replay", "prepare-tone", "prepare-clock-silence", "prepare-white-noise", "prepare-prbs16k", "prepare-silence", "prepare-chime", "validate-native-replay"))
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
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--repeats", type=int, default=1, help="prepare-prbs16k frame count")
    parser.add_argument("--gap", type=float, default=0.3, help="prepare-prbs16k silence between frames")
    args = parser.parse_args()
    if args.mode == "validate-native-replay":
        data = args.input.read_bytes() if args.input else b""
        if len(data) != 192000 or any(data[:38400]) or any(data[-38400:]):
            raise ValueError("replay must be 500 ms S32 stereo with >=100 ms zero at both ends")
        samples = [v[0] for v in struct.iter_unpack('<i', data)]
        if any(v % 256 or abs(v) > math.floor(2**23 * .006) * 256 for v in samples):
            raise ValueError("replay exceeds 0.6%FS or is not native 24-MSB PCM")
        print("native replay byte layout and 0.6%FS peak limit verified; no audio opened")
    elif args.mode == "prepare-tone":
        args.output.write_bytes(tone_data(args.duration, args.amplitude, args.format,
                                         args.lead_silence, args.tail_silence, args.fade))
    elif args.mode == "prepare-clock-silence":
        args.output.write_bytes(clock_silence_data(args.duration))
    elif args.mode == "prepare-white-noise":
        args.output.write_bytes(
            white_noise_data(args.duration, args.amplitude, args.seed)
        )
    elif args.mode == "prepare-prbs16k":
        args.output.write_bytes(prbs16k_data(args.amplitude, args.seed, args.repeats, args.gap))
    elif args.mode == "prepare-silence":
        args.output.write_bytes(silence_data(args.repeats, args.gap))
    elif args.mode == "prepare-chime":
        args.output.write_bytes(chime_data())
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
