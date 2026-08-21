"""IchiPing UNO Q bring-up controller.

This is intentionally a transport and UI smoke test, not an acoustic model.
The deterministic sequence proves the Linux-to-MCU Router Bridge and the
onboard 8x13 LED Matrix before audio hardware is selected.
"""

import time

from arduino.app_utils import App, Bridge, Logger


logger = Logger("ichiping-uno-q")
_smoke_test_complete = False


def on_runtime_status(stage: str, hardware_status: int) -> None:
    logger.info(
        f"MCU stage={stage} matrix={bool(hardware_status & 0x01)} "
        f"pca9685={bool(hardware_status & 0x02)} rain={bool(hardware_status & 0x04)}"
    )


def on_infer_request(physical_state: int) -> None:
    # Bring-up loopback only. Replace this call with model inference once the
    # UNO Q audio path and exported IchiPing model have been integrated.
    state_mask = int(physical_state) & 0x1F
    logger.info(f"EXEC requested state=0b{state_mask:05b}; returning loopback result")
    Bridge.call("show_prediction", state_mask, 100)


Bridge.provide("on_runtime_status", on_runtime_status)
Bridge.provide("on_infer_request", on_infer_request)


def loop() -> None:
    global _smoke_test_complete
    if not _smoke_test_complete:
        time.sleep(2)
        hardware_status = int(Bridge.call("get_hardware_status"))
        physical_state = int(Bridge.call("get_physical_state")) & 0x1F
        logger.info(
            f"bring-up status=0x{hardware_status:02x} physical=0b{physical_state:05b}"
        )
        Bridge.call("run_matrix_self_test")
        for state_mask in (0x00, 0x01, 0x03, 0x07, 0x0F, 0x1F, 0x15):
            Bridge.call("show_prediction", state_mask, 87)
            time.sleep(0.35)
        logger.info("smoke test PASS: bridge calls and matrix sequence completed")
        _smoke_test_complete = True
    time.sleep(5)


App.run(user_loop=loop)
