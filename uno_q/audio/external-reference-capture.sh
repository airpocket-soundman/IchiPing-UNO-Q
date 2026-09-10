#!/bin/sh
# Only called by safe-audio-test.sh with its independent reset already armed.
set -eu
[ "$#" -eq 2 ] || exit 2
capture=$1
run_id=$2
systemctl is-active --quiet ichiping-audio-watchdog.timer || exit 1

wait_running() {
	status=$1
	pid=$2
	for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
		grep -q 'state: RUNNING' "$status" && return 0
		kill -0 "$pid" 2>/dev/null || return 1
		sleep 0.005
	done
	return 1
}

aplay -D hw:0,0 -t raw -f S32_LE -c 2 -r 48000 \
	--period-size=480 --buffer-size=1920 /var/tmp/ichiping-prepared-tone.raw &
playback_pid=$!
wait_running /proc/asound/card0/pcm0p/sub0/status "$playback_pid"
sleep 0.10
arecord -D hw:0,1 -t raw -f S16_LE -c 2 -r 48000 \
	--period-size=1920 --buffer-size=15360 -d 1 "$capture" &
capture_pid=$!
wait_running /proc/asound/card0/pcm1c/sub0/status "$capture_pid"
# RUNNING is a handshake, not proof of received acoustic samples or alignment.
printf 'ICHIPING_CAPTURE_READY:%s\n' "$run_id"
wait "$capture_pid"
wait "$playback_pid"
