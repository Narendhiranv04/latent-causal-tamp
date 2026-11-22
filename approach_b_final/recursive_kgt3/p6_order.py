#!/usr/bin/env python3
"""P6A — PUBLIC, training-free, execution-aware ORDER composition for a FIXED endpoint assignment (same object -> destination pairs,
each object moved once, target never moved).  Inputs: learner-visible DEV scene (dev_public), sealed P4 planner candidate pools
(planner outputs, no labels) and the frozen K<=3 scorer.  Never reads kill tables, private witnesses, teacher rows or certified K.

Score (lower = better), causal sliding windows of the frozen chained-X head:
    px_j = frozen px( window = moves[j-w+1 .. j] | HYPOTHETICAL scene Edit(S0, moves[0 .. j-w]) with the robot at q_ref )
    C(order) = sum_j -log max(eps, px_j)          components reported: sum, mean, bottleneck (max), first-move
  Inside a window the frozen head models chained relocations with carried robot state (its K<=3 training semantics); across windows the
  robot is ASSUMED back at q_ref.  px_j is therefore a hypothetical-prefix ranking signal, not a physical execution estimate.
Search: beam over ordered prefixes; key = (set of done moves, last w-1 moves).  C is Markov in that key, so merging on it is exact
  (beam width >= #keys == exact DP); different histories with different last moves are kept separately.  Ties: (cost, sequence).
    python p6_order.py run ENDPOINTS.jsonl DEV_PUBLIC OUT.jsonl [--device cuda]      (ENDPOINTS from `select` or an evaluator file)
    python p6_order.py select P4_DIR DEV_PUBLIC OUT_ENDPOINTS.jsonl                  (public endpoint selection, see select())
    python p6_order.py score ORDERS.jsonl DEV_PUBLIC OUT.jsonl                       (per-step px of given orders, W1/W2/W3/P4CHUNK)"""
import hashlib, json, math, random, sys, time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CFG = {"eps": 1e-4, "w": 3, "B": 16, "keep": 5, "n_endpoints_per_root": 2, "arms_P4": ("R2", "R3", "F"), "budgets": (1, 4, 16, 64),
       "score_modes": ("W1", "W2", "W3", "RANDSCORE")}


def jl(p):
    return [json.loads(l) for l in open(p)]


def nll(p, eps=CFG["eps"]):
    return -math.log(max(eps, p))


def _u(*a):
    return int(hashlib.sha256("|".join(map(str, a)).encode()).hexdigest()[:12], 16) / 16 ** 12


class Scorer:
    """Window px oracle with per-endpoint caches.  mode W1/W2/W3 = frozen px with window 1/2/3; RANDSCORE = seeded uniform (matched control).
    mk_hr is injectable for the mock tests (default: data.HypoRoot, the audited hypothetical-scene view)."""
    def __init__(s, M, row0, mode="W3", mk_hr=None):
        import data as DA
        s.M, s.row0, s.mode, s.hrc, s.calls = M, row0, mode, {}, 0
        s.w = {"W1": 1, "W2": 2}.get(mode, 3)
        s.mk_hr = mk_hr or (lambda base: DA.HypoRoot(row0, [list(a) for a in base]))

    def hr(s, base):
        k = tuple(sorted(base))                               # the hypothetical scene depends only on WHICH moves are done
        if k not in s.hrc:
            s.hrc[k] = s.mk_hr(k)
        return s.hrc[k]

    def step_batch(s, items):
        """items [(prefix tuple, action)] -> px of the window ending at action (base = prefix minus its last w-1 moves)."""
        out, groups = [None] * len(items), defaultdict(list)
        for i, (p, a) in enumerate(items):
            base = p[:max(0, len(p) - (s.w - 1))]
            groups[base].append((i, tuple(p[len(base):]) + (a,)))
        for base, L in groups.items():
            s.calls += len(L)
            if s.mode == "RANDSCORE":
                r = [_u("RS", s.row0["root_id"], base, q) for _, q in L]
            else:
                r = [x["px"] for x in s.M.score(s.hr(base), [q for _, q in L])]
            for (i, _), x in zip(L, r):
                out[i] = float(x)
        return out

    def steps(s, order):
        order = [tuple(a) for a in order]
        return s.step_batch([(tuple(order[:j]), order[j]) for j in range(len(order))])

    def p4chunk(s, order):
        """P4's fixed stride-3 chunks (non-causal): px of moves[j:j+3] in Edit(S0, moves[:j]) for j = 0, 3, 6, ..."""
        order = [tuple(a) for a in order]
        return [s.M.score(s.hr(tuple(order[:j])), [tuple(order[j:j + 3])])[0]["px"] for j in range(0, len(order), 3)]


