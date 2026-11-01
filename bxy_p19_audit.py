"""BXY-P19 K3/K4 preflight audit (read-only; no teacher label, no optimizer step).
    python3 bxy_p19_audit.py reproduce | kgeom | caps | phases | order | power | matrix | all
reproduce  P17 evaluation re-run vs the committed EVALUATION_P17.json; P18 pooled rule applied read-only to the P17 OOF scores (diagnostic,
           NOT an estimate of the 15-checkpoint ensemble); checkpoint custody.
kgeom      per P16 root: the order-free analytic lower bound LB (min over finite pick x place modes of movable discs to remove, union model),
           the recorded greedy-order K_geom, and the CERTIFIED necessity bound K_cert: for every set R of K-1 movable discs, the real
           populated-scene screen with R removed is certified closed (all declared candidates fail with a definite collision / NO_IK) for the
           target pick or place. Monotonicity (removing discs only opens a screen, adding discs at destinations only closes it) makes
           K_cert >= K a sound bound on the relocations any successful repair needs, within the declared grasp family.
caps       for K_geom >= 3 roots, the full outcome-blind candidate list vs the 16-candidate / 44-query frozen design (truncation by kind).
phases     failure phases of intended repairs / prefixes by mechanism and K_geom (P16 labels, evaluator side).
order      strict order diagnostic on P17 OOF scores: true permutations of one action multiset, same endpoint, both F1-admissible, X discordant;
           certified-failure subset; |dP| <= 1e-8 is a tie (fixed before computing). The historical P17 metric is not changed.
power      paired-difference variance and simulated CI half-widths (corrects the P18 single-proportion 'worst case').
matrix     K0-K4 requirements-to-evidence matrix."""
from __future__ import annotations

import collections
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

import bxy_data as bd
import bxy_p16 as G

OUT = Path("runs/approach_b/bxy_p19_v1")
TIE = 1e-8
WAVES = ("wA", "wB", "wC")


# ------------------------------------------------------------------ certified screen closure (shared with P20)
def screen_cert(kind, s, oid="t0", dest=None):
    """(open candidate count, certified): certified = every failing declared candidate failed for a definite reason (collision / NO_IK)."""
    import motion as mo
    import skill as sk
    E = G.bd_2d.env()
    rob, p = E["robot"], sk.params(E["cfg"])
    o = s.get(oid)
    if kind == "pick":
        cs = sk.screen_pick(rob, mo.checkers(rob, s, oid, None, None, p["delta"], p["eps"]), o.xy_m, o.radius_m, p)
    else:
        d, local = s.lattice.center(dest), (rob.grasp_x, 0.0)
        cs = sk.screen_place(rob, mo.checkers(rob, s, oid, d, local, p["delta"], p["eps"]), d, local, 2 * o.radius_m, p)
    ok = sum(c.stage == "OK" for c in cs)
    return ok, ok == 0 and all(c.certified for c in cs if c.stage != "OK")


def removed_scene(rec, removed):
    """S0 with the discs in `removed` taken off the board (T, fixed and the other movables stay)."""
    from dataclasses import replace
    from scene import scene_from_dict
    s0 = scene_from_dict(rec["scene"])
    return replace(s0, objects=tuple(o for o in s0.objects if o.id not in set(removed)))


def k_cert(rec, k_max=4):
    """Largest k <= k_max such that every set of k-1 movable discs, removed, leaves the target pick or place certified closed (and the
    counts of real screens used). k = 0 if S0 itself is not certified closed."""
    mov = sorted(rec["roles"])
    goal, calls, best = rec["goal_cell"], 0, 0
    for k in range(1, k_max + 1):
        ok = True
        for R in itertools.combinations(mov, k - 1):
            s = removed_scene(rec, R)
            calls += 1
            _, cp = screen_cert("pick", s)
            if cp:
                continue
            calls += 1
            _, cg = screen_cert("place", s, dest=goal)
            if not cg:
                ok = False
                break
        if not ok:
            break
        best = k
    return best, calls


def lower_bound(rec):
    """Order-free analytic LB over the finite modes (union model) and the recorded greedy K_geom."""
    c0 = bd.cells0(rec)
    mov = {o: c0[o] for o in rec["roles"]}
    fixed = [c0[o] for o in rec["fixed_ids"]]
    req = G.requirements(mov, fixed, c0["t0"], rec["goal_cell"])
    return (req[0][0] if req else None), rec["construction"]["K_geom"]


