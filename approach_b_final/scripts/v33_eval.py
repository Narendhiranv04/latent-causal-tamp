"""V3.3 physically verified VALIDATION evaluation of scratch samplers (frozen D-expanded, exhaustive M4, frozen rule).  Same label merge and outcome
semantics as V3.2 (v32b_phys.labels / outcome; UNKNOWN never counted as failure; exact deltas refused while UNKNOWN remains).
Arm spec NAME:SEEDS:PATTERN, PATTERN with {d} and {s}, e.g. control:0,1,2:RUN/{d}/control_s{s}_D0_M4_val_p*.jsonl
    v33_eval.py todo  SNAP CACHE_GLOB_2D CACHE_GLOB_3D OUTDIR   ARM ...   -> OUTDIR/todo_<dom>.jsonl (unique unlabelled selected repairs)
    v33_eval.py table SNAP CACHE_GLOB_2D CACHE_GLOB_3D OUT_JSON ARM ...   primary contrast = expanded - control; every arm vs 'q2init' as reference"""
import collections, glob, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v32b_phys import GRID, RULE, labels, outcome, boot  # noqa: E402
from v33_proposals import known  # noqa: E402

RI = GRID.index(RULE)
M = "4"


def recs(pattern, d, s):
    out = {}
    for p in sorted(glob.glob(pattern.format(d=d, s=s))):
        for l in open(p):
            r = json.loads(l)
            out[r["root_id"]] = r
    return out


def dec(r):
    v = r["per_M"][M]["decisions"][RI]
    return (None, None) if v is None else (v["seq"], v["p11"])


def main():
    mode, snap, g2, g3, out = sys.argv[1:6]
    specs = [a.split(":", 2) for a in sys.argv[6:]]
    res = {}
    for d, g in (("2d", g2), ("3d", g3)):
        lab = labels(d, g)
        rows, pos = known(snap, d, g)
        A = {}
        for name, seeds, pat in specs:
            for s in map(int, seeds.split(",")):
                r = recs(pat, d, s)
                if r:
                    A[(name, s)] = r
        if mode == "todo":
            want = {(k, json.dumps(dec(r)[0])) for rec in A.values() for k, r in rec.items() if dec(r)[0] and (k, json.dumps(dec(r)[0])) not in lab}
            Path(out).mkdir(parents=True, exist_ok=True)
            with open(Path(out) / f"todo_{d}.jsonl", "w") as f:
                for k, s in sorted(want):
                    f.write(json.dumps({"root_id": k, "selected_ordered_seq": json.loads(s), "decision": "REPAIR"}) + "\n")
            print(d, "runs", sorted(A), "complete", {f"{n}_s{s}": len(r) == len(rows) for (n, s), r in A.items()},
                  "unlabelled unique selections", len(want), "roots", len({k for k, _ in want}))
            continue
        R, per = {}, {}
        for name, _, _ in specs:
            seeds = sorted(s for (n, s) in A if n == name)
            if not seeds:
                continue
            acc = collections.defaultdict(lambda: collections.defaultdict(list)); unk, seed_task, seed_abs, cal, fail = 0, [], [], [], collections.Counter()
            wall, nsc = [], []
            for s in seeds:
                rec = A[(name, s)]
                assert set(rec) == set(rows), (d, name, s, len(rec), len(rows))
                st, sa = [], []
                for k, row in rows.items():
                    seq, p = dec(rec[k])
                    o = outcome(seq, lab, k); mk, K = row["masks"], row["K_legacy"]
                    unk += o == "UNKNOWN"
                    wall.append(rec[k]["wall_s"]); nsc.append(rec[k]["per_M"][M]["n_scored"])
                    if o in ("SUCCESS", "FAIL_X", "FAIL_Y"):
                        cal.append((p, o == "SUCCESS"))
                    if mk["eval_task"]:
                        ok = o == "SUCCESS"
                        acc["task"][k].append(ok); acc[f"task_K{K}"][k].append(ok); st.append(ok)
                        D6 = rec[k]["D6"]
                        cov = any(all(str(ob) in D6 and c in D6[str(ob)][:int(M)] for ob, c in a) for a in pos[k])
                        acc["known_cover"][k].append(cov)
                        if not ok:
                            fail[("RANK_" if cov else "COVER_") + o] += 1
                    if mk["eval_abstain"]:
                        acc["abstain"][k].append(o == "ABSTAIN"); acc["none_fail"][k].append(o in ("FAIL_X", "FAIL_Y")); sa.append(o == "ABSTAIN")
                    if mk["eval_noop"]:
                        acc["noop"][k].append(o == "NOOP")
                seed_task.append(float(np.mean(st))); seed_abs.append(float(np.mean(sa)))
            m = {key: {k: float(np.mean(v)) for k, v in dd.items()} for key, dd in acc.items()}
            per[name] = m
            cal = np.array(cal, float)
            R[name] = {"seeds": seeds, "unknown_selected": unk, **{key: float(np.mean(list(v.values()))) for key, v in m.items()},
                       "n": {key: len(v) for key, v in m.items()}, "task_per_seed": seed_task, "abstain_per_seed": seed_abs,
                       "task_seed_sd": float(np.std(seed_task)), "selected_mean_p11": float(cal[:, 0].mean()), "selected_verified_rate": float(cal[:, 1].mean()),
                       "overconfidence": float(cal[:, 0].mean() - cal[:, 1].mean()), "n_selected_repairs": int(len(cal)),
                       "task_failures": {k: v / len(seeds) for k, v in sorted(fail.items())},
                       "wall_s_median": float(np.median(wall)), "wall_s_p99": float(np.percentile(wall, 99)), "n_scored_median": float(np.median(nsc))}

        def delta(a, b):
            if a not in per or b not in per or R[a]["unknown_selected"] or R[b]["unknown_selected"]:
                return None
            o = {}
            for key in ("task", "abstain", "noop", "task_K1", "task_K2", "task_K3", "known_cover"):
                c = sorted(set(per[a].get(key, {})) & set(per[b].get(key, {})))
                if c:
                    o[key] = boot([per[a][key][k] - per[b][key][k] for k in c])
            return o
        R["delta_expanded_vs_control"] = delta("expanded", "control")
        for n in ("control", "expanded"):
            R[f"reference_{n}_vs_q2init"] = delta(n, "q2init")
        res[d] = R
        f = lambda t: "" if not t else f"{100*t[0]:+.1f} [{100*t[1]:+.1f}, {100*t[2]:+.1f}]"  # noqa: E731
        print("=====", d)
        for k, x in R.items():
            if k.startswith(("delta", "reference")):
                print(f"  {k}: " + ("UNKNOWN>0" if x is None else "  ".join(f"{kk} {f(v)}" for kk, v in x.items())))
            else:
                print(f"  {k:9s} s{x['seeds']} task {100*x['task']:.1f}+-{100*x['task_seed_sd']:.1f}  K {100*x['task_K1']:.0f}/{100*x['task_K2']:.0f}/{100*x['task_K3']:.0f}"
                      f"  abst {100*x['abstain']:.1f}  noop {100*x['noop']:.1f}  cover {100*x['known_cover']:.1f}  unk {x['unknown_selected']}"
                      f"  p11sel {x['selected_mean_p11']:.3f} vs ok {x['selected_verified_rate']:.3f}")
    if mode == "table":
        Path(out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
