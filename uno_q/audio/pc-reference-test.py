#!/usr/bin/env python3
"""Windows reference speaker -> UNO Q mic. Default is OFFLINE PREPARATION ONLY."""
import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import queue
import re
import shlex
import struct
import subprocess
import sys
import threading
import time
import uuid
import wave

ROOT = Path(__file__).resolve().parent
RATE = 48000
DURATION = .1
AMPLITUDE = .0001
FREQUENCY = 440
PRE_ROLL = .030


def timing_check(data):
    """Conservative tone-envelope check, not a sound quality or clock calibration."""
    samples = [pair[0] / 32768 for pair in struct.iter_unpack('<hh', data)]
    size, hop = 1200, 240  # 25 ms = exactly 11 cycles of the 440 Hz reference.
    windows = []
    for start in range(0, len(samples)-size+1, hop):
        segment = samples[start:start+size]
        dc = sum(segment) / size
        re = sum((v-dc)*math.cos(2*math.pi*FREQUENCY*i/RATE) for i, v in enumerate(segment))
        im = sum((v-dc)*math.sin(2*math.pi*FREQUENCY*i/RATE) for i, v in enumerate(segment))
        windows.append((start/RATE, 2*(re*re+im*im)/(size*size)))
    if len(windows) < 5:
        return {'status': 'insufficient capture; timing NOT established'}
    powers = sorted(power for start, power in windows)
    floor = powers[max(0, len(powers)//5)]
    peak = powers[-1]
    if peak <= max(1e-14, floor*4):
        return {'status': 'no distinct reference envelope; timing NOT established'}
    active = [start for start, power in windows if power >= max(peak*.1, floor*4)]
    first, last = active[0], active[-1]+size/RATE
    duration = len(samples)/RATE
    contained = first >= .010 and duration-last >= .010
    return {'status': 'candidate reference has margins; review required' if contained else
            'reference may be truncated; timing NOT established',
            'candidate_start_seconds': first, 'candidate_end_seconds': last,
            'capture_seconds': duration, 'pre_margin_seconds': first,
            'post_margin_seconds': duration-last}


def reference_pcm():
    samples = []
    for i in range(round(RATE * DURATION)):
        envelope = min(1, i / 240, (RATE * DURATION - 1 - i) / 240)
        samples.append(round(32767 * AMPLITUDE * envelope * math.sin(2*math.pi*FREQUENCY*i/RATE)))
    return b''.join(struct.pack('<hh', v, v) for v in samples)


def write_wav(path, data, channels):
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(data)


def run_checked(command, **kwargs):
    return subprocess.run(command, check=True, timeout=15, capture_output=True, **kwargs)


def wait_ready(events, run_id, timeout=8):
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('No matching capture-ready handshake; PC sound NOT started')
        try:
            line = events.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError('No capture-ready handshake; PC sound NOT started') from None
        if line is None:
            raise RuntimeError('SSH ended before capture-ready; PC sound NOT started')
        if line.strip() == 'ICHIPING_CAPTURE_READY:' + run_id:
            return


def play_child(wav_path):
    # Only the explicitly launched child imports Windows audio APIs.
    import winsound
    with wave.open(str(wav_path), 'rb') as wav:
        duration = wav.getnframes() / wav.getframerate()
        if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (RATE, 2, 2):
            raise ValueError('unexpected playback format')
        data = wav.readframes(wav.getnframes())
    if not 0 < duration <= DURATION or any(abs(v[0]) > 3 for v in struct.iter_unpack('<h', data)):
        raise ValueError('PC reference exceeds duration/peak limit')
    try:
        winsound.PlaySound(str(wav_path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        time.sleep(duration + .025)
    finally:
        winsound.PlaySound(None, 0)


def execute(args, output, run_id, report):
    if sys.platform != 'win32':
        raise RuntimeError('Live PC playback requires Windows')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@-]*', args.host):
        raise ValueError('invalid SSH host')
    if not re.fullmatch(r'[A-Za-z0-9]+', args.serial):
        raise ValueError('invalid serial')
    key = args.key.resolve()
    if not key.is_file():
        raise FileNotFoundError('SSH private key not found')
    ssh = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', '-i', str(key), args.host]
    scp = ['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', '-i', str(key)]
    # No credentials are placed in command arguments, environment, files or logs.
    password = getpass.getpass('UNO Q sudo password (not saved): ')
    run_checked(ssh + ['sudo -S -p "" -v'], input=(password+'\n').encode())
    remote = '/var/tmp/ichiping-pc-reference-' + run_id
    run_checked(ssh + ['mkdir -m 700 ' + remote])
    files = ['safe-audio-test.sh', 'route-mi2s0.sh', 'audio-smoke-test.py', 'external-reference-capture.sh']
    run_checked(scp + [str(ROOT / f) for f in files] + [args.host + ':' + remote + '/'])
    run_checked(ssh + ['chmod 755 ' + remote + '/*.sh'])
    command = ('sudo -S -p "" env ICHIPING_EXPECTED_USB_SERIAL=' + shlex.quote(args.serial) +
               ' sh ' + remote + '/safe-audio-test.sh external-reference ' + run_id)
    proc = subprocess.Popen(ssh + [command], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    events = queue.Queue()
    def read_lines():
        for line in proc.stdout:
            # Defensive redaction; sudo's password itself should never be echoed.
            line = line.replace(password, '[REDACTED]') if password else line
            report['board_log'].append(line.rstrip())
            events.put(line)
        events.put(None)
    reader = threading.Thread(target=read_lines, daemon=True)
    reader.start()
    try:
        proc.stdin.write(password + '\n')
        proc.stdin.flush()
        proc.stdin.close()
        wait_ready(events, run_id)
        report['capture_ready_host_monotonic'] = time.monotonic()
        # Capture starts first; command receipt is not the acoustic onset.
        time.sleep(PRE_ROLL)
        # Parent timeout kills the player if its own finally block hangs.
        report['pc_play_requested_host_monotonic'] = time.monotonic()
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--play-child',
                        str(output / 'reference.wav')], check=True, timeout=.5)
        report['pc_play_finished_host_monotonic'] = time.monotonic()
    finally:
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
        reader.join(timeout=1)
    # Reboot disconnect is expected, but does not constitute an acoustic pass.
    deadline = time.monotonic() + 120
    raw = output / 'capture-stereo-s16.raw'
    while time.monotonic() < deadline:
        try:
            run_checked(scp + [args.host + ':/var/tmp/ichiping-pc-reference-' + run_id + '.raw', str(raw)])
            break
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            time.sleep(2)
    else:
        raise TimeoutError('Unable to retrieve this run; no earlier capture substituted')
    data = raw.read_bytes()
    if not data or len(data) % 4:
        raise ValueError('empty or truncated stereo frames')
    write_wav(output / 'capture-stereo.wav', data, 2)
    left = b''.join(struct.pack('<h', pair[0]) for pair in struct.iter_unpack('<hh', data))
    write_wav(output / 'capture-left.wav', left, 1)
    spec = importlib.util.spec_from_file_location('capture_analysis', ROOT / 'analyze-capture.py')
    analyzer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzer)
    report['capture_analysis'] = analyzer.inspect(data, channels=2)
    report['timing_check'] = timing_check(data)
    report['capture_sha256'] = hashlib.sha256(data).hexdigest()
    report['status'] = 'captured; acoustic quality and reference overlap UNVERIFIED'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Explicitly deploy, arm board reset, play PC sound and record')
    parser.add_argument('--host', default='airpocket@192.168.50.160')
    parser.add_argument('--serial', default='2261748543')
    parser.add_argument('--key', type=Path, default=ROOT.parent / 'test_ssh/unoq_test_ed25519')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--play-child', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.play_child:
        play_child(args.play_child)
        return
    run_id = uuid.uuid4().hex
    output = args.output or ROOT / 'local-runs' / run_id
    output.mkdir(parents=True, exist_ok=False)
    write_wav(output / 'reference.wav', reference_pcm(), 2)
    report = {'run_id': run_id, 'created_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'prepared only; NO sound/SSH/board access',
              'reference_hz': FREQUENCY, 'reference_seconds': DURATION,
              'pre_roll_after_ready_seconds': PRE_ROLL,
              'reference_peak_fs': 3/32768, 'host': args.host, 'expected_serial': args.serial,
              'board_log': [], 'limitations': ['PC output uses current Windows default device and volume',
              'SSH/audio latency is not synchronized; overlap requires offline validation',
              'Board zero PCM is not a hardware amplifier mute',
              '500 ms software reset deadline is not a measured acoustic guarantee']}
    try:
        if args.execute:
            execute(args, output, run_id, report)
    except BaseException as exc:
        report['status'] = 'failed: ' + type(exc).__name__
        raise
    finally:
        (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(output.resolve())


if __name__ == '__main__':
    main()
