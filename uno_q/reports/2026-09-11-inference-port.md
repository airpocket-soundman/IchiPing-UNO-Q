# UNO Q inference software port — 2026-09-11

## Scope and result

- Board: Arduino UNO Q, USB serial `2261748543`, QRB2210 Debian application container.
- Software: current `IchiPing-UNO-Q` working tree on 2026-09-11; ONNX Runtime 1.30.0.
- Result: **PASS** for retraining, FP32 ONNX export, feature-equivalence tests,
  packaged-model evaluation, and model execution on the UNO Q CPU.
- Not yet claimed: end-to-end accuracy from the installed UNO Q speaker and
  microphone. A live all-closed baseline and calibrated white-noise recordings
  are still required.

## Data and accuracy

The available tracked training subset contains 160 unique two-second WAV files:
five recordings for each of 32 states from `full_32_train_v21` through `v25`.
The separately tracked `full_32_eval_v1` contains one recording per state. This
is much smaller than the historical 8,000/320-file data set, so the result is a
preliminary pipeline check rather than a generalization claim.

- Model: `IchiPingV1_32clsNeutron-XL`, 104,000 parameters.
- Feature: `noise_diff_norm`, 16 kHz mono, two seconds, 1,024 Welch bins.
- Internal training test: 32-state 93.33%, 14-class 100%.
- Tracked independent representative evaluation: 30/32 = 93.75% at 32-state;
  32/32 = 100% at 14-class; 14-class macro-F1 1.0.
- Checkpoint SHA256:
  `2995bd0804fe3520515d6888bf39e67c71ef894db555bcddcac9ed73cdf07110`.

## Packaged UNO Q runtime

The consolidated opset-18 FP32 model is
`uno_q/app/models/ichiping-representative-20260911.onnx` with SHA256
`144d2316b04d67500470060c494cb0cdcf0f143f101cd5ab4420ee7d8a285695`.
Its input is `[1,1,1,1024]` and output is `[1,32,1,1]`.

The UNO Q application now contains:

- stereo S16_LE left-slot extraction, anti-aliased 48-to-16 kHz decimation,
  stable center two-second crop, and a NumPy Welch implementation matched to
  the original SciPy feature path;
- all-closed baseline creation and `noise_diff_norm` inference;
- a manifest-pinned ONNX predictor and offline capture CLI;
- a one-slot newest-wins request mailbox, removing the Router Bridge nested-call
  timeout in the EXEC callback.

Measured in the UNO Q application container: model load 194.83 ms, mean inference
1.394 ms, p95 1.659 ms, and process RSS 61.8 MiB. These are below the project
budgets. Live inference remains disabled until live audio capture and baseline
orchestration are connected; no synthetic success is shown.
After deployment, the normal app startup log reported the manifest-pinned model
ready while retaining `audio=not-configured baseline=missing mode=waiting-audio`.

## White-noise calibration software

The calibration path prepares deterministic S32_LE stereo noise with 0.5 seconds
of leading silence, exactly 5 seconds of audible noise, and 1 second of trailing
silence. Recording lasts 6 seconds. Analysis uses the stable center two seconds
after left-channel extraction and 48-to-16 kHz conversion.

Each invocation performs one level only. The next level is calculated after the
recording is inspected, may increase by at most 2x, and never exceeds 10%FS RMS.
The target derived from the tracked training recordings is 18–19%FS recorded RMS
with recorded peak below 90%FS. No calibration sound was emitted while adding
this software.

The no-playback preparation check on the UNO Q produced exactly 2,496,000 bytes
(6.5 seconds), with both silent margins intact, active RMS 0.29928%FS, and peak
0.51961%FS for a requested 0.3%FS RMS. The audio route was not opened.

## Verification

- UNO Q application Python offline tests: 10 passed.
- Audio and safety offline tests: 26 passed.
- Packaged ONNX representative evaluation is part of the application test set
  and asserts exactly 30/32 correct.
- Audio hardware connected for earlier acceptance: MAX98357A, speaker, INMP441,
  GPIO28 SD control with external 10 kOhm pulldown, common ground.
- Unconnected test equipment during this software-only work: OWON oscilloscope
  and SLogic analyzer were not required.
