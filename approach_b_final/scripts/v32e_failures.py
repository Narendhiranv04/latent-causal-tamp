"""V3.2 E2 / failure attribution on VALIDATION task roots: for each arm (capped frozen, exhaustive frozen V3 D s0, D-control s0-2, D-expanded s0-2)
and M, each task root's verified top-1 outcome is classed as
  SUCCESS | RANK_FAIL_<Y|X|ABSTAIN|NOOP> (a known X=1/Y=1 sequence WAS in the scored pool, but the selected one failed / no repair chosen)
          | COVER_UNKNOWN_<...>        (no known success in the pool; an unknown feasible one may still exist -> lower bound on coverage)
          | UNKNOWN (unlabelled; never counted as failure)
Known-success-in-pool comes from the exhaustive records (known X=1, Y=1 snapshot labels of that root that lie in the top-M pool).
usage: v32e_failures.py SNAP FROZEN_RUNDIR TRAINED_RUNDIR OUT_JSON CACHE_GLOB_2D CACHE_GLOB_3D"""
import collections, glob, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v32b_phys import GRID, RULE, labels, outcome  # noqa: E402

RI = GRID.index(RULE)


def jl(p):
    return [json.loads(l) for l in open(p)]


def main():
    snap, frozen, trained, out, g2, g3 = sys.argv[1:7]
    res = {}
    for d, g in (("2d", g2), ("3d", g3)):
        rows = {r["root_id"]: r for r in jl(Path(snap) / f"data{d}.jsonl") if r["split"] == "val" and r["masks"]["eval_task"]}
        lab = labels(d, g)
        ex = {r["root_id"]: r for r in jl(Path(frozen) / d / "ex_M6_val.jsonl") if r["root_id"] in rows}
        capped = {r["root_id"]: r for r in jl(Path(frozen) / d / "old_M4_B4096_val.jsonl") if r["root_id"] in rows}
        arms = {"frozen_V3D_s0": [ex]}
        for arm in ("control", "expanded"):
            arms[arm] = []
            for s in (0, 1, 2):
                rec = {}
                for p in sorted(glob.glob(f"{trained}/{d}/{arm}_s{s}_M6_val*.jsonl")):
                    rec.update({r["root_id"]: r for r in jl(p) if r["root_id"] in rows})
                if rec:
                    arms[arm].append(rec)
        R = {}
        cs = collections.defaultdict(collections.Counter)
        for k, r in capped.items():                                     # capped: pool = run_root's stored pool (known_success_in_pool from oldpath)
            o = outcome(r["selected"], lab, k)
            cls = "SUCCESS" if o == "SUCCESS" else "UNKNOWN" if o == "UNKNOWN" else (("RANK_FAIL_" if r["known_success_in_pool"] else "COVER_UNKNOWN_") + o.replace("FAIL_", ""))
            cs["all"][cls] += 1; cs["K" + rows[k]["K_legacy"]][cls] += 1
        R["capped_M4_B4096"] = {g_: dict(c) for g_, c in cs.items()}
        for arm, recs in arms.items():
            for M in ("4", "5", "6"):
                cs = collections.defaultdict(collections.Counter)
                for rec in recs:
                    for k, r in rec.items():
                        dec = r["per_M"][M]["decisions"][RI]
                        o = outcome(None if dec is None else dec["seq"], lab, k)
                        kin = r["per_M"][M]["known_success_in_pool"] > 0
                        cls = "SUCCESS" if o == "SUCCESS" else "UNKNOWN" if o == "UNKNOWN" else (("RANK_FAIL_" if kin else "COVER_UNKNOWN_") + o.replace("FAIL_", ""))
                        cs["all"][cls] += 1; cs["K" + rows[k]["K_legacy"]][cls] += 1
                        cs["all"]["known_in_pool"] += kin; cs["K" + rows[k]["K_legacy"]]["known_in_pool"] += kin
                n = len(recs)
                R[f"{arm}_M{M}"] = {g_: {c: v / n for c, v in cnt.items()} for g_, cnt in cs.items()} | {"seeds": n}
        res[d] = R
        print("=====", d, "task roots", len(rows))
        for a, x in R.items():
            al = x["all"]; tot = sum(v for c, v in al.items() if c != "known_in_pool")
            print(f"  {a:18s} " + "  ".join(f"{c} {100 * v / tot:.1f}" for c, v in sorted(al.items()) if c != "known_in_pool")
                  + (f"  | known-in-pool {100 * al.get('known_in_pool', 0) / tot:.1f}" if "known_in_pool" in al else ""))
    Path(out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
