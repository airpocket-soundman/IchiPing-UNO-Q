"""Host-side acceptance test for the model packaged with the UNO Q app."""

import json
from pathlib import Path
import sys
import unittest

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "pc" / "training"))

from dataset import IchiPingDataset
from ichiping_inference import OnnxPredictor, load_manifest

# Held-out UNO Q evaluation session (raw captures are not in Git; the test is
# skipped when the capture directory is absent).
UNO_Q_EVAL = ROOT / "pc" / "captures" / "uno_q_eval_20260912_gray_s32"


class PackagedModelTests(unittest.TestCase):
    def setUp(self):
        self.model_dir = HERE.parent / "models"
        self.manifest = load_manifest(self.model_dir / "manifest.json")
        self.predictor = OnnxPredictor(
            self.model_dir / self.manifest["model_file"],
            self.manifest["model_sha256"],
            self.manifest,
        )

    def test_manifest_pins_the_packaged_onnx(self):
        self.assertEqual(self.manifest["feature_mode"], "noise_diff_norm")
        self.assertEqual(self.manifest["sample_rate_hz"], 16000)
        prediction = self.predictor.predict_features(np.zeros(1024, dtype=np.float32))
        self.assertTrue(0 <= prediction.state_mask < 32)

    def test_runs_on_the_tracked_original_eval_subset(self):
        # The deployed model is trained on UNO Q recordings, so accuracy on the
        # original FRDM recordings is not asserted; the full path must run.
        dataset = IchiPingDataset(
            captures_dirs=[ROOT / "pc" / "captures" / "full_32_eval_v1"],
            feature_mode="noise_diff_norm",
        )
        self.assertEqual(len(dataset), 32)
        for item in dataset:
            prediction = self.predictor.predict_features(item["x"].numpy().reshape(1024))
            self.assertTrue(0 <= prediction.state_mask < 32)

    @unittest.skipUnless((UNO_Q_EVAL / "records.jsonl").is_file(), "UNO Q eval captures not present")
    def test_uno_q_held_out_accuracy(self):
        sys.path.insert(0, str(ROOT / "pc"))
        import uno_q_evaluate as ev

        records = ev.load_frames(UNO_Q_EVAL, "int16")
        import ichiping_inference as ii
        baseline = ii.calibrate_baseline([r["frame"] for r in records if r["group"] == "baseline"])
        tests = [r for r in records if r["group"] != "baseline"]
        correct = sum(self.predictor.predict_audio(r["frame"], baseline).state_mask == r["state"]
                      for r in tests)
        self.assertGreaterEqual(correct / len(tests), 0.85)


if __name__ == "__main__":
    unittest.main()
