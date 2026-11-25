#!/usr/bin/env python3
"""P0 audit: provenance hashes, frozen parity on 40 deterministic roots, TRAIN label coverage by frozen cVAE rank, xy.fit normalization,
family partition / leakage, reconciliation of the completed study's aggregates, and the CONFIRM candidate pool (private).
    python audit.py all"""
from __future__ import annotations

import collections, glob, hashlib, json, os, subprocess, sys
from pathlib import Path

import numpy as np

import rr

PROTECTED = ["xy.py", "search.py", "contracts.py", "placement.py", "exhaustive.py", "construct.py", "benchmark.py", "evaluate.py",
             "scripts/v32b_phys.py", "full_domain_sets/domain.py", "full_domain_sets/fsearch.py", "full_domain_sets/run.py",
             "full_domain_sets/analyze.py", "mcts_sets/search_sets.py"]


def git(*a):
    return subprocess.run(["git", *a], cwd=rr.ABF, capture_output=True, text=True).stdout.strip()


def provenance():
    man = json.loads((rr.BUNDLE / "MANIFEST.json").read_text())
    return {"parent_commit": "7db1132d983a36b4505da02f23888237905cd17b", "head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "plan_sha256": rr.sha(rr.HERE / "plan.md"), "bundle_manifest_sha256": rr.sha(rr.BUNDLE / "MANIFEST.json"),
            "bundle_2d": {k: v for k, v in man["files"].items() if k.startswith("2d/")},
            "scorer_provenance": {k: v for k, v in man["provenance"].items() if k.startswith("2d/")}, "frozen_config": man["config"],
            "snapshot": {"path": str(rr.SNAP), "data2d_sha256": rr.sha(rr.SNAP / "data2d.jsonl"),
                         "lock": json.loads((rr.SNAP / "data_snapshot.lock.json").read_text())},
            "public_val_sha256": rr.sha(rr.PUB_VAL), "caches_sha256": {str(c).replace(str(rr.H), "~"): rr.sha(c) for c in rr.CACHES},
            "protected_source_sha256": {p: rr.sha(rr.ABF / p) for p in PROTECTED},
            "protected_reports_unchanged": git("diff", "--stat", "7db1132d98", "--", "full_domain_sets", "mcts_sets") == ""}


def parity(n=40):
    """D4/D6, EXACT4 decision vs the sealed full-domain EVAL predictions, readout identities, batch / shuffle invariance."""
    import torch
    import exhaustive as EX
    import search as S
    sys.path.insert(0, str(rr.ABF / "full_domain_sets"))
    import fsearch as FS
    import domain as DM
    samp, scor, man = rr.bundle()
    sealed = {r["root_id"]: next(x for x in r["results"] if x["arm"] == "EXACT4") for r in rr.jl(rr.FDS_REP / "P3_EVAL_PREDICTIONS.jsonl.gz")}
    pub = {r["root_id"]: r for r in rr.public_val()}
    roots = sorted(sealed, key=lambda r: rr.hx("XYRR_P0|", r))[:n]
    cv = rr.cvae_table(list(pub.values()), samp, "val")
    out = collections.Counter(); worst = collections.defaultdict(float)
    for rid in roots:
        row = pub[rid]; R = S.Root(row, "2d")
        out["D6_equal"] += EX.proposals(R, samp, 0) == {int(k): v for k, v in cv[rid]["D6"].items()}
        dom = DM.Domain(cv[rid]["raw"], cv[rid]["D6"], 0.25)
        x = FS.run_arm("EXACT4", dom, lambda s: scor.score(R, s), None, rr.RULE, rid, disp=R.displacement)
        out["EXACT4_decision_equal"] += (x["decision"], x["seq"]) == (sealed[rid]["decision"], sealed[rid]["seq"])
        seqs = [[]]
        pool = dom.D(4)
        for o, ds in pool.items():
            for d in ds:
                seqs.append([[o, d]])
        mv = sorted(pool)
        if len(mv) > 1:
            seqs += [[[mv[0], pool[mv[0]][0]], [mv[1], pool[mv[1]][1 if pool[mv[1]][0] == pool[mv[0]][0] else 0]]]]
            seqs += [seqs[-1][::-1]]
        ref = scor.score(R, seqs)
        a = rr.readout(scor.net, [(row, seqs)])[0]["rows"]
        g = np.random.default_rng(rr.hx("SHUF", rid) % 2 ** 32); perm = g.permutation(len(seqs))
        b = rr.readout(scor.net, [(row, [seqs[i] for i in perm])])[0]["rows"]
        for i, (r0, r1) in enumerate(zip(ref, a)):
            worst["p11_vs_Scorer.score"] = max(worst["p11_vs_Scorer.score"], abs(r0["p11"] - r1["p11"]))
            if seqs[i]:
                worst["px_vs_Scorer.score"] = max(worst["px_vs_Scorer.score"], abs(r0["px"] - r1["px"]))
                worst["py_vs_Scorer.score"] = max(worst["py_vs_Scorer.score"], abs(r0["py"] - r1["py"]))
                worst["p11=py*px1"] = max(worst["p11=py*px1"], abs(r1["p11"] - r1["py"] * r1["px1"]))
                worst["px=py*px1+(1-py)*px0"] = max(worst["px=py*px1+(1-py)*px0"], abs(r1["px"] - (r1["py"] * r1["px1"] + (1 - r1["py"]) * r1["px0"])))
        for j, i in enumerate(perm):
            worst["shuffle_invariance_p11"] = max(worst["shuffle_invariance_p11"], abs(b[j]["p11"] - a[i]["p11"]))
        if len(seqs) >= 3 and len(seqs[-1]) == 2:
            worst["same_endpoint_py_across_orders"] = max(worst["same_endpoint_py_across_orders"], abs(a[-1]["py"] - a[-2]["py"]))
        out["roots"] += 1
    multi = rr.readout(scor.net, [(pub[r], [[]]) for r in roots])
    single = [rr.readout(scor.net, [(pub[r], [[]])])[0] for r in roots]
    worst["cross_root_batch_invariance_p_noop"] = max(abs(m["p_noop"] - s["p_noop"]) for m, s in zip(multi, single))
    res = {"roots": roots, **dict(out), "max_abs_err": dict(worst)}
    res["pass"] = out["D6_equal"] == n and out["EXACT4_decision_equal"] == n and max(worst.values()) < 1e-5
    return res


