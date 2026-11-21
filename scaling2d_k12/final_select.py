#!/usr/bin/env python3
"""G4 final-cohort candidate selection (SCALING2D_FINAL_LOCK_V1).  Pure bookkeeping, no physics, no model.
  - fingerprint = GEOM_V1 (approach_b_final/scripts/v34_geomfp.geom_fp) of the learner view: sorted per-object (cell, radius, is_target,
    is_obstacle, is_fixed) + target cell + goal cell; generated discs are r = 0.024 with t0 first then o00..
  - reject if the fingerprint is in G0/HIST_EXCLUSIONS.json (historical + V3.4 cohort), or in any ENGINEERING layout, or a near-duplicate:
    occupied-cell Jaccard > 0.85 against any engineering layout with the same target and goal cells (or against an earlier selected candidate)
  - order: sha256('FINAL|root_id'); exact K_lb stratum; <= CAP candidates per stratum
    python final_select.py CANDIDATES.jsonl ENG_GLOB_FILE(list of jsonl paths) OUT.jsonl STRATA(e.g. 4,5,6) CAP"""
import glob, hashlib, json, sys
from pathlib import Path

H = Path(__file__).resolve().parent


def geom_fp(cells0, goal):
    objs = sorted([int(c), 0.024, 1.0 if i == 0 else 0.0, 0.0 if i == 0 else 1.0, 0.0] for i, c in enumerate(cells0))
    return hashlib.sha256(json.dumps([objs, int(cells0[0]), int(goal)], separators=(",", ":")).encode()).hexdigest()


def rid(L):
    return "FIN_" + hashlib.sha256(json.dumps([L.get("geom", "original"), L["cells0"], L["goal_cell"]]).encode()).hexdigest()[:12]


def main(cand_f, eng_list, out_f, strata, cap):
    hist = json.loads((H / "G0/HIST_EXCLUSIONS.json").read_text())
    excl = set(hist["historical_geom_fp"]) | set(hist.get("v34_cohort_2d_layout_fp", []))
    eng = []
    for p in [l.strip() for l in open(eng_list) if l.strip()]:
        for f in glob.glob(p):
            for l in open(f):
                r = json.loads(l)
                if "cells0" in r:
                    eng.append(r)
    eng_fp = {geom_fp(r["cells0"], r["goal_cell"]) for r in eng}
    by_tg = {}
    for r in eng:
        by_tg.setdefault((r["cells0"][0], r["goal_cell"]), []).append(set(r["cells0"]))
    jac = lambda a, b: len(a & b) / len(a | b)  # noqa: E731
    C = [json.loads(l) for l in open(cand_f)]
    for L in C:
        L["root_id"] = rid(L)
    C.sort(key=lambda L: hashlib.sha256(("FINAL|" + L["root_id"]).encode()).hexdigest())
    strata = [int(s) for s in strata.split(",")]
    sel, cnt, rej = [], {k: 0 for k in strata}, {}
    seen = set()
    for L in C:
        k = L["K_lb"]
        if k not in cnt or cnt[k] >= cap:
            continue
        fp = geom_fp(L["cells0"], L["goal_cell"])
        S = set(L["cells0"])
        why = ("historical" if fp in excl else "engineering_exact" if fp in eng_fp else "duplicate" if fp in seen else
               "engineering_near_duplicate" if any(jac(S, e) > 0.85 for e in by_tg.get((L["cells0"][0], L["goal_cell"]), [])) else
               "final_near_duplicate" if any(jac(S, set(x["cells0"])) > 0.85 for x in sel if x["cells0"][0] == L["cells0"][0] and x["goal_cell"] == L["goal_cell"]) else None)
        if why:
            rej[why] = rej.get(why, 0) + 1
            continue
        seen.add(fp)
        L["geom_fp"], L["final_order"] = fp, len(sel)
        sel.append(L); cnt[k] += 1
    with open(out_f, "w") as f:
        for L in sel:
            f.write(json.dumps(L) + "\n")
    print(json.dumps({"candidates": len(C), "engineering_layouts": len(eng), "selected": cnt, "rejected": rej}))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3], int(a[4]))
