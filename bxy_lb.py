"""Phase 1: the frozen production LB (p17_b ARMS['LB'] = ModelBC7('B', 'none', order='pred'), keyed unique-factor NLL, lambda_static =
lambda_travel = 0, AdamW 1e-3 / wd 1e-4, root batch 12, clip 10, validation every 20 updates, patience 15, <= 3000 updates) trained from
scratch on the BD_GEN_V1 2D roots. Only a data adapter is new: recorded labels go in unchanged (original -> seq:empty, D -> scene edits,
B -> whole-sequence queries); layout = P17_LAYOUT_V1 with the move cap raised from 4 to 6 (MAX_ACTIVE = 9 still holds: a 6-move
candidate keeps z0 + zR + 6 omissions + 1 scene edit). No historical P13-P17 root is read."""
from __future__ import annotations

import contextlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

import bxy_data as bd
import config as cf
import p17_b as pb

OUT = Path("runs/approach_b/bd2d_lb_v1")
LAYOUT = "BXY_LB_LAYOUT_V1"


@contextlib.contextmanager
def cap6():
    """p17_b.layout with MOVE_CAP = 6 under its own version string; restored afterwards (historical P17 code untouched)."""
    old = pb.MOVE_CAP, pb.LAYOUT
    pb.MOVE_CAP, pb.LAYOUT = 6, LAYOUT
    try:
        yield
    finally:
        pb.MOVE_CAP, pb.LAYOUT = old


def labels(k, rec) -> dict:
    """Recorded binary labels as LB queries (y unchanged; cost = recorded travel of a successful sequence)."""
    src = rec["ids"]["label_protocol"]
    out = {f"seq:{k}:empty": {"y": rec["labels"]["original"]["y"], "source": src, "weight": 1.0, "cost": None}}
    for e in rec["labels"]["D"]:
        out[f"scene:{k}:{pb.sig(sorted((o, int(c)) for o, c in e['edit'].items()))}"] = {"y": e["y"], "source": src, "weight": 1.0, "cost": None}
    for b in rec["labels"]["B"]:
        out[f"seq:{k}:{pb.sig([(o, int(c)) for o, c in b['sequence']])}"] = {"y": b["y"], "source": src, "weight": 1.0,
                                                                              "cost": b["travel"] if b["y"] == 1 else None}
    return out


def records(R, dino=None) -> list:
    import learn_data as ld
    import p10c_train_eval as pc
    import p6_learn as pl
    cfg, dino = cf.load_config("config.toml"), dino or ld.dino()
    out, sc = [], pl.static_checks
    pl.static_checks = lambda cfg, s, ids, seed: sc(cfg, s, ids, seed) if any(o.kind == "obstacle" for o in s.objects) else []  # target-only
    with cap6():                                                    # scenes: nothing to place (static terms have lambda 0 in LB anyway)
        for k, rec in R.items():
            lat = [{"kind": "+".join(sorted(e["edit"])), "edit_kind": "+".join(sorted(e["edit"])), "edit": {o: int(c) for o, c in e["edit"].items()},
                    "eligible": True} for e in rec["labels"]["D"]]
            seqs = [c["seq"] for c in bd.catalogue(rec)]
            items = [{"kind": "BXY_LB_CANDIDATE", "sequence": [list(a) for a in s], "z_layout": pb.layout(k, s, pb.edits_for(s, lat))} for s in seqs]
            r = {"scene": rec["scene"], "goal_cell": rec["goal_cell"], "family": rec["ids"]["parent_family_id"], "stratum": rec["start_stratum"],
                 "seed": rec["ids"]["construction_seed"]}
            x, _ = pc._record(cfg, dino, k, r, labels(k, rec), bd.split_of(rec), "BD_GEN_V1", lat, items)
            x["audit"] |= {"layout": LAYOUT, "verified_K": rec["verified_K"], "roles": [c["role"] for c in bd.catalogue(rec)]}
            out.append(x)
    pl.static_checks = sc
    return out


def build() -> None:
    R = bd.roots()
    recs = records(R)
    OUT.mkdir(parents=True, exist_ok=True)
    torch.save({"version": "BXY_LB_RECORDS_V1", "data_hash": bd.data_hash(), "layout": LAYOUT, "roots": recs}, OUT / "RECORDS.pt")


def split(name):
    d = torch.load(OUT / "RECORDS.pt", weights_only=False)
    return pb.prepare([r for r in d["roots"] if r["audit"]["split"] == name])


