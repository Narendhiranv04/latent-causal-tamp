#!/bin/bash
# Progress + ETA of every FINAL_READINESS_GATE stage (rate = items finished since the stage's first output line).
cd /home/naren/Desktop/boltzmann_lfd/final_dataset_generation/FINAL_READINESS_GATE
python3 - <<'PY'
import json, os, subprocess, time
from pathlib import Path
now = time.time()
ps = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
def stage(name, items, out, pat):
    tot = len(json.load(open(items))) if Path(items).exists() else 0
    done = sum(1 for l in open(out) if l.strip()) if Path(out).exists() else 0
    running = pat in ps
    if done >= tot and tot:
        return f"{name}: DONE {done}/{tot}"
    if not running:
        return f"{name}: queued (0/{tot})" if done == 0 else f"{name}: stopped at {done}/{tot}"
    t0 = os.path.getctime(out) if Path(out).exists() else now
    el = max(now - t0, 1)
    rate = done / el
    eta = (tot - done) / rate if rate > 0 else None
    return f"{name}: {done}/{tot} ({100*done/max(tot,1):.0f}%), ETA " + (time.strftime('%H:%M IST', time.localtime(now + eta)) + f" (~{eta/60:.0f} min)" if eta else "n/a")
print(time.strftime("%H:%M IST", time.localtime(now)))
print(stage("2D main X/Y", "work/xy2d_items.json", "work/xy2d_fin.jsonl", "xyfin2d.py run work/xy2d_items.json"))
print(stage("2D empty-endpoint Y", "work/xy2d_items_empty.json", "work/xy2d_empty.jsonl", "xyfin2d.py run work/xy2d_items_empty"))
print(stage("3D replay A/B (mandatory+sample)", "work/rpl3d_items.json", "work/rpl3d_AB.jsonl", "rpl3d.py run work/rpl3d_items.json"))
print(stage("3D replay C (all witnessed)", "work/rpl3d_items_C.json", "work/rpl3d_C.jsonl", "rpl3d.py run work/rpl3d_items_C"))
print(stage("3D replay D (rerun R2/R1+)", "work/rpl3d_items_D.json", "work/rpl3d_D.jsonl", "rpl3d.py run work/rpl3d_items_D"))
print(stage("3D replay E (empty sample)", "work/rpl3d_items_E.json", "work/rpl3d_E.jsonl", "rpl3d.py run work/rpl3d_items_E"))
agree = mism = 0
for f in ("rpl3d_AB.jsonl", "rpl3d_C.jsonl", "rpl3d_D.jsonl", "rpl3d_E.jsonl"):
    p = Path("work") / f
    if p.exists():
        for l in open(p):
            for q in json.loads(l)["results"]:
                if q["q"] in ("X", "Y"):
                    if q["verdict"] in ("AGREE", "AGREE_VALUE_PHASE_DIFFERS"): agree += 1
                    else: mism += 1
print(f"3D replay so far: {agree} agree, {mism} not agree")
t = [int(open(d/"temp1_input").read())/1000 for d in Path("/sys/class/hwmon").glob("hwmon*") if (d/"name").read_text().strip()=="k10temp"]
print(f"CPU temp {t[0] if t else '?'} C, load {os.getloadavg()[0]:.1f}")
PY
