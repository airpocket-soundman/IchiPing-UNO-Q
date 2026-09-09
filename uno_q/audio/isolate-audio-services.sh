#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
	echo "run as root" >&2
	exit 1
fi

units="pipewire.service pipewire.socket pipewire-pulse.service pipewire-pulse.socket wireplumber.service"

case "${1:-}" in
	prepare)
		systemctl --global mask $units
		for uid in 103 1001; do
			if [ -d "/run/user/$uid" ]; then
				user=$(getent passwd "$uid" | cut -d: -f1)
				[ -n "$user" ] || continue
				runuser -u "$user" -- env XDG_RUNTIME_DIR="/run/user/$uid" \
					systemctl --user stop $units 2>/dev/null || true
			fi
		done
		pkill -TERM -x pipewire 2>/dev/null || true
		pkill -TERM -x pipewire-pulse 2>/dev/null || true
		pkill -TERM -x wireplumber 2>/dev/null || true
		sleep 0.5
		if pgrep -x pipewire >/dev/null 2>&1 || \
			pgrep -x pipewire-pulse >/dev/null 2>&1 || \
			pgrep -x wireplumber >/dev/null 2>&1; then
			echo "audio services are still running" >&2
			exit 1
		fi
		;;
	restore)
		systemctl --global unmask $units
		for uid in 103 1001; do
			if [ -d "/run/user/$uid" ]; then
				user=$(getent passwd "$uid" | cut -d: -f1)
				[ -n "$user" ] || continue
				runuser -u "$user" -- env XDG_RUNTIME_DIR="/run/user/$uid" \
					systemctl --user start pipewire.socket pipewire-pulse.socket wireplumber.service \
					2>/dev/null || true
			fi
		done
		;;
	*)
		echo "usage: $0 {prepare|restore}" >&2
		exit 2
		;;
esac
