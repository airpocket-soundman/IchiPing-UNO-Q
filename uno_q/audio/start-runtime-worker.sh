#!/bin/sh
# Start the IchiPing runtime audio worker at boot (user crontab: @reboot).
# Runs as the arduino user (audio + gpiod groups, no sudo).  A worker-ready.json
# left over from before a power cut is removed first so the app never talks
# to a dead worker.
set -eu
APP=/home/arduino/ArduinoApps/ichiping-uno-q
SPOOL=$APP/runtime/audio
LOG=/var/tmp/ichiping-worker.log
cd /home/arduino/ichiping-audio
if pgrep -f '[r]untime-audio-worker.py' >/dev/null; then
    exit 0
fi
mkdir -p "$SPOOL"
rm -f "$SPOOL/worker-ready.json"
exec python3 runtime-audio-worker.py --spool "$SPOOL" \
    --safe-script /home/arduino/ichiping-audio/safe-audio-test.sh \
    --serial 2261748543 --playback-rms 0.0088 --excitation prbs16k \
    --capture-format S32_LE --loop >"$LOG" 2>&1 </dev/null
