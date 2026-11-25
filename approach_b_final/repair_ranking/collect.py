#!/usr/bin/env python3
"""P3: deterministic TRAIN acquisition manifest, teacher job file, and strict label merge into an augmented TRAIN snapshot (private).
    python collect.py manifest     # -> reports/P3_MANIFEST.jsonl (+ SEAL), ~/xyrr_private/p3_jobs_2d.jsonl
    python collect.py merge CACHE  # -> ~/xyrr_private/snap_aug/data2d.jsonl, reports/P3_COUNTS.json
Candidates come from the frozen cVAE + frozen s0 scorer on PUBLIC TRAIN inputs; original TRAIN labels are used only to (a) choose verified
positive anchors for contrasts and (b) skip sequences already labelled.  No VAL / CONFIRM / TEST root is touched."""
from __future__ import annotations

import collections, hashlib, itertools, json, random, sys
from pathlib import Path

import numpy as np

import rr
import diagnostics as D

QUOTA = {"HIGHCONF": 540, "DEST": 450, "OBJSET": 360, "ORDER": 270, "RANDOM": 180}           # plan 8.1 shares of 1,800
N_ROOTS = {"1": 190, "2": 170}
GV_ROOTS = "/home/projects/long-horizon/naren_workspace/k3abl/abf/mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/raw/roots"


def roster():
    av = set((rr.PRIV / "train_roots_on_gvlab2.txt").read_text().split())
    rows = [r for r in rr.snapshot_rows("train") if r["root_id"] in av]
    out = []
    for K, n in N_ROOTS.items():
        rs = sorted((r for r in rows if r["K_legacy"] == K), key=lambda r: rr.hx("XYRR_P3_ROSTER|", r["root_id"]))
        out += rs[:n]
    return sorted(out, key=lambda r: rr.hx("XYRR_P3_ORDER|", r["root_id"]))


def candidates(r, ent, net, rng):
    """Per-category ordered candidate lists for one TRAIN root."""
    import search as S
    R = S.Root(r, "2d"); rk = rr.Ranks(ent); L = R.legal_dests(R.cells0); mv = R.movable
    labelled = {json.dumps([[int(i), int(c)] for i, c in q["seq"]]) for q in r["labels"]["X"]}
    Y = {json.dumps(sorted([int(i), int(c)] for i, c in y["edit"])): y["y"] for y in r["labels"]["Y"]}
    anchors = [[[int(i), int(c)] for i, c in q["seq"]] for q in r["labels"]["X"]
               if q["x"] == 1 and Y.get(json.dumps(sorted([int(i), int(c)] for i, c in q["seq"]))) == 1 and rr.legal_k2(r, q["seq"])]
    anchors = sorted({json.dumps(a): a for a in anchors}.values(), key=lambda a: (len(a), json.dumps(a)))
    tier_cells = lambda o, t: [d for d in L if rk.tier((o, d)) == t]  # noqa: E731
    D12 = collections.defaultdict(list)
    for (o, d), k in rk.rank.items():
        if k <= 12:
            D12[o].append(d)
    D12 = {o: sorted(v, key=lambda d: rk.rank[(o, d)]) for o, v in D12.items()}
    samp = []
    for _ in range(600):                                                      # score-independent full-domain draws (tail coverage)
        k = rng.choice([1, 2]); objs = rng.sample(mv, min(k, len(mv))); ds = rng.sample(L, len(objs))
        samp.append([[o, d] for o, d in zip(objs, ds)])
    pool = D.pool(D12, 12) + samp
    ok = lambda s: rr.legal_k2(r, s)  # noqa: E731
    cat = {}
    # 1 HIGHCONF: best order per set, highest frozen p11, unlabelled
    sc = rr.readout(net, [(r, pool)])[0]["rows"]
    best = {}
    for s, x in zip(pool, sc):
        k = json.dumps(sorted(s))
        if json.dumps(s) not in labelled and (k not in best or x["p11"] > best[k][1]):
            best[k] = (s, x["p11"])
    cat["HIGHCONF"] = [s for s, p in sorted(best.values(), key=lambda t: (-t[1], json.dumps(t[0])))]
    # 2 DEST: same object set, one destination replaced by a rank 5-6 / 7-12 / >12 cell (cycled)
    dest = []
    for t in ("T56", "R7_12", "TAIL", "T56", "R7_12", "TAIL"):
        for a in anchors:
            j = rng.randrange(len(a)); o = a[j][0]
            cs = [d for d in tier_cells(o, t) if d not in {x[1] for x in a}]
            if cs:
                s = [list(x) for x in a]; s[j] = [o, rng.choice(cs)]; dest.append(s)
    cat["DEST"] = dest
    # 3 OBJSET: omission, object substitution (same destination), addition of a compatible move
    obs = []
    for a in anchors:
        if len(a) == 2:
            obs += [[a[0]], [a[1]]]
        used = {x[0] for x in a}
        others = [o for o in mv if o not in used]
        if others:
            j = rng.randrange(len(a)); s = [list(x) for x in a]; s[j] = [rng.choice(others), a[j][1]]; obs.append(s)
        if len(a) == 1 and others:
            o = rng.choice(others); d = next((d for d in D12.get(o, []) if d != a[0][1]), None)
            if d is not None:
                obs.append([a[0], [o, d]])
    cat["OBJSET"] = obs
    # 4 ORDER: other order of labelled / anchor / high-confidence K2 sequences
    k2 = [json.loads(x) for x in sorted(labelled) if len(json.loads(x)) == 2] + [s for s in cat["HIGHCONF"][:3] if len(s) == 2]
    cat["ORDER"] = [s[::-1] for s in k2]
    # 5 RANDOM: score-independent uniform legal sets, alternating length
    rnd = []
    for i in range(12):
        k = 1 + i % 2; objs = rng.sample(mv, min(k, len(mv))); ds = rng.sample(L, len(objs))
        s = [[o, d] for o, d in zip(objs, ds)]; rng.shuffle(s); rnd.append(s)
    cat["RANDOM"] = rnd
    for k in cat:
        seen, keep = set(), []
        for s in cat[k]:
            j = json.dumps(s)
            if ok(s) and j not in labelled and j not in seen:
                seen.add(j); keep.append(s)
        cat[k] = keep
    return cat, {"anchors": len(anchors)}


