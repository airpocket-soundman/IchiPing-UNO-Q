#!/usr/bin/env python3
"""Bounded OWON acquisition; never drives UNO Q (external stimulus is separate)."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading


def capture(output, voltage_range=20, profile='compensation', i2s_rate=100000000, ch2_pin=99, trigger_ch=1, ch1_pin=98):
    import numpy as np
    from vds1022 import VDS1022, CH1, CH2, DC, EDGE, RISE, ONCE
    from vds1022.vds1022 import CMD

    # Upstream checks a Linux-only kernel attachment API unconditionally.
    # Windows libusb0 raises NotImplementedError; no Linux driver needs detaching.
    if sys.platform == 'win32':
        from usb.backend import libusb0
        backend = libusb0.get_backend()
        if backend is not None:
            type(backend).is_kernel_driver_active = lambda self, handle, interface: False

    class AcquisitionOnly(VDS1022):
        def _load_fpga(self, source):
            # Reuse the image initialized by the official app, never load one.
            if self._send(CMD.QUERY_FPGA, 0) != 1:
                raise RuntimeError('FPGA not initialized; open official app first, then close it')

        def write_flash(self, *args):
            raise RuntimeError('Flash writes disabled')

        def sync_flash(self, *args):
            raise RuntimeError('Flash writes disabled')

        def _save_calibration(self, *args):
            raise RuntimeError('Calibration writes disabled')

    rate = i2s_rate if profile == 'i2s' else 1250000
    level = 1.6 if profile == 'i2s' else 2.5
    dev = None
    deadline = None
    report = {'created_utc': datetime.now(timezone.utc).isoformat(),
              'kind': 'physical_unloaded_I2S' if profile == 'i2s' else 'physical_scope_compensation_NOT_UNO_audio',
              'api_version': '1.1.5', 'probe_ratio': 10, 'coupling': 'DC',
              'trigger': f'CH{trigger_ch} rising {level}V single (API scale)', 'requested_rate_hz': rate,
              'requested_range_v': voltage_range, 'status': 'STARTED'}
    if profile == 'i2s':
        report['wiring'] = {'CH1': f'GPIO{ch1_pin}', 'CH2': f'GPIO{ch2_pin}'}
    try:
        dev = AcquisitionOnly()
        # send() preserves and submits initialization, unlike stop() which clears it.
        dev.send(CMD.SET_RUNSTOP, 1)
        report.update(serial=dev.serial, hardware_version=dev.version,
                      fpga_version=dev.vfpga,
                      calibration_sha256=hashlib.sha256(
                          json.dumps(dev.calibration).encode()).hexdigest())
        dev.set_sampling(rate, roll=False, peak=False)
        dev.set_channel(CH1, range=voltage_range, offset=.3, probe=10, coupling=DC)
        dev.set_channel(CH2, range=voltage_range, offset=.3, probe=10, coupling=DC)
        dev.set_trigger(CH1 if trigger_ch == 1 else CH2, EDGE, RISE, level=level, position=.5, sweep=ONCE)
        dev.send(CMD.SET_RUNSTOP, 0)
        # wait() flushes the configuration/trigger queue under the API lock.
        dev.wait(.25)
        report['armed_utc'] = datetime.now(timezone.utc).isoformat()
        triggered = dev.get_triggered()
        (output / 'armed.json').write_text(json.dumps({
            'armed_utc': report['armed_utc'], 'serial': dev.serial,
            'already_triggered': triggered, 'profile': profile}), encoding='utf-8')
        if profile == 'i2s' and triggered:
            raise RuntimeError('Triggered before external stimulus; discard acquisition')
        deadline = threading.Timer(45, dev.stop)
        deadline.daemon = True
        deadline.start()
        frames = dev.fetch()
        deadline.cancel()
        # Save ADC samples before API voltage conversion can clip buffers in place.
        np.savez(output / 'adc.npz', **{f.name: np.array(f.buffer, copy=True) for f in frames})
        with (output / 'waveform.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(['time_s'] + [f.name + '_v' for f in frames])
            writer.writerows(zip(frames.x(), *(f.y() for f in frames)))
        report['sampling_rate_hz'] = dev.sampling_rate
        report['channels'] = {}
        for frame in frames:
            y = frame.y()
            low, high = np.percentile(y, [10, 90])
            edges = np.flatnonzero((y[:-1] < (low + high)/2) & (y[1:] >= (low + high)/2))
            frequency = (dev.sampling_rate * (len(edges)-1) / float(edges[-1]-edges[0])
                         if len(edges) >= 2 and high - low > 1 else None)
            aliased_bclk = (profile == 'i2s' and rate < 6144000
                            and (ch1_pin if frame.name == 'CH1' else ch2_pin) == 98)
            if aliased_bclk:
                frequency = None
            report['channels'][frame.name] = {
                'samples': len(y), 'min_v': float(y.min()), 'max_v': float(y.max()),
                'low_p10_v': float(low), 'high_p90_v': float(high),
                'robust_vpp': float(high-low), 'frequency_hz_from_edges': frequency,
                'device_frequency_hz': frame.frequency,
                'bclk_undersampled_do_not_interpret': aliased_bclk,
                'rising_edge_indices': edges.tolist() if high-low > 1 else [],
                'note': (f'CH1=GPIO{ch1_pin}, CH2=GPIO{ch2_pin}; voltage scale UNVERIFIED'
                         if profile == 'i2s' else 'Only CH1 confirmed on compensation output.')}
        report['status'] = 'ACQUIRED; calibration accuracy not certified'
    except Exception as exc:
        report.update(status='FAILED', error=repr(exc))
        raise
    finally:
        if deadline is not None:
            deadline.cancel()
        if dev is None:
            dev = getattr(AcquisitionOnly, '_instance', None)
        if dev is not None:
            try:
                report['stop_acknowledged'] = bool(dev.stop())
            finally:
                dev.dispose()
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--execute', action='store_true', help='Open the physical scope')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--range-v', type=int, choices=(20, 50), default=20)
    parser.add_argument('--profile', choices=('compensation', 'i2s'), default='compensation')
    parser.add_argument('--i2s-rate', type=int, choices=(1000000, 25000000, 100000000), default=100000000)
    parser.add_argument('--ch2-pin', type=int, choices=(98, 99, 101), default=99)
    parser.add_argument('--ch1-pin', type=int, choices=(98, 99), default=98)
    parser.add_argument('--trigger-ch', type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    if not args.execute:
        print('No hardware opened. Close OWON GUI, confirm profile wiring and x10, then use --execute.')
        return
    if args.worker:
        capture(args.output, args.range_v, args.profile, args.i2s_rate, args.ch2_pin, args.trigger_ch, args.ch1_pin)
        return
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        result = subprocess.run([sys.executable, __file__, str(args.output.resolve()),
                                 '--execute', '--worker', '--range-v', str(args.range_v),
                                 '--profile', args.profile, '--i2s-rate', str(args.i2s_rate),
                                 '--ch2-pin', str(args.ch2_pin), '--trigger-ch', str(args.trigger_ch),
                                 '--ch1-pin', str(args.ch1_pin)],
                                capture_output=True, text=True, timeout=60 if args.profile == 'i2s' else 20)
    except subprocess.TimeoutExpired:
        (args.output / 'timeout.txt').write_text(
            'API worker timed out and was terminated. Scope stop NOT verified; this script does not operate UNO Q.\n')
        raise
    (args.output / 'api.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
