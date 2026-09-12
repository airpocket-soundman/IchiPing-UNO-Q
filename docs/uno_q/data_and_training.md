# Data collection and training

All UNO Q data was recorded on the real device, commanded from a PC over Wi-Fi. Raw captures stay on the PC (`pc/captures/`, not in Git); the board deletes each capture after it is copied.

## Collection protocol

| Item | Setting |
|---|---|
| State order | Gray code: every step moves exactly one servo |
| Settle | capture starts 0.5 s after the last servo stopped |
| Frames per state | 50 in one batch: one continuous PCM (2.0 s PRBS + 0.3 s gap) and one continuous capture, split offline at the exact frame pitch |
| Capture format | S32_LE (24-bit) raw kept; exported to the original int16 scale for training |
| Baseline | 50 all-closed frames at the start of each session |

One session = 50 baseline + 32 × 50 frames = 1,650 frames, about 72 minutes.

```bash
python pc/uno_q_collect.py pc/captures/<session> --batch --rounds 1 --repeats 50 \
    --baseline 50 --order gray --format S32_LE --settle 0.5 --gap 0.3
python pc/uno_q_export_dataset.py pc/captures/<session> pc/captures/<session>_wav
```

## Sessions recorded on 2026-09-12

| Data | Time | Notes |
|---|---|---|
| Sessions 1–6 | 08:48–16:34 | PRBS ±0.0088, 1,650 frames each |
| Sessions 7–8 | 16:59–19:19 | PRBS ±0.048 (louder test), exported at ×2.72 |
| Ambient | 16:34 and 21:05 | speaker silent: room noise and crowd noise, 50 frames each |
| Evaluation sets | 09:00, 19:35, 20:44, 21:28 | never used for training; 21:28 with crowd noise playing |

## Training recipe

Training runs on a PC (PyTorch, CUDA). The recipe follows the original IchiPing training and adds temperature augmentation:

| Option | Effect |
|---|---|
| `--feature-mode noise_diff_norm` | baseline difference + per-frame normalisation |
| `--aug-strong --feature-aug --spike-fix` | time shift, level jitter, white noise, frequency masks, spectral jitter |
| `--baseline-jitter-dirs <all sessions>` | cross-baseline: each recording is also diffed against every other session's baseline |
| `--ambient-dirs <room> <crowd>` | real ambient noise from the same microphone mixed at 0–35 dB SNR |
| `--freq-warp 0.03` | warp the sample's log-spectrum by ±3 % in frequency before the baseline is subtracted (temperature) |
| `--init-ckpt` | additional training from an existing model |

```bash
python -m training.train_32cls --captures <session wav dirs> --baseline-jitter-dirs <same> \
    --ambient-dirs <ambient wav dirs> --freq-warp 0.03 --feature-mode noise_diff_norm \
    --feature-aug --spike-fix --aug-strong --arch neutron --size XL --epochs 80
```

## Why temperature augmentation

In the evening the accuracy of every model dropped. The all-closed spectrum had drifted by 5.8 dB, and the drift was almost entirely a frequency scaling: the afternoon spectrum warped by −2.15 % matched the evening one (window-a opening pattern correlation 0.42 → 0.84). Resonances scale with the speed of sound, about 0.18 %/°C, so the air conditioner cooling the room shifted every resonance. The drift decayed over the night (−2.15 % → −1.05 % → −0.80 %). Warping only the sample, never the baseline, teaches the model that a baseline recorded at another temperature is normal.

## Evaluation

`pc/uno_q_evaluate.py` evaluates one model on one set, `pc/uno_q_evaluate_all.py` evaluates every packaged model on all evaluation sets, and `pc/uno_q_model_table.py` builds the comparison table. Evaluation always uses each set's own all-closed baseline, as the device does.