def components(px):
    v = [nll(x) for x in px]
    return {"C": sum(v), "mean": sum(v) / len(v), "bottleneck": max(v), "first": v[0], "px": px}


def beam(sc, acts, B, keep=CFG["keep"]):
    """Beam over ordered prefixes, merging exactly on (done set, last w-1 moves).  Returns top `keep` complete orders + search stats."""
    acts = sorted(tuple(a) for a in acts); m = len(acts)
    cur = {(): (0.0, [])}                                   # prefix -> (cost, px list)
    expanded = merged = 0
    for _ in range(m):
        items = [(p, a) for p in cur for a in acts if a not in p]
        px = sc.step_batch(items); expanded += len(items)
        best = {}
        for (p, a), x in zip(items, px):
            q = p + (a,); c = cur[p][0] + nll(x)
            k = (frozenset(q), q[len(q) - (sc.w - 1):] if sc.w > 1 else ())
            if k not in best or (c, q) < (best[k][0], best[k][1]):
                merged += k in best
                best[k] = (c, q, cur[p][1] + [x])
        top = sorted(best.values(), key=lambda t: (t[0], t[1]))[:B]
        cur = {q: (c, pxs) for c, q, pxs in top}
    fin = sorted(((c, q, pxs) for q, (c, pxs) in cur.items()), key=lambda t: (t[0], t[1]))[:keep]
    return [{"order": [list(a) for a in q], **components(pxs)} for c, q, pxs in fin], {"expanded": expanded, "merged": merged}


def exhaustive(sc, acts):
    """Reference for tests (m <= 7): all permutations under the same score."""
    import itertools
    best = None
    for perm in itertools.permutations(sorted(tuple(a) for a in acts)):
        c = sum(nll(x) for x in sc.steps(perm))
        if best is None or (c, perm) < best:
            best = (c, perm)
    return best


def controls(row0, acts, src_order):
    """Public, model-free order heuristics (fixed orders on S0 geometry): ORIG (the P4 pool order), RANDOM (seeded), BASE_NEAR_FIRST
    (source closest to the robot base first), CLUTTER_LOW_FIRST (fewest S0 neighbours within 1.5 cells first, then base distance)."""
    inp = row0["inputs"]; xy = {int(k): v for k, v in inp["cell_xy"].items()}; c0 = [int(c) for c in inp["cells0"]]; b = inp["base"]
    pitch = abs(xy[1][0] - xy[0][0])
    dist = lambda o: math.dist(xy[c0[o]], b)  # noqa: E731
    nb = lambda o: sum(1 for j, c in enumerate(c0) if j != o and math.dist(xy[c], xy[c0[o]]) <= 1.5 * pitch + 1e-9)  # noqa: E731
    acts = sorted(tuple(a) for a in acts); rnd = list(acts); random.Random(_u("CTRL", row0["root_id"], acts)).shuffle(rnd)
    return {"ORIG": [tuple(a) for a in src_order], "RANDOM": rnd, "BASE_NEAR_FIRST": sorted(acts, key=lambda a: (dist(a[0]), a)),
            "CLUTTER_LOW_FIRST": sorted(acts, key=lambda a: (nb(a[0]), dist(a[0]), a))}


def select(p4, dev_public, out, n=CFG["n_endpoints_per_root"]):
    """PUBLIC endpoint selection: per DEV root, the union of sealed P4 R2/R3/F candidate pools, deduplicated by sorted assignment, ranked by
    the frozen endpoint hY stored with each candidate (desc; ties: lower recorded energy C, then signature); keep the top n.  ORIG order =
    the lowest-energy recorded order of that assignment.  No label, teacher row, kill table or certified K is read."""
    rows = []
    for r in jl(dev_public):
        E = {}
        for a in CFG["arms_P4"]:
            for c in json.loads((Path(p4) / a / "traces" / f"{r['root_id']}.json").read_text())["cands"]:
                sig = json.dumps(sorted([int(o), int(d)] for o, d in c["seq"]))
                e = E.setdefault(sig, {"hY": c["hY"], "C": c["C"], "order": c["seq"], "arms": set()})
                e["arms"].add(a)
                if c["C"] < e["C"]:
                    e.update(C=c["C"], order=c["seq"])
        for k, (sig, e) in enumerate(sorted(E.items(), key=lambda t: (-t[1]["hY"], t[1]["C"], t[0]))[:n]):
            rows.append({"root_id": r["root_id"], "endpoint_signature": sig, "rank_public": k, "hY_frozen": e["hY"], "src_order": e["order"],
                         "src_arms": sorted(e["arms"]), "set": "PUBLIC_TOP_HY"})
    Path(out).write_text("".join(json.dumps(x) + "\n" for x in rows))
    print(json.dumps({"endpoints": len(rows), "roots": len({x["root_id"] for x in rows})}))


