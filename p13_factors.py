"""P13 analyses on frozen predictions only (no fitting, no label edits): P13-0 corrected P12 kappa estimand + zero-interaction
baseline + strict D / scene-edit correspondence; later stages add factor audits and targeted endpoints here."""
from __future__ import annotations

import collections
import math

import numpy as np

import config as cf
import p12_closure as p12
from p13_pipeline import OUT

ARMS = p12.FROZEN_ARMS
V, C = "VERIFIED_FEASIBLE", "CERTIFIED_INFEASIBLE"


def _paired(e, a, b, ks=None):
    """Root-paired Delta = e[a] - e[b] (positive = b better), exact two-sided sign test (ties removed), bootstrap CI."""
    ks = sorted(set(e[a]) & set(e[b])) if ks is None else ks
    d = [e[a][k] - e[b][k] for k in ks]
    p, pos, neg, ties = p12._sign(d)
    return {"roots": len(d), "mean_delta": float(np.mean(d)) if d else None, "ci95": p12._boot(d), "p_raw": p,
            f"{b}_better": pos, f"{a}_better": neg, "ties": ties,
            "effect_size_d": float(np.mean(d) / np.std(d, ddof=1)) if len(d) > 2 and np.std(d) > 0 else None}


def p12_four_tuples():
    snap, P, rec = p12._rd(p12.HOLD / "PREDICTIONS_FROZEN.json"), p12.plans(), {}
    for b in sorted(p12.HOLD.glob("batch*/plan.json")):
        rec |= p12.sealed_records(b.parent.name)
    four = {}
    for k, r in P.items():
        t = {it["token"]: it["query"] for it in r["items"]}
        qs = [t[""], t["edit:A"], t["edit:B"], t["edit:A+B"]]
        st = [rec.get(q, {}).get("teacher_status") for q in qs]
        if all(s in (V, C) for s in st):
            y = [int(s == V) for s in st]
            four[k] = {"q": qs, "y": y, "kappa": y[3] - y[1] - y[2] + y[0], "family": r["family"], "status": st}
    return snap, P, four


