#!/usr/bin/env python3
"""Progress + ETA of every FINAL_READINESS_GATE stage.  Remaining CPU = sum over unfinished queries of the measured mean wall time of finished
queries of the same kind (2D: role/query; 3D: query/label/method), divided by the stage's workers; stages chained in their execution order."""
import collections as C, json, os, statistics, subprocess, time
from pathlib import Path
W = Path(__file__).resolve().parent.parent / "work"
now = time.time()
procs = [l for l in subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout.splitlines() if "python" in l.split()[0]]
run = lambda pat: any(pat in l for l in procs)
jl = lambda p: [json.loads(l) for l in open(p) if l.strip()] if p.exists() else []


def model2d():
    m = C.defaultdict(list)
    for f in ("xy2d_fin.jsonl", "xy2d_empty.jsonl"):
        for r in jl(W / f):
            for q in r["results"]:
                m[(q["role"], q["q"])].append(q.get("wall_s", 0))
    return {k: statistics.mean(v) for k, v in m.items()}


def model3d():
    m = C.defaultdict(list)
    for f in ("rpl3d_AB.jsonl", "rpl3d_C.jsonl", "rpl3d_D.jsonl", "rpl3d_E.jsonl"):
        for r in jl(W / f):
            for q in r["results"]:
                c = ((q.get("replay") or {}).get("cpu_s") or 0) + ((q.get("rerun") or {}).get("cpu_s") or 0) + ((q.get("legacy") or {}).get("cpu_s") or 0)
                m[(q["q"], q.get("label_x", q.get("label_y")), q.get("witnesses") is None)].append(c)
    return {k: statistics.mean(v) for k, v in m.items()}


M2, M3 = model2d(), model3d()


def cost(q, dom):
    if dom == "2D":
        return M2.get((q["role"], q["q"])) or M2.get(("EMPTY_PARITY", "Y"), 0.5) if q["role"] == "EMPTY_ALL" else M2.get((q["role"], q["q"]), 30.0)
    k = (q["q"], q.get("label_x", q.get("label_y")), q.get("witnesses") is None)
    return M3.get(k, 40.0)


def stage(name, items, out, pat, workers, dom):
    it = json.load(open(W / items)) if (W / items).exists() else []
    done = {r["key"] for r in jl(W / out)}
    rem = [i for i in it if i["key"] not in done]
    cpu = sum(cost(q, dom) for i in rem for q in i["queries"])
    return {"name": name, "done": len(it) - len(rem), "tot": len(it), "running": run(pat), "wall": cpu / workers * 1.1}


S = {k: stage(*v) for k, v in {
    "2d": ("2D main X/Y (20 workers)", "xy2d_items.json", "xy2d_fin.jsonl", "xyfin2d.py run work/xy2d_items.json", 20, "2D"),
    "2e": ("2D empty-endpoint Y (18)", "xy2d_items_empty.json", "xy2d_empty.jsonl", "xyfin2d.py run work/xy2d_items_empty", 18, "2D"),
    "ab": ("3D replay A/B mandatory+sample (7)", "rpl3d_items.json", "rpl3d_AB.jsonl", "rpl3d.py run work/rpl3d_items.json", 7, "3D"),
    "c": ("3D laptop share A: witnessed replays (7)", "rpl3d_items_C.json", "rpl3d_C.jsonl", "rpl3d.py run work/rpl3d_items_C", 7, "3D"),
    "d": ("3D laptop share B: re-runs + witnessed, after 2D (20)", "rpl3d_items_D.json", "rpl3d_D.jsonl", "rpl3d.py run work/rpl3d_items_D", 20, "3D"),
    "e": ("3D replay E (moved to gvlab)", "rpl3d_items_E.json", "rpl3d_E.jsonl", "rpl3d.py run work/rpl3d_items_E", 20, "3D")}.items()}
# gvlab share (tier D re-runs + tier E): progress fetched over ssh into work/rpl3d_GV.jsonl (copy)
try:
    subprocess.run(["timeout", "40", "rsync", "-a", "gvlab:rgate/G/FINAL_READINESS_GATE/work/rpl3d_GV.jsonl", str(W / "rpl3d_GV.jsonl")], capture_output=True)
    gvrun = "rpl3d.py run work/rpl3d_items_GV" in subprocess.run(["timeout", "20", "ssh", "-o", "BatchMode=yes", "gvlab", "ps -eo args"], capture_output=True, text=True).stdout
except Exception:  # noqa: BLE001
    gvrun = False
S["gv"] = stage("3D gvlab share: re-runs + empty sample (16, gvlab)", "rpl3d_items_GV.json", "rpl3d_GV.jsonl", "@@never@@", 16, "3D")
S["gv"]["running"] = gvrun
end = {}
t = now
end["gv"] = now + S["gv"]["wall"]
for k in ("2d", "2e", "d", "e"):            # chain on CPUs 12-31
    t += S[k]["wall"]; end[k] = t
t = now
for k in ("ab", "c"):                      # chain on CPUs 5-11
    t += S[k]["wall"]; end[k] = t
fmt = lambda x: time.strftime("%H:%M", time.localtime(x))
print("Status at", fmt(now), "IST")
for k in ("2d", "2e", "ab", "c", "d", "gv"):
    s = S[k]
    st = "DONE" if s["done"] == s["tot"] and s["tot"] else ("running" if s["running"] else "queued")
    print(f"- {s['name']}: {s['done']}/{s['tot']} roots, {st}" + ("" if st == "DONE" else f", ETA ~{fmt(end[k])} IST"))
print(f"All compute done ~{fmt(max(end.values()))} IST; reports ~10 min after that")
agree = bad = 0
for f in ("rpl3d_AB.jsonl", "rpl3d_C.jsonl", "rpl3d_D.jsonl", "rpl3d_E.jsonl", "rpl3d_GV.jsonl"):
    for r in jl(W / f):
        for q in r["results"]:
            if q["q"] in ("X", "Y"):
                agree += q["verdict"] in ("AGREE", "AGREE_VALUE_PHASE_DIFFERS"); bad += q["verdict"] not in ("AGREE", "AGREE_VALUE_PHASE_DIFFERS")
miss2 = sum(1 for f in ("xy2d_fin.jsonl", "xy2d_empty.jsonl") for r in jl(W / f) for q in r["results"] if q.get("resolution") != "EVALUATED")
tmp = [int(open(d / "temp1_input").read()) / 1000 for d in Path("/sys/class/hwmon").glob("hwmon*") if (d / "name").read_text().strip() == "k10temp"]
print(f"3D replay so far: {agree} agree, {bad} not agree | 2D queries not evaluated (admin/error): {miss2} | CPU {tmp[0] if tmp else '?'} C, load {os.getloadavg()[0]:.1f}")
