from pathlib import Path
import tempfile
import unittest

import numpy as np

import ichiping_cli


class IchiPingCliTests(unittest.TestCase):
    def test_create_baseline_writes_finite_1024_vector(self):
        rng = np.random.default_rng(9)
        stereo = np.zeros((48_000 * 6, 2), dtype="<i2")
        stereo[:, 0] = rng.integers(-2000, 2000, stereo.shape[0], dtype=np.int16)
        with tempfile.TemporaryDirectory() as root:
            captures = []
            for index in range(3):
                capture = Path(root) / f"closed-{index}.raw"
                capture.write_bytes(stereo.tobytes())
                captures.append(capture)
            output = Path(root) / "baseline.npy"
            report = ichiping_cli.create_baseline(captures, output)
            baseline = np.load(output, allow_pickle=False)
        self.assertEqual(report["count"], 3)
        self.assertEqual(baseline.shape, (1024,))
        self.assertTrue(np.isfinite(baseline).all())


if __name__ == "__main__":
    unittest.main()
