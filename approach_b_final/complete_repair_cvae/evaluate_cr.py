#!/usr/bin/env python3
"""Evaluator side (plan.md 5-6): DEV diagnostics on VAL, locked-cohort public rows, seals, teacher manifests, strict / operational outcomes,
paired family-cluster statistics.  This module reads private labels; planner code (infer.py) never imports it.

    python evaluate_cr.py devids                      -> reports/P2_DEV_IDS.json (100 DEV roots / domain, 20 per legacy stratum; 20 timing roots)
    python evaluate_cr.py dev DOM PRED [SEEDPRED...]  -> reports/P2_DEV_<dom>.json (recall, diversity, decisions, retrospective labels)"""
from __future__ import annotations

import collections, json, sys
from pathlib import Path

import numpy as np

import data as D

REP = D.HERE / "reports"
ARMS = ("C0", "C1", "C2")


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def wj(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1, default=str))


def q(x, f):
    return float(np.percentile(x, f)) if len(x) else None


# ------------------------------------------------------------------------------------------------ DEV (VAL) diagnostics
def devids():
    out = {}
    for dom in ("2d", "3d"):
        rr = D.rows(dom, D.VAL_SNAP, "val")
        ids = []
        for K in ("0", "1", "2", "3", "NONE"):
            ids += sorted((r["root_id"] for r in rr if r["K_legacy"] == K), key=lambda x: D.stratum_hash("CRCVAE_DEV100", x))[:20]
        out[dom] = ids
        out[dom + "_timing"] = sorted(ids, key=lambda x: D.stratum_hash("CRCVAE_WALL_V1", x))[:20]
    wj(REP / "P2_DEV_IDS.json", out)
    print({k: len(v) for k, v in out.items()})


def known(row):
    """Known verified witnesses (TRAIN/VAL labels): ordered keys, assignment keys, object sets."""
    vo = D.verified_orders(row)
    orders = {x for v in vo.values() for x in v}
    return orders, set(vo), {json.dumps(sorted(o for o, _ in json.loads(v[0]))) for v in vo.values()}


def keys(seq):
    return json.dumps([[int(o), int(d)] for o, d in seq]), json.dumps(sorted(map(tuple, seq))).replace("(", "[").replace(")", "]"), json.dumps(sorted(o for o, _ in seq))


def label_of(row, seq):
    """Retrospective snapshot label of an exact ordered sequence -> SUCCESS / FAIL_X / FAIL_Y / UNLABELLED (selection-biased; DEV only)."""
    import contracts as CT
    if seq is None or seq == []:
        return None
    Y = {CT.ekey(y["edit"]): y["y"] for y in row["labels"]["Y"]}
    X = {json.dumps(q_["seq"]): q_["x"] for q_ in row["labels"]["X"]}
    y, x = Y.get(CT.ekey(seq)), X.get(json.dumps([[int(o), int(d)] for o, d in seq]))
    return "FAIL_Y" if y == 0 else "SUCCESS" if (y == 1 and x == 1) else "FAIL_X" if (y == 1 and x == 0) else "UNLABELLED"


def pool_stats(rec, row, budgets):
    """Recall of known witnesses + diversity at every nested budget (pool order = first appearance; budget b = first b draws)."""
    ko, ka, ks = known(row)
    out = {}
    for b in budgets:
        acct = rec["pool_acct"][str(b)]
        out[b] = {"unique": acct["unique"], "dup_rate": acct["dup_draws"] / max(1, acct["raw"] - acct["no_candidate"]),
                  "no_candidate": acct["no_candidate"], "illegal": acct["illegal"]}
    return out, (ko, ka, ks)


