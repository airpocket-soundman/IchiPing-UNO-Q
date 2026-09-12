# UNO Q speaker-to-microphone loop test — 2026-09-11

- Board: Arduino UNO Q, USB 2341:0078, ADB serial 2261748543.
- Software: kernel 6.16.7-g0dd6551ae96b; q6asm-dai SHA256
  `c4292c7c9504c7aa01a94cd0007b86213def67a1d4a8123dd23be3ff92653526`.
- Connected: INMP441, MAX98357A, speaker, GPIO28 SD control with external 10 kOhm pulldown.
- Format: playback S32_LE stereo and capture S16_LE stereo, 48 kHz.
- Playback: generated 440 Hz, 0.5-second PCM containing 100 ms leading silence,
  300 ms tone and 100 ms trailing silence. Capture duration was 1 second.
- 0.6%FS playback produced left-channel RMS 0.7203%FS and peak 2.0050%FS.
  The best 100 ms window contained 99.9877% 440 Hz power.
- 1.2%FS playback produced left-channel RMS 1.4300%FS and peak 3.9154%FS.
  The best 100 ms window contained 99.9953% 440 Hz power.
- The capture level ratio was 1.985 for a 2x playback-level change. Neither run
  clipped. The right channel was entirely zero, consistent with INMP441 L/R=GND.
- Both runs stopped routes, returned SD_MODE Low, cleared markers, and did not
  reset the board.

Verdict: **PASS** for generated-tone playback to INMP441 capture, channel
selection, linear level response, 440 Hz content and bounded stop. Acoustic
calibration and arbitrary real-world sound quality remain outside this test.

The selected 0.1–0.2 second segment from the 1.2%FS capture had 99.9953% 440 Hz
power and estimated harmonic ratio 0.342%. It was DC-corrected, faded and peak
limited to 0.6%FS for one guarded 0.5-second replay. Source capture SHA256:
`f75e50c34f345b070c828845ad40381f0ebe67d65933eb3ed755a2fba0b62dfd`.
Prepared replay SHA256:
`97dcfb25c18d9a0769c4a16e01ab22f58cf6b8b38f19c2fdbd21099b0ce47ad7`.
