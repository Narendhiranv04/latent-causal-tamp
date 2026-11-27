#!/usr/bin/env python3
"""R4.1 frozen-cVAE proposal-coverage recovery (model-only; GPU).  No assignment optimization; the witness is used ONLY by the evaluator.
Per DEV witness root (P3.panel) and eligible object: the production S1 Monte-Carlo marginal (n_z 64, generator seed 0, the SAME batched call as
fz.proposals -> parity-checked against D4) gives the destination ranking.  Proposal arms:
  TOPk     k in 4 (production D4), 6, 8, 12: first k legal cells of the marginal ranking (GA keeps cells passing V.legal_seq)
  ANCn     ancestral latent sampling, n in 16, 64, 256, 1024 draws per object: z ~ N(0, I), d ~ softmax(masked dec(c, z)); union of cells
  FULL     every legal cell (diagnostic upper bound, not a learned proposal)
Fig. 3A (separate): the union of every (object, destination) proposed during recursive.discover R-FIG3 (scaling cfg), and the candidate pool.
ORACLE_PREFIX (evaluator diagnostic): witness destination rank in the marginal on the scene rebased after the witness prefix.
Witness-action failure taxonomy per arm: OBJECT_NOT_PROPOSED | DEST_ZERO_MASS (never sampled) | TRUNCATED (sampled, rank >= k) |
FILTERED (dropped by the grammar) | COVERED.
    $PYG cover.py DOM    -> O/kgt3/r4/cover_DOM.jsonl + cover_DOM.json"""
from __future__ import annotations

import collections, json, math, statistics, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
O = K.C.FIG3 / "kgt3" / "r4"
TOPK, ANC = (4, 6, 8, 12), (16, 64, 256, 1024)


def marg(fz, row, objs, n_z=64, seed=0, anc=()):
    """-> ({obj: marginal np.array over cells}, legal list, {n: {obj: set(cells)}} ancestral unions, decoder evals) for one scene."""
    import numpy as np
    import placement as PL
    import search as S
    import torch
    R = S.Root(row, fz.dom); cells = R.cells0
    sp = fz.samp; m = sp.m
    cd = {R.ids[i]: c for i, c in enumerate(cells)}
    legal = R.legal_dests(cells)
    if not legal or not objs:
        return {o: None for o in objs}, legal, {}, 0
    Fs, Ms, Os, Ls = [], [], [], []
    for o in objs:
        F, Mk, occ, _ = PL.scene_features(fz.dom, R.pattr, cd, R.ids[o], R.legal)
        lg = np.zeros(len(occ), bool); lg[legal] = True
        if isinstance(m, PL.TaskCVAE):
            occ = np.concatenate([occ, PL.task_features(fz.dom, row["inputs"], cells, o, getattr(m, "task_on", True))])
        Fs.append((F - sp.mu) / sp.sd * Mk[:, None]); Ms.append(Mk); Os.append(occ); Ls.append(lg)
    T = lambda a, dt: torch.as_tensor(np.stack(a), dtype=dt, device=sp.dev)  # noqa: E731
    obj, mask, occ, lgl = T(Fs, torch.float32), T(Ms, torch.bool), T(Os, torch.float32), T(Ls, torch.bool)
    gen = torch.Generator(device=sp.dev).manual_seed(seed)
    p, ev = PL.marginal(m, obj, mask, occ, lgl, None, n_z, gen)
    P = {o: p[i].double().cpu().numpy() for i, o in enumerate(objs)}
    U = {}
    with torch.no_grad():
        c = m.enc(obj, mask, occ)
        for n in anc:
            g = torch.Generator(device=sp.dev).manual_seed(1000 + n)
            z = torch.randn(c.shape[0], n, m.zdim, device=c.device, generator=g)
            pr = PL.masked(m.dec(torch.cat([c[:, None].expand(-1, n, -1), z], -1)), lgl[:, None]).softmax(-1)
            d = torch.multinomial(pr.reshape(-1, pr.shape[-1]), 1, generator=g).reshape(c.shape[0], n)
            U[n] = {o: d[i].tolist() for i, o in enumerate(objs)}
            ev += n
    return P, legal, U, ev * len(objs)


def ranking(p, legal):
    lg = set(legal)
    return [int(c) for c in sorted(range(len(p)), key=lambda c: (-p[c], c)) if c in lg and p[c] > 0]


def proj(sizes, H):
    import compose as CP
    import planners as PL
    ub = {k: PL.elem(sizes, k) for k in range(1, H + 1)}
    return {"assign_ub": ub, "distinct_x": CP.distinct_requests(ub), "dp_lookups": sum(ub[k] * CP.nx(k) for k in range(4, H + 1)),
            "exact_envelope": all(v <= PL.CFG["assign_per_size"] for v in ub.values()) and CP.distinct_requests(ub) <= PL.CFG["exact_x_est"]}