def run(endpoints, dev_public, out, device="cuda"):
    import models as MD
    import data as DA
    pub = {r["root_id"]: r for r in jl(dev_public)}; E = jl(endpoints)
    M = MD.Frozen(device)
    DA.install_guard([HERE, HERE.parent, Path(out).parent, Path(endpoints).parent, Path(dev_public).parent, Path(sys.executable).resolve().parents[1]])
    with open(out, "w") as f:
        for e in E:
            row0 = pub[e["root_id"]]; acts = [tuple(a) for a in json.loads(e["endpoint_signature"])]
            assert DA.check_sequence(row0, [list(a) for a in e["src_order"]]) is None and sorted(map(tuple, e["src_order"])) == sorted(acts)
            rec = {k: e[k] for k in e if k != "src_order"} | {"m": len(acts), "arms": {}}
            t0, c0 = time.time(), dict(M.c)
            for mode in CFG["score_modes"]:                          # score ablations at the default budget
                sc = Scorer(M, row0, mode); top, st = beam(sc, acts, CFG["B"])
                rec["arms"][f"{mode}_B{CFG['B']}"] = {"top": top, "stats": st, "window_calls": sc.calls}
            for B in CFG["budgets"]:                                 # budget ablation for the main score
                if B != CFG["B"]:
                    sc = Scorer(M, row0, "W3"); top, st = beam(sc, acts, B)
                    rec["arms"][f"W3_B{B}"] = {"top": top, "stats": st, "window_calls": sc.calls}
            sc = Scorer(M, row0, "W3")
            for name, o in controls(row0, acts, e["src_order"]).items():   # heuristic controls, scored by the same frozen W3 score
                rec["arms"][name] = {"top": [{"order": [list(a) for a in o], **components(sc.steps(o))}], "window_calls": len(o)}
            for arm in rec["arms"].values():                         # every order also gets the P4 fixed-chunk score (rerank ablation)
                for t in arm["top"]:
                    t["P4CHUNK"] = sum(nll(x) for x in sc.p4chunk(t["order"]))
                    assert DA.check_sequence(row0, t["order"]) is None and sorted(map(tuple, t["order"])) == sorted(acts)
            rec["frozen_calls"] = {k: M.c.get(k, 0) - c0.get(k, 0) for k in M.c}; rec["wall_s"] = round(time.time() - t0, 2)
            f.write(json.dumps(rec) + "\n"); f.flush()
            for c in ("_sc", "_prop", "_yend"):
                getattr(M, c).clear()
    print(json.dumps({"endpoints": len(E), "out": str(out)}))


def score(orders, dev_public, out, device="cuda"):
    """Per-step frozen px of GIVEN orders (W1/W2/W3 + P4 chunks); the input file carries only (key, root_id, order)."""
    import models as MD
    import data as DA
    pub = {r["root_id"]: r for r in jl(dev_public)}; M = MD.Frozen(device)
    DA.install_guard([HERE, HERE.parent, Path(out).parent, Path(orders).parent, Path(dev_public).parent, Path(sys.executable).resolve().parents[1]])
    with open(out, "w") as f:
        for o in jl(orders):
            row0 = pub[o["root_id"]]
            r = {"key": o["key"], "root_id": o["root_id"], **{m: Scorer(M, row0, m).steps(o["order"]) for m in ("W1", "W2", "W3")}}
            r["P4CHUNK"] = Scorer(M, row0, "W3").p4chunk(o["order"])
            f.write(json.dumps(r) + "\n")
            M._sc.clear()
    print(json.dumps({"scored": "ok", "out": str(out)}))


if __name__ == "__main__":
    a = sys.argv[1:]; dev = "--device" in a and a[a.index("--device") + 1] or "cuda"
    {"select": lambda: select(*a[1:4]), "run": lambda: run(a[1], a[2], a[3], dev), "score": lambda: score(a[1], a[2], a[3], dev)}[a[0]]()
