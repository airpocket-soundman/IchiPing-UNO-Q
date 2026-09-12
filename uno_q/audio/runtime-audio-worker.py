#!/usr/bin/env python3
"""Worker for bounded IchiPing MI2S0 captures requested by the App Lab app.

The app (container) writes runtime/audio/request.json; this host process runs
safe-audio-test.sh and publishes the capture plus a response.  It runs as
root (systemd .path unit, one shot) or, with ``--loop``, as a user in the
audio and gpiod groups (safe-audio-test.sh no longer needs root).
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o644)
    os.replace(temporary, path)


def validate_request(payload: dict) -> tuple[str, int]:
    if payload.get("version") != 1 or payload.get("operation") not in (
            "capture-white-noise", "capture-prbs16k"):
        raise ValueError("unsupported audio request")
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or len(request_id) != 32:
        raise ValueError("invalid request ID")
    if any(char not in "0123456789abcdef" for char in request_id):
        raise ValueError("invalid request ID")
    state = payload.get("requested_state")
    if not isinstance(state, int) or not 0 <= state <= 31:
        raise ValueError("invalid requested state")
    return request_id, state


def process(spool: Path, safe_script: Path, serial: str, playback_rms: float,
            excitation: str = "white", capture_format: str = "S16_LE") -> bool:
    request_path = spool / "request.json"
    if not request_path.is_file():
        return False
    claimed = spool / f"request.processing-{os.getpid()}.json"
    os.replace(request_path, claimed)
    request_id = "unknown"
    try:
        payload = json.loads(claimed.read_text(encoding="utf-8"))
        request_id, requested_state = validate_request(payload)
        environment = os.environ.copy()
        environment.update({
            "ICHIPING_EXPECTED_USB_SERIAL": serial,
            "ICHIPING_EXCITATION": excitation,
            "ICHIPING_CAPTURE_FORMAT": capture_format,
        })
        if excitation == "prbs16k":
            environment["ICHIPING_PRBS_AMPLITUDE"] = str(playback_rms)
        else:
            environment["ICHIPING_NOISE_RMS"] = str(playback_rms)
        started = time.monotonic()
        completed = subprocess.run(
            [str(safe_script), "calibrate-noise", request_id],
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=12,
            check=False,
        )
        # The capture path depends on the running user's work directory.
        marker = "ICHIPING_CALIBRATION_CAPTURE:"
        reported = [line[len(marker):].strip() for line in completed.stdout.splitlines()
                    if line.startswith(marker)]
        source = Path(reported[-1]) if reported else None
        if completed.returncode != 0 or source is None or not source.is_file():
            raise RuntimeError(
                f"safe audio capture failed rc={completed.returncode}: "
                f"{completed.stdout[-1000:]}"
            )
        capture_dir = spool / "captures"
        capture_dir.mkdir(exist_ok=True)
        destination = capture_dir / f"{request_id}.raw"
        shutil.move(source, destination)
        os.chmod(destination, 0o644)
        atomic_json(spool / "responses" / f"{request_id}.json", {
            "version": 1,
            "request_id": request_id,
            "requested_state": requested_state,
            "status": "ok",
            "capture_file": destination.name,
            "capture_bytes": destination.stat().st_size,
            "elapsed_seconds": time.monotonic() - started,
            "playback_rms_fs": playback_rms,
            "excitation": excitation,
            "capture_format": capture_format,
        })
    except Exception as error:
        if request_id != "unknown":
            atomic_json(spool / "responses" / f"{request_id}.json", {
                "version": 1,
                "request_id": request_id,
                "status": "error",
                "error": str(error),
            })
        raise
    finally:
        claimed.unlink(missing_ok=True)
    return True


def audio_capable_user() -> bool:
    if os.geteuid() == 0:
        return True
    import grp
    groups = {grp.getgrgid(gid).gr_name for gid in os.getgroups()}
    return {"audio", "gpiod"} <= groups


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spool", required=True, type=Path)
    parser.add_argument("--safe-script", required=True, type=Path)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--playback-rms", required=True, type=float,
                        help="white: noise RMS FS; prbs16k: PRBS +-amplitude FS")
    parser.add_argument("--excitation", choices=("white", "prbs16k"), default="white")
    parser.add_argument("--capture-format", choices=("S16_LE", "S32_LE"), default="S16_LE")
    parser.add_argument("--loop", action="store_true",
                        help="stay resident, poll for requests and publish worker-ready.json")
    parser.add_argument("--poll", type=float, default=0.05)
    args = parser.parse_args()
    if not audio_capable_user():
        raise SystemExit("runtime audio worker must run as root or in the audio and gpiod groups")
    if not 0 < args.playback_rms <= 0.10:
        raise SystemExit("playback level must be >0 and <=0.10 FS")
    args.spool.mkdir(parents=True, exist_ok=True)
    (args.spool / "responses").mkdir(exist_ok=True)
    lock_path = args.spool / "worker.lock"
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not args.loop:
            process(args.spool, args.safe_script, args.serial, args.playback_rms,
                    args.excitation, args.capture_format)
            return
        ready = args.spool / "worker-ready.json"
        atomic_json(ready, {"version": 1, "status": "ready", "playback_rms_fs": args.playback_rms,
                            "excitation": args.excitation, "capture_format": args.capture_format,
                            "pid": os.getpid()})
        try:
            while True:
                try:
                    process(args.spool, args.safe_script, args.serial, args.playback_rms,
                            args.excitation, args.capture_format)
                except Exception as error:  # one failed capture must not stop the service
                    print(f"capture failed: {error}", flush=True)
                time.sleep(args.poll)
        finally:
            ready.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
