#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
	echo "run as root" >&2
	exit 1
fi

vid=$(cat /sys/kernel/config/usb_gadget/g1/idVendor 2>/dev/null || true)
pid=$(cat /sys/kernel/config/usb_gadget/g1/idProduct 2>/dev/null || true)
serial=$(cat /sys/kernel/config/usb_gadget/g1/strings/0x409/serialnumber 2>/dev/null || true)
if [ "$vid" != "0x2341" ] || [ "$pid" != "0x0078" ]; then
	echo "refusing install: target is not the expected Arduino UNO Q USB gadget ($vid:$pid)" >&2
	exit 1
fi
if [ -n "${EXPECTED_USB_SERIAL:-}" ] && [ "$serial" != "$EXPECTED_USB_SERIAL" ]; then
	echo "refusing install: USB serial is $serial, expected $EXPECTED_USB_SERIAL" >&2
	exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
kernel=$(uname -r)
machine_id=$(cat /etc/machine-id)
base_dtb=/boot/efi/dtb/qcom/qrb2210-arduino-imola.dtb
install_dir=/boot/efi/ichiping
custom_dtb=$install_dir/qrb2210-arduino-imola-ichiping-mi2s0.dtb
entry=/boot/efi/loader/entries/ichiping-mi2s0-test+1.conf
loader_conf=/boot/efi/loader/loader.conf

set -- /boot/efi/loader/entries/*-"$kernel".conf
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
	echo "could not uniquely identify the current kernel boot entry" >&2
	exit 1
fi
stock_entry=$1

mkdir -p "$install_dir"
"$script_dir/build-overlay.sh" "$base_dtb" "$custom_dtb.tmp"
mv "$custom_dtb.tmp" "$custom_dtb"
cp -p "$stock_entry" "$install_dir/stock-entry-backup.conf"
if [ ! -f "$install_dir/loader.conf.backup" ]; then
	cp -p "$loader_conf" "$install_dir/loader.conf.backup"
fi
sha256sum "$base_dtb" "$custom_dtb" > "$install_dir/SHA256SUMS"

linux_path=$(awk '$1 == "linux" { print $2 }' "$stock_entry")
initrd_path=$(awk '$1 == "initrd" { print $2 }' "$stock_entry")
options=$(sed -n 's/^options[[:space:]]\+//p' "$stock_entry")

rm -f /boot/efi/loader/entries/ichiping-mi2s0-test*.conf
{
	echo "title IchiPing UNO Q MI2S0 test"
	echo "version $kernel-ichiping-mi2s0"
	echo "machine-id $machine_id"
	echo "linux $linux_path"
	echo "initrd $initrd_path"
	echo "devicetree /ichiping/$(basename "$custom_dtb")"
	echo "options $options panic=10"
} > "$entry"

{
	echo "timeout 3"
	echo "default ichiping-mi2s0-test*"
} > "$loader_conf"

echo "Prepared boot-counted MI2S0 test for Arduino UNO Q USB serial $serial"
echo "Stock entry remains unchanged: $stock_entry"
echo "Boot-count fallback has been unreliable on this board; verify the running DT after every reboot."