def dev(dom, pred, *seed_preds):
    rows = {r["root_id"]: r for r in D.rows(dom, D.VAL_SNAP, "val")}
    P = jl(pred)
    lay = layout_overlap(dom)
    budgets = sorted(int(b) for b in P[0]["pool_acct"])
    res = {"dom": dom, "n": len(P), "budgets": budgets, "main": P[0]["main_budget"], "layout_overlap_roots": len(lay)}
    # pools: the stored main pool + accounting; recall at other budgets needs the pool at that budget -> recomputed from 'pool_by_budget'
    R = collections.defaultdict(list)
    lens = collections.Counter()
    off4, n_act = 0, 0
    for p in P:
        row = rows[p["root_id"]]
        ko, ka, ks = known(row)
        for b in budgets:
            a = p["pool_acct"][str(b)]
            R[f"unique@{b}"].append(a["unique"]); R[f"dup_rate@{b}"].append(a["dup_draws"] / max(1, a["raw"] - a["no_candidate"]))
            R[f"no_candidate@{b}"].append(a["no_candidate"] / a["raw"]); R[f"illegal@{b}"].append(a["illegal"])
        pool = p["pool"]
        K = {k for s in pool for k in [keys(s)]}
        o_, a_, s_ = {k[0] for k in K}, {k[1] for k in K}, {k[2] for k in K}
        R["objsets_in_pool"].append(len(s_)); R["assignments_in_pool"].append(len(a_))
        for s in pool:
            lens[len(s)] += 1
        if "C0" in p:
            t4 = {int(k): set(v) for k, v in p["C0"]["proposals"].items()}
            for s in pool:
                for o, d in s:
                    n_act += 1; off4 += d not in t4.get(o, set())
        if ko:
            g = "excl_layout" if p["root_id"] not in lay else "layout_overlap"
            for bb in budgets:
                Kb = [keys(s) for s, f in zip(p["pool_bmax"], p["pool_bmax_first_draw"]) if f < bb]
                for name, j, kk in (("order", 0, ko), ("assignment", 1, ka), ("objset", 2, ks)):
                    R[f"recall_{name}@{bb}"].append(bool({k[j] for k in Kb} & kk))
            for name, have, kk in (("order", o_, ko), ("assignment", a_, ka), ("objset", s_, ks)):
                R[f"recall_{name}@{p['main_budget']}|{g}"].append(bool(have & kk))
                R[f"recall_{name}@{p['main_budget']}|K{row['K_legacy']}"].append(bool(have & kk))
            if "C0" in p:
                t4 = {int(k): set(v) for k, v in p["C0"]["proposals"].items()}
                inC0 = lambda s: all(d in t4.get(o, set()) for o, d in json.loads(s))  # noqa: E731
                R["C0_recall_assignment"].append(any(inC0(x) for x in ko))          # C0 keeps every order -> order recall = assignment recall
                R[f"C0_recall_assignment|K{row['K_legacy']}"].append(any(inC0(x) for x in ko))
            ll = p["C1"]["loglik"]
            if ll and o_ & ko:
                rk = sorted(range(len(pool)), key=lambda i: -ll[i])
                R["C1_rank_best_known"].append(min(rk.index(i) for i, s in enumerate(pool) if keys(s)[0] in ko) + 1)
                p11 = p["C2"]["p11"]
                rk2 = sorted(range(len(pool)), key=lambda i: -p11[i])
                R["C2_rank_best_known"].append(min(rk2.index(i) for i, s in enumerate(pool) if keys(s)[0] in ko) + 1)
        for arm in ARMS + ("C1_common_gate",):
            if arm in p and not p[arm].get("props_only"):
                x = p[arm]
                R[f"{arm}_decision|K{row['K_legacy']}"].append(x["decision"])
                R[f"{arm}_label|K{row['K_legacy']}"].append(label_of(row, x["seq"]) if x["decision"] == "REPAIR" else x["decision"])
        R[f"head|label{D.root_label(row, D.verified_orders(row))}"].append(p["C1"]["head"])
        R["C1_select_s"].append(p["C1"]["select_s"]); R["C2_select_s"].append(p["C2"]["select_s"]); R["sample_s_bmax"].append(p["sample_s_bmax"])
        R["C1_decoder_passes"].append(p["C1"]["decoder_passes"])
        if "C0" in p and not p["C0"].get("props_only"):
            R["C0_total_s"].append(p["C0"]["timing_s"]["total"])
        if "C0" in p:
            R["C0_n_scored"].append(p["C0"]["n_scored"])
        R["first_draw_is_known"].append(bool(p["first_draw"]) and keys(p["first_draw"])[0] in ko if ko else None)
    agg = {}
    for k, v in R.items():
        if v and isinstance(v[0], str) or (v and v[0] is None and any(isinstance(x, str) for x in v)):
            agg[k] = dict(collections.Counter(map(str, v)))
        elif v and all(isinstance(x, (bool, np.bool_)) for x in v if x is not None):
            vv = [x for x in v if x is not None]
            agg[k] = {"n": len(vv), "rate": round(float(np.mean(vv)), 4) if vv else None}
        else:
            vv = np.array([x for x in v if x is not None], float)
            agg[k] = {"n": len(vv), "mean": round(float(vv.mean()), 5), "p50": q(vv, 50), "p90": q(vv, 90), "max": float(vv.max())} if len(vv) else None
    res["agg"] = agg
    res["pool_length_dist"] = dict(lens)
    res["off_top4_action_rate"] = off4 / n_act if n_act else None
    res["seed_stability"] = {}
    for sp in seed_preds:
        Q = {r["root_id"]: r for r in jl(sp)}
        rec = []
        for p in P:
            ko, _, _ = known(rows[p["root_id"]])
            if ko and p["root_id"] in Q:
                rec.append(bool({keys(s)[0] for s in Q[p["root_id"]]["pool"]} & ko))
        res["seed_stability"][Path(sp).name] = {"recall_order@main": float(np.mean(rec)) if rec else None, "n": len(rec),
                                                "unique_mean": float(np.mean([Q[k]["pool_acct"][str(res["main"])]["unique"] for k in Q]))}
    wj(REP / f"P2_DEV_{dom}.json", res)
    show = {k: v for k, v in agg.items() if k.startswith(("recall_order", "recall_assignment", "recall_objset", "C0_recall_assignment", "unique@", "dup_rate@"))
            and "|" not in k}
    print(json.dumps(show, indent=0)[:3000])
    return res


def layout_overlap(dom):
    def fp(r):
        inp = r["inputs"]
        return json.dumps([sorted(int(c) for i, c in enumerate(inp["cells0"]) if i != inp["tid"]), int(inp["cells0"][inp["tid"]]), int(inp["goal_cell"])])
    tr = {fp(r) for r in D.rows(dom, D.TRAIN_SNAP, "train")}
    return {r["root_id"] for r in D.rows(dom, D.VAL_SNAP, "val") if fp(r) in tr}

# ------------------------------------------------------------------------------------------------ P3: locked cohort public rows, seal
V34 = D.H / "abf_v34"
P3 = D.RUNS / "p3"
P4 = D.RUNS / "p4"
TIERS = ("T1_task_C1C2", "T2_C0_uncached", "T3_safeguard")


