"""BXY-P17 data: leakage-separated (ScorerView, Labels, EvalView) triples for every development corpus, and the analytic access features.

Corpora: PMIN (bxy_p11.build over the 176 TRAIN + 21 VAL P-min roots; outcome-guided historical catalogues), P15 (BXY_GEN_V2 pilot, 28
outcome-blind roots) and V21 (BXY_GEN_V21 / V21B waves of P16). New roots go through the SAME view contract as bxy_p11.build: the scorer sees
label-free tensors (bxy_p16_inputs), the frozen design's Y edit poses / ordered X actions / shared parents, the Y0 index and the canonical
(m, signature)-sorted candidates with analytic F1 admissibility; labels hold observed X / Y (attempted, observed, binary; censored /
unattempted / screened are absent), DIRECT success events and complete-witness travel; the evaluator view holds candidate outcomes, kinds,
negative kinds, order groups, omissions and strata. The 34 exposed P-min test roots never appear (bxy_p11.build refuses them).

Access features (GEO2, geometry only, from the scorer's own tensors + the P16 access maps; union model of the analytic grasp screens):
  phi_Y(S_s)  [open T-pick modes / 48, open T-place modes / 48, pick open?, place open?, goal occupied?]  of the edited scene at q_ref
  phi_X(q)    over the actions of the ordered prefix, in each action's IDEAL predecessor scene: mean and min of [object pick modes / 48, place
              modes at its destination / 48], fraction with closed pick, fraction with closed place  (8 values)
  phi_X0(q)   the order-invariant twin: the same statistics with every action evaluated in S0 (used by the order-invariant control only)."""
from __future__ import annotations

import collections
import json
from pathlib import Path

import numpy as np

import bxy_data as bd
import bxy_f1 as F1
import bxy_p11 as P
import bxy_p15 as P15
import bxy_p16 as G
import bxy_teacher as T

OUT = Path("runs/approach_b/bxy_p17_v1")
INPUTS = {"P15": Path("runs/approach_b/bxy_p16_v1/inputs/INPUTS_P15_PILOT.pt"), "V21": Path("runs/approach_b/bxy_p16_v1/inputs/INPUTS_V21.pt")}
N_CAND = 48.0
EXTRA_MAPS = OUT / "ACCESS_MAPS_PLACE_EXTRA.json"


def _maps() -> dict:
    """P16 access maps + the P17 place maps of the 30 non-goal cells (merged in memory only; the P16 file is never rewritten)."""
    M = G._load_maps()
    if "place:0" not in M and EXTRA_MAPS.exists():
        M.update(json.loads(EXTRA_MAPS.read_text())["maps"])
    return M