def kappa_correction() -> dict:
    """P12 primary F3 / F5s under the PREREGISTERED estimand |mean_s khat_s - kappa| (seed-averaged marginals), next to the
    published seed-wise statistic mean_s |khat_s - kappa|; constant-zero and no-coupling controls; stratified by kappa and truth pattern."""
    snap, P, four = p12_four_tuples()
    ks_ = collections.defaultdict(dict)                       # arm -> root -> [khat per seed 0..2]
    for a in snap["arms"].values():
        for k, f in four.items():
            m = a["roots"][k].get("marginals") or {}
            if all(q in m for q in f["q"]):
                q0, qa, qb, qab = f["q"]
                ks_[a["arm"]].setdefault(k, {})[a["seed"]] = m[qab] - m[qa] - m[qb] + m[q0]
    full = {arm: {k: v for k, v in d.items() if sorted(v) == [0, 1, 2]} for arm, d in ks_.items()}
    pre = {arm: {k: abs(float(np.mean(list(v.values()))) - four[k]["kappa"]) for k, v in d.items()} for arm, d in full.items()}
    sw = {arm: {k: float(np.mean([abs(x - four[k]["kappa"]) for x in v.values()])) for k, v in d.items()} for arm, d in full.items()}
    pre["ZERO"] = sw["ZERO"] = {k: float(abs(f["kappa"])) for k, f in four.items()}
    out = {"cohort": {"N": len(four), "kappa": dict(collections.Counter(f["kappa"] for f in four.values())),
                      "truth_patterns_y0_yA_yB_yAB": dict(collections.Counter("".join(map(str, f["y"])) for f in four.values()))}}
    for name, e in (("preregistered_seed_mean_marginals", pre), ("published_seedwise_errors", sw)):
        prim = {"F3": _paired(e, "B-F3", "K-B"), "F5s": _paired(e, "B-F5s", "K-B")}
        h = p12._holm({t: v["p_raw"] for t, v in prim.items()})
        for t in prim:
            prim[t]["p_holm"] = h[t]
            prim[t]["verdict"] = ("CONFIRMED" if h[t] < 0.05 and prim[t]["mean_delta"] > 0 else
                                  "SIGNIFICANT_REVERSAL" if h[t] < 0.05 else "NOT_CONFIRMED")
        out[name] = {"primary": prim, "mae": {a: float(np.mean(list(v.values()))) for a, v in e.items()},
                     "mae_by_kappa": {a: {str(c): float(np.mean([v[k] for k in v if four[k]["kappa"] == c])) for c in (-1, 0, 1)
                                          if any(four[k]["kappa"] == c for k in v)} for a, v in e.items()},
                     "B_vs_zero": _paired(e, "ZERO", "K-B"), "B_vs_SF": _paired(e, "SF", "K-B")}
    mean_khat = {arm: {k: float(np.mean(list(v.values()))) for k, v in d.items()} for arm, d in full.items()}
    out["false_interaction_on_kappa0"] = {a: {"rate_nearest_integer_nonzero": float(np.mean([abs(v[k]) >= 0.5 for k in v if four[k]["kappa"] == 0])),
                                              "mean_abs_khat": float(np.mean([abs(v[k]) for k in v if four[k]["kappa"] == 0]))}
                                          for a, v in mean_khat.items()}
    out["by_family_preregistered"] = {t: {f: float(np.mean([pre[abl][k] - pre["K-B"][k] for k in pre["K-B"] if four[k]["family"] == f]))
                                          for f in sorted({x["family"] for x in four.values()})} for t, abl in (("F3", "B-F3"), ("F5s", "B-F5s"))}
    out["per_variable_bce_not_joint"] = _bce(snap, four)
    old = p12._rd("runs/p12/p12_4/FACTOR_TESTS.json")["primary"]
    out["published_reproduced"] = {t: abs(out["published_seedwise_errors"]["primary"][t]["mean_delta"] - old[t]["mean_delta"]) < 1e-12 and
                                   abs(out["published_seedwise_errors"]["primary"][t]["p_holm"] - old[t]["p_holm"]) < 1e-12 for t in ("F3", "F5s")}
    out["mean_khat_seed_mean"] = mean_khat
    out["per_root"] = {k: {"kappa": f["kappa"], "y": f["y"], "family": f["family"]} for k, f in four.items()}
    (OUT / "p13_0").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "p13_0" / "KAPPA_CORRECTED.json", out)
    return out


def _bce(snap, four):
    """Mean per-variable binary NLL over the four fixed-q0 bits (seed-mean marginals). NOT a joint likelihood."""
    v = collections.defaultdict(list)
    for arm in ARMS:
        for k, f in four.items():
            ps = [a["roots"][k]["marginals"] for a in snap["arms"].values() if a["arm"] == arm and a["roots"][k].get("marginals")]
            if len(ps) == 3:
                for q, y in zip(f["q"], f["y"]):
                    p = min(max(float(np.mean([m[q] for m in ps])), 1e-9), 1 - 1e-9)
                    v[arm].append(-math.log(p if y else 1 - p))
    return {a: float(np.mean(x)) for a, x in v.items()}


def _strict(r, k):
    """Exact D <-> scene-edit correspondence for one root: every parking subset of the pool is a planned item whose edit equals the
    parking map restricted to that subset, keyed by the same object ids, evaluated at the root's q0 (empty subset = the executed empty
    repair, i.e. the original task). Returns (subset -> query) or the failure reason."""
    import p10b_scenes as pb
    import itertools
    inv, pool = {v: kk for kk, v in r["ids"].items()}, list(r["parking"])
    byq = {it["query"]: it for it in r["items"]}
    lat = {}
    for n in range(len(pool) + 1):
        for sub in itertools.combinations(pool, n):
            roles = sorted(inv[o] for o in sub)
            ed = {o: r["parking"][o] for o in sub}
            q = pb._query_id(k, "ORDERED_TEACHER", []) if not sub else pb._query_id(k, "SCENE_TARGET_ONLY", ed)
            it = byq.get(q)
            if it is None:
                return None, "parking subset not in the frozen catalogue"
            if it.get("d_subset") is None or sorted(it["d_subset"]) != roles:
                return None, "subset label differs from the parking subset"
            if sub and (it["kind"] != "SCENE_TARGET_ONLY" or it["edit"] != ed):
                return None, "edit dict differs from the parking map"
            if not sub and (it["kind"] != "ORDERED_TEACHER" or it["sequence"]):
                return None, "original is not the empty fixed-q0 repair"
            lat[frozenset(pool.index(o) for o in sub)] = q
    return lat, None