def roster(dom):
    return {e["root_id"]: e for e in jl(D.PRIV / f"cohort_{dom}.jsonl")}


def cohort_public():
    """Public rows (root_id, domain, inputs) of the roster, copied from the V3.4 sealed public files (no K / labels / paths)."""
    P3.mkdir(parents=True, exist_ok=True)
    out = {}
    for dom in ("2d", "3d"):
        ids = set(roster(dom))
        rows = [r for b in ("batchA", "batchB") for r in jl(V34 / b / f"public_{dom}.jsonl") if r["root_id"] in ids]
        rows.sort(key=lambda r: r["root_id"])
        assert len(rows) == len(ids) and set(rows[0]) == {"root_id", "domain", "inputs"}, (dom, len(rows))
        with open(P3 / f"public_{dom}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r, sort_keys=True) + "\n")
        out[dom] = {"n": len(rows), "sha256": D.sha(P3 / f"public_{dom}.jsonl")}
    print(out)
    return out


def bench_row(rec, arm, ids):
    x = rec[arm]
    moves = [{"object_id": ids[o], "object_index": o, "destination_cell": int(c)} for o, c in (x["seq"] if x["decision"] == "REPAIR" else [])]
    return {"root_id": rec["root_id"], "domain": rec["domain"], "decision": x["decision"], "moves": moves, "arm": arm,
            "score_type": x.get("score_type", "p11"), "score": x.get("score")}


def seal(freeze):
    """Per-arm prediction files (benchmark schema) + one SEAL manifest: sha256 of every file, C1/C2 pool-hash identity, C0 vs V3.4 sealed picks,
    static legality of every prediction (benchmark.validate).  Must run before any teacher call on these predictions."""
    import benchmark as BM
    fr = json.loads(Path(freeze).read_text())
    man = {"freeze": fr, "freeze_sha256": D.sha(freeze), "domains": {}}
    for dom in ("2d", "3d"):
        recs = jl(P3 / f"pred_{dom}.jsonl")
        pub = {r["root_id"]: r for r in jl(P3 / f"public_{dom}.jsonl")}
        assert set(r["root_id"] for r in recs) == set(pub), "prediction missing for a roster root"
        for r in recs:
            assert r["C2_pool_hash"] == r["pool_hash"][str(r["main_budget"])], r["root_id"]
            assert r["ckpt_sha256"] == fr["checkpoints"][dom]["sha256"]
        files = {}
        for arm in ARMS + ("C1_common_gate", "C3", "C4"):
            if arm not in recs[0]:
                continue
            fp = P3 / f"sealed_{arm}_{dom}.jsonl"
            with open(fp, "w") as f:
                for r in recs:
                    f.write(json.dumps(bench_row(r, arm, pub[r["root_id"]]["inputs"]["ids"])) + "\n")
            v, c = BM.validate(P3 / f"public_{dom}.jsonl", fp, quiet=True)
            assert not any(v.values()), (arm, dom, c)
            files[fp.name] = {"sha256": D.sha(fp), "validate": dict(c)}
        v34 = {r["root_id"]: r for b in ("batchA", "batchB") for r in jl(V34 / b / f"pred_{dom}.jsonl")}
        same = sum(1 for r in recs if v34[r["root_id"]]["decision"] == r["C0"]["decision"] and
                   [[m["object_index"], m["destination_cell"]] for m in v34[r["root_id"]]["moves"]] == (r["C0"]["seq"] if r["C0"]["decision"] == "REPAIR" else []))
        man["domains"][dom] = {"n": len(recs), "records_sha256": D.sha(P3 / f"pred_{dom}.jsonl"), "public_sha256": D.sha(P3 / f"public_{dom}.jsonl"),
                               "files": files, "C1_C2_pool_hash_identical": True, "C0_equals_V34_sealed": same,
                               "pool_hashes_sha256": __import__("hashlib").sha256("".join(r["C2_pool_hash"] for r in recs).encode()).hexdigest()}
    import time
    man["sealed_utc"] = time.strftime("%FT%TZ", time.gmtime())
    man["statement"] = "sealed before any physical teacher call on these predictions; checkpoints, budgets, rule and roster frozen in P2_FREEZE"
    wj(REP / "P3_SEAL.json", man)
    import shutil
    (REP / "sealed").mkdir(exist_ok=True)
    for dom in ("2d", "3d"):
        for fn in man["domains"][dom]["files"]:
            shutil.copyfile(P3 / fn, REP / "sealed" / fn)                  # compact per-arm predictions are committed with the seal
    print(json.dumps({d: {k: v for k, v in x.items() if k != "files"} for d, x in man["domains"].items()}))


# ------------------------------------------------------------------------------------------------ labels: caches, strict / operational
def cache_files(dom):
    return [V34 / b / "cache" / f"verify_{dom}.jsonl" for b in ("batchA", "batchB")] + sorted(P4.glob(f"cache/verify_{dom}*.jsonl"))


def factor(dom, r, kind):
    """One teacher factor -> (strict value or None, operational value or None, status string)."""
    if not r:
        return None, None, "MISSING"
    v = r.get("x" if kind == "X" else "y")
    v = v if v in (0, 1) else None
    if dom == "2d":
        st = r.get("status") or ""
        strict = v if st in ("VERIFIED", "EMPTY", "CERTIFIED_INFEASIBLE") else None
        return strict, v, st
    res = r.get("resolution", "EVALUATED")
    ok = v if res == "EVALUATED" else None
    return ok, ok, f"{res}:{r.get('status')}"


def labels(dom):
    """(root, json seq) -> {"strict": (x, y), "oper": (x, y), "status": (sx, sy), "src": file}.  Decided conflicts across files abort."""
    lab = {}
    for f in cache_files(dom):
        if not f.exists():
            continue
        for v in jl(f):
            for x in v["results"]:
                k = (v["root"], json.dumps(x["seq"]))
                xs, xo, xst = factor(dom, x["x"], "X")
                ys, yo, yst = factor(dom, x["y"], "Y")
                new = {"strict": (xs, ys), "oper": (xo, yo), "status": (xst, yst), "src": f.parent.parent.name + "/" + f.name}
                old = lab.get(k)
                if old:
                    for kk in ("strict", "oper"):
                        a, b = old[kk], new[kk]
                        if all(t is not None for t in a + b) and a != b:
                            raise SystemExit(f"CONFLICT {k} {old} {new}")
                    if sum(t is not None for t in new["strict"]) <= sum(t is not None for t in old["strict"]):
                        continue
                lab[k] = new
    return lab


def z_of(xy):
    x, y = xy
    if x == 1 and y == 1:
        return 1
    if x == 0 or y == 0:
        return 0
    return None


def outcome(rec_arm, lab, rid, conv):
    """-> SUCCESS / FAIL_X / FAIL_Y / UNKNOWN / UNQUERIED / NOOP / ABSTAIN (conv = 'strict' | 'oper')."""
    d = rec_arm["decision"]
    if d != "REPAIR":
        return d
    L = lab.get((rid, json.dumps(rec_arm["seq"])))
    if L is None:
        return "UNQUERIED"
    x, y = L[conv]
    if y == 0:
        return "FAIL_Y"
    if x == 0:
        return "FAIL_X"
    if x == 1 and y == 1:
        return "SUCCESS"
    return "UNKNOWN"


def manifest(cap=450):
    """Teacher jobs for sealed REPAIR picks lacking an exact-key strict-decided label, tiered and capped (P0_PREREG 5)."""
    seal_ = json.loads((REP / "P3_SEAL.json").read_text())
    out = {"seal_sha256": D.sha(REP / "P3_SEAL.json"), "cap_per_domain": cap, "domains": {}}
    P4.mkdir(parents=True, exist_ok=True)
    for dom in ("2d", "3d"):
        assert D.sha(P3 / f"pred_{dom}.jsonl") == seal_["domains"][dom]["records_sha256"], "predictions changed after seal"
        lab = labels(dom)
        ros = roster(dom)
        need = collections.defaultdict(dict)                     # root -> {seq json: tier}
        cached = collections.Counter()
        for r in jl(P3 / f"pred_{dom}.jsonl"):
            K = ros[r["root_id"]]["K"]
            for arm in ARMS:
                x = r[arm]
                if x["decision"] != "REPAIR":
                    continue
                k = json.dumps(x["seq"])
                L = lab.get((r["root_id"], k))
                if L is not None:
                    cached[(arm, "cached_any")] += 1
                    continue                                       # exact-key label exists (decided or UNKNOWN): reused, never re-queried
                tier = "T2_C0_uncached" if arm == "C0" else ("T1_task_C1C2" if K in ("1", "2", "3") else "T3_safeguard")
                old = need[r["root_id"]].get(k)
                need[r["root_id"]][k] = min(tier, old) if old else tier
        jobs = [(rid, k, t) for rid, v in need.items() for k, t in v.items()]
        order = sorted(jobs, key=lambda j: (TIERS.index(j[2]), D.stratum_hash("CRCVAE_QCAP_V1", j[0]), j[1]))
        # whole roots are kept or dropped together within a tier (all arms of a root)
        keep, n = [], 0
        for t in TIERS:
            for rid in sorted({j[0] for j in order if j[2] == t}, key=lambda x: D.stratum_hash("CRCVAE_QCAP_V1", x)):
                js = [j for j in order if j[0] == rid and j[2] == t]
                if n + len(js) <= cap:
                    keep += js; n += len(js)
        dropped = [j for j in jobs if j not in keep]
        base = V34 / "final"
        idx = {e["root_id"]: e for e in jl(base / "PRIVATE_INDEX.jsonl")}
        byroot = collections.defaultdict(list)
        for rid, k, t in keep:
            byroot[rid].append(k)
        with open(P4 / f"jobs_{dom}.jsonl", "w") as f:
            for rid in sorted(byroot):
                e = idx[rid]
                f.write(json.dumps({"root_id": rid, "dom": dom.upper(), "path": str((base / e["path"]).resolve()), "geom": e.get("geom", "original"),
                                    "seqs": [[[e["ids"][o], c] for o, c in json.loads(k)] for k in sorted(byroot[rid])], "ids": e["ids"]}) + "\n")
        out["domains"][dom] = {"jobs_roots": len(byroot), "queries": len(keep), "by_tier": dict(collections.Counter(t for _, _, t in keep)),
                               "dropped": len(dropped), "dropped_by_tier": dict(collections.Counter(t for _, _, t in dropped)),
                               "cached_picks": {f"{a}|{b}": v for (a, b), v in cached.items()},
                               "jobs_sha256": D.sha(P4 / f"jobs_{dom}.jsonl"), "dropped_list": sorted([list(j) for j in dropped])}
    wj(REP / "P4_QUERY_MANIFEST.json", out)
    print(json.dumps({d: {k: v for k, v in x.items() if k != "dropped_list"} for d, x in out["domains"].items()}))


# ------------------------------------------------------------------------------------------------ P5: per-root outcomes, witnesses, statistics
def legacy_witnesses(dom, rid, ids):
    """Generator legacy-protocol witnesses of a cohort root (labels.B with y = 1) as [[obj index, cell]] keys.  Legacy protocol, NOT the
    finalized X/Y contract: used only as a lower-bound coverage diagnostic."""
    e = roster(dom)[rid]
    rec = json.loads((V34 / "final" / e["path"]).read_text())
    out = set()
    for b in rec.get("labels", {}).get("B", []):
        if b.get("y") == 1 and b.get("sequence"):
            seq = [[ids.index(o), int(c) if not isinstance(c, list) else int(c[0]) * 6 + int(c[1])] for o, c in b["sequence"]]
            if len(seq) <= 3:
                out.add(json.dumps(seq))
    return out


def per_root():
    """-> reports/P5_PER_ROOT.jsonl: per (domain, root, arm) strict / operational outcome, correctness and pool-witness diagnostics."""
    out = []
    for dom in ("2d", "3d"):
        lab = labels(dom)
        ros = roster(dom)
        pub = {r["root_id"]: r for r in jl(P3 / f"public_{dom}.jsonl")}
        fin = collections.defaultdict(set)                          # finalized verified ordered successes (any source, strict)
        for (rid, k), L in lab.items():
            if k != "[]" and L["strict"] == (1, 1):
                fin[rid].add(k)
        for r in jl(P3 / f"pred_{dom}.jsonl"):
            rid, e = r["root_id"], ros[r["root_id"]]
            K = e["K"]
            ids = pub[rid]["inputs"]["ids"]
            gt0 = lab.get((rid, "[]"))
            leg = legacy_witnesses(dom, rid, ids)
            known = leg | fin[rid]
            pool = {json.dumps(s) for s in r["pool"]}
            pool_sets = {json.dumps(sorted(map(tuple, json.loads(s)))) for s in pool}
            c0props = {int(k): set(v) for k, v in r["C0"]["proposals"].items()}
            inC0 = lambda s: all(d in c0props.get(o, set()) for o, d in json.loads(s))  # noqa: E731
            base = {"domain": dom, "root_id": rid, "K": K, "family": e["parent_family_id"], "batch": e["batch"],
                    "y_empty_gt": None if gt0 is None else gt0["strict"][1], "n_movable": r["n_movable"],
                    "known_legacy": len(leg), "known_finalized": len(fin[rid]),
                    "CR_pool_has_known": bool(pool & known), "CR_pool_has_known_set": bool(pool_sets & {json.dumps(sorted(map(tuple, json.loads(s)))) for s in known}),
                    "C0_pool_has_known": any(inC0(s) for s in known), "CR_pool_unique": len(r["pool"]), "C0_n_scored": r["C0"]["n_scored"]}
            for arm in ARMS + ("C1_common_gate", "C3", "C4"):
                if arm not in r:
                    continue
                x = r[arm]
                o_s, o_o = outcome(x, lab, rid, "strict"), outcome(x, lab, rid, "oper")
                L = lab.get((rid, json.dumps(x.get("seq")))) if x["decision"] == "REPAIR" else None
                row = {**base, "arm": arm, "decision": x["decision"], "seq": x.get("seq"), "len": len(x["seq"]) if x["decision"] == "REPAIR" else 0,
                       "strict": o_s, "oper": o_o, "status": None if L is None else L["status"], "label_src": None if L is None else L["src"],
                       "pick_is_known": x["decision"] == "REPAIR" and json.dumps(x["seq"]) in known,
                       "pick_in_C0_pool": x["decision"] == "REPAIR" and inC0(json.dumps(x["seq"])),
                       "score_type": x.get("score_type"), "score": x.get("score")}
                if K in ("1", "2", "3"):
                    row["correct_strict"] = {"SUCCESS": 1, "FAIL_X": 0, "FAIL_Y": 0, "NOOP": 0, "ABSTAIN": 0}.get(o_s)      # None = UNKNOWN / UNQUERIED
                    row["correct_oper"] = {"SUCCESS": 1, "FAIL_X": 0, "FAIL_Y": 0, "NOOP": 0, "ABSTAIN": 0}.get(o_o)
                elif K == "0":
                    row["correct_strict"] = row["correct_oper"] = (1 if x["decision"] == "NOOP" else 0) if base["y_empty_gt"] == 1 else None
                else:
                    row["correct_strict"] = row["correct_oper"] = 1 if x["decision"] == "ABSTAIN" else 0
                out.append(row)
    with open(REP / "P5_PER_ROOT.jsonl", "w") as f:
        for x in out:
            f.write(json.dumps(x) + "\n")
    print(len(out))
    return out


def boot_pair(rows_a, rows_b, key, n=4000, seed=0, fill=None):
    """Paired family-cluster bootstrap stratified by K of mean(a) - mean(b) over roots.  rows: {root: (K, family, value or None)}.
    fill None -> complete case (both decided); fill = (va, vb) -> UNKNOWN replaced by va in a and vb in b; 'strictzero' -> None counts 0."""
    roots = sorted(set(rows_a) & set(rows_b))
    d = {}
    for rt in roots:
        Ka, fa, va = rows_a[rt]
        vb = rows_b[rt][2]
        if fill == "strictzero":
            va, vb = va or 0, vb or 0
        elif fill is not None:
            va = fill[0] if va is None else va
            vb = fill[1] if vb is None else vb
        if va is None or vb is None:
            continue
        d[rt] = (Ka, fa, va - vb)
    if not d:
        return None
    strata = collections.defaultdict(lambda: collections.defaultdict(list))
    for rt, (K, fam, v) in d.items():
        strata[K][fam].append(v)
    cl = {K: list(f.values()) for K, f in strata.items()}
    pt = float(np.mean([v for _, _, v in d.values()]))
    g = np.random.default_rng(seed)
    bs = []
    for _ in range(n):
        tot, cnt = 0.0, 0
        for K, cs in cl.items():
            for i in g.integers(0, len(cs), len(cs)):
                tot += sum(cs[i]); cnt += len(cs[i])
        bs.append(tot / cnt)
    bs = np.array(bs)
    p = float(min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean())))
    vals = [v for _, _, v in d.values()]
    return {"n": len(d), "delta_pp": round(100 * pt, 2), "ci95_pp": [round(100 * float(np.percentile(bs, 2.5)), 2), round(100 * float(np.percentile(bs, 97.5)), 2)],
            "p_boot": p, "wins": sum(v > 0 for v in vals), "losses": sum(v < 0 for v in vals), "families": sum(len(c) for c in cl.values())}


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def stats():
    R = jl(REP / "P5_PER_ROOT.jsonl")
    res = {"domains": {}, "primary": []}
    for dom in ("2d", "3d"):
        Dm = {"arms": {}, "contrasts": {}}
        for arm in sorted({x["arm"] for x in R if x["domain"] == dom}):
            X = [x for x in R if x["domain"] == dom and x["arm"] == arm]
            A = {}
            for grp, Ks in (("K1-3", ("1", "2", "3")), ("K1", ("1",)), ("K2", ("2",)), ("K3", ("3",)), ("K0", ("0",)), ("NONE", ("NONE",))):
                Y = [x for x in X if x["K"] in Ks]
                if not Y:
                    continue
                c = collections.Counter(x["strict"] for x in Y)
                co = collections.Counter(x["oper"] for x in Y)
                N = len(Y)
                a = {"N": N, "strict": dict(c), "oper": dict(co)}
                if grp.startswith("K") and grp != "K0":
                    ver, unk = c["SUCCESS"], c["UNKNOWN"] + c["UNQUERIED"]
                    dec = N - unk
                    a.update({"all_root_strict_pct": round(100 * ver / N, 2), "bounds_pct": [round(100 * ver / N, 2), round(100 * (ver + unk) / N, 2)],
                              "decided_only_pct": round(100 * ver / dec, 2) if dec else None, "unknown_pct": round(100 * unk / N, 2),
                              "oper_pct": round(100 * co["SUCCESS"] / N, 2), "mean_len_repairs": round(float(np.mean([x["len"] for x in Y if x["len"]] or [0])), 3)})
                elif grp == "K0":
                    ev = [x for x in Y if x["correct_strict"] is not None]
                    a.update({"noop_correct_pct": round(100 * np.mean([x["correct_strict"] for x in ev]), 2) if ev else None, "evaluable": len(ev),
                              "repairs": sum(x["decision"] == "REPAIR" for x in Y), "repair_success": c["SUCCESS"]})
                else:
                    a.update({"abstain_correct_pct": round(100 * np.mean([x["correct_strict"] for x in Y]), 2), "repairs": sum(x["decision"] == "REPAIR" for x in Y),
                              "repair_verified_success": c["SUCCESS"]})
                A[grp] = a
            Dm["arms"][arm] = A
        def vals(arm, conv):
            return {x["root_id"]: (x["K"], x["family"], x[f"correct_{conv}"]) for x in R if x["domain"] == dom and x["arm"] == arm and x["K"] in ("1", "2", "3")}
        for a, b in (("C2", "C1"), ("C0", "C2"), ("C0", "C1"), ("C1_common_gate", "C1"), ("C2", "C1_common_gate"), ("C3", "C2"), ("C0", "C4"), ("C0", "C3"), ("C4", "C2")):
            if not any(x["arm"] == a for x in R if x["domain"] == dom) or not any(x["arm"] == b for x in R if x["domain"] == dom):
                continue
            va, vb = vals(a, "strict"), vals(b, "strict")
            Dm["contrasts"][f"{a}-{b}"] = {"all_root_strict": boot_pair(va, vb, "strict", fill="strictzero"),
                                           "complete_case": boot_pair(va, vb, "strict"),
                                           "bound_best_for_a": boot_pair(va, vb, "strict", fill=(1, 0)), "bound_worst_for_a": boot_pair(va, vb, "strict", fill=(0, 1)),
                                           "operational": boot_pair(vals(a, "oper"), vals(b, "oper"), "oper", fill="strictzero")}
            for K in ("1", "2", "3"):
                Dm["contrasts"][f"{a}-{b}"][f"K{K}_all_root_strict"] = boot_pair({k: v for k, v in va.items() if v[0] == K}, {k: v for k, v in vb.items() if v[0] == K}, "s", fill="strictzero")
        res["domains"][dom] = Dm
        for c in ("C2-C1", "C0-C2"):
            res["primary"].append({"domain": dom, "contrast": c, **Dm["contrasts"][c]["all_root_strict"]})
    adj = holm([x["p_boot"] for x in res["primary"]])
    for x, a in zip(res["primary"], adj):
        dom = x["domain"]
        unk = [res["domains"][dom]["arms"][arm]["K1-3"]["unknown_pct"] for arm in x["contrast"].split("-")]
        x["p_holm"] = round(a, 4)
        x["max_unknown_pct"] = max(unk)
        x["verdict"] = ("INCONCLUSIVE (UNKNOWN > 20 %)" if max(unk) > 20 else
                        "ESTABLISHED: first arm better" if a < 0.05 and x["ci95_pp"][0] > 0 else
                        "ESTABLISHED: second arm better" if a < 0.05 and x["ci95_pp"][1] < 0 else "NO ESTABLISHED DIFFERENCE")
    wj(REP / "P5_STATS.json", res)
    print(json.dumps(res["primary"], indent=1))
    return res



