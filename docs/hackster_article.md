# One Ping, 32 States: Acoustic Sensing with Arduino UNO Q

**Elevator pitch:** An edge-AI system that plays one acoustic chirp and uses one MEMS microphone to identify the combined state of three windows and two doors.

**Platform:** Arduino UNO Q  
**Difficulty:** Advanced  
**Topics:** Edge AI, active acoustics, embedded Linux, Zephyr, audio, smart home

## Why listen to a room?

A conventional smart-room installation places a contact sensor on every door and window. That works, but every additional sensor adds wiring, batteries, radio provisioning, and another possible point of failure.

This project asks a different question: can the room itself act as the sensor?

Opening a door or window changes the way sound reflects through an enclosed space. A short, repeatable chirp excites those reflections. One microphone records the response, and a neural network classifies the resulting acoustic fingerprint.

The demonstrator contains three windows and two doors. Each opening is either open or closed, giving:

**2⁵ = 32 possible combined states.**

The goal is to recognize all 32 states from one active acoustic measurement.

**IMAGE TO INSERT HERE — Use-case comic**  
Caption: One chirp, one microphone, and a single 32-state result.  
Path: `docs/img/hackster_one_ping_comic_en.png`

**IMAGE TO INSERT HERE — Arduino UNO Q system architecture**  
Caption: Audio is processed on Linux while deterministic GPIO, servo, and display control remain on the STM32U585.  
Path: `docs/img/hackster_unoq_architecture.png`

## Why Arduino UNO Q?

UNO Q combines two processors with very different strengths:

- The **STM32U585 MCU** runs Arduino Core on Zephyr and handles deterministic I/O: switches, the EXEC button, the PCA9685 servo controller, and the external ILI9341 TFT.
- The **Qualcomm QRB2210 MPU** runs Debian Linux and handles audio capture, chirp playback, feature extraction, model inference, storage, and future networking.
- **Arduino Bridge** provides typed calls and notifications between the Linux application and the MCU sketch.

This division keeps timing-sensitive physical control separate from the accuracy-oriented AI pipeline. It also leaves enough Linux memory to evaluate larger FP32 models and small ensembles instead of forcing the classifier into a tiny MCU-only footprint.

## Connections

The complete bill of materials is maintained in Hackster's **Things** section. All grounds are common. The servos must use the external 5 V rail; they must not be powered from the UNO Q 3.3 V output.

### State, control, and I²C

| UNO Q pin | Connection | Function |
|---|---|---|
| D3–D7 | Five switches to GND | Window a, b, c, door AB, door BC; `INPUT_PULLUP` |
| D8 | Momentary button to GND | EXEC trigger |
| D9 | 3.3 V digital rain input | Optional environmental input |
| D20 / SDA | PCA9685 SDA | I²C address `0x40` |
| D21 / SCL | PCA9685 SCL | I²C, initially 100 kHz |

### ILI9341 display

| UNO Q pin | ILI9341 pin |
|---|---|
| D11 | MOSI |
| D13 | SCK |
| D10 | CS |
| A0 | RESET |
| A1 | DC |
| A2 | Backlight control |
| 3V3 | VCC |
| GND | GND |

The display driver is write-only, so D12/MISO is not connected. The onboard LED Matrix is not used.

### MI2S0 audio candidate

The QRB2210 audio bus is a **1.8 V interface** exposed through JMISC or the UNO Breakout Carrier. It is not available on the standard UNO header.

| Signal | Breakout J15 | Raw JMISC | Proposed endpoint |
|---|---:|---:|---|
| MI2S0 CLK / GPIO98 | 32 | 46 | INMP441 SCK + MAX98357A BCLK |
| MI2S0 WS / GPIO99 | 34 | 48 | INMP441 WS + MAX98357A LRC |
| MI2S0 DATA0 / GPIO100 | 36 | 50 | INMP441 SD, capture candidate |
| MI2S0 DATA1 / GPIO101 | 38 | 52 | MAX98357A DIN, playback candidate |

The clock and word-select lines are shared. The microphone runs from an external regulated 1.8 V rail. The MAX98357A uses the external 5 V rail while accepting the 1.8 V digital input levels.

**Important:** DATA0/DATA1 direction, the Linux Device Tree codec DAI, and the ALSA capture/playback routes must be validated before the audio modules are connected and powered. Never drive a QRB2210 MI2S0 pin with a 3.3 V or 5 V signal.

The complete, maintained connection diagram is available in [`gpio_wiring.html`](gpio_wiring.html).

## What happens after pressing EXEC?

1. The STM32U585 debounces the EXEC button and reads the five ground-truth switches.
2. The TFT changes to an active-measurement animation.
3. The MCU notifies the Debian application through Arduino Bridge.
4. Linux plays the chirp and records the microphone response.
5. The signal pipeline aligns the recording and extracts the room impulse response.
6. A spectral feature vector is passed to the 32-class model.
7. Linux returns the predicted state and confidence through Bridge.
8. The TFT displays five state tiles and a confidence bar.

The five-bit class index is:

```text
state = window_a + 2×window_b + 4×window_c + 8×door_AB + 16×door_BC
```

This produces class IDs from 0 to 31 while preserving the physical order of the openings.

## Signal processing and AI

The measurement pipeline is designed to emphasize changes in the room rather than absolute microphone level:

1. Play a known broadband chirp.
2. Align the captured waveform with matched filtering.
3. Crop the useful room-impulse-response window.
4. Compute the spectrum and convert it to log magnitude.
5. Subtract or normalize against a closed-room baseline.
6. Run a 32-class convolutional model.

