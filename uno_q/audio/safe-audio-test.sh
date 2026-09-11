#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
model=$(tr -d '\000' </proc/device-tree/sound/model)
failed=0

case "${1:-}" in
	speaker|cycle|replay-cycle|external-reference|instrument-playback|instrument-duplex) ;;
	microphone)
		echo "refusing capture-only clocks: use ICHIPING_TONE_AMPLITUDE=0 $0 cycle" >&2
		exit 2 ;;
	*) echo "usage: $0 {speaker|cycle|replay-cycle FILE|instrument-playback FILE|instrument-duplex FILE|external-reference ID}" >&2; exit 2 ;;
esac

if [ "$(id -u)" -ne 0 ]; then
	echo "refusing test: run as root so failure can force an immediate reboot" >&2
	exit 1
fi

# Shared route controls and prepared PCM must have a single owner.
exec 9>/run/lock/ichiping-audio-test.lock
flock -n 9 || { echo "refusing concurrent audio test" >&2; exit 1; }

if [ "$model" != "Arduino-Imola-IchiPing-MI2S0" ]; then
	echo "refusing test: unexpected sound card model: $model" >&2
	exit 1
fi

if [ "${1:-}" = external-reference ] || [ "${1:-}" = instrument-playback ] || [ "${1:-}" = instrument-duplex ]; then
	[ "$#" -eq 2 ] || exit 2
	if [ "$1" = external-reference ]; then
		case "$2" in ''|*[!0-9a-f]*) exit 2 ;; esac
		[ "${#2}" -eq 32 ] || exit 2
	fi
	[ "$(cat /sys/kernel/config/usb_gadget/g1/idVendor)" = 0x2341 ] || exit 1
	[ "$(cat /sys/kernel/config/usb_gadget/g1/idProduct)" = 0x0078 ] || exit 1
	[ "$(cat /sys/kernel/config/usb_gadget/g1/strings/0x409/serialnumber)" = "${ICHIPING_EXPECTED_USB_SERIAL:?}" ] || exit 1
	printf 'ICHIPING_BOARD_VERIFIED:%s\n' "$ICHIPING_EXPECTED_USB_SERIAL"
	date -Is
	uname -r
	sha256sum /lib/modules/"$(uname -r)"/kernel/sound/soc/qcom/qdsp6/q6asm-dai.ko
fi

if ! grep -q 'Arduino-Imola-IchiPing-MI2S0' /proc/asound/cards; then
	echo "refusing test: MI2S0 ALSA card is not ready (check DSP/LPASS probe)" >&2
	exit 1
fi

if pgrep -x pipewire >/dev/null 2>&1 || \
	pgrep -x wireplumber >/dev/null 2>&1 || \
	pgrep -x pipewire-pulse >/dev/null 2>&1; then
	echo "refusing test: PipeWire/WirePlumber must be stopped first" >&2
	exit 1
fi

stop_audio() {
	pkill -TERM -x aplay 2>/dev/null || true
	pkill -TERM -x arecord 2>/dev/null || true
	sleep 0.1
	pkill -KILL -x aplay 2>/dev/null || true
	pkill -KILL -x arecord 2>/dev/null || true
	"$script_dir/route-mi2s0.sh" off || failed=1
	"$script_dir/route-mi2s0.sh" verify-off || failed=1
}

emergency_stop() {
	failed=1
	stop_audio
	echo "audio test failed; rebooting immediately to force MI2S clocks off" >&2
	systemctl reboot --force --force
}

"$script_dir/route-mi2s0.sh" off
"$script_dir/route-mi2s0.sh" verify-off
trap 'emergency_stop' HUP INT TERM

if [ "${1:-}" = replay-cycle ] || [ "${1:-}" = instrument-playback ] || [ "${1:-}" = instrument-duplex ]; then
	[ "$#" -eq 2 ] || exit 2
	python3 "$script_dir/audio-smoke-test.py" validate-native-replay --input "$2"
	cp -- "$2" /var/tmp/ichiping-prepared-tone.raw
	export ICHIPING_PLAYBACK_FORMAT=S32_LE
	if [ "$1" = replay-cycle ]; then set -- cycle; fi
