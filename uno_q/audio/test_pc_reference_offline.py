"""Mocked/offline only: no winsound, SSH, I2S or actual subprocess is invoked."""
import importlib.util
import json
import math
from pathlib import Path
import queue
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

spec = importlib.util.spec_from_file_location('pc_reference', Path(__file__).with_name('pc-reference-test.py'))
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)


class PCReferenceTests(unittest.TestCase):
    def test_timing_margins_and_truncation(self):
        def signal(lead, tone, tail):
            return (bytes(round(lead*48000)*4) +
                    b''.join(struct.pack('<hh', round(100*math.sin(2*math.pi*440*i/48000)), 0)
                             for i in range(round(tone*48000))) + bytes(round(tail*48000)*4))
        self.assertIn('has margins', pc.timing_check(signal(.05, .1, .1))['status'])
        self.assertIn('truncated', pc.timing_check(signal(0, .1, .1))['status'])
        self.assertIn('NOT established', pc.timing_check(bytes(48000))['status'])

    def test_reference_limits(self):
        data = pc.reference_pcm()
        self.assertEqual(len(data), 4800 * 4)
        frames = list(struct.iter_unpack('<hh', data))
        self.assertTrue(all(left == right and abs(left) <= 3 for left, right in frames))
        self.assertEqual(frames[0], (0, 0))
        self.assertEqual(frames[-1], (0, 0))

    def test_prepare_never_connects_or_plays(self):
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / 'run'
            with patch.object(sys, 'argv', ['pc-reference-test.py', '--output', str(output)]), \
                 patch.object(pc, 'execute') as execute, patch.object(pc, 'play_child') as play:
                pc.main()
                execute.assert_not_called()
                play.assert_not_called()
            report = json.loads((output / 'report.json').read_text())
            self.assertIn('NO sound', report['status'])
            with wave.open(str(output / 'reference.wav'), 'rb') as wav:
                self.assertEqual(wav.getnframes(), 4800)
                self.assertEqual(wav.getframerate(), 48000)

    def test_exact_run_handshake_required(self):
        events = queue.Queue()
        events.put('ICHIPING_CAPTURE_READY:other-run')
        events.put(None)
        with self.assertRaises(RuntimeError):
            pc.wait_ready(events, 'expected')
        events.put('ICHIPING_CAPTURE_READY:expected')
        pc.wait_ready(events, 'expected')

    def test_no_ready_times_out(self):
        with self.assertRaises(TimeoutError):
            pc.wait_ready(queue.Queue(), 'run', timeout=.001)

    def test_player_clears_audio_on_error(self):
        from unittest.mock import MagicMock
        fake = MagicMock()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reference.wav'
            pc.write_wav(path, pc.reference_pcm(), 2)
            with patch.dict(sys.modules, {'winsound': fake}), \
                 patch.object(pc.time, 'sleep', side_effect=RuntimeError('simulated')):
                with self.assertRaises(RuntimeError):
                    pc.play_child(path)
            fake.PlaySound.assert_called_with(None, 0)


if __name__ == '__main__':
    unittest.main()
