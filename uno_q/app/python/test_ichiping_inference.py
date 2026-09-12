"""Offline tests for the UNO Q inference preprocessing; no hardware is opened."""

import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ichiping_inference", HERE / "ichiping_inference.py")
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)


class InferenceRuntimeTests(unittest.TestCase):
    def test_stereo_extract_and_alignment_guard(self):
        raw = np.array([[100, 0], [-200, 0]], dtype="<i2").tobytes()
        np.testing.assert_allclose(
            runtime.left_s16le_to_float(raw), np.array([100, -200]) / 32768
        )
        for invalid in (b"", b"\0", b"\0\0"):
            with self.assertRaises(ValueError):
                runtime.left_s16le_to_float(invalid)

    def test_decimator_preserves_440_and_rejects_ultrasonic(self):
        t = np.arange(48_000) / 48_000
        x = np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 12_000 * t)
        y = runtime.decimate_48k_to_16k(x.astype(np.float32))
        spectrum = np.abs(np.fft.rfft(y))
        bin_440 = round(440 * len(y) / 16_000)
        alias_4k = round(4_000 * len(y) / 16_000)
        self.assertGreater(spectrum[bin_440], 100 * spectrum[alias_4k])

    def test_capture_conversion_returns_center_two_seconds(self):
        frames = np.zeros((48_000 * 6, 2), dtype="<i2")
        frames[:, 0] = 100
        converted = runtime.capture_to_model_audio(frames.tobytes())
        self.assertEqual(converted.shape, (32_000,))
        self.assertAlmostEqual(float(converted.mean()), 100 / 32768, places=5)

    def test_capture_health_guards_duration_slot_silence_and_clipping(self):
        rng = np.random.default_rng(3)
        valid = np.zeros((48_000 * 6, 2), dtype="<i2")
        valid[:, 0] = rng.integers(-2000, 2000, valid.shape[0], dtype=np.int16)
        health = runtime.capture_health(valid.tobytes())
        self.assertAlmostEqual(health["duration_seconds"], 6.0)
        for invalid in (
            np.zeros_like(valid),
            np.column_stack((valid[:, 0], valid[:, 0])).astype("<i2"),
            np.full_like(valid, (32767, 0)),
            valid[:48_000],
        ):
            with self.assertRaises(ValueError):
                runtime.capture_health(invalid.tobytes())

    def test_welch_matches_training_implementation(self):
        pc_training = HERE.parents[2] / "pc" / "training"
        sys.path.insert(0, str(pc_training))
        try:
            import features
            rng = np.random.default_rng(42)
            x = rng.normal(0, .1, 32_000).astype(np.float32)
            expected = features.samples_to_logmag_psd(x)
        finally:
            sys.path.remove(str(pc_training))
        np.testing.assert_allclose(runtime.logmag_psd(x), expected, rtol=2e-5, atol=2e-5)

    def test_normalization_and_softmax(self):
        rng = np.random.default_rng(7)
        x = rng.normal(0, .1, 32_000).astype(np.float32)
        feature = runtime.noise_diff_norm(x, np.zeros(1024, dtype=np.float32))
        self.assertAlmostEqual(float(feature.mean()), 0.0, places=5)
        self.assertAlmostEqual(float(feature.std()), 1.0, places=5)
        logits = np.zeros(32, dtype=np.float32)
        logits[21] = 4
        state, confidence = runtime.softmax_confidence(logits)
        self.assertEqual(state, 0b10101)
        self.assertGreater(confidence, .6)

    def test_baseline_average(self):
        rng = np.random.default_rng(9)
        frames = [rng.normal(0, .1, 32_000).astype(np.float32) for _ in range(2)]
        baseline = runtime.calibrate_baseline(frames)
        expected = (runtime.logmag_psd(frames[0]) + runtime.logmag_psd(frames[1])) / 2
        np.testing.assert_allclose(baseline, expected)


if __name__ == "__main__":
    unittest.main()
