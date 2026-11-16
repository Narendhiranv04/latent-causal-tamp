#!/usr/bin/env python3
"""V3.2-A exact exhaustive top-M inference (frozen-model diagnostic; NOT a deployed search strategy).

Frozen task cVAE q2init_all (S1, V3 per-root generator seeding) -> top-6 legal destinations per eligible movable object (top-4 / top-5 are
prefixes: identical Monte-Carlo draws) -> EVERY statically legal ordered sequence of length 1-3 (construct.assignments order, all
permutations, no cap, no subsampling) streamed in fixed chunks -> frozen V3 D (+ the frozen V3 travel head, used only by rules with gamma > 0)
through the unchanged search.Scorer (X order-sensitive, endpoint Y shared by permutations) -> exact online selection.

A candidate belongs to M4 / M5 / M6 iff the largest proposal rank among its actions is < M.  For every M and every rule of evaluate.GRID the
selector reproduces xy.choose exactly: no-op gate first; admissible pool = {p11 >= eta} including the no-op; argmin of the key
(round(-log max(p11, 1e-12) + alpha m + beta D + gamma J_hat, 12), m, D, json signature).  Per chunk a numeric pre-filter keeps the
candidates within 1e-9 of the chunk minimum and the exact Python key decides; the no-op is merged at the end.

    python exhaustive.py run DOM SPLIT MMAX TAG [N]   -> $V3OUT/v32a/<dom>/<TAG>.jsonl (resumable)
    python exhaustive.py oldpath DOM SPLIT TAG        construct.run_root (B = 4,096, store=all) on every root, derived per-rule decisions"""
from __future__ import annotations

import itertools, json, math, os, sys, time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
ABF = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
V3OUT = Path(os.environ.get("V3OUT", str(ABF.parent / "runs")))
MS = (4, 5, 6)
TOP = 32


def grid():
    import evaluate as EV
    return EV.GRID


def stream(D6, mmax):
    """Yield (ordered sequence as tuple of (obj, dest), max proposal rank) for every legal ordered sequence over the top-mmax sets.
    Same enumeration as construct.build in complete mode (assignments in construct.assignments order, then all permutations)."""
    import construct as CO
    rank = {(o, d): i for o, v in D6.items() for i, d in enumerate(v)}
    D = {o: v[:mmax] for o, v in D6.items()}
    for k in (1, 2, 3):
        for a in CO.assignments(D, k):
            r = max(rank[x] for x in a)
            for p in itertools.permutations(a):
                yield p, r


def key(cost, m, D, seq):
    return (round(cost, 12), int(m), float(D), json.dumps([list(map(int, x)) for x in seq]))


class Selectors:
    """Online argmin of the xy.choose key for every (M, eta, alpha, beta, gamma); the no-op and the gate are applied in finish()."""

    def __init__(self, rules):
        self.rules = rules
        self.combos = sorted({(r["alpha"], r["beta"], r["gamma"]) for r in rules})
        self.etas = sorted({r["eta"] for r in rules})
        self.best = {}                                     # (M, eta, combo) -> (key, payload)

    def update(self, seqs, p, m, D, J, r, extra):
        lp = -np.log(np.maximum(p, 1e-12))
        for combo in self.combos:
            a, b, g = combo
            cost = lp + a * m + b * D + g * J
            for M in MS:
                inM = r < M
                for eta in self.etas:
                    idx = np.nonzero(inM & (p >= eta))[0]
                    if not len(idx):
                        continue
                    c = cost[idx]
                    near = idx[c <= c.min() + 1e-9]
                    cand = min((key(float(cost[i]), m[i], D[i], seqs[i]), int(i)) for i in near)
                    k0, i0 = cand
                    cur = self.best.get((M, eta, combo))
                    if cur is None or k0 < cur[0]:
                        self.best[(M, eta, combo)] = (k0, {"seq": [list(map(int, x)) for x in seqs[i0]], "p11": float(p[i0]), "cost": float(cost[i0]),
                                                          "m": int(m[i0]), "D": float(D[i0]), **{k: float(v[i0]) for k, v in extra.items()}})

    def finish(self, p_noop):
        """-> {M: [decision per rule in self.rules order]} with decision = {"seq": None (ABSTAIN) | [] (NOOP) | [[o, d], ...], ...}."""
        out = {}
        for M in MS:
            ds = []
            for rule in self.rules:
                if rule.get("noop_gate") is not None and p_noop >= rule["noop_gate"]:
                    ds.append({"seq": [], "p11": p_noop}); continue
                best = self.best.get((M, rule["eta"], (rule["alpha"], rule["beta"], rule["gamma"])))
                if p_noop >= rule["eta"]:
                    kn = key(-math.log(max(p_noop, 1e-12)) + 0.0, 0, 0.0, [])
                    if best is None or kn < best[0]:
                        ds.append({"seq": [], "p11": p_noop}); continue
                ds.append(None if best is None else best[1])
            out[M] = ds
        return out


