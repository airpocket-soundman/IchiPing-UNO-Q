#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
	echo "run as root" >&2
	exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
app_dir=${ICHIPING_APP_DIR:-/home/arduino/ArduinoApps/ichiping-uno-q}
serial=${ICHIPING_EXPECTED_USB_SERIAL:?set the verified UNO Q USB serial}
noise_rms=${ICHIPING_NOISE_RMS:?set the reviewed white-noise playback RMS}

case "$serial" in ''|*[!0-9]*) echo "invalid USB serial" >&2; exit 2 ;; esac
python3 - "$noise_rms" <<'PY'
import sys
value = float(sys.argv[1])
if not 0 < value <= 0.10:
    raise SystemExit("ICHIPING_NOISE_RMS must be >0 and <=0.10 FS")
PY

install -d -o arduino -g arduino -m 0750 "$app_dir/runtime/audio/responses" "$app_dir/runtime/audio/captures"
install -d -o root -g root -m 0755 /opt/ichiping/audio
for file in safe-audio-test.sh route-mi2s0.sh audio-smoke-test.py audio-cycle-test.sh white-noise-cycle.sh runtime-audio-worker.py; do
	install -o root -g root -m 0755 "$script_dir/$file" "/opt/ichiping/audio/$file"
done
install -o root -g root -m 0644 "$script_dir/systemd/ichiping-audio-runtime.service" /etc/systemd/system/
install -o root -g root -m 0644 "$script_dir/systemd/ichiping-audio-runtime.path" /etc/systemd/system/
printf 'ICHIPING_APP_DIR=%s\nICHIPING_EXPECTED_USB_SERIAL=%s\nICHIPING_NOISE_RMS=%s\n' \
	"$app_dir" "$serial" "$noise_rms" >/etc/ichiping-audio-runtime.conf
chmod 0600 /etc/ichiping-audio-runtime.conf
printf '{"version":1,"status":"ready","playback_rms_fs":%s}\n' "$noise_rms" \
	>"$app_dir/runtime/audio/worker-ready.json"
chown arduino:arduino "$app_dir/runtime/audio/worker-ready.json"
chmod 0644 "$app_dir/runtime/audio/worker-ready.json"
systemctl daemon-reload
systemctl enable --now ichiping-audio-runtime.path
systemctl is-active --quiet ichiping-audio-runtime.path
echo "IchiPing audio runtime path worker installed; no audio was played"
