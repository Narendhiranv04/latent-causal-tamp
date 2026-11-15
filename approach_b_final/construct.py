#!/usr/bin/env python3
"""V3 direct one-shot candidate construction and single-repair selection (plan V3 sections 2.1, 2.3, 4.1, 4.2).  Shared by 2D and 3D.

    original root -> ONE batched sampler query per eligible movable object on S0 (never on an edited scene) -> distinct legal destination sets
    D_o -> every statically legal ordered sequence of 1..3 distinct objects with pairwise distinct destinations (all permutations kept as separate
    X candidates; complete enumeration if it fits B_score, else the label-blind budgeted constructor below) -> batched X/Y scoring from the
    ORIGINAL root (endpoint Y shared by permutations) -> frozen no-op gate / eta / argmin -log p11 + alpha m + beta D + gamma J_hat -> ONE repair,
    NOOP or ABSTAIN.  No prefix frontier, no re-query on hypothetical scenes, no physical planner (planner_calls = 0 by construction).

Budgeted constructor (label- and model-blind, seeded per root): all K1 actions; the rest of B_score split evenly between K2 and K3 (unused share
rolls over).  A length-k share is filled with whole unordered assignments sampled uniformly (uniform k-combination of objects, uniform destination
per object, rejection of shared destinations / repeats) and ALL k! orders of each sampled assignment, so the scorer, not the constructor, chooses
the order.  Exact valid counts per length are computed by inclusion-exclusion and recorded with what was built and scored.

    python construct.py run DOM SPLIT ARM SEED [M] [B]    -> $V3OUT/v3_1/<dom>/<arm>_M<M>_B<B>_s<seed>_<split>.jsonl (resumable)
    python construct.py verify DOM FILE.jsonl WORKERS CPU0  physical X / Y of the selected repairs (cache reuse: frozen V2 cache read-only)"""
from __future__ import annotations

import collections, hashlib, itertools, json, math, os, random, sys, time
from pathlib import Path

ABF = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
V3OUT = Path(os.environ.get("V3OUT", str(ABF.parent / "runs")))


# --------------------------------------------------------------------------------------------- construction (pure python, torch-free)
def counts(D):
    """D {obj: [dests]} -> exact number of valid ordered sequences of length 1, 2, 3 (distinct objects, pairwise distinct destinations)."""
    S = {o: set(v) for o, v in D.items() if v}
    ob = sorted(S)
    n1 = sum(len(S[o]) for o in ob)
    n2 = sum(len(S[a]) * len(S[b]) - len(S[a] & S[b]) for a, b in itertools.combinations(ob, 2)) * 2
    n3 = 0
    for a, b, c in itertools.combinations(ob, 3):
        A, B, C = S[a], S[b], S[c]
        n3 += len(A) * len(B) * len(C) - len(A & B) * len(C) - len(A & C) * len(B) - len(B & C) * len(A) + 2 * len(A & B & C)
    return [n1, n2, n3 * 6]


def assignments(D, k):
    """All unordered valid k-assignments (sorted tuples of (obj, dest))."""
    ob = sorted(o for o, v in D.items() if v)
    for objs in itertools.combinations(ob, k):
        for ds in itertools.product(*(D[o] for o in objs)):
            if len(set(ds)) == k:
                yield tuple(zip(objs, ds))


def sample_assignments(D, k, n, rng, max_tries=200):
    """n distinct unordered k-assignments: uniform k-combination of objects, uniform destination per object, rejection of invalid / repeats."""
    ob = sorted(o for o, v in D.items() if v)
    got, tries = {}, 0
    while len(got) < n and tries < max_tries * max(n, 1):
        tries += 1
        objs = sorted(rng.sample(ob, k))
        ds = [rng.choice(D[o]) for o in objs]
        if len(set(ds)) == k:
            got.setdefault(tuple(zip(objs, ds)), None)
    return list(got)