def manifest():
    samp, _, _ = rr.bundle()
    net = rr.load_net(rr.scorer_path(0))
    ros = roster()
    cv = rr.cvae_table(ros, samp, "train")
    C, meta = {}, {}
    for r in ros:
        rng = random.Random(rr.hx("XYRR_P3_RNG|", r["root_id"]) % 2 ** 32)
        C[r["root_id"]], meta[r["root_id"]] = candidates(r, cv[r["root_id"]], net, rng)
    taken = collections.defaultdict(set); man = []; left = dict(QUOTA); ptr = {k: collections.Counter() for k in QUOTA}
    order = [r["root_id"] for r in ros]
    for k in ("ORDER", "HIGHCONF", "DEST", "OBJSET", "RANDOM"):              # deterministic round-robin; leftover rolls to RANDOM
        while left[k] > 0:
            prog = False
            for rid in order:
                if left[k] == 0:
                    break
                lst = C[rid][k]
                while ptr[k][rid] < len(lst) and json.dumps(lst[ptr[k][rid]]) in taken[rid]:
                    ptr[k][rid] += 1
                if ptr[k][rid] < len(lst):
                    s = lst[ptr[k][rid]]; ptr[k][rid] += 1; taken[rid].add(json.dumps(s))
                    man.append({"root_id": rid, "category": k, "seq": s}); left[k] -= 1; prog = True
            if not prog:
                if k != "RANDOM":
                    left["RANDOM"] += left[k]
                left[k] = 0
    rows = {r["root_id"]: r for r in ros}
    cv_ = cv
    for m in man:
        m["max_tier"] = rr.Ranks(cv_[m["root_id"]]).seq_info(m["seq"])["max_tier"]; m["K"] = rows[m["root_id"]]["K_legacy"]
    out = rr.REP / "P3_MANIFEST.jsonl"
    out.write_text("".join(json.dumps(m) + "\n" for m in man))
    jobs = collections.defaultdict(list)
    for m in man:
        jobs[m["root_id"]].append(m["seq"])
    with open(rr.PRIV / "p3_jobs_2d.jsonl", "w") as f:
        for rid in order:
            if rid in jobs:
                ids = rows[rid]["inputs"]["ids"]
                f.write(json.dumps({"root_id": rid, "dom": "2D", "path": f"{GV_ROOTS}/{rid}.json", "geom": "original", "ids": ids,
                                    "seqs": [[[ids[o], int(c)] for o, c in s] for s in jobs[rid]]}) + "\n")
    summ = {"queries": len(man), "roots": len(jobs), "by_category": dict(collections.Counter(m["category"] for m in man)),
            "by_K": dict(collections.Counter(m["K"] for m in man)), "by_max_tier": dict(collections.Counter(m["max_tier"] for m in man)),
            "by_len": dict(collections.Counter(len(m["seq"]) for m in man)), "roots_with_anchor": sum(1 for v in meta.values() if v["anchors"]),
            "manifest_sha256": rr.sha(out), "jobs_sha256": rr.sha(rr.PRIV / "p3_jobs_2d.jsonl"), "snapshot_sha256": rr.sha(rr.SNAP / "data2d.jsonl")}
    rr.wjson(rr.REP / "P3_MANIFEST.SEAL.json", summ)
    print(json.dumps(summ, indent=1))


