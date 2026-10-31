"""BXY-P11-TRAINING-PREREG: leakage-separated V2 training interface over the verified P-min sidecar, exact joint objective, preregistered
arms / training / selection / evaluation, design freezing. NO real-data training, tuning, teacher query or test evaluation happens here.

Three strictly separated per-root objects (build()):
  ScorerView  the ONLY model input: label-free scene tensors (am.Root of the record's `inputs`), every frozen P-min design query of the root
              (Y edit poses, ordered X actions, shared parent Y), the Y0 index and the canonical candidate list (sig, m, C_d, X / Y index,
              analytic F1 admissibility). Variables come from the outcome-free design, candidates are sorted by (m, signature) -- never by the
              outcome-guided historical catalogue order -- and carry no role, y_full, travel or failed_step.
  Labels      training targets only (consumed by the loss, never by coeffs): observed X / Y, success events for DIRECT, complete-witness travel.
  EvalView    evaluator-only oracle: candidate outcomes, negative kinds / phases, legacy roles, order groups, omission structure, strata.
Probability model (methodology §4.2, bxy_core): P(Y_s=1) = sigma(b_s/tau), P(X_q=1|Y=y) = sigma((a_q + w_q y)/tau), tau = 1,
p_succ(q) = sigma(b_s) sigma(a_q + w_q), p_succ(empty) = P(Y0=1); L = L_joint (root mean of the exact observed-data NLL) + lambda_J L_J,
L_J = sum_w Huber(log1p J_hat, log1p J_obs) / N_J over independently replayed complete witnesses (no-op: Y0 target travel)."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

import bxy_core as X
import bxy_data as bd
import bxy_f1 as F1
import bxy_pmin as PM
import bxy_teacher as T
import bxy_v2 as V
from abc_models import W, mlp

OUT = Path("runs/approach_b/bxy_p11_v1")
SIDECAR = PM.OUT / "BXY_SIDECAR_V2_PMIN.json"
EVIDENCE = {"BXY_SIDECAR_V2_PMIN.json": "0191f49bc165cf21b33246855f7e8a788a17fd74b187eb120d31548c4176cd7e",
            "PMIN_DESIGN.json": "8f164845e5804821b8fbf9411c52ca2584f22d6f6f4a0efd19b8c3bcb86ff658",
            "PMIN_LOCK.json": "4d42027e8c111e49557a68c9e128d0359918dd6032dcf8431fd051c044dfffaa"}
EXPECT = {"x": 2222, "y": 1866, "pairs": 2222, "j_complete": 1452, "j_noop": 142, "train": 176, "val": 21}
PHASE = "PMIN_DEV_MATCHED"
SCORER_KEYS = ("R", "cands", "key", "parent", "x_seqs", "y0", "y_poses")
CAND_KEYS = ("admissible", "cd", "m", "sig", "xi", "yi")
FORBIDDEN = ("role", "y_full", "travel", "failed_step", "witness", "negative_kind", "teacher_status", "J_", "label", "y_obs", "x_obs")
ARMS = {"XY-quadratic": {"kind": "xy", "coupled": True, "sa": False, "travel": True},
        "XY-quadratic-noJ": {"kind": "xy", "coupled": True, "sa": False, "travel": False},
        "XY-uncoupled": {"kind": "xy", "coupled": False, "sa": False, "travel": True},
        "XY-uncoupled-SA": {"kind": "xy", "coupled": False, "sa": True, "travel": True},
        "DIRECT": {"kind": "direct", "coupled": False, "sa": True, "travel": False}}
TRAIN = {"optimizer": "AdamW", "lr": 1e-3, "weight_decay": 1e-4, "clip_norm": 10.0, "batch_roots": 12, "max_updates": 3000, "eval_every": 20,
         "patience_evals": 15, "rel_tol": 1e-3, "torch_threads": 1, "dtype": "float64", "huber_delta": 1.0, "tau": 1.0}
SEEDS = (0, 1, 2)
LAMBDAS = (0.1, 0.3, 1.0)
RULE = {"noop_gate": 0.5, "eta": 0.0, "alpha": 0.1, "beta": 0.0, "gamma": 0.05}
SENSITIVITY = {"alpha": (0.0, 0.1, 0.3), "beta": (0.0, 0.1), "gamma": (0.0, 0.05, 0.2), "eta": (0.0, 0.5)}
FOLDS, ES_EVERY = 5, 8


# ------------------------------------------------------------------ evidence
def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def evidence() -> dict:
    """Immutable P-min evidence hashes and counts; raises on any difference (never repaired here)."""
    bad = [f"{f}: {sha(PM.OUT / f)} != {h}" for f, h in EVIDENCE.items() if sha(PM.OUT / f) != h]
    sc = json.loads(SIDECAR.read_text())
    O = V.observations(sc)
    n = {"x": len(sc["x_queries"]), "y": len(sc["y_queries"]), "pairs": len(sc["paired"]),
         "j_complete": sum(len([j for j in o["j"] if j[0]]) for o in O.values()), "j_noop": sum(len([j for j in o["j"] if not j[0]]) for o in O.values())}
    D, R = json.loads((PM.OUT / "PMIN_DESIGN.json").read_text()), bd.roots()
    for s in ("train", "val"):
        n[s] = sum(bd.split_of(R[k]) == s for k in D["root_order"])
    bad += [f"count {k}: {n[k]} != {v}" for k, v in EXPECT.items() if n[k] != v]
    if bad:
        raise RuntimeError("; ".join(bad))
    return {"hashes": EVIDENCE, "counts": n}


def inputs(records=V.RECORDS) -> dict:
    return {r["audit"]["root"]: {"inputs": r["inputs"], "ids": r["audit"]["ids"], "split": r["audit"]["split"]}
            for r in torch.load(records, weights_only=False)["roots"]}


def load() -> tuple:
    return V.load(SIDECAR), json.loads((PM.OUT / "PMIN_DESIGN.json").read_text()), bd.roots(), inputs()


# ------------------------------------------------------------------ the three separated views
def _sig(key) -> str:
    return key.split(":", 3)[3]


def cd_cells(rec, seq) -> float:
    c0 = bd.cells0(rec)
    return float(sum(np.hypot(d % 8 - c0[o] % 8, d // 8 - c0[o] // 8) for o, d in seq))


def build(splits=("train", "val"), sc=None, D=None, R=None, I=None) -> list:
    """[(ScorerView, Labels, EvalView)] for every P-min root in `splits` (train / val only; a test root raises)."""
    import abc_models as am
    from scene import scene_from_dict
    if not set(splits) <= {"train", "val"}:
        raise ValueError(f"only train / val views exist in P11, got {splits}")
    if sc is None or D is None or R is None or I is None:
        sc, D, R, I = (a if a is not None else b for a, b in zip((sc, D, R, I), load()))
    O = V.observations(sc)
    bad = V.check_identity(sc, R)
    if bad:
        raise ValueError(f"identity: {bad[:3]}")
    xrow = {r["x_key"]: r for r in sc["x_queries"]}
    yrow = {r["y_key"]: r for r in sc["y_queries"]}
    out = []
    for k in D["root_order"]:
        rec, d, inp = R[k], D["roots"][k], I[k]
        split = bd.split_of(rec)
        if split == "test" or d["split"] == "test" or inp["split"] != split:
            raise RuntimeError(f"split violation {k}: {split} / {d['split']} / {inp['split']}")
        if split not in splits:
            continue
        ids, lat = inp["ids"], scene_from_dict(rec["scene"]).lattice
        Q = {key: q for key, q in d["queries"].items() if PHASE in q["phases"]}
        xk = sorted(key for key, q in Q.items() if q["side"] == "x")
        y0 = T.ykey(k, rec, [])
        edits = {key: q["edit"] for key, q in Q.items() if q["side"] == "y"}
        for q in xk:                                                       # shared Y: every order with this endpoint maps to one Y node
            e = bd.endpoint(rec, [tuple(a) for a in Q[q]["seq"]])
            if edits.setdefault(Q[q]["parent_y_key"], e) != e:
                raise RuntimeError(f"{k}: {q} parent edit differs from its endpoint")
        yk = sorted(edits)
        xi, yi = {q: i for i, q in enumerate(xk)}, {q: i for i, q in enumerate(yk)}
        enc = lambda seq: [(ids.index(o), tuple(lat.center(int(c)))) for o, c in seq]  # noqa: E731
        cat = {}
        for c in bd.catalogue(rec):
            seq = [(o, int(dd)) for o, dd in c["seq"]]
            s = bd.sig(seq)
            ok = not seq or F1.screen(rec, seq)["complete_ok"]                      # analytic F1 (x_ok, y_ok, no GOAL_BLOCKED)
            if ok and seq and (T.xkey(k, rec, seq) not in xi or T.ykey(k, rec, seq) not in yi):
                raise RuntimeError(f"{k}: admissible candidate {s} outside the frozen design")
            cat.setdefault(s, {"sig": s, "m": len(seq), "cd": cd_cells(rec, seq), "xi": xi[T.xkey(k, rec, seq)] if ok and seq else None,
                               "yi": yi[T.ykey(k, rec, seq)] if ok else None, "admissible": bool(ok)})
        cands = sorted(cat.values(), key=lambda c: (c["m"], c["sig"]))
        sv = {"key": k, "R": am.Root({"inputs": inp["inputs"]}), "y_poses": [{ids.index(o): tuple(lat.center(int(c))) for o, c in sorted(edits[q].items())} for q in yk],
              "x_seqs": [enc(Q[q]["seq"]) for q in xk], "parent": [yi[Q[q]["parent_y_key"]] for q in xk], "y0": yi[y0], "cands": cands}
        o = O.get(k, {"x": {}, "y": {}})
        ox = {xi[q]: v["y"] for q, v in o["x"].items()}
        oy = {yi[q]: v["y"] for q, v in o["y"].items()}
        if set(o["x"]) - set(xi) or set(o["y"]) - set(yi):
            raise RuntimeError(f"{k}: observation outside the frozen design")
        lab = {"key": k, "obs_x": ox, "obs_y": oy, "succ": success_events(ox, oy, sv["parent"], sv["y0"]), "j": travel_items(k, xk, yk, xrow, yrow, sc)}
        ev = evaluator(k, rec, d, sv, ox, oy, xk, yk, xrow, yrow, split)
        out.append((sv, lab, ev))
    return out


def success_events(ox, oy, parent, y0) -> dict:
    """DIRECT targets: {xi: x AND y} where decided (an observed 0 on either side decides 0), plus {None: Y0}."""
    s = {}
    for q, p in enumerate(parent):
        x, y = ox.get(q), oy.get(p)
        if x == 0 or y == 0:
            s[q] = 0
        elif x == 1 and y == 1:
            s[q] = 1
    if y0 in oy:
        s[None] = oy[y0]
    return s


def travel_items(k, xk, yk, xrow, yrow, sc) -> list:
    """[(xi | None, yi, J)]: J_total of a full-joint-success pair whose X and Y were both independently replayed (J_total = stitched
    prefix incl. connector + target), and the replayed Y0 target travel of the zero-move repair. Nothing else is ever a travel label."""
    xi, yi, out = {q: i for i, q in enumerate(xk)}, {q: i for i, q in enumerate(yk)}, []
    for p in sc["paired"]:
        if p["root"] != k or p.get("full_joint_success") != 1:
            continue
        x, y = xrow[p["x_key"]], yrow[p["y_key"]]
        ok = p.get("matched_protocol") and x.get("independent_replay") is True and y.get("independent_replay") is True and \
            x["verification"].get("witness") and y["verification"].get("witness")
        if not ok or abs(p["J_total"] - (x["travel_parts"]["J_prefix_stitched"] + y["J_target"])) > 1e-9:
            raise RuntimeError(f"unverifiable complete witness {p['x_key']}")
        out.append((xi[p["x_key"]], yi[p["y_key"]], float(p["J_total"])))
    for key, r in yrow.items():
        if r["root"] == k and not r["hypothetical_poses"] and r["y"] == 1:
            if r.get("independent_replay") is not True or r.get("J_target") is None:
                raise RuntimeError(f"unverifiable Y0 witness {key}")
            out.append((None, yi[key], float(r["J_target"])))
    return sorted(out, key=lambda t: (t[0] is not None, t[0] or 0, t[1]))


def evaluator(k, rec, d, sv, ox, oy, xk, yk, xrow, yrow, split) -> dict:
    roles = {}
    for c in bd.catalogue(rec):
        roles.setdefault(bd.sig([(o, int(dd)) for o, dd in c["seq"]]), []).append({"role": c["role"], "legacy_y_full": c["y_full"], "legacy_travel": c["travel"]})
    meta = lambda r: {"status": r["teacher_status"], "negative_kind": r["negative_kind"], "phase": r["failed_phase"], "detail": r.get("detail")}  # noqa: E731
    cands = []
    for c in sv["cands"]:
        if not c["admissible"]:
            out = None
        elif c["m"] == 0:
            out = oy.get(sv["y0"])
        else:
            x, y = ox.get(c["xi"]), oy.get(c["yi"])
            out = 0 if 0 in (x, y) else 1 if (x, y) == (1, 1) else None
        cands.append({"sig": c["sig"], "success": out, "x": ox.get(c["xi"]) if c["xi"] is not None else None, "y": oy.get(c["yi"]) if c["yi"] is not None else None,
                      "legacy": roles.get(c["sig"], [])})
    groups = {}
    for q, key in enumerate(xk):
        if len(xrow[key]["ordered_actions"]) >= 2:
            groups.setdefault(sv["parent"][q], []).append(q)
    order = [{"y": p, "members": [{"xi": q, "x": ox[q], **meta(xrow[xk[q]])} for q in g]} for p, g in sorted(groups.items()) if len(g) >= 2]
    omi = []
    xi, yi = {q: i for i, q in enumerate(xk)}, {q: i for i, q in enumerate(yk)}
    for c in sv["cands"]:
        if c["admissible"] and c["m"] >= 2:
            seq = [(a.split(">")[0], int(a.split(">")[1])) for a in c["sig"].split(".")]
            oms = [[a for i, a in enumerate(seq) if i != t] for t in range(len(seq))]
            omi.append({"sig": c["sig"], "xi": c["xi"], "yi": c["yi"], "omit": [{"xi": xi.get(T.xkey(k, rec, om)), "yi": yi.get(T.ykey(k, rec, om))} for om in oms]})
    return {"key": k, "split": split, "family": rec["ids"]["parent_family_id"], "stratum": d["stratum"], "verified_K": rec["verified_K"],
            "y0": oy.get(sv["y0"]), "cands": cands, "parent": list(sv["parent"]), "order_groups": order, "omissions": omi,
            "obs_x": dict(ox), "obs_y": dict(oy), "x_meta": {q: meta(xrow[key]) for q, key in enumerate(xk)}, "y_meta": {s: meta(yrow[key]) for s, key in enumerate(yk) if key in yrow},
            "x_keys": xk, "y_keys": yk}


def check_scorer(sv) -> None:
    """The model-facing whitelist: exact key sets and no forbidden field name anywhere (raises)."""
    if tuple(sorted(sv)) != SCORER_KEYS or any(tuple(sorted(c)) != CAND_KEYS for c in sv["cands"]):
        raise KeyError(f"scorer view keys {sorted(sv)}")
    text = json.dumps({k: v for k, v in sv.items() if k != "R"}, default=str)
    hit = [f for f in FORBIDDEN if f in text]
    if hit:
        raise KeyError(f"forbidden field in scorer view: {hit}")


# ------------------------------------------------------------------ model (shared LB modules; one extra head per arm, see ARMS)
class Model(V.ModelXY2):
    """XY arms: b_s = F3 scene unary, a_q = F2 prefix unary (+ xs(g_q, v_s, c) for the scene-aware uncoupled control), w_q = xy(g_q, v_s, c)
    (coupled) else 0, J(q) = jt(v_s, c) + softplus(cost(g_q)), J(empty) = jt(v_0, c). DIRECT: success logit d_q = a_q (with xs), d_empty = b_0."""

    def __init__(self, arm):
        cfg = ARMS[arm]
        super().__init__(coupled=cfg["coupled"])
        self.arm, self.family = arm, cfg["kind"]
        if cfg["sa"]:
            self.xs = mlp(3 * W, 1)

    def coeffs(self, sv) -> dict:
        check_scorer(sv)
        R, z = sv["R"], torch.zeros((), dtype=X.D)
        self._memo = {}
        try:
            c = self.ctxn(R.ctx)
            v = [self.memo(("v", tuple(sorted(p.items()))), lambda p=p: self.scene_vec(R, self.edited(R, p))) for p in sv["y_poses"]]
            b = torch.stack([self.scene(torch.cat([x, c]))[0] for x in v])
            a, w, J = [], [], []
            for seq, s in zip(sv["x_seqs"], sv["parent"]):
                sq, g, _ = self.order(R, seq)
                h = torch.cat([g, v[s], c])
                a.append(sq + (self.xs(h)[0] if hasattr(self, "xs") else z))
                w.append(self.xy(h)[0] if self.coupled else z)
                J.append(self.j_hat(g, v[s], c))
            J0 = self.j_hat(None, v[sv["y0"]], c)
        finally:
            self._memo = None
        e = torch.zeros(0, dtype=X.D)
        return {"b": b, "a": torch.stack(a) if a else e, "w": torch.stack(w) if w else e, "J": torch.stack(J) if J else e, "J0": J0}


def build_model(arm, seed=None) -> Model:
    if seed is not None:
        torch.manual_seed(seed)
    return Model(arm).double()


def params(m) -> int:
    return sum(p.numel() for p in m.parameters())


# ------------------------------------------------------------------ exact objective
def log_evidence(b, a, w, parent, obs_x, obs_y, tau=X.TAU):
    """Vectorized bxy_core.log_evidence: per unique scene, logsumexp over allowed y of log P^Y(y) + sum of observed children log P^X(x|y)."""
    S = len(b)
    q = torch.tensor(sorted(obs_x), dtype=torch.long)
    cols = []
    for y in (0.0, 1.0):
        col = X.log_py(b, y, tau)
        if len(q):
            xv = torch.tensor([float(obs_x[i]) for i in q.tolist()], dtype=X.D)
            col = col.index_add(0, torch.tensor([parent[i] for i in q.tolist()], dtype=torch.long), X.log_px(a[q], w[q], xv, y, tau))
        cols.append(col)
    L = torch.stack(cols, 1)
    if obs_y:
        s = torch.tensor(sorted(obs_y), dtype=torch.long)
        mask = torch.zeros(S, 2, dtype=X.D)
        mask[s, torch.tensor([1 - obs_y[i] for i in s.tolist()])] = float("-inf")
        L = L + mask
    return torch.logsumexp(L, 1).sum()


def root_terms(m, sv, lab, tau=X.TAU) -> tuple:
    """(root NLL, J_pred [n], J_obs [n]) -- the NLL is the exact joint observed-data NLL (XY) or the success-event BCE sum (DIRECT)."""
    C = m.coeffs(sv)
    if m.family == "xy":
        nll = -log_evidence(C["b"], C["a"], C["w"], sv["parent"], lab["obs_x"], lab["obs_y"], tau)
    else:
        lg = torch.stack([C["b"][sv["y0"]] if q is None else C["a"][q] for q in lab["succ"]]) if lab["succ"] else torch.zeros(0, dtype=X.D)
        nll = F.binary_cross_entropy_with_logits(lg, torch.tensor([float(v) for v in lab["succ"].values()], dtype=X.D), reduction="sum")
    jp = torch.stack([C["J0"] if i is None else C["J"][i] for i, _, _ in lab["j"]]) if lab["j"] else torch.zeros(0, dtype=X.D)
    return nll, jp, torch.tensor([j for *_, j in lab["j"]], dtype=X.D)


def batch_loss(m, svs, labs, lam, tau=X.TAU) -> tuple:
    """L = mean_roots NLL + lam * (sum_w Huber(log1p J_hat, log1p J) / N_J) over the batch's complete witnesses (methodology §6.2)."""
    t = [root_terms(m, s, l, tau) for s, l in zip(svs, labs)]
    nll = torch.stack([x[0] for x in t]).mean()
    jp, jo = torch.cat([x[1] for x in t]), torch.cat([x[2] for x in t])
    tr = F.huber_loss(torch.log1p(jp), torch.log1p(jo), reduction="sum", delta=TRAIN["huber_delta"]) / len(jp) if len(jp) else None
    tot = nll + lam * tr if (lam and tr is not None) else nll
    return tot, {"nll": float(nll.detach()), "travel": None if tr is None else float(tr.detach())}