def auroc(y, p):
    y, p = np.asarray(y), np.asarray(p)
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return None
    return float(((pos[:, None] > neg[None]) + 0.5 * (pos[:, None] == neg[None])).mean())


def metrics(y, p) -> dict:
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    if not len(y):
        return {"n": 0}
    return {"n": int(len(y)), "positives": int(y.sum()), "brier": float(np.mean((p - y) ** 2)), "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log1p(-p))),
            "auroc": auroc(y, p), "acc@0.5": float(np.mean((p >= 0.5) == y))}


def predictions(m, roots) -> dict:
    """Prior marginals (no labels used) for every candidate query and every scene-edit query, with their recorded labels."""
    import unique_factor as uf
    import unique_factor_keyed as ufk
    import joint_likelihood as jl
    out = {}
    with ufk.installed(), torch.no_grad():
        for r in roots:
            pm, lab = uf.prior_marginals(uf.instances(m, r)), jl.labels(r)
            out[r["key"]] = {"candidates": [{"query": c["query"], "seq": [[r["ids"][i], list(d)] for i, d in c["seq"]], "m": len(c["seq"]),
                                             "role": role, "p": pm[c["query"]], "y": lab.get(c["query"])} for c, role in zip(r["cands"], r["audit"]["roles"])],
                             "scene": [{"query": q, "p": pm[q], "y": lab.get(q)} for q in r["edit_q"].values()]}
    return out


def evaluate(m, roots) -> dict:
    import unique_factor as uf
    import unique_factor_keyed as ufk
    with ufk.installed(), torch.no_grad():
        nll = uf.total(m, roots, 0.0, 0.0)[1]["nll"]
    P = predictions(m, roots)
    rows = [c for v in P.values() for c in v["candidates"] if c["y"] is not None]
    sc = [s for v in P.values() for s in v["scene"] if s["y"] is not None]
    return {"root_nll": nll, "roots": len(roots), "candidates_all": metrics([c["y"] for c in rows], [c["p"] for c in rows]),
            "candidates_empty": metrics([c["y"] for c in rows if not c["m"]], [c["p"] for c in rows if not c["m"]]),
            "candidates_nonempty": metrics([c["y"] for c in rows if c["m"]], [c["p"] for c in rows if c["m"]]),
            "scene_edits": metrics([s["y"] for s in sc], [s["p"] for s in sc])}, P


def run(seed=0, updates=3000) -> dict:
    tr, va, te = split("train"), split("val"), split("test")
    c0, w0 = time.process_time(), time.time()
    with cap6():
        m, rec = pb.fit("LB", seed, tr, va, updates)
    cpu, wall = time.process_time() - c0, time.time() - w0
    ck = OUT / "ckpt" / f"BXY-LB-s{seed}.pt"
    ck.parent.mkdir(parents=True, exist_ok=True)
    torch.save(m.state_dict(), ck)
    m.eval()
    ev = {s: evaluate(m, rs) for s, rs in (("val", va), ("test", te))}
    hist = [{k: h.get(k) for k in ("update", "total", "nll", "val", "grad_pre", "clipped")} for h in rec["history"]]
    import p17_eval as pe
    res = {"arm": "LB", "model": "abc7_models.ModelBC7('B','none',order='pred')", "objective": "unique_factor_keyed NLL, lambda_static=lambda_travel=0",
           "seed": seed, "updates_cap": updates, **{k: v for k, v in rec.items() if k != "history"}, "train_cpu_s": round(cpu, 1), "train_wall_s": round(wall, 1),
           "roots": {"train": len(tr), "val": len(va), "test": len(te)}, "sampler_groups": "all roots kappa_group 'none' (BD edits are not A/B/A+B): uniform",
           "checkpoint": pe.sha(ck), "records": pe.sha(OUT / "RECORDS.pt"), "data_hash": bd.data_hash(), "layout": LAYOUT,
           "val": ev["val"][0], "test": ev["test"][0]}
    cf.write_json(OUT / f"EVAL_s{seed}.json", res)
    cf.write_json(OUT / f"TRAIN_LOG_s{seed}.json", {"seed": seed, "history": hist})
    cf.write_json(OUT / f"PREDICTIONS_s{seed}.json", {"val": ev["val"][1], "test": ev["test"][1]})
    return res


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build()
    else:
        r = run(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
        print(json.dumps({k: r[k] for k in ("best_update", "updates_run", "stopped_early", "val_root_nll", "train_cpu_s", "val", "test")}, indent=1))
