"""Contract tests for the complete-repair cVAE (plan.md 6 P1).  CPU only, small real TRAIN/VAL subsets + synthetic fixtures.
    python -m pytest tests -q"""
import copy, itertools, json, math, os, sys
from pathlib import Path

import numpy as np
import pytest
import torch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
os.environ.setdefault("CR_DEVICE", "cpu")
import data as D  # noqa: E402
from model import CRCVAE, param_counts  # noqa: E402
import contracts as CT  # noqa: E402

DEV = "cpu"


def first_rows(dom, split="train", per_k=8, snap=None):
    """First per_k rows of each legacy-K stratum (snapshots may be sorted by K)."""
    out, cnt = [], {}
    for line in open((snap or D.TRAIN_SNAP) / f"data{dom}.jsonl"):
        r = json.loads(line)
        if r["split"] == split and cnt.get(r["K_legacy"], 0) < per_k:
            cnt[r["K_legacy"]] = cnt.get(r["K_legacy"], 0) + 1
            out.append(r)
    return out


def tens(dom, rows):
    return {k: torch.as_tensor(v) for k, v in D.stack([D.encode(dom, r) for r in rows]).items()}


def one(b, i):
    return {k: v[i:i + 1] for k, v in b.items()}


@pytest.fixture(scope="module", params=["2d", "3d"])
def dom(request):
    return request.param


@pytest.fixture(scope="module")
def rows2():
    return {d: first_rows(d) for d in ("2d", "3d")}


def model(dom, seed=0):
    torch.manual_seed(seed)
    return CRCVAE(dom, 32, 4).eval()


# ------------------------------------------------------------------------------------------------ supervision
def test_orders_verified_dedup_and_weights(dom, rows2):
    for r in rows2[dom]:
        vo = D.verified_orders(r)
        Y = {CT.ekey(y["edit"]): y["y"] for y in r["labels"]["Y"]}
        X = {json.dumps(q["seq"]): q["x"] for q in r["labels"]["X"]}
        for k, os_ in vo.items():
            assert Y[k] == 1 and len(os_) == len(set(os_))
            assert all(X[o] == 1 for o in os_)                       # only verified X = 1 orders, never inferred permutations
            assert all(CT.ekey(json.loads(o)) == k for o in os_)
            assert not CT.v3_grammar(r["inputs"], json.loads(os_[0]))


def test_root_weights_sum_to_one(dom):
    rr, triples, labels = D.supervision(dom, D.VAL_SNAP, "val")
    s = {}
    for i, _, w in triples:
        s[i] = s.get(i, 0.0) + w
    assert s and max(abs(v - 1) for v in s.values()) < 1e-9
    assert len(labels) == len(rr)


def test_endpoint_join_by_key_not_index():
    r = {"inputs": {"attrs": [[0, 0, 0, 0]] * 3, "tid": 0, "cells0": [0, 1, 2], "legal_cells": list(range(10)), "goal_cell": 9},
         "labels": {"Y": [{"edit": [[2, 5], [1, 4]], "y": 1}, {"edit": [], "y": 0}, {"edit": [[1, 4]], "y": 0}],
                    "X": [{"seq": [[1, 4]], "x": 1, "kind": "k"}, {"seq": [[2, 5], [1, 4]], "x": 1, "kind": "k"}, {"seq": [[1, 4], [2, 5]], "x": 0, "kind": "k"}]},
         "K_legacy": "2"}
    vo = D.verified_orders(r)
    assert list(vo.values()) == [[json.dumps([[2, 5], [1, 4]])]]   # [[1,4]] alone has Y = 0; failed order [[1,4],[2,5]] excluded
    assert D.root_label(r, vo) == 1


def test_root_labels():
    base = {"inputs": None, "labels": {"X": [], "Y": [{"edit": [], "y": 0}]}}
    assert D.root_label({**base, "K_legacy": "NONE"}, {}) == 2
    assert D.root_label({**base, "K_legacy": "NONE"}, {"a": ["x"]}) == D.MASKED      # NONE contradicted by a verified repair
    assert D.root_label({**base, "K_legacy": "2"}, {}) == D.MASKED                   # legacy K without a finalized repair
    assert D.root_label({**base, "K_legacy": "0"}, {}) == D.MASKED                   # K0 with Y(empty) = 0
    assert D.root_label({"labels": {"X": [], "Y": [{"edit": [], "y": 1}]}, "K_legacy": "0"}, {}) == 0
    assert D.root_label({"labels": {"X": [], "Y": []}, "K_legacy": "1"}, {"a": ["x"]}) == D.MASKED   # Y(empty) missing


def test_public_inputs_only(dom, rows2):
    r = rows2[dom][0]
    pub = {"root_id": r["root_id"], "domain": dom, "inputs": r["inputs"]}
    a, b = D.encode(dom, r), D.encode(dom, pub)
    assert all(np.array_equal(a[k], b[k]) for k in a)


