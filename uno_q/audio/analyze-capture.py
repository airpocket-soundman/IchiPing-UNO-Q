#!/usr/bin/env python3
"""Offline S16_LE mono/stereo inspection. Never opens an audio device."""
import argparse
import json
import math
import struct
from pathlib import Path

def inspect(data, rate=48000, channels=1):
    if channels not in (1, 2) or not data or len(data) % (2 * channels):
        raise ValueError('expected nonempty, frame-aligned S16_LE data')
    samples = list(struct.iter_unpack('<' + 'h' * channels, data))
    report = {'format': 'S16_LE', 'rate': rate, 'frames': len(samples),
              'seconds': len(samples) / rate, 'channels': [],
              'acoustic_verdict': 'UNVERIFIED: compare tone and silent windows'}
    for channel in range(channels):
        x = [frame[channel] / 32768 for frame in samples]
        mean = sum(x) / len(x)
        windows = []
        step = rate // 10
        for start in range(0, len(x) - step + 1, step):
            segment = x[start:start + step]
            dc = sum(segment) / step
            power = sum((v-dc)**2 for v in segment) / step
            # 100 ms contains exactly 44 cycles at 440 Hz.
            re = sum((v-dc)*math.cos(2*math.pi*440*i/rate)
                     for i, v in enumerate(segment))
            im = sum((v-dc)*math.sin(2*math.pi*440*i/rate)
                     for i, v in enumerate(segment))
            tone_power = 2*(re*re+im*im)/(step*step)
            windows.append({'start_seconds': start/rate,
                            'rms_fs': math.sqrt(power),
                            'tone_440_power_fraction': tone_power/power if power else 0})
        report['channels'].append({'channel': channel, 'dc_fs': mean,
            'peak_fs': max(abs(v) for v in x),
            'rms_fs': math.sqrt(sum(v*v for v in x)/len(x)),
            'clipped_samples': sum(abs(frame[channel]) >= 32767 for frame in samples),
            'zero_fraction': sum(v == 0 for v in x)/len(x), 'windows': windows})
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    parser.add_argument('--channels', type=int, choices=(1, 2), default=1)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = json.dumps(inspect(args.capture.read_bytes(), channels=args.channels), indent=2)
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    print(report)
