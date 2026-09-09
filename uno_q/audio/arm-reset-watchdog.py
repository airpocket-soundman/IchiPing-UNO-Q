#!/usr/bin/env python3
"""Arm a hardware reset; deliberately never feed it. Test board only."""
import array
import fcntl
import os
import signal
import time

WDIOC_SETTIMEOUT = 0xC0045706
WDIOC_GETTIMEOUT = 0x80045707

def main():
    if os.geteuid() != 0:
        raise SystemExit("root required")
    identity = open('/sys/class/watchdog/watchdog0/identity').read().strip()
    if identity != 'qcom_wdt':
        raise SystemExit(f'unexpected watchdog: {identity}')
    os.sync()
    fd = os.open('/dev/watchdog0', os.O_WRONLY | os.O_CLOEXEC)
    try:
        interval = array.array('i', [2])
        fcntl.ioctl(fd, WDIOC_SETTIMEOUT, interval, True)
        fcntl.ioctl(fd, WDIOC_GETTIMEOUT, interval, True)
        if interval[0] != 2:
            raise RuntimeError(f'unsupported reset interval: {interval[0]}')
    except BaseException:
        os.write(fd, b'V')
        os.close(fd)
        raise
    for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal.SIG_IGN)
    print('HARDWARE RESET ARMED: 2 seconds; no audio started', flush=True)
    while True:
        time.sleep(0.1)

if __name__ == '__main__':
    main()
