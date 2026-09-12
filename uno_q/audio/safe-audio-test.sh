#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
model=$(tr -d '\000' </proc/device-tree/sound/model)
failed=0
marker=/sys/class/leds/green:user/brightness

case "${1:-}" in
	speaker|cycle|replay-cycle|external-reference|instrument-playback|instrument-duplex|calibrate-noise) ;;
	microphone)
		echo "refusing capture-only clocks: use ICHIPING_TONE_AMPLITUDE=0 $0 cycle" >&2
		exit 2 ;;
	*) echo "usage: $0 {speaker|cycle|replay-cycle FILE|instrument-playback FILE|instrument-duplex FILE|external-reference ID|calibrate-noise ID}" >&2; exit 2 ;;
esac

# Every stop path (aplay/arecord, MI2S routes, user LED marker) is reachable
# without root: the audio group owns the ALSA PCM/control nodes and the gpiod
# group owns the marker.  Root keeps the historical /var/tmp paths used by
# the systemd worker; other users get a private work directory so root-owned
# leftovers never block them and their captures can be deleted after fetch.
if [ "$(id -u)" -eq 0 ]; then
	work=/var/tmp
else
	for group in audio gpiod; do
		id -nG | tr ' ' '\n' | grep -qx "$group" || {
			echo "refusing test: run as root or as a member of audio and gpiod" >&2
			exit 1
		}
	done
	work=/var/tmp/ichiping-audio-$(id -un)
	mkdir -p "$work"
	chmod 700 "$work"
fi
export ICHIPING_AUDIO_WORKDIR="$work"

# Shared route controls must have a single owner across users.  flock works
# on a read-only descriptor, so a lock file created by root still serialises.
lock=/run/lock/ichiping-audio-test.lock
if [ -e "$lock" ] && [ ! -w "$lock" ]; then
	exec 9<"$lock"
else
	exec 9>"$lock"
fi
flock -n 9 || { echo "refusing concurrent audio test" >&2; exit 1; }

if [ "$model" != "Arduino-Imola-IchiPing-MI2S0" ]; then
	echo "refusing test: unexpected sound card model: $model" >&2
	exit 1
fi

if [ "${1:-}" = external-reference ] || [ "${1:-}" = instrument-playback ] || [ "${1:-}" = instrument-duplex ] || [ "${1:-}" = calibrate-noise ]; then
	[ "$#" -eq 2 ] || exit 2
	if [ "$1" = external-reference ] || [ "$1" = calibrate-noise ]; then
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
	printf '0\n' > "$marker" 2>/dev/null || failed=1
}

emergency_stop() {
	failed=1
	stop_audio
	echo "audio test failed; processes, route, SD_MODE and marker were stopped" >&2
}

"$script_dir/route-mi2s0.sh" off
"$script_dir/route-mi2s0.sh" verify-off
[ -w "$marker" ] || { echo "refusing test: UNO Q user LED marker is unavailable" >&2; exit 1; }
printf '0\n' > "$marker"
trap 'emergency_stop; exit 1' HUP INT TERM
trap 'stop_audio' EXIT

if [ "${1:-}" = replay-cycle ] || [ "${1:-}" = instrument-playback ] || [ "${1:-}" = instrument-duplex ]; then
	[ "$#" -eq 2 ] || exit 2
	python3 "$script_dir/audio-smoke-test.py" validate-native-replay --input "$2"
	cp -- "$2" "$work"/ichiping-prepared-tone.raw
	export ICHIPING_PLAYBACK_FORMAT=S32_LE
	if [ "$1" = replay-cycle ]; then set -- cycle; fi
elif [ "${1:-}" = external-reference ]; then
	# Shared clocks can activate the amplifier: provide valid ZERO data first.
	python3 "$script_dir/audio-smoke-test.py" prepare-clock-silence --duration 6.5 \
		--output "$work"/ichiping-prepared-tone.raw
