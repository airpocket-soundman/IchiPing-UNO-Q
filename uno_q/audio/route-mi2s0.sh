#!/bin/sh
set -eu

case "${1:-}" in
	playback-on)
		amixer -q cset name='PRI_MI2S_RX Audio Mixer MultiMedia1' on
		;;
	playback-off)
		amixer -q cset name='PRI_MI2S_RX Audio Mixer MultiMedia1' off
		;;
	capture-on)
		amixer -q cset name='MultiMedia2 Mixer PRI_MI2S_TX' on
		;;
	capture-off)
		amixer -q cset name='MultiMedia2 Mixer PRI_MI2S_TX' off
		;;
	off)
		amixer -q cset name='PRI_MI2S_RX Audio Mixer MultiMedia1' off
		amixer -q cset name='MultiMedia2 Mixer PRI_MI2S_TX' off
		;;
	status)
		amixer cget name='PRI_MI2S_RX Audio Mixer MultiMedia1'
		amixer cget name='MultiMedia2 Mixer PRI_MI2S_TX'
		;;
	verify-off)
		status=$(
			amixer cget name='PRI_MI2S_RX Audio Mixer MultiMedia1'
			amixer cget name='MultiMedia2 Mixer PRI_MI2S_TX'
		)
		count=$(printf '%s\n' "$status" | grep -c ': values=off' || true)
		if [ "$count" -ne 2 ]; then
			printf '%s\n' "$status" >&2
			echo "MI2S0 routes did not stop" >&2
			exit 1
		fi
		;;
	*)
		echo "usage: $0 {playback-on|playback-off|capture-on|capture-off|off|status|verify-off}" >&2
		exit 2
		;;
esac