def d_strict(cohort="p10b") -> dict:
    """D / D-pairless / geometry vs A / B / C / SF blocker attribution on roots whose whole parking lattice is exactly the scored
    scene-edit queries (_strict). Per-arm coverage and NO_PREDICTED_CLEARING_SET are reported; scores are on the same common roots,
    with a no-clearing-set choice scored as a miss (F1 0, exact 0), never as an empty blocker set; seed-level masks, metrics averaged."""
    import p11_closure as q
    snap, P, rec, dl, roots, get, heur = p12._cohort(cohort)
    inf = {k: dl[k] for k in roots if dl[k]["mask"] is not None and dl[k]["y0"] == 0 and dl[k]["n"] > 0}
    lat, why = {}, collections.Counter()
    for k in inf:
        L, w = _strict(P[k], k)
        (lat.__setitem__(k, L) if L else why.update([w]))
    preds, nopred, cover = collections.defaultdict(dict), collections.Counter(), collections.defaultdict(set)
    for n, a in snap["arms"].items():
        if a["arm"] not in ("A", "SF", "K-B", "K-C") or a.get("regime", "full") != "full":
            continue
        for k, L in lat.items():
            m = (get("arms", n, k) or {}).get("marginals") or {}
            if not all(x in m for x in L.values()):
                continue
            st = {s: m[x] for s, x in L.items()}
            pm = None if not any(p >= 0.5 for p in st.values()) else q._derived_mask(st, inf[k]["n"])
            nopred[a["arm"]] += pm is None
            preds[a["arm"]].setdefault(k, []).append(pm)
    for arm, d in preds.items():
        cover[arm] = {k for k, v in d.items() if len(v) == 3}
    for n, x in snap["d"].items():
        if x["lambda_B"] == snap["baselines"][f"{x['arm']}_lambda_B"]:
            thr = snap["baselines"][f"{x['arm']}_threshold"]
            for k in inf:
                v = get("d", n, k)
                preds[x["arm"]].setdefault(k, []).append([int(v["p_feasible"] < 0.5 and mm >= thr) for mm in v["marg"]])
    preds["geometry_heuristic"] = {k: [heur[k]] for k in inf}
    arms = ("D", "D-pairless", "geometry_heuristic", "K-B", "K-C", "A", "SF")
    common = sorted(set(lat).intersection(*[cover[a] for a in ("K-B", "K-C", "A", "SF")])) if lat else []
    allpred = [k for k in common if all(pm is not None for a in ("K-B", "K-C", "A", "SF") for pm in preds[a][k])]
    miss = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "exact": 0.0, "jaccard": 0.0}
    def score(arm, ks):
        return {k: {m: float(np.mean([(q._set_metrics(inf[k]["mask"], pm) if pm is not None else miss)[m] for pm in preds[arm][k]]))
                    for m in miss} for k in ks}
    agg = lambda per: {"roots": len(per)} | {m: float(np.mean([v[m] for v in per.values()])) if per else None for m in miss}  # noqa: E731
    out = {"cohort": cohort, "infeasible_complete_masks": len(inf), "strict_lattice_roots": len(lat), "strict_failures": dict(why),
           "coverage_full_lattice_3_seeds": {a: len(cover[a]) for a in ("K-B", "K-C", "A", "SF")},
           "NO_PREDICTED_CLEARING_SET_choices": dict(nopred), "common_N": len(common), "all_arms_predict_N": len(allpred),
           "common_proof_grounded_N": sum(inf[k]["provenance"] == "proof_grounded" for k in common)}
    for name, ks in (("common_conservative", common), ("common_all_arms_predict", allpred),
                     ("common_proof_grounded", [k for k in common if inf[k]["provenance"] == "proof_grounded"]),
                     ("common_operational", [k for k in common if inf[k]["provenance"] != "proof_grounded"])):
        per = {a: score(a, ks) for a in arms}
        out[name] = {"arms": {a: agg(per[a]) for a in arms},
                     "paired_f1_vs_D": {a: _paired({x: {k: v["f1"] for k, v in per[x].items()} for x in ("D", a)}, a, "D") for a in arms if a != "D"} if len(ks) > 1 else None}
    p12old = p12._rd(f"runs/p12/p12_6/D_SEMANTICS_{cohort}.json")["matched"]
    out["p12_published_matched_N"] = p12old["matched_infeasible_N"]
    cf.write_json(OUT / "p13_0" / f"D_STRICT_{cohort}.json", out)
    return out


