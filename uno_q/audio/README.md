# UNO Q MI2S0 Linux bring-up

This directory adds the IchiPing INMP441 microphone and MAX98357A amplifier to
the QRB2210 primary MI2S backend. It targets Arduino's
`qcom-v6.16.7-unoq` kernel at commit
`0dd6551ae96b78024086e72339fefbef6fcc604b`.

The MAX98357A is treated as Adafruit product 3006-equivalent. Its SD node is
controlled by 1.8 V GPIO28 and has a mandatory external 10 kOhm pulldown to GND.
The running test Device Tree declares `sdmode-gpios` and an 8 ms delay. Loaded
Low/High and bounded PCM start/stop were electrically verified with the speaker
disconnected. A subsequent bounded generated-tone test passed by user listening. See
[SDMODE_GPIO28.md](SDMODE_GPIO28.md).

## Wiring

| Function | UNO Q / J15 / JMISC | Endpoint |
|---|---|---|
| BCLK | GPIO98 / 32 / 46 | INMP441 SCK + MAX98357A BCLK |
| WS | GPIO99 / 34 / 48 | INMP441 WS + MAX98357A LRC |
| Capture DATA0 | GPIO100 / 36 / 50 | INMP441 SD |
| Playback DATA1 | GPIO101 / 38 / 52 | MAX98357A DIN |
| Logic supply | 1.8 V | INMP441 VDD |
| Amplifier supply | 5 V | MAX98357A VIN |
| Amplifier shutdown | GPIO28 / JMISC 51 | MAX98357A SD + external 10 kOhm to GND |

