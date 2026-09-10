#!/usr/bin/env python3
"""WS/DIN timing estimate; assumes 32 BCLK per WS half-period, no BCLK captured."""
import argparse
import csv
import json
from pathlib import Path
import struct


def compare(source, pcm, threshold=.9):
    with source.open(encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    ws = [float(r['CH1_v']) > threshold for r in rows]
    din = [float(r['CH2_v']) > threshold for r in rows]
    edges = [i for i in range(1, len(ws)) if ws[i] != ws[i-1]]
    reference = list(struct.unpack('<' + 'I'*(pcm.stat().st_size//4), pcm.read_bytes()))
    results = {}
    for offset in (.5, 1.5, 2.5):
        slots = []
        for left, right in zip(edges[:-1], edges[1:]):
            indices = [round(left + (bit+offset)*(right-left)/32) for bit in range(32)]
            if indices[-1] >= len(din):
                continue
            word = 0
            for i in indices:
                word = (word << 1) | din[i]
            slots.append({'channel': 'right' if ws[left] else 'left', 'u32': word})
        words = [slot['u32'] for slot in slots]
        parity = 1 if slots and slots[0]['channel'] == 'right' else 0
        matches = [i for i in range(parity, len(reference)-len(words)+1, 2)
                   if reference[i:i+len(words)] == words] if words and any(words) else []
        results[str(offset)] = {'slots': slots, 'matching_pcm_word_offsets': matches}
    return {'kind': 'WS_DIN_ESTIMATE_NOT_THREE_SIGNAL_DECODE',
            'threshold_api_v': threshold, 'assumed_bits_per_ws_half_period': 32,
            'standard_i2s_sample_offset_bits': 1.5, 'offset_comparison': results,
            'caveat': 'BCLK not simultaneously captured; does not prove setup/hold, full waveform or acoustic quality.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('pcm', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = compare(args.source, args.pcm)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
