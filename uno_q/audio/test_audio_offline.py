"""Offline regression tests; no audio hardware is opened."""
import importlib.util
import math
from pathlib import Path
import struct
import unittest
from unittest.mock import patch


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analyzer = load('analyzer', 'analyze-capture.py')
smoke = load('smoke', 'audio-smoke-test.py')
replay = load('replay', 'prepare-reviewed-replay.py')


class OfflineTests(unittest.TestCase):
    def test_reviewed_replay_peak_and_padding(self):
        source = b''.join(struct.pack('<hh', round(10 * math.sin(2*math.pi*440*i/48000)), 0)
                          for i in range(9600))
        data, report = replay.prepare(source)
        self.assertEqual(len(data), 192000)
        self.assertEqual(data[:38400], bytes(38400))
        self.assertEqual(data[76800:], bytes(115200))
        self.assertLessEqual(report['output_peak_fs_max'], .0001)

    def test_reviewed_replay_rejects_invalid_signal(self):
        with self.assertRaises(ValueError):
            replay.prepare(bytes(38400))
        with self.assertRaises(ValueError):
            replay.prepare(struct.pack('<hh', 200, 0) * 9600)

    def test_quiet_tone_and_silent_control(self):
        data = smoke.tone_data(.5, .0001)
        self.assertEqual(len(data), 96000)
        frames = list(struct.iter_unpack('<hh', data))
        self.assertTrue(all(left == right and abs(left) <= 3 for left, right in frames))
        self.assertEqual(smoke.tone_data(.5, 0), bytes(96000))

    def test_s24_container_and_level(self):
        data = smoke.tone_data(.5, .0001, 'S24_LE')
        self.assertEqual(len(data), 192000)
        frames = list(struct.iter_unpack('<ii', data))
        self.assertTrue(all(left == right and abs(left) <= 839 for left, right in frames))
        self.assertGreater(max(left for left, right in frames), 800)

    def test_native_s32_preserves_normalized_level(self):
        data = smoke.tone_data(.5, .0001, 'S32_LE')
        frames = list(struct.iter_unpack('<ii', data))
        self.assertEqual(len(data), 192000)
        self.assertTrue(all(left == right and left % 256 == 0 for left, right in frames))
        self.assertLessEqual(max(abs(left) for left, right in frames) / 2**31, .0001001)

    def test_silence_padding(self):
        data = smoke.tone_data(.5, .0001, 'S32_LE', .1, .1, .005)
        self.assertEqual(data[:4800 * 8], bytes(4800 * 8))
        self.assertEqual(data[-4800 * 8:], bytes(4800 * 8))
        self.assertNotEqual(data[4800 * 8:-4800 * 8], bytes(14400 * 8))

    def test_stereo_channel_separation(self):
        data = b''.join(struct.pack('<hh', round(1000 * math.sin(2 * math.pi * 440 * i / 48000)), 0)
                        for i in range(9600))
        report = analyzer.inspect(data, channels=2)
        self.assertEqual(report['frames'], 9600)
        self.assertGreater(report['channels'][0]['windows'][0]['tone_440_power_fraction'], .999)
        self.assertEqual(report['channels'][1]['rms_fs'], 0)

    def test_partial_frames_rejected(self):
        for data in (b'', b'\x00', b'\x00\x00'):
            with self.assertRaises(ValueError):
                analyzer.inspect(data, channels=2)

    def test_duration_and_amplitude_guard(self):
        with patch.object(smoke, 'run') as run:
            for duration, amplitude in ((.501, .0001), (0, .0001), (.5, .002), (.5, -.1)):
                with self.assertRaises(ValueError):
                    smoke.speaker('unused', duration, amplitude)
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
