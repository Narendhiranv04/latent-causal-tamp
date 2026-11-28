#!/usr/bin/env python3
"""Planner-side inference (plan.md 5): public rows + frozen checkpoints in, one decision per root and arm out.  No labels, K, witnesses or
teacher are read here (allowlist: public rows {root_id, domain, inputs}, the bundle, the CR checkpoint).

  C0 / OURS    frozen bundle: exhaustive.proposals (S1 top-6, seed 0) -> top-4 -> all legal ordered K<=3 -> frozen X/Y -> production rule
  pool         CR-cVAE prior: BMAX raw trajectories from a root-derived RNG; budget b pool = unique legal sequences among the first b
               trajectories (nested prefixes of one stream), in first-appearance order; pool hash = sha256 of that ordered list
  C1 / CR-ONLY standalone: integrated decision head; REPAIR -> argmax approximate prior predictive log p(r | c) (L shared latents)
  C2 / CR+XY   the SAME pool (hash checked) scored once by the frozen X/Y; exhaustive.Selectors with the production rule

    python infer.py predict DOM PUBLIC.jsonl CKPT OUT.jsonl [--budgets 64,256,1024] [--main 256] [--L 64] [--c0] [--ids F]
    python infer.py parity  DOM PUBLIC.jsonl ARCHIVED_PRED.jsonl IDS.json OUT.json
    python infer.py timing  DOM PUBLIC.jsonl CKPT OUT.json --ids IDS.json [--caps 0.05,0.25,1.0] [--main 256]
  C3 / C4 (secondary, --controls with --c0): count-matched CR+XY continuing the same stream; C0-budgeted hash-stratified subset"""
from __future__ import annotations

import argparse, hashlib, itertools, json, math, os, sys, time
from pathlib import Path

import numpy as np
import torch

import data as D
from train import load as load_cr

for p in (str(D.ABF),):
    if p not in sys.path:
        sys.path.insert(0, p)
import benchmark as BM  # noqa: E402
import exhaustive as EX  # noqa: E402
import search as S  # noqa: E402

RULE = BM.RULE
TIE = ("NOOP", "ABSTAIN", "REPAIR")                       # deterministic decision-head tie order


def seed_of(tag, rid, seed):
    return int(hashlib.sha256(f"{tag}|{rid}|{seed}".encode()).hexdigest()[:15], 16)


def sync():
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def seq_key(s):
    return json.dumps([[int(o), int(d)] for o, d in s])


def pool_hash(seqs):
    return hashlib.sha256(json.dumps([json.loads(seq_key(s)) for s in seqs]).encode()).hexdigest()


def enc_t(dom, row, dev, musd):
    return {k: torch.as_tensor(v[None], device=dev) for k, v in D.encode(dom, row, musd).items()}


# ------------------------------------------------------------------------------------------------ C0
def c0(root, samp, scor, man):
    sync(); t0 = time.time()
    D6 = EX.proposals(root, samp, man["config"]["proposal_seed"])
    sync(); t1 = time.time()
    rec = EX.score_root(root, D6, scor, [man["config"]["rule"]], man["config"]["M"], set(), man["config"]["chunk"])
    sync(); t2 = time.time()
    d = rec["per_M"][str(man["config"]["M"])]["decisions"][0]
    return {"decision": "ABSTAIN" if d is None else "NOOP" if d["seq"] == [] else "REPAIR", "seq": None if d is None else d["seq"],
            "score_type": "p11", "score": None if d is None else d["p11"], "p_noop": rec["p_noop"],
            "proposals": {k: v[:man["config"]["M"]] for k, v in rec["D6"].items()}, "n_scored": rec["per_M"][str(man["config"]["M"])]["n_scored"],
            "counts_by_K": rec["per_M"][str(man["config"]["M"])]["counts_by_K"], "sampler_contexts": len(D6),
            "timing_s": {"proposal": round(t1 - t0, 5), "construct_score_select": round(t2 - t1, 5), "total": round(t2 - t0, 5)}}


def c0_props(root, samp, man):
    """DEV-only shortcut: C0's top-4 proposals and exact ordered-pool size (enumerated, not scored); no decision."""
    D6 = EX.proposals(root, samp, man["config"]["proposal_seed"])
    n = sum(1 for _ in EX.stream(D6, man["config"]["M"]))
    return {"props_only": True, "decision": None, "proposals": {str(k): v[:man["config"]["M"]] for k, v in D6.items()}, "n_scored": n}