# ------------------------------------------------------------------ analytic access features (scorer tensors only)
def _cell(xy) -> int:
    return int(min(7, max(0, int(xy[1] // 0.08)))) * 8 + int(min(7, max(0, int(xy[0] // 0.08))))


def _cells(Rt, edit) -> list:
    xy = Rt.xy0.numpy().copy()
    for o, p in edit.items():
        xy[int(o)] = p
    return [_cell(p) for p in xy]


def phi_y(Rt, edit) -> list:
    cells, t = _cells(Rt, edit), Rt.tid
    goal = _cell(Rt.goal.numpy())
    others = [c for i, c in enumerate(cells) if i != t]
    p = len(G.open_after(_maps()[f"pick:{cells[t]}"], others))
    q = len(G.open_after(_maps()[f"place:{goal}"], others))
    return [p / N_CAND, q / N_CAND, float(p > 0), float(q > 0), float(goal in others)]


def phi_x(Rt, seq, ordered=True) -> list:
    """seq: [(object index, (x, y))] as in ScorerView x_seqs."""
    cells0 = _cells(Rt, {})
    cur, P_, Q_ = list(cells0), [], []
    for i, dest in seq:
        base = cur if ordered else cells0
        others = [c for j, c in enumerate(base) if j != i]
        d = _cell(dest)
        M = _maps()
        P_.append(len(G.open_after(M[f"pick:{base[i]}"], others)) / N_CAND)
        Q_.append(len(G.open_after(M[f"place:{d}"], others)) / N_CAND)
        if ordered:
            cur[i] = d
    if not P_:
        return [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    return [float(np.mean(P_)), float(min(P_)), float(np.mean(Q_)), float(min(Q_)), float(np.mean([p == 0 for p in P_])),
            float(np.mean([q == 0 for q in Q_])), float(len(P_)) / 6.0, 0.0]


# ------------------------------------------------------------------ views of the outcome-blind corpora
def _results(rdir) -> dict:
    out = {}
    for f in sorted(Path(rdir).glob("*.json")) if Path(rdir).exists() else []:
        r = json.loads(f.read_text())
        out[r["design_key"]] = r
    return out


def _obs(r) -> bool:
    return bool(r) and bool(r.get("attempted")) and bool(r.get("observed")) and r.get("y") in (0, 1)


def corpus_roots():
    """[(corpus, wave, root key, record, design entry, results dir)] for P15 and every collected P16 wave (frozen designs only)."""
    out = []
    D15 = json.loads((P15.OUT / "PILOT_DESIGN.json").read_text())
    R15 = P15.pilot_roots()
    for k in D15["root_order"]:
        out.append(("P15", "pilot", k, R15[k], D15["roots"][k], P15.OUT / "results" / k))
    for w in sorted(G.WAVES):
        f = G.wdir(w) / "DESIGN.json"
        if not f.exists() or not (G.wdir(w) / "SUMMARY.json").exists():
            continue
        D, R = json.loads(f.read_text()), G.roots_of(w)
        for k in D["root_order"]:
            out.append(("V21", w, k, R[k], D["roots"][k], G.wdir(w) / "results" / k))
    return out


def view(corpus, wave, k, rec, d, rdir, inp) -> tuple:
    import abc_models as am
    from scene import scene_from_dict
    ids, lat = inp["ids"], scene_from_dict(rec["scene"]).lattice
    Q, res = d["queries"], _results(rdir)
    xk = sorted(key for key, q in Q.items() if q["side"] == "x")
    edits = {key: q["edit"] for key, q in Q.items() if q["side"] == "y"}
    for q in xk:
        e = bd.endpoint(rec, [tuple(a) for a in Q[q]["seq"]])
        if edits.setdefault(Q[q]["parent_y_key"], e) != e:
            raise RuntimeError(f"{k}: parent edit differs from its endpoint")
    yk = sorted(edits)
    xi, yi = {q: i for i, q in enumerate(xk)}, {q: i for i, q in enumerate(yk)}
    y0 = T.ykey(k, rec, [])
    enc = lambda seq: [(ids.index(o), tuple(lat.center(int(c)))) for o, c in seq]  # noqa: E731
    cat, kinds = {}, {}
    c0 = bd.cells0(rec)
    for c in [{"seq": [], "kind": "noop", "f1_complete_ok": True}] + d["catalogue"]:
        seq = [(o, int(dd)) for o, dd in c["seq"]]
        s = bd.sig(seq)
        ok = (not seq) or (c["f1_complete_ok"] and T.xkey(k, rec, seq) in xi and T.ykey(k, rec, seq) in yi)
        cat.setdefault(s, {"sig": s, "m": len(seq), "cd": P.cd_cells(rec, seq), "xi": xi[T.xkey(k, rec, seq)] if ok and seq else None,
                           "yi": yi[T.ykey(k, rec, seq)] if ok else None, "admissible": bool(ok)})
        kinds.setdefault(s, c["kind"])
    cands = sorted(cat.values(), key=lambda c: (c["m"], c["sig"]))
    sv = {"key": k, "R": am.Root({"inputs": inp["inputs"]}), "y_poses": [{ids.index(o): tuple(lat.center(int(c))) for o, c in sorted(edits[q].items())} for q in yk],
          "x_seqs": [enc(Q[q]["seq"]) for q in xk], "parent": [yi[Q[q]["parent_y_key"]] for q in xk], "y0": yi[y0], "cands": cands}
    P.check_scorer(sv)
    ox = {xi[q]: int(res[q]["y"]) for q in xk if _obs(res.get(q))}
    oy = {yi[q]: int(res[q]["y"]) for q in yk if _obs(res.get(q))}
    j = []
    for c in cands:                                                                  # complete-witness travel only (both replayed)
        if not c["admissible"]:
            continue
        if c["m"] == 0:
            r = res.get(y0)
            if _obs(r) and r["y"] == 1 and r.get("independent_replay") is True and r.get("J_target") is not None:
                j.append((None, c["yi"], float(r["J_target"])))
            continue
        xr, yr = res.get(xk[c["xi"]]), res.get(yk[c["yi"]])
        if _obs(xr) and _obs(yr) and xr["y"] == 1 and yr["y"] == 1 and xr.get("independent_replay") is True and yr.get("independent_replay") is True:
            j.append((c["xi"], c["yi"], float(xr["travel_parts"]["J_prefix_stitched"] + yr["J_target"])))
    lab = {"key": k, "obs_x": ox, "obs_y": oy, "succ": P.success_events(ox, oy, sv["parent"], sv["y0"]), "j": sorted(set(j), key=lambda t: (t[0] is not None, t[0] or 0, t[1]))}
    meta = lambda r: {"status": (r or {}).get("teacher_status"), "negative_kind": (r or {}).get("negative_kind"), "phase": (r or {}).get("failed_phase")}  # noqa: E731
    ecands = []
    for c in cands:
        x = ox.get(c["xi"]) if c["xi"] is not None else None
        y = oy.get(c["yi"]) if c["yi"] is not None else None
        out = None if not c["admissible"] else (oy.get(sv["y0"]) if c["m"] == 0 else 0 if 0 in (x, y) else 1 if (x, y) == (1, 1) else None)
        ecands.append({"sig": c["sig"], "success": out, "x": x, "y": y, "kind": kinds.get(c["sig"]), "legacy": []})
    groups = collections.defaultdict(list)
    for q, key in enumerate(xk):
        if len(Q[key]["seq"]) >= 2 and q in ox:
            groups[sv["parent"][q]].append(q)
    order = [{"y": p, "members": [{"xi": q, "x": ox[q], **meta(res.get(xk[q]))} for q in g]} for p, g in sorted(groups.items()) if len(g) >= 2]
    omi = []
    for c in cands:
        if c["admissible"] and c["m"] >= 2:
            seq = [(a.split(">")[0], int(a.split(">")[1])) for a in c["sig"].split(".")]
            oms = [[a for i, a in enumerate(seq) if i != t] for t in range(len(seq))]
            omi.append({"sig": c["sig"], "xi": c["xi"], "yi": c["yi"], "omit": [{"xi": xi.get(T.xkey(k, rec, om)), "yi": yi.get(T.ykey(k, rec, om))} for om in oms]})
    vk = None
    if oy.get(sv["y0"]) == 1:
        vk = 0
    elif oy.get(sv["y0"]) == 0:
        ok = [c["m"] for c, e in zip(cands, ecands) if e["success"] == 1]
        vk = min(ok) if ok else None
    ev = {"key": k, "split": "train", "corpus": corpus, "wave": wave, "family": rec["ids"]["parent_family_id"], "stratum": rec.get("start_stratum"),
          "verified_K": vk, "y0": oy.get(sv["y0"]), "cands": ecands, "parent": list(sv["parent"]), "order_groups": order, "omissions": omi,
          "obs_x": dict(ox), "obs_y": dict(oy), "x_meta": {q: meta(res.get(key)) for q, key in enumerate(xk)}, "y_meta": {s: meta(res.get(key)) for s, key in enumerate(yk)},
          "x_keys": xk, "y_keys": yk, "mechanism": rec["spec"].get("mechanism"), "K_intent": rec["spec"].get("K_intent"),
          "K_geom": rec.get("construction", {}).get("K_geom"), "travel": {kinds_sig: None for kinds_sig in []}}
    ev["travel"] = {c["sig"]: J for c in cands for a, b, J in lab["j"] if (a == c["xi"] and b == c["yi"] and c["m"] > 0) or (a is None and c["m"] == 0)}
    return sv, lab, ev


def build_all() -> list:
    """Every development triple: PMIN (train + val) then P15 then V21 (corpus recorded in EvalView['corpus'])."""
    import torch
    out = []
    for sv, lab, ev in P.build(("train", "val")):
        ev = dict(ev, corpus="PMIN", wave="pmin", mechanism=None, K_intent=None, K_geom=None)
        out.append((sv, lab, ev))
    inp = {}
    for name, f in INPUTS.items():
        if f.exists():
            inp.update(torch.load(f, weights_only=False)["roots"])
    for corpus, wave, k, rec, d, rdir in corpus_roots():
        out.append(view(corpus, wave, k, rec, d, rdir, inp[k]))
    return out
