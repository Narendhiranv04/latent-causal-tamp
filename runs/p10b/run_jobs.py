"""Parallel runner: python run_jobs.py <jobs file 'name|call'> <parallel>; env P10C_OUT / P10C_BATCHES set by the caller."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, os.getcwd())
import p10b_dataset as d  # noqa: E402

out = Path(os.environ["P10C_OUT"])
jobs = [l.split("|", 1) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]


def run(j):
    name, call = j
    if (out / "runs" / f"{name}.json").exists():
        return name, "DONE"
    g = d.job(f"p10c_{out.name}_{name}", call, 3000.0, module="p10c_train_eval", category="training", wall=7000)
    return name, g["stop"]


with ThreadPoolExecutor(int(sys.argv[2])) as ex:
    for name, st in ex.map(run, jobs):
        print(name, st, flush=True)
print("TRAIN_END", flush=True)