def freeze(main=256, L=64, caps=(0.05, 0.25, 1.0)):
    """P2_FREEZE.json: deployment checkpoints (seed 0), inference settings, rule, arms, roster hashes, code commit.  Written before cohort access."""
    import subprocess, torch
    fr = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=D.HERE, capture_output=True, text=True).stdout.strip(),
          "checkpoints": {}, "seed_checkpoints": {}, "inference": {"budgets": [64, 256, 1024], "main_budget": main, "L": L, "pool_seed": 0,
          "pool_rng": "torch.Generator(device).manual_seed(sha256('CRPOOL|root|0')[:15])", "lik_rng": "sha256('CRLIK|root|0')",
          "device": torch.cuda.get_device_name(0), "c3_cap_raw": 4096, "c4": "sha256('CRC4|root|seq') within k, round-robin k=1,2,3",
          "wall_caps_s": list(caps), "decision_head_ties": ["NOOP", "ABSTAIN", "REPAIR"]},
          "rule": json.loads((D.BUNDLE / "MANIFEST.json").read_text())["config"]["rule"], "bundle_manifest_sha256": D.sha(D.BUNDLE / "MANIFEST.json"),
          "remedy": "NOT TRIGGERED (see P2_TRAIN.json)", "arms_primary": list(ARMS), "arms_secondary": ["C1_common_gate", "C3", "C4", "C1_first_draw"],
          "roster": {d: D.sha(D.PRIV / f"cohort_{d}.jsonl") for d in ("2d", "3d")}, "prereg_sha256": D.sha(REP / "P0_PREREG.md")}
    for dom in ("2d", "3d"):
        for s in (0, 1, 2):
            ck = D.RUNS / "models" / dom / f"cr_s{s}" / "model.pt"
            c = json.loads((ck.parent / "curve.json").read_text())
            (fr["checkpoints"] if s == 0 else fr["seed_checkpoints"])[dom if s == 0 else f"{dom}_s{s}"] = {"path": str(ck), "sha256": D.sha(ck), "best_step": c["best_step"]}
    wj(REP / "P2_FREEZE.json", fr)
    print(json.dumps(fr["checkpoints"]))