# ------------------------------------------------------------------ P13-1: source-level factor audit (implementation, not utility)
GROUPS = {"F1_static": ("unary", "pairh"), "F2_order": ("pairo", "mix", "order_s"), "F2_C_gru": ("h0", "gru"), "F3_pair_scene": ("pair_scene",),
          "F4_pair_omit": ("pair_omit",), "F5_pair_cpl": ("cpl",), "F5q_HO": ("ho_u", "ho_s", "ho_q"), "J_cost": ("cost",), "vision_vproj": ("vproj",),
          "scene_unary": ("scene",), "shared_encoders": ("enc", "ctxn", "pooln", "act", "edit_proj", "edit_head", "typ")}


def _group(name):
    top = name.split(".")[0]
    return next((g for g, mods in GROUPS.items() if top in mods), "other")


def components(m, r, inst=None) -> dict:
    """Keyed energies split by named factor, rebuilt from the model's own modules on the instance structure of
    unique_factor_keyed.instances; the parts must sum to the instance energies exactly (checked by the caller / tests)."""
    import torch
    import unique_factor_keyed as ufk
    from abc_models import TYPES
    inst = inst or ufk.instances(m, r)
    R, sn = r["R"], inst["S"]["names"]
    ks = len(sn)
    m._memo = {}
    try:
        S = m.scene_block(R, sn, r["edits"])
        c, Z = m.ctxn(R.ctx), S["Z"]
        q2 = lambda W_, Zm: -0.5 * ((Zm @ W_) * Zm).sum(1)  # noqa: E731
        sc = {"scene_unary": -Z @ S["s"], "F3_pair_scene": q2(m._pairs(S["v"], c, [(0, k, "scene") for k in range(1, ks)]), Z),
              "F5_scene_scene": q2(m._pairs(S["v"], c, [(a, b, "couple") for a in range(1, ks) for b in range(a + 1, ks)]), Z)}
        sc["F5q_ho_scene"] = -m.ho_s(torch.cat([Z @ m.ho_u(S["v"]), c.expand(len(Z), -1)], 1))[:, 0] if m.couple == "full" else 0 * Z[:, 0]
        blocks = {}
        for q, b in inst["blocks"].items():
            qs = b["queries"]
            _, g, _ = m.order(R, list(inst["seq"][q]))
            vs = [g + m.typ(torch.tensor(TYPES["zR"]))] + [m.order(R, list(inst["seq"][o]))[1] + m.typ(torch.tensor(TYPES["zO"])) for o in qs[1:]]
            V, kq = torch.cat([S["v"], torch.stack(vs)]), len(qs)
            Zb = torch.tensor(list(__import__("itertools").product((0.0, 1.0), repeat=ks + kq)), dtype=torch.float64)
            blocks[q] = {"F4_pair_omit": q2(m._pairs(V, g, [(ks, ks + j, "omit") for j in range(1, kq)]), Zb),
                         "F5_scene_query": q2(m._pairs(V, g, [(a, ks, "couple") for a in range(ks)]), Zb),
                         "F5_omit_omit": q2(m._pairs(V, g, [(ks + a, ks + b, "couple") for a in range(1, kq) for b in range(a + 1, kq)]), Zb),
                         "F5q_ho_block": (-m.ho_q(torch.cat([Zb @ m.ho_u(V), g.expand(len(Zb), -1)], 1))[:, 0] if m.couple == "full" else 0 * Zb[:, 0])}
    finally:
        m._memo = None
    return {"scene": sc, "scene_E": S["E"], "blocks": blocks, "inst": inst}