elif [ "${1:-}" = external-reference ]; then
	# Shared clocks can activate the amplifier: provide valid ZERO data first.
	python3 "$script_dir/audio-smoke-test.py" prepare-tone --duration 0.5 \
		--amplitude 0 --format S32_LE --output /var/tmp/ichiping-prepared-tone.raw
elif [ "${1:-}" = cycle ]; then
	python3 "$script_dir/audio-smoke-test.py" prepare-tone --duration 0.5 \
		--amplitude "${ICHIPING_TONE_AMPLITUDE:-0.0001}" \
		--format "${ICHIPING_PLAYBACK_FORMAT:-S32_LE}" \
		--lead-silence 0.1 --tail-silence 0.1 --fade 0.005 \
		--output /var/tmp/ichiping-prepared-tone.raw
fi

# Independent of this shell. Direct reboot bypasses service shutdown. This is
# a tested idle reset fallback, not proof of acoustic shutdown under DSP faults.
if [ "${1:-}" = instrument-duplex ]; then
	capture=$(mktemp /var/tmp/ichiping-instrument-duplex-XXXXXX.raw)
	echo "ICHIPING_INSTRUMENT_CAPTURE:$capture"
fi
sync
systemd-run --quiet --unit=ichiping-audio-watchdog \
	--on-active=500ms --timer-property=AccuracySec=1ms \
	/usr/bin/systemctl reboot --force --force

case "${1:-}" in
	instrument-duplex)
		# Unloaded measurement: same verified PCM, then capture after playback RUNNING.
		"$script_dir/route-mi2s0.sh" playback-on
		"$script_dir/route-mi2s0.sh" capture-on
		if ! timeout --signal=TERM --kill-after=0.25 3.5 \
			"$script_dir/audio-cycle-test.sh" "$capture"; then
			emergency_stop
			exit 1
		fi
		;;
	instrument-playback)
		# Measurement-only playback: never open the microphone/capture route.
		# The reference file was validated and copied BEFORE arming the timer.
		"$script_dir/route-mi2s0.sh" playback-on
		if ! timeout --signal=TERM --kill-after=0.25 1 \
			aplay -D hw:0,0 -t raw -f S32_LE -c 2 -r 48000 \
				--period-size=480 --buffer-size=1920 /var/tmp/ichiping-prepared-tone.raw; then
			emergency_stop
			exit 1
		fi
		;;
	external-reference)
		capture=/var/tmp/ichiping-pc-reference-$2.raw
		# Never overwrite an earlier run's evidence.
		[ ! -e "$capture" ] || exit 1
		"$script_dir/route-mi2s0.sh" playback-on
		"$script_dir/route-mi2s0.sh" capture-on
		if ! timeout --signal=TERM --kill-after=0.25 3.5 \
			"$script_dir/external-reference-capture.sh" "$capture" "$2"; then
			emergency_stop
			exit 1
		fi
		;;
	speaker)
		shift
		"$script_dir/route-mi2s0.sh" playback-on
		if ! timeout --signal=TERM --kill-after=0.25 3.5 \
			python3 "$script_dir/audio-smoke-test.py" speaker \
				--duration 0.5 --amplitude 0.0001 "$@"; then
			emergency_stop
			exit 1
		fi
		;;
	cycle)
		shift
		capture=/var/tmp/ichiping-mic-cycle.raw
		rm -f "$capture"
		"$script_dir/route-mi2s0.sh" playback-on
		"$script_dir/route-mi2s0.sh" capture-on
		if ! timeout --signal=TERM --kill-after=0.25 3.5 \
			"$script_dir/audio-cycle-test.sh" "$capture" "$@"; then
			emergency_stop
			exit 1
		fi
		;;
	*)
		echo "usage: $0 {speaker|cycle} [test options]" >&2
		exit 2
		;;
esac

stop_audio
trap - HUP INT TERM
if [ "$failed" -ne 0 ]; then
	echo "audio stop verification failed; rebooting immediately" >&2
	systemctl reboot --force --force
	exit 1
fi

sync
echo "audio transfer finished; requesting direct reset (acoustic stop unverified)"
systemctl reboot --force --force
