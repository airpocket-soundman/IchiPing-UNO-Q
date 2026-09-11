#!/usr/bin/env python3
"""Convert this project's 16-channel SLogic SR capture to transition CSV.

Reads actual sample indices, avoiding vendor CSV time-unit/dedup ambiguity.
Requires numpy. D0=BCLK, D1=WS, D2=amp DIN, D3=mic SD.
"""
import argparse
import configparser
import csv
import json
import re
import zipfile
from pathlib import Path
import numpy as np


def convert(source, destination):
    with zipfile.ZipFile(source) as archive:
        cfg = configparser.ConfigParser()
        cfg.read_string(archive.read('metadata').decode())
        dev = cfg['device 1']
        if dev.getint('unitsize') != 2 or any(dev.get(f'probe{i+1}') != f'D{i}' for i in range(4)):
            raise ValueError('Expected 16-bit samples with D0..D3 as bits 0..3')
        match = re.fullmatch(r'([\d.]+)\s*(Hz|kHz|MHz|GHz)', dev['samplerate'])
        if not match:
            raise ValueError('Unknown samplerate units')
        rate = float(match[1]) * {'Hz': 1, 'kHz': 1e3, 'MHz': 1e6, 'GHz': 1e9}[match[2]]
        prefix = dev['capturefile'] + '-'
        chunks = sorted((n for n in archive.namelist() if n.startswith(prefix)),
                        key=lambda n: int(n[len(prefix):]))
        if not chunks or rate <= 0:
            raise ValueError('Empty capture or invalid rate')
        offset, previous, last_written, rows = 0, None, -1, 0
        with destination.open('x', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(['time_s', 'bclk', 'ws', 'din', 'mic'])
            for name in chunks:
                data = np.frombuffer(archive.read(name), dtype='<u2') & 15
                if not len(data):
                    continue
                indices = np.flatnonzero(data[1:] != data[:-1]) + 1
                if previous is None or data[0] != previous:
                    indices = np.concatenate(([0], indices))
                for index in indices:
                    value = int(data[index])
                    last_written = offset + int(index)
                    writer.writerow([format(last_written / rate, '.12g'),
                                     *(value >> bit & 1 for bit in range(4))])
                    rows += 1
                offset += len(data)
                previous = int(data[-1])
            if not offset:
                raise ValueError('No samples')
            if last_written != offset - 1:
                writer.writerow([format((offset - 1) / rate, '.12g'),
                                 *(previous >> bit & 1 for bit in range(4))])
                rows += 1
        return {'samples': offset, 'samplerate_hz': rate, 'duration_s': offset / rate,
                'csv_rows': rows, 'source': str(source), 'output': str(destination)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(convert(args.source, args.destination), indent=2))