# ------------------------------------------------------------------------------------------------ CR pool, C1, C2
def make_pool(m, dom, row, b1, bmax, seed):
    """-> raw trajectory index per draw (-1 = no candidate), unique legal sequences (first-appearance order), timing."""
    gen = torch.Generator(device=b1["tok"].device).manual_seed(seed_of("CRPOOL", row["root_id"], seed))
    sync(); t0 = time.time()
    o, d, n = m.sample(b1, bmax, gen)
    sync(); t1 = time.time()
    o, d, n = o.cpu().numpy(), d.cpu().numpy(), n.cpu().numpy()
    enc = {k: v[0].cpu().numpy() for k, v in b1.items()}
    uniq, idx, first, bad, fdraw = [], {}, [], 0, []
    for i in range(bmax):
        if n[i] == 0:
            first.append(-1); continue
        s = [[int(o[i, t]), int(d[i, t])] for t in range(n[i])]
        if D.static_legal(enc, s):
            bad += 1; first.append(-2); continue
        k = seq_key(s)
        if k not in idx:
            idx[k] = len(uniq); uniq.append(s); fdraw.append(i)
        first.append(idx[k])
    return {"traj": first, "uniq": uniq, "first_draw": fdraw, "illegal": bad, "sample_s": round(t1 - t0, 5)}


def prefix(P, b):
    """Budget-b pool: unique sequences among the first b trajectories, and raw counts."""
    tr = P["traj"][:b]
    ids = sorted({i for i in tr if i >= 0})
    cnt = np.bincount([i for i in tr if i >= 0], minlength=len(P["uniq"]))
    return [P["uniq"][i] for i in ids], {"raw": b, "no_candidate": tr.count(-1), "illegal": tr.count(-2), "unique": len(ids),
                                         "dup_draws": int(sum(cnt[i] - 1 for i in ids))}


def c1(m, root, b1, seqs, L, seed):
    """Standalone CR-ONLY: decision head + argmax approximate marginal likelihood over the unique pool."""
    sync(); t0 = time.time()
    with torch.no_grad():
        c, _, _ = m.encode(b1)
        pr = m.decision_logits(c).softmax(-1)[0].cpu().numpy()
    best = max(range(3), key=lambda k: (pr[k], -TIE.index(D.CLASSES[k])))
    head = D.CLASSES[best]
    ll, passes = None, 0
    if seqs:
        g = torch.Generator(device=b1["tok"].device).manual_seed(seed_of("CRLIK", root.id, seed))
        z = torch.randn(L, m.zdim, device=b1["tok"].device, generator=g)
        o, d, n = (torch.as_tensor(a, device=b1["tok"].device) for a in D.seq_arrays(seqs))
        ll, passes = m.marginal_loglik(b1, o, d, n, z)
        ll = ll.cpu().numpy()
    sync(); t1 = time.time()
    pick = None
    if seqs:
        key = lambda i: (-round(float(ll[i]), 9), len(seqs[i]), round(root.displacement(seqs[i]), 9), seq_key(seqs[i]))  # noqa: E731
        pick = min(range(len(seqs)), key=key)
    dec = head if head != "REPAIR" else ("REPAIR" if pick is not None else "ABSTAIN")
    return {"decision": dec, "seq": seqs[pick] if dec == "REPAIR" else ([] if dec == "NOOP" else None), "score_type": "log_marginal_likelihood",
            "score": float(ll[pick]) if dec == "REPAIR" else None, "head_probs": [round(float(x), 6) for x in pr], "head": head,
            "best_repair": None if pick is None else {"seq": seqs[pick], "loglik": float(ll[pick])}, "decoder_passes": passes,
            "loglik": None if ll is None else [round(float(x), 5) for x in ll], "select_s": round(t1 - t0, 5)}


def c2(scor, root, seqs, chunk=8192):
    """CR+XY: every unique pool sequence scored once by the frozen X/Y, production selector (exhaustive.Selectors, r = 0 for all)."""
    sync(); t0 = time.time()
    sel = EX.Selectors([RULE])
    noop = scor.score(root, [[]])[0]["p11"]
    p_all = []
    for s in range(0, len(seqs), chunk):
        buf = [tuple(tuple(a) for a in q) for q in seqs[s:s + chunk]]
        sc = scor.score(root, [list(map(list, q)) for q in buf])
        p = np.array([x["p11"] for x in sc], float)
        J = np.array([x["J"] for x in sc], float)
        mm = np.array([len(q) for q in buf])
        Dd = np.array([root.displacement(list(q)) for q in buf], float)
        sel.update(buf, p, mm, Dd, J, np.zeros(len(buf), int), {"py": np.array([x["py"] for x in sc], float), "px": np.array([x["px"] for x in sc], float)})
        p_all += p.tolist()
    d = sel.finish(noop)[4][0]
    sync(); t1 = time.time()
    return {"decision": "ABSTAIN" if d is None else "NOOP" if d["seq"] == [] else "REPAIR", "seq": None if d is None else d["seq"],
            "score_type": "p11", "score": None if d is None else d["p11"], "p_noop": noop, "n_scored": len(seqs),
            "p11": [round(x, 6) for x in p_all], "select_s": round(t1 - t0, 5)}


