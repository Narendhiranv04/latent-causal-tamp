"""V3.3 teacher-free screening.
    v33_proposals.py dump DOM SPLIT KIND SEED OUT_JSONL      top-6 S1 proposals (exhaustive.proposals: per-root generator seed 0, the scoring
                                                           path's exact RNG stream) for every root; sampler from V3_TASK_STAGE / KIND / SEED
    v33_proposals.py cover SNAP CACHE_GLOB_2D CACHE_GLOB_3D OUT_JSON NAME=DIR ...   known-success coverage at M4/5/6 from dumps DIR/<dom>.jsonl
A root is covered at M if some KNOWN positive assignment (Y = 1 endpoint with an X = 1 order; base snapshot labels + verify caches) has every
action (object, destination) inside the top-M proposals of its object.  Known labels are incomplete -> coverage is a lower bound."""
import collections, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def dump(dom, split, kind, seed, out):
    import construct as CO
    import exhaustive as EX
    import search as S
    samp = CO.make_sampler(dom, kind, int(seed), CO.RULES["S1"])
    with open(out, "w") as f:
        for r in EX.rows_of(dom, split):
            root = S.Root(r, dom)
            f.write(json.dumps({"root_id": r["root_id"], "D6": {str(o): v for o, v in EX.proposals(root, samp).items()}}) + "\n")


def known(snap, dom, g):
    import contracts as CT
    from v32b_phys import labels
    lab = labels(dom, g)
    rows = {r["root_id"]: r for r in map(json.loads, open(Path(snap) / f"data{dom}.jsonl")) if r["split"] == "val"}
    Y, X = collections.defaultdict(dict), collections.defaultdict(set)
    for rid, r in rows.items():
        for y in r["labels"]["Y"]:
            Y[rid][CT.ekey(y["edit"])] = y["y"]
        for q in r["labels"]["X"]:
            if q["x"] == 1 and q["seq"]:
                X[rid].add(CT.ekey(q["seq"]))
    for (rid, s), (xv, yv) in lab.items():
        seq = json.loads(s)
        if rid in rows and seq:
            if yv in (0, 1):
                Y[rid].setdefault(CT.ekey(seq), yv)
            if xv == 1:
                X[rid].add(CT.ekey(seq))
    return rows, {rid: [json.loads(k) for k in X[rid] if Y[rid].get(k) == 1] for rid in rows}


def cover(snap, g2, g3, out, arms):
    res = {}
    for dom, g in (("2d", g2), ("3d", g3)):
        rows, pos = known(snap, dom, g)
        res[dom] = {"val_roots": len(rows), "task_roots": sum(r["masks"]["eval_task"] for r in rows.values()),
                    "task_roots_with_known_positive": sum(bool(pos[k]) for k, r in rows.items() if r["masks"]["eval_task"]), "arms": {}}
        for name, d in arms:
            D = {json.loads(l)["root_id"]: json.loads(l)["D6"] for l in open(Path(d) / f"{dom}.jsonl")}
            assert set(D) == set(rows), (name, dom)
            a = {}
            for M in (4, 5, 6):
                per = collections.defaultdict(list)
                for k, r in rows.items():
                    D6 = D[k]
                    hit = any(all(str(o) in D6 and c in D6[str(o)][:M] for o, c in A) for A in pos[k])
                    if r["masks"]["eval_task"]:
                        per["task"].append(hit); per["K" + r["K_legacy"]].append(hit)
                    uniq = {(o, c) for o, v in D6.items() for c in v[:M]}
                    per["unique_actions"].append(len(uniq))
                    per["n_movable"].append(len(D6))
                a[M] = {k: float(np.mean(v)) for k, v in per.items()} | {"n_task": len(per["task"])}
                a[M]["per_root_task"] = {k: any(all(str(o) in D[k] and c in D[k][str(o)][:M] for o, c in A) for A in pos[k])
                                         for k, r in rows.items() if r["masks"]["eval_task"]} if M == 4 else None
            res[dom]["arms"][name] = a
            print(dom, name, {M: round(a[M]["task"], 4) for M in (4, 5, 6)}, flush=True)
    Path(out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "dump":
        dump(*sys.argv[2:7])
    elif sys.argv[1] == "cover":
        cover(*sys.argv[2:6], [a.split("=", 1) for a in sys.argv[6:]])
    else:
        raise SystemExit(__doc__)
