"""File-spool client for the privileged UNO Q MI2S0 capture worker."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
import uuid


@dataclass(frozen=True)
class AudioCapture:
    request_id: str
    raw: bytes
    metadata: dict


class AudioRuntimeError(RuntimeError):
    pass


class FileAudioBroker:
    """Request one bounded capture through a host-owned systemd path worker.

    The App Lab container and host share the app directory. The unprivileged
    app writes a fixed-schema request; the root worker owns ALSA routing and
    always performs route/SD cleanup before publishing a response.
    """

    def __init__(self, spool_dir: Path, timeout_seconds: float = 12.0) -> None:
        self.spool_dir = Path(spool_dir)
        self.timeout_seconds = timeout_seconds

    @property
    def ready(self) -> bool:
        return (self.spool_dir / "worker-ready.json").is_file()

    def capture_white_noise(self, requested_state: int) -> AudioCapture:
        return self.capture(requested_state, "capture-white-noise")

    def capture_prbs16k(self, requested_state: int) -> AudioCapture:
        return self.capture(requested_state, "capture-prbs16k")

    def capture(self, requested_state: int, operation: str) -> AudioCapture:
        if not self.ready:
            raise AudioRuntimeError("privileged audio worker is not ready")
        request_id = uuid.uuid4().hex
        response_path = self.spool_dir / "responses" / f"{request_id}.json"
        request_path = self.spool_dir / "request.json"
        if request_path.exists():
            raise AudioRuntimeError("audio worker already has a pending request")
        payload = {
            "version": 1,
            "request_id": request_id,
            "operation": operation,
            "requested_state": int(requested_state) & 0x1F,
            "created_monotonic_ns": time.monotonic_ns(),
        }
        self.spool_dir.mkdir(parents=True, exist_ok=True)
        (self.spool_dir / "responses").mkdir(exist_ok=True)
        temporary = self.spool_dir / f".request-{os.getpid()}.tmp"
        temporary.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        os.replace(temporary, request_path)

        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            if response_path.is_file():
                response = json.loads(response_path.read_text(encoding="utf-8"))
                response_path.unlink(missing_ok=True)
                if response.get("request_id") != request_id:
                    raise AudioRuntimeError("audio response ID mismatch")
                if response.get("status") != "ok":
                    raise AudioRuntimeError(str(response.get("error", "audio capture failed")))
                capture_name = response.get("capture_file")
                capture_path = self.spool_dir / "captures" / str(capture_name)
                if capture_path.parent != self.spool_dir / "captures":
                    raise AudioRuntimeError("invalid capture response path")
                raw = capture_path.read_bytes()
                return AudioCapture(request_id, raw, response)
            time.sleep(0.05)
        if request_path.is_file():
            try:
                pending = json.loads(request_path.read_text(encoding="utf-8"))
                if pending.get("request_id") == request_id:
                    request_path.unlink()
            except (OSError, ValueError):
                pass
        raise AudioRuntimeError("audio worker response timed out")