def kgeom_audit() -> dict:
    t0 = time.process_time()
    rows = []
    for w in WAVES:
        S = {r["root"]: r for r in json.loads((G.wdir(w) / "SUMMARY.json").read_text())["rows"]}
        for k, rec in G.roots_of(w).items():
            lb, kg = lower_bound(rec)
            kc, calls = k_cert(rec, max(kg, 1) if kg else 1) if kg and kg >= 1 else (0, 0)
            r = S[k]
            rows.append({"root": k, "wave": w, "mechanism": rec["spec"]["mechanism"], "K_intent": rec["spec"]["K_intent"], "LB_union": lb, "K_geom": kg,
                         "K_cert": kc, "screens": calls, "y0": r["y0"], "verified_K": r["verified_K"],
                         "greedy_exceeds_LB": lb is not None and kg is not None and kg > lb})
    c = collections.Counter
    return {"rows": rows, "cpu_s": round(time.process_time() - t0, 1),
            "summary": {"K_geom_vs_K_cert": dict(c(f"{r['K_geom']}->{r['K_cert']}" for r in rows if r["K_geom"])),
                        "greedy_exceeds_LB": sum(r["greedy_exceeds_LB"] for r in rows),
                        "verified_and_cert": dict(c(f"vK{r['verified_K']}|cert{r['K_cert']}" for r in rows if isinstance(r["verified_K"], int) and r["verified_K"] >= 2))}}


# ------------------------------------------------------------------ catalogue / query caps
def cap_audit() -> dict:
    t0 = time.process_time()
    out = []
    for w in WAVES:
        D = json.loads((G.wdir(w) / "DESIGN.json").read_text())
        for k, rec in G.roots_of(w).items():
            if rec["construction"]["K_geom"] < 3:
                continue
            full = G.candidates(rec)
            kept = {c["sig"] for c in D["roots"][k]["catalogue"]}
            lost = [kind for seq, kind in full if bd.sig(seq) not in kept]
            out.append({"root": k, "K_geom": rec["construction"]["K_geom"], "generated": len(full), "kept": len(kept), "queries": len(D["roots"][k]["queries"]),
                        "truncated_kinds": dict(collections.Counter(lost))})
    tk = collections.Counter()
    for r in out:
        tk.update(r["truncated_kinds"])
    return {"rows": out, "truncated_kinds_total": dict(tk), "cpu_s": round(time.process_time() - t0, 1),
            "prefix_or_omission_truncated": sum(v for k, v in tk.items() if k.startswith(("prefix", "omission")))}


# ------------------------------------------------------------------ failure phases
def phase_audit() -> dict:
    by = collections.defaultdict(collections.Counter)
    for w in WAVES:
        for r in json.loads((G.wdir(w) / "SUMMARY.json").read_text())["rows"]:
            if not r["K_geom"]:
                continue
            key = f"{r['spec']['mechanism']}|K{r['K_geom']}"
            rep = next((x for x in r["rows"] if x["kind"] == "repair"), None)
            by[key]["roots"] += 1
            by[key]["verified_K>=K_geom" if isinstance(r["verified_K"], int) and r["verified_K"] >= r["K_geom"] else "no_verified_K_geom_repair"] += 1
            if rep:
                if rep["x"] == 0:
                    by[key][f"repair_X0:{(rep['x_phase'] or '').split(':')[0]}:{rep['x_neg']}"] += 1
                if rep["y"] == 0:
                    by[key][f"repair_Y0:{rep['y_neg']}"] += 1
                if rep["x"] == 1 and rep["y"] == 1:
                    by[key]["repair_11"] += 1
                if rep["x"] == 1 and (rep["x_phase"] or "") == "":
                    pass
            for x in r["rows"]:
                if x["x"] == 0 and (x["x_phase"] or "").startswith("relocation"):
                    by[key]["any_X0_relocation_index:" + x["x_phase"].split(":")[1]] += 1
    return {k: dict(v) for k, v in sorted(by.items())}


