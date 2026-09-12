import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

import numpy as np

from audio_runtime import AudioCapture
from ichiping_inference import Prediction


HERE = Path(__file__).resolve().parent


class FakeBridge:
    calls = []
    physical_state = 5
    servo_state = 5

    @classmethod
    def provide(cls, *_args):
        return None

    @classmethod
    def call(cls, name, *args):
        cls.calls.append((name, *args))
        if name == "get_physical_state":
            return cls.physical_state
        if name == "get_servo_state":
            return cls.servo_state
        if name == "show_prediction":
            return args[-1]
        return 0


class FakeApp:
    @staticmethod
    def run(**_kwargs):
        return None


class FakeLogger:
    def __init__(self, _name):
        pass

    def info(self, _message):
        pass

    def error(self, _message):
        pass


def load_main():
    arduino = types.ModuleType("arduino")
    app_utils = types.ModuleType("arduino.app_utils")
    app_utils.App = FakeApp
    app_utils.Bridge = FakeBridge
    app_utils.Logger = FakeLogger
    arduino.app_utils = app_utils
    sys.modules["arduino"] = arduino
    sys.modules["arduino.app_utils"] = app_utils
    spec = importlib.util.spec_from_file_location("ichiping_main_test", HERE / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeBroker:
    ready = True

    def __init__(self, _path):
        pass

    def capture_white_noise(self, requested_state):
        rng = np.random.default_rng(11)
        stereo = np.zeros((48_000 * 6, 2), dtype="<i2")
        stereo[:, 0] = rng.integers(-2000, 2000, stereo.shape[0], dtype=np.int16)
        return AudioCapture("a" * 32, stereo.tobytes(), {"requested_state": requested_state})


class FakePredictor:
    def predict_audio(self, _frame, _baseline):
        logits = np.zeros(32, dtype=np.float32)
        logits[7] = 5
        return Prediction(7, 0.9, logits)


class MainRuntimeTests(unittest.TestCase):
    def setUp(self):
        FakeBridge.calls = []
        FakeBridge.physical_state = 5
        FakeBridge.servo_state = 5
        self.main = load_main()
        self.main._model_predictor = FakePredictor()
        self.main._model_manifest = {"model_sha256": "a" * 64}
        self.main._baseline = np.zeros(1024, dtype=np.float32)

    def _eval(self, tmp, **command):
        import json
        (tmp / "command.json").write_text(json.dumps(command), encoding="utf-8")
        FakeBridge.calls = []
        self.main.process_eval_command()
        self.assertFalse((tmp / "command.json").exists())
        return json.loads((tmp / f"result-{command['id']}.json").read_text(encoding="utf-8"))

    def test_eval_arm_set_state_moves_only_changed_channels_and_disarm(self):
        import tempfile
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            self.main.EVAL_DIR = tmp
            refused = self._eval(tmp, id="c0", op="set_state", state=3)
            self.assertEqual(refused["status"], "error")
            armed = self._eval(tmp, id="c1", op="arm")
            self.assertEqual(armed["status"], "ok")
            self.assertIn(("set_servo_automation", 0), FakeBridge.calls)
            self.assertIn(("set_servo_armed", 1, 5), FakeBridge.calls)
            moves = [c for c in FakeBridge.calls if c[0] == "move_servo_deg"]
            self.assertEqual(moves, [("move_servo_deg", ch, 180) for ch in (4, 3, 2, 1, 0)])
            first = self._eval(tmp, id="c2", op="set_state", state=0b00101)
            self.assertEqual(first["servo_state"], 0b00101)
            self.assertEqual([c for c in FakeBridge.calls if c[0] == "move_servo_deg"],
                             [("move_servo_deg", 0, 0), ("move_servo_deg", 2, 0)])
            second = self._eval(tmp, id="c3", op="set_state", state=0b10001)
            self.assertEqual([c for c in FakeBridge.calls if c[0] == "move_servo_deg"],
                             [("move_servo_deg", 2, 180), ("move_servo_deg", 4, 0)])
            self.assertEqual(second["servo_state"], 0b10001)
            released = self._eval(tmp, id="c4", op="disarm")
            self.assertEqual(released["status"], "ok")
            self.assertIn(("set_servo_armed", 0, 0), FakeBridge.calls)
            self.assertIsNone(released["servo_state"])

    def test_eval_follow_switches_and_baseline_ops(self):
        import tempfile
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            self.main.EVAL_DIR = tmp
            follow = self._eval(tmp, id="f1", op="follow_switches")
            self.assertEqual(follow["status"], "ok")
            self.assertIn(("set_servo_armed", 1, 5), FakeBridge.calls)
            self.assertIn(("set_servo_automation", 1), FakeBridge.calls)
            FakeBridge.servo_state = 0
            saved = {}
            with mock.patch.object(self.main, "FileAudioBroker", FakeBroker), \
                    mock.patch.object(self.main, "initialize_runtime", lambda: None), \
                    mock.patch.object(self.main, "_worker_playback_rms", lambda: 0.0088), \
                    mock.patch.object(self.main, "save_baseline", lambda *a, **k: saved.update(k)), \
                    mock.patch.object(self.main, "load_baseline",
                                      lambda *a, **k: (np.zeros(1024, np.float32), {"capture_count": 3})):
                base = self._eval(tmp, id="b1", op="calibrate_baseline")
            self.assertEqual(base["status"], "ok", base)
            self.assertEqual(base["baseline_capture_count"], 3)
            self.assertEqual(len(saved["capture_ids"]), 3)
            self.assertEqual(FakeBridge.calls[-2], ("set_inference_busy", 0))

    def test_exec_capture_predict_display_and_busy_cleanup(self):
        with mock.patch.object(self.main, "FileAudioBroker", FakeBroker):
            self.main.process_inference_request(5)
        names = [call[0] for call in FakeBridge.calls]
        self.assertIn(("set_inference_busy", 1), FakeBridge.calls)
        self.assertIn("show_prediction", names)
        self.assertEqual(FakeBridge.calls[-1], ("set_inference_busy", 0))

    def test_state_change_discards_stale_prediction(self):
        FakeBridge.servo_state = 6
        with mock.patch.object(self.main, "FileAudioBroker", FakeBroker):
            self.main.process_inference_request(5)
        names = [call[0] for call in FakeBridge.calls]
        self.assertNotIn("show_prediction", names)
        self.assertIn(("show_runtime_status", 8), FakeBridge.calls)
        self.assertEqual(FakeBridge.calls[-1], ("set_inference_busy", 0))


if __name__ == "__main__":
    unittest.main()
