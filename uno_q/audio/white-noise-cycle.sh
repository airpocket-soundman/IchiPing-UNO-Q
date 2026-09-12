#!/bin/sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 3 ]; then
	echo "usage: $0 CAPTURE_RAW [CAPTURE_SECONDS] [S16_LE|S32_LE]" >&2
	exit 2
fi

capture=$1
capture_seconds=${2:-6}
capture_format=${3:-S16_LE}
case "$capture_seconds" in
	3|6) length="-d $capture_seconds" ;;
	0)
		# Batch PRBS: exact frame count supplied by safe-audio-test.sh.
		case "${ICHIPING_CAPTURE_FRAMES:-}" in
			''|*[!0-9]*) echo "capture frames must be set for batch capture" >&2; exit 2 ;;
		esac
		length="-s $ICHIPING_CAPTURE_FRAMES" ;;
	*) echo "capture seconds must be 3 (prbs16k), 6 (white) or 0 (batch)" >&2; exit 2 ;;
esac
# The patched q6asm capture period is fixed at 7680 bytes: 1920 stereo S16
# frames or 960 stereo S32 frames (24 significant MSBs, native DSP layout).
case "$capture_format" in
	S16_LE) period=1920; buffer=15360 ;;
	S32_LE) period=960; buffer=7680 ;;
	*) echo "capture format must be S16_LE or S32_LE" >&2; exit 2 ;;
esac

# white PCM: 0.5 s silence, 5.0 s noise, 1.0 s silence; 6 s capture, center
# two seconds analysed.  prbs16k PCM: 0.5 s silence, 2.0 s PRBS, 1.0 s
# silence; 3 s capture, the 2 s frame is aligned to the PRBS onset offline.
# Capture starts after playback is RUNNING and always ends before the PCM.
aplay -D hw:0,0 -t raw -f S32_LE -c 2 -r 48000 \
	--period-size=480 --buffer-size=1920 \
	"${ICHIPING_NOISE_PCM:-${ICHIPING_AUDIO_WORKDIR:-/var/tmp}/ichiping-calibration-noise.raw}" &
playback_pid=$!
ready=0
for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
	if grep -q 'state: RUNNING' /proc/asound/card0/pcm0p/sub0/status; then
		ready=1
		break
	fi
	kill -0 "$playback_pid" 2>/dev/null || break
	sleep 0.01
done
if [ "$ready" -ne 1 ]; then
	echo "playback did not reach RUNNING; refusing capture" >&2
	exit 1
fi
sleep 0.10
arecord -D hw:0,1 -t raw -f "$capture_format" -c 2 -r 48000 \
	--period-size="$period" --buffer-size="$buffer" $length "$capture"
wait "$playback_pid"
echo "calibration capture saved for offline inspection: $capture"
