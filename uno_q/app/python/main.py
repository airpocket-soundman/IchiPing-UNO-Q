"""IchiPing UNO Q controller: safe capture, ONNX inference, and original TFT UI."""

from __future__ import annotations

import json
import os
from pathlib import Path
import time

from arduino.app_utils import App, Bridge, Logger

from audio_runtime import AudioRuntimeError, FileAudioBroker
from baseline_store import load_baseline, save_baseline
from ichiping_inference import (
    OnnxPredictor,
    align_prbs_capture,
    calibrate_baseline,
    capture_health,
    capture_to_model_audio,
    load_manifest,
)
from request_mailbox import RequestMailbox


logger = Logger("ichiping-uno-q")
APP_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = APP_DIR / "models"
RUNTIME_DIR = APP_DIR / "runtime"
AUDIO_SPOOL = RUNTIME_DIR / "audio"
BASELINE_DIR = RUNTIME_DIR / "baseline"
EVAL_DIR = RUNTIME_DIR / "eval"
MODEL_RETRY_SECONDS = 30.0
BASELINE_CAPTURE_COUNT = 3

_startup_complete = False
_last_switch_states = None
_inference_requests = RequestMailbox()
_model_predictor = None
_model_manifest = None
_baseline = None
_baseline_metadata = None
_next_model_retry = 0.0
_request_sequence = 0
_eval_servo_state = None  # evaluation-owned endpoint state, None = not armed/unknown


def initialize_runtime() -> None:
    """Load model and matching baseline, retrying recoverable startup failures."""
    global _model_predictor, _model_manifest, _baseline, _baseline_metadata
    global _next_model_retry
    if _model_predictor is not None or time.monotonic() < _next_model_retry:
        return
    _next_model_retry = time.monotonic() + MODEL_RETRY_SECONDS
    try:
        manifest = load_manifest(MODEL_DIR / "manifest.json")
        predictor = OnnxPredictor(
            MODEL_DIR / manifest["model_file"], manifest["model_sha256"], manifest
        )
        _model_manifest = manifest
        _model_predictor = predictor
        try:
            _baseline, _baseline_metadata = load_baseline(
                BASELINE_DIR, model_sha256=manifest["model_sha256"]
            )
            baseline_mode = f"ready count={_baseline_metadata['capture_count']}"
        except FileNotFoundError:
            baseline_mode = "missing"
        except Exception as error:
            _baseline = None
            _baseline_metadata = None
            baseline_mode = f"invalid error={error}"
        logger.info(
            f"MODEL ready file={manifest['model_file']} "
            f"baseline={baseline_mode} audio_worker={FileAudioBroker(AUDIO_SPOOL).ready}"
        )
    except Exception as error:
        _model_predictor = None
        _model_manifest = None
        logger.error(f"MODEL unavailable retry_s={MODEL_RETRY_SECONDS:g} error={error}")


def on_runtime_status(stage: str, hardware_status: int) -> None:
    logger.info(
        f"MCU stage={stage} ili9341_init_sent={bool(hardware_status & 0x01)} "
        f"pca9685={bool(hardware_status & 0x02)} "
        f"servo_armed={bool(hardware_status & 0x10)} "
        f"servo_fault={bool(hardware_status & 0x20)} "
        f"inference_busy={bool(hardware_status & 0x40)} "
        f"servo_state_known={bool(hardware_status & 0x80)}"
    )


def on_infer_request(physical_state: int) -> None:
    state_mask = int(physical_state) & 0x1F
    accepted = _inference_requests.submit(state_mask)
    logger.info(
        f"EXEC queued physical=0b{state_mask:05b} "
        f"policy={'new' if accepted else 'coalesced-newest'}"
    )


Bridge.provide("on_runtime_status", on_runtime_status)
Bridge.provide("on_infer_request", on_infer_request)


def _worker_playback_rms() -> float:
    status = json.loads((AUDIO_SPOOL / "worker-ready.json").read_text(encoding="utf-8"))
    value = float(status["playback_rms_fs"])
    if not 0 < value <= 0.10:
        raise ValueError("invalid worker playback RMS")
    return value


