"""V3.2 E6: exposed-TEST regression of the registered configuration (D-expanded, exhaustive M, seeds 0-2) against the V3.1-4 capped primary
(task cVAE + frozen V3 D s<seed>, M4, B=4,096, seeds 0-2; selections reports/v3_1/v3_1_4/selections/<d>/v3_1_4__v3D_task:q2init_all-S1_M4_B4096_s*_test.jsonl.gz).
Seed-averaged per-root outcomes, paired root bootstrap (2,000).  UNKNOWN is reported, never counted as failure; deltas only when none remain.
usage: v32_test_regression.py SNAP RECORDS_DIR V314_SELECTIONS_DIR M OUT_JSON CACHE_GLOB_2D CACHE_GLOB_3D"""
import collections, glob, gzip, json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v32b_phys import GRID, RULE, labels, outcome, boot  # noqa: E402

RI = GRID.index(RULE)


def main():
    snap, recdir, seldir, M, out, g2, g3 = sys.argv[1:8]
    res = {}
    for d, g in (("2d", g2), ("3d", g3)):
        rows = {r["root_id"]: r for r in map(json.loads, open(Path(snap) / f"data{d}.jsonl")) if r["split"] == "test"}
        lab = labels(d, g)
        arms = {"capped_V3_M4_B4096": [], f"D-expanded_M{M}": []}
        for s in (0, 1, 2):
            f = Path(seldir) / d / f"v3_1_4__v3D_task:q2init_all-S1_M4_B4096_s{s}_test.jsonl.gz"
            arms["capped_V3_M4_B4096"].append({r["root_id"]: r["selected_ordered_seq"] for r in map(json.loads, gzip.open(f, "rt"))})
            rec = {}
            for p in glob.glob(f"{recdir}/{d}/expanded_s{s}_M6_test*.jsonl"):
                for l in open(p):
                    r = json.loads(l); dec = r["per_M"][M]["decisions"][RI]
                    rec[r["root_id"]] = None if dec is None else dec["seq"]
            arms[f"D-expanded_M{M}"].append(rec)
        R, per = {}, {}
        for a, seeds in arms.items():
            acc = collections.defaultdict(lambda: collections.defaultdict(list)); unk = 0; st = []
            for sel in seeds:
                assert set(sel) == set(rows), (d, a, len(sel), len(rows))
                ts = []
                for k in rows:
                    o = outcome(sel[k], lab, k); mk, K = rows[k]["masks"], rows[k]["K_legacy"]
                    unk += o == "UNKNOWN"
                    if mk["eval_task"]:
                        acc["task"][k].append(o == "SUCCESS"); acc[f"task_K{K}"][k].append(o == "SUCCESS"); ts.append(o == "SUCCESS")
                    if mk["eval_abstain"]:
                        acc["abstain"][k].append(o == "ABSTAIN")
                    if mk["eval_noop"]:
                        acc["noop"][k].append(o == "NOOP")
                st.append(float(np.mean(ts)))
            m = {key: {k: float(np.mean(v)) for k, v in dd.items()} for key, dd in acc.items()}
            per[a] = m
            R[a] = {"unknown_selected": unk, "task_per_seed": st, "task_seed_sd": float(np.std(st)), **{key: float(np.mean(list(v.values()))) for key, v in m.items()},
                    "n_task_roots": len(m["task"]), "n_none_roots": len(m["abstain"])}
        a, b = per[f"D-expanded_M{M}"], per["capped_V3_M4_B4096"]
        if R[f"D-expanded_M{M}"]["unknown_selected"] == 0 and R["capped_V3_M4_B4096"]["unknown_selected"] == 0:
            for key in ("task", "abstain", "noop"):
                c = sorted(set(a[key]) & set(b[key]))
                R[f"D-expanded_M{M}"][f"delta_{key}_vs_capped"] = boot([a[key][k] - b[key][k] for k in c])
        res[d] = R
        print("=====", d)
        for k, x in R.items():
            f = lambda t: "" if not t else f"{100*t[0]:+.1f} [{100*t[1]:+.1f}, {100*t[2]:+.1f}]"  # noqa: E731
            print(f"  {k:20s} task {100*x['task']:.1f}+-{100*x['task_seed_sd']:.1f}  K {100*x['task_K1']:.0f}/{100*x['task_K2']:.0f}/{100*x['task_K3']:.0f}"
                  f"  abst {100*x['abstain']:.1f}  noop {100*x['noop']:.1f}  unk {x['unknown_selected']}  dTask {f(x.get('delta_task_vs_capped'))}"
                  f"  dAbst {f(x.get('delta_abstain_vs_capped'))}  dNoop {f(x.get('delta_noop_vs_capped'))}")
    Path(out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
