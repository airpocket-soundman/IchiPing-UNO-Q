# Audio failure investigation — 2026-09-09 JST

## Repeat — 2026-09-10 06:02:28 JST

Same UNO Q USB 2341:0078 / 2261748543, machine-id
3e660e15577e4d88ad85a3673a183368, kernel 6.16.7-g0dd6551ae96b,
clock-stop module SHA256 d483125499439612381e56ac0c9a1bafe433f1680de528d546f16177dc3a507a.
No wiring changes; microphone/amplifier connected, rain sensor unconfirmed.
440 Hz, 0.01%FS, 0.5-second S16_LE stereo playback with 1-second S16_LE
mono capture; independent 2-second direct-reset timer armed before routing.
Both transfers completed and reset returned with boot ID
9ef10ea2-c019-44ff-b117-9660a419da56. User confirmed sound stopped but was
heavily contaminated with noise. Stop observed for this trial; exact acoustic
duration not measured. Sound quality FAIL; no general stop guarantee inferred.

Recovered 96000 bytes / 48000 frames. RMS 2.7271%FS (previous 2.3911%),
peak 24.9481%FS (previous 20.4468%), DC -0.4999%FS, zero clipped samples.
440 Hz power fraction over 100 ms windows: 0.039–2.241%. This reproduces
the noisy recording, not clean sine playback. No recording replay performed.
Artifacts: C:/Users/yamas/AppData/Local/Temp/ichiping-audio-analysis-20260910/.

All audible trials so far FAILED: user heard noisy/distorted output, including
sound persisting after PCM completion. Captures are now available, but the
microphone path itself is not independently validated.
An ALSA successful return is not an acoustic pass. PipeWire isolation did not
resolve the failure, so competition with PipeWire is not an established cause.

## Evidence and changes

- Arduino kernel commit `0dd6551ae96b78024086e72339fefbef6fcc604b`:
  `q6asm-dai.c` exposes S16_LE/S24_LE, not S32_LE. Backend S32_LE does not mean
  that frontend S32_LE is supported. The attempted S32_LE trial was invalid.
- Capture requires 6720-byte periods, eight periods. S16_LE stereo therefore
  uses period_size=1680 and buffer_size=13440 frames. Format/channel negotiation
  errors alone do not establish that the INMP441 requires mono frontend audio.
- Primary MI2S startup enabled IBIT at 3072000 Hz, while the earlier machine
  patch returned from shutdown without disabling it. The new, separately built
  `sm8250-primary-clock-stop.patch` counts active primary streams and requests
  zero frequency after the last one closes. Clock/fmt startup errors propagate.
  Patch application and build passed; this module has NOT been deployed or
  acoustically verified. Module.symvers was absent during build (CONFIG_MODVERSIONS
  is disabled); build warnings are not proof of load compatibility.
- New test PCM is S16_LE at 48 kHz stereo with explicit period/buffer parameters.
  At 0.01%FS the 16-bit sine has a peak of only three integer counts, so it is
  heavily quantized. This is a diagnostic format, not a high fidelity reference.
- Generated tone and prepared replay are capped at 0.5 seconds. Capture is saved
  for offline analysis and is not automatically replayed. `analyze-capture.py`
  reports per-channel DC, RMS, peak, clipping, and 440 Hz energy in 100 ms windows.
  Those statistics do not by themselves prove microphone or speaker correctness.
- A no-audio hardware reset probe on USB identity 2341:0078 / 2261748543,
  machine-id 3e660e15577e4d88ad85a3673a183368, kernel 6.16.7-g0dd6551ae96b,
  around 23:00 JST accepted qcom_wdt timeout=2 but did not show a reboot within
  that interval. A pretimeout event appeared and later SSH became unavailable.
  Reset timing FAILED/UNVERIFIED. Do not use this as a proven output cutoff.
  No peripherals were disconnected by the agent; rain sensor connection remains
  unconfirmed. Before this probe audio card initialization was deferred because
  LPASS could not acquire its audio clock. Verify boot and card readiness first.

## Primary references