def _worker_config() -> dict:
    """Excitation/format published by the host worker; {} means legacy white noise."""
    try:
        return json.loads((AUDIO_SPOOL / "worker-ready.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _capture_checked(broker: FileAudioBroker, state: int) -> tuple[str, object, dict]:
    config = _worker_config()
    if config.get("excitation") == "prbs16k":
        # Original-collector excitation: 2 s PRBS, frame aligned to the onset
        # and scaled x16 like the training dataset (see ichiping_inference).
        capture_format = config.get("capture_format", "S16_LE")
        capture = broker.capture_prbs16k(state)
        health = capture_health(capture.raw, capture_format, (2.5, 3.5))
        frame = align_prbs_capture(capture.raw, capture_format)
    else:
        capture = broker.capture_white_noise(state)
        health = capture_health(capture.raw)
        frame = capture_to_model_audio(capture.raw)
    (AUDIO_SPOOL / "captures" / f"{capture.request_id}.raw").unlink(missing_ok=True)
    logger.info(
        f"CAPTURE id={capture.request_id} bytes={len(capture.raw)} "
        f"rms={health['left_rms_fs']:.6f} peak={health['left_peak_fs']:.6f}"
    )
    return capture.request_id, frame, health


def _calibrate_live_baseline(broker: FileAudioBroker) -> None:
    global _baseline, _baseline_metadata
    servo_state = int(Bridge.call("get_servo_state"))
    if servo_state < 0:
        Bridge.call("show_runtime_status", 9)
        raise ValueError("baseline calibration requires a synchronized servo state")
    if servo_state & 0x1F:
        Bridge.call("show_runtime_status", 2)
        raise ValueError("baseline calibration requires all five states closed")
    Bridge.call("show_runtime_status", 3)
    capture_ids = []
    frames = []
    for _ in range(BASELINE_CAPTURE_COUNT):
        capture_id, frame, _health = _capture_checked(broker, 0)
        if int(Bridge.call("get_servo_state")) != 0:
            raise RuntimeError("state changed during baseline calibration")
        capture_ids.append(capture_id)
        frames.append(frame)
    baseline = calibrate_baseline(frames)
    playback_rms = _worker_playback_rms()
    save_baseline(
        BASELINE_DIR,
        baseline,
        model_sha256=_model_manifest["model_sha256"],
        capture_ids=capture_ids,
        playback_rms_fs=playback_rms,
    )
    _baseline, _baseline_metadata = load_baseline(
        BASELINE_DIR, model_sha256=_model_manifest["model_sha256"]
    )
    logger.info(
        f"BASELINE ready count={len(capture_ids)} playback_rms_fs={playback_rms:.6f}"
    )
    Bridge.call("show_runtime_status", 7)


def process_inference_request(requested_state: int) -> None:
    global _request_sequence
    initialize_runtime()
    broker = FileAudioBroker(AUDIO_SPOOL)
    if _model_predictor is None:
        Bridge.call("show_runtime_status", 6)
        return
    if not broker.ready:
        logger.error("INFERENCE unavailable: privileged audio worker is not configured")
        Bridge.call("show_runtime_status", 1)
        return
    if _baseline is None and requested_state != 0:
        logger.info("BASELINE required: set all five states closed and press EXEC")
        Bridge.call("show_runtime_status", 2)
        return

    Bridge.call("set_inference_busy", 1)
    try:
        if _baseline is None:
            _calibrate_live_baseline(broker)
            return
        Bridge.call("show_runtime_status", 4)
        capture_id, frame, health = _capture_checked(broker, requested_state)
        current_state = int(Bridge.call("get_servo_state"))
        if current_state != requested_state:
            logger.error(
                f"INFERENCE discarded id={capture_id} requested=0b{requested_state:05b} "
                f"current=0b{current_state:05b}"
            )
            Bridge.call("show_runtime_status", 8)
            return
        started = time.monotonic()
        prediction = _model_predictor.predict_audio(frame, _baseline)
        inference_ms = (time.monotonic() - started) * 1000.0
        _request_sequence = (_request_sequence + 1) & 0x7FFFFFFF
        if _request_sequence == 0:
            _request_sequence = 1
        result = int(Bridge.call(
            "show_prediction",
            prediction.state_mask,
            prediction.confidence_percent,
            requested_state,
            _request_sequence,
        ))
        if result != _request_sequence:
            logger.error(f"INFERENCE display rejected request={_request_sequence} result={result}")
            return
        logger.info(
            f"INFERENCE model id={capture_id} request={_request_sequence} "
            f"actual=0b{requested_state:05b} predicted=0b{prediction.state_mask:05b} "
            f"confidence={prediction.confidence:.6f} margin={prediction.top2_margin:.6f} "
            f"inference_ms={inference_ms:.3f} "
            f"capture_rms={health['left_rms_fs']:.6f}"
        )
    except AudioRuntimeError as error:
        logger.error(f"CAPTURE failed error={error}")
        Bridge.call("show_runtime_status", 5)
    except Exception as error:
        logger.error(f"INFERENCE failed error={error}")
        Bridge.call("show_runtime_status", 6)
    finally:
        try:
            Bridge.call("set_inference_busy", 0)
        except Exception as error:
            logger.error(f"MCU busy-clear failed error={error}")


def _eval_move(channel: int, degrees: int) -> None:
    result = int(Bridge.call("move_servo_deg", channel, degrees))
    if result != 0:
        raise RuntimeError(f"move_servo_deg ch={channel} deg={degrees} failed={result}")


def _eval_drive_to(target: int) -> None:
    """Move only changed channels: CLOSE BC->a first, then OPEN a->BC."""
    global _eval_servo_state
    current = _eval_servo_state
    _eval_servo_state = None  # unknown until every move succeeded
    for channel in range(4, -1, -1):
        if current is None or (current >> channel & 1 and not target >> channel & 1):
            if not target >> channel & 1:
                _eval_move(channel, 180)
    for channel in range(5):
        if target >> channel & 1 and (current is None or not current >> channel & 1):
            _eval_move(channel, 0)
    _eval_servo_state = target


def process_eval_command() -> None:
    """Operator-approved evaluation servo control through a host-owned file.

    The host writes ``runtime/eval/command.json`` ({"id", "op", "state"}); the
    result is published atomically as ``result-<id>.json``.  Automatic switch
    following stays OFF; ``disarm`` releases every PCA9685 channel.
    """
    global _eval_servo_state
    command_path = EVAL_DIR / "command.json"
    if not command_path.is_file():
        return
    try:
        command = json.loads(command_path.read_text(encoding="utf-8"))
    finally:
        command_path.unlink(missing_ok=True)
    command_id = str(command.get("id", ""))
    if not command_id.isalnum() or len(command_id) > 64:
        logger.error("EVAL rejected command with invalid id")
        return
    op = command.get("op")
    result = {"id": command_id, "op": op, "status": "ok"}
    try:
        if op == "arm":
            Bridge.call("set_servo_automation", 0)
            expected = int(Bridge.call("get_physical_state")) & 0x1F
            armed = int(Bridge.call("set_servo_armed", 1, expected))
            if armed != 0:
                raise RuntimeError(f"set_servo_armed failed={armed}")
            _eval_servo_state = None
            _eval_drive_to(0)
        elif op == "set_state":
            if _eval_servo_state is None:
                raise RuntimeError("evaluation servos are not armed/synchronised")
            target = int(command["state"])
            if not 0 <= target <= 0x1F:
                raise ValueError("state must be 0..31")
            _eval_drive_to(target)
        elif op == "calibrate_baseline":
            # Same live all-closed baseline as the first EXEC, triggered by the
            # host so the operator only flips switches and presses EXEC.
            initialize_runtime()
            broker = FileAudioBroker(AUDIO_SPOOL)
            if _model_predictor is None or not broker.ready:
                raise RuntimeError("model or audio worker not ready")
            Bridge.call("set_inference_busy", 1)
            try:
                _calibrate_live_baseline(broker)
            finally:
                Bridge.call("set_inference_busy", 0)
            result["baseline_capture_count"] = int(_baseline_metadata["capture_count"])
        elif op == "follow_switches":
            # Operator mode: servos follow D3-D7 and EXEC runs inference.
            expected = int(Bridge.call("get_physical_state")) & 0x1F
            armed = int(Bridge.call("set_servo_armed", 1, expected))
            if armed != 0:
                raise RuntimeError(f"set_servo_armed failed={armed}")
            automation = int(Bridge.call("set_servo_automation", 1))
            if automation != 0:
                raise RuntimeError(f"set_servo_automation failed={automation}")
            _eval_servo_state = None
        elif op == "disarm":
            _eval_servo_state = None
            disarmed = int(Bridge.call("set_servo_armed", 0, 0))
            if disarmed != 0:
                raise RuntimeError(f"set_servo_armed(0) failed={disarmed}")
        elif op != "status":
            raise ValueError(f"unknown op {op!r}")
    except Exception as error:
        result["status"] = "error"
        result["error"] = str(error)
    result["servo_state"] = _eval_servo_state
    result["hardware_status"] = int(Bridge.call("get_hardware_status"))
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    temporary = EVAL_DIR / f".result-{command_id}.tmp"
    temporary.write_text(json.dumps(result) + "\n", encoding="utf-8")
    os.replace(temporary, EVAL_DIR / f"result-{command_id}.json")
    logger.info(f"EVAL {op} status={result['status']} servo_state={_eval_servo_state}")


def loop_once() -> None:
    global _startup_complete, _last_switch_states
    initialize_runtime()
    process_eval_command()
    if not _startup_complete:
        time.sleep(2)
        hardware_status = int(Bridge.call("get_hardware_status"))
        physical_state = int(Bridge.call("get_physical_state")) & 0x1F
        servo_state = int(Bridge.call("get_servo_state"))
        servo_text = f"0b{servo_state:05b}" if servo_state >= 0 else "unknown"
        logger.info(
            f"bring-up status=0x{hardware_status:02x} "
            f"switch_request=0b{physical_state:05b} servo={servo_text}"
        )
        logger.info("Transport ready; TFT remains on the original inf/act idle screen")
        _startup_complete = True

    requested_state = _inference_requests.take()
    if requested_state is not None:
        process_inference_request(requested_state)
    switch_states = int(Bridge.call("get_switch_states")) & 0x3F
    if switch_states != _last_switch_states:
        labels = ("WIN_A", "WIN_B", "WIN_C", "DOOR_AB", "DOOR_BC", "EXEC")
        logger.info("INPUT " + " ".join(
            f"{label}={(switch_states >> bit) & 1}"
            for bit, label in enumerate(labels)
        ))
        _last_switch_states = switch_states
    time.sleep(0.1)


def loop() -> None:
    global _startup_complete
    try:
        loop_once()
    except Exception as error:
        _startup_complete = False
        logger.error(f"RUNTIME transient failure; retrying error={error}")
        time.sleep(1.0)


App.run(user_loop=loop)