INMP441 L/R and MAX98357A GAIN are tied to GND. Grounds are common. These four
MI2S signals are 1.8 V only.
GAIN tied directly to GND selects **12 dB**, not 3 dB, on MAX98357A.
The copied FRDM wiring notes describe this incorrectly; they are reference
material, not the UNO Q audio specification. See the manufacturer's
[gain application note](https://www.analog.com/en/resources/design-notes/optimize-cost-size-and-performance-with-max98357-wlp.html).
Do not infer output safety from the GAIN=GND connection.

## Files

- **Next environment:** [scope-only handoff and experiment plan](HANDOFF_SCOPE_TEST.md).
  Amplifier/microphone tests will run on another setup with an oscilloscope but
  no logic analyzer. Includes a two-channel scope sequence and explicit safety
  gates. SD/start-stop control is implemented and electrically verified, but it
  is not an acoustic fix. Raw local captures are not included by Git pull.

- [GPIO28 SD_MODE control](SDMODE_GPIO28.md): specifies the required 10 kOhm
  fail-safe pulldown, Device Tree properties, and staged scope acceptance
  sequence. Loaded Low/High and driver-controlled start/stop passed with the
  speaker disconnected. Do not connect a speaker until the remaining documented
  gate and bounded low-level test are ready.

- [2026-09-11 signal audit](reports/2026-09-11-i2s-signal-audit.md): unloaded,
  playback-only S32 test measured 3.072 MHz BCLK / 48 kHz WS and exact agreement
  with 24,000 reference samples per channel, including negative values. This is
  not an acoustic pass. BCLK continued for 1.2–1.4 ms after the last WS edge,
  matching the manufacturer's warning condition for an enabled MAX98357A.
  Reconsider always-enabled/open SD for this implementation before reconnecting
  the amplifier. No SD wiring or driver changes were made by this audit.
  Use explicit `logic_channels=4` and no trigger for the validated SLogic capture
  configuration; the earlier 16-channel/triggered acquisition had artifacts.
  `slogic-sr-to-csv.py` converts sample indices from SR files directly (numpy).
  The subsequent unloaded `instrument-duplex FILE` trial also matched all
  reference PCM samples. It uses a unique recording file. The earlier reset-timer
  measurements remain historical evidence; routine tests no longer force reboot.
  See the audit for Windows capture warnings and an ADSP initialization failure.

- [INSTRUMENT_TEST.md](INSTRUMENT_TEST.md): unloaded → amplifier → microphone
  measurement sequence, offline reference generator and I2S CSV decoder.
  `instrument-playback` is a serial-checked playback-only test mode. One unloaded
  zero-PCM trial was run on 2026-09-10;
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
  Signals, detected transfer failures, and unexpected shell exit stop processes,
  routes, SD_MODE and the diagnostic LED. Routine tests do not reboot the board.

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
full-scale, 440 Hz sine for 0.5 seconds. After the SD hardware cutoff passed,
the diagnostic ceiling was raised to 1.2%FS; it still rejects durations above
0.5 seconds and amplitudes above 1.2%. The green user LED marks the bounded
audio test and is cleared by every normal/error stop path. The onboard LED
Matrix is not used by the production app.
This limits generated PCM duration only: audible
shutdown was historically unverified after observed persistent noise. GPIO28
SD_MODE now provides the measured cutoff: `safe-audio-test.sh` kills transfers,
turns routes off, verifies route state and clears its marker on normal completion,
signals, handled errors and shell exit. After bounded 0.5-second tests repeatedly
stopped cleanly, the user authorized removal of the forced-reboot safeguard on
2026-09-11. A test failure must still leave SD_MODE Low before another attempt.

Generated 440 Hz speaker playback passed user listening at 0.3%FS and again at
0.6%FS on 2026-09-11; both stopped after 0.5 seconds without a board reset. This
was followed by a speaker-to-INMP441 capture test at 0.6%FS and 1.2%FS. The
recorded level scaled 1.985x for a 2x stimulus change, the best windows contained
more than 99.98% 440 Hz power, and neither clipped. A reviewed segment was then
replayed at 0.6%FS. See
[reports/2026-09-11-speaker-pass.md](reports/2026-09-11-speaker-pass.md) and
[reports/2026-09-11-microphone-pass.md](reports/2026-09-11-microphone-pass.md) and
[INVESTIGATION.md](INVESTIGATION.md) for the evidence and earlier failures. The offline
`analyze-capture.py` never plays audio. `arm-reset-watchdog.py` is an experimental
reset-only probe, not an approved audio cutoff. At 0.01%FS S16_LE has only three
peak counts; its quantization must be considered in spectral analysis.

The current cycle prepares S32_LE/native-24 PCM before enabling any route,
starts playback first, checks RUNNING, waits 100 ms, then opens stereo S16 capture.
Its 500 ms file has 100 ms leading/trailing silence and 5 ms fades, leaving a
300 ms tone. Capture-only mode is refused because starting shared clocks without
valid playback data reproduced loud noise. For a silent control use
`sudo ICHIPING_TONE_AMPLITUDE=0 ./safe-audio-test.sh cycle`.
The generated playback duration remains capped at 0.5 seconds; there is no
routine forced reboot after the 2026-09-11 SD_MODE acceptance.

## White-noise level calibration

The model-calibration path is separate from the 0.5-second diagnostic tone cap.
It emits exactly five seconds of deterministic white noise inside a 6.5-second
clocked file, records for six seconds, and uses the stable center two seconds for
analysis. Run exactly one level, stop, inspect it, and only then select the next
level. The initial level is 0.3%FS RMS and the analyzer permits at most a 2x
increase per run, capped at 10%FS RMS.

No sound is emitted by preparation or analysis. A live run requires the same
serial identity gate as instrument tests:

```sh
sudo ICHIPING_EXPECTED_USB_SERIAL=2261748543 \
  ICHIPING_NOISE_RMS=0.003 ./safe-audio-test.sh calibrate-noise RUN_ID_32_HEX
python3 analyze-white-noise-calibration.py CAPTURE.raw \
  --playback-rms 0.003 --output report.json
```

The target is 18–19%FS RMS in the recorded center crop with peak below 90%FS,
matching the tracked training subset. This target is a recording-level target,
not permission to jump directly to a high speaker level.
