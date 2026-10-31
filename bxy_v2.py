"""Approach B X/Y V2 learner interface (BXY-P10-PREREG; no training is run here).

Reads a BXY_SIDECAR_V2* file (context-hashed X2/Y2 keys, x_queries / y_queries / paired) READ-ONLY and builds the same per-root views as
bxy_core.views (which stays the frozen V1 reader of runs/approach_b/bxy/SIDECAR.json):
  identity   every key is recomputed from the immutable root record (bxy_teacher.xkey / ykey / context); any mismatch raises
  labels     observed iff attempted and observed and y in {0, 1}; CENSORED / NOT_ATTEMPTED / INELIGIBLE / F1-screened are ABSENT (never 0);
             one variable per distinct key; two rows with one key must agree (else ConflictError)
  variables  observed X and every X's parent Y (shared across orders); full=True adds every F1-admissible catalogue candidate unobserved
  travel     COMPLETE-witness travel only (methodology §6.1): J_total of a replayed full-joint-success pair, and for the zero-move repair the
             replayed Y0 target witness from q_ref (X_empty = 1 by definition, robot already at q_ref, no connector)
Cost convention (fixes bxy_run.predict_xy's J_hat = 0 for the no-op): J_hat(r) = J_corr(g_r) + J_tgt(v_s(r), c), J_corr = softplus(cost(g_r))
for a nonempty prefix (relocations + connector) and exactly 0 for the zero-move repair (no motion precedes the target), J_tgt = softplus of
a scene head on the edited scene at q_ref. Every candidate, the no-op included, is charged the complete action travel."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

import bxy_core as X
import bxy_data as bd
import bxy_f1 as F1
import bxy_teacher as T
from abc_models import W, mlp

PILOT = Path("runs/approach_b/bxy_teacher_pilot_v1/BXY_SIDECAR_V2_PILOT.json")
VERSIONS = ("BXY_SIDECAR_V2_PILOT", "BXY_SIDECAR_V2_PMIN")
RECORDS = "runs/approach_b/bd2d_lb_v1/RECORDS.pt"


class ConflictError(ValueError):
    pass


def load(path=PILOT) -> dict:
    raw = Path(path).read_bytes()
    sc = json.loads(raw)
    if sc.get("version") not in VERSIONS:
        raise ValueError(f"not a V2 sidecar: {sc.get('version')}")
    return sc | {"_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(), "_path": str(path)}


def check_identity(sc, R) -> list:
    """Problems (empty = every row's identity re-derives exactly from the immutable root records)."""
    bad = []
    if len(sc["manifest"]["teacher_hash"]) != 1:
        bad.append(f"mixed teacher hashes {sc['manifest']['teacher_hash']}")
    for r in sc["x_queries"]:
        k, seq = r["root"], [tuple(a) for a in r.get("ordered_actions") or []]
        if "x_key" in r and (r["x_key"] != T.xkey(k, R[k], seq) or r["parent_y_key"] != T.ykey(k, R[k], seq)):
            bad.append(f"x identity {r['x_key']}")
    for r in sc["y_queries"]:
        k = r["root"]
        if "y_key" in r and (r["y_key"] != T.ykey(k, R[k], edit=r["hypothetical_poses"]) or r["q_ref_hash"] != T.context(k, R[k])
                             or not np.allclose(r["robot_start_q_ref"], T.qref(R[k]), atol=0)):
            bad.append(f"y identity {r['y_key']}")
    return bad


def _obs(r) -> bool:
    return bool(r.get("attempted")) and bool(r.get("observed")) and r.get("y") in (0, 1)


def observations(sc) -> dict:
    """{root: {"x": {key: {y, seq, parent}}, "y": {key: {y, edit}}, "j": [(x_key | None, y_key, J)], "absent": [(key | item, status)]}}."""
    out = {}

    def put(d, key, val):
        if key in d and d[key]["y"] != val["y"]:
            raise ConflictError(f"{key}: {d[key]['y']} vs {val['y']}")
        d.setdefault(key, val)
    for side, rows in (("x", sc["x_queries"]), ("y", sc["y_queries"])):
        for r in rows:
            o = out.setdefault(r["root"], {"x": {}, "y": {}, "j": [], "absent": []})
            if not _obs(r):
                o["absent"].append((r.get(f"{side}_key", r.get("item")), r.get("teacher_status")))
            elif side == "x":
                put(o["x"], r["x_key"], {"y": int(r["y"]), "seq": [tuple(a) for a in r["ordered_actions"]], "parent": r["parent_y_key"]})
            else:
                put(o["y"], r["y_key"], {"y": int(r["y"]), "edit": {a: int(c) for a, c in r["hypothetical_poses"].items()}})
                if r["y"] == 1 and not r["hypothetical_poses"] and r.get("J_target") is not None and r.get("independent_replay"):
                    o["j"].append((None, r["y_key"], float(r["J_target"])))           # zero-move complete witness
    for p in sc["paired"]:
        if p.get("full_joint_success") == 1 and p.get("J_total") is not None and p.get("matched_protocol"):
            out[p["root"]]["j"].append((p["x_key"], p["y_key"], float(p["J_total"])))
    for o in out.values():
        o["j"] = sorted(set(o["j"]), key=str)
    return out


def catalogue(k, rec) -> list:
    """bd.catalogue with V2 keys and the F1 screen of every candidate (the zero-move candidate is always kept)."""
    out = []
    for c in bd.catalogue(rec):
        f = F1.screen(rec, c["seq"])
        out.append({**c, "seq": [list(a) for a in c["seq"]], "x": T.xkey(k, rec, c["seq"]) if c["seq"] else None, "y": T.ykey(k, rec, c["seq"]),
                    "f1_complete_ok": f["complete_ok"] or not c["seq"], "f1_x_ok": f["x_ok"], "f1_y_ok": f["y_ok"]})
    return out


def views(split, path=PILOT, records=RECORDS, full=False) -> list:
    """Per-root views (bxy_core.views layout + j_items) over the roots of a V2 sidecar in this split."""
    import abc_models as am
    from scene import scene_from_dict
    sc, R = load(path), bd.roots()
    bad = check_identity(sc, R)
    if bad:
        raise ValueError(f"V2 identity check failed: {bad[:5]}")
    O, out = observations(sc), []
    for rec in torch.load(records, weights_only=False)["roots"]:
        k = rec["audit"]["root"]
        if k not in O or rec["audit"]["split"] != split:
            continue
        assert bd.split_of(R[k]) == split, k
        o, ids, lat, cat = O[k], rec["audit"]["ids"], scene_from_dict(R[k]["scene"]).lattice, catalogue(k, R[k])
        xs = {q: v["seq"] for q, v in o["x"].items()}
        par = {q: v["parent"] for q, v in o["x"].items()}
        ed = {q: v["edit"] for q, v in o["y"].items()}
        if full:
            for c in cat:
                if c["seq"] and c["f1_x_ok"]:
                    xs.setdefault(c["x"], [tuple(a) for a in c["seq"]])
                    par.setdefault(c["x"], c["y"])
                if c["f1_y_ok"]:
                    ed.setdefault(c["y"], bd.endpoint(R[k], [tuple(a) for a in c["seq"]]))
        for q, s in xs.items():
            ed.setdefault(par[q], bd.endpoint(R[k], s))
        xk, yk = sorted(xs), sorted(ed)
        xi, yi = {q: i for i, q in enumerate(xk)}, {q: i for i, q in enumerate(yk)}
        enc = lambda pairs: [(ids.index(a), tuple(lat.center(c))) for a, c in pairs]  # noqa: E731
        out.append({"key": k, "R": am.Root(rec), "ids": ids, "y_keys": yk, "x_keys": xk,
                    "y_poses": [{ids.index(a): tuple(lat.center(c)) for a, c in ed[q].items()} for q in yk],
                    "x_seqs": [enc(xs[q]) for q in xk], "parent": [yi[par[q]] for q in xk],
                    "obs_y": {yi[q]: v["y"] for q, v in o["y"].items()}, "obs_x": {xi[q]: v["y"] for q, v in o["x"].items()},
                    "j_items": [(xi[a] if a else None, yi[b]) for a, b, _ in o["j"]], "j_obs": [j for *_, j in o["j"]],
                    "catalogue": cat, "verified_K": R[k]["verified_K"], "cells0": bd.cells0(R[k]),
                    "provenance": {"sidecar": sc["version"], "sha256": sc["_sha256"], "teacher_hash": sc["manifest"]["teacher_hash"][0],
                                   "absent": o["absent"]}})
    return out


class ModelXY2(X.ModelXY):
    """ModelXY + the target-travel scene head; J over rt['j_items'] = complete-witness travel (no-op included)."""

    def __init__(self, coupled=True):
        super().__init__(coupled)
        self.jt = mlp(2 * W, 1)

    def coeffs(self, rt):
        R, c = rt["R"], None
        self._memo = {}
        try:
            c = self.ctxn(R.ctx)
            v = [self.memo(("v", tuple(sorted(p.items()))), lambda p=p: self.scene_vec(R, self.edited(R, p))) for p in rt["y_poses"]]
            b = torch.stack([self.scene(torch.cat([x, c]))[0] for x in v]) if v else torch.zeros(0, dtype=X.D)
            a, w, g = [], [], []
            for seq, s in zip(rt["x_seqs"], rt["parent"]):
                sq, gq, _ = self.order(R, seq)
                a.append(sq)
                g.append(gq)
                w.append(self.xy(torch.cat([gq, v[s], c]))[0] if self.coupled else torch.zeros((), dtype=X.D))
            J = [self.j_hat(g[i] if i is not None else None, v[s], c) for i, s in rt.get("j_items", [])]
        finally:
            self._memo = None
        z = torch.zeros(0, dtype=X.D)
        return b, (torch.stack(a) if a else z), (torch.stack(w) if w else z), (torch.stack(J) if J else z)

    def j_hat(self, g, v, c):
        tgt = F.softplus(self.jt(torch.cat([v, c]))[0])
        return tgt if g is None else tgt + F.softplus(self.cost(g)[0])


def build(arm) -> ModelXY2:
    return ModelXY2(coupled=X.ARMS[arm]).double()


def root_loss(m, rt, lam_j, tau=X.TAU):
    b, a, w, J = m.coeffs(rt)
    nll = -X.log_evidence(b, a, w, rt["parent"], rt["obs_y"], rt["obs_x"], tau)
    tr = F.huber_loss(torch.log1p(J), torch.log1p(torch.tensor(rt["j_obs"], dtype=X.D))) if len(J) and lam_j else None
    return nll, tr


@torch.no_grad()
def predict(m, rt) -> list:
    """Every catalogue candidate with p_succ (marginalized, no label), complete J_hat (no-op = target travel) and its F1 admissibility.
    rt must be a full=True view."""
    rt2 = dict(rt)
    xi, yi = {q: i for i, q in enumerate(rt["x_keys"])}, {q: i for i, q in enumerate(rt["y_keys"])}
    adm = [c for c in rt["catalogue"] if c["f1_complete_ok"]]
    rt2["j_items"] = [(xi[c["x"]] if c["x"] else None, yi[c["y"]]) for c in adm]
    b, a, w, J = m.coeffs(rt2)
    mg = X.marginals(b, a, w, rt["parent"])
    rows, it = [], iter(J.tolist())
    for c in rt["catalogue"]:
        seq = [(o, int(d)) for o, d in c["seq"]]
        row = {"seq": c["seq"], "role": c["role"], "m": len(seq), "admissible": c["f1_complete_ok"], "x_key": c["x"], "y_key": c["y"]}
        if c["f1_complete_ok"]:
            p = float(mg["psucc"][xi[c["x"]]]) if seq else float(mg["py"][yi[c["y"]]])
            row |= {"p": p, "cd": float(np.sum([np.hypot(d % 8 - rt["cells0"][o] % 8, d // 8 - rt["cells0"][o] // 8) for o, d in seq])),
                    "J_hat": next(it)}
        rows.append(row)
    return rows


def choose(rows, eta, alpha, beta, gamma):
    """F1 first (screened candidates are never scored), then bxy_run.choose's validation-frozen cost rule on the admissible ones."""
    import bxy_run
    adm = [i for i, r in enumerate(rows) if r["admissible"]]
    j = bxy_run.choose([rows[i] for i in adm], eta, alpha, beta, gamma)
    return None if j is None else adm[j]