def test_movable_semantics(dom, rows2):
    for r in rows2[dom]:
        e = D.encode(dom, r)
        inp = r["inputs"]
        n = len(inp["ids"])
        assert not e["movable"][inp["tid"]] and not e["movable"][n:].any() and not e["tmask"][n:].any()
        fixed = [bool(a[3]) for a in inp["attrs"]] if dom == "2d" else [False] * n
        assert all(e["movable"][i] == (i != inp["tid"] and not fixed[i]) for i in range(n))
        legal = set(int(c) for c in inp["legal_cells"]) - set(int(c) for c in inp["cells0"]) - {int(inp["goal_cell"])}
        assert set(np.nonzero(e["legal0"])[0].tolist()) == legal


# ------------------------------------------------------------------------------------------------ decoder masks, STOP, normalization
def test_samples_static_legal_and_stop(dom, rows2):
    m = model(dom)
    b = tens(dom, rows2[dom][:6])
    for i in range(6):
        b1 = one(b, i)
        o, d, n = m.sample(b1, 256, torch.Generator().manual_seed(i))
        enc = {k: v[0].numpy() for k, v in b1.items()}
        has = enc["movable"].any() and enc["legal0"].any()
        assert ((n >= 1) == has).all() and (n <= 3).all()            # STOP never at t = 0; no candidate only when nothing is legal
        for j in range(256):
            if n[j]:
                assert D.static_legal(enc, [[int(o[j, t]), int(d[j, t])] for t in range(n[j])]) is None


def small_root(dom, rows2, nobj=2, ncell=3):
    b1 = one(tens(dom, rows2[dom][:1]), 0)
    b1 = {k: v.clone() for k, v in b1.items()}
    mv = torch.nonzero(b1["movable"][0]).squeeze(1)
    lg = torch.nonzero(b1["legal0"][0]).squeeze(1)
    assert len(mv) >= nobj and len(lg) >= ncell
    b1["movable"][:] = False; b1["movable"][0, mv[:nobj]] = True
    b1["legal0"][:] = False; b1["legal0"][0, lg[:ncell]] = True
    return b1, mv[:nobj].tolist(), lg[:ncell].tolist()


def all_seqs(objs, cells):
    out = []
    for k in (1, 2, 3):
        for os_ in itertools.permutations(objs, k):
            for ds in itertools.permutations(cells, k):
                out.append([[o, d] for o, d in zip(os_, ds)])
    return out


@pytest.mark.parametrize("nobj,ncell", [(2, 3), (3, 2), (3, 4), (1, 1)])
def test_exact_normalization_over_all_legal_sequences(dom, rows2, nobj, ncell):
    m = model(dom)
    b1, objs, cells = small_root(dom, rows2, nobj, ncell)
    seqs = all_seqs(objs, cells)
    z = torch.randn(1, m.zdim)
    o, d, n = (torch.as_tensor(a) for a in D.seq_arrays(seqs))
    B = len(seqs)
    c, T, Ce = m.encode(b1)
    with torch.no_grad():
        lp, _ = m.logp(c.expand(B, -1), T.expand(B, -1, -1), Ce.expand(B, -1, -1), b1["movable"].expand(B, -1), b1["legal0"].expand(B, -1),
                       z.expand(B, -1), o, d, n)
    assert abs(float(lp.exp().sum()) - 1.0) < 1e-5                    # STOP / forced STOP / masks define a proper distribution


def test_marginal_loglik_matches_manual(dom, rows2):
    m = model(dom)
    b1, objs, cells = small_root(dom, rows2, 2, 3)
    seqs = all_seqs(objs, cells)[:5]
    z = torch.randn(7, m.zdim)
    o, d, n = (torch.as_tensor(a) for a in D.seq_arrays(seqs))
    ll, passes = m.marginal_loglik(b1, o, d, n, z, chunk=4)
    c, T, Ce = m.encode(b1)
    man = []
    for u in range(len(seqs)):
        lp, _ = m.logp(c.expand(7, -1), T.expand(7, -1, -1), Ce.expand(7, -1, -1), b1["movable"].expand(7, -1), b1["legal0"].expand(7, -1), z,
                       o[u:u + 1].expand(7, -1), d[u:u + 1].expand(7, -1), n[u:u + 1].expand(7))
        man.append(float(lp.logsumexp(0) - math.log(7)))
    assert passes == 35 and np.allclose(ll.detach().numpy(), man, atol=1e-5)


def test_no_candidate_when_nothing_legal(dom, rows2):
    m = model(dom)
    b1 = {k: v.clone() for k, v in one(tens(dom, rows2[dom][:1]), 0).items()}
    b1["legal0"][:] = False
    o, d, n = m.sample(b1, 16, torch.Generator().manual_seed(0))
    assert (n == 0).all()


def test_posterior_not_used_at_inference(dom, rows2):
    m = model(dom)
    m.posterior = None                                                # any access would raise
    b1 = one(tens(dom, rows2[dom][:1]), 0)
    o, d, n = m.sample(b1, 8, torch.Generator().manual_seed(0))
    seqs = [[[int(o[j, t]), int(d[j, t])] for t in range(n[j])] for j in range(8) if n[j]]
    a = [torch.as_tensor(x) for x in D.seq_arrays(seqs)]
    ll, _ = m.marginal_loglik(b1, *a, torch.randn(4, m.zdim))
    assert torch.isfinite(ll).all()