elif [ "${1:-}" = calibrate-noise ]; then
	# white: 5 s noise / 6 s capture.  prbs16k: the original collector's 2 s
	# ±1 PRBS (16 kHz band) inside 3.5 s of clocked PCM, 3 s capture.
	case "${ICHIPING_EXCITATION:-white}" in
		white)
			python3 "$script_dir/audio-smoke-test.py" prepare-white-noise \
				--duration 5 --amplitude "${ICHIPING_NOISE_RMS:-0.003}" \
				--seed "${ICHIPING_NOISE_SEED:-20260911}" \
				--output "$work"/ichiping-calibration-noise.raw
			capture_seconds=6 ;;
		prbs16k)
			# Deterministic PCM is generated once per (amplitude, seed) and
			# reused, so the delay from the caller's servo settle to the
			# noise onset stays constant (generation takes ~1.8 s).
			amplitude=${ICHIPING_PRBS_AMPLITUDE:?set the reviewed PRBS amplitude}
			seed=${ICHIPING_NOISE_SEED:-20260912}
			# Batch mode: N frames back-to-back in one clocked PCM and one
			# continuous capture (split offline at the known frame pitch).
			repeats=${ICHIPING_PRBS_REPEATS:-1}
			gap=${ICHIPING_PRBS_GAP:-0.3}
			case "$amplitude$seed$repeats$gap" in
				''|*[!0-9.]*) echo "refusing test: invalid PRBS parameters" >&2; exit 2 ;;
			esac
			noise_pcm="$work"/ichiping-prbs16k-a$amplitude-s$seed-r$repeats-g$gap.raw
			if [ ! -s "$noise_pcm" ]; then
				python3 "$script_dir/audio-smoke-test.py" prepare-prbs16k \
					--amplitude "$amplitude" --seed "$seed" --repeats "$repeats" \
					--gap "$gap" --output "$noise_pcm.tmp"
				mv "$noise_pcm.tmp" "$noise_pcm"
			fi
			if [ "$repeats" = 1 ]; then
				capture_seconds=3
			else
				# Capture starts after playback RUNNING + 0.1 s and must end
				# before the PCM: stop 0.6 s short of the total duration.
				total=$(awk -v r="$repeats" -v g="$gap" 'BEGIN { print 0.5 + 2.0 * r + g * (r - 1) + 1.0 }')
				export ICHIPING_CAPTURE_FRAMES=$(awk -v t="$total" 'BEGIN { printf "%d", (t - 0.6) * 48000 }')
				capture_timeout=$(awk -v t="$total" 'BEGIN { printf "%d", t + 5 }')
				capture_seconds=0
			fi ;;
		silence)
			# Ambient capture: prbs16k timing with an all-zero PCM, so the
			# speaker stays silent while the microphone records the room.
			repeats=${ICHIPING_PRBS_REPEATS:-1}
			gap=${ICHIPING_PRBS_GAP:-0.3}
			case "$repeats$gap" in
				''|*[!0-9.]*) echo "refusing test: invalid silence parameters" >&2; exit 2 ;;
			esac
			noise_pcm="$work"/ichiping-silence-r$repeats-g$gap.raw
			if [ ! -s "$noise_pcm" ]; then
				python3 "$script_dir/audio-smoke-test.py" prepare-silence \
					--repeats "$repeats" --gap "$gap" --output "$noise_pcm.tmp"
				mv "$noise_pcm.tmp" "$noise_pcm"
			fi
			if [ "$repeats" = 1 ]; then
				capture_seconds=3
			else
				total=$(awk -v r="$repeats" -v g="$gap" 'BEGIN { print 0.5 + 2.0 * r + g * (r - 1) + 1.0 }')
				export ICHIPING_CAPTURE_FRAMES=$(awk -v t="$total" 'BEGIN { printf "%d", (t - 0.6) * 48000 }')
				capture_timeout=$(awk -v t="$total" 'BEGIN { printf "%d", t + 5 }')
				capture_seconds=0
			fi ;;
		chime)
			# Operator call signal: three quiet 880 Hz beeps (fixed level).
			python3 "$script_dir/audio-smoke-test.py" prepare-chime \
				--output "$work"/ichiping-calibration-noise.raw
			capture_seconds=3 ;;
		*) echo "refusing test: unknown ICHIPING_EXCITATION" >&2; exit 2 ;;
	esac
	export ICHIPING_NOISE_PCM="${noise_pcm:-"$work"/ichiping-calibration-noise.raw}"
	# S32_LE keeps all 24 microphone bits for new UNO Q datasets; S16_LE is
	# the previously verified capture path.
	capture_format=${ICHIPING_CAPTURE_FORMAT:-S16_LE}
	case "$capture_format" in
		S16_LE|S32_LE) ;;
		*) echo "refusing test: unknown ICHIPING_CAPTURE_FORMAT" >&2; exit 2 ;;
	esac
elif [ "${1:-}" = cycle ]; then
	python3 "$script_dir/audio-smoke-test.py" prepare-tone --duration 0.5 \
		--amplitude "${ICHIPING_TONE_AMPLITUDE:-0.0001}" \
		--format "${ICHIPING_PLAYBACK_FORMAT:-S32_LE}" \
		--lead-silence 0.1 --tail-silence 0.1 --fade 0.005 \
		--output "$work"/ichiping-prepared-tone.raw
fi

if [ "${1:-}" = instrument-duplex ]; then
	capture=$(mktemp "$work"/ichiping-instrument-duplex-XXXXXX.raw)
	echo "ICHIPING_INSTRUMENT_CAPTURE:$capture"
fi
if ! printf '1\n' > "$marker"; then
	emergency_stop
	exit 1
fi

case "${1:-}" in
	calibrate-noise)
		capture="$work"/ichiping-noise-calibration-$2.raw
		[ ! -e "$capture" ] || { echo "refusing to overwrite $capture" >&2; exit 1; }
		"$script_dir/route-mi2s0.sh" playback-on
		"$script_dir/route-mi2s0.sh" capture-on
		if ! timeout --signal=TERM --kill-after=0.25 "${capture_timeout:-8}" \
			"$script_dir/white-noise-cycle.sh" "$capture" "$capture_seconds" "$capture_format"; then
			emergency_stop
			exit 1
		fi
		echo "ICHIPING_CALIBRATION_CAPTURE:$capture"
		;;
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
				--period-size=480 --buffer-size=1920 "$work"/ichiping-prepared-tone.raw; then
			emergency_stop
			exit 1
		fi
		;;
	external-reference)
		capture="$work"/ichiping-pc-reference-$2.raw
		# Never overwrite an earlier run's evidence.
		[ ! -e "$capture" ] || exit 1
		"$script_dir/route-mi2s0.sh" playback-on
		"$script_dir/route-mi2s0.sh" capture-on
		if ! timeout --signal=TERM --kill-after=0.25 8 \
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
		capture="$work"/ichiping-mic-cycle.raw
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
trap - EXIT HUP INT TERM
if [ "$failed" -ne 0 ]; then
	echo "audio stop verification failed" >&2
	exit 1
fi

sync
echo "audio transfer finished; route off, SD_MODE Low, marker off; no reset requested"
