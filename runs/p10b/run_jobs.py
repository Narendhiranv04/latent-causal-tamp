"""Parallel runner, ONE PROCESS PER JOB (each guard measures only its own process tree; a threaded runner over-counted CPU
through shared RUSAGE_CHILDREN). python run_jobs.py <jobs file 'name|call'> <parallel>; env P10C_OUT / P10C_BATCHES from the caller."""
import os
import subprocess
import sys
import time
from pathlib import Path

out = Path(os.environ["P10C_OUT"])
jobs = [l.split("|", 1) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
todo = [(n, c) for n, c in jobs if not (out / "runs" / f"{n}.json").exists()]
CODE = ("import sys, p10b_dataset as d; g = d.job('p10c_' + sys.argv[1] + '_' + sys.argv[2], sys.argv[3], 3000.0, "
        "module='p10c_train_eval', category='training', wall=7000); print(sys.argv[2], g['stop'], g['cpu_s'], flush=True)")
run = []
while todo or run:
    while todo and len(run) < int(sys.argv[2]):
        n, c = todo.pop(0)
        run.append(subprocess.Popen([sys.executable, "-c", CODE, out.name, n, c]))
    time.sleep(2)
    run = [p for p in run if p.poll() is None]
print("TRAIN_END", flush=True)
