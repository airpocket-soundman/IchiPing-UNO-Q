from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SKETCH = HERE.parent / "sketch"


class OriginalUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.display = (SKETCH / "ili9341_display.cpp").read_text(encoding="utf-8")
        cls.sketch = (SKETCH / "sketch.ino").read_text(encoding="utf-8")
        cls.main = (HERE / "main.py").read_text(encoding="utf-8")

    def test_original_landscape_ui_labels_order_and_verdicts(self):
        self.assertIn("{0xE8}", self.display)
        self.assertIn('"UNO Ping infer"', self.display)
        self.assertIn('"inf"', self.display)
        self.assertIn('"act"', self.display)
        self.assertIn("order[5] = {2, 4, 1, 3, 0}", self.display)
        for message in ("Complete Success", "Conditional Success", "Failure"):
            self.assertIn(message, self.display)

    def test_original_colors_and_observability_are_present(self):
        for color in ("0x000F", "0x001F", "0xFD20", "0x8410", "0x7A80"):
            self.assertIn(color, self.display)
        self.assertIn("bit == 0 || bit == 3", self.display)

    def test_original_switch_polarity_and_result_invalidation(self):
        self.assertIn("digitalRead(kStatePins[i]) == HIGH", self.sketch)
        self.assertIn("capturedPhysicalState & 0x1F) != servoState", self.sketch)
        self.assertNotIn("kPredictionHoldMs", self.sketch)

    def test_no_fake_startup_or_loopback_prediction_is_displayed(self):
        self.assertNotIn('Bridge.call("run_display_self_test")', self.main)
        self.assertNotIn('Bridge.call("show_prediction", requested_state', self.main)
        self.assertIn('Bridge.call("show_runtime_status", 1)', self.main)
        self.assertIn("privileged audio worker is not configured", self.main)

    def test_servo_automation_is_explicitly_gated(self):
        self.assertIn("bool servoAutomationEnabled = false", self.sketch)
        self.assertIn("bool servoControlsArmed = false", self.sketch)
        self.assertIn('Bridge.provide("set_servo_armed"', self.sketch)
        self.assertIn('Bridge.provide("set_servo_automation"', self.sketch)
        self.assertIn('Bridge.provide("get_servo_state"', self.sketch)
        self.assertIn("bool servoStateKnown = false", self.sketch)
        self.assertIn("for (int channel = 4; channel >= 0; --channel)", self.sketch)
        self.assertIn("disableAllPca9685Channels", self.sketch)

    def test_inference_result_is_state_bound_and_busy_gated(self):
        self.assertIn("capturedPhysicalState", self.sketch)
        self.assertIn("!= physicalState", self.sketch)
        self.assertIn('Bridge.provide("set_inference_busy"', self.sketch)
        self.assertIn('Bridge.call("set_inference_busy", 1)', self.main)
        self.assertIn('Bridge.call("set_inference_busy", 0)', self.main)

    def test_onboard_matrix_is_not_used(self):
        self.assertNotIn("Arduino_LED_Matrix", self.sketch)
        self.assertNotIn("set_audio_test_marker", self.sketch)

    def test_rain_detection_is_not_implemented(self):
        self.assertNotIn("kRainPin", self.sketch)
        self.assertNotIn("digitalRead(D9)", self.sketch)
        self.assertNotIn("rain=", self.main)


if __name__ == "__main__":
    unittest.main()