def common_gate(c1r, c2r, seqs):
    """Diagnostic (not a one-model baseline): frozen X/Y no-op gate, then the CR likelihood argmax repair (no eta); empty pool -> ABSTAIN."""
    if c2r["p_noop"] >= RULE["noop_gate"]:
        return {"decision": "NOOP", "seq": []}
    br = c1r["best_repair"]
    return {"decision": "REPAIR", "seq": br["seq"]} if br else {"decision": "ABSTAIN", "seq": None}


# ------------------------------------------------------------------------------------------------ secondary accounting controls
def c3(m, dom, row, b1, root, scor, target, seed=0, cap=4096, block=1024):
    """CR+XY count-matched: continue the SAME pool stream (block 0 = the main pool's 1,024 draws) until `target` unique legal sequences or `cap`
    raw draws; the first `target` uniques in first-appearance order are scored once by X/Y with the production selector."""
    gen = torch.Generator(device=b1["tok"].device).manual_seed(seed_of("CRPOOL", row["root_id"], seed))
    enc = {k: v[0].cpu().numpy() for k, v in b1.items()}
    uniq, seen, raw = [], set(), 0
    sync(); t0 = time.time()
    while raw < cap and len(uniq) < target:
        o, d, n = (x.cpu().numpy() for x in m.sample(b1, block, gen))
        for i in range(block):
            raw += 1
            if n[i] and len(uniq) < target:
                s = [[int(o[i, t]), int(d[i, t])] for t in range(n[i])]
                k = seq_key(s)
                if k not in seen and not D.static_legal(enc, s):
                    seen.add(k); uniq.append(s)
            if len(uniq) >= target:
                break
    sync(); ts = time.time() - t0
    r = c2(scor, root, uniq)
    return {**{k: r[k] for k in ("decision", "seq", "score", "p_noop", "n_scored", "select_s")}, "raw_draws": raw, "target": target,
            "underfilled": len(uniq) < target, "sample_s": round(ts, 5), "pool_hash": pool_hash(uniq)}


def c4(root, samp, scor, man, target):
    """C0-budgeted: the C0 ordered pool (top-4, all legal orders), deterministic subset of size `target`: within k = 1 / 2 / 3 ordered by
    sha256('CRC4|root|seq'), then round-robin over k; scored by X/Y with the production selector.  No score is looked at before selection."""
    D6 = EX.proposals(root, samp, man["config"]["proposal_seed"])
    byk = {1: [], 2: [], 3: []}
    for s, _ in EX.stream(D6, man["config"]["M"]):
        byk[len(s)].append([list(map(int, a)) for a in s])
    for k in byk:
        byk[k].sort(key=lambda s: D.stratum_hash(f"CRC4|{root.id}", seq_key(s)))
    sel, i = [], 0
    while len(sel) < target and any(i < len(v) for v in byk.values()):
        for k in (1, 2, 3):
            if i < len(byk[k]) and len(sel) < target:
                sel.append(byk[k][i])
        i += 1
    r = c2(scor, root, sel)
    return {**{k: r[k] for k in ("decision", "seq", "score", "p_noop", "n_scored", "select_s")}, "target": target, "available": sum(map(len, byk.values())),
            "by_k": [sum(len(s) == k for s in sel) for k in (1, 2, 3)]}