def train_coverage():
    """TRAIN X/Y labels by kind, K, length, joint class and the frozen cVAE rank of each relocation (TRAIN S0 marginal)."""
    samp, _, _ = rr.bundle()
    rows = rr.snapshot_rows("train")
    cv = rr.cvae_table(rows, samp, "train")
    import search as S
    T = collections.Counter(); K = collections.Counter(); J = collections.Counter(); kindtier = collections.Counter(); per_root = []
    pairs_roots = collections.Counter(); grammar = collections.Counter(); legal_support = collections.Counter(); src = collections.Counter()
    for r in rows:
        R = S.Root(r, "2d"); rk = rr.Ranks(cv[r["root_id"]]); Lset = set(R.legal_dests(R.cells0)); mv = set(R.movable)
        nobj = len(rk.rank and {o for o, _ in rk.rank})
        for t, n in (("T4", 4), ("T56", 2), ("R7_12", 6)):
            legal_support[t] += n * nobj
        legal_support["TAIL"] += max(0, len(Lset) - 12) * nobj
        Y = {json.dumps(sorted([int(i), int(c)] for i, c in y["edit"])): y["y"] for y in r["labels"]["Y"]}
        zs, nx = [], 0
        for q in r["labels"]["X"]:
            seq = [[int(i), int(c)] for i, c in q["seq"]]
            y = Y.get(json.dumps(sorted(seq)))
            z = rr.z_logic(q["x"], y)
            info = rk.seq_info(seq)
            leg = (len({i for i, _ in seq}) == len(seq) and len({c for _, c in seq}) == len(seq) and all(i in mv for i, _ in seq) and all(c in Lset for _, c in seq))
            grammar["legal_original_grammar" if leg else "outside_original_grammar"] += 1
            T[(info["max_tier"], len(seq))] += 1; kindtier[(q["kind"], info["max_tier"])] += 1
            J[f"x{q['x']}_y{'?' if y is None else y}"] += 1; K[(r["K_legacy"], info["max_tier"])] += 1
            zs.append(z); nx += 1
        ny = len(r["labels"]["Y"])
        src[r["source"]] += 1
        has_p, has_n = 1 in zs, 0 in zs
        pairs_roots["roots_with_Z+_and_Z-" if has_p and has_n else "Z+_only" if has_p else "Z-_only" if has_n else "no_decided_Z"] += 1
        per_root.append({"K": r["K_legacy"], "nx": nx, "ny": ny, "nodes": nx + ny})
    nodes = np.array([p["nodes"] for p in per_root])
    rank_counts = collections.Counter()
    for (t, L), n in T.items():
        rank_counts[t] += n
    return {"n_train_roots": len(rows), "train_sources": dict(src), "X_labels_by_max_tier_and_len": {f"{t}|len{L}": n for (t, L), n in sorted(T.items())},
            "X_labels_by_kind_and_max_tier": {f"{k}|{t}": n for (k, t), n in sorted(kindtier.items())},
            "X_labels_by_K_and_max_tier": {f"K{k}|{t}": n for (k, t), n in sorted(K.items())},
            "joint_class_counts (x, y of endpoint; ? = endpoint Y not labelled)": dict(J), "grammar": dict(grammar),
            "per_root_label_nodes": {"median": float(np.median(nodes)), "mean": float(nodes.mean()), "p90": float(np.percentile(nodes, 90)), "max": int(nodes.max()),
                                     "C_median_nodes_per_root (rank-loss scale, fixed before training)": max(1, int(np.median(nodes)))},
            "decided_Z_root_classes": dict(pairs_roots),
            "legal_action_support_by_tier (objects x cells, TRAIN S0)": dict(legal_support),
            "label_share_vs_support_by_max_tier": {t: {"labels": rank_counts.get(t, 0), "share_labels": rank_counts.get(t, 0) / max(1, sum(rank_counts.values())),
                                                      "share_legal_actions": legal_support.get(t, 0) / max(1, sum(legal_support.values()))} for t in ("T4", "T56", "R7_12", "TAIL", "OUTSIDE")},
            "note": "x / y are finalized snapshot labels (UNKNOWN absent = missing); rank = frozen S1 marginal on the TRAIN root S0; OUTSIDE = destination not in the original-grammar legal set (e.g. vacated or occupied cell) or object not movable"}