def main(dom):
    import learn as LN
    import p3 as P3
    import planners as PL
    import recursive as RC
    import views as V
    fz, _ = LN.load(dom, "F0")
    H = PL.CFG["H"][dom]
    out, outf = [], open(O / f"cover_{dom}.jsonl", "w")
    for rid, row, A, W, meta in P3.panel(dom):
        r0 = {"root_id": row["root_id"], "domain": row["domain"], "inputs": row["inputs"]}
        W = [tuple(map(int, a)) for a in W]
        el = V.eligible(r0)
        fz.reset(); fz.caps = {}
        D4 = fz.proposals(r0, el)
        t0 = time.perf_counter()
        P, legal, U, ev = marg(fz, r0, el, anc=ANC)
        if str(fz.dev).startswith("cuda"):
            fz.torch.cuda.synchronize()
        wall = time.perf_counter() - t0
        rk = {o: ranking(P[o], legal) if P[o] is not None else [] for o in el}
        ok = lambda o, d: V.legal_seq(r0, [[o, d]], H)  # noqa: E731
        parity = all([d for d in rk[o] if True][:4] == D4[o][:4] or D4[o] == [] for o in el)
        arms = {}
        for k in TOPK:
            arms[f"TOP{k}"] = {o: [d for d in rk[o][:k] if ok(o, d)] for o in el}
        for n in ANC:
            arms[f"ANC{n}"] = {o: sorted({d for d in U[n][o] if ok(o, d)}) for o in el}
        arms["FULL"] = {o: [d for d in legal if ok(o, d)] for o in el}
        rec = {"root_id": rid, "K": meta["K"], "N": meta["N"], "n_eligible": len(el), "n_legal": len(legal), "D4_parity": parity, "decoder_evals": ev, "wall_s": round(wall, 3),
               "witness": [list(a) for a in W], "rank": {}, "arms": {}}
        for o, d in W:
            p = P.get(o)
            r = rk.get(o, [])
            rec["rank"][f"{o}:{d}"] = {"rank": r.index(d) if d in r else None, "mass": float(p[d]) if p is not None else None, "eligible": o in el,
                                       "legal_now": d in legal, "grammar_ok": ok(o, d)}
        for a, Dm in arms.items():
            why = {}
            for o, d in W:
                if o not in el or not rk.get(o) and a != "FULL":
                    why[f"{o}:{d}"] = "OBJECT_NOT_PROPOSED"
                elif d in Dm[o]:
                    why[f"{o}:{d}"] = "COVERED"
                elif a.startswith("TOP") and d in rk[o][:int(a[3:])]:
                    why[f"{o}:{d}"] = "FILTERED"
                elif a.startswith("ANC") and d in U[int(a[3:])][o]:
                    why[f"{o}:{d}"] = "FILTERED"
                elif a == "FULL":
                    why[f"{o}:{d}"] = "FILTERED" if d in legal else "NOT_LEGAL_NOW"
                elif P[o] is None or P[o][d] <= 0:
                    why[f"{o}:{d}"] = "DEST_ZERO_MASS"
                else:
                    why[f"{o}:{d}"] = "TRUNCATED" if a.startswith("TOP") else "NOT_SAMPLED"
            sizes = [len(v) for v in Dm.values() if v]
            draws = int(a[3:]) * len(el) if a.startswith("ANC") else None
            rec["arms"][a] = {"why": why, "action_recall": sum(v == "COVERED" for v in why.values()) / len(W), "assignment_covered": all(v == "COVERED" for v in why.values()),
                              "objects_with_proposals": len(sizes), "unique_dests": sum(sizes), "dup_rate": None if not draws else 1 - sum(len(set(U[int(a[3:])][o])) for o in el) / draws,
                              "proj": proj(sizes, H)}
        # ORACLE_PREFIX (evaluator diagnostic): witness destination rank on the scene after the witness prefix
        orp = []
        for i, (o, d) in enumerate(W):
            S = V.rebase(r0, [list(a) for a in W[:i]])
            Pp, lp, _, _ = marg(fz, S, [o])
            r = ranking(Pp[o], lp) if Pp[o] is not None else []
            orp.append(r.index(d) if d in r else None)
        rec["oracle_prefix_rank"] = orp
        # Fig. 3A: recursive retargeting proposal union and pool (scaling cfg, no displacement tie-break)
        fz.reset()
        t1 = time.perf_counter()
        rc = {**PL.CFG["rec"], "m_max": H, "wall_s": PL.CFG["wall_s"] * 0.6, "x_unique": PL.CFG["x_unique"], "y_unique": PL.CFG["y_unique"], "disp_tiebreak": False}
        ctx, pool, tree, stop = RC.discover(fz, r0, "R-FIG3", rc)
        uni = {(int(o), int(d)) for v in fz._p.values() for o, ds in v.items() for d in ds[:4]}
        sets = [sorted(tuple(map(int, a)) for a in P_) for P_, _, _ in pool.values()]
        pool_acts = {a for s in sets for a in s}
        rec["fig3a"] = {"proposal_union_actions": len(uni), "witness_action_recall_union": sum(a in uni for a in W) / len(W),
                        "witness_assignment_in_union": all(a in uni for a in W), "pool": len(pool), "witness_action_recall_pool": sum(a in pool_acts for a in W) / len(W),
                        "witness_set_in_pool": sorted(W) in sets, "best_overlap_pool": max((len(set(s) & set(W)) for s in sets), default=0), "stop": stop,
                        "wall_s": round(time.perf_counter() - t1, 3), "proposal_calls": fz.c["proposal_calls"], "temp_readouts": ctx.n["temp_readouts"]}
        outf.write(json.dumps(rec) + "\n"); outf.flush(); out.append(rec)
        print(rid, meta["K"], meta["N"], {a: round(v["action_recall"], 2) for a, v in rec["arms"].items()}, rec["oracle_prefix_rank"], rec["fig3a"]["witness_action_recall_union"], flush=True)
    summ = {"n": len(out), "D4_parity": sum(r["D4_parity"] for r in out), "arms": {}}
    for a in out[0]["arms"]:
        why = collections.Counter(v for r in out for v in r["arms"][a]["why"].values())
        summ["arms"][a] = {"action_recall": sum(r["arms"][a]["action_recall"] * len(r["witness"]) for r in out) / sum(len(r["witness"]) for r in out),
                           "assignment_coverage": sum(r["arms"][a]["assignment_covered"] for r in out), "why": dict(why),
                           "unique_dests_median": statistics.median(r["arms"][a]["unique_dests"] for r in out),
                           "exact_envelope_roots": sum(r["arms"][a]["proj"]["exact_envelope"] for r in out),
                           "distinct_x_median": statistics.median(r["arms"][a]["proj"]["distinct_x"] for r in out),
                           "dp_lookups_median": statistics.median(r["arms"][a]["proj"]["dp_lookups"] for r in out),
                           "by_K": {k: [sum(r["arms"][a]["assignment_covered"] for r in out if r["K"] == k), sum(1 for r in out if r["K"] == k)] for k in sorted({r["K"] for r in out})},
                           "dup_rate_median": statistics.median(r["arms"][a]["dup_rate"] for r in out) if a.startswith("ANC") else None}
    ranks = [v["rank"] for r in out for v in r["rank"].values()]
    summ["rank_hist"] = dict(collections.Counter("none" if x is None else str(x) if x < 12 else "12+" for x in ranks))
    summ["oracle_prefix_rank_hist"] = dict(collections.Counter("none" if x is None else str(x) if x < 12 else "12+" for r in out for x in r["oracle_prefix_rank"]))
    summ["fig3a"] = {"witness_action_recall_union": statistics.mean(r["fig3a"]["witness_action_recall_union"] for r in out),
                     "witness_assignment_in_union": sum(r["fig3a"]["witness_assignment_in_union"] for r in out),
                     "witness_action_recall_pool": statistics.mean(r["fig3a"]["witness_action_recall_pool"] for r in out),
                     "witness_set_in_pool": sum(r["fig3a"]["witness_set_in_pool"] for r in out), "pool_median": statistics.median(r["fig3a"]["pool"] for r in out),
                     "wall_median": statistics.median(r["fig3a"]["wall_s"] for r in out)}
    summ["by_N"] = {n: [sum(r["arms"]["TOP4"]["assignment_covered"] for r in out if r["N"] == n), sum(1 for r in out if r["N"] == n),
                        statistics.mean(r["arms"]["TOP4"]["action_recall"] for r in out if r["N"] == n), statistics.mean(r["arms"]["TOP12"]["action_recall"] for r in out if r["N"] == n)]
                    for n in sorted({r["N"] for r in out})}
    summ["neural_wall_median_s"] = statistics.median(r["wall_s"] for r in out)
    (O / f"cover_{dom}.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps(summ, default=str)[:3000])


if __name__ == "__main__":
    main(sys.argv[1])