def capped_select(root, scor, seq_iter, t0, cap, chunk):
    """Score sequences from an iterator in chunks while elapsed < cap (a chunk started before the cap is finished); production selector over
    the fully scored candidates.  -> decision, number scored, completed flag."""
    sel = EX.Selectors([RULE])
    noop = scor.score(root, [[]])[0]["p11"]
    n, done, buf = 0, True, []
    it = iter(seq_iter)
    while True:
        if time.time() - t0 > cap:
            done = next(it, None) is None
            break
        buf = [tuple(tuple(a) for a in s) for s in itertools.islice(it, chunk)]
        if not buf:
            break
        sc = scor.score(root, [list(map(list, q)) for q in buf])
        p = np.array([x["p11"] for x in sc], float)
        sel.update(buf, p, np.array([len(q) for q in buf]), np.array([root.displacement(list(q)) for q in buf], float), np.zeros(len(buf)),
                   np.zeros(len(buf), int), {})
        n += len(buf)
    d = sel.finish(noop)[4][0]
    sync()
    return {"decision": "ABSTAIN" if d is None else "NOOP" if d["seq"] == [] else "REPAIR", "seq": None if d is None else d["seq"], "n_scored": n,
            "completed": done, "wall_s": round(time.time() - t0, 5)}


def timing(dom, public, ckpt, ids, outp, caps=(None,), repeats=3, main=256, L=64, dev=None):
    """Live CUDA-synchronized uncached timing of the natural pipelines (C0; CR pool of `main` draws + C1; same pool + C2) and wall-capped
    C0 / CR+XY, 1 warm-up + `repeats` repeats per root.  Timing replays draw `main` raw samples directly (not a 1,024 prefix)."""
    dev = dev or os.environ.get("CR_DEVICE", "cuda")
    m, _ = load_cr(ckpt, dev)
    samp, scor, man = BM.load_bundle(D.BUNDLE, dom, dev, 0)
    musd = D.scalers(dom)
    rows = [r for r in map(json.loads, open(public)) if r["domain"] == dom and r["root_id"] in ids]
    out = []
    for r in rows:
        root = S.Root(r, dom)
        rec = {"root_id": r["root_id"], "n_movable": len(root.movable), "natural": {}, "capped": {}}
        for rep in range(repeats + 1):
            sync(); t0 = time.time()
            x0 = c0(root, samp, scor, man)
            t_c0 = time.time() - t0
            sync(); t0 = time.time()
            b1 = enc_t(dom, r, dev, musd)
            P = make_pool(m, dom, r, b1, main, 0)
            seqs = prefix(P, main)[0]
            t_pool = time.time() - t0
            x1 = c1(m, root, b1, seqs, L, 0)
            t_c1 = time.time() - t0
            x2 = c2(scor, root, seqs)
            t_c2 = t_pool + x2["select_s"]
            if rep:
                for k, v in (("C0", t_c0), ("C1", t_c1), ("C2", t_c2), ("pool", t_pool)):
                    rec["natural"].setdefault(k, []).append(round(v, 5))
        rec.update({"C0_n_scored": x0["n_scored"], "C2_n_scored": x2["n_scored"], "C1_decoder_passes": x1["decoder_passes"]})
        for cap in caps:
            if cap is None:
                continue
            t0 = time.time()
            D6 = EX.proposals(root, samp, man["config"]["proposal_seed"])
            a = capped_select(root, scor, (s for s, _ in EX.stream(D6, man["config"]["M"])), t0, cap, 512)
            t0 = time.time()
            b1 = enc_t(dom, r, dev, musd)
            P = make_pool(m, dom, r, b1, main, 0)
            b = capped_select(root, scor, prefix(P, main)[0], t0, cap, 32)
            rec["capped"][str(cap)] = {"C0": {**a, "same_as_natural": a["seq"] == x0["seq"]}, "C2": {**b, "same_as_natural": b["seq"] == x2["seq"]}}
        out.append(rec)
    Path(outp).write_text(json.dumps({"dom": dom, "device": torch.cuda.get_device_name(0) if dev.startswith("cuda") else "cpu",
                                      "repeats": repeats, "main": main, "L": L, "rows": out}, indent=1))
    print(json.dumps({"out": str(outp), "n": len(out)}), flush=True)


