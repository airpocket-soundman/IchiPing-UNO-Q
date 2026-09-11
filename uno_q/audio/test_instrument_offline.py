"""Synthetic I2S tests; no measurement device, network or audio is opened."""
import csv
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('instrument', Path(__file__).with_name('instrument-analysis.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def waveform(words, slot_bits=32):
    # Independently serialize: each slot starts with the preceding word's LSB,
    # then its own bits 31..1. Its LSB occurs at the next WS transition.
    rows = [(0., 0, 1, 0)]
    t = 0.
    previous_lsb = 0
    for index, word in enumerate(words):
        bits = [previous_lsb] + [(word >> bit) & 1 for bit in range(31, 0, -1)]
        previous_lsb = word & 1
        for bit in bits[:slot_bits]:
            t += 1 / 6144000
            rows.append((t, 0, index % 2, bit))
            t += 1 / 6144000
            rows.append((t, 1, index % 2, bit))
    return rows


class InstrumentTests(unittest.TestCase):
    def test_i2s_delay_sign_and_channels(self):
        words = [0, 0, 0x12345679, -12345, 0x7fffffff, -2147483648, 0, 0]
        samples, errors, timing = tool.decode(waveform(words))
        self.assertEqual([s['sample_s32'] for s in samples], words[1:-1])
        self.assertEqual([s['channel'] for s in samples], [1, 0, 1, 0, 1, 0])
        self.assertFalse(any(errors.values()))
        self.assertAlmostEqual(timing['bclk_hz_median'], 3072000, places=2)

    def test_short_slot(self):
        samples, errors, _ = tool.decode(waveform([0] * 8, 31))
        self.assertFalse(samples)
        self.assertGreater(errors['short_slots'], 0)

    def test_clock_gap(self):
        rows = waveform([0] * 8)
        rows = [((t + .001 if i > 200 else t), c, w, d)
                for i, (t, c, w, d) in enumerate(rows)]
        _, errors, _ = tool.decode(rows)
        self.assertEqual(errors['clock_gaps'], 1)

    def test_capture_tail_is_separate_from_clock_span(self):
        rows = waveform([0] * 5)
        t, _, ws, bit = rows[-1]
        rows.extend([(t + 1e-6, 0, ws, bit), (t + .1, 0, ws, bit)])
        _, _, timing = tool.decode(rows)
        self.assertAlmostEqual(timing['tail_after_last_bclk_rise_s'], .1)
        self.assertEqual(timing['final_logic_state']['bclk'], 0)

    def test_playback_only_safety_structure(self):
        # Static regression only; does not simulate systemd, ALSA or a real reset.
        script = Path(__file__).with_name('safe-audio-test.sh').read_text()
        branch = script.split('\tinstrument-playback)')[1].split(';;')[0]
        self.assertIn('playback-on', branch)
        self.assertNotIn('capture-on', branch)
        self.assertNotIn('arecord', branch)
        self.assertLess(script.index('--on-active=500ms'), script.index('\tinstrument-playback)'))
        self.assertLess(script.index('validate-native-replay'), script.index('--on-active=500ms'))
        self.assertIn('ICHIPING_EXPECTED_USB_SERIAL:?', script)

    def test_rising_edge_changes_are_flagged(self):
        rows = waveform([0] * 5)
        t, clk, ws, _ = rows[20]
        rows[20] = (t, clk, ws, 1)
        _, errors, _ = tool.decode(rows)
        self.assertGreater(errors['data_changes_on_rising_edge'], 0)

    def test_duplex_measurement_keeps_reset_and_unique_capture(self):
        script = Path(__file__).with_name('safe-audio-test.sh').read_text()
        branch = script.split('\tinstrument-duplex)')[1].split(';;')[0]
        self.assertLess(script.index('--on-active=500ms'), script.index('\tinstrument-duplex)'))
        self.assertIn('mktemp /var/tmp/ichiping-instrument-duplex-', script)
        self.assertIn('audio-cycle-test.sh', branch)
        self.assertNotIn('rm ', branch)
        cycle = Path(__file__).with_name('audio-cycle-test.sh').read_text()
        self.assertLess(cycle.index('state: RUNNING'), cycle.index('arecord -D'))

    def test_empty_capture_not_pass(self):
        samples, _, timing = tool.decode([])
        self.assertEqual(samples, [])
        self.assertIsNone(timing['bclk_hz_median'])

    def test_prepare_limits_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'run'
            manifest = tool.prepare(path)
            self.assertEqual(manifest['measurement']['result'], 'NOT_RUN')
            data = (path / 'sine.raw').read_bytes()
            self.assertEqual(len(data), 192000)
            self.assertEqual(data[:38400], bytes(38400))
            self.assertEqual(data[76800:], bytes(115200))
            values = [s[0] for s in struct.iter_unpack('<i', data)]
            self.assertGreater(max(values), 0)
            self.assertLessEqual(max(map(abs, values)) / 2**31, .0001)
            self.assertTrue(all(v % 256 == 0 for v in values))
            self.assertEqual((path / 'zero.raw').read_bytes(), bytes(192000))
            with self.assertRaises(FileExistsError):
                tool.prepare(path)

    def test_reference_mismatch_and_partial(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'ref.raw'
            path.write_bytes(struct.pack('<iiii', 123, -456, 10, 20))
            samples = [{'channel': 0, 'sample_s32': 123}, {'channel': 1, 'sample_s32': -456}]
            report = tool.compare(samples, path, 0)
            self.assertEqual(report['mismatched_slots'], 0)
            self.assertFalse(report['entire_reference_matched'])
            samples[1]['sample_s32'] = 456
            self.assertEqual(tool.compare(samples, path, 0)['mismatched_slots'], 1)

    def test_csv_roundtrip_and_validation(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'capture.csv'
            with path.open('w', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['time_s', 'bclk', 'ws', 'din'])
                writer.writerows(waveform([0, 0, 123, -456, 0, 0]))
            report = tool.analyze(path, Path(root) / 'result', 'din')
            self.assertEqual(report['complete_slots'], 4)
            self.assertFalse(any(report['errors'].values()))
            with self.assertRaises(ValueError):
                tool.analyze(path, Path(root) / 'other', 'din', path)
            path.write_text('time_s,bclk,ws,din\n0,0,0,0\n0,1,0,0\n')
            with self.assertRaises(ValueError):
                list(tool.states(path, 'din'))


if __name__ == '__main__':
    unittest.main()