- [Arduino kernel](https://github.com/arduino/linux-qcom/tree/qcom-v6.16.7-unoq)
- [TDK INMP441 datasheet](https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/inmp441.pdf):
  SD is high impedance outside its 24-bit slot; a 100 kohm external pulldown is
  specified. Internal LPASS pulldown is a diagnostic comparison, not verification
  that the external resistor requirement has been electrically met.
- [Adafruit Linux setup](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/raspberry-pi-usage):
  uses ALSA and also discusses idle silence to reduce start/stop pops. Raspberry
  Pi configuration is not a drop-in UNO Q configuration.
- [Analog Devices clock-stop FAQ](https://ez.analog.com/audio/a/documents/do11587/dc-output-on-speaker-for-max98357):
  removing LRCLK with BCLK running can leave DC at the output; SD shutdown is
  recommended before stopping LRCLK. This supports investigating clock shutdown,
  but does not establish the measured cause of our noise.
- [Arduino Media Carrier](https://docs.arduino.cc/resources/datasheets/ASX00083-datasheet.pdf):
  MI2S0 pins are 1.8 V. Its analog playback examples do not validate this external
  MAX98357A/INMP441 MI2S0 implementation.

## Follow-up — approximately 23:07 JST

The additional 480-frame period alignment in q6asm_dai_open makes stereo
capture impossible with 6720-byte periods: S16 stereo needs 1680 frames, which
is not divisible by 480. S16 mono uses 3360 frames and meets both constraints.
The earlier 1680-frame candidate failed and has been replaced by mono capture.

An idle systemd 500 ms timer with `systemctl reboot --force --force` recorded
timer/service starts in the same second and changed boot ID. This validates
an idle reset only, not an exact acoustic cutoff under faults. The test wrapper
now arms a separate 2-second direct-reset timer before enabling routes.

The clock-stop module was installed, rebooted and hash-verified:
`d483125499439612381e56ac0c9a1bafe433f1680de528d546f16177dc3a507a`.
Same board identity/kernel and connections as above. PipeWire remained masked.
The 0.5-second S16 stereo tone plus 1-second S16 mono capture completed and
the direct reset executed. The board returned with boot ID
`f686b14e-5235-4bce-b96f-536bf758db1a` and 96000 bytes of capture persisted.

Offline measured capture: 48000 frames, RMS=2.3911%FS, peak=20.4468%FS,
DC=-0.5253%FS, zero clipped samples. The 440 Hz power fraction in 100 ms
windows is 0.00098–0.01731, insufficient to classify this as a clean sine.
The first half has substantial energy around 3.5 kHz. The second half includes
a 440 Hz line amid broadband energy. Transport completion is not acoustic
success; speaker distortion and capture artifacts are not yet separated.
No captured audio has been replayed. User confirmation of audible stopping
and sound quality for this particular trial is pending.

Raw capture and JSON analysis were retained locally under
`C:/Users/yamas/AppData/Local/Temp/ichiping-audio-analysis-20260909/`.
Next: compare capture against an independent sound reference and examine the
stereo slots (requires resolving the frontend period constraint); do not
normalize and replay noise as if it were a valid microphone recording.

## Autonomous diagnosis — 2026-09-10 06:26:50 JST

Same board/kernel/wiring as the 06:02 trial; rain sensor still unconfirmed.
Zero-data mono control before the period patch gave RMS 3.0946%FS and peak
26.7731%FS. Zero PCM does not eliminate the captured noise; sine generation alone
cannot explain it. This does not distinguish acoustic noise from capture errors.

Installed q6asm-dai with 7680-byte fixed capture periods (stock 6720 cannot
meet stereo and 480-frame constraints simultaneously). Module SHA256
5b46c2c1295896bc0b9f678a18e94adddccf9e43614bbace939a7b44f641771f;
stock backup SHA256
4cfdfec9657cfe52581614b8a09f4095bd574fd499650d212dcb909f1f950a00.
An orderly reboot temporarily left LPASS audio-clock acquisition deferred;
direct reset restored the card. Module loaded without reported symbol errors.

Changed independent reset deadline from 2 s to 500 ms BEFORE enabling routes.
This covers capture-clock activation, not just generated tone. A zero-data
stereo test recovered 86016 bytes / 21504 frames / 0.448 s of partial capture;
reset returned with boot ID cdd8b846-26bd-42e5-89c9-09cc03ac7ec8.
Actual acoustic stop duration is not instrumentally measured.
Left RMS 11.5992%FS, peak 60.1471%; right RMS 1.9598%, peak 25%; no clipping.
Right samples are predominantly zero or negative powers of two (-512, -1024,
-64, etc.), consistent with a floating-slot hypothesis, but not proof.
Signal quality FAIL. Artifacts: stereo-silence.raw/json in the Sep10 local folder.

For the next comparison only DATA0 input bias changes from disabled to pulldown.
New DTB SHA256 d31628f403aa6ac8ca4b1bc5aee40e4f24daf7e5a4ad040b6fa571bd353c4492.
Old DTB retained as /boot/efi/ichiping/backup/mi2s0-bias-disable.dtb.
No amplifier SD wiring change, and no captured data replayed.

At 06:30:17 JST, pulldown comparison recovered another 0.448 s stereo capture.
Unused right channel became exactly zero in every sample (previous RMS 1.9598%).
Left remained noisy: RMS 10.7740%FS, peak 59.8236%. This is a specific improvement
in the unused slot, NOT an acoustic pass. Artifacts: stereo-silence-pulldown.*.

At 06:31:59 JST a playback-first attempt was aborted before recording because
the 100 ms RUNNING-state wait expired during Python preparation. Error handling
killed playback and directly reset; no capture or quality verdict for that test.
Tone data is now prepared before the reset timer/routes; the cycle starts aplay
first, checks RUNNING, then starts capture. The independent 500 ms deadline
is unchanged. Offline regression tests cover stereo analysis, invalid data,
duration/amplitude rejection, zero control, and peak-three-count tone generation.

At 06:33 JST the next boot had no ALSA card / no APR child devices despite an
active apr_audio_svc rpmsg device. Pre-route amixer failed; no audio enabled.
Unbind/rebind of the APR rpmsg driver did not recover it and produced a duplicate
device (-EEXIST) warning. Do not adopt this as recovery; a direct reset followed.

At 06:35:19 JST playback-first zero PCM reached RUNNING before capture opened.
Recovered 77824 bytes / 19456 stereo frames / 0.405333 s. Left overall RMS
0.5853%FS, peak 5.3162%; first 100 ms has a transient, but subsequent 100 ms
AC RMS windows are 0.02496%, 0.01981%, 0.02007%FS. Right remains exactly zero.
This is a large improvement over capture-first (about 10%FS noise), supporting
startup ordering as a major contributor. It does not yet validate sine fidelity
or eliminate startup transients. Artifact: playback-first-silence.*.
At 06:36:31 JST the intended tone trial was refused by the new preflight because
the next boot again lacked an ALSA card. No audio started; direct reset followed.

At approximately 06:38 JST an additional boot still lacked APR children. With
no ALSA card and no active audio, stopping then starting remoteproc1 (verified
name=adsp) restored msm/adsp/audio_pd notifications, all four APR service devices,
and the ALSA card. This is a single successful idle recovery, not an emergency
audio cutoff. Unlike unbinding only the APR driver, this did recover the DSP
service discovery. The subsequent tone comparison began at 06:38:10 JST.

At 06:38:10 JST S16 playback-first tone was captured for 0.405333 s. Left
440 Hz power fractions in 100-200/200-300/300-400 ms windows were 17.55%,
32.69%, 35.82%; right zero. Harmonic peaks 2-8 relative to fundamental over
200-400 ms give about 1.49% (noise-contaminated estimate, not calibrated THD).
This detects the tone; low SNR and the startup transient prevent a clean-audio
pass or replay approval. Artifact: playback-first-tone.*.

At 06:40:29 JST an equal nominal S24_LE low-24-bit test yielded almost no
440 Hz (0.018-0.173% power), despite successful PCM transfer. Artifact:
playback-first-tone-s24.*. A source-level explanation was found in Qualcomm's
[public APR header](https://android.googlesource.com/kernel/msm-extra/+/48696dd1a1e9bf42b32045253819137717020aa2/include/dsp/apr_audio-v2.h):
ASM_MEDIA_FMT_MULTI_CHANNEL_PCM_V2 expects the MOST significant 24 bits in a
32-bit word, contrary to ALSA S24_LE's low-24-bit layout. The running q6asm driver
advertised S24_LE without converting its DMA data. This is a concrete format
mismatch; exact audible impact remains to be measured.

q6asm-native-s32.patch replaces the misleading S24_LE advertisement with S32_LE,
marks 24 significant bits, and still tells the DSP to use its native 24-bit
precision. No DSP API or physical backend change. Generator packs 24-bit samples
into the top bits of a signed 32-bit word, retaining 0.01% normalized full scale.
Do not send these words as S24_LE or to the old driver. Build still has missing
Module.symvers warnings; vermagic and the new msbits symbol checked before install.

Native-S32 module SHA256:
c4292c7c9504c7aa01a94cd0007b86213def67a1d4a8123dd23be3ff92653526.
At 06:45:01 JST the native-S32 0.01%FS tone recovered 440 Hz at approximately
the S16 level, with steady 440 Hz fractions 56.57% and 47.83%. This supports
the alignment correction. Right channel zero. Artifact: playback-first-tone-s32.*.

At 06:47:59 JST added 100 ms leading/trailing silence, 5 ms fades (300 ms active
tone inside a 500 ms file), and delayed capture by 100 ms after playback RUNNING.
The independent reset remains 500 ms BEFORE routing, not after this wait.
Recovered 0.298667 s / 57344 bytes. Left peak 0.1068%FS, RMS 0.02281%FS;
large transient absent from this delayed recording. This does not prove there
was no acoustic transient during the unrecorded warmup. Right all zero.
Central 100-200 ms: 440 Hz fraction 68.26%, harmonics 2-8 ratio estimate 1.36%,
no clipping; 440 Hz is the strongest spectral line. Low-frequency background
noise remains. Artifact: warmed-tone-s32.*.

That central segment passed an explicit replay gate: right slot zero, peak
under 0.2%FS, 440 Hz fraction at least 60%, harmonic estimate below 5%.
prepare-reviewed-replay.py removes DC, reduces peak to 0.0099897%FS, applies
5 ms fades, and pads 100 ms leading / 300 ms trailing silence. It uses the
actual recorded samples, no sine resynthesis or frequency filtering. Source
SHA256 1c82b4bcd6468f8efecc4e1442e96563dbdc9ef7e8fc048063d6d367f432c788.
Replay trial started at 06:51:20 JST, same board/modules/wiring, via guarded
replay-cycle. Nonzero recorded audio is at most 100 ms. Nine offline tests pass.

User feedback after these trials: still only noise-like sound, not a clean sine.
Acoustic quality remains FAIL; spectral tone detection and a selected-segment
replay gate must not be described as successful clean sine playback.

At 06:54:27 JST, at the user's explicit request, repeated the identical reviewed
recorded segment (SHA256 ba1bde7f0f16f4f08255dc57c77b1c93ecec037e50dcda68d0f0c5d1a8dd4b57).
Same board USB 2341:0078 / 2261748543 and native-S32 module, unchanged wiring.
Idle ADSP stop/start first restored the missing ALSA card; no audio active during
recovery. Replay-cycle validated the 0.01%FS cap and zero padding, started playback
and capture with the independent 500 ms direct reset armed. Nonzero source 100 ms.
This repetition is not an acoustic pass. Rain sensor connection still unconfirmed.

At 06:55:37 JST the user requested a generated tone under the same conditions,
not the recorded samples. Generated fresh 440 Hz S32/native-24 PCM: 100 ms
active span with 5 ms fades, 100 ms leading and 300 ms trailing zeros, peak
838/8388608 = 0.0099897%FS (same peak ceiling as the prior recorded replay).
File SHA256 9d0d3d1464f6b9795d965e6f5292a72908909ada0d3da2197be748ef3c169fac.
The existing prevalidated-file wrapper (named replay-cycle) played this NEW
GENERATED file, not any microphone recording. Same 500 ms reset deadline,
same UNO Q 2341:0078 / 2261748543, kernel/modules/wiring unchanged.
Playback/capture started; acoustic quality not inferred from transfer success.
Rain sensor connection remains unconfirmed.

## Session close / repository handoff

Subsequent local-only development (2026-09-10): added PC-reference playback /
UNO Q capture orchestration at the user's request, explicitly without sounding
either device. No SSH, hardware deployment, reset or capture was performed for
this development. Added 30 ms pre-roll after capture-ready and a post-capture
440 Hz envelope margin check to account for command-to-sound latency. The board
500 ms reset deadline is unchanged; incomplete overlap is not a success. See
PC_REFERENCE.md for the amplifier-zero-data limitation and future live workflow.
Offline tests use mocked playback only; hardware identity/results from earlier
experiments must not be attributed to this new, untested workflow.

The 06:51 replay recapture retained 0.32 s: left peak 0.0610%FS, RMS 0.01508%FS,
440 Hz fraction 7.14% in the first 100 ms, then 0.156% and 0.081%; right zero.
Boot ID after that reset: 9c9b660c-d834-45a1-98fe-9be9f11f3f61.
This is evidence of a brief detected component, not proof of pleasant or clean
sound. The user explicitly reported hearing only noise-like sound.

After the final 06:55 generated-tone comparison the user said "OK" and asked
to stop work. Record this as agreement to stop, not an explicit clean-sine pass.
No further hardware tests were performed for the commit/push request.
Original analysis JSON reports are archived in reports/2026-09-10/; raw audio
and private SSH key remain local. App integration, reliable boot recovery,
calibrated acoustic quality, and measured hard stop timing remain unfinished.

## 2026-09-10 instrument follow-up / handoff

Later unloaded OWON measurements confirmed approximately 3.072 MHz BCLK,
48 kHz WS and 64 clocks per frame. A 339-bit DIN subsequence matched the source;
subsequent WS/DIN capture matched nine frames under standard I2S timing assumptions.
These short digital captures do not establish full-stream or acoustic correctness.
See reports/2026-09-10-owon-din.md for limitations and board/software identifiers.
SLogic CLI release 1.1.0 is ready, but normal USB3 enumeration remains unsuccessful.
DFU (359f:30f1, WinUSB, ProblemCode 0) works on the current hub. No firmware update
was performed. User will try another PC; see reports/2026-09-10-slogic-usb.md.