def build(D, B, seed_key):
    """-> (ordered sequences [[(obj, dest)]], accounting).  Complete enumeration when the valid total fits B, else the budgeted constructor."""
    n = counts(D)
    acc = {"valid_by_len": n, "B_score": B}
    if sum(n) <= B:
        seqs = [list(p) for k in (1, 2, 3) for a in assignments(D, k) for p in itertools.permutations(a)]
        acc.update(mode="complete", built_by_len=[sum(len(s) == k for s in seqs) for k in (1, 2, 3)])
        return seqs, acc
    rng = random.Random("v3construct|" + seed_key)
    one = [list(a) for a in assignments(D, 1)]
    if len(one) >= B:
        seqs = [one[i] for i in sorted(rng.sample(range(len(one)), B))]
        acc.update(mode="budgeted", built_by_len=[len(seqs), 0, 0])
        return seqs, acc
    seqs, left = list(one), B - len(one)
    share2 = min(n[1], left // 2)
    share2 -= share2 % 2
    share3 = min(n[2], (left - share2) // 6 * 6)
    share2 = min(n[1], (left - share3) // 2 * 2)                       # roll-over of an unused K3 share back to K2
    for k, share in ((2, share2), (3, share3)):
        na = share // math.factorial(k)
        if na == 0:
            continue
        A = list(assignments(D, k)) if na * math.factorial(k) >= n[k - 1] else sample_assignments(D, k, na, rng)
        seqs += [list(p) for a in A for p in itertools.permutations(a)]
    acc.update(mode="budgeted", built_by_len=[sum(len(s) == k for s in seqs) for k in (1, 2, 3)])
    return seqs, acc


# --------------------------------------------------------------------------------------------- one root end-to-end (GPU models)
def run_root(root, sampler, scorer, M, B, rule, seed, store_top=2048, chunk=8192):
    """-> per-root audit record (plan V3 8.2).  The sampler is called exactly once (one batched call over all movable objects on S0)."""
    import torch
    import search as S
    t0 = time.time()
    gen = torch.Generator(device=sampler.dev).manual_seed(int(seed))
    c0 = (sampler.calls, sampler.raw, scorer.evals)
    D = sampler.propose_many(root, root.cells0, list(root.movable), M, gen) if root.movable else {}
    D = {o: [int(d) for d in v] for o, v in D.items()}
    t1 = time.time()
    seqs, acc = build(D, B, f"{root.id}|{seed}|{M}|{B}")
    t2 = time.time()
    sc = scorer.score(root, [[]])
    for i in range(0, len(seqs), chunk):
        sc += scorer.score(root, seqs[i:i + chunk])
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    t3 = time.time()
    cands = [{"seq": [list(a) for a in s], "p11": c["p11"], "J": c["J"], "m": len(s), "D": root.displacement(s) if s else 0.0}
             for s, c in zip([[]] + seqs, sc)]
    pick = S.select(cands, rule)
    sel = None if pick is None else next(c for c in cands if c["seq"] == pick)
    keep = cands
    if len(cands) > store_top:
        top = sorted(cands[1:], key=lambda c: -c["p11"])[:store_top]
        keep = [cands[0]] + top + ([sel] if sel is not None and sel["m"] and all(c is not sel for c in top) else [])
    return {"root_id": root.id, "domain": root.dom, "split": root.row["split"], "K": root.row["K_legacy"],
            "M_by_object": {str(o): len(v) for o, v in D.items()}, "proposal_actions": [[o, d] for o, v in sorted(D.items()) for d in v],
            "candidate_budget": {"raw_draws": sampler.raw - c0[1], "sampler_calls": sampler.calls - c0[0], "sampler_passes": 1 if root.movable else 0,
                                 "unique_actions": sum(len(v) for v in D.values()), "n_scored": scorer.evals - c0[2], **acc},
            "selected_ordered_seq": pick, "p11": None if sel is None else round(sel["p11"], 6), "decision": "ABSTAIN" if pick is None else ("NOOP" if not pick else "REPAIR"),
            "p_noop": round(cands[0]["p11"], 6), "planner_calls": 0,
            "wall_s": {"propose": round(t1 - t0, 4), "construct": round(t2 - t1, 4), "score": round(t3 - t2, 4), "total": round(t3 - t0, 4)},
            "stored": "all" if len(cands) <= store_top else f"noop+top{store_top}_by_p11+selected",
            "cands": [{"seq": c["seq"], "p11": round(c["p11"], 6), "J": round(c["J"], 5), "m": c["m"], "D": round(c["D"], 4)} for c in keep]}


ARMS = {"v2frozen": {"sampler": ("v1", "cvae"), "xy": ("v2", "D")}}           # frozen V2 = V1 Q2 cVAE (unchanged in V2) + V2-retrained coupled D


def run(dom, split, arm, seed, M=4, B=4096):
    import torch
    import evaluate as EV
    import search as S
    EV.SNAP = ABF / "snapshot/abf_9de85710c2a7103f"
    a = ARMS[arm]
    out = V3OUT / "v3_1" / dom.lower() / f"{arm}_M{M}_B{B}_s{seed}_{split}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["root_id"] for l in open(out)} if out.exists() else set()
    samp = S.Sampler(dom.lower(), a["sampler"][1], seed, ABF / "data" / f"q2_{dom.lower()}")
    p2 = ABF / "runs" / ("v2" if a["xy"][0] == "v2" else "") / f"p2_{dom.lower()}" / f"{a['xy'][1]}_s{seed}" / "model.pt"
    scor = S.Scorer(p2, ABF / "runs" / f"p3_{dom.lower()}" / f"cost_s{seed}" / "model.pt")
    rule = json.loads((ABF / "runs/v2" / f"p5_{dom.lower()}" / "rule.json").read_text())
    torch.cuda.reset_peak_memory_stats()
    with open(out, "a") as f:
        for r in EV.rows_of(dom.upper(), split):
            if r["root_id"] in done:
                continue
            rec = run_root(S.Root(r, dom.lower()), samp, scor, M, B, rule, seed)
            rec.update(arm=arm, seed=seed, sampler_version=f"{a['sampler'][0]}:{a['sampler'][1]}_s{seed}", scorer_version=f"{a['xy'][0]}:{a['xy'][1]}_s{seed}",
                       sampling_rule="S0_repeat_dedup_raw_mult8", rule=rule, gpu_peak_mib=round(torch.cuda.max_memory_allocated() / 2 ** 20, 1))
            f.write(json.dumps(rec) + "\n"); f.flush()
    print(json.dumps({"out": str(out), "roots": sum(1 for _ in open(out))}))


# --------------------------------------------------------------------------------------------- independent physical verification of the ONE selection
def verify(dom, files, workers, cpu0, cache_in=()):
    """Physical X / Y (unchanged teachers via evaluate._verify_job) of every selected REPAIR / NOOP in `files`, once per (root, sequence).  Read-only
    caches (e.g. the frozen V2 verify.jsonl, same teachers and roots) are consulted first; new results append to $V3OUT/verify_<dom>.jsonl."""
    import multiprocessing as mp
    import evaluate as EV
    EV.SNAP = ABF / "snapshot/abf_9de85710c2a7103f"
    os.environ["FIN3D_STORE"] = str(V3OUT / "verify_store_3d")
    cache_out = V3OUT / f"verify_{dom.lower()}.jsonl"
    have = set()
    for p in list(cache_in) + [cache_out]:
        for v in EV.jl(p):
            have |= {(v["root"], json.dumps(r["seq"])) for r in v["results"]}
    want = collections.defaultdict(set)
    for fn in files:
        for r in EV.jl(fn):
            if r["selected_ordered_seq"] and (r["root_id"], json.dumps(r["selected_ordered_seq"])) not in have:   # REPAIRs (NOOP/ABSTAIN need no teacher)
                want[r["root_id"]].add(json.dumps(r["selected_ordered_seq"]))
    rows = {r["root_id"]: r for split in ("val", "train") for r in EV.rows_of(dom.upper(), split)}
    jobs = []
    for root, seqs in sorted(want.items()):
        ids = rows[root]["inputs"]["ids"]
        path = EV.path_of(dom.upper(), rows[root])
        geom = "fastgeom1" if dom.upper() == "2D" and json.loads(Path(path).read_text()).get("geometry_impl") == "fastgeom1" else "original"
        jobs.append({"dom": dom.upper(), "path": str(path), "geom": geom, "seqs": [[(ids[i], c) for i, c in json.loads(s)] for s in sorted(seqs)]})
    print(json.dumps({"roots": len(want), "queries": sum(len(j["seqs"]) for j in jobs)}), flush=True)
    os.sched_setaffinity(0, set(range(cpu0, cpu0 + workers)))
    with open(cache_out, "a") as f:
        for geom in sorted({j["geom"] for j in jobs}):
            js = [j for j in jobs if j["geom"] == geom]
            with mp.get_context("spawn").Pool(workers, initializer=_boot, initargs=(dom.upper(), geom), maxtasksperchild=50) as pool:
                for i, r in enumerate(pool.imap_unordered(EV._verify_job, js), 1):
                    ids = rows[r["root"]]["inputs"]["ids"]
                    for x in r["results"]:
                        x["seq"] = [[ids.index(o), c] for o, c in x["seq"]]
                    r["teacher_provenance"] = "unchanged finalized teacher (evaluate._verify_job), V3 run"
                    f.write(json.dumps(r) + "\n"); f.flush()
                    if i % 25 == 0:
                        print(f"{time.strftime('%H:%M:%S')} {geom} {i}/{len(js)}", flush=True)


def legacy(search_file, rule_file, out, label):
    """Old V1/V2 search output (search.search records) -> the V3 per-root record format, selection by the same frozen rule (evaluate.select)."""
    import evaluate as EV
    rule = json.loads(Path(rule_file).read_text())
    with open(out, "w") as f:
        for r in EV.jl(search_file):
            pick = EV.select(r["cands"], rule)
            sel = next((c for c in r["cands"] if c["seq"] == pick), None) if pick is not None else None
            acts = sorted({tuple(a) for c in r["cands"] for a in c["seq"]})
            f.write(json.dumps({"root_id": r["root"], "K": r["K"], "arm": label, "seed": r.get("seed", 0), "selected_ordered_seq": pick,
                                "decision": "ABSTAIN" if pick is None else ("NOOP" if not pick else "REPAIR"), "p11": sel and sel["p11"],
                                "proposal_actions": [list(a) for a in acts], "planner_calls": r.get("planner_calls", 0), "rule": rule,
                                "candidate_budget": {"n_scored": r["scorer_evals"], "raw_draws": r["raw_draws"], "sampler_calls": r["sampler_calls"],
                                                     "expansions": r["expansions"], "unique_actions": len(acts),
                                                     "built_by_len": [sum(c["m"] == k for c in r["cands"]) for k in (1, 2, 3)]},
                                "wall_s": {"total": r["wall_s"]}, "cands": r["cands"]}) + "\n")
    print(out)


def summary(dom, files, caches, out, ref=None, B=2000):
    """Per arm on its roots: decisions, verified top-1 task / repair success, no-op and abstention (legacy protocol), known-assignment ingredient
    recall and presence in the scored set, confirmed-success presence (known X=1/Y=1 order or a verified candidate), conditional selection
    success, failure attribution (success / ranking failure / unresolved; never 'proposal failure' without labels), budgets and latency, and the
    paired root-cluster bootstrap difference in task success vs `ref`."""
    import numpy as np
    import contracts as CT
    import evaluate as EV
    rows = {r["root_id"]: r for r in map(json.loads, open(ABF / "snapshot/abf_9de85710c2a7103f" / f"data{dom.lower()}.jsonl"))}
    ver = {}
    for p in caches:
        for v in EV.jl(p):
            for x in v["results"]:
                xv, yv = (x["x"] or {}).get("x"), (x["y"] or {}).get("y")
                if dom.upper() == "3D":
                    xv = xv if (x["x"] or {}).get("resolution", "EVALUATED") == "EVALUATED" else None
                    yv = yv if (x["y"] or {}).get("resolution", "EVALUATED") == "EVALUATED" else None
                ver[(v["root"], json.dumps(x["seq"]))] = int(xv == 1 and yv == 1) if xv in (0, 1) and yv in (0, 1) else None
    res, per_root = {}, {}
    for fn in files:
        recs = EV.jl(fn)
        arm = recs[0].get("arm", Path(fn).stem) + ("" if "_M" not in Path(fn).stem else "|" + Path(fn).stem.split("_", 1)[1])
        S = collections.defaultdict(list)
        for r in recs:
            row = rows[r["root_id"]]
            mk, K = row["masks"], row["K_legacy"]
            Y = {CT.ekey(y["edit"]): y["y"] for y in row["labels"]["Y"]}
            known_ok = {json.dumps(q["seq"]) for q in row["labels"]["X"] if q["x"] == 1 and Y.get(CT.ekey(q["seq"])) == 1}
            pa = CT.positive_assignments(row)
            acts = {tuple(a) for a in r["proposal_actions"]}
            scored = {json.dumps(c["seq"]) for c in r["cands"] if c["seq"]}
            scored_ekeys = {CT.ekey(json.loads(s)) for s in scored}
            sel = r["selected_ordered_seq"]
            v = ver.get((r["root_id"], json.dumps(sel))) if sel else None
            succ = bool(sel) and v == 1
            conf = bool(scored & known_ok) or any(ver.get((r["root_id"], s)) == 1 for s in scored)
            if mk["eval_task"]:
                S["task"].append(succ); S["unverified"].append(bool(sel) and v is None)
                if pa:
                    S["ingredient_recall"].append(any(all(tuple(a) in acts for a in A["assignment"]) for A in pa.values()))
                    S["known_assignment_scored"].append(any(k in scored_ekeys for k in pa))
                S["confirmed_success_in_scored"].append(conf)
                S["known_success_order_in_scored"].append(bool(scored & known_ok))
                if conf:
                    S["conditional_selection"].append(succ)
                S["attr_" + ("success" if succ else "ranking_failure" if conf else "unresolved")].append(1)
                S["task_K" + K].append(succ)
            if mk["eval_repair"]:
                S["repair"].append(succ and len(sel) == int(K))
            if mk["eval_noop"]:
                S["noop"].append(r["decision"] == "NOOP")
            if mk["eval_abstain"]:
                S["abstain"].append(r["decision"] == "ABSTAIN")
            S["n_scored"].append(r["candidate_budget"]["n_scored"]); S["wall_total"].append(r["wall_s"]["total"])
            S["unique_actions"].append(r["candidate_budget"]["unique_actions"])
            for k in (1, 2, 3):
                S[f"scored_K{k}"].append(r["candidate_budget"]["built_by_len"][k - 1])
            S["mode_complete"].append(r["candidate_budget"].get("mode") == "complete")
            S["planner_calls"].append(r.get("planner_calls", 0))
            S["decision_" + r["decision"]].append(1)
            if mk["eval_task"]:
                per_root.setdefault(arm, {})[r["root_id"]] = float(succ)
        n = lambda k: len(S[k])  # noqa: E731
        res[arm] = {"roots": len(recs), "task_success": float(np.mean(S["task"])), "n_task": n("task"),
                    **{f"task_K{K}": float(np.mean(S[f"task_K{K}"])) for K in "123" if S[f"task_K{K}"]},
                    "repair_success": float(np.mean(S["repair"])) if S["repair"] else None, "n_repair": n("repair"),
                    "noop_correct": float(np.mean(S["noop"])) if S["noop"] else None, "n_noop": n("noop"),
                    "abstain_correct": float(np.mean(S["abstain"])) if S["abstain"] else None, "n_abstain": n("abstain"),
                    "unverified_selected_repairs": int(sum(S["unverified"])),
                    "ingredient_recall_known": float(np.mean(S["ingredient_recall"])), "known_assignment_in_scored_set": float(np.mean(S["known_assignment_scored"])),
                    "confirmed_success_in_scored_set": float(np.mean(S["confirmed_success_in_scored"])),
                    "known_success_order_in_scored_set": float(np.mean(S["known_success_order_in_scored"])),
                    "conditional_selection_success": float(np.mean(S["conditional_selection"])) if S["conditional_selection"] else None,
                    "attribution_task_roots": {k[5:]: n(k) for k in S if k.startswith("attr_")},
                    "decisions": {k[9:]: n(k) for k in S if k.startswith("decision_")},
                    "n_scored_median": float(np.median(S["n_scored"])), "n_scored_p90": float(np.percentile(S["n_scored"], 90)),
                    "scored_by_len_mean": [float(np.mean(S[f"scored_K{k}"])) for k in (1, 2, 3)], "unique_actions_mean": float(np.mean(S["unique_actions"])),
                    "complete_enumeration_fraction": float(np.mean(S["mode_complete"])), "planner_calls_total": int(sum(S["planner_calls"])),
                    "latency_s_median": float(np.median(S["wall_total"])), "latency_s_p90": float(np.percentile(S["wall_total"], 90))}
    if ref:
        g = np.random.default_rng(0)
        for arm, d in per_root.items():
            if arm == ref or ref not in per_root:
                continue
            common = sorted(set(d) & set(per_root[ref]))
            x = np.array([d[k] - per_root[ref][k] for k in common])
            bs = [x[g.integers(0, len(x), len(x))].mean() for _ in range(B)]
            res[arm]["task_delta_vs_" + ref] = {"delta": float(x.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], "roots": len(x)}
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def _boot(dom, geom):
    import evaluate as EV
    EV._boot(dom, geom)
    if dom == "2D":
        (V3OUT / "teacher2d_witnesses").mkdir(parents=True, exist_ok=True)
        EV._W["T"]._M["wout"] = str(V3OUT / "teacher2d_witnesses")


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "run":
        run(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), *(int(x) for x in sys.argv[6:8]))
    elif c == "verify":
        verify(sys.argv[2], sys.argv[3].split(","), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6].split(",") if len(sys.argv) > 6 else ())
    elif c == "legacy":
        legacy(*sys.argv[2:6])
    elif c == "summary":
        summary(sys.argv[2], sys.argv[3].split(","), sys.argv[4].split(","), sys.argv[5], sys.argv[6] if len(sys.argv) > 6 else None)
    else:
        raise SystemExit(__doc__)
