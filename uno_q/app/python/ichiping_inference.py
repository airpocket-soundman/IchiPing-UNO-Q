"""UNO Q Linux preprocessing and ONNX inference for IchiPing white-noise frames."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np


RATE_CAPTURE_HZ = 48_000
RATE_MODEL_HZ = 16_000
NFFT = 2048
HOP = 1024
DB_FLOOR = -80.0
N_CLASSES = 32


def capture_health(raw: bytes, capture_format: str = "S16_LE",
                   duration_range: tuple[float, float] = (5.5, 6.5)) -> dict:
    """Reject truncated, silent, clipped, or wrong-slot INMP441 captures.

    Levels are fractions of the I2S word full scale (before the x16
    original-collector gain).
    """
    width = {"S16_LE": 2, "S32_LE": 4}.get(capture_format)
    if width is None:
        raise ValueError("capture format must be S16_LE or S32_LE")
    if not raw or len(raw) % (2 * width):
        raise ValueError(f"capture must be nonempty frame-aligned stereo {capture_format}")
    frames = len(raw) // (2 * width)
    duration = frames / RATE_CAPTURE_HZ
    if not duration_range[0] <= duration <= duration_range[1]:
        raise ValueError(f"unexpected capture duration: {duration:.3f}s")
    dtype, scale = ("<i2", 32768.0) if width == 2 else ("<i4", 2.0**31)
    stereo = np.frombuffer(raw, dtype=dtype).reshape(-1, 2).astype(np.float64)
    rms = np.sqrt(np.mean(stereo * stereo, axis=0)) / scale
    peak = np.max(np.abs(stereo), axis=0) / scale
    if rms[0] < 1e-4:
        raise ValueError("left microphone slot is silent")
    if peak[0] >= 0.95:
        raise ValueError("left microphone slot is clipping")
    if rms[1] > max(1e-5, rms[0] * 0.10):
        raise ValueError("unexpected signal in right microphone slot")
    return {
        "duration_seconds": duration,
        "left_rms_fs": float(rms[0]),
        "left_peak_fs": float(peak[0]),
        "right_rms_fs": float(rms[1]),
    }


def left_s16le_to_float(raw: bytes) -> np.ndarray:
    """Extract the active (left) INMP441 slot from stereo S16_LE frames."""
    if not raw or len(raw) % 4:
        raise ValueError("capture must be nonempty frame-aligned stereo S16_LE")
    stereo = np.frombuffer(raw, dtype="<i2").reshape(-1, 2)
    return stereo[:, 0].astype(np.float32) / 32768.0


def decimate_48k_to_16k(samples: np.ndarray) -> np.ndarray:
    """Anti-aliased 3:1 decimation using a deterministic 63-tap FIR."""
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim != 1 or x.size < 63:
        raise ValueError("expected at least 63 mono samples")
    taps = 63
    center = (taps - 1) / 2
    n = np.arange(taps, dtype=np.float64) - center
    # Cut off below the new Nyquist frequency; Blackman window limits aliasing.
    cutoff = 0.15  # cycles/input sample; new Nyquist is 1/6 ~= 0.1667
    kernel = 2 * cutoff * np.sinc(2 * cutoff * n) * np.blackman(taps)
    kernel /= kernel.sum()
    filtered = np.convolve(x.astype(np.float64), kernel, mode="same")
    return filtered[::3].astype(np.float32)


# The FRDM collector stored int16 = clip(32-bit I2S word >> 12).  Relative to
# the word full scale used here (S16_LE = word >> 16, S32_LE = word) that is a
# fixed x16 gain; measured UNO Q PRBS captures confirm the scale.
ORIGINAL_CAPTURE_GAIN = 16


def left_capture_to_float(raw: bytes, capture_format: str = "S16_LE") -> np.ndarray:
    """Left INMP441 slot as a fraction of the 32-bit I2S word full scale."""
    if capture_format == "S16_LE":
        return left_s16le_to_float(raw)
    if capture_format != "S32_LE":
        raise ValueError("capture format must be S16_LE or S32_LE")
    if not raw or len(raw) % 8:
        raise ValueError("capture must be nonempty frame-aligned stereo S32_LE")
    stereo = np.frombuffer(raw, dtype="<i4").reshape(-1, 2)
    # 24 significant bits are exact in float32.
    return (stereo[:, 0].astype(np.float64) / 2**31).astype(np.float32)


def to_original_scale(samples_16k: np.ndarray, quantize: str = "int16") -> np.ndarray:
    """Map word-scale 16 kHz audio onto the original collector's int16 scale.

    ``int16`` reproduces the collector's arithmetic-shift floor and INT16
    clipping, so new captures can be mixed with the original WAV dataset.
    ``float`` keeps every captured bit (clipped to the same range) for
    UNO Q-native datasets.
    """
    y = np.asarray(samples_16k, dtype=np.float64) * ORIGINAL_CAPTURE_GAIN
    if quantize == "int16":
        y = np.clip(np.floor(y * 32768.0), -32768, 32767) / 32768.0
    elif quantize == "float":
        y = np.clip(y, -1.0, 32767 / 32768)
    else:
        raise ValueError("quantize must be 'int16' or 'float'")
    return y.astype(np.float32)


PRBS_SEED = 20260912
PRBS_FRAME_SAMPLES = 32_000  # original collector: 2.0 s at 16 kHz


def prbs_source(seed: int = PRBS_SEED) -> np.ndarray:
    """The ±1 16 kHz PRBS played by uno_q/audio (same generator, same seed)."""
    import random

    rng = random.Random(seed)
    return np.array([1.0 if rng.getrandbits(1) else -1.0
                     for _ in range(PRBS_FRAME_SAMPLES)], dtype=np.float64)


def align_prbs_capture(raw: bytes, capture_format: str = "S32_LE",
                       seed: int = PRBS_SEED, quantize: str = "int16") -> np.ndarray:
    """2.0 s model frame starting at the acoustic PRBS onset, original scale.

    Same processing as the dataset export: decimate, locate the onset by
    cross-correlation with the known PRBS, x16 (collector word >> 12).
    """
    word = decimate_48k_to_16k(left_capture_to_float(raw, capture_format))
    mono = word.astype(np.float64)
    mono -= mono.mean()
    reference = prbs_source(seed)
    n = reference.size
    if mono.size < n:
        raise ValueError("capture is shorter than the PRBS frame")
    size = 1 << int(np.ceil(np.log2(mono.size + n)))
    corr = np.fft.irfft(np.fft.rfft(mono, size) * np.conj(np.fft.rfft(reference, size)), size)
    lag = int(np.argmax(np.abs(corr[: mono.size - n + 1])))
    return to_original_scale(word[lag:lag + n], quantize)


def capture_to_model_audio(raw: bytes, crop_seconds: float = 2.0,
                           capture_format: str = "S16_LE") -> np.ndarray:
    """Convert a 48 kHz stereo capture and take a stable center crop for the model."""
    if not 0 < crop_seconds <= 5.0:
        raise ValueError("crop_seconds must be > 0 and <= 5")
    mono_16k = decimate_48k_to_16k(left_capture_to_float(raw, capture_format))
    wanted = round(RATE_MODEL_HZ * crop_seconds)
    if mono_16k.size < wanted:
        raise ValueError("capture is shorter than requested model crop")
    start = (mono_16k.size - wanted) // 2
    return mono_16k[start:start + wanted].copy()


def logmag_psd(samples_16k: np.ndarray) -> np.ndarray:
    """NumPy equivalent of scipy.signal.welch used by pc/training/features.py."""
    x = np.asarray(samples_16k, dtype=np.float32)
    if x.ndim != 1 or x.size < NFFT:
        raise ValueError(f"need at least {NFFT} mono samples at {RATE_MODEL_HZ} Hz")
    starts = range(0, x.size - NFFT + 1, HOP)
    window = np.hanning(NFFT + 1)[:-1].astype(np.float64)  # periodic Hann
    scale = 1.0 / float(window.sum() ** 2)
    accum = np.zeros(NFFT // 2 + 1, dtype=np.float64)
    count = 0
    for start in starts:
        segment = x[start:start + NFFT].astype(np.float64)
        segment -= segment.mean()  # scipy Welch default detrend="constant"
        spectrum = np.fft.rfft(segment * window)
        power = np.abs(spectrum) ** 2 * scale
        power[1:-1] *= 2.0
        accum += power
        count += 1
    pxx = accum / count
    db = 10.0 * np.log10(pxx[1:] + 1e-12)
    return np.maximum(db, DB_FLOOR).astype(np.float32)


def noise_diff_norm(samples_16k: np.ndarray, baseline_db: np.ndarray) -> np.ndarray:
    baseline = np.asarray(baseline_db, dtype=np.float32)
    if baseline.shape != (1024,):
        raise ValueError("baseline must have shape (1024,)")
    feature = logmag_psd(samples_16k) - baseline
    feature -= feature.mean()
    return (feature / (float(feature.std()) + 1e-6)).astype(np.float32)


def calibrate_baseline(frames_16k: list[np.ndarray]) -> np.ndarray:
    """Average absolute Welch spectra from one or more all-closed recordings."""
    if not frames_16k:
        raise ValueError("at least one all-closed baseline frame is required")
    spectra = np.stack([logmag_psd(frame) for frame in frames_16k])
    baseline = spectra.mean(axis=0).astype(np.float32)
    if baseline.shape != (1024,) or not np.isfinite(baseline).all():
        raise ValueError("invalid calibrated baseline")
    return baseline


def softmax_confidence(logits: np.ndarray) -> tuple[int, float]:
    flat = np.asarray(logits, dtype=np.float32).reshape(-1)
    if flat.shape != (N_CLASSES,) or not np.isfinite(flat).all():
        raise ValueError("model must return 32 finite logits")
    shifted = flat - flat.max()
    probabilities = np.exp(shifted)
    probabilities /= probabilities.sum()
    state = int(probabilities.argmax())
    return state, float(probabilities[state])


@dataclass(frozen=True)
class Prediction:
    state_mask: int
    confidence: float
    logits: np.ndarray

    @property
    def confidence_percent(self) -> int:
        return max(0, min(100, round(self.confidence * 100)))

    @property
    def top2_margin(self) -> float:
        shifted = self.logits.astype(np.float64) - float(np.max(self.logits))
        probabilities = np.exp(shifted)
        probabilities /= probabilities.sum()
        top = np.partition(probabilities, -2)[-2:]
        return float(top.max() - top.min())


class OnnxPredictor:
    """Load one manifest-pinned ONNX model and execute 32-state inference."""

    def __init__(
        self,
        model_path: Path,
        expected_sha256: str | None = None,
        manifest: dict | None = None,
    ) -> None:
        path = Path(model_path)
        if expected_sha256:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected_sha256:
                raise ValueError(f"model SHA256 mismatch: {actual}")
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(path), options, providers=["CPUExecutionProvider"]
        )
        inputs = self.session.get_inputs()
        outputs = self.session.get_outputs()
        if len(inputs) != 1 or tuple(inputs[0].shape) not in (
            (1, 1, 1024), (1, 1, 1, 1024)
        ):
            raise ValueError(f"unsupported model input: {[item.shape for item in inputs]}")
        if len(outputs) != 1:
            raise ValueError("expected one logits output")
        if tuple(outputs[0].shape) not in ((1, 32), (1, 32, 1, 1)):
            raise ValueError(f"unsupported model output: {outputs[0].shape}")
        if manifest is not None:
            expected_input = tuple(manifest["input_shape"])
            expected_output = tuple(manifest["output_shape"])
            if inputs[0].name != manifest["input_name"] or tuple(inputs[0].shape) != expected_input:
                raise ValueError("ONNX input does not match manifest")
            if outputs[0].name != manifest["output_name"] or tuple(outputs[0].shape) != expected_output:
                raise ValueError("ONNX output does not match manifest")
        self.input = inputs[0]

    def predict_features(self, features: np.ndarray) -> Prediction:
        x = np.asarray(features, dtype=np.float32)
        if x.shape != (1024,) or not np.isfinite(x).all():
            raise ValueError("features must have shape (1024,) and be finite")
        shape = (1, 1, 1024) if len(self.input.shape) == 3 else (1, 1, 1, 1024)
        logits = np.asarray(
            self.session.run(None, {self.input.name: x.reshape(shape)})[0],
            dtype=np.float32,
        ).reshape(-1)
        state, confidence = softmax_confidence(logits)
        return Prediction(state, confidence, logits)

    def predict_audio(
        self, samples_16k: np.ndarray, baseline_db: np.ndarray
    ) -> Prediction:
        return self.predict_features(noise_diff_norm(samples_16k, baseline_db))


def load_manifest(path: Path) -> dict:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {
        "model_file", "model_sha256", "feature_mode", "sample_rate_hz",
        "input_name", "input_shape", "output_name", "output_shape",
        "frame_seconds", "state_bit_order",
    }
    missing = required - manifest.keys()
    if missing:
        raise ValueError(f"manifest missing: {sorted(missing)}")
    if manifest["feature_mode"] != "noise_diff_norm":
        raise ValueError("UNO Q runtime currently requires noise_diff_norm")
    if manifest["sample_rate_hz"] != RATE_MODEL_HZ:
        raise ValueError("model sample rate mismatch")
    if manifest["frame_seconds"] != 2.0:
        raise ValueError("model frame duration mismatch")
    if manifest["input_shape"] not in ([1, 1, 1024], [1, 1, 1, 1024]):
        raise ValueError("manifest input shape mismatch")
    if manifest["output_shape"] not in ([1, 32], [1, 32, 1, 1]):
        raise ValueError("manifest output shape mismatch")
    if manifest["state_bit_order"] != [
        "window_a", "window_b", "window_c", "door_AB", "door_BC"
    ]:
        raise ValueError("state bit order mismatch")
    return manifest