# ------------------------------------------------------------------ strict order diagnostic on P17 OOF
def _seq(xkey):
    sig = xkey.split(":", 3)[3]
    return [(a.split(">")[0], int(a.split(">")[1])) for a in sig.split(".")] if sig else []


def order_audit() -> dict:
    import bxy_p17 as M
    import bxy_p17_eval as E
    C = E.context()
    res = {}
    for arm in M.ARMS:
        if arm.startswith("A:"):
            continue
        stats = collections.defaultdict(lambda: {"pairs": 0, "concordant": 0.0, "ties": 0, "roots": set()})
        for s in M.SEEDS:
            for k, pr in C["oof"][(arm, s)].items():
                sv, lab, ev = C["by"][k]
                px = pr["vars"]["px"]
                pop = "OB" if ev["corpus"] in ("P15", "V21") else "PMIN"
                for g in ev["order_groups"]:
                    for u, v in itertools.combinations(g["members"], 2):
                        a, b = _seq(ev["x_keys"][u["xi"]]), _seq(ev["x_keys"][v["xi"]])
                        if u["x"] == v["x"] or len(a) != len(b) or sorted(a) != sorted(b) or a == b:
                            continue
                        pos, neg = (u, v) if u["x"] == 1 else (v, u)
                        d = px[pos["xi"]] - px[neg["xi"]]
                        for sub in ("all", "certified") if neg["negative_kind"] == "CERTIFIED" else ("all",):
                            st = stats[(pop, sub)]
                            st["pairs"] += 1
                            st["roots"].add(k)
                            if abs(d) <= TIE:
                                st["ties"] += 1
                                st["concordant"] += 0.5
                            elif d > 0:
                                st["concordant"] += 1
        res[arm] = {f"{p}|{sub}": {"pairs_x_seeds": v["pairs"], "roots": len(v["roots"]), "concordance": v["concordant"] / v["pairs"] if v["pairs"] else None,
                                   "ties": v["ties"]} for (p, sub), v in stats.items()}
    return res


