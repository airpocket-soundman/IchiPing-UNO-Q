# IchiPing UNO Q bring-up app

`app/` is an Arduino App Lab application for the first IchiPing porting stage.
It verifies the UNO Q MCU/Linux bridge, external ILI9341 SPI TFT, five state
inputs, EXEC input, rain input, and PCA9685 address detection.

The current Python result is explicitly a loopback result. It does not claim
that the acoustic model is running yet.

## Deploy on a USB-connected UNO Q

Push this directory to `/home/arduino/ArduinoApps/ichiping-uno-q`, then run:

```sh
TMPDIR=/tmp arduino-app-cli app start /home/arduino/ArduinoApps/ichiping-uno-q
TMPDIR=/tmp arduino-app-cli app logs /home/arduino/ArduinoApps/ichiping-uno-q --all
```

The original IchiPing 2.4-inch ILI9341 TFT and shield wiring are reused. UNO Q
wiring is `D11=MOSI`, `D13=SCK`, `A2=CS`, `A3=RST`, `A4=DC`, `A5=BL`, `3V3`,
and `GND`; `D12/MISO` is not connected for the write-only driver. Five tiles are
ordered `a, b, c, AB, BC`, followed by a confidence meter. The onboard LED
Matrix is not used.

The bridge also exposes `get_switch_states`: bits 0..4 are window a, window b,
window c, door AB, and door BC; bit 5 is EXEC. A set bit means the active-low
input is asserted.

Servo bring-up exposes `test_servo_channel(channel)` for a small center sweep
and `move_servo_deg(channel, degrees)` for a raw mechanical angle. Both calls
validate the PCA9685, drive only one channel, then release PWM. The original
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
EXEC press/release was observed twice. However, the EXEC notification callback
called `show_prediction` synchronously from `Bridge.read_loop` and timed out
after 10 seconds, followed by an unknown-message-ID warning. Thus GPIO input
operation is confirmed, but the complete EXEC-to-result flow has not passed.