def _structure(inst, m):
    ks = len(inst["S"]["names"])
    seqs = {q: inst["seq"][q] for q in inst["unary"]}
    by = collections.defaultdict(list)
    for q, s in seqs.items():
        by[tuple(sorted(s))].append(q)
    om = [len(b["queries"]) - 1 for b in inst["blocks"].values()]
    full, pairs = m.couple in ("full", "quadratic"), m.couple != "none"
    return {"scene_bits": ks - 1, "F3_z0_zS_pairs": (ks - 1) * pairs * hasattr(m, "pair_scene"), "F5_scene_scene_pairs": math.comb(ks - 1, 2) * full,
            "sequence_variables": len(seqs), "multi_move_variables": sum(len(s) >= 2 for s in seqs.values()),
            "F2_same_endpoint_order_pairs": sum(math.comb(len(v), 2) for v in by.values() if len(v) > 1),
            "F4_zR_zO_pairs": sum(om) * pairs * hasattr(m, "pair_omit"), "F5_scene_query_pairs": ks * len(seqs) * full,
            "F5_omit_omit_pairs": sum(math.comb(x, 2) for x in om) * full, "F5q_HO_instances": (1 + len(inst["blocks"])) * (m.couple == "full"),
            "max_variables_in_block": max([ks + 1 + x for x in om], default=ks), "omission_blocks": sum(x > 0 for x in om)}


def factor_audit(n_val=40) -> dict:
    """Implementation evidence per factor on real roots with the frozen P10c checkpoints: parameter counts, the exact energy
    decomposition (parts == instance energies), state-wise magnitude of every named term, activation counts, gradient reachability
    through the actual keyed training loss, keyed-vs-unkeyed instance differences, D pair activation, and J / F1 decision influence."""
    import os
    import torch
    os.environ.setdefault("P10C_OUT", "runs/p10c")
    import d_blockers as db
    import p10c_train_eval as pc
    import unique_factor as uf
    import unique_factor_keyed as ufk
    out = {"params": {}, "removed_vs_K-B": {}}
    for arm in ARMS:
        m = pc.build(arm)
        cnt = collections.Counter()
        for n, p in m.named_parameters():
            cnt[_group(n)] += p.numel()
        out["params"][arm] = {"total": sum(cnt.values())} | dict(cnt)
    kb = {n for n, _ in pc.build("K-B").named_parameters()}
    for arm in ARMS:
        names = {n for n, _ in pc.build(arm).named_parameters()}
        out["removed_vs_K-B"][arm] = sorted({n.split(".")[0] for n in kb - names}) + [f"+{x}" for x in sorted({n.split(".")[0] for n in names - kb})]
    for arm in ("D", "D-pairless"):
        out["params"][arm] = {"total": sum(p.numel() for p in db.ModelD(pair=arm == "D").parameters())}
    tv = pc.prepared("trainval")
    val = [r for r in tv if r["split"] == "validation"][:n_val]
    blind = pc.prepared("blind")
    ds = __import__("torch").load(p12.HOLD / "records.pt", weights_only=False)
    import abc7_train as t7
    hold = t7.prepare(ds)
    for r, rec in zip(hold, ds["roots"]):
        r["ids"], r["d"] = rec["audit"]["ids"], rec.get("d")
    cohorts = {"p10b_validation": val, "p10b_blind": blind, "p12_holdout": hold, "p10b_train": [r for r in tv if r["split"] == "train"]}
    m, _ = pc.load("F-K-B-s0")
    act, mag, maxerr, keydiff = {}, collections.defaultdict(lambda: collections.defaultdict(list)), 0.0, collections.Counter()
    with torch.no_grad():
        for cname, rs in cohorts.items():
            rows = []
            for r in rs:
                inst = ufk.instances(m, r)
                rows.append(_structure(inst, m))
                if cname == "p10b_train":
                    continue
                comp = components(m, r, inst)
                maxerr = max(maxerr, float((sum(comp["scene"].values()) - comp["scene_E"]).abs().max()))
                for q, b in comp["blocks"].items():
                    maxerr = max(maxerr, float((sum(b.values()) - inst["blocks"][q]["energy"].reshape(-1)).abs().max()))
                for k, e in comp["scene"].items():
                    mag[cname][k].append(float(e.std(unbiased=False)))
                for b in comp["blocks"].values():
                    for k, e in b.items():
                        if k != "F4_pair_omit" or b[k].abs().sum() > 0:
                            mag[cname][k].append(float(e.std(unbiased=False)))
                u = uf.instances(m, r)
                n_u = sum(len(b["queries"]) for b in u["blocks"].values())
                n_k = sum(len(b["queries"]) for b in inst["blocks"].values())
                keydiff[(cname, "keyed_differs")] += int(n_u != n_k or set(u["blocks"]) != set(inst["blocks"]))
            act[cname] = {"roots": len(rows)} | {k: {"total": int(sum(x[k] for x in rows)), "roots_active": int(sum(x[k] > 0 for x in rows))}
                                                 for k in rows[0]}
    out["activation_K-B"] = act
    out["energy_std_over_states_K-B_s0"] = {c: {k: {"mean": float(np.mean(v)), "n": len(v)} for k, v in d.items()} for c, d in mag.items()}
    out["decomposition_max_abs_error"] = maxerr
    out["keyed_vs_unkeyed_roots_differing"] = {f"{a}": v for (a, _), v in keydiff.items()}
    out["gradient_reachability"] = _grads(pc, val[:12])
    out["D_pair_activation"] = {c: {"roots_pool_ge2": sum(len((r.get("d") or {}).get("pool", [])) >= 2 for r in rs),
                                    "pair_instances": sum(math.comb(len((r.get("d") or {}).get("pool", [])), 2) for r in rs)} for c, rs in cohorts.items()}
    out["decision_influence"] = {c: _influence(c) for c in ("p10b_blind", "p12_holdout")}
    (OUT / "p13_1").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "p13_1" / "FACTOR_AUDIT.json", out)
    return out


