#!/usr/bin/env python3
"""Offline-only measurement preparation and standard-I2S CSV decoder (stdlib).

Never opens a device, starts audio, or deploys files. CSV rows are complete logic
states after the timestamp, either regularly sampled or transition-compressed.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import struct
from datetime import datetime, timezone


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location(
        'smoke', Path(__file__).with_name('audio-smoke-test.py'))
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    # Floor, not round: stay strictly <= 0.01%FS in native 24-MSB PCM.
    amplitude = math.floor(2**23 * .0001) / (2**23 - 1)
    files = {}
    for name, level in (('zero', 0), ('sine', amplitude)):
        path = directory / (name + '.raw')
        path.write_bytes(smoke.tone_data(.5, level, 'S32_LE', .1, .3, .005))
        files[path.name] = digest(path)
    manifest = {
        'kind': 'offline_preparation_NOT_hardware_result',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'pcm': {'rate': 48000, 'channels': 2, 'format': 'S32_LE',
                'significant_bits': 'upper 24', 'file_seconds': .5,
                'tone_seconds': .1, 'lead_seconds': .1, 'tail_seconds': .3,
                'fade_seconds': .005, 'frequency_hz': 440,
                'peak_limit_fs': .0001},
        'sha256': files,
        'wiring': {'D0': 'GPIO98 BCLK', 'D1': 'GPIO99 WS',
                   'D2': 'GPIO101 amplifier DIN', 'D3': 'GPIO100 microphone SD'},
        'measurement': {
            'board_serial': None, 'software_commit': None, 'kernel': None,
            'instrument_models_serials_versions': None,
            'connected_boards': None, 'probe_locations': None,
            'sample_rate_hz': None, 'threshold_v': None,
            'scope_probe_attenuation_coupling_ranges': None,
            'capture_files': [], 'result': 'NOT_RUN'},
        'safety': '500ms reset request before route enable; acoustic cutoff unverified',
    }
    (directory / 'manifest.json').write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def states(path, data_column):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        required = ('time_s', 'bclk', 'ws', data_column)
        if not reader.fieldnames or not set(required) <= set(reader.fieldnames):
            raise ValueError('required CSV columns: ' + ','.join(required))
        previous_time = -math.inf
        for line, row in enumerate(reader, 2):
            t = float(row['time_s'])
            if not math.isfinite(t) or t <= previous_time:
                raise ValueError(f'line {line}: timestamps must be finite and increasing')
            bits = [row[key].strip() for key in required[1:]]
            if any(bit not in ('0', '1') for bit in bits):
                raise ValueError(f'line {line}: logic states must be 0 or 1')
            previous_time = t
            yield (t, *(int(bit) for bit in bits))


def decode(rows, expected_bclk=3072000):
    """32-bit slots, WS low=left, rising-edge sampling, one-bit I2S delay.

    The rising edge observing a WS change still carries the previous slot's LSB.
    No assumption about the initial partial slot is made. A clock gap discards
    partial state and requires another observed WS transition for synchronization.
    """
    samples, periods = [], []
    errors = {'short_slots': 0, 'long_slots': 0, 'clock_gaps': 0,
              'data_changes_on_rising_edge': 0, 'ws_changes_on_rising_edge': 0}
    previous = None
    capture_start = None
    last_rise = first_rise = None
    sampled_ws = None
    slot = None
    count = word = 0
    start = None
    for row in rows:
        t, clk, ws, bit = row
        if capture_start is None:
            capture_start = t
        if previous is not None and previous[1] == 0 and clk == 1:
            if first_rise is None:
                first_rise = t
            if bit != previous[3]:
                errors['data_changes_on_rising_edge'] += 1
            if ws != previous[2]:
                errors['ws_changes_on_rising_edge'] += 1
            if last_rise is not None:
                period = t - last_rise
                periods.append(period)
                if period > 1.5 / expected_bclk:
                    errors['clock_gaps'] += 1
                    slot = sampled_ws = None
            last_rise = t
            if slot is not None:
                count += 1
                word = (word << 1) | bit
            if sampled_ws is not None and ws != sampled_ws:
                if slot is not None:
                    if count == 32:
                        signed = word - 2**32 if word & 2**31 else word
                        samples.append({'time_s': start, 'channel': slot,
                                        'sample_s32': signed})
                    else:
                        errors['short_slots' if count < 32 else 'long_slots'] += 1
                slot, count, word, start = ws, 0, 0, t
            # Bound accumulation on an absent WS clock.
            if count > 32:
                word = 0
            sampled_ws = ws
        previous = row
    timing = {
        'capture_start_s': capture_start,
        'capture_end_s': previous[0] if previous is not None else None,
        'tail_after_last_bclk_rise_s': (previous[0] - last_rise
                                        if last_rise is not None else None),
        'final_logic_state': ({'bclk': previous[1], 'ws': previous[2], 'data': previous[3]}
                              if previous is not None else None),
        'first_bclk_rise_s': first_rise, 'last_bclk_rise_s': last_rise,
        'observed_clock_span_s': None if first_rise is None else last_rise - first_rise,
        'bclk_hz_median': 1 / statistics.median(periods) if periods else None,
        'rise_period_min_s': min(periods) if periods else None,
        'rise_period_max_s': max(periods) if periods else None,
        'discarded_final_partial_slot': slot is not None,
    }
    return samples, errors, timing


def compare(samples, reference, offset):
    """Explicit alignment only; never auto-select a best-looking sine segment."""
    if offset < 0:
        raise ValueError('reference offset must be nonnegative')
    data = reference.read_bytes()
    if not data or len(data) % 8:
        raise ValueError('reference must be nonempty S32_LE stereo')
    frames = list(struct.iter_unpack('<ii', data))
    # Skip the first right slot if capture began mid-frame.
    start = next((i for i, item in enumerate(samples) if item['channel'] == 0), len(samples))
    selected = samples[start:]
    mismatches = checked = 0
    for index, item in enumerate(selected):
        frame, channel = offset + index // 2, index % 2
        if item['channel'] != channel:
            raise ValueError('missing/duplicated channel: cannot align reference across broken frames')
        if frame >= len(frames):
            break
        mismatches += item['sample_s32'] != frames[frame][channel]
        checked += 1
    return {'reference_sha256': digest(reference), 'reference_frame_offset': offset,
            'checked_slots': checked, 'mismatched_slots': mismatches,
            'decoded_slots_beyond_reference': len(selected) - checked,
            'reference_frames': len(frames),
            'entire_reference_matched': offset == 0 and checked == 2 * len(frames) and mismatches == 0,
            'note': 'Exact wire-word hypothesis only; DSP transforms require separate investigation.'}


def analyze(path, output, data_column, reference=None, offset=None):
    if reference is not None and offset is None:
        raise ValueError('--reference requires explicit --reference-frame-offset')
    samples, errors, timing = decode(states(path, data_column))
    report = {'kind': 'digital_only_NOT_acoustic_or_electrical_pass',
              'source_sha256': digest(path), 'data_column': data_column,
              'assumption': 'standard I2S; 32-bit slots; rising edge; WS=0 left',
              'complete_slots': len(samples), 'errors': errors, 'timing': timing,
              'channels': {str(ch): {
                  'slots': sum(item['channel'] == ch for item in samples),
                  'peak_fs': max((abs(item['sample_s32']) / 2**31 for item in samples
                                  if item['channel'] == ch), default=None),
                  'nonzero_slots': sum(item['channel'] == ch and item['sample_s32'] != 0
                                       for item in samples)} for ch in (0, 1)}}
    if reference is not None:
        report['comparison'] = compare(samples, reference, offset)
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'decoded.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=('time_s', 'channel', 'sample_s32'))
        writer.writeheader()
        writer.writerows(samples)
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('directory', type=Path)
    dec = sub.add_parser('decode')
    dec.add_argument('csv', type=Path)
    dec.add_argument('output', type=Path)
    dec.add_argument('--data-column', choices=('din', 'mic'), default='din')
    dec.add_argument('--reference', type=Path)
    dec.add_argument('--reference-frame-offset', type=int)
    args = parser.parse_args()
    if args.command == 'prepare':
        report = prepare(args.directory)
    else:
        report = analyze(args.csv, args.output, args.data_column,
                         args.reference, args.reference_frame_offset)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
