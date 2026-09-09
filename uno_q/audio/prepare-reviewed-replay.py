#!/usr/bin/env python3
"""Offline extraction of a verified 100 ms test-tone segment; never plays audio."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def prepare(data):
    if len(data) % 4 or len(data) < 9600 * 4:
        raise ValueError('need at least 200 ms of stereo S16_LE capture')
    frames = list(struct.iter_unpack('<hh', data))[4800:9600]
    if any(right != 0 for left, right in frames):
        raise ValueError('unused microphone slot is not zero')
    x = [left for left, right in frames]
    if max(abs(v) for v in x) > 65:
        raise ValueError('segment peak exceeds 0.2%FS review threshold')
    mean = sum(x) / len(x)
    x = [v - mean for v in x]
    power = sum(v*v for v in x) / len(x)
    def amplitude(h):
        re = sum(v * math.cos(2*math.pi*440*h*i/48000) for i, v in enumerate(x))
        im = sum(v * math.sin(2*math.pi*440*h*i/48000) for i, v in enumerate(x))
        return 2 * math.hypot(re, im) / len(x)
    a = [amplitude(h) for h in range(1, 9)]
    fraction = a[0]**2 / (2*power) if power else 0
    harmonics = math.sqrt(sum(v*v for v in a[1:])) / a[0] if a[0] else 1
    if fraction < .6 or harmonics > .05:
        raise ValueError('segment fails tone-dominance/harmonic review gate')
    peak = max(abs(v) for v in x)
    out = bytearray(4800 * 8)  # 100 ms silent clock warmup
    target = math.floor((2**23 - 1) * .0001)
    for i, v in enumerate(x):
        envelope = min(1, i / 240, (len(x)-1-i) / 240)
        sample = round(v / peak * target * envelope) << 8
        out.extend(struct.pack('<ii', sample, sample))
    out.extend(bytes((24000-9600) * 8))  # Keep valid zero data until reset.
    return bytes(out), {'source_sha256': hashlib.sha256(data).hexdigest(),
        'source_segment_seconds': [.1, .2], 'source_format': 'S16_LE stereo left',
        'tone_440_power_fraction': fraction, 'harmonic_ratio_estimate': harmonics,
        'processing': 'DC removal, peak reduction, 5 ms fades; no tone resynthesis or frequency filtering',
        'output_format': 'S32_LE with native 24 significant MSBs',
        'output_seconds': .5, 'nonzero_audio_seconds_max': .1,
        'output_peak_fs_max': target / 2**23,
        'verdict': 'eligible for guarded quiet replay of this segment only'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    output, report = prepare(args.input.read_bytes())
    args.output.write_bytes(output)
    args.output.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
