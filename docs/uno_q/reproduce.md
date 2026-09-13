# Reproduce UNO Ping

This guide assumes the parts in [Hardware and wiring](hardware.md) and a UNO Q reachable over SSH.

## 1. Build the model apartment

Three rooms in a row (A, B, C), a window on each room (a, b, c) and inner doors AB and BC. Put the speaker and the microphone in room A. Attach one SG90 to each window and door so that 180° closes and 0° opens it.

## 2. Wire the MCU side

Connect the switches (D3–D7), the EXEC button (D8), the PCA9685 (D20/D21, 0x40) with its servos on channels 0–4, and the ILI9341 (D11, D13, A2–A5). Use an external 5 V supply for the servos with a common ground.

## 3. Enable the MI2S0 audio bus (once, needs root)

Follow `uno_q/audio/README.md`: build the Device Tree overlay `ichiping-mi2s0.dtso`, build the patched ALSA modules for the running kernel, and install the test boot entry. After reboot, check:

```sh
cat /proc/device-tree/sound/model     # Arduino-Imola-IchiPing-MI2S0
aplay -l && arecord -l
```

Then wire the INMP441 and MAX98357A (1.8 V signals, 10 kΩ from SD to GND) with the board powered off.

## 4. Install the audio tools (normal user)

```sh
mkdir -p ~/ichiping-audio && cp uno_q/audio/{safe-audio-test.sh,white-noise-cycle.sh,audio-cycle-test.sh,external-reference-capture.sh,route-mi2s0.sh,audio-smoke-test.py,runtime-audio-worker.py} ~/ichiping-audio/
```

The user must be in the `audio` and `gpiod` groups. A first safe test (quiet 440 Hz tone and capture):

```sh
ICHIPING_TONE_AMPLITUDE=0.0001 ~/ichiping-audio/safe-audio-test.sh cycle
```

## 5. Deploy the App Lab app

Copy `uno_q/app/` to `~/ArduinoApps/ichiping-uno-q/` and start it:

```sh
arduino-app-cli app start ~/ArduinoApps/ichiping-uno-q
```

The sketch is built and flashed to the STM32U585, and the Python app loads `models/manifest.json` and the ONNX model.

## 6. Start the audio worker

```sh
cd ~/ichiping-audio && setsid nohup python3 runtime-audio-worker.py \
  --spool ~/ArduinoApps/ichiping-uno-q/runtime/audio --safe-script ~/ichiping-audio/safe-audio-test.sh \
  --serial <your UNO Q USB serial> --playback-rms 0.0088 --excitation prbs16k \
  --capture-format S32_LE --loop > /tmp/ichiping-worker.log 2>&1 &
```

## 7. First use

1. Set all five switches to CLOSE and press EXEC once: the app records the all-closed baseline.
2. Flip switches: the servos follow.
3. Press EXEC: after about 5 s the TFT shows the prediction.

Record the baseline again after large temperature changes.

## 8. Train your own model

1. Collect sessions with `pc/uno_q_collect.py` (see [Data collection and training](data_and_training.md)).
2. Export them with `pc/uno_q_export_dataset.py`.
3. Train with `pc/training/train_32cls.py` (cross-baseline, ambient, `--freq-warp 0.03`).
4. Export ONNX with `pc/export_neutron_4d.py --backend none`, write a manifest, and compare models with `pc/uno_q_evaluate_all.py`.
5. Copy the ONNX and `manifest.json` to `uno_q/app/models/` and restart the app.