def predict(dom, public, ckpt, outp, budgets=(64, 256, 1024), main=256, L=64, seed=0, do_c0=False, ids=None, dev=None, controls=False):
    dev = dev or os.environ.get("CR_DEVICE", "cuda")
    m, ck = load_cr(ckpt, dev)
    samp, scor, man = BM.load_bundle(D.BUNDLE, dom, dev, 0)
    musd = D.scalers(dom)
    rows = [r for r in map(json.loads, open(public)) if r["domain"] == dom and (ids is None or r["root_id"] in ids)]
    done = {json.loads(l)["root_id"] for l in open(outp)} if Path(outp).exists() else set()
    ck_sha = hashlib.sha256(Path(ckpt).read_bytes()).hexdigest()
    with open(outp, "a") as f:
        for r in rows:
            if r["root_id"] in done:
                continue
            root = S.Root(r, dom)
            b1 = enc_t(dom, r, dev, musd)
            P = make_pool(m, dom, r, b1, max(budgets), seed)
            pools = {b: prefix(P, b) for b in budgets}
            seqs, acct = pools[main]
            first = P["uniq"][P["traj"][0]] if P["traj"][0] >= 0 else None
            r1 = c1(m, root, b1, seqs, L, seed)
            r2 = c2(scor, root, seqs)
            rec = {"root_id": r["root_id"], "domain": dom, "seed": seed, "ckpt_sha256": ck_sha, "main_budget": main,
                   "pool_hash": {str(b): pool_hash(pools[b][0]) for b in budgets}, "pool_acct": {str(b): pools[b][1] for b in budgets},
                   "pool": seqs, "pool_bmax": P["uniq"], "pool_bmax_first_draw": P["first_draw"], "first_draw": first, "sample_s_bmax": P["sample_s"], "bmax": max(budgets),
                   "C1": r1, "C2": r2, "C2_pool_hash": pool_hash(seqs), "C1_common_gate": common_gate(r1, r2, seqs),
                   "n_movable": len(root.movable), "n_objects": len(root.ids), "teacher_calls": 0}
            if do_c0 == "props":
                rec["C0"] = c0_props(root, samp, man)
            elif do_c0:
                rec["C0"] = c0(root, samp, scor, man)
            if controls and do_c0:
                rec["C3"] = c3(m, dom, r, b1, root, scor, rec["C0"]["n_scored"], seed)
                rec["C4"] = c4(root, samp, scor, man, len(seqs))
            f.write(json.dumps(rec) + "\n"); f.flush()
    print(json.dumps({"out": str(outp), "n": sum(1 for _ in open(outp))}), flush=True)


def parity(dom, public, archived, ids_file, out, dev=None):
    """C0 through this package == archived frozen-bundle predictions (decision + sequence) on the given public roots."""
    dev = dev or os.environ.get("CR_DEVICE", "cuda")
    ids = json.loads(Path(ids_file).read_text())[dom]
    samp, scor, man = BM.load_bundle(D.BUNDLE, dom, dev, 0)
    arch = {r["root_id"]: r for r in map(json.loads, open(archived))}
    pub = {r["root_id"]: r for r in map(json.loads, open(public))}
    res = []
    for rid in ids:
        a = arch[rid]
        x = c0(S.Root(pub[rid], dom), samp, scor, man)
        aseq = [[mv["object_index"], mv["destination_cell"]] for mv in a["moves"]] if a["decision"] == "REPAIR" else ([] if a["decision"] == "NOOP" else None)
        res.append({"root_id": rid, "archived": [a["decision"], aseq, a.get("score_p11")], "now": [x["decision"], x["seq"], x["score"]],
                    "equal": a["decision"] == x["decision"] and aseq == x["seq"],
                    "score_abs_diff": None if x["score"] is None or a.get("score_p11") is None else abs(x["score"] - a["score_p11"]),
                    "proposals_equal": a.get("proposals") == x["proposals"]})
    rep = {"dom": dom, "n": len(res), "equal": sum(r["equal"] for r in res), "proposals_equal": sum(r["proposals_equal"] for r in res),
           "max_score_abs_diff": max([r["score_abs_diff"] for r in res if r["score_abs_diff"] is not None], default=0.0), "rows": res}
    Path(out).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}), flush=True)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["predict", "parity", "timing"]); ap.add_argument("dom"); ap.add_argument("args", nargs="+")
    ap.add_argument("--budgets", default="64,256,1024"); ap.add_argument("--main", type=int, default=256); ap.add_argument("--L", type=int, default=64)
    ap.add_argument("--c0", action="store_true"); ap.add_argument("--c0props", action="store_true"); ap.add_argument("--ids"); ap.add_argument("--controls", action="store_true")
    ap.add_argument("--caps", default="")
    A = ap.parse_args()
    if A.cmd == "predict":
        ids = set(json.loads(Path(A.ids).read_text())[A.dom]) if A.ids else None
        predict(A.dom, *A.args[:3], tuple(int(x) for x in A.budgets.split(",")), A.main, A.L, 0, "props" if A.c0props else A.c0, ids, controls=A.controls)
    elif A.cmd == "timing":
        ids = set(json.loads(Path(A.ids).read_text())[A.dom])
        timing(A.dom, A.args[0], A.args[1], ids, A.args[2], tuple(float(x) for x in A.caps.split(",") if x) or (None,), main=A.main, L=A.L)
    else:
        parity(A.dom, *A.args[:4])
