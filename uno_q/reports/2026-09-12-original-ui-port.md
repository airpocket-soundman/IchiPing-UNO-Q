# Original IchiPing UI and operation port — 2026-09-12

## Reference selection

The original repository was inspected read-only. It contains two materially
different application UIs:

- `firmware/projects/10_inference/main.c`: landscape 320x240 local UI for five
  state toggles, an EXEC button, servos, and inference.
- `firmware/projects/11_smart_window/main.c`: portrait 240x320 rain/ESP status
  UI without the local toggle/EXEC implementation.

Some original README diagrams describe older layouts and disagree with their
current source. The UNO Q shield has the five toggles and EXEC control, so the
current project 10 source code—not its stale prose—was selected as the UI and
operation reference. The original repository was not modified.

## Ported display contract

- ILI9341 landscape-flip orientation and exact original RGB565 color constants.
- Navy `IchiPing infer` header on a black screen.
- `inf` and `act` five-character rows in physical left-to-right order
  `c, BC, b, AB, a`.
- Before inference and after a physical-state change, `inf` is grey `-----`.
- Correct/incorrect observable inference bits are green/red; non-observable bits
  use dark green/red. Actual bits are orange/dark orange.
- Observability matches the 14-class collapse: a and AB always; b and BC when AB
  is open; c only when AB and BC are open.
- Exact-state match shows a blue `Complete Success` banner; 14-class-only match
  shows green `Conditional Success`; otherwise red `Failure`.
- Results have no fixed timeout. A changed physical state invalidates the prior
  prediction and removes the banner.
- The temporary tile UI, confidence meter, and shrinking-frame animation were
  removed because none exists in the selected original implementation.

The original 5x7 font data was copied into the UNO Q ILI9341 driver so text and
layout do not depend on a new graphics library. While live audio and the room
baseline remain unavailable, EXEC shows `Audio not ready`; it does not present
the physical switch state as a fabricated successful prediction.

## Input and servo operation

The state input polarity was corrected to the original contract: switch to GND
is CLOSE=0, released pull-up is OPEN=1. EXEC remains active-low and triggers on
the press edge.

The original servo sequence is implemented behind an explicit Bridge gate:
`set_servo_automation(1)`. Enabling it closes BC→AB→c→b→a sequentially, then
opens only channels requested by the switches. Later changes move one matching
servo for 500 ms and release PWM. The gate defaults off after every boot, so
software deployment and display testing cannot unexpectedly move the five SG90s.
It was not enabled during this UI deployment.
Until that one-time physical synchronization is enabled, the `act` row reflects
the switch-requested state and must not be treated as proof of servo position.
After synchronization, the two are kept together by the same move path.

Project 11's rain-trigger and ESP-UART behavior is intentionally outside the
UNO Q port scope. D9 remains reserved and does not trigger inference.

## Verification

- Board: Arduino UNO Q, USB serial `2261748543`.
- No-rain UI build/upload at this checkpoint: PASS; program 29,480 bytes,
  global RAM 6,636 bytes. The later safety/runtime integration build is recorded
  in `2026-09-12-implementation-gap-audit.md`.
- App restart: PASS; model loaded and Bridge reported hardware status `0x0b`.
  Reserved bit 2 remained zero.
- Startup input after polarity correction: `0b11111` with all five pull-ups High.
- Dependency-free Python UI/CLI/mailbox contract suite: 9 tests passed.
- Connected: ILI9341, five state inputs, EXEC, PCA9685/servos, audio hardware.
- No servo movement, audio playback, or microphone recording was requested or
  performed during this UI deployment.
