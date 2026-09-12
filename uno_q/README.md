# IchiPing UNO Q app

`app/` is an Arduino App Lab application for the first IchiPing porting stage.
It verifies the UNO Q MCU/Linux bridge, external ILI9341 SPI TFT, five state
inputs, EXEC input, and PCA9685 address detection. D9 is reserved and unused;
rain detection is not part of this port.

The EXEC software path now covers a bounded privileged white-noise capture,
capture-health checks, center-crop preprocessing, a model-bound live baseline,
ONNX inference, stale-state rejection, and TFT update. The privileged worker is
kept disabled until a reviewed white-noise RMS has been calibrated, so the
currently deployed app still emits no sound and reports `Audio not ready`.

On 2026-09-11, the standalone MI2S0 bring-up passed for both directions. The
MAX98357A produced a clean generated 440 Hz sine and stopped after 0.5 s. The
INMP441 capture contained at least 99.98% 440 Hz energy, tracked a 2x playback
level change by 1.985x, and did not clip. A provisional Neutron-XL model trained
from the 160 tracked representative WAVs scored 30/32 (93.75%) for exact
32-state classification and 32/32 with macro-F1 1.0 after collapse to the 14
observable classes. This is a preliminary small-sample result, not a final
generalization claim.

The packaged ONNX model was also loaded inside the UNO Q app container with
ONNX Runtime 1.30.0. Load time was 194.83 ms; warm inference mean/p95 were
1.394/1.659 ms and measured RSS was 61.8 MiB, within the project budgets.

## Deploy on a USB-connected UNO Q

Push this directory to `/home/arduino/ArduinoApps/ichiping-uno-q`, then run:

```sh
TMPDIR=/tmp arduino-app-cli app start /home/arduino/ArduinoApps/ichiping-uno-q
TMPDIR=/tmp arduino-app-cli app logs /home/arduino/ArduinoApps/ichiping-uno-q --all
```

The original IchiPing 2.4-inch ILI9341 TFT and shield wiring are reused. UNO Q
wiring is `D11=MOSI`, `D13=SCK`, `A2=CS`, `A3=RST`, `A4=DC`, `A5=BL`, `3V3`,
and `GND`; `D12/MISO` is not connected for the write-only driver. The display
now follows the original project 10 implementation: landscape-flip, `inf` and
`act` five-digit rows ordered `c, BC, b, AB, a`, observable/unobservable color
levels, and Complete/Conditional/Failure banners. There is no confidence meter
or TFT ping animation. The onboard LED Matrix is not part of the normal UI.

The bridge also exposes `get_switch_states`: bits 0..4 are window a, window b,
window c, door AB, and door BC; bit 5 is EXEC. For the five state switches, the
original contract is grounded Low=CLOSE(0) and released pull-up High=OPEN(1);
EXEC remains Low=pressed.

Servo bring-up exposes `test_servo_channel(channel)` for a small center sweep
and `move_servo_deg(channel, degrees)` for a raw mechanical angle. Both calls
require an explicit state-matched `set_servo_armed(1, expected_state)` call,
validate the PCA9685, drive only one of channels 0..4, then release PWM. Startup
and every fault path attempt FULL_OFF on all 16 PCA9685 channels. The original
IchiPing implementation currently maps channels 0..4 to `a, b, c, AB, BC` and
uses 180 degrees / tick 553 for closed and 0 degrees / tick 102 for open.

## Verified hardware result

On 2026-08-21, USB-connected UNO Q serial `2261748543` compiled and uploaded
the ILI9341 sketch successfully. Program usage is 25,160 bytes and global RAM
usage is 6,588 bytes. Router Bridge returned hardware status `0x01` and
physical state `0b00000`; the ILI9341 command and pixel-write sequence
completed. A visual test still needs the TFT connected. No PCA9685 was
connected, the rain input was inactive, and servo PWM was not enabled.

On 2026-09-08, the same board (USB serial `2261748543`) was retested with the
ILI9341 and six switches connected. Display, backlight, and all six inputs were
visually confirmed. With USB removed and external 5 V applied, PCA9685 address
0x40 and five SG90 servos on channels 0..4 were tested one at a time. The small
sweep and closed-open-closed endpoint command sequence completed without I2C
errors; PWM was released after every move. Rain and audio remained disconnected.

When the CLI is launched through ADB, set `TMPDIR=/tmp`; ADB otherwise exports
the Android-style `/data/local/tmp`, which does not exist on the UNO Q Debian
image used for this test.

### Retest: 2026-09-08 11:21 JST

The saved on-board LCD header still used CS=D10, RST=A0, DC=A1 and BL=A2.
The earlier test therefore did not establish that A5 was driven. Redeployed
the local CS=A2, RST=A3, DC=A4 and BL=A5 configuration to board `2261748543`.
Compilation, MCU upload and application start succeeded: 25,220 bytes program,
6,588 bytes global RAM. Bridge status was 0x01; the five state inputs initially
read active/Low and EXEC inactive/High. Individual press/release testing and LCD
visual confirmation remain pending. Input changes are now logged every 100 ms.
No servo PWM was enabled. PCA9685 was not detected; rain and audio were not tested.

Wi-Fi connected at 192.168.101.14; gateway, external IP, DNS and HTTPS tests passed.
The requested existing profile was made secondary with autoconnect priority -10,
preserving the other profiles. Credentials are not recorded here.

At 11:26 JST the user confirmed LCD operation. Logs independently confirmed
changes on all six inputs: WIN_A, WIN_B, WIN_C, DOOR_AB, DOOR_BC and EXEC.
EXEC press/release was observed twice. However, at that time the EXEC notification callback
called `show_prediction` synchronously from `Bridge.read_loop` and timed out
after 10 seconds, followed by an unknown-message-ID warning. Thus GPIO input
operation was confirmed, but the complete EXEC-to-result flow had not passed.
On 2026-09-11 the re-entrant call was removed: the Bridge provider now only
enqueues the newest request. On 2026-09-12 the live inference software path was
connected, with worker/baseline readiness gates preventing a fake prediction.

The original toggle-to-servo behavior is implemented behind
`set_servo_automation(1)`. It is deliberately disabled after boot so deploying
or restarting the development app cannot move hardware unexpectedly. Enabling
it performs the original sequential BC→AB→c→b→a close, then synchronizes the
switches requesting OPEN. Each later switch change moves only its corresponding
servo for 500 ms and releases PWM.
Until this one-time physical synchronization succeeds, `act` is shown as
`-----`. Afterward it is the last successfully commanded five-servo endpoint
state, not position-sensor feedback. Switch positions remain a separate request.