# ------------------------------------------------------------------ paired power
def power_audit(B=4000, seed=0) -> dict:
    import bxy_p17_eval as E
    C = E.context()
    R_ = E.rules(C)
    T = E.tables(C, R_)
    keep = lambda k: C["corpus"][k] in ("P15", "V21")  # noqa: E731
    f = E.METRICS["succ_inf"]("RULE")
    out = {}
    rng = np.random.default_rng(seed)
    for a, b in (("D:XYQ-GEO-SYM", "A:DIRECT-GEO"), ("D:XYQ-GEO-SYM", "E:XY-UNC-SA-GEO-SYM")):
        da, db = E.seed_mean(T, a, f, keep), E.seed_mean(T, b, f, keep)
        d = np.array([da[k] - db[k] for k in sorted(set(da) & set(db))])
        sd = float(d.std(ddof=1))
        sim = {}
        for n in (40, 60, 80, 100, 150, 200):
            hw = [1.96 * rng.choice(d, n).std(ddof=1) / np.sqrt(n) for _ in range(B // 10)]
            sim[n] = {"half_width_mean": float(np.mean(hw)), "power_vs_observed_mean": float(np.mean([abs(m) > 1.96 * s / np.sqrt(n) for m, s in
                     ((x.mean(), x.std(ddof=1)) for x in (rng.choice(d, n) for _ in range(B // 10)))]))}
        out[f"{a} vs {b}"] = {"n": len(d), "mean": float(d.mean()), "sd_paired": sd, "nonzero_disagreement_rate": float(np.mean(np.abs(d) > 1e-12)),
                              "se_formula": "SE(mean D) = s_D / sqrt(n)", "simulated": sim,
                              "p18_claim_check": "1.96*0.5/sqrt(n) is the single-proportion bound, not a bound for paired D in [-1, 1] (|D| up to 1 gives SD up to 1)"}
    return out


# ------------------------------------------------------------------ reproduction
def reproduce() -> dict:
    import bxy_p17 as M
    import bxy_p17_eval as E
    import bxy_p18 as Z
    new = json.loads(json.dumps(E.evaluate(), sort_keys=True, default=str))
    old = json.loads((M.OUT / "EVALUATION_P17.json").read_text())
    new.pop("accounting"), old.pop("accounting")
    out = {"P17_identical": new == old, "differing": sorted(k for k in set(new) | set(old) if new.get(k) != old.get(k))}
    fz = json.loads((Z.OUT / "FROZEN_MODELS.json").read_text())
    C = E.context()
    T = E.tables(C, {(a, f): {"rule": fz["arms"][a]["rule"]["rule"]} for a in M.ARMS for f in range(M.FOLDS)})
    keep = lambda k: C["corpus"][k] in ("P15", "V21")  # noqa: E731
    diag = {}
    for a in M.ARMS:
        s = E.seed_mean(T, a, E.METRICS["succ_inf"]("RULE"), keep)
        u = E.seed_mean(T, a, E.METRICS["unnecessary"]("RULE"), keep)
        diag[a] = {"pooled_rule": fz["arms"][a]["rule"]["rule"], "succ_inf": float(np.mean(list(s.values()))), "unnecessary": float(np.mean(list(u.values()))),
                   "fold_rule_succ_inf": old["arms"]["OB"][a]["RULE"]["succ_inf"], "fold_rule_unnecessary": old["arms"]["OB"][a]["RULE"]["unnecessary"]}
    out["P18_pooled_rule_on_P17_OOF_diagnostic"] = diag
    out["note"] = ("OOF 3-seed scores with fold-specific inner rules (the P17 estimate) vs the same OOF scores under each arm's single pooled P18 rule. "
                   "Neither is an estimate of the frozen 15-checkpoint ensemble, whose members saw 12/15 of every development root.")
    return out


# ------------------------------------------------------------------ requirements matrix (K0-K4)
def matrix(kg) -> list:
    rows = [r for w in WAVES for r in json.loads((G.wdir(w) / "SUMMARY.json").read_text())["rows"]]
    vk = collections.Counter(str(r["verified_K"]) for r in rows)
    cert = collections.Counter(f"{r['verified_K']}" for r in kg["rows"] if isinstance(r["verified_K"], int) and r["verified_K"] >= 2 and r["K_cert"] >= r["verified_K"])
    M_ = []
    for K in range(5):
        M_.append({"item": f"K{K} verified (catalogue-relative, P16)", "count": vk.get(str(K), 0),
                   "certified_necessary": cert.get(str(K), 0) if K >= 2 else None,
                   "status": "PROVEN_BY_WITNESSES" if vk.get(str(K), 0) >= 12 else ("WEAK" if vk.get(str(K), 0) else "MISSING")})
    M_ += [{"item": "prefix lengths 1-6 labelled", "status": "lengths <= 5 only (P16 0123 §1)"},
           {"item": "strict same-endpoint permutation order twins", "status": "see ORDER_AUDIT.json"},
           {"item": "omissions of verified K>=2 repairs", "status": "59 omission Y labels, 16 differ (P16)"},
           {"item": "harmful edits", "status": "12 roots (P16)"}, {"item": "X/Y four cells", "status": "66/28/68/42 roots (P16)"},
           {"item": "matched success / travel", "status": "P17 figure 08"}, {"item": "independent test", "status": "PROPOSAL ONLY (P18)"}]
    return M_


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1]
    t0 = time.process_time()
    jobs = {"reproduce": ("REPRODUCTION.json", reproduce), "kgeom": ("KGEOM_AUDIT.json", kgeom_audit), "caps": ("CAP_AUDIT.json", cap_audit),
            "phases": ("PHASE_AUDIT.json", phase_audit), "order": ("ORDER_AUDIT.json", order_audit), "power": ("POWER_AUDIT.json", power_audit)}
    for name in (jobs if cmd == "all" else [cmd]):
        if name == "matrix":
            continue
        f, fn = jobs[name]
        t1 = time.process_time()
        r = fn()
        (OUT / f).write_text(json.dumps(r, indent=1, sort_keys=True, default=str))
        print(name, round(time.process_time() - t1, 1), "CPU-s")
    if cmd in ("matrix", "all"):
        (OUT / "REQUIREMENTS_MATRIX_K04.json").write_text(json.dumps(matrix(json.loads((OUT / "KGEOM_AUDIT.json").read_text())), indent=1))
    print("total", round(time.process_time() - t0, 1))