Baseline calibration is especially useful because constant background sound becomes part of the reference and is largely removed by the difference feature. In controlled evaluation, live calibration reached **32/32 correct states**, while baseline-jitter augmentation reached **28/32 states without live calibration**. These are controlled-environment results; cross-session, microphone-position, and background-noise splits remain the deciding metrics for the final UNO Q model.

**IMAGE TO INSERT HERE — FFT difference feature**  
Caption: The raw spectra look similar; subtracting the all-closed baseline reveals the acoustic change caused by one open window.  
Path: `docs/img/hackster_fft_diff_en.png`

The first physical model predicted only 14 acoustically distinguishable groups because a closed door should hide the openings beyond it:

**IMAGE TO INSERT HERE — Initial acoustic observability model**  
Caption: A closed door was initially expected to hide the acoustic state of rooms beyond it.  
Path: `docs/img/hackster_observability_en.png`

The controlled experiment exceeded that simplified model. Real doors were not perfect acoustic barriers; weak transmitted signatures remained, and the classifier used them to separate all 32 states with live calibration. This result is encouraging, but it also makes group-held-out testing essential: a model must recognize openings, not memorize one recording session.

UNO Q allows a more accuracy-oriented search than a small MCU deployment. The planned comparison starts with the compact convolutional baseline, then evaluates approximately 1 M, 5 M, and 10–30 M parameter models, multi-resolution time-frequency features, and two- or three-model ensembles.

Candidate deployment limits are:

- Warm inference p95: **1 second or less**
- Inference application peak RSS: **1.5 GiB or less**
- Complete model package: **500 MiB or less**
- No swap dependency

FP32 is the reference format. FP16 or INT8 will only be accepted if the held-out accuracy is statistically unchanged.

## Display design

The ILI9341 runs in 320×240 landscape orientation. Five tiles represent window a, window b, window c, door AB, and door BC. Green means open, a dark tile means closed, and a vertical bar on the right shows confidence. During measurement, a cyan frame contracts toward the center.

The display code is deliberately small and uses direct SPI commands and RGB565 fills. It does not require a large GUI framework for the bring-up stage.

## Software structure

The project is an Arduino App Lab application with two cooperating parts:

- `sketch/sketch.ino` — MCU state machine, GPIO, I²C, TFT, and Bridge services
- `sketch/ili9341_display.*` — lightweight SPI display driver
- `python/main.py` — Linux controller and current Bridge smoke test
- `pc/` — datasets, feature extraction, training, export, and evaluation tools

The MCU exposes these Bridge services:

- `get_hardware_status`
- `get_physical_state`
- `show_prediction`
- `run_display_self_test`

The Linux application receives `on_infer_request`, runs the inference pipeline, and calls `show_prediction` with the five-bit result and confidence.

## Bring-up procedure

Bring up one subsystem at a time:

1. Connect only the switches and EXEC button. Verify D3–D8 with pull-ups.
2. Connect PCA9685 logic power and I²C, without servo power. Confirm address `0x40`.
3. Connect the ILI9341 and run the red/green/blue/white/black self-test.
4. Join the external 5 V ground to UNO Q ground, then add one servo at a time.
5. Validate MI2S0 voltage, clocks, and Linux routing with a logic analyzer before connecting the microphone and amplifier.
6. Verify chirp playback and 16 kHz mono capture.
7. Compare the Linux feature vector with the reference pipeline using the same WAV file.
8. Enable real model inference only after the feature vectors match.

## Current prototype status

The connected UNO Q has passed the following software bring-up tests:

- STM32U585 sketch compiled and uploaded through the Arduino Zephyr core
- Program size: **25,160 bytes**
- Global RAM: **6,588 bytes**
- Arduino Bridge round-trip completed
- D3–D9 GPIO reads completed
- PCA9685-not-connected handling completed without stopping the app
- ILI9341 initialization, full-screen fill, state rendering, and Bridge display sequence completed
- The App Lab application remains running on the board

The external TFT still needs a visual color/orientation test with the physical display connected. The MI2S0 Device Tree and ALSA routes are the remaining blockers for end-to-end acoustic inference on UNO Q. Until those routes are confirmed, the Linux application clearly labels its returned result as a loopback smoke-test result rather than an AI prediction.

## What I learned

The most useful result is not simply that a classifier can memorize 32 labels. The project shows how strongly active acoustics depends on measurement discipline:

- A repeatable excitation signal matters more than raw model size.
- Baseline handling can turn constant noise from a problem into a removable reference.
- Random train/test splits are not enough; collection session and physical placement must be held out.
- A dual-processor board is a natural fit: deterministic I/O stays on the MCU while the Linux side can prioritize model accuracy.

One speaker, one microphone, and one short ping can reveal much more about a space than their component count suggests.

## Next steps

- Finalize the QRB2210 MI2S0 Device Tree codec configuration.
- Pass simultaneous chirp playback and microphone capture.
- Run the complete 32-state acquisition sequence on UNO Q.
- Train the accuracy-oriented model sweep with group-held-out evaluation.
- Add confidence calibration and an automatic retry when confidence is low.
- Replace the loopback Bridge handler with ONNX Runtime inference.

## Source code and documentation

- Project repository: <https://github.com/airpocket-soundman/IchiPing-UNO-Q>
- UNO Q connection diagram: [`gpio_wiring.html`](gpio_wiring.html)
- Accuracy-first AI strategy: [`uno_q_ai_strategy.html`](uno_q_ai_strategy.html)
