"""Collect UNO Q PRBS evaluation captures over the 32 servo states.

usage: python pc/uno_q_collect.py OUT_DIR [--rounds 3] [--baseline 3] [--amplitude 0.0088]
                          [--format S16_LE] [--states 0,1,...]
Each shot: eval set_state -> settle -> root calibrate-noise (prbs16k) -> scp raw.
Raw captures and one JSONL record per shot are kept; inference is offline.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import time
import uuid
from pathlib import Path

HOST = "arduino@192.168.50.160"
KEY = str(Path.home() / ".ssh" / "airpocket_ed25519")
SSH = ["ssh", "-i", KEY, "-o", "BatchMode=yes", HOST]
EVAL = "/home/arduino/ArduinoApps/ichiping-uno-q/runtime/eval"
SERIAL = "2261748543"
# User-owned copy of uno_q/audio: runs without sudo (audio + gpiod groups).
AUDIO = "/home/arduino/ichiping-audio/safe-audio-test.sh"
WORK = "/var/tmp/ichiping-audio-arduino"


def ssh(command: str, timeout: float = 60) -> str:
    done = subprocess.run(SSH + [command], capture_output=True, text=True, timeout=timeout)
    if done.returncode != 0:
        raise RuntimeError(f"ssh failed rc={done.returncode}: {done.stdout[-400:]} {done.stderr[-400:]}")
    return done.stdout


def eval_command(op: str, state: int = 0) -> dict:
    cid = uuid.uuid4().hex
    out = ssh(
        f"mkdir -p {EVAL} && printf '{{\"id\":\"{cid}\",\"op\":\"{op}\",\"state\":{state}}}\\n' > {EVAL}/.cmd.tmp"
        f" && mv {EVAL}/.cmd.tmp {EVAL}/command.json && for i in $(seq 1 300); do"
        f" if [ -f {EVAL}/result-{cid}.json ]; then cat {EVAL}/result-{cid}.json; rm -f {EVAL}/result-{cid}.json; exit 0; fi;"
        f" sleep 0.1; done; echo TIMEOUT; exit 1")
    result = json.loads(out.strip().splitlines()[-1])
    if result.get("status") != "ok":
        raise RuntimeError(f"eval {op} failed: {result}")
    return result


def state_and_shot(state: int, amplitude: float, capture_format: str, settle: float,
                   repeats: int = 1, gap: float = 0.3, excitation: str = "prbs16k") -> dict:
    """One SSH round trip: servo command, fixed settle, then the capture.

    Servos move one at a time (500 ms MCU hold each); the app publishes the
    result after the LAST servo stopped.  The capture starts exactly
    ``settle`` seconds later, and its cached PCM has 0.5 s of silence before
    the noise, so every shot has the same servo-stop -> noise delay.
    """
    cid, run_id = uuid.uuid4().hex, uuid.uuid4().hex
    out = ssh(
        f"E={EVAL}; t0=$(date +%s.%N);"
        f" printf '{{\"id\":\"{cid}\",\"op\":\"set_state\",\"state\":{state}}}\\n' > $E/.cmd.tmp && mv $E/.cmd.tmp $E/command.json;"
        f" ts=none; for i in $(seq 1 500); do if [ -f $E/result-{cid}.json ]; then ts=$(date +%s.%N);"
        f" echo RESULT $(cat $E/result-{cid}.json); rm -f $E/result-{cid}.json; break; fi; sleep 0.01; done;"
        f" [ \"$ts\" != none ] || {{ echo TIMING $t0 none none 1; exit 0; }};"
        f" sleep {settle}; ta=$(date +%s.%N);"
        f" ICHIPING_EXPECTED_USB_SERIAL={SERIAL} ICHIPING_EXCITATION={excitation}"
        f" ICHIPING_PRBS_AMPLITUDE={amplitude} ICHIPING_CAPTURE_FORMAT={capture_format}"
        f" ICHIPING_PRBS_REPEATS={repeats} ICHIPING_PRBS_GAP={gap}"
        f" {AUDIO} calibrate-noise {run_id} > /tmp/shot-{run_id}.log 2>&1;"
        f" rc=$?; te=$(date +%s.%N); echo AUDIOSTART $ta;"
        f" echo STOP $(tail -1 /tmp/shot-{run_id}.log); rm -f /tmp/shot-{run_id}.log;"
        f" echo PCM $(cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status);"
        f" echo TIMING $t0 $ts $te $rc", timeout=90 + repeats * 2.5)
    fields = {line.split(" ", 1)[0]: line.split(" ", 1)[1] for line in out.strip().splitlines() if " " in line}
    t0, ts, te, rc = fields["TIMING"].split()
    if "RESULT" not in fields or ts == "none":
        raise RuntimeError(f"servo result missing: {out[-400:]}")
    result = json.loads(fields["RESULT"])
    if result.get("status") != "ok":
        raise RuntimeError(f"eval set_state failed: {result}")
    if rc != "0" or "SD_MODE Low" not in fields.get("STOP", "") or fields.get("PCM", "").split() != ["closed", "closed"]:
        raise RuntimeError(f"audio stop verification failed: {out[-400:]}")
    return {"run_id": run_id, "servo_state": result["servo_state"], "stop": fields["STOP"],
            "servo_done_s": float(ts) - float(t0),
            "settle_actual_s": float(fields["AUDIOSTART"]) - float(ts),
            "shot_s": float(te) - float(t0)}


def fetch(out: Path, run_ids: list[str]) -> None:
    """Stream finished captures in one SSH connection (root-owned, readable)."""
    if not run_ids:
        return
    names = " ".join(f"ichiping-noise-calibration-{r}.raw" for r in run_ids)
    tar = subprocess.run(SSH + [f"cd {WORK} && tar cf - {names}"], capture_output=True, timeout=300, check=True)
    subprocess.run(["tar", "xf", "-", "-C", str(out)], input=tar.stdout, check=True, timeout=120)
    for r in run_ids:
        local = out / f"ichiping-noise-calibration-{r}.raw"
        if local.stat().st_size == 0:
            raise RuntimeError(f"empty capture after fetch: {r}")
        local.replace(out / f"{r}.raw")
    # Board storage: delete only after every file arrived intact on the PC.
    ssh(f"cd {WORK} && rm -f {names}")


def shot(out: Path, amplitude: float, capture_format: str) -> tuple[str, str]:
    run_id = uuid.uuid4().hex
    log = ssh(
        f"sudo -n ICHIPING_EXPECTED_USB_SERIAL={SERIAL} ICHIPING_EXCITATION=prbs16k"
        f" ICHIPING_PRBS_AMPLITUDE={amplitude} ICHIPING_CAPTURE_FORMAT={capture_format}"
        f" /usr/local/lib/ichiping-calib/safe-audio-test.sh calibrate-noise {run_id} 2>&1 | tail -1;"
        f" cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status", timeout=90)
    if "SD_MODE Low" not in log or log.count("closed") != 2:
        raise RuntimeError(f"audio stop verification failed: {log}")
    local = out / f"{run_id}.raw"
    subprocess.run(["scp", "-q", "-i", KEY, "-o", "BatchMode=yes",
                    f"{HOST}:/var/tmp/ichiping-noise-calibration-{run_id}.raw", str(local)],
                   check=True, timeout=60)
    ssh(f"rm -f /var/tmp/ichiping-noise-calibration-{run_id}.raw || true")
    return run_id, log.strip().splitlines()[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--baseline", type=int, default=3)
    parser.add_argument("--amplitude", type=float, default=0.0088)
    # New UNO Q datasets keep all 24 bits; convert to int16-compatible offline.
    parser.add_argument("--format", default="S32_LE", choices=("S16_LE", "S32_LE"))
    parser.add_argument("--states", default=",".join(str(s) for s in range(32)))
    # Fixed wait after the LAST servo stopped, before the capture starts.  The
    # cached PCM adds 0.5 s of silence, so noise onset ~= settle + ~0.65 s.
    parser.add_argument("--settle", type=float, default=0.5,
                        help="seconds to wait after the last servo stopped")
    parser.add_argument("--seed", type=int, default=20260912)
    parser.add_argument("--order", choices=("gray", "random"), default="gray")
    parser.add_argument("--repeats", type=int, default=1,
                        help="consecutive shots per state without moving servos")
    parser.add_argument("--batch", action="store_true",
                        help="capture the repeats of one state as one continuous PCM/capture")
    parser.add_argument("--gap", type=float, default=0.3,
                        help="batch mode: silence between PRBS frames (room decay)")
    parser.add_argument("--excitation", choices=("prbs16k", "silence"), default="prbs16k",
                        help="silence: speaker muted, records ambient frames for --ambient-dirs")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    records = args.out / "records.jsonl"
    states = [int(s) for s in args.states.split(",")]
    rng = random.Random(args.seed)
    plan = [("baseline", 0)] * args.baseline
    # Gray-code order: consecutive states differ by one servo (1 move per shot
    # instead of ~2.5 for random order).  Each round starts at a different
    # offset and alternates direction so no state is always captured at the
    # same point in the run.
    gray = [i ^ (i >> 1) for i in range(32)]
    for round_index in range(args.rounds):
        if args.order == "random":
            order = states[:]
            rng.shuffle(order)
        else:
            offset = (round_index * 11) % 32
            order = gray[offset:] + gray[:offset]
            if round_index % 2:
                order.reverse()
            order = [s for s in order if s in states]
        # Repeats of one state are captured back-to-back: only the first shot
        # of a state moves a servo, the rest re-use the settled position.
        plan += [(f"round{round_index}", s) for s in order for _ in range(args.repeats)]
    # --batch: consecutive shots of one state become ONE clocked PCM + ONE
    # continuous capture (frames split offline), so there is no per-shot
    # startup; only the silent gap separates frames.
    steps: list[list] = []
    for group, state in plan:
        if args.batch and steps and steps[-1][0] == group and steps[-1][1] == state:
            steps[-1][2] += 1
        else:
            steps.append([group, state, 1])
    if args.batch:
        # Pre-build the cached PCM for each batch length so generation time
        # never sits between the servo settle and the noise.
        for count in sorted({c for _, _, c in steps if c > 1}):
            if args.excitation == "silence":
                name = f"ichiping-silence-r{count}-g{args.gap}.raw"
                prepare = f"prepare-silence --repeats {count} --gap {args.gap}"
            else:
                name = f"ichiping-prbs16k-a{args.amplitude}-s20260912-r{count}-g{args.gap}.raw"
                prepare = (f"prepare-prbs16k --amplitude {args.amplitude} --seed 20260912"
                           f" --repeats {count} --gap {args.gap}")
            ssh(f"mkdir -p {WORK} && [ -s {WORK}/{name} ] || (python3 /home/arduino/ichiping-audio/audio-smoke-test.py"
                f" {prepare} --output {WORK}/{name}.tmp && mv {WORK}/{name}.tmp {WORK}/{name})", timeout=300)
    started = time.time()
    pending: list[str] = []
    done = 0
    for index, (group, state, count) in enumerate(steps):
        shot_info = state_and_shot(state, args.amplitude, args.format, args.settle, count, args.gap,
                                   args.excitation)
        # label follows the dataset directories: s<a><b><c><AB><BC>; state bit0 = window a.
        dataset_label = "s" + "".join(str(state >> i & 1) for i in range(5))
        with records.open("a", encoding="utf-8") as handle:
            for frame_index in range(count):
                record = {"index": done + frame_index, "group": group, "state": state,
                          "label": dataset_label,
                          "run_id": shot_info["run_id"], "file": f"{shot_info['run_id']}.raw",
                          "frame_index": frame_index if count > 1 else None,
                          "repeats": count, "gap": args.gap if count > 1 else None,
                          "amplitude": args.amplitude, "capture_format": args.format,
                          "excitation": args.excitation, "prbs_seed": 20260912, "order": args.order,
                          "servo_state": shot_info["servo_state"],
                          "servo_done_s": round(shot_info["servo_done_s"], 3),
                          "settle_s": args.settle,
                          "settle_actual_s": round(shot_info["settle_actual_s"], 3),
                          "shot_s": round(shot_info["shot_s"], 3),
                          "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "stop": shot_info["stop"]}
                handle.write(json.dumps(record) + "\n")
        done += count
        pending.append(shot_info["run_id"])
        last_of_group = index + 1 == len(steps) or steps[index + 1][0] != group
        if last_of_group or count > 1:
            fetch(args.out, pending)
            pending = []
        elapsed = time.time() - started
        print(f"[{done}/{len(plan)}] {group} {dataset_label} x{count} servo {shot_info['servo_done_s']:.2f}s "
              f"settle {shot_info['settle_actual_s']:.2f}s shot {shot_info['shot_s']:.1f}s "
              f"eta {elapsed / done * (len(plan) - done) / 60:.1f} min", flush=True)
    eval_command("set_state", 0)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
