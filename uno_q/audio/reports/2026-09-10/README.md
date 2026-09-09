# Offline analysis snapshots — 2026-09-10 JST

These are the original JSON reports retained from the session. See
[INVESTIGATION.md](../../INVESTIGATION.md) for board identity, software hashes,
wiring, timestamps, user feedback and limitations. Raw microphone recordings
remain local; no ambient audio or private authentication material is published.

- `analysis.json`: 06:02 repeat, mono capture.
- `silence.json`: mono zero-PCM control.
- `stereo-silence.json`: stereo capture, input bias disabled.
- `stereo-silence-pulldown.json`: input pulldown comparison.
- `playback-first-silence.json`: playback-first zero-PCM control.
- `playback-first-tone.json`: S16 tone.
- `playback-first-tone-s24.json`: mismatched low-24-bit trial.
- `playback-first-tone-s32.json`: corrected native-MSB format.
- `warmed-tone-s32.json`: delayed capture with silence padding/fades.
- `reviewed-replay-s32.json`: selected segment preparation and source hash.
- `replay-recapture.json`: first recorded-segment replay recapture.

Tone-detection statistics and the segment's automated gate do NOT constitute
an acoustic quality pass. User reported noise-like output. Final generated-tone
comparison ended the session by agreement, without an explicit clean-sine verdict.
