"""Home-anchored chunk ranking (plan §4).  For a fixed ordered candidate r and a partition pi into chunks of 1-3 relocations:
    E_home(r, pi) = - sum_j log max(eps, pX(c_j | S_{j-1}, q_ref, ORIGINAL task)) - log max(eps, Y_final(r))      (uncalibrated ranking)
A single chunk (|r| <= 3, pi = (|r|,)) keeps the exact frozen joint p11:  E = - log max(eps, p11(r | S0)).
The best partition is found by DP over the prefix index (edge i -> j, 1 <= j - i <= 3, cost from the rebased scene S_i) and is checked
against brute-force enumeration in the tests.  The partition actually scored is the one that is executed (R0 issue 11)."""
from __future__ import annotations

import json, math

import views as V

EPS = 1e-8


def chunk_cost(fz, row0, seq, i, j):
    x = fz.score(V.rebase(row0, seq[:i]), [seq[i:j]])[0]["px"]
    return -math.log(max(EPS, x))


def final_y(fz, row0, seq, mode="global"):
    if mode == "global":
        return fz.y_global(row0, [seq])[0]
    return fz.p_noop(V.rebase(row0, seq))                                    # Y_rebase diagnostic (fresh-root no-op readout)


def best_partition(fz, row0, seq, ymode="global"):
    """-> (E, partition tuple, per-chunk pX, Y_final).  Multi-chunk: DP; single chunk m <= 3: exact p11 (compared on the same E scale)."""
    m = len(seq)
    if m == 0:
        return 0.0, (), [], None
    yf = final_y(fz, row0, seq, ymode)
    ey = -math.log(max(EPS, yf))
    best = {0: (0.0, 0, ())}                                                   # prefix length -> (cost, n_chunks, partition)
    for j in range(1, m + 1):
        opts = []
        for g in range(1, min(3, j) + 1):
            i = j - g
            if i not in best or (i == 0 and j == m):                          # the single-chunk partition is scored by p11 below
                continue
            c, n, p = best[i]
            opts.append((c + chunk_cost(fz, row0, seq, i, j), n + 1, p + (g,)))
        if opts:
            best[j] = min(opts, key=lambda t: (round(t[0], 12), t[1], t[2]))
    cands = []
    if m <= 3:
        p11 = fz.score(row0, [seq])[0]["p11"]
        cands.append((-math.log(max(EPS, p11)), 1, (m,)))
    if m in best and best[m][2]:
        c, n, p = best[m]
        cands.append((c + ey, n, p))
    E, _, part = min(cands, key=lambda t: (round(t[0], 12), t[1], t[2]))
    px = [] if part == (m,) and m <= 3 else [math.exp(-chunk_cost(fz, row0, seq, s, s + g)) for s, g in _starts(part)]
    return E, part, px, yf


def _starts(part):
    s = 0
    for g in part:
        yield s, g; s += g


def brute_partition(fz, row0, seq, ymode="global"):
    """Exhaustive reference for the DP (tests)."""
    m = len(seq)
    yf = final_y(fz, row0, seq, ymode); ey = -math.log(max(EPS, yf))
    out = []
    for part in V.partitions(m):
        if part == (m,) and m <= 3:
            out.append((-math.log(max(EPS, fz.score(row0, [seq])[0]["p11"])), 1, part))
        elif len(part) > 1 or m > 3:
            if len(part) == 1:
                continue
            out.append((sum(chunk_cost(fz, row0, seq, s, s + g) for s, g in _starts(part)) + ey, len(part), part))
    return min(out, key=lambda t: (round(t[0], 12), t[1], t[2]))


def select(row0, cands, fz, rule):
    """Frozen NOOP gate at S0 (production rule), then fixed top-1 by E (lower is better); ABSTAIN only when the pool is empty.
    Declared: no eta admission for the long arms (E is not calibrated), unlike B0's p11 >= 0.3."""
    noop = fz.p_noop(row0)
    if noop >= rule["noop_gate"]:
        return None, "NOOP_GATE", noop
    pool = [c for c in cands if c["seq"]]
    if not pool:
        return None, "ABSTAIN_EMPTY_POOL", noop
    best = min(pool, key=lambda c: (round(c["E"], 12), len(c["seq"]), len(c["partition"]), round(V.displacement(row0, c["seq"]), 9), json.dumps(c["seq"])))
    return best, "SELECTED", noop


def b0(fz, row0, rule, kmax=3):
    """Released EXACT4 K <= 3 (search_sets.choose semantics): D4 at S0, all legal sets x all orders, frozen p11, gate 0.5, eta 0.3,
    argmin (round(-log p, 12), m, displacement, signature)."""
    import itertools
    import construct as CO
    D = fz.proposals(row0, V.eligible(row0))
    D = {o: v for o, v in D.items() if v}
    seqs = [[list(a) for a in p] for k in range(1, kmax + 1) for A in CO.assignments(D, k) for p in itertools.permutations(A)]
    sc = fz.score(row0, [[]] + seqs)
    noop = sc[0]["p11"]
    if noop >= rule["noop_gate"]:
        return {"decision": "NOOP", "seq": None, "score": noop, "D4": D}
    pool = [(s, x["p11"]) for s, x in zip(seqs, sc[1:]) if x["p11"] >= rule["eta"]] + ([([], noop)] if noop >= rule["eta"] else [])
    if not pool:
        return {"decision": "ABSTAIN", "seq": None, "score": None, "D4": D}
    s, p = min(pool, key=lambda t: (round(-math.log(max(t[1], 1e-12)), 12), len(t[0]), round(V.displacement(row0, t[0]), 9), json.dumps(t[0])))
    return {"decision": "REPAIR" if s else "NOOP", "seq": s or None, "score": p, "D4": D}
