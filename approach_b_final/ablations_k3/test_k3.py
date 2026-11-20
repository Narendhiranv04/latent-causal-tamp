#!/usr/bin/env python3
"""P1 smoke / fairness tests on TRAIN roots (GPU env on gvlab2): python test_k3.py OUT.json
Uniform4 legality + determinism; TaskFlowMatch finite loss, task-context gradient, legal unique proposals; no-task zero branch; C1 = exactly one
candidate + no-op, label-blind, deterministic; G permutation invariance and DIRECT outputs on smoke-trained nets; resumable / idempotent predict."""
import hashlib, itertools, json, os, sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import arms as A  # noqa: E402
import benchmark as BM  # noqa: E402
import placement as PL  # noqa: E402
import run as RN  # noqa: E402
import search as S  # noqa: E402
import xy as XY  # noqa: E402

K3 = Path(os.environ["K3"])
T = {}


def train_rows(dom, n=12):
    rows = [json.loads(l) for l in open(A.ORIG / f"data{dom}.jsonl") if '"split": "train"' in l]
    rows = sorted(rows, key=lambda r: hashlib.sha256(("k3test|" + r["root_id"]).encode()).hexdigest())
    return [{"root_id": r["root_id"], "domain": dom, "inputs": r["inputs"]} for r in rows if r["K_legacy"] in ("2", "3")][:n]


for dom in ("2d", "3d"):
    rows = train_rows(dom)
    roots = [S.Root(r, dom) for r in rows]
    u = [A.propose_uniform4(rt, 4, 0) for rt in roots]
    T[f"{dom}_uniform4_legal_distinct"] = all(set(v) <= set(rt.legal_dests(rt.cells0)) and len(set(v)) == len(v) == min(4, len(rt.legal_dests(rt.cells0)))
                                             for rt, D in zip(roots, u) for v in D.values())
    T[f"{dom}_uniform4_deterministic"] = u == [A.propose_uniform4(rt, 4, 0) for rt in roots] and u != [A.propose_uniform4(rt, 4, 1) for rt in roots]
    samp, _, man = BM.load_bundle(RN.BUNDLE, dom, "cuda", 0)
    R, C = PL.GRID[dom]
    fm = A.TaskFlowMatch(R, C, PL.task_dim(dom)).cuda()
    torch.nn.init.normal_(fm.enc.task[-1].weight, std=0.1)          # untrained net: open the zero-initialized task branch for the gradient test
    obj, mask, occx, lg, _ = A.contexts(samp, roots[0], list(roots[0].movable))
    occx.requires_grad_(True)
    l, _ = fm.loss_w(obj, mask, occx, lg, torch.nonzero(lg)[:, 1][:len(obj)] if lg.sum() >= len(obj) else lg.float().argmax(1), None, torch.ones(len(obj), device="cuda"))
    l.backward()
    T[f"{dom}_taskfm_loss_finite"] = bool(torch.isfinite(l))
    T[f"{dom}_taskfm_task_context_gradient"] = float(occx.grad[:, fm.N:].abs().sum()) > 0
    D, info = A.propose_taskfm(samp, fm.eval(), roots[0], 4, 64, 0)
    leg = set(roots[0].legal_dests(roots[0].cells0))
    T[f"{dom}_taskfm_proposals_legal_unique"] = all(set(v) <= leg and len(set(v)) == len(v) == min(4, len(leg)) for v in D.values())
    T[f"{dom}_taskfm_evals_64x32"] = info["evals"] == 64 * 32 * len(roots[0].movable)
    T[f"{dom}_notask_features_zero"] = not PL.task_features(dom, rows[0]["inputs"], roots[0].cells0, roots[0].movable[0], False).any() and \
        PL.task_features(dom, rows[0]["inputs"], roots[0].cells0, roots[0].movable[0], True).any()
    T[f"{dom}_notask_variant_matched"] = {k: v for k, v in PL.VARIANTS["scratch_all_notask"].items() if k != "task"} == \
        {k: v for k, v in PL.VARIANTS["scratch_all"].items() if k != "task"} and PL.VARIANTS["scratch_all_notask"]["task"] is False
    scor = RN.SafeScorer(RN.BUNDLE / dom / "scorer_s0.pt", None, device="cuda")
    ok, det = True, True
    for rt in roots[:6]:
        D6 = {int(o): v[:4] for o, v in __import__("exhaustive").proposals(rt, samp, 0).items()}
        e0 = scor.evals
        d1 = RN.c1_decision(rt, D6, scor, 0)
        ok &= (scor.evals - e0) <= 1 and (d1[2] is None or len(d1[2]) in (1, 2, 3))
        det &= RN.c1_decision(rt, D6, scor, 0)[2] == d1[2]
    T[f"{dom}_c1_one_candidate_one_scorer_call"] = ok
    T[f"{dom}_c1_deterministic"] = det
    T[f"{dom}_c1_label_blind_public_rows"] = all(set(r) == {"root_id", "domain", "inputs"} for r in rows)

# G invariance / DIRECT outputs on smoke-trained nets (XY_SMOKE subset; never used as results)
os.environ["XY_SMOKE"] = "64"
for arm in ("G", "DIRECT"):
    out = K3 / "runs/p1_smoke" / arm
    XY.fit(A.EXP, "2D", arm, 0, epochs=2, out=out)
net = XY.load_model(K3 / "runs/p1_smoke/G/model.pt")
dnet = XY.load_model(K3 / "runs/p1_smoke/DIRECT/model.pt")
rows = train_rows("2d", 8)
inv, dok = True, True
for r in rows:
    rt = S.Root(r, "2d")
    mv = rt.movable[:3]
    leg = rt.legal_dests(rt.cells0)
    if len(mv) < 2 or len(leg) < 3:
        continue
    a = [(o, leg[i]) for i, o in enumerate(mv)]
    perms = [list(p) for p in itertools.permutations(a)]
    sg = S.Scorer.__new__(S.Scorer); sg.net, sg.dev, sg.cost, sg.evals = net, "cuda", None, 0
    p = [c["p11"] for c in sg.score(rt, perms)]
    inv &= max(p) - min(p) < 1e-5
    sd = RN.SafeScorer.__new__(RN.SafeScorer); sd.net, sd.dev, sd.cost, sd.evals = dnet, "cuda", None, 0
    c = sd.score(rt, [[]] + perms)
    dok &= all(0 <= x["p11"] <= 1 for x in c) and all(x["py"] != x["py"] for x in c[1:])
T["G_permutation_invariant_same_endpoint"] = inv
T["DIRECT_outputs_psucc_no_marginals"] = dok
# resumable / idempotent predict (3 public VAL roots, FULL_s0) -> no duplicate root rows
pub = K3 / "runs/public/public_val_3d.jsonl"
tmp = K3 / "runs/public/public_p1idem_3d.jsonl"
tmp.write_text("".join(open(pub).readlines()[:3]))
for _ in range(2):
    RN.predict("FULL_s0", "3d", "p1idem")
rr = BM.jl(K3 / "runs/predictions/FULL_s0/p1idem_3d.jsonl")
T["predict_resumable_idempotent"] = len(rr) == 3 == len({r["root_id"] for r in rr})
T = {k: bool(v) for k, v in T.items()}
Path(sys.argv[1]).write_text(json.dumps(T, indent=1, sort_keys=True) + "\n")
print(json.dumps(T, indent=1)); sys.exit(0 if all(T.values()) else 1)