def fit_audit():
    import inspect
    import xy as XY
    src = inspect.getsource(XY.XYNet.loss) + inspect.getsource(XY.batched_log_evidence)
    return {"objective": "nll_r = -batched_log_evidence(...) per root (SUM over the root's observed Y / X nodes, missing marginalized); nll = nll_r.mean() over roots",
            "per_label_normalization": "none (root-summed evidence; roots with more labels weigh more)", "travel_lam": XY.ARMS["D"]["lam"], "sym_aux": XY.ARMS["D"]["loss"],
            "arm_D_cfg": XY.ARMS["D"], "optimizer": "AdamW lr 1e-3 wd 1e-4, clip 10, batch 64 roots (fixed seeded partition, reshuffled order), 60 epochs, early stop on snapshot 'val' NLL",
            "early_stopping_split": "snapshot 'val' = the 751 old VAL roots (so VAL is NOT independent of the scorer's checkpoint selection)",
            "source_contains_index_add_root_sum": "index_add(0, root_of_scene, per_scene)" in src}


def layout_fp(inp):
    return hashlib.sha256(json.dumps([sorted(map(int, inp["cells0"])), int(inp["cells0"][inp["tid"]]), int(inp["goal_cell"])]).encode()).hexdigest()


def partition():
    vm = rr.val_meta()
    tr = rr.snapshot_rows("train"); va = rr.snapshot_rows("val"); te = rr.snapshot_rows("test")
    ftr, fva = {r["parent_family_id"] for r in tr}, {r["parent_family_id"] for r in va}
    lt, lv = collections.Counter(layout_fp(r["inputs"]) for r in tr), {layout_fp(r["inputs"]): r["root_id"] for r in va}
    man = {rid: m["part"] for rid, m in sorted(vm.items())}
    rr.wjson(rr.REP / "P0_SPLIT_MANIFEST.json", {"rule": "DEV_CAL iff sha256('XYRR_DEV|'+parent_family_id) even", "parts": man,
                                                 "sha256": hashlib.sha256(json.dumps(man, sort_keys=True).encode()).hexdigest()})
    c = collections.Counter((m["part"], m["K"]) for m in vm.values())
    return {"DEV_CAL_roots": sum(m["part"] == "DEV_CAL" for m in vm.values()), "DEV_AUDIT_roots": sum(m["part"] == "DEV_AUDIT" for m in vm.values()),
            "by_part_K": {f"{p}|K{k}": n for (p, k), n in sorted(c.items())},
            "families": {"VAL": len(fva), "DEV_CAL": len({m["family"] for m in vm.values() if m["part"] == "DEV_CAL"}),
                         "DEV_AUDIT": len({m["family"] for m in vm.values() if m["part"] == "DEV_AUDIT"}), "TRAIN": len(ftr)},
            "family_overlap_TRAIN_VAL": len(ftr & fva), "family_overlap_DEVCAL_DEVAUDIT": 0,
            "layout_fp_overlap_TRAIN_VAL_roots": sum(1 for f in lv if f in lt), "root_id_overlap_TRAIN_VAL": len({r["root_id"] for r in tr} & set(vm)),
            "test_roots_opened": 0, "split_manifest": "reports/P0_SPLIT_MANIFEST.json"}