def frozen_rule(dom):
    return json.loads((V3OUT / "v3_5" / f"rule_{dom}.json").read_text())


def score_root(root, D6, scorer, rules, mmax, known, chunk=8192):
    """Exhaustively score one root; -> record.  known: set of known X=1 / Y=1 ordered sequences (tuples) for coverage / rank diagnostics."""
    import torch
    t0 = time.time()
    sel = Selectors(rules)
    noop = scorer.score(root, [[]])[0]
    p_all, r_all = [], []
    cnt = {M: [0, 0, 0] for M in MS}
    found = {}
    tops = {M: [] for M in MS}
    buf, rbuf = [], []
    n_seen = set() if os.environ.get("V32_CHECK_UNIQUE") else None
    small = {}                                             # per-sequence p11 of the M4 pool, kept only while it has <= 4,096 sequences

    def flush():
        if not buf:
            return
        sc = scorer.score(root, [list(map(list, s)) for s in buf])
        p = np.array([c["p11"] for c in sc], float)
        J = np.array([c["J"] for c in sc], float)
        py = np.array([c["py"] for c in sc], float)
        px = np.array([c["px"] for c in sc], float)
        m = np.array([len(s) for s in buf])
        D = np.array([root.displacement(list(s)) for s in buf], float)
        r = np.array(rbuf)
        sel.update(buf, p, m, D, J, r, {"py": py, "px": px, "J": J})
        p_all.append(p.astype(np.float32)); r_all.append(r.astype(np.int8))
        for i, s in enumerate(buf):
            if s in known:
                found[s] = (float(p[i]), int(r[i]), float(py[i]), float(px[i]))
            if r[i] < 4 and small is not None:
                small[json.dumps([list(map(int, x)) for x in s])] = float(p[i])
        for M in MS:
            idx = np.nonzero(r < M)[0]
            if len(idx):
                top = idx[np.argsort(-p[idx], kind="stable")[:TOP]]
                tops[M] = sorted(tops[M] + [(float(p[i]), json.dumps([list(map(int, x)) for x in buf[i]]), float(py[i]), float(px[i])) for i in top],
                                 key=lambda t: (-t[0], t[1]))[:TOP]
        buf.clear(); rbuf.clear()

    for s, r in stream(D6, mmax):
        if n_seen is not None:
            assert s not in n_seen, s
            n_seen.add(s)
        for M in MS:
            if r < M:
                cnt[M][len(s) - 1] += 1
        buf.append(s); rbuf.append(r)
        if len(buf) >= chunk:
            flush()
            if small is not None and len(small) > 4096:
                small = None
    flush()
    if small is not None and len(small) > 4096:
        small = None
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    P = np.concatenate(p_all) if p_all else np.zeros(0, np.float32)
    R = np.concatenate(r_all) if r_all else np.zeros(0, np.int8)
    dec = sel.finish(noop["p11"])
    per_M = {}
    for M in MS:
        inM = R < M
        pm = P[inM]
        ks = {json.dumps([list(x) for x in s]): v for s, v in found.items() if v[1] < M}
        best_known = max(ks.items(), key=lambda kv: kv[1][0]) if ks else None
        per_M[M] = {"counts_by_K": cnt[M], "n_scored": int(inM.sum()),
                    "n_admissible": {str(e): int((pm >= e).sum()) for e in (0.1, 0.3)},
                    "known_success_in_pool": len(ks),
                    "best_known": None if best_known is None else {"seq": json.loads(best_known[0]), "p11": best_known[1][0], "py": best_known[1][2],
                                                                     "px": best_known[1][3], "rank_by_p11": int((pm > best_known[1][0]).sum()) + 1},
                    "decisions": dec[M], "top": tops[M]}
    return {"root_id": root.id, "K": root.row["K_legacy"], "n_movable": len(root.movable), "D6": {str(o): v for o, v in D6.items()},
            "p_noop": noop["p11"], "mmax": mmax, "per_M": {str(M): v for M, v in per_M.items() if M <= mmax}, "p11_M4_small": small,
            "wall_s": round(time.time() - t0, 3)}


def known_success(row):
    import contracts as CT
    Y = {CT.ekey(y["edit"]): y["y"] for y in row["labels"]["Y"]}
    return {tuple(tuple(map(int, a)) for a in q["seq"]) for q in row["labels"]["X"] if q["x"] == 1 and Y.get(CT.ekey(q["seq"])) == 1}


def setup(dom, seed=0):
    import construct as CO
    import search as S
    samp = CO.make_sampler(dom, "task:q2init_all", seed, CO.RULES["S1"])
    dpath = os.environ.get("V32_SCORER")                                       # V3.2: e.g. .../p2_{dom}/D_s1/model.pt; sampler stays seed 0
    scor = S.Scorer(Path(dpath.format(dom=dom)) if dpath else V3OUT / "v3_5" / f"p2_{dom}" / f"D_s{seed}" / "model.pt",
                    ABF / "runs" / f"p3_{dom}" / f"cost_s{seed}" / "model.pt")
    return samp, scor


