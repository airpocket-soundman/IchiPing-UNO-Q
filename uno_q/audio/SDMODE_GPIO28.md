# MAX98357A SD_MODE control — GPIO28

Status: wired and electrically verified with the amplifier connected and speaker
disconnected on 2026-09-11. The GPIO-controlled Device Tree is running on test
board `2261748543`. Acoustic quality is still not tested or accepted.

## Selected signal

- UNO Breakout Carrier JMISC physical pin 51, labelled `SOC_GPIO_28`.
- Linux `gpiochip1` (`500000.pinctrl`) line 28; QRB2210 1.8 V logic.
- Do not confuse this with physical header number 28 (`EAR_P_R`) or an Arduino
  digital pin. The carrier's printed signal label must be `28` in the SoC GPIO
  bank beside GPIO18/82/86, corresponding to JMISC pin 51 in the official pinout.
- Live inspection found GPIO28 mux and GPIO ownership unclaimed before testing.
  Unloaded and amplifier-loaded scope tests observed Low/High and return to Low.
  See `reports/2026-09-11-gpio28.md`.

## Required fail-safe wiring

With all power off:

1. Add **10 kOhm from MAX98357A breakout SD to common GND**.
2. Connect GPIO28 to the same SD node.
3. Keep the breakout's existing `105` (1 MOhm) component unchanged.
4. Keep amplifier VIN=5 V and UNO Q/amp grounds common.

The 10 kOhm resistor is mandatory for this design. A direct GPIO-to-SD wire is
not considered reset-safe. Never connect GPIO28 to 5 V or 3.3 V. Do not use a
speaker output terminal as GND.

The breakout is treated as Adafruit 3006-equivalent: 1 MOhm from SD to VIN,
and the MAX98357A contains nominal 100 kOhm SD pulldown. With the GPIO high-Z,
the added 10 kOhm dominates. At worst for this estimate (VIN=5.5 V, internal
pulldown=108 kOhm, ideal 1 MOhm pullup), SD is about 0.050 V, below the
manufacturer's minimum B0 trip point of 0.08 V. Thus shutdown does not depend
on Linux having probed the GPIO. Confirm the actual unpowered voltage before
connecting a speaker; this calculation is not a measurement.

With GPIO28 driven High, the intended SD level is the 1.8 V rail, above the B2
maximum trip point of 1.5 V (left channel). GPIO load from 10 kOhm plus the
internal pulldown is approximately 0.2 mA. The source PCM is currently identical
on left/right, but the selected left-channel mode is still recorded explicitly.
The amplifier VDD=5 V is greater than VDDIO=1.8 V, satisfying the data-sheet
condition for a push-pull High without the extra series resistor mentioned for
VDD lower than VDDIO. Loaded High measured about 1.78–1.80 V (p10–p90).

## Linux implementation

`ichiping-mi2s0.dtso` contains this in the MAX98357A node:

```dts
sdmode-gpios = <&tlmm 28 0>; /* active high */
sdmode-delay = <8>;          /* milliseconds */
```

The kernel driver requests this descriptor as `GPIOD_OUT_LOW`, sets it High on
PCM START after `sdmode-delay`, and sets it Low on STOP/SUSPEND/PAUSE. Eight
milliseconds exceeds the amplifier's typical 7–7.5 ms turn-on time and gives
I2S clocks time to appear before enable. This value and the actual trigger order
must be verified on SD and WS/BCLK; the property alone is not proof of ordering.

It was built on board serial `2261748543` against
`/boot/efi/dtb/qcom/qrb2210-arduino-imola.dtb` and installed as a distinct test
DTB; the stock DTB was not overwritten. `fdtoverlay` succeeded; `fdtget` reported the GPIO
specifier as phandle/line/flags `1a 1c 0` (line `0x1c` = 28, active-high flags
0) and delay 8. Test DTB SHA256:
`6c2b0982545f9005bd85acd85a154dd6a2503ab976c6dd4e9e3d7a4882cef7cc`.
After reboot, `/proc/device-tree/ichiping-max98357a/` contained both properties
and `gpioinfo` reported line 28 as output with `consumer=sdmode`.

## Acceptance sequence

1. Power off: measure resistance SD-to-GND; verify no short and nominal 10 kOhm
   behavior while accounting for parallel parts.
2. Power amp only, GPIO not driven: SD must remain below 0.08 V including boot.
3. UNO Q on, no audio: SD remains Low after driver probe and route changes off.
4. No amp/speaker: CH1=SD and CH2=WS, then CH1=SD and CH2=BCLK. Confirm I2S is
   stable before SD rises, and SD falls before WS can stop while BCLK remains.
5. Amp connected, speaker disconnected: repeat at the amplifier pins and verify
   SD Low/High and I2S logic thresholds under load.
6. Only after all prior gates pass, connect the speaker and perform zero PCM,
   then the bounded low-level sine test. Any persistent sound is an immediate
   stop condition.

### 2026-09-11 wired Low verification

User reported the microphone and amplifier connected, with SD connected to
GPIO28 and pulled down as specified. No audio process was running and the ALSA
card was present. With GPIO28 first read Low and then explicitly held as an
input with bias disabled, the digital read remained 0. Settled CH1 measurements
at the SD/GPIO28 node were approximately 0.04–0.06 V on the 5 V full-range API
setting (x10/DC, 1 MS/s). This is below the 0.08 V minimum B0 trip point, but the
scope is not traceably calibrated; it is a test result, not a replacement for
the external resistor. No speaker-output test was made in this Low-only gate.

### 2026-09-11 loaded High and PCM start/stop verification

With the amplifier connected, external 10 kOhm pulldown present, and speaker
explicitly disconnected, a bounded GPIO request measured SD p10–p90 at
1.78–1.80 V. Explicit cleanup and the driver-owned idle state measured 0–0.04 V.

The GPIO-controlled test DT was then booted and all-zero 48 kHz stereo S32_LE
PCM was opened with the existing pre-route 500 ms reset request. A 250 kS/s
capture measured WS activity approximately 0.484 ms before SD reached High.
The driver's configured 8 ms delay precedes its GPIO write, but the first
externally visible WS edge need not coincide with the CPU trigger callback.
Therefore the 0.484 ms result is the relevant measured clock-to-enable margin,
not evidence that the DT property was ignored.

A 2.5 kS/s continuous capture measured an SD High interval of approximately
515.6 ms. SD returned Low in the same 0.4 ms sample interval as the final
observed WS activity and stayed Low after reset. At this sample rate WS is
severely aliased, so it proves only activity/cessation and must not be used for
WS frequency or fine edge ordering. Raw local captures are intentionally ignored
by Git; the numerical verdict is recorded in `reports/2026-09-11-gpio28.md`.

## Sources

- MAX98357A/B data sheet Rev 7: SD trip points B0 0.08–0.355 V,
  B1 0.65–0.825 V, B2 1.245–1.5 V; internal pulldown 92–108 kOhm;
  push-pull/open-drain application diagrams; do not remove LRCLK with BCLK.
- Adafruit mono breakout guide: board has 1 MOhm SD-to-VIN and defaults to
  `(L+R)/2` at 5 V.
- Arduino UNO Breakout Carrier full pinout, revision 2026-03-03: JMISC pin 51 is
  `SOC_GPIO_28`, and SoC/MPU pins are 1.8 V only.
- Arduino linux-qcom `max98357a.c` at commit
  `0dd6551ae96b78024086e72339fefbef6fcc604b`.