def reconcile():
    """Recompute the completed study's strict / operational EXACT4 and seeded-MCTS counts from committed per-root records."""
    per = rr.jl(rr.FDS_REP / "P3_PHYSICAL_PER_ROOT.jsonl")
    out = {}
    for arm in ("EXACT4@None", "PW_MCTS_SEEDED4@1024", "EXACT_FULL@None"):
        c = collections.Counter(r[arm]["strict"] for r in per if r["K"] in ("1", "2"))
        dec = c["SUCCESS"] + sum(v for k, v in c.items() if k not in ("SUCCESS", "UNKNOWN"))
        out[arm] = {"K1K2_roots": sum(c.values()), "strict_counts": dict(c), "strict_decided": dec, "strict_success": c["SUCCESS"]}
    out["published"] = {"EXACT4": "120/148 strict, 43 UNKNOWN; 120/191 operational", "PW_MCTS_SEEDED4@1024": "123/153 strict", "EXACT_FULL": "109/149 strict"}
    out["match"] = (out["EXACT4@None"]["strict_success"], out["EXACT4@None"]["strict_decided"]) == (120, 148) and \
                   (out["PW_MCTS_SEEDED4@1024"]["strict_success"], out["PW_MCTS_SEEDED4@1024"]["strict_decided"]) == (123, 153)
    return out


def cache_audit():
    lab = rr.strict_labels()
    pub = {r["root_id"]: r for r in rr.public_val()}
    vm = rr.val_meta()
    c = collections.Counter()
    for (rid, sq), e in lab.items():
        if rid not in pub:
            c["not_val_root"] += 1; continue
        seq = json.loads(sq)
        c["keys"] += 1; c["quarantined_conflict"] += e["conflict"]
        c[f"len{len(seq)}"] += 1
        z = rr.z_logic(e["x"], e["y"])
        c[f"z_logic_{z}"] += 1
        c[f"hist_{rr.z_hist(e['x'], e['y'])}"] += 1
    roots = collections.defaultdict(set)
    for (rid, sq), e in lab.items():
        if rid in vm and vm[rid]["K"] in ("1", "2") and len(json.loads(sq)) <= 2:
            z = rr.z_logic(e["x"], e["y"])
            if z is not None:
                roots[rid].add(z)
    both = [r for r, s in roots.items() if s == {0, 1}]
    return {"val_cache_keys": dict(c), "K1K2_roots_with_decided_Z+_and_Z-_(len<=2)": len(both),
            "by_part": dict(collections.Counter(vm[r]["part"] for r in both)), "generator_labels": "secondary, descriptive only (genlab_val_2d)"}


