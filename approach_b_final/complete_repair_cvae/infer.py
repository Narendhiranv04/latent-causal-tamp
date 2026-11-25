#!/usr/bin/env python3
"""Planner-side inference (plan.md 5): public rows + frozen checkpoints in, one decision per root and arm out.  No labels, K, witnesses or
teacher are read here (allowlist: public rows {root_id, domain, inputs}, the bundle, the CR checkpoint).

  C0 / OURS    frozen bundle: exhaustive.proposals (S1 top-6, seed 0) -> top-4 -> all legal ordered K<=3 -> frozen X/Y -> production rule
  pool         CR-cVAE prior: BMAX raw trajectories from a root-derived RNG; budget b pool = unique legal sequences among the first b
               trajectories (nested prefixes of one stream), in first-appearance order; pool hash = sha256 of that ordered list
  C1 / CR-ONLY standalone: integrated decision head; REPAIR -> argmax approximate prior predictive log p(r | c) (L shared latents)
  C2 / CR+XY   the SAME pool (hash checked) scored once by the frozen X/Y; exhaustive.Selectors with the production rule

    python infer.py predict DOM PUBLIC.jsonl CKPT OUT.jsonl [--budgets 64,256,1024] [--main 256] [--L 64] [--c0] [--ids F]
    python infer.py parity  DOM PUBLIC.jsonl ARCHIVED_PRED.jsonl IDS.json OUT.json"""
from __future__ import annotations

import argparse, hashlib, json, math, os, sys, time
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


# ------------------------------------------------------------------------------------------------ CR pool, C1, C2
def make_pool(m, dom, row, b1, bmax, seed):
    """-> raw trajectory index per draw (-1 = no candidate), unique legal sequences (first-appearance order), timing."""
    gen = torch.Generator(device=b1["tok"].device).manual_seed(seed_of("CRPOOL", row["root_id"], seed))
    sync(); t0 = time.time()
    o, d, n = m.sample(b1, bmax, gen)
    sync(); t1 = time.time()
    o, d, n = o.cpu().numpy(), d.cpu().numpy(), n.cpu().numpy()
    enc = {k: v[0].cpu().numpy() for k, v in b1.items()}
    uniq, idx, first, bad = [], {}, [], 0
    for i in range(bmax):
        if n[i] == 0:
            first.append(-1); continue
        s = [[int(o[i, t]), int(d[i, t])] for t in range(n[i])]
        if D.static_legal(enc, s):
            bad += 1; first.append(-2); continue
        k = seq_key(s)
        if k not in idx:
            idx[k] = len(uniq); uniq.append(s)
        first.append(idx[k])
    return {"traj": first, "uniq": uniq, "illegal": bad, "sample_s": round(t1 - t0, 5)}


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


def predict(dom, public, ckpt, outp, budgets=(64, 256, 1024), main=256, L=64, seed=0, do_c0=False, ids=None, dev=None):
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
                   "pool": seqs, "first_draw": first, "sample_s_bmax": P["sample_s"], "bmax": max(budgets),
                   "C1": r1, "C2": r2, "C2_pool_hash": pool_hash(seqs), "C1_common_gate": common_gate(r1, r2, seqs),
                   "n_movable": len(root.movable), "n_objects": len(root.ids), "teacher_calls": 0}
            if do_c0:
                rec["C0"] = c0(root, samp, scor, man)
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
    ap.add_argument("cmd", choices=["predict", "parity"]); ap.add_argument("dom"); ap.add_argument("args", nargs="+")
    ap.add_argument("--budgets", default="64,256,1024"); ap.add_argument("--main", type=int, default=256); ap.add_argument("--L", type=int, default=64)
    ap.add_argument("--c0", action="store_true"); ap.add_argument("--ids")
    A = ap.parse_args()
    if A.cmd == "predict":
        ids = set(json.loads(Path(A.ids).read_text())[A.dom]) if A.ids else None
        predict(A.dom, *A.args[:3], tuple(int(x) for x in A.budgets.split(",")), A.main, A.L, 0, A.c0, ids)
    else:
        parity(A.dom, *A.args[:4])
