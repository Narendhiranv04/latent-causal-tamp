#!/usr/bin/env python3
"""Memory-guarded job queue for the P4 runs (no torch here).  Each job = one resumable run_p4.py shard; at most MAXP at once; a job starts only
when MemAvailable >= START_GB and swap used <= SWAP_GB; if MemAvailable falls below PAUSE_GB the newest running job is SIGSTOPped until memory
recovers (then SIGCONT).  When every shard of an arm has finished, a seal pass (no shard) writes predictions + SEAL.json.
    python p4_queue.py ARMS(comma) DEV_PUBLIC P4_DIR [--maxp 6] [--shards 3]"""
import argparse, os, signal, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def meminfo():
    m = {}
    for l in open("/proc/meminfo"):
        k, v = l.split(":")[0], int(l.split()[1])
        m[k] = v / 1048576.0
    return m["MemAvailable"], m["SwapTotal"] - m["SwapFree"]


def main(arms, dev, p4, maxp, shards, start_gb=6.0, swap_gb=1.0, pause_gb=2.5):
    p4 = Path(p4); log = open(p4 / "queue.log", "a")
    say = lambda *a: (log.write(time.strftime("%H:%M:%S ") + " ".join(map(str, a)) + "\n"), log.flush())  # noqa: E731
    jobs = [(a, i) for a in arms for i in range(shards)]
    run, stopped, cpu = {}, set(), 0
    say("START", arms, "maxp", maxp)
    while jobs or run:
        for k, p in list(run.items()):
            if p.poll() is not None:
                say("DONE", k, "rc", p.returncode); run.pop(k); stopped.discard(k)
        avail, swp = meminfo()
        if avail < pause_gb and run:
            k = max((k for k in run if k not in stopped), key=lambda k: run[k].pid, default=None)
            if k:
                run[k].send_signal(signal.SIGSTOP); stopped.add(k); say("PAUSE", k, f"avail={avail:.1f}G")
        elif stopped and avail > start_gb:
            k = stopped.pop(); run[k].send_signal(signal.SIGCONT); say("RESUME", k, f"avail={avail:.1f}G")
        if jobs and len(run) < maxp and avail >= start_gb and swp <= swap_gb and not stopped:
            a, i = jobs.pop(0)
            core = f"{2 + 2 * (cpu % 14)}-{3 + 2 * (cpu % 14)}"; cpu += 1
            cmd = ["taskset", "-c", core, sys.executable, str(HERE / "run_p4.py"), a, dev, str(p4 / a), "--device", "cuda",
                   "--shard", f"{i}/{shards}", "--no-seal"] + (["--reverse"] if i % 2 else [])
            env = {**os.environ, "OMP_NUM_THREADS": "2"}
            run[(a, i)] = subprocess.Popen(cmd, stdout=open(p4 / f"{a}_s{i}.log", "a"), stderr=subprocess.STDOUT, env=env)
            say("LAUNCH", (a, i), f"avail={avail:.1f}G swap={swp:.1f}G core={core}")
        time.sleep(5)
    for a in arms:                                     # seal passes (all traces exist -> no model work, writes SEAL.json)
        r = subprocess.run([sys.executable, str(HERE / "run_p4.py"), a, dev, str(p4 / a), "--device", "cuda"], capture_output=True, text=True)
        say("SEAL", a, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:])
    say("ALL_DONE")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("arms"); ap.add_argument("dev"); ap.add_argument("p4")
    ap.add_argument("--maxp", type=int, default=6); ap.add_argument("--shards", type=int, default=3)
    a = ap.parse_args(); main(a.arms.split(","), a.dev, a.p4, a.maxp, a.shards)