# ------------------------------------------------------------------------------------------------ equivariance, determinism, gradients
def permute_row(r, perm):
    """Slot permutation of a snapshot row's learner inputs (new slot j holds old slot perm[j])."""
    r = copy.deepcopy(r)
    inp = r["inputs"]
    for k in ("ids", "xy0", "cells0", "attrs"):
        inp[k] = [inp[k][p] for p in perm]
    inp["tid"] = perm.index(inp["tid"])
    return r


def test_permutation_equivariance(dom, rows2):
    m = model(dom)
    r = next(x for x in rows2[dom] if len(x["inputs"]["ids"]) >= 4 and D.verified_orders(x))
    seq = json.loads(next(iter(D.verified_orders(r).values()))[0])
    n = len(r["inputs"]["ids"])
    perm = list(np.random.default_rng(3).permutation(n))
    inv = {old: new for new, old in enumerate(perm)}
    r2 = permute_row(r, perm)
    seq2 = [[inv[o], dd] for o, dd in seq]
    z = torch.randn(1, m.zdim)
    vals = []
    for rr, s in ((r, seq), (r2, seq2)):
        b1 = one(tens(dom, [rr]), 0)
        c, T, Ce = m.encode(b1)
        a = [torch.as_tensor(x) for x in D.seq_arrays([s])]
        lp, _ = m.logp(c, T, Ce, b1["movable"], b1["legal0"], z, *a)
        vals.append((float(lp), m.decision_logits(c).detach().numpy()))
    assert abs(vals[0][0] - vals[1][0]) < 1e-4 and np.allclose(vals[0][1], vals[1][1], atol=1e-5)


def test_sampling_deterministic(dom, rows2):
    m = model(dom)
    b1 = one(tens(dom, rows2[dom][:1]), 0)
    a = m.sample(b1, 64, torch.Generator().manual_seed(5))
    b = m.sample(b1, 64, torch.Generator().manual_seed(5))
    c = m.sample(b1, 64, torch.Generator().manual_seed(6))
    assert all(torch.equal(x, y) for x, y in zip(a, b)) and not all(torch.equal(x, y) for x, y in zip(a, c))


def test_gradients_reach_every_trained_module(dom, rows2):
    import train as TR
    rr = [r for r in rows2[dom] if D.verified_orders(r)][:8]
    m = CRCVAE(dom, 32, 4)
    b = tens(dom, rr)
    seqs = [json.loads(next(iter(D.verified_orders(r).values()))[0]) for r in rr]
    o, d, n = (torch.as_tensor(x) for x in D.seq_arrays(seqs))
    nll, parts, kl, _ = m.elbo_terms(b, o, d, n)
    c, _, _ = m.encode(b)
    loss = nll.mean() + kl.mean() + torch.nn.functional.cross_entropy(m.decision_logits(c), torch.ones(len(rr), dtype=torch.long))
    loss.backward()
    none = [k for k, p in m.named_parameters() if p.grad is None or not torch.isfinite(p.grad).all() or float(p.grad.abs().sum()) == 0]
    assert not none, none
    assert TR.KEYS and param_counts(m)["inference"] < param_counts(m)["total"]


# ------------------------------------------------------------------------------------------------ inference helpers
def test_pool_prefix_nesting_and_selector_parity():
    import infer as IF
    P = {"traj": [0, 1, 0, -1, 2, 1, 3, -2], "uniq": [[[1, 2]], [[1, 3]], [[2, 4], [1, 2]], [[3, 9]]]}
    s4, a4 = IF.prefix(P, 4)
    s8, a8 = IF.prefix(P, 8)
    assert s8[:len(s4)] == s4 and a4 == {"raw": 4, "no_candidate": 1, "illegal": 0, "unique": 2, "dup_draws": 1}
    assert a8["unique"] == 4 and a8["illegal"] == 1 and a8["dup_draws"] == 2
    assert IF.pool_hash(s4) != IF.pool_hash(s8) and IF.pool_hash(s4) == IF.pool_hash([list(map(list, q)) for q in s4])
    import exhaustive as EX, xy as XY
    rng = np.random.default_rng(0)
    seqs = [((1, 2),), ((1, 3),), ((2, 4), (1, 2)), ((3, 9),)]
    for _ in range(50):
        p = rng.uniform(0, 1, 4); pn = float(rng.uniform(0, 1))
        sel = EX.Selectors([IF.RULE])
        sel.update(seqs, p, np.array([len(s) for s in seqs]), np.zeros(4), np.zeros(4), np.zeros(4, int), {})
        got = sel.finish(pn)[4][0]
        rows = [{"admissible": True, "m": 0, "p": pn, "cd": 0.0, "J_hat": 0.0, "sig": "[]"}] + [
            {"admissible": True, "m": len(s), "p": float(p[i]), "cd": 0.0, "J_hat": 0.0, "sig": json.dumps([list(a) for a in s])} for i, s in enumerate(seqs)]
        k = XY.choose(rows, IF.RULE)
        want = None if k is None else json.loads(rows[k]["sig"])
        assert (None if got is None else got["seq"]) == want