def proposals(root, samp, seed=0):
    import torch
    gen = torch.Generator(device=samp.dev).manual_seed(seed)                   # = construct.run_root / the V3.2 audit
    D = samp.propose_many(root, root.cells0, list(root.movable), 6, gen) if root.movable else {}
    return {int(o): [int(d) for d in v] for o, v in D.items()}


def rows_of(dom, split):
    snap = ABF / "snapshot/abf_9de85710c2a7103f"
    return [r for r in map(json.loads, open(snap / f"data{dom}.jsonl")) if r["split"] == split]


def run(dom, split, mmax, tag, n=None, chunk=8192):
    import torch
    import search as S
    out = V3OUT / "v32a" / dom
    out.mkdir(parents=True, exist_ok=True)
    fo = out / f"{tag}.jsonl"
    done = {json.loads(l)["root_id"] for l in open(fo)} if fo.exists() else set()
    samp, scor = setup(dom)
    rules = grid()
    rows = rows_of(dom, split)
    if n:
        import hashlib
        rows = sorted(rows, key=lambda r: hashlib.sha256(("v32sub|" + r["root_id"]).encode()).hexdigest())[:n]
    part = os.environ.get("V32_PART")                                          # 'i/k': this process scores roots with sha256(root) % k == i
    if part:
        import hashlib
        i_, k_ = map(int, part.split("/"))
        rows = [r for r in rows if int(hashlib.sha256(r["root_id"].encode()).hexdigest(), 16) % k_ == i_]
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    with open(fo, "a") as f:
        for r in rows:
            if r["root_id"] in done:
                continue
            root = S.Root(r, dom)
            D6 = proposals(root, samp)
            rec = score_root(root, D6, scor, rules, mmax, known_success(r), chunk)
            rec["gpu_peak_mib"] = round(torch.cuda.max_memory_allocated() / 2 ** 20, 1)
            f.write(json.dumps(rec) + "\n"); f.flush()
    print(json.dumps({"out": str(fo), "roots": sum(1 for _ in open(fo)), "s": round(time.time() - t0, 1)}), flush=True)


def oldpath(dom, split, tag):
    """The capped V3 path (construct.run_root, M = 4, B = 4,096, store=all) on every root -> per-rule decisions (evaluate.select on the stored
    pool) + mode (complete / budgeted) + the candidate set when complete, for parity and for the capped baseline."""
    import evaluate as EV
    import construct as CO
    import search as S
    out = V3OUT / "v32a" / dom
    out.mkdir(parents=True, exist_ok=True)
    fo = out / f"{tag}.jsonl"
    done = {json.loads(l)["root_id"] for l in open(fo)} if fo.exists() else set()
    samp, scor = setup(dom)
    rules = grid()
    with open(fo, "a") as f:
        for r in rows_of(dom, split):
            if r["root_id"] in done:
                continue
            rec = CO.run_root(S.Root(r, dom), samp, scor, 4, 4096, frozen_rule(dom), 0, store="all")
            cands = rec["cands"]
            kn = {json.dumps([list(x) for x in s]) for s in known_success(r)}
            pk = sorted((c["p11"] for c in cands if json.dumps(c["seq"]) in kn), reverse=True)
            allp = np.array([c["p11"] for c in cands[1:]], float)
            f.write(json.dumps({"root_id": r["root_id"], "K": r["K_legacy"], "mode": rec["candidate_budget"]["mode"],
                                "valid_by_len": rec["candidate_budget"]["valid_by_len"], "built_by_len": rec["candidate_budget"]["built_by_len"],
                                "p_noop": rec["p_noop"], "selected": rec["selected_ordered_seq"],
                                "decisions": [EV.select(cands, rule) for rule in rules],
                                "p11": {json.dumps(c["seq"]): c["p11"] for c in cands} if rec["candidate_budget"]["mode"] == "complete" else None,
                                "n_scored": rec["candidate_budget"]["n_scored"], "known_success_in_pool": len(pk),
                                "best_known_p11": pk[0] if pk else None, "best_known_rank": int((allp > pk[0]).sum()) + 1 if pk else None,
                                "n_admissible": {str(e): int((allp >= e).sum()) for e in (0.1, 0.3)},
                                "wall_s": rec["wall_s"]["total"]}) + "\n")
            f.flush()
    print(json.dumps({"out": str(fo), "roots": sum(1 for _ in open(fo))}), flush=True)


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "run":
        run(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], int(sys.argv[6]) if len(sys.argv) > 6 else None)
    elif c == "oldpath":
        oldpath(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit(__doc__)
