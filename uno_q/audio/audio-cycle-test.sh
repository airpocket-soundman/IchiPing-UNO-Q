#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
	echo "usage: $0 CAPTURE_RAW" >&2
	exit 2
fi

capture=$1
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# Establish valid playback data before capture starts shared BCLK/WS.
# The outer wrapper's independent 500 ms reset is mandatory.
aplay -D hw:0,0 -t raw -f "${ICHIPING_PLAYBACK_FORMAT:-S32_LE}" -c 2 -r 48000 \
	--period-size=480 --buffer-size=1920 /var/tmp/ichiping-prepared-tone.raw &
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
# Allow microphone clock startup to settle. This does not extend the outer
# reset deadline and is not proof that an acoustic startup pop was removed.
sleep 0.10
arecord -D hw:0,1 -t raw -f S16_LE -c 2 -r 48000 \
	--period-size=1920 --buffer-size=15360 -d 1 "$capture"
wait "$playback_pid"
echo "capture saved for offline inspection: $capture"
