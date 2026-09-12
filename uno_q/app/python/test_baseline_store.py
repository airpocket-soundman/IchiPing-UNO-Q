from pathlib import Path
import tempfile
import unittest

import numpy as np

from baseline_store import load_baseline, save_baseline


class BaselineStoreTests(unittest.TestCase):
    def test_roundtrip_is_model_bound_and_requires_three_captures(self):
        baseline = np.linspace(-20, 20, 1024, dtype=np.float32)
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            save_baseline(
                directory,
                baseline,
                model_sha256="a" * 64,
                capture_ids=["1", "2", "3"],
                playback_rms_fs=0.003,
            )
            loaded, metadata = load_baseline(directory, model_sha256="a" * 64)
            np.testing.assert_array_equal(loaded, baseline)
            self.assertEqual(metadata["capture_count"], 3)
            with self.assertRaises(ValueError):
                load_baseline(directory, model_sha256="b" * 64)
            with self.assertRaises(ValueError):
                save_baseline(
                    directory,
                    baseline,
                    model_sha256="a" * 64,
                    capture_ids=["1"],
                    playback_rms_fs=0.003,
                )


if __name__ == "__main__":
    unittest.main()