CAP_H = {"2d": 8.0, "3d": 16.0}


def cpu_used(dom):
    """Teacher CPU seconds recorded by the workers (process_time per job) in this study's cache, and query count."""
    f = P4 / "cache" / f"verify_{dom}.jsonl"
    rows = jl(f) if f.exists() else []
    return sum(r.get("cpu_s", 0) for r in rows), sum(len(r["results"]) for r in rows), rows


def teach(dom, workers=16, cpu0=8, batch_q=120, first=None, headroom_s=None, tag=""):
    """Dispatch the sealed manifest's jobs to the UNCHANGED teachers (benchmark.teach, V3.4 laptop envs) in batches; before each batch, stop if
    recorded CPU + the batch's projected CPU + headroom would exceed the authorized cap.  first = profile only the first N jobs."""
    import os, subprocess, time
    L = D.H / "abf_v3_laptop"
    jobs = jl(P4 / f"jobs{tag}_{dom}.jsonl")
    man = json.loads((REP / ("P4_QUERY_MANIFEST.json" if not tag else "P4_QUERY_MANIFEST_SECONDARY.json")).read_text())
    assert D.sha(P4 / f"jobs{tag}_{dom}.jsonl") == man["domains"][dom]["jobs_sha256"], "jobs file changed after manifest"
    (P4 / "cache").mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "ABF_ROOT": str(L / "root"), "V3OUT": str(P4 / "teach_out"), "FIN3D_CODE": str(L / "gen/final3d_v4/code"),
           "FIN3D_SRC": str(L / "gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass"), "FIN3D_STORE": str(P4 / "store3d"),
           "MUJOCO_GL": "disable", "OMP_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": ""}
    log = open(P4 / f"teach_{dom}.log", "a")
    have = {(r["root"], json.dumps(x["seq"])) for r in cpu_used(dom)[2] for x in r["results"]}
    todo = [j for j in jobs if any((j["root_id"], json.dumps([[j["ids"].index(o), c] for o, c in s_])) not in have for s_ in j["seqs"])][: first or None]
    head = headroom_s if headroom_s is not None else workers * (900 if dom == "2d" else 300)
    i = 0
    while i < len(todo):
        batch, n = [], 0
        while i < len(todo) and n + len(todo[i]["seqs"]) <= batch_q:
            batch.append(todo[i]); n += len(todo[i]["seqs"]); i += 1
        if not batch:
            batch, i = [todo[i]], i + 1
        used, nq, rows = cpu_used(dom)
        per_q = used / nq if nq else (26.6 if dom == "2d" else 35.2)
        proj = used + per_q * sum(len(j["seqs"]) for j in batch) + head
        if proj > CAP_H[dom] * 3600:
            log.write(f"{time.strftime('%FT%TZ', time.gmtime())} STOP_CAP used={used:.0f}s projected={proj:.0f}s\n"); log.flush()
            break
        bf = P4 / f"batch{tag}_{dom}.jsonl"
        with open(bf, "w") as f:
            for j in batch:
                f.write(json.dumps(j) + "\n")
        t0 = time.time()
        log.write(f"{time.strftime('%FT%TZ', time.gmtime())} BATCH roots={len(batch)} queries={sum(len(j['seqs']) for j in batch)} used_cpu_s={used:.0f}\n"); log.flush()
        subprocess.run(["nice", "-n", "10", str(L / f"env{dom}" / "bin" / "python"), "benchmark.py", "teach", dom, str(bf), str(P4 / "cache"), str(workers), str(cpu0)],
                       cwd=D.ABF, env=env, stdout=log, stderr=log, check=True)
        log.write(f"{time.strftime('%FT%TZ', time.gmtime())} BATCH_DONE wall={time.time() - t0:.0f}s\n"); log.flush()
    used, nq, rows = cpu_used(dom)
    print(json.dumps({"dom": dom, "cpu_h": round(used / 3600, 3), "queries_done": nq, "roots_done": len(rows), "jobs_roots": len(jobs)}))



