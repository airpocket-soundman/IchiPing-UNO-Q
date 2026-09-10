# UNO Q MI2S0 Linux bring-up

This directory adds the IchiPing INMP441 microphone and MAX98357A amplifier to
the QRB2210 primary MI2S backend. It targets Arduino's
`qcom-v6.16.7-unoq` kernel at commit
`0dd6551ae96b78024086e72339fefbef6fcc604b`.

The MAX98357A breakout is treated as Adafruit product 3006-equivalent: its SD
pin is left open and the breakout's SD bias enables the amplifier. The Device
Tree intentionally declares no `sdmode-gpios` property.

## Wiring

| Function | UNO Q / J15 / JMISC | Endpoint |
|---|---|---|
| BCLK | GPIO98 / 32 / 46 | INMP441 SCK + MAX98357A BCLK |
| WS | GPIO99 / 34 / 48 | INMP441 WS + MAX98357A LRC |
| Capture DATA0 | GPIO100 / 36 / 50 | INMP441 SD |
| Playback DATA1 | GPIO101 / 38 / 52 | MAX98357A DIN |
| Logic supply | 1.8 V | INMP441 VDD |
| Amplifier supply | 5 V | MAX98357A VIN |

INMP441 L/R and MAX98357A GAIN are tied to GND. Grounds are common. These four
MI2S signals are 1.8 V only.
GAIN tied directly to GND selects **12 dB**, not 3 dB, on MAX98357A.
The copied FRDM wiring notes describe this incorrectly; they are reference
material, not the UNO Q audio specification. See the manufacturer's
[gain application note](https://www.analog.com/en/resources/design-notes/optimize-cost-size-and-performance-with-max98357-wlp.html).
Do not infer output safety from the GAIN=GND connection.

## Files

- [INSTRUMENT_TEST.md](INSTRUMENT_TEST.md): unloaded → amplifier → microphone
  measurement sequence, offline reference generator and I2S CSV decoder.
  `instrument-playback` is a serial-checked playback-only test mode using the
  existing 500ms reset request. One unloaded zero-PCM trial was run on 2026-09-10;
  OWON single triggering did not complete, so no waveform verdict is available.
  ALSA card enumeration failed after reset. OWON API compensation capture and CSV
  export now work, but voltage is inconsistent across ranges; see
  [API report](reports/2026-09-10-owon-api.md). Subsequent armed API captures measured
  GPIO98 at approximately 3.072 MHz. Triggering on GPIO99 then captured ~48 kHz WS,
  with 64 BCLK edges per WS cycle; earlier BCLK-triggered windows missed WS startup. See the
  [unloaded I2S report](reports/2026-09-10-owon-i2s.md). Acoustic quality is not established.
  [DIN capture](reports/2026-09-10-owon-din.md) matches 339 bits of the transmitted PCM
  as a subsequence; WS-relative framing and acoustic quality remain unverified.

- [PC_REFERENCE.md](PC_REFERENCE.md): Windows PC reference playback with UNO Q
  recording handshake, pre-roll and offline timing checks. Preparation is the
  default; live deployment/playback requires explicit `--execute`. Not hardware-tested.

- `ichiping-mi2s0.dtso` adds the LPASS pinmux, primary MI2S RX/TX DAIs,
  MAX98357A playback codec and a capture-only stub DAI for the INMP441.
- `sm8250-primary-mi2s-duplex.patch` makes the QRB2210 machine driver configure
  primary capture for 48 kHz, stereo, S32_LE and a 3.072 MHz bit clock.
- `Dockerfile.kernel-build` provides the native and AArch64 compilers needed to
  build the patched module against Arduino's exact kernel source and config.
- `install-test-boot.sh` creates a separate boot-counted systemd-boot entry. It
  never overwrites the stock DTB or stock boot entry. The `+1` entry is eligible
  for one attempt in principle, but fallback has NOT worked reliably on this
  board. Check the actual running DT; do not rely on automatic fallback.
- `route-mi2s0.sh` controls playback and capture independently; there is no
  command that enables both routes together.
- `safe-audio-test.sh` checks the actual ALSA card and starts with both routes off.
  The cycle enables both directions; standalone probes enable the requested one.
  Signals and detected transfer failures stop processes/routes and request reset.
  The independent reset remains armed if an unexpected shell exit bypasses cleanup.

The overlay can be validated without changing boot state:

```sh
./build-overlay.sh \
  /boot/efi/dtb/qcom/qrb2210-arduino-imola.dtb \
  /tmp/qrb2210-arduino-imola-ichiping.dtb
```

Install a one-shot test boot only after building/installing the patched
`snd-soc-sm8250.ko` for the exact running kernel:

```sh
sudo EXPECTED_USB_SERIAL=2261748543 ./install-test-boot.sh
sudo reboot
```

After reboot, verify the card and links before enabling routes:

```sh
cat /proc/device-tree/sound/model
aplay -l
arecord -l
./route-mi2s0.sh status
./safe-audio-test.sh speaker
```

The stock ALSA frontend advertises S16_LE/S24_LE, but DSP PCM v2 expects
24-bit samples in the TOP of a 32-bit word, not ALSA S24_LE's low bits.
`q6asm-native-s32.patch` replaces S24_LE with S32_LE (24 significant MSBs);
DSP precision remains 24. Apply this low-context patch with `git apply --unidiff-zero`
after the capture-period patch. Tests using S32_LE require this exact patched
driver; do not merely shift data and send it as S24_LE. S16_LE remains supported.
The Qualcomm backend patch forces 48 kHz, two channels and S32_LE on the wire.
`q6asm-capture-period.patch` changes fixed
capture periods from 6720 to 7680 bytes to satisfy the additional 480-frame
alignment for stereo. The cycle test uses stereo period_size=1920 and
buffer_size=15360; the standalone mono probe uses 3840/30720. Both require the
patched q6asm-dai module. Stereo acoustic validation is pending.
The smoke test defaults to a 0.01%
full-scale, 440 Hz sine for 0.5 seconds. It rejects durations above 0.5 seconds
and amplitudes above 0.1%. This limits generated PCM duration only: audible
shutdown is still unverified after observed persistent noise, even with routes
off. Do not treat the software reset timer as a verified acoustic stop guarantee.
`safe-audio-test.sh` requests route shutdown on normal completion and handled errors.
The independent direct-reset timer is now 500 ms from BEFORE route enable,
including capture clocks, not 2 seconds. Reset may interrupt capture and leave
partial data; collect and label that data as partial. This is a software
deadline, not a measured hard real-time acoustic guarantee.

All audible tests remain FAILED. See [INVESTIGATION.md](INVESTIGATION.md) for
evidence, candidate clock-stop patch, and reset limitations. The offline
`analyze-capture.py` never plays audio. `arm-reset-watchdog.py` is an experimental
reset-only probe, not an approved audio cutoff. At 0.01%FS S16_LE has only three
peak counts; its quantization must be considered in spectral analysis.

The current cycle prepares S32_LE/native-24 PCM before enabling any route,
starts playback first, checks RUNNING, waits 100 ms, then opens stereo S16 capture.
Its 500 ms file has 100 ms leading/trailing silence and 5 ms fades, leaving a
300 ms tone. Capture-only mode is refused because starting shared clocks without
valid playback data reproduced loud noise. For a silent control use
`sudo ICHIPING_TONE_AMPLITUDE=0 ./safe-audio-test.sh cycle`.
The outer reset timer still starts before routing and is never extended.