# ------------------------------------------------------------------------------------------------------------- CONFIRM candidate pool
def confirm_pool():
    """Accepted-but-never-admitted fresh 2D roots of the V3.4 generation runs (new seeds / ids; never inferred, never teacher-evaluated by a
    method).  Disjointness: root id / construction seed / sha256 / GEOM_V1 layout fp vs historical EXCL lists, the V3.4 cohort, enrichment
    parents (shared lineage with cohort children) and within-pool.  Private index written to ~/xyrr_private/confirm/; public rows via
    benchmark.public.  Template families may recur (as in the V3.4 Option B definition)."""
    import shutil
    A = rr.H / "abf_v34"
    sys.path.insert(0, str(rr.H / "Desktop/boltzmann_lfd/.claude/worktrees/approach-b-v3-4-final-benchmark/approach_b_final/scripts"))
    import v34_geomfp as GF
    import contracts as CT
    coh = rr.jl(A / "final/PRIVATE_INDEX.jsonl")
    X = json.loads((A / "excl/EXCL2D.json").read_text()); XG = set(json.loads((A / "excl/EXCL2D_GEOM.json").read_text())["geom_fp"])
    hist = {"root_id": set(map(str, X["root_ids"])), "seed": set(map(str, X["seeds"])), "sha": set(map(str, X["root_sha256"])), "fp": XG}
    cohort = {"root_id": {r["root_id"] for r in coh}, "seed": {str(r["construction_seed"]) for r in coh}, "sha": {r["root_sha256"] for r in coh},
              "fp": {r["layout_fp"] for r in coh}}
    enrich_parents = set()
    for f in glob.glob(str(A / "enrich/**/*.jsonl"), recursive=True) + glob.glob(str(A / "enrich_dev/**/*.jsonl"), recursive=True):
        for l in open(f):
            try:
                e = json.loads(l)
            except Exception:
                continue
            for k in ("parent", "parent_root_id", "root_id"):
                if isinstance(e.get(k), str):
                    enrich_parents.add(e[k])
    cand = {}
    for f in sorted(glob.glob(str(A / "gen/*/ledger.jsonl"))) + sorted(glob.glob(str(A / "collect/*/ledger.jsonl"))):
        for l in open(f):
            try:
                e = json.loads(l)
            except Exception:
                continue
            if e.get("accepted") and e["root_id"].startswith("2d") and str(e.get("verified_K")) in ("0", "1", "2", "None"):
                p = Path(f).parent / "roots" / f"{e['root_id']}.json"
                if p.exists():
                    cand.setdefault(e["root_id"], (e, p))
    out = rr.PRIV / "confirm"; (out / "roots").mkdir(parents=True, exist_ok=True)
    rows, seen, skip = [], {k: set() for k in ("root_id", "seed", "sha", "fp")}, collections.Counter()
    for rid in sorted(cand, key=lambda r: rr.hx("XYRR_CONFIRM|", r)):
        e, p = cand[rid]
        raw = p.read_bytes(); rec = json.loads(raw); h = hashlib.sha256(raw).hexdigest()
        v = CT.view2d(rec); fp, seed = GF.geom_fp(v), str(rec["ids"]["construction_seed"])
        hit = [f"{k}:{w}" for k, val in (("root_id", rid), ("seed", seed), ("sha", h), ("fp", fp))
               for w, S_ in (("historical", hist[k]), ("v34_cohort", cohort[k]), ("within_pool", seen[k])) if val in S_]
        if rid in enrich_parents:
            hit.append("enrichment_parent")
        if str(rec.get("observed")) != str(e.get("verified_K")) and not (e.get("verified_K") is None and str(rec.get("observed")) == "NONE"):
            hit.append("class_mismatch")
        if hit:
            skip.update(hit); continue
        for k, val in (("root_id", rid), ("seed", seed), ("sha", h), ("fp", fp)):
            seen[k].add(val)
        K = "NONE" if e.get("verified_K") is None else str(e["verified_K"])
        shutil.copyfile(p, out / "roots" / f"{rid}.json")
        rows.append({"root_id": rid, "domain": "2d", "K": K, "path": f"roots/{rid}.json", "root_sha256": h, "layout_fp": fp, "construction_seed": int(seed),
                     "template_id": rec["ids"]["parent_family_id"], "parent_family_id": rec["ids"]["parent_family_id"], "instance_lineage_id": rid,
                     "evaluation_group_id": "grp-" + hashlib.sha256(rid.encode()).hexdigest()[:12], "config_hash": rec["ids"]["config_hash"],
                     "teacher_version": rec["ids"].get("teacher_version"), "geom": rec.get("geometry_impl", "original"), "ids": v["ids"],
                     "masks": {"eval_task": K in ("1", "2"), "eval_noop": K == "0", "eval_abstain": K == "NONE"}, "source_ledger": str(p.parent.parent).replace(str(rr.H), "~")})
    with open(out / "PRIVATE_INDEX.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    trf = {r["parent_family_id"] for r in rr.snapshot_rows("train")}
    return {"candidates_accepted_unused": len(cand), "admitted": len(rows), "by_K": dict(collections.Counter(r["K"] for r in rows)),
            "skipped": dict(skip), "template_family_overlap_with_TRAIN": sum(r["parent_family_id"] in trf for r in rows),
            "geoms": dict(collections.Counter(r["geom"] for r in rows)), "private_index_sha256": rr.sha(out / "PRIVATE_INDEX.jsonl"),
            "teacher_queries_spent": 0}


if __name__ == "__main__":
    what = sys.argv[1]
    if what in ("prov", "all"):
        rr.wjson(rr.REP / "P0_PROVENANCE.json", {"provenance": provenance(), "fit": fit_audit(), "partition": partition(), "reconcile": reconcile(), "caches": cache_audit()})
        print("prov done", flush=True)
    if what in ("parity", "all"):
        rr.wjson(rr.REP / "P0_PARITY.json", parity()); print("parity done", flush=True)
    if what in ("train", "all"):
        rr.wjson(rr.REP / "P0_TRAIN_COVERAGE.json", train_coverage()); print("train done", flush=True)
    if what in ("confirm", "all"):
        rr.wjson(rr.REP / "P0_CONFIRM_POOL.json", confirm_pool()); print("confirm done", flush=True)
