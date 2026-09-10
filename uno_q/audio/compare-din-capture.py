#!/usr/bin/env python3
"""Compare scope BCLK/DIN samples to PCM bits without assuming WS alignment.

Exact subsequence matches are candidates, not proof of channel/I2S framing.
No hardware access. Threshold is in uncalibrated API volts.
"""
import argparse
import csv
import json
from pathlib import Path
import struct


def compare(waveform, pcm, threshold=1.4):
    with waveform.open(encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    clock = [float(r['CH1_v']) >= threshold for r in rows]
    # First sample after each threshold crossing, near the rising edge.
    edges = [i for i in range(1, len(clock)) if clock[i] and not clock[i-1]]
    bits = ''.join('1' if float(rows[i]['CH2_v']) >= threshold else '0' for i in edges)
    # Keep a little context before first data high; omit long leading idle zero.
    first = bits.find('1')
    start = max(0, first-32) if first >= 0 else 0
    observed = bits[start:]
    words = [v[0] for v in struct.iter_unpack('<I', pcm.read_bytes())]
    reference = ''.join(f'{word:032b}' for word in words)
    matches = []
    pos = reference.find(observed) if first >= 0 and len(observed) >= 64 else -1
    while pos >= 0 and len(matches) < 100:
        matches.append({'bit_offset': pos, 'pcm_frame': pos//64, 'bit_in_frame': pos%64})
        pos = reference.find(observed, pos+1)
    return {'status': 'CANDIDATE_EXACT_SUBSEQUENCE' if matches else 'NO_EXACT_MATCH_OR_INSUFFICIENT_DATA',
            'threshold_api_v': threshold, 'sampled_bits': len(bits),
            'compared_bits': len(observed), 'high_bits': observed.count('1'),
            'observed_bits': observed, 'matches': matches,
            'caveat': 'No WS captured: frame phase, left/right and I2S delay unverified. No acoustic verdict.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('waveform', type=Path)
    p.add_argument('pcm', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    result = compare(args.waveform, args.pcm)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != 'observed_bits'}, indent=2))
