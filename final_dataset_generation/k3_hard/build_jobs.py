#!/usr/bin/env python3
"""Per-layout start points for the hard-order K3 search (2D and 3D).
Layout = the ORIGINAL verified K3 root of each K3 row in the V2 selection (a re-parked child maps to its parent's layout).
Known assignments per layout = the original + every accepted same-layout child (DEPSEEK V1 stores, plus earlier HARDK3 roots).
Start = the known assignment with the fewest successful orders (>= 1).  Layouts already at 1/6 get no job.

  build_jobs.py 2d|3d OUT.json [variant]"""
import glob, json, sys
from pathlib import Path

H = Path(__file__).resolve().parent
G = H.parent
B = G.parent
dom, outp = sys.argv[1], Path(sys.argv[2])
variant = sys.argv[3] if len(sys.argv) > 3 else "v1"
sel = json.loads((G / "FINAL_DATASET_SELECTION_MANIFESTS" / f"{dom.upper()}_SELECTION_V2.json").read_text())["rows"]
k3 = [r for r in sel if r["K"] == "3"]
cellt = (lambda d: int(d)) if dom == "2d" else (lambda d: tuple(d))


def lay_of(r):
    return r["root_id"] if r["source"] == "ORIGINAL_SELECTED" else r["parent_root_id"]


split = {}
for r in k3:
    split[lay_of(r)] = r["split"]
known = {L: [] for L in split}
src = B / ("order_classification_2d/per_scene_six_permutation_outcomes.jsonl" if dom == "2d"
           else "order_classification_3d/3D_ORDER_CLASSIFICATION_PER_SCENE.jsonl")
for l in open(src):
    r = json.loads(l)
    if r["root_id"] in known and r.get("permutations"):
        known[r["root_id"]].append((r["root_id"], r["assignment"], r["permutations"]))
stores = [G / "d2/store/roots", H / "d2/store/roots"] if dom == "2d" else \
    [G / "d3_gvlab/store/roots", G / "d3_blackwell/store/roots", G / "d3_laptop/store/roots", H / "d3/store/roots"]
for st in stores:
    for f in sorted(st.glob("*.json")):
        r = json.loads(f.read_text())
        c = r.get("construction", {})
        L = c.get("layout_root_id") or c.get("parent_root_id")
        if r.get("verified_K") == 3 and L in known and c.get("same_layout_as_parent") and r.get("permutations"):
            mini = next(b for b in r["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
            known[L].append((r["ids"]["root_id"], mini["sequence"], r["permutations"]))
jobs = []
for L, ks in sorted(known.items()):
    if not ks:
        continue
    best = None
    keys = []
    for rid, assign, perms in ks:
        if any(p["y"] not in (0, 1) for p in perms) or len(perms) != 6:
            continue
        keys.append(json.dumps(sorted([o, cellt(d) if dom == "2d" else list(d)] for o, d in assign)))
        ns = sum(p["y"] for p in perms)
        succ = [[o for o, _ in p["order"]] for p in perms if p["y"] == 1]
        if ns >= 1 and (best is None or ns < best[0]):
            best = (ns, rid, assign, succ)
    if best is None or best[0] <= 1:
        continue
    jobs.append({"job_id": f"HJ{dom}_{variant}_{L}", "layout": L, "split": split[L], "start_id": best[1], "start_ns": best[0],
                 "start_assign": best[2], "start_succ": best[3], "known_keys": sorted(set(keys)), "variant": variant})
outp.write_text(json.dumps(jobs))
import collections as C
print(dom, "layouts", len(known), "jobs", len(jobs), C.Counter((j["start_ns"], j["split"]) for j in jobs))
