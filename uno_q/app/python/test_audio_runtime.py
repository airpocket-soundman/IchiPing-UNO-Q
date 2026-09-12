import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from audio_runtime import AudioRuntimeError, FileAudioBroker


class AudioRuntimeTests(unittest.TestCase):
    def test_requires_ready_worker(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(AudioRuntimeError):
                FileAudioBroker(Path(root), timeout_seconds=0.01).capture_white_noise(0)

    def test_request_response_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            spool = Path(root)
            (spool / "worker-ready.json").write_text("{}", encoding="utf-8")

            def worker():
                request_path = spool / "request.json"
                deadline = time.monotonic() + 1
                while not request_path.exists() and time.monotonic() < deadline:
                    time.sleep(0.005)
                request = json.loads(request_path.read_text(encoding="utf-8"))
                captures = spool / "captures"
                responses = spool / "responses"
                captures.mkdir(exist_ok=True)
                responses.mkdir(exist_ok=True)
                name = f"{request['request_id']}.raw"
                (captures / name).write_bytes(b"audio")
                (responses / f"{request['request_id']}.json").write_text(json.dumps({
                    "request_id": request["request_id"],
                    "status": "ok",
                    "capture_file": name,
                }), encoding="utf-8")

            thread = threading.Thread(target=worker)
            thread.start()
            capture = FileAudioBroker(spool, timeout_seconds=1).capture_white_noise(7)
            thread.join()
            self.assertEqual(capture.raw, b"audio")


if __name__ == "__main__":
    unittest.main()