def fit(arm, seed, tr, es, lam, cfg=TRAIN, log=None) -> tuple:
    """The preregistered trainer (validated on synthetic roots only in P11). tr / es: [(sv, lab)]; early stopping on es mean root NLL."""
    torch.set_num_threads(cfg["torch_threads"])
    m = build_model(arm, seed)
    np.random.seed(seed)
    opt = torch.optim.AdamW(m.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    rng, n = np.random.default_rng(seed), len(tr)
    best, stale, hist = (float("inf"), copy.deepcopy(m.state_dict()), 0), 0, []
    for u in range(cfg["max_updates"]):
        idx = sorted(rng.choice(n, size=min(cfg["batch_roots"], n), replace=False).tolist())
        opt.zero_grad()
        tot, rec = batch_loss(m, [tr[i][0] for i in idx], [tr[i][1] for i in idx], lam)
        if not torch.isfinite(tot):
            hist.append({"update": u, "nonfinite": True})
            break
        tot.backward()
        rec |= {"update": u, "total": float(tot.detach()), "grad_pre": float(torch.nn.utils.clip_grad_norm_(m.parameters(), cfg["clip_norm"]))}
        opt.step()
        if (u + 1) % cfg["eval_every"] == 0:
            with torch.no_grad():
                rec["es_nll"] = float(np.mean([float(root_terms(m, s, l)[0]) for s, l in es]))
            if rec["es_nll"] < best[0] * (1 - cfg["rel_tol"]) if np.isfinite(best[0]) else True:
                best, stale = (rec["es_nll"], copy.deepcopy(m.state_dict()), u + 1), 0
            else:
                stale += 1
        hist.append(rec)
        if log:
            log(rec)
        if stale >= cfg["patience_evals"]:
            break
    m.load_state_dict(best[1])
    return m.eval(), {"best_update": best[2], "es_nll": best[0], "updates_run": len(hist), "stopped_early": stale >= cfg["patience_evals"],
                      "params": params(m), "lambda_J": lam, "history": hist}


# ------------------------------------------------------------------ prediction and the frozen selection rule (no label is read)
def predict(m, sv) -> list:
    return predict_all(m, sv)["cands"]


@torch.no_grad()
def predict_all(m, sv) -> dict:
    """{"cands": canonical candidate rows with p (p_succ; no-op P(Y0)), J_hat and, for XY arms, px / py / w; "vars": per-variable
    psucc / px / py / w over every X / Y variable of the root (order and omission metrics need non-catalogue queries)}."""
    C = m.coeffs(sv)
    if m.family == "xy":
        mg = X.marginals(C["b"], C["a"], C["w"], sv["parent"])
        py = mg["py"]
        var = {"psucc": mg["psucc"].tolist(), "px": mg["px"].tolist(), "py": py.tolist(), "w": C["w"].tolist()}
    else:
        var = {"psucc": torch.sigmoid(C["a"]).tolist(), "px": None, "py": None, "w": None}
    rows = []
    for c in sv["cands"]:
        r = dict(c)
        if c["admissible"]:
            if m.family == "direct":
                r["p"] = float(torch.sigmoid(C["b"][sv["y0"]] if c["m"] == 0 else C["a"][c["xi"]]))
            else:
                r |= {"p": float(py[sv["y0"]]) if c["m"] == 0 else float(mg["psucc"][c["xi"]]), "py": float(py[c["yi"] if c["m"] else sv["y0"]]),
                      "px": 1.0 if c["m"] == 0 else float(mg["px"][c["xi"]]), "w": None if c["m"] == 0 else float(C["w"][c["xi"]])}
            r["J_hat"] = float(C["J0"] if c["m"] == 0 else C["J"][c["xi"]])
        rows.append(r)
    return {"cands": rows, "vars": var}


def choose(rows, rule=RULE):
    """F1 first; no-op gate (P(Y0) >= gate -> no-op); admit p >= eta (none -> abstain = None); argmin -log p + alpha m + beta C_d + gamma J_hat;
    ties by (m, C_d, signature). Candidate list order never matters."""
    adm = [i for i, r in enumerate(rows) if r["admissible"]]
    e = next(i for i in adm if rows[i]["m"] == 0)
    if rule.get("noop_gate") is not None and rows[e]["p"] >= rule["noop_gate"]:
        return e
    pool = [i for i in adm if rows[i]["p"] >= rule["eta"]]
    if not pool:
        return None
    cost = lambda r: -np.log(max(r["p"], 1e-12)) + rule["alpha"] * r["m"] + rule["beta"] * r["cd"] + rule["gamma"] * (r.get("J_hat") or 0.0)  # noqa: E731
    return min(pool, key=lambda i: (round(cost(rows[i]), 12), rows[i]["m"], rows[i]["cd"], rows[i]["sig"]))


REFERENCES = {"NOOP": lambda rows: next(i for i, r in enumerate(rows) if r["m"] == 0),
              "SHORTEST_ADMISSIBLE": lambda rows: min((i for i, r in enumerate(rows) if r["admissible"] and r["m"] > 0), default=None,
                                                      key=lambda i: (rows[i]["m"], rows[i]["cd"], rows[i]["sig"])),
              "DISPLACEMENT_RANK": lambda rows: min((i for i, r in enumerate(rows) if r["admissible"] and r["m"] > 0), default=None,
                                                    key=lambda i: (rows[i]["cd"], rows[i]["m"], rows[i]["sig"]))}


def verify_first(ev, sv) -> dict:
    """Oracle reference: verify admissible candidates in (m, C_d, sig) order until one succeeds; cost = number of verifications."""
    order = sorted((i for i, c in enumerate(sv["cands"]) if c["admissible"]), key=lambda i: (sv["cands"][i]["m"], sv["cands"][i]["cd"], sv["cands"][i]["sig"]))
    hit = next((n for n, i in enumerate(order) if ev["cands"][i]["success"] == 1), None)
    return {"success": int(hit is not None), "verifications": hit + 1 if hit is not None else len(order), "chosen": order[hit] if hit is not None else None}


# ------------------------------------------------------------------ preregistered metrics (root-grouped)
def selection_row(rows, ev, i, travel) -> dict:
    """travel: {sig: witnessed J_total} of the root's successful complete candidates (evaluator side)."""
    c = ev["cands"][i] if i is not None else None
    ok = [j for j, x in enumerate(ev["cands"]) if x["success"] == 1]
    s = int(c is not None and c["success"] == 1)
    return {"root": ev["key"], "stratum": ev["stratum"], "initially_feasible": ev["y0"], "chosen": i, "abstain": i is None, "success": s,
            "unverified": int(c is not None and c["success"] is None), "available": int(bool(ok)), "m": rows[i]["m"] if i is not None else None,
            "cd": rows[i]["cd"] if i is not None else None, "J": travel.get(rows[i]["sig"]) if s else None,
            "optimal": int(s and rows[i]["m"] == min(rows[j]["m"] for j in ok)), "false_repair": int(ev["y0"] == 1 and i is not None and rows[i]["m"] > 0)}


def selection_summary(sel) -> dict:
    f = lambda rs, k: float(np.mean([r[k] for r in rs])) if rs else None  # noqa: E731
    inf = [r for r in sel if r["initially_feasible"] == 0]
    fea = [r for r in sel if r["initially_feasible"] == 1]
    ok = [r for r in sel if r["success"]]
    return {"roots": len(sel), "infeasible_roots": len(inf), "success_infeasible": f(inf, "success"), "success": f(sel, "success"),
            "false_repair_on_feasible": f(fea, "false_repair"), "abstain": f(sel, "abstain"), "available_infeasible": f(inf, "available"),
            "optimal": f(sel, "optimal"), "unverified": f(sel, "unverified"), "mean_m_success": f(ok, "m"), "mean_cd_success": f(ok, "cd"),
            "mean_J_success": float(np.mean([r["J"] for r in ok if r["J"] is not None])) if any(r["J"] is not None for r in ok) else None}


def prob_metrics(items) -> dict:
    """items: [(root, y, p)] -> root-averaged and pooled log loss / Brier, ECE (10 equal-width bins, pooled), counts."""
    if not items:
        return {"n": 0}
    by = {}
    for k, y, p in items:
        by.setdefault(k, []).append((y, min(max(p, 1e-12), 1 - 1e-12)))
    ll = lambda v: -np.mean([y * np.log(p) + (1 - y) * np.log(1 - p) for y, p in v])  # noqa: E731
    br = lambda v: np.mean([(p - y) ** 2 for y, p in v])  # noqa: E731
    y, p = np.array([i[1] for i in items], float), np.array([i[2] for i in items], float)
    bins = np.minimum((p * 10).astype(int), 9)
    return {"n": len(items), "roots": len(by), "logloss_root": float(np.mean([ll(v) for v in by.values()])), "brier_root": float(np.mean([br(v) for v in by.values()])),
            "logloss_pooled": float(ll(list(zip(y, np.clip(p, 1e-12, 1 - 1e-12))))), "brier_pooled": float(np.mean((p - y) ** 2)),
            "ece10": float(sum(abs(p[bins == b].mean() - y[bins == b].mean()) * (bins == b).mean() for b in range(10) if (bins == b).any())),
            "base_rate": float(y.mean())}


def per_root(items, kind="logloss") -> dict:
    by = {}
    for k, y, p in items:
        p = min(max(p, 1e-12), 1 - 1e-12)
        by.setdefault(k, []).append(-(y * np.log(p) + (1 - y) * np.log(1 - p)) if kind == "logloss" else (p - y) ** 2)
    return {k: float(np.mean(v)) for k, v in by.items()}


def cluster_boot(a: dict, b: dict, B=10000, seed=0) -> dict:
    """Paired root-cluster bootstrap of mean(a - b) over the roots both define."""
    ks = sorted(set(a) & set(b))
    d = np.array([a[k] - b[k] for k in ks])
    rng = np.random.default_rng(seed)
    bs = d[rng.integers(0, len(d), (B, len(d)))].mean(1) if len(d) else np.zeros(1)
    return {"roots": len(ks), "diff": float(d.mean()) if len(d) else None, "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]}


def order_metric(preds, evs, use="psucc") -> dict:
    """Same-endpoint different-order X pairs with discordant X: does the arm rank the executable order higher? Split by whether the failing
    order carries a certified relocation failure (sound geometry) or a planner / connector budget failure (teacher-policy dependent)."""
    out = {"certified": [], "budget_policy": []}
    for pr, ev in zip(preds, evs):                                       # preds: predict_all outputs; use: "psucc" or "px"
        px = dict(enumerate(pr["vars"][use] or []))
        for g in ev["order_groups"]:
            for i, u in enumerate(g["members"]):
                for v in g["members"][i + 1:]:
                    if u["x"] == v["x"] or u["xi"] not in px or v["xi"] not in px:
                        continue
                    pos, neg = (u, v) if u["x"] == 1 else (v, u)
                    s = 1.0 if px[pos["xi"]] > px[neg["xi"]] else 0.5 if px[pos["xi"]] == px[neg["xi"]] else 0.0
                    out["certified" if neg["negative_kind"] == "CERTIFIED" else "budget_policy"].append((ev["key"], s))
    return {k: {"pairs": len(v), "roots": len({r for r, _ in v}), "concordance": float(np.mean([s for _, s in v])) if v else None} for k, v in out.items()}


def omission_metric(preds, evs) -> dict:
    """Full multi-move candidate vs each single-action omission (recomputed from S0): for every decided pair whose labels differ, does the
    predicted change have the observed sign? X via P(X) (XY) / p_succ (DIRECT), Y via P(Y) (unique endpoint pairs), success via p_succ."""
    out = {"x": [], "y": [], "success": []}
    for pr, ev in zip(preds, evs):
        v, seen = pr["vars"], set()
        pxv = v["px"] or v["psucc"]
        for o in ev["omissions"]:
            for t in o["omit"]:
                pairs = [("x", o["xi"], t["xi"], ev["obs_x"], pxv)]
                if v["py"] is not None and (o["yi"], t["yi"]) not in seen:
                    seen.add((o["yi"], t["yi"]))
                    pairs.append(("y", o["yi"], t["yi"], ev["obs_y"], v["py"]))
                sf = lambda q: None if q is None else (0 if 0 in (ev["obs_x"].get(q), ev["obs_y"].get(ev["parent"][q])) else  # noqa: E731
                                                       1 if (ev["obs_x"].get(q), ev["obs_y"].get(ev["parent"][q])) == (1, 1) else None)
                pairs.append(("success", o["xi"], t["xi"], {q: sf(q) for q in (o["xi"], t["xi"]) if q is not None and sf(q) is not None}, v["psucc"]))
                for side, f, om, lab, pp in pairs:
                    if f is None or om is None or lab.get(f) is None or lab.get(om) is None or lab[f] == lab[om]:
                        continue
                    d = (pp[f] - pp[om]) * (lab[f] - lab[om])
                    out[side].append((ev["key"], f"{lab[f]}->{lab[om]}", 1.0 if d > 0 else 0.5 if d == 0 else 0.0))
    return {k: {"pairs": len(v), "roots": len({r for r, _, _ in v}), "by_transition": {t: sum(1 for _, x, _ in v if x == t) for t in ("1->0", "0->1")},
                "sign_agreement": float(np.mean([s for *_, s in v])) if v else None} for k, v in out.items()}


def verdict(ll_unc, ll_sa, sel_unc, sel_sa, seeds_ok, margin=0.05) -> str:
    """Coupling decision from paired cluster-bootstrap results (quadratic - control). ll_*: success log loss (lower is better), sel_*: success on
    initially infeasible roots. BENEFICIAL only if quadratic beats BOTH controls on log loss (CI upper < 0), is non-inferior on selection
    (CI lower > -margin) and >= 2 of 3 seeds agree; UNSUPPORTED if it does not improve the point estimate against either control or is
    selection-inferior (point < 0 and CI lower <= -margin); otherwise INCONCLUSIVE."""
    if ll_unc["diff"] >= 0 or ll_sa["diff"] >= 0 or any(s["diff"] < 0 and s["ci95"][0] <= -margin for s in (sel_unc, sel_sa)):
        return "UNSUPPORTED"
    if ll_unc["ci95"][1] < 0 and ll_sa["ci95"][1] < 0 and sel_unc["ci95"][0] > -margin and sel_sa["ci95"][0] > -margin and seeds_ok:
        return "BENEFICIAL"
    return "INCONCLUSIVE"


# ------------------------------------------------------------------ preregistered splits (family-grouped, stratified)
SEVERITY = {"K0": 0, "K1": 1, "None": 2, "K>=2": 3}


def folds(D, R) -> dict:
    """5 family-grouped folds over the 197 train+val roots, stratified by the family's most severe stratum (hash order, round robin), and per
    fold an early-stopping subset of ~1/8 of the training families (per stratum, hash order). Test roots never appear."""
    fam = {}
    for k in D["root_order"]:
        fam.setdefault(R[k]["ids"]["parent_family_id"], []).append(k)
    st = {f: max((D["roots"][k]["stratum"] for k in ks), key=SEVERITY.get) for f, ks in fam.items()}
    fold = {}
    for s in SEVERITY:
        for i, f in enumerate(sorted((f for f in fam if st[f] == s), key=lambda f: PM.bc.sha([f, "BXY_P11_FOLD"]))):
            fold[f] = i % FOLDS
    out = []
    for j in range(FOLDS):
        pool = [f for f in fam if fold[f] != j]
        es = set()
        for s in SEVERITY:
            fs = sorted((f for f in pool if st[f] == s), key=lambda f: PM.bc.sha([f, "BXY_P11_ES", j]))
            es |= set(fs[:max(1, round(len(fs) / ES_EVERY))] if len(fs) >= 2 else [])
        roots = lambda fs: sorted(k for f in fs for k in fam[f])  # noqa: E731
        out.append({"fold": j, "heldout": roots([f for f in fam if fold[f] == j]), "early_stop": roots(es), "train": roots([f for f in pool if f not in es])})
    return {"folds": out, "family_stratum": st}


def roster(D, R) -> list:
    """Every training run the next gate may launch, in launch order. 'SELECTED' lambda = the arm's own lambda* from the SPLIT phase."""
    runs = []
    for arm in ("XY-quadratic", "XY-uncoupled", "XY-uncoupled-SA"):
        runs += [{"id": f"split/{arm}/lam{l}/s{s}", "phase": "SPLIT", "arm": arm, "lambda_J": l, "seed": s, "train": "train176", "early_stop": "val21"}
                 for l in LAMBDAS for s in SEEDS]
    runs += [{"id": f"split/{a}/lam0/s{s}", "phase": "SPLIT", "arm": a, "lambda_J": 0.0, "seed": s, "train": "train176", "early_stop": "val21"}
             for a in ("XY-quadratic-noJ", "DIRECT") for s in SEEDS]
    for f in range(FOLDS):
        runs += [{"id": f"cv/f{f}/{a}/s{s}", "phase": "CROSSFIT", "arm": a, "lambda_J": "SELECTED" if ARMS[a]["travel"] else 0.0, "seed": s,
                  "train": f"fold{f}.train", "early_stop": f"fold{f}.early_stop", "heldout": f"fold{f}.heldout"} for a in ARMS for s in SEEDS]
    return runs