def _grads(pc, roots):
    """Gradient norm per named group from one backward pass of the actual training objective (keyed unique-factor NLL + lambda_static
    static BCE + lambda_travel J) for every frozen B-family arm, and of the D NLL for D / D-pairless."""
    import torch
    import d_blockers as db
    import unique_factor as uf
    import unique_factor_keyed as ufk
    out = {}
    for arm in ("K-B", "K-C", "B-F2", "B-F3", "B-F4", "B-F5s", "B-F5q"):
        m, _ = pc.load(f"F-{arm}-s0")
        m.train()
        m.zero_grad()
        with ufk.installed():
            loss, rec = uf.total(m, roots)
        loss.backward()
        g = collections.defaultdict(float)
        for n, p in m.named_parameters():
            g[_group(n)] += float(p.grad.norm() ** 2) if p.grad is not None else 0.0
        out[arm] = {k: math.sqrt(v) for k, v in g.items()} | {"loss_terms": {k: v for k, v in rec.items() if not k.startswith("n_")}}
    for arm, pair in (("D", True), ("D-pairless", False)):
        m = db.ModelD(pair=pair).double()
        items = [(r["R"], r["d"]["pool"], r["d"]["y0"], r["d"]["mask"]) for r in roots if (r.get("d") or {}).get("y0") is not None]
        loss = torch.stack([db.nll(*m(R, pool), y0, b, 2.0) for R, pool, y0, b in items]).mean()
        loss.backward()
        out[arm + "_random_init"] = {n.split(".")[0]: float(p.grad.norm()) if p.grad is not None else 0.0 for n, p in m.named_parameters()
                                     if n.split(".")[0] in ("pairf", "unary", "feas")}
    return out


