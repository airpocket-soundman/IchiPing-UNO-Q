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
calibration = load('calibration', 'analyze-white-noise-calibration.py')


class OfflineTests(unittest.TestCase):
    def test_reviewed_replay_peak_and_padding(self):
        source = b''.join(struct.pack('<hh', round(10 * math.sin(2*math.pi*440*i/48000)), 0)
                          for i in range(9600))
        data, report = replay.prepare(source)
        self.assertEqual(len(data), 192000)
        self.assertEqual(data[:38400], bytes(38400))
        self.assertEqual(data[76800:], bytes(115200))
        self.assertLessEqual(report['output_peak_fs_max'], .006)

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
            for duration, amplitude in ((.501, .0001), (0, .0001), (.5, .013), (.5, -.1)):
                with self.assertRaises(ValueError):
                    smoke.speaker('unused', duration, amplitude)
            run.assert_not_called()

    def test_external_clock_silence_guard(self):
        data = smoke.clock_silence_data(6.5)
        self.assertEqual(len(data), round(smoke.RATE * 6.5) * 8)
        self.assertEqual(data, bytes(len(data)))
        for duration in (0, 6.501):
            with self.assertRaises(ValueError):
                smoke.clock_silence_data(duration)

    def test_white_noise_is_bounded_deterministic_native_s32(self):
        data = smoke.white_noise_data(5, .003, 123)
        self.assertEqual(len(data), round(smoke.RATE * 6.5) * 8)
        self.assertEqual(data[:round(smoke.RATE * .5) * 8],
                         bytes(round(smoke.RATE * .5) * 8))
        self.assertEqual(data[-round(smoke.RATE) * 8:],
                         bytes(round(smoke.RATE) * 8))
        self.assertEqual(data, smoke.white_noise_data(5, .003, 123))
        active = data[round(smoke.RATE * .5) * 8:-round(smoke.RATE) * 8]
        frames = list(struct.iter_unpack('<ii', active))
        left = [a / 2**31 for a, b in frames]
        self.assertTrue(all(a == b and a % 256 == 0 for a, b in frames))
        rms = math.sqrt(sum(value * value for value in left) / len(left))
        self.assertAlmostEqual(rms, .003, delta=.00003)
        self.assertLess(max(map(abs, left)), .006)

    def test_white_noise_guards(self):
        for duration, amplitude in ((0, .003), (5.001, .003), (5, 0), (5, .101)):
            with self.assertRaises(ValueError):
                smoke.white_noise_data(duration, amplitude, 1)

    def test_calibration_analysis_uses_center_crop_and_bounded_steps(self):
        rate = 48000
        frames = []
        for index in range(rate * 6):
            value = round(32767 * .05 * math.sin(2 * math.pi * 440 * index / rate))
            frames.append(struct.pack('<hh', value, 0))
        report = calibration.analyze(b''.join(frames), .003)
        self.assertEqual(report['status'], 'below-target')
        self.assertEqual(report['recommended_next_playback_rms_fs'], .006)
        self.assertAlmostEqual(report['capture_rms_fs'], .05 / math.sqrt(2), places=3)

    def test_prbs16k_is_original_2s_band_limited_native_s32(self):
        import numpy as np
        data = smoke.prbs16k_data(.009, 7)
        rate = smoke.RATE
        self.assertEqual(len(data), round(rate * 3.5) * 8)
        self.assertEqual(data[:round(rate * .5) * 8], bytes(round(rate * .5) * 8))
        self.assertEqual(data[-round(rate) * 8:], bytes(round(rate) * 8))
        self.assertEqual(data, smoke.prbs16k_data(.009, 7))
        frames = np.frombuffer(data, '<i4').reshape(-1, 2)
        self.assertTrue(np.all(frames[:, 0] == frames[:, 1]))
        self.assertTrue(np.all(frames[:, 0] % 256 == 0))
        active = frames[round(rate * .5):-round(rate), 0] / 2**31
        self.assertEqual(active.size, 2 * rate)
        power = np.abs(np.fft.rfft(active)) ** 2
        freqs = np.fft.rfftfreq(active.size, 1 / rate)
        self.assertLess(power[freqs > 8500].sum() / power.sum(), .01)
        self.assertAlmostEqual(float(np.sqrt(np.mean(active ** 2))), .009, delta=.0012)
        # Band-limited ±1 sequences overshoot to roughly 2x the source level.
        self.assertLess(float(np.abs(active).max()), .009 * 2.3)

    def test_chime_is_three_quiet_beeps_in_prbs_timing(self):
        import numpy as np
        data = smoke.chime_data()
        rate = smoke.RATE
        self.assertEqual(len(data), round(rate * 3.5) * 8)
        left = np.frombuffer(data, '<i4').reshape(-1, 2)[:, 0] / 2**31
        self.assertLessEqual(np.abs(left).max(), smoke.CHIME_PEAK + 1e-6)
        window = round(rate * .01)  # 10 ms envelope, ignores sine zero crossings
        envelope = np.sqrt(np.convolve(left ** 2, np.ones(window) / window, mode='same'))
        active = envelope > smoke.CHIME_PEAK * .3
        edges = np.flatnonzero(np.diff(active.astype(int)) == 1)
        self.assertEqual(len(edges), 3)
        self.assertFalse(active[:round(rate * .5)].any())
        self.assertFalse(active[round(rate * 2.5):].any())

    def test_safe_audio_workdir_is_defined_before_use(self):
        script = Path(__file__).with_name('safe-audio-test.sh').read_text(encoding='utf-8')
        self.assertIn('\twork=/var/tmp\n', script)
        self.assertIn('\twork=/var/tmp/ichiping-audio-$(id -un)\n', script)
        definition = script.index('export ICHIPING_AUDIO_WORKDIR="$work"')
        self.assertLess(definition, script.index('"$work"/ichiping-'))
        self.assertNotIn('work="$work"', script)

    def test_prbs16k_batch_layout(self):
        rate = smoke.RATE
        single = smoke.prbs16k_data(.009, 7)
        batch = smoke.prbs16k_data(.009, 7, repeats=3, gap=.3)
        self.assertEqual(len(batch), round(rate * smoke.prbs16k_seconds(3, .3)) * 8)
        lead, active, gap = round(rate * .5) * 8, 2 * rate * 8, round(rate * .3) * 8
        frame = single[lead:lead + active]
        for index in range(3):
            start = lead + index * (active + gap)
            self.assertEqual(batch[start:start + active], frame)
            if index < 2:
                self.assertEqual(batch[start + active:start + active + gap], bytes(gap))
        with self.assertRaises(ValueError):
            smoke.prbs16k_data(.009, 7, repeats=101)
        with self.assertRaises(ValueError):
            smoke.prbs16k_data(.009, 7, repeats=2, gap=.05)

    def test_batch_capture_splits_into_aligned_frames(self):
        import numpy as np
        rng = np.random.default_rng(4)
        source = np.asarray(smoke.prbs_source(5), dtype=np.float64)
        up = np.repeat(source, 3) * .003
        pitch48 = round((2.0 + .3) * 48000)
        start = 18003
        capture = rng.normal(0, .00002, start + 3 * pitch48 + 48000)
        for index in range(3):
            capture[start + index * pitch48:start + index * pitch48 + up.size] += up * (1 + .1 * index)
        left = np.round(capture * 32768).astype('<i2')
        raw = np.stack([left, np.zeros_like(left)], axis=1).tobytes()
        frames = calibration.align_prbs_frames(raw, 5, 3, .3)
        self.assertEqual(len(frames), 3)
        for index, (frame, info) in enumerate(frames):
            self.assertEqual(frame.size, 32000)
            self.assertLessEqual(abs(info['onset_sample_16k'] - (start + index * pitch48) // 3), 2)
            self.assertLessEqual(abs(info['pitch_error_samples']), 2)
        rms = [float(np.sqrt(np.mean(f.astype(float) ** 2))) for f, _ in frames]
        self.assertLess(rms[0], rms[1])
        self.assertLess(rms[1], rms[2])
        with self.assertRaises(ValueError):
            calibration.align_prbs_frames(raw, 5, 5, .3)

    def test_app_prbs_alignment_matches_analyzer(self):
        import numpy as np
        import ichiping_inference as ii
        self.assertTrue(np.array_equal(ii.prbs_source(20260912),
                                       np.asarray(smoke.prbs_source(20260912), dtype=float)))
        rng = np.random.default_rng(8)
        up = np.repeat(ii.prbs_source(), 3) * .004
        capture = rng.normal(0, .00002, 48000 * 3)
        capture[17004:17004 + up.size] += up
        word = np.round(capture * 2**23).astype(np.int64) << 8
        raw = np.stack([word, np.zeros_like(word)], axis=1).astype('<i4').tobytes()
        app = ii.align_prbs_capture(raw, 'S32_LE')
        ref, _ = calibration.align_prbs_frame(raw, 20260912, 'S32_LE', 'int16')
        np.testing.assert_array_equal(app, ref)
        health = ii.capture_health(raw, 'S32_LE', (2.5, 3.5))
        self.assertAlmostEqual(health['duration_seconds'], 3.0)

    def test_silence_pcm_matches_prbs_timing_and_is_zero(self):
        for repeats, gap in ((1, .3), (4, .3)):
            data = smoke.silence_data(repeats, gap)
            self.assertEqual(len(data), len(smoke.prbs16k_data(.009, 1, repeats, gap)))
            self.assertFalse(any(data))
        with self.assertRaises(ValueError):
            smoke.silence_data(0)

    def test_silent_capture_splits_on_fixed_grid(self):
        import numpy as np
        rng = np.random.default_rng(6)
        pitch48 = round(2.3 * 48000)
        capture = rng.normal(0, .0002, round(48000 * (0.38 + 3 * 2.3 + .3)))
        left = np.round(capture * 32768).astype('<i2')
        raw = np.stack([left, np.zeros_like(left)], axis=1).tobytes()
        frames = calibration.split_fixed_frames(raw, 3, .3)
        self.assertEqual([f.size for f, _ in frames], [32000] * 3)
        self.assertEqual([i['onset_sample_16k'] for _, i in frames],
                         [6080 + k * (pitch48 // 3) for k in range(3)])
        with self.assertRaises(ValueError):
            calibration.split_fixed_frames(raw, 4, .3)

    def test_prbs16k_guards(self):
        for amplitude in (0, 1, -.1):
            with self.assertRaises(ValueError):
                smoke.prbs16k_data(amplitude, 1)
        with self.assertRaises(ValueError):
            smoke.prbs16k_data(.9, 1)  # clips after band limiting

    def test_prbs_analysis_aligns_onset_and_reports_snr(self):
        import numpy as np
        rng = np.random.default_rng(3)
        source = np.asarray(smoke.prbs_source(5), dtype=np.float64)
        up = np.repeat(source, 3) * .003  # x16 original gain -> 4.8%FS
        capture = rng.normal(0, .00002, 48000 * 3)
        start = 21003
        capture[start:start + up.size] += up
        left = np.round(capture * 32768).astype('<i2')
        raw = np.stack([left, np.zeros_like(left)], axis=1).tobytes()
        report, frame = calibration.analyze_prbs(raw, .01, 5)
        self.assertEqual(frame.size, 32000)
        self.assertLessEqual(abs(report['onset_sample_16k'] - start // 3), 2)
        self.assertGreater(report['alignment_correlation'], .8)
        self.assertGreater(report['snr_db'], 30)
        self.assertEqual(report['status'], 'below-target')
        self.assertAlmostEqual(report['recommended_next_prbs_amplitude_fs'], .02)
        # 0.048 before decimation; the 3:1 FIR removes the unfiltered 7-8 kHz
        # top of this sample-and-hold test signal (~0.85x RMS).
        self.assertAlmostEqual(report['capture_rms_fs'], .041, delta=.003)
        self.assertEqual(report['clipped_samples'], 0)

    def test_s32_int16_mode_is_bit_exact_original_shift12(self):
        import numpy as np
        import ichiping_inference as ii
        rng = np.random.default_rng(9)
        v24 = rng.integers(-2**23, 2**23, 5000)
        v24[:4] = (2**23 - 1, -2**23, 2**19, -2**19 - 1)  # clip cases
        word = (v24 << 8).astype(np.int64)
        raw = np.stack([word, np.zeros_like(word)], axis=1).astype('<i4').tobytes()
        x = ii.left_capture_to_float(raw, 'S32_LE')
        got = np.round(ii.to_original_scale(x, 'int16').astype(np.float64) * 32768).astype(np.int64)
        expected = np.clip(word >> 12, -32768, 32767)  # FRDM mic_word_to_int16
        np.testing.assert_array_equal(got, expected)
        exact = ii.to_original_scale(x, 'float').astype(np.float64) * 32768
        inside = np.abs(expected) < 32767
        self.assertTrue(np.all(np.abs(exact[inside] - expected[inside]) < 1))
        self.assertTrue(np.any(exact[inside] != expected[inside]))  # keeps sub-LSB bits

    def test_s16_capture_scales_by_16_on_original_grid(self):
        import numpy as np
        import ichiping_inference as ii
        s16 = np.array([0, 1, -1, 2047, -2048, 2048, 30000], dtype=np.int64)
        raw = np.stack([s16, np.zeros_like(s16)], axis=1).astype('<i2').tobytes()
        got = ii.to_original_scale(ii.left_capture_to_float(raw, 'S16_LE'), 'int16')
        np.testing.assert_array_equal(np.round(got.astype(np.float64) * 32768),
                                      np.clip(s16 * 16, -32768, 32767))


if __name__ == '__main__':
    unittest.main()
