# UNO Q implementation-gap audit — 2026-09-12

## Scope

The current UNO Q implementation was checked against `AGENTS.md`, the original
IchiPing project 10 implementation, the packaged model, and the verified MI2S0
bring-up path. The original `D:\GitHub\IchiPing` repository was read-only and
remained clean.

## Confirmed complete

- Project 10 display meaning: landscape orientation, `inf`/`act`, physical
  order `c, BC, b, AB, a`, observability colors, and the three verdicts.
- State bit order and switch polarity: bit 0..4 = a, b, c, AB, BC;
  grounded Low=CLOSE and pull-up High=OPEN. EXEC is active-low.
- D9 is reserved and is not initialized, sampled, logged, or used as a trigger.
- Packaged ONNX SHA, names, input/output shapes, 16 kHz rate, two-second frame,
  and state order match the manifest.

## Gaps fixed in this pass

- Connected the application path for EXEC → privileged bounded white-noise
  capture → capture-health checks → 48-to-16 kHz conversion → center two-second
  crop → model-bound baseline → ONNX inference → state-bound TFT result.
- Added a root-owned systemd path-worker design. The App Lab container only
  writes a fixed-schema request into its bind-mounted runtime directory; it is
  not granted ALSA, GPIO, Docker, or root access.
- Added six-second duration, left-slot signal, right-slot leakage, silence, and
  clipping guards before inference.
- Baseline creation now requires three independent all-closed captures and is
  stored atomically with the model SHA and playback RMS. A stale or corrupt
  baseline is rejected.
- Bound every prediction to its capture-time physical state and a request ID.
  A state change during capture discards the result. The MCU busy gate suppresses
  duplicate EXEC edges and defers servo synchronization during recording.
- Added model-load retry/backoff and top-2 probability-margin diagnostics.
- Added explicit state-matched servo arming. Raw/test/automatic movement is
  rejected while unarmed, channels are restricted to 0..4, startup attempts
  FULL_OFF on all 16 PCA9685 outputs, and any I2C/PWM-stop failure latches a
  fault, unarms control, and retries FULL_OFF.
- Removed production use of the onboard LED Matrix. The Linux green user LED
  remains the bounded-audio marker.

## Verification

- Board: Arduino UNO Q USB serial `2261748543`, Wi-Fi host
  `192.168.50.160`.
- Final MCU build/upload: PASS; program 31,432 bytes, global RAM 6,596 bytes.
- App restart: PASS. Container stayed running; model loaded; startup reported
  hardware status `0x03`, switch request `0b11111`, and servo state `unknown`.
- Status `0x03` means TFT initialization commands sent and PCA9685 present;
  servo-armed, servo-fault, and inference-busy bits were all clear.
- Host Python suite: 24 tests passed, including packaged-model evaluation,
  capture guards, baseline persistence, file-broker round trip, stale-state
  rejection, busy cleanup, UI contract, and mailbox behavior.
- Audio/instrument offline suite: 33 tests passed, including bounded waveform
  generation, stop-path cleanup, duplex timing, logic decoding, and PC-reference
  handshakes.
- Shell and worker Python syntax were checked on the UNO Q.
- No audio playback, microphone capture, or servo movement occurred in this
  pass. Startup only issued PCA9685 FULL_OFF writes.

## Intentionally still gated

- The five-second white-noise playback RMS must be measured against the training
  capture level before enabling the systemd worker. The installer therefore has
  not been run and `audio_worker=False` is the expected current app state.
- After the RMS is reviewed, install the worker, close all five states, and press
  EXEC once to collect the three baseline captures. Then run the 32-state
  hardware evaluation.
- Servo automation remains unarmed after every reboot. Enabling it requires the
  existing power/GND/mechanical-end checks plus an explicit state-matched arm
  call; this audit did not move the servos.
- `act` remains `-----` until the one-time servo synchronization is deliberately
  enabled and completed. It then reports the last successfully commanded
  five-servo endpoint state; it is not position-sensor feedback.
- Confidence/OOD rejection needs the additional live dataset requested by the
  user; no arbitrary threshold was invented from the small representative set.