def _influence(cohort):
    """How often the second TOP1 key J (predicted travel) changes the choice among admitted, non-vetoed minimum-move candidates, and
    how often the energy key (the only TOP1 path of learned F1 E_static) is reached by exact (moves, J, C_d) ties. Frozen rows are used
    where stored (P12); P10b blind rows are re-scored deterministically with the frozen checkpoints (no fitting, no physical calls)."""
    import torch
    import p10_protocol as pp
    import p10c_train_eval as pc
    import p10b_dataset as pd
    import p9_l3 as l3
    import p9_l3c as l3c
    import unique_factor as uf
    import unique_factor_keyed as ufk
    from scene import scene_from_dict
    cfg = cf.load_config("config.toml")
    if cohort == "p10b_blind":
        snap, P = p12._rd("runs/p10d/predictions.json"), {}
        for b in pc.batches():
            P |= p12._rd(b / "plan.json")["roots"]
        rs = pc.prepared("blind")
    else:
        import abc7_train as t7
        snap, P = p12._rd(p12.HOLD / "PREDICTIONS_FROZEN.json"), p12.plans()
        ds = torch.load(p12.HOLD / "records.pt", weights_only=False)
        rs = t7.prepare(ds)
        for r, rec in zip(rs, ds["roots"]):
            r["ids"] = rec["audit"]["ids"]
    veto = {r["key"]: frozenset(c["query"] for c in r["cands"] if c["seq"] and pp.static_veto(
        scene_from_dict(P[r["key"]]["scene"]), [(r["ids"][i], l3.cell(d)) for i, d in c["seq"]], P[r["key"]]["goal_cell"], cfg)) for r in rs}
    out = {"vetoed_candidates": sum(len(v) for v in veto.values()), "roots_with_veto": sum(bool(v) for v in veto.values())}
    for arm in ("K-B", "K-C", "B-F3", "B-F5s"):
        c = collections.Counter()
        for s in (0, 1, 2):
            n = f"F-{arm}-s{s}"
            a = snap["arms"][n]
            m = pc.load(n)[0] if cohort == "p10b_blind" else None
            for r in rs:
                k = r["key"]
                if m is not None:
                    with torch.no_grad(), ufk.installed():
                        rows = l3c.deployed(m, r, uf.instances(m, r), a["tau"], a["threshold"])[1]
                else:
                    rows = a["roots"][k]["rows"]
                adm = [y for y in rows if y["query"] not in veto[k] and 1 / (1 + math.exp(-y["u"] / a["tau"])) >= a["threshold"]]
                c["choices"] += 1
                if not adm:
                    c["abstain"] += 1
                    continue
                mm = min(y["m"] for y in adm)
                tie = [y for y in adm if y["m"] == mm]
                withj = min(tie, key=lambda y: (y["J_pred"], y["C_d"], y["energy"], y["query"]))
                c["matches_frozen_top1"] += withj["query"] == (a["roots"]["blind"] if cohort == "p10b_blind" else a["roots"])[k]["top1"]
                c["J_active_ge2_min_moves"] += len(tie) > 1
                c["J_changes_choice"] += min(tie, key=lambda y: (y["C_d"], y["energy"], y["query"]))["query"] != withj["query"]
                c["F1_energy_key_reached"] += sum((y["J_pred"], y["C_d"]) == (withj["J_pred"], withj["C_d"]) for y in tie) > 1
        out[arm] = dict(c)
    return out


