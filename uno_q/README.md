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

## Verified hardware result

On 2026-08-21, USB-connected UNO Q serial `2261748543` compiled and uploaded
the ILI9341 sketch successfully. Program usage is 25,160 bytes and global RAM
usage is 6,588 bytes. Router Bridge returned hardware status `0x01` and
physical state `0b00000`; the ILI9341 command and pixel-write sequence
completed. A visual test still needs the TFT connected. No PCA9685 was
connected, the rain input was inactive, and servo PWM was not enabled.

When the CLI is launched through ADB, set `TMPDIR=/tmp`; ADB otherwise exports
the Android-style `/data/local/tmp`, which does not exist on the UNO Q Debian
image used for this test.
