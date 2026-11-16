"""V3.2 Phase D/E: physically verified evaluation of trained scorer arms on exhaustive M4 / M5 / M6 pools (frozen sampler s0, frozen rule).
Inputs: exhaustive records <RUNDIR>/<dom>/<arm>_s<seed>_M6_<split>_p*.jsonl (+ the frozen-model V3.2-A pass and the capped baseline as references),
physical verify caches (glob).  UNKNOWN (unlabelled selected repair) is never counted as failure: tables report [lower, upper] and refuse
exact deltas while any UNKNOWN remains.
    v32e_eval.py todo  SNAP RUNDIR SPLIT CACHE_GLOB_2D CACHE_GLOB_3D OUTDIR       -> OUTDIR/todo_E_<dom>.jsonl (unique unlabelled selections)
    v32e_eval.py table SNAP RUNDIR SPLIT CACHE_GLOB_2D CACHE_GLOB_3D OUT_JSON [FROZEN_RUNDIR]"""
import collections, glob, json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v32b_phys import GRID, RULE, labels as _labels, outcome, boot  # noqa: E402  (same label merge / outcome semantics as Phase B)

RI = GRID.index(RULE)
ARMS = ("control", "expanded")


def jl(p):
    return [json.loads(l) for l in open(p)]


def records(rundir, d, arm, seed, split):
    out = {}
    for p in sorted(glob.glob(f"{rundir}/{d}/{arm}_s{seed}_M6_{split}*.jsonl")):
        for r in jl(p):
            out[r["root_id"]] = r
    return out


def selections(rec, M):
    return {k: (None if (v := r["per_M"][str(M)]["decisions"][RI]) is None else v["seq"]) for k, r in rec.items()}, \
           {k: (None if (v := r["per_M"][str(M)]["decisions"][RI]) is None else v["p11"]) for k, r in rec.items()}


def main():
    mode, snap, rundir, split, g2, g3, out = sys.argv[1:8]
    globs = {"2d": g2, "3d": g3}
    res = {}
    for d in ("2d", "3d"):
        lab = _labels(d, globs[d])
        rows = {r["root_id"]: r for r in jl(Path(snap) / f"data{d}.jsonl") if r["split"] == split}
        arms = {}
        for arm in ARMS:
            for s in (0, 1, 2):
                rec = records(rundir, d, arm, s, split)
                if rec:
                    arms[(arm, s)] = rec
        if mode == "todo":
            want = set()
            for rec in arms.values():
                for M in (4, 5, 6):
                    sel, _ = selections(rec, M)
                    want |= {(k, json.dumps(v)) for k, v in sel.items() if v and (k, json.dumps(v)) not in lab}
            Path(out).mkdir(parents=True, exist_ok=True)
            with open(Path(out) / f"todo_E_{d}.jsonl", "w") as f:
                for k, s in sorted(want):
                    f.write(json.dumps({"root_id": k, "selected_ordered_seq": json.loads(s), "decision": "REPAIR"}) + "\n")
            print(d, "arms/seeds", sorted(arms), "unlabelled unique selections", len(want), "roots", len({k for k, _ in want}))
            continue
        R, per = {}, {}
        for arm in ARMS:
            for M in (4, 5, 6):
                seeds = [s for s in (0, 1, 2) if (arm, s) in arms]
                if not seeds:
                    continue
                acc = collections.defaultdict(lambda: collections.defaultdict(list)); unk = 0; seed_task = []; cal = []
                for s in seeds:
                    rec = arms[(arm, s)]
                    assert set(rec) == set(rows), (d, arm, s, len(rec), len(rows))
                    sel, p11 = selections(rec, M)
                    st = []
                    for k in rows:
                        o = outcome(sel[k], lab, k); mk, K = rows[k]["masks"], rows[k]["K_legacy"]
                        unk += o == "UNKNOWN"
                        if o in ("SUCCESS", "FAIL_X", "FAIL_Y"):
                            cal.append((p11[k], o == "SUCCESS"))
                        if mk["eval_task"]:
                            acc["task"][k].append(o == "SUCCESS"); acc[f"task_K{K}"][k].append(o == "SUCCESS"); st.append(o == "SUCCESS")
                        if mk["eval_abstain"]:
                            acc["abstain"][k].append(o == "ABSTAIN"); acc["none_fail"][k].append(o in ("FAIL_X", "FAIL_Y"))
                        if mk["eval_noop"]:
                            acc["noop"][k].append(o == "NOOP")
                    seed_task.append(float(np.mean(st)))
                m = {key: {k: float(np.mean(v)) for k, v in dd.items()} for key, dd in acc.items()}
                per[(arm, M)] = m
                cal = np.array(cal, float)
                R[f"{arm}_M{M}"] = {"seeds": seeds, "unknown_selected": unk, **{key: float(np.mean(list(v.values()))) for key, v in m.items()},
                                    "task_seed_sd": float(np.std(seed_task)), "task_per_seed": seed_task,
                                    "selected_mean_p11": float(cal[:, 0].mean()) if len(cal) else None,
                                    "selected_verified_rate": float(cal[:, 1].mean()) if len(cal) else None,
                                    "overconfidence": float(cal[:, 0].mean() - cal[:, 1].mean()) if len(cal) else None,
                                    "n_selected_repairs": int(len(cal))}
        for M in (4, 5, 6):                                               # H3: expanded vs control on identical candidate sets (same draws, same roots)
            a, b = per.get(("expanded", M)), per.get(("control", M))
            if a and b and R[f"expanded_M{M}"]["unknown_selected"] == 0 and R[f"control_M{M}"]["unknown_selected"] == 0:
                for key in ("task", "abstain"):
                    c = sorted(set(a[key]) & set(b[key]))
                    R[f"expanded_M{M}"][f"delta_{key}_vs_control"] = boot([a[key][k] - b[key][k] for k in c])
        for arm in ARMS:                                                  # H4: within-model M5 / M6 vs M4
            for M in (5, 6):
                a, b = per.get((arm, M)), per.get((arm, 4))
                if a and b and R[f"{arm}_M{M}"]["unknown_selected"] == 0 and R[f"{arm}_M4"]["unknown_selected"] == 0:
                    for key in ("task", "abstain"):
                        c = sorted(set(a[key]) & set(b[key]))
                        R[f"{arm}_M{M}"][f"delta_{key}_vs_M4"] = boot([a[key][k] - b[key][k] for k in c])
        res[d] = R
        print("=====", d)
        for k, x in R.items():
            f = lambda t: "" if not t else f"{100*t[0]:+.1f} [{100*t[1]:+.1f}, {100*t[2]:+.1f}]"  # noqa: E731
            print(f"  {k:12s} task {100*x['task']:.1f}+-{100*x['task_seed_sd']:.1f}  K {100*x['task_K1']:.0f}/{100*x['task_K2']:.0f}/{100*x['task_K3']:.0f}"
                  f"  abst {100*x['abstain']:.1f}  noop {100*x['noop']:.1f}  unk {x['unknown_selected']}  p11sel {x['selected_mean_p11'] or 0:.3f} vs ok {x['selected_verified_rate'] or 0:.3f}"
                  f"  vsCtl {f(x.get('delta_task_vs_control'))}  abst-vsCtl {f(x.get('delta_abstain_vs_control'))}  vsM4 {f(x.get('delta_task_vs_M4'))}")
    if mode == "table":
        Path(out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