def joint_scene_nll() -> dict:
    """EXPLORATORY (post-hoc, disclosed): joint log-loss of the observed four fixed-q0 bits (z0, zS[A], zS[B], zS[A+B]) under each
    B-family model's root-scoped P_S, against the product of the same model's marginals and against A / SF (independent re-scoring,
    joint = product of marginals). Re-inference with frozen checkpoints only; proof-grounded four-tuples only."""
    import torch
    import p10b_dataset as pd
    import abc7_train as t7
    import p10c_train_eval as pc
    import unique_factor_keyed as ufk
    res = {}
    for cohort in ("p12_holdout", "p10b_blind"):
        if cohort == "p12_holdout":
            snap, P, four = p12_four_tuples()
            ds = torch.load(p12.HOLD / "records.pt", weights_only=False)
            rs = {r["key"]: r for r in t7.prepare(ds)}
        else:
            snap, rec, P = p12._rd("runs/p10d/predictions.json"), {}, {}
            for b in pc.batches():
                P |= p12._rd(b / "plan.json")["roots"]
                rec |= pd.records(b, ("blind",))
            rs, four = {r["key"]: r for r in pc.prepared("blind")}, {}
            for k, r in P.items():
                t = {it["token"]: it["query"] for it in r["items"]}
                if r["split"] != "blind" or not all(x in t for x in ("", "edit:A", "edit:B", "edit:A+B")):
                    continue
                qs = [t[""], t["edit:A"], t["edit:B"], t["edit:A+B"]]
                st = [rec.get(q, {}).get("teacher_status") for q in qs]
                if all(s in (V, C) for s in st):
                    y = [int(s == V) for s in st]
                    four[k] = {"q": qs, "y": y, "kappa": y[3] - y[1] - y[2] + y[0]}
        per = collections.defaultdict(lambda: collections.defaultdict(list))
        for arm in ARMS:
            for s in (0, 1, 2):
                n = f"F-{arm}-s{s}"
                a = snap["arms"][n]
                roots = a["roots"]["blind"] if cohort == "p10b_blind" else a["roots"]
                m = pc.load(n)[0] if arm not in ("A", "SF") else None
                for k, fo in four.items():
                    mg = roots[k]["marginals"]
                    lm = sum(math.log(min(max(mg[q] if y else 1 - mg[q], 1e-12), 1.0)) for q, y in zip(fo["q"], fo["y"]))
                    per[arm + "|product_of_marginals"][k].append(-lm)
                    if m is None:
                        continue
                    with torch.no_grad(), ufk.installed():
                        S = ufk.instances(m, rs[k])["S"]
                    idx = [S["queries"].index(q) for q in fo["q"]]
                    row = (S["Z"][:, idx] == torch.tensor(fo["y"], dtype=torch.float64)).all(1)
                    per[arm + "|joint_P_S"][k].append(-float(torch.logsumexp(S["logp"][row], 0)))
        e = {name: {k: float(np.mean(v)) for k, v in d.items()} for name, d in per.items()}
        out = {"N": len(four), "kappa": dict(collections.Counter(x["kappa"] for x in four.values())),
               "mean_nll": {name: float(np.mean(list(v.values()))) for name, v in e.items()},
               "mean_nll_by_kappa": {name: {str(c): float(np.mean([v[k] for k in v if four[k]["kappa"] == c])) for c in (-1, 0, 1)
                                            if any(four[k]["kappa"] == c for k in v)} for name, v in e.items()}}
        out["paired"] = {"B_joint_vs_B_product": _paired(e, "K-B|product_of_marginals", "K-B|joint_P_S"),
                         "B-F3_joint_vs_B_joint": _paired(e, "B-F3|joint_P_S", "K-B|joint_P_S"),
                         "B-F5s_joint_vs_B_joint": _paired(e, "B-F5s|joint_P_S", "K-B|joint_P_S"),
                         "B-F5q_joint_vs_B_joint": _paired(e, "B-F5q|joint_P_S", "K-B|joint_P_S"),
                         "SF_vs_B_joint": _paired(e, "SF|product_of_marginals", "K-B|joint_P_S")}
        res[cohort] = out
    cf.write_json(OUT / "p13_1" / "JOINT_SCENE_NLL_EXPLORATORY.json", res)
    return res


def keyed_erratum() -> dict:
    """Erratum to 0060 section 3: keyed vs unkeyed instantiation compared by F5 scene-query pair INSTANCES (unkeyed: every listed slot of
    every candidate block, with the parent's context and role; keyed: one per (scene bit, distinct query)), not by block counts."""
    import os
    import torch
    os.environ.setdefault("P10C_OUT", "runs/p10c")
    import abc7_train as t7
    import p10c_train_eval as pc
    import unique_factor as uf
    import unique_factor_keyed as ufk
    m, _ = pc.load("F-K-B-s0")
    hold = t7.prepare(torch.load(p12.HOLD / "records.pt", weights_only=False))
    out = {}
    with torch.no_grad():
        for c, rs in (("p10b_blind", pc.prepared("blind")), ("p12_holdout", hold)):
            n_u = n_k = diff = 0
            for r in rs:
                ku, kk = uf.instances(m, r), ufk.instances(m, r)
                ks = len(ku["S"]["names"])
                a, b = sum(ks * len(x["queries"]) for x in ku["blocks"].values()), ks * len(kk["blocks"])
                n_u, n_k, diff = n_u + a, n_k + b, diff + (a != b)
            out[c] = {"roots": len(rs), "roots_differing": diff, "scene_query_pairs_unkeyed": n_u, "scene_query_pairs_keyed": n_k}
    cf.write_json(OUT / "p13_1" / "KEYED_ERRATUM.json", out)
    return out