# ------------------------------------------------------------------------------------------------------------- merge (after teacher)
def merge(cache):
    """Strict merge: X added iff VERIFIED / CERTIFIED_*; Y (endpoint) added iff decided and not already labelled; conflicts quarantined."""
    man = rr.jl(rr.REP / "P3_MANIFEST.jsonl")
    want = {(m["root_id"], json.dumps(m["seq"])): m for m in man}
    lab = rr.strict_labels([Path(cache)])
    rows = rr.jl(rr.SNAP / "data2d.jsonl")
    c = collections.Counter(); per = collections.defaultdict(lambda: collections.Counter()); quarantine = []
    for r in rows:
        if r["split"] != "train":
            continue
        rid = r["root_id"]
        Y = {json.dumps(sorted([int(i), int(cc)] for i, cc in y["edit"])): y for y in r["labels"]["Y"]}
        Xs = {json.dumps([[int(i), int(cc)] for i, cc in q["seq"]]) for q in r["labels"]["X"]}
        for (rr_, sq), m in want.items():
            if rr_ != rid:
                continue
            e = lab.get((rid, sq))
            c["manifest"] += 1
            if e is None:
                c["missing_from_cache"] += 1; continue
            if e["conflict"]:
                c["conflict_quarantined"] += 1; quarantine.append([rid, sq]); continue
            seq = json.loads(sq); ep = json.dumps(sorted(seq))
            if e["y"] is not None:
                if ep in Y:
                    if Y[ep]["y"] != e["y"]:
                        c["endpoint_conflict_with_original_quarantined"] += 1; quarantine.append([rid, sq]); continue
                    c["endpoint_already_labelled_agree"] += 1
                else:
                    Y[ep] = {"edit": sorted(seq), "y": int(e["y"]), "kinds": [f"XYRR_P3_{m['category']}"]}
                    r["labels"]["Y"].append(Y[ep]); c["new_Y"] += 1
            if e["x"] is not None and sq not in Xs:
                r["labels"]["X"].append({"seq": seq, "x": int(e["x"]), "kind": f"XYRR_P3_{m['category']}", "x_witnesses": [], "x_provenance": "XYRR_P3 benchmark.teach (exact contract)"})
                Xs.add(sq); c["new_X"] += 1
            z = rr.z_logic(e["x"], e["y"])
            c[f"z_{z}"] += 1; c[f"hist_{rr.z_hist(e['x'], e['y'])}"] += 1
            per[m["category"]][f"z_{z}"] += 1; per[m["max_tier"]][f"z_{z}"] += 1
    out = rr.PRIV / "snap_aug"; out.mkdir(parents=True, exist_ok=True)
    with open(out / "data2d.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    # support gates
    pairs = 0; tailroots = 0
    for r in rows:
        if r["split"] != "train":
            continue
        Y = {json.dumps(sorted([int(i), int(cc)] for i, cc in y["edit"])): y["y"] for y in r["labels"]["Y"]}
        zs = [rr.z_logic(q["x"], Y.get(json.dumps(sorted([int(i), int(cc)] for i, cc in q["seq"])))) for q in r["labels"]["X"]]
        pairs += (1 in zs) and (0 in zs)
    newtail = {m["root_id"] for (rid, sq), m in want.items() if m["max_tier"] in ("R7_12", "TAIL") and lab.get((rid, sq)) and rr.z_logic(lab[(rid, sq)]["x"], lab[(rid, sq)]["y"]) is not None}
    tailroots = len(newtail)
    res = {"counts": dict(c), "by_category_and_tier": {k: dict(v) for k, v in per.items()}, "quarantined": len(quarantine),
           "train_roots_with_Z+_and_Z-_after_merge": pairs, "roots_with_new_decided_rank>6_candidates": tailroots,
           "gate_pairs>=100": pairs >= 100, "gate_tail_roots>=50": tailroots >= 50,
           "original_snapshot_sha256": rr.sha(rr.SNAP / "data2d.jsonl"), "augmented_snapshot_sha256": rr.sha(out / "data2d.jsonl"), "cache_sha256": rr.sha(cache)}
    rr.wjson(rr.REP / "P3_COUNTS.json", res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"manifest": manifest, "merge": lambda: merge(sys.argv[2])}[sys.argv[1]]()
