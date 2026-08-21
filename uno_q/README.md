# IchiPing UNO Q bring-up app

`app/` is an Arduino App Lab application for the first IchiPing porting stage.
It verifies the UNO Q MCU/Linux bridge, onboard 8×13 LED Matrix, five state
inputs, EXEC input, rain input, and PCA9685 address detection.

The current Python result is explicitly a loopback result. It does not claim
that the acoustic model is running yet.

## Deploy on a USB-connected UNO Q

Push this directory to `/home/arduino/ArduinoApps/ichiping-uno-q`, then run:

```sh
TMPDIR=/tmp arduino-app-cli app start /home/arduino/ArduinoApps/ichiping-uno-q
TMPDIR=/tmp arduino-app-cli app logs /home/arduino/ArduinoApps/ichiping-uno-q --all
```

The LED Matrix uses five two-column cells, ordered `a, b, c, AB, BC` from
left to right. Bright cells mean open; dim cells mean closed. The rightmost
column is the confidence meter. A spreading diamond is the active ping/infer
animation.

## Verified hardware result

On 2026-08-21, USB-connected UNO Q serial `2261748543` compiled and uploaded
the sketch successfully. Program usage was 23,680 bytes and global RAM usage
was 6,068 bytes. Router Bridge returned hardware status `0x01` and physical
state `0b00000`; the smoke-test call sequence completed. This means the Matrix
API initialized, no PCA9685 was connected, and the rain input was inactive.
Servo PWM was not enabled.

When the CLI is launched through ADB, set `TMPDIR=/tmp`; ADB otherwise exports
the Android-style `/data/local/tmp`, which does not exist on the UNO Q Debian
image used for this test.
