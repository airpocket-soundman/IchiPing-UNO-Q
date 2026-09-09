#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
	echo "run as root" >&2
	exit 1
fi

if [ -f /boot/efi/ichiping/loader.conf.backup ]; then
	cp -p /boot/efi/ichiping/loader.conf.backup /boot/efi/loader/loader.conf
fi
rm -f /boot/efi/loader/entries/ichiping-mi2s0-test*.conf
rm -f /boot/efi/ichiping/qrb2210-arduino-imola-ichiping-mi2s0.dtb
echo "Removed the IchiPing MI2S0 test entry; the stock entry was not changed."