def manifest_secondary(cap=450):
    """Secondary physical tier (after primary coverage is complete): K1-K3 REPAIR picks of C1_common_gate, then C4, then C3, lacking an exact-key
    label, whole roots by sha256('CRCVAE_QSEC_V1|root') within tier, capped at (cap - primary queries)."""
    prim = json.loads((REP / "P4_QUERY_MANIFEST.json").read_text())
    out = {"primary_manifest_sha256": D.sha(REP / "P4_QUERY_MANIFEST.json"), "domains": {}}
    for dom in ("2d", "3d"):
        assert D.sha(P3 / f"pred_{dom}.jsonl") == json.loads((REP / "P3_SEAL.json").read_text())["domains"][dom]["records_sha256"]
        used, nq, _ = cpu_used(dom)
        assert nq == prim["domains"][dom]["queries"], (dom, "primary teacher coverage incomplete", nq)
        left = cap - nq
        lab, ros = labels(dom), roster(dom)
        need = collections.defaultdict(dict)
        tiers = ("S1_C1_common_gate", "S2_C4", "S3_C3")
        for r in jl(P3 / f"pred_{dom}.jsonl"):
            if ros[r["root_id"]]["K"] not in ("1", "2", "3"):
                continue
            for arm, t in zip(("C1_common_gate", "C4", "C3"), tiers):
                x = r[arm]
                if x["decision"] == "REPAIR" and (r["root_id"], json.dumps(x["seq"])) not in lab:
                    k = json.dumps(x["seq"])
                    need[r["root_id"]][k] = min(t, need[r["root_id"]].get(k, t))
        keep, n = [], 0
        for t in tiers:
            for rid in sorted({rid for rid, v in need.items() if t in v.values()}, key=lambda x: D.stratum_hash("CRCVAE_QSEC_V1", x)):
                js = [(rid, k, t) for k, tt in need[rid].items() if tt == t]
                if n + len(js) <= left:
                    keep += js; n += len(js)
        allj = [(rid, k, t) for rid, v in need.items() for k, t in v.items()]
        idx = {e["root_id"]: e for e in jl(V34 / "final" / "PRIVATE_INDEX.jsonl")}
        byroot = collections.defaultdict(list)
        for rid, k, t in keep:
            byroot[rid].append(k)
        with open(P4 / f"jobs2_{dom}.jsonl", "w") as f:
            for rid in sorted(byroot):
                e = idx[rid]
                f.write(json.dumps({"root_id": rid, "dom": dom.upper(), "path": str((V34 / "final" / e["path"]).resolve()), "geom": e.get("geom", "original"),
                                    "seqs": [[[e["ids"][o], c] for o, c in json.loads(k)] for k in sorted(byroot[rid])], "ids": e["ids"]}) + "\n")
        out["domains"][dom] = {"remaining_cap": left, "queries": len(keep), "by_tier": dict(collections.Counter(t for _, _, t in keep)),
                               "needed_by_tier": dict(collections.Counter(t for _, _, t in allj)), "dropped": len(allj) - len(keep),
                               "jobs_sha256": D.sha(P4 / f"jobs2_{dom}.jsonl"), "primary_cpu_h": round(used / 3600, 3)}
    wj(REP / "P4_QUERY_MANIFEST_SECONDARY.json", out)
    print(json.dumps(out["domains"]))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "devids":
        devids()
    elif cmd == "dev":
        dev(*sys.argv[2:])
    elif cmd == "public":
        cohort_public()
    elif cmd == "seal":
        seal(sys.argv[2])
    elif cmd == "manifest":
        manifest()
    elif cmd == "freeze":
        freeze()
    elif cmd == "teach":
        teach(sys.argv[2], first=int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != "0" else None, tag=sys.argv[4] if len(sys.argv) > 4 else "")
    elif cmd == "manifest2":
        manifest_secondary()
    elif cmd == "per_root":
        per_root()
    elif cmd == "stats":
        stats()
