#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
	echo "usage: $0 BASE_DTB OUTPUT_DTB" >&2
	exit 2
fi

base_dtb=$1
output_dtb=$2
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

dtc -@ -I dts -O dtb \
	-o "$work_dir/ichiping-mi2s0.dtbo" \
	"$script_dir/ichiping-mi2s0.dtso"
fdtoverlay -i "$base_dtb" \
	-o "$output_dtb" \
	"$work_dir/ichiping-mi2s0.dtbo"

fdtget "$output_dtb" / model
fdtget "$output_dtb" /sound model
fdtget "$output_dtb" /sound/ichiping-mi2s0-playback-dai-link link-name
fdtget "$output_dtb" /sound/ichiping-mi2s0-capture-dai-link link-name
