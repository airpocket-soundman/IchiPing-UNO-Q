# Results

All numbers are on held-out UNO Q evaluation sets that were never used for training. Values are **32-state / 14-class (observable)** accuracy in %.

## Deployed model

| Evaluation set | Condition | 32-state | 14-class |
|---|---|---|---|
| 09:00 | stable, same state as training | 91.7 | 100 |
| 19:35 | largest temperature drift (−2.15 % frequency warp) | 81.9 | 100 |
| 20:44 | drift −1.05 % | 74.7 | 100 |
| 21:28 | crowd noise playing, drift −0.80 % | 81.9 | 100 |

The deployed model (sessions 1–8, cross-baseline, strong augmentation, room + crowd ambient, ±3 % frequency warp) keeps **100 % on the observable classes** on every set and reaches **82.5 %** mean 32-state accuracy.

## Going beyond the observable region

The observable-class model says a closed door AB hides window b, window c and door BC. The 32-state accuracy measures how well the model reads those hidden openings from the weak sound that still leaks through the door. It improved step by step:

| Step | Mean 32-state accuracy |
|---|---|
| Original FRDM model on UNO Q | 19.3 |
| UNO Q data, 1 session | 27–38 |
| 4 sessions + original recipe (cross-baseline, strong augmentation) | 68.9 |
| + ambient noise | 70.3 |
| + frequency warp (temperature) | 77.6 |
| 8 sessions + warp + ambient (deployed) | **82.5** |

Window c behind closed doors — the smallest cue, about 0.5–0.9 dB — rose from 56 % with the original model to 86–90 %.

## All models

The full table (23 models, with training data, augmentation, ambient overlay and start point) is in [pc/runs/model_comparison_20260912.md](../../pc/runs/model_comparison_20260912.md). Key observations:

- More sessions help most: 47 % → 94 % on an unseen session going from one to five sessions.
- Cross-baseline training fixes session-to-session drift of door BC (58 % → 100 %).
- Frequency warp gives the largest single gain under temperature drift (+12 points at 19:35 and 20:44) and costs nothing on stable data.
- Mixing the original FRDM dataset into UNO Q training did not help once enough UNO Q sessions existed.
- A louder excitation did not make window c easier to read; the level is kept at the original ±0.0088.

## Latency and resources

| Metric | Value |
|---|---|
| One inference, end to end | about 5 s (2 s PRBS + 3 s capture + processing) |
| Model inference (Cortex-A53, ONNX Runtime FP32) | 1.7 ms p95 |
| Inference process RSS | about 62 MiB |
| Sketch | 31,992 bytes flash, 6,644 bytes RAM |
