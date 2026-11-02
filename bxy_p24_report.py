"""BXY-P24 post-evaluation reporting (read-only): machine-readable tables and figures from the sealed predictions, the collected teacher rows and
the single EVALUATION_P24.json. Written after the one-shot evaluation; it never calls the teacher, never re-scores, never writes into the P24 run."""
from __future__ import annotations

import collections
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_p23_engine as EN  # noqa: E402
import bxy_p24_confirm as C  # noqa: E402
import bxy_pmin_sidecar as S  # noqa: E402
import bxy_teacher as TT  # noqa: E402
from bxy_p11_viz import _arrows  # noqa: E402
from bxy_p12_viz import _clean  # noqa: E402
from bxy_p14_run import _swap  # noqa: E402
from bxy_p17_viz import AC  # noqa: E402
from bxy_pmin_viz import _panel  # noqa: E402

OUT = C.OUT
TAB = Path("runs/approach_b/bxy_p24_report_v1")
FIG = Path("visualizations/approach_b/bxy_p24_v1")
ARMS = C.ARMS
SHORT = {"D:XYQ-GEO-SYM": "D (X/Y, quadratic)", "E:XY-UNC-SA-GEO-SYM": "E (X/Y, uncoupled)", "A:DIRECT-GEO": "DIRECT-GEO",
         "G:XYQ-GEO-SYM-ORDINV": "G (order-invariant)"}
sig_seq = lambda s: [] if s == "empty" else [(a.split(">")[0], int(a.split(">")[1])) for a in s.split(".")]  # noqa: E731


def context() -> dict:
    """The exact per-root views evaluate() used (same rows filter), plus the raw teacher rows keyed by design key."""
    import torch
    ev = json.loads((OUT / "EVALUATION_P24.json").read_text())
    D = EN.design(OUT)
    rows = EN.rows(OUT, D)
    inp = torch.load(OUT / "INPUTS_P24.pt", weights_only=False)["roots"]
    preds = json.loads((OUT / "PREDICTIONS_P24.json").read_text())
    by = {}
    for k in D["root_order"]:
        rec = json.loads((OUT / "roots" / f"{k}.json").read_text())
        res = {r["design_key"]: r for (kk, _, _), r in rows.items() if kk == k and r["status"] in ("OBSERVED", "CENSORED")}
        sv, lab, e = C.view(OUT, k, rec, D, inp[k], res)
        by[k] = {"sv": sv, "lab": lab, "ev": e, "rec": rec, "res": res, "preds": preds[k]}
    return {"eval": ev["row"], "eval_sha256": C.sha_file(OUT / "EVALUATION_P24.json"), "by": by, "rows": rows,
            "gen": json.loads((OUT / "GENERATION.json").read_text())}


def _omission_sign(e, xi, yi):
    if xi is None and yi is None:
        return "UNOBSERVED"
    x, y = e["obs_x"].get(xi) if xi is not None else None, e["obs_y"].get(yi) if yi is not None else None
    if y == 0 and e["y_meta"][yi]["negative_kind"] == "CERTIFIED":
        return "NECESSARY_CERTIFIED"                                       # the edited scene without this object's move: target certified infeasible
    if x == 1 and y == 1:
        return "UNNECESSARY"
    if x == 0 or y == 0:
        return "NECESSARY_UNCERTIFIED"                                     # failed, but by NO_PLAN_FOUND / TIMEOUT (bounded planner)
    return "UNOBSERVED"


def shortest_verified(e, sv):
    ok = [j for j, c in enumerate(e["cands"]) if c["success"] == 1 and c["kind"] != "noop"]
    return min(ok, key=lambda j: (sv["cands"][j]["m"], sv["cands"][j]["sig"])) if ok else None


def tables(Cx) -> dict:
    E_, by, gen = Cx["eval"], Cx["by"], Cx["gen"]
    pr = E_["per_root"]
    cohort = collections.defaultdict(lambda: {"slots": 0, "accepted": 0, "rejected": 0})
    for a in gen["attempts"]:
        c = cohort[f"{a['spec']['family']}|K{a['spec']['K_intent']}"]
        c["slots"] += 1
        c["accepted" if a["accepted"] else "rejected"] += 1
    rej = collections.Counter(a["reject"].split(":")[0] for a in gen["attempts"] if not a["accepted"])
    kx = collections.Counter((i["K_intent"], i["K"], i["K_cert"] if i["certified"] else None, i["y0"]) for i in (pr[k]["info"] for k in pr))
    kx_rows = [{"K_intent": a, "verified_K": b, "K_cert": c, "y0": d, "roots": n} for (a, b, c, d), n in sorted(kx.items(), key=str)]
    INF = [k for k in pr if pr[k]["info"]["y0"] == 0]
    FEA = [k for k in pr if pr[k]["info"]["y0"] == 1]
    choice = {}
    for a in ARMS:
        z = collections.Counter()
        for k in INF:
            r, i = pr[k][a], pr[k]["info"]
            z["INF"] += 1
            z["success"] += r["success"]
            z["noop_on_INF"] += r["m"] == 0
            z["failed_repair"] += (r["m"] > 0 and not r["success"])
            if i["available"]:
                z["AVAIL"] += 1
                z["AVAIL_success"] += r["success"]
                z["AVAIL_shorter_than_K"] += 0 < r["m"] < (i["K"] or 0)
                z["AVAIL_longer_than_K"] += r["m"] > (i["K"] or 99)
        for k in FEA:
            z["FEA"] += 1
            z["FEA_unnecessary"] += pr[k][a]["false_repair"]
        choice[a] = dict(z)
    om, om_by_k = collections.Counter(), collections.defaultdict(collections.Counter)
    twins = collections.Counter()
    for k, v in by.items():
        e, sv = v["ev"], v["sv"]
        j = shortest_verified(e, sv)
        if j is not None and e["y0"] == 0:
            o = next((o for o in e["omissions"] if o["sig"] == sv["cands"][j]["sig"]), None)
            for t in (o["omit"] if o else []):
                s = _omission_sign(e, t["xi"], t["yi"])
                om[s] += 1
                om_by_k[f"K{e['verified_K']}"][s] += 1
        for g in e["order_groups"]:
            xs = {u["x"] for u in g["members"] if u["x"] is not None}
            if len(g["members"]) >= 2 and xs == {0, 1}:
                twins["discordant_groups"] += 1
                twins["discordant_certified_failure"] += any(u["x"] == 0 and u["negative_kind"] == "CERTIFIED" for u in g["members"])
        twins["roots_with_discordant"] += any(len(g["members"]) >= 2 and {u["x"] for u in g["members"] if u["x"] is not None} == {0, 1} for g in e["order_groups"])
    led = [json.loads(ln) for ln in (OUT / "LEDGER.jsonl").read_text().splitlines()]
    charge = collections.defaultdict(lambda: {"cpu_s": 0.0, "wall_s": 0.0, "events": 0})
    for x in led:
        if x["event"] in ("charge", "finish"):
            ph = x.get("phase") or "labelling_root"
            charge[ph]["cpu_s"] += x["cpu_s"]
            charge[ph]["wall_s"] += x.get("wall_s") or 0.0
            charge[ph]["events"] += 1
    capped = [x["root"] for x in led if x["event"] == "finish" and x.get("exit") not in (None, 0)]
    keep = ("populations", "underpowered", "arms", "primary", "secondary_K34", "order", "order_concordance_level", "strata_availability_conditioned",
            "coverage", "calibration_y0", "travel_matched_successes", "oracle_verify_first", "status_counts")
    return {"version": "BXY_P24_TABLES_V1", "source": {"evaluation_sha256": Cx["eval_sha256"], "seal_sha256": C.sha_file(OUT / "SEAL_P24.json"),
                                                      "generation_sha256": C.sha_file(OUT / "GENERATION.json")},
            "cohort": {"slots": gen["slots"], "accepted": gen["accepted"], "rejection_reasons": dict(rej), "by_family_K_intent": dict(cohort)},
            "K_crosstab": kx_rows, "choices": choice, "omission_signs_shortest_verified": {"all": dict(om), "by_verified_K": {k: dict(v) for k, v in om_by_k.items()}},
            "order_twins": dict(twins), "ledger_by_phase": {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in charge.items()},
            "roots_at_cpu_cap": capped, "evaluation": {k: E_[k] for k in keep}}


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def fig_endpoints(T):
    ev, pop = T["evaluation"], T["evaluation"]["populations"]
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.4), constrained_layout=True)
    for a_, (key, wk, title) in zip(ax[:2], (("U", "U_wilson", f"U: verified corrective success, all {pop['INF']} infeasible roots (primary)"),
                                             ("C", "C_wilson", f"C: availability-conditioned, {pop['AVAIL']} roots (consistency)"))):
        names = list(ARMS) + ["ANALYTIC_ACCESS", "NOOP"]
        for i, a in enumerate(names):
            s = ev["arms"][a]
            lo, hi = s[wk] if s[wk] else (s[key], s[key])
            col = AC.get(a, "#888")
            a_.plot([lo, hi], [i, i], color=col, lw=2.2, solid_capstyle="round")
            a_.plot(s[key], i, "o", color=col, ms=8, mec="white", mew=1.5)
            a_.text(hi + 0.01, i, f"{s[key]:.3f}", va="center", fontsize=8, color="#333")
        a_.set_yticks(range(len(names)), [SHORT.get(a, a.replace("_", " ").lower()) for a in names])
        a_.invert_yaxis()
        a_.set(xlim=(0, 1), xlabel="success rate (Wilson 95% CI)", title=title)
        _clean(a_)
    a_ = ax[2]
    for i, a in enumerate(ARMS):
        s = ev["arms"][a]
        a_.barh(i, s["unnecessary"], color=AC[a], height=0.55)
        a_.text(s["unnecessary"] + 0.005, i, f"{round(s['unnecessary'] * pop['FEA'])}/{pop['FEA']}", va="center", fontsize=8)
    a_.set_yticks(range(len(ARMS)), [SHORT[a] for a in ARMS])
    a_.invert_yaxis()
    a_.set(xlim=(0, 0.4), xlabel="share of initially feasible roots repaired anyway", title="unnecessary repairs on FEA (all neutral: target still reachable)")
    _clean(a_)
    fig.suptitle("BXY-P24 one-shot confirmation: 237 independent bxyg34confirm roots, frozen 15-member ensembles, single locked evaluation", x=0.01, ha="left")
    return _save(fig, "01_endpoints.png")


def fig_contrasts(T):
    ev = T["evaluation"]
    items = []
    for fam, d, ep in (("primary", ev["primary"], "U_unconditional"), ("primary (C check)", ev["primary"], "C_availability_conditioned"),
                       ("secondary K34", ev["secondary_K34"], "REP34_conditional"), ("order", ev["order"], "test")):
        for name, v in d.items():
            if isinstance(v, dict) and ep in v:
                items.append((f"{fam}: {name.replace('_', ' ')}", v[ep], v["label"]))
    fig, ax = plt.subplots(figsize=(11, 0.42 * len(items) + 1.2), constrained_layout=True)
    for i, (nm, r, lab) in enumerate(items):
        lo, hi = r.get("ci_holm") or r["ci95"]
        col = "#1baf7a" if lab == "IMPROVES" else "#555"
        ax.plot([lo, hi], [i, i], color=col, lw=2.4, solid_capstyle="round")
        ax.plot(r["diff"], i, "o", color=col, ms=7, mec="white", mew=1.3)
        ax.text(max(hi, 0.0) + 0.012, i, f"{r['diff']:+.3f}  p={r['p_two_sided']:.3g}  n={r['n']}  {lab}", va="center", fontsize=8, color="#333")
    ax.axvline(0, color="#222", lw=0.8)
    ax.axvline(0.10, color="#999", lw=0.8, ls=":")
    ax.set_yticks(range(len(items)), [i[0] for i in items], fontsize=8)
    ax.invert_yaxis()
    ax.set(xlim=(-0.15, 0.95), xlabel="paired difference (root-family bootstrap, B = 10,000; Holm CI where registered; dotted: +0.10 success-gain gate)")
    _clean(ax)
    ax.set_title("Locked contrasts: label from the registered rule (U authoritative; C must agree; unnecessary-repair guardrail)\n"
                 "O1 / O3: G is order-invariant, so its strict-order concordance is 0.5 by construction; O2 is the outcome-level order test", loc="left", fontsize=10)
    return _save(fig, "02_contrasts.png")


def fig_strata(T):
    st = T["evaluation"]["strata_availability_conditioned"]
    ks = [k for k in ("K1", "K2", "K3", "K4") if k in st]
    fig, ax = plt.subplots(figsize=(11, 4.2), constrained_layout=True)
    w = 0.2
    for j, a in enumerate(ARMS):
        for i, k in enumerate(ks):
            s = st[k][a]
            if s["success"] is None:
                continue
            x = i + (j - 1.5) * w
            ax.bar(x, s["success"], w * 0.92, color=AC[a], label=SHORT[a] if i == 0 else None)
            ax.plot([x, x], s["wilson"], color="#222", lw=0.8)
    ax.set_xticks(range(len(ks)), [f"verified {k}\nn = {st[k]['n']}" for k in ks])
    ax.set(ylim=(0, 1.05), ylabel="success given a verified repair exists (Wilson 95%)", title="Availability-conditioned success by verified K (descriptive strata)")
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper left")
    _clean(ax)
    return _save(fig, "03_strata_by_K.png")


def fig_funnel(T):
    coh, pop = T["cohort"], T["evaluation"]["populations"]
    fam = coh["by_family_K_intent"]
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.2), constrained_layout=True, gridspec_kw={"width_ratios": [1.3, 1]})
    names = list(fam)
    ax[0].barh(range(len(names)), [fam[n]["accepted"] for n in names], color="#2a78d6", label="accepted")
    ax[0].barh(range(len(names)), [fam[n]["rejected"] for n in names], left=[fam[n]["accepted"] for n in names], color="#c8c8c8", label="rejected (NO_VALID_LAYOUT; kept, not replaced)")
    for i, n in enumerate(names):
        ax[0].text(fam[n]["slots"] + 2, i, f"{fam[n]['accepted']}/{fam[n]['slots']}", va="center", fontsize=8)
    ax[0].set_yticks(range(len(names)), [n.replace("|", "  K_intent=").replace("K_intent=K", "K_intent=") for n in names], fontsize=8)
    ax[0].invert_yaxis()
    ax[0].set(xlabel="construction slots", title=f"440 predeclared slots -> {coh['accepted']} accepted roots")
    ax[0].legend(frameon=False, fontsize=8, loc="lower right")
    _clean(ax[0])
    st = [("roots", pop["roots"]), ("initially infeasible (INF)", pop["INF"]), ("with a verified repair (AVAIL)", pop["AVAIL"]),
          ("verified K3/K4 (REP34)", pop["REP34"]), ("initially feasible (FEA)", pop["FEA"])]
    ax[1].barh(range(len(st)), [s[1] for s in st], color=["#555", "#b4441c", "#2a78d6", "#1baf7a", "#999"])
    for i, (n, v) in enumerate(st):
        ax[1].text(v + 2, i, str(v), va="center", fontsize=9)
    ax[1].set_yticks(range(len(st)), [s[0] for s in st])
    ax[1].invert_yaxis()
    ax[1].set(xlabel="roots", title="Locked analysis populations (teacher-verified)")
    _clean(ax[1])
    return _save(fig, "04_cohort_populations.png")


def _row(v, side, i):
    keys = v["ev"]["x_keys"] if side == "x" else v["ev"]["y_keys"]
    return v["res"].get(keys[i]) if i is not None else None


def fig_choices(Cx, T, n=3):
    """Verified K4 / K3 roots where D and DIRECT-GEO choose differently: each arm's sealed choice and the teacher's physical outcome."""
    pr, by, E_ = T["evaluation"], Cx["by"], TT.env()
    per = Cx["eval"]["per_root"]
    dif = sorted((k for k in per if per[k]["info"]["available"] and per[k]["info"]["K"] in (3, 4)
                  and per[k]["D:XYQ-GEO-SYM"]["success"] != per[k]["A:DIRECT-GEO"]["success"]), key=lambda k: (-per[k]["info"]["K"], k))
    wins = {w: [k for k in dif if per[k]["D:XYQ-GEO-SYM"]["success"] == w] for w in (1, 0)}
    ks = wins[1][:n - 1] + wins[0][:1]                                     # both directions: D right / DIRECT wrong, and the reverse if it occurs
    if not ks:
        return None
    fig, ax = plt.subplots(len(ks), 3, figsize=(17, 5.3 * len(ks)), constrained_layout=True, squeeze=False)
    for row, k in zip(ax, ks):
        v = by[k]
        rec, sv, e = v["rec"], v["sv"], v["ev"]
        c0 = bd.cells0(rec)
        for a_, arm in zip(row[:2], ("D:XYQ-GEO-SYM", "A:DIRECT-GEO")):
            i = per[k][arm]["chosen"]
            c = sv["cands"][i]
            seq = sig_seq(c["sig"])
            xr = _row(v, "x", c["xi"])
            with _swap(S, "OUT", OUT):
                _panel(a_, E_, k, rec, {**c0, **dict(seq)}, f"{SHORT[arm]} (sealed) chooses {c['sig']} (m = {len(seq)})", q=TT.qref(rec),
                       x=xr if xr and xr.get("y") == 1 else None,
                       note=f"teacher: X = {e['obs_x'].get(c['xi'])}, Y = {e['obs_y'].get(c['yi'])} -> success = {per[k][arm]['success']}")
            if seq:
                _arrows(a_, rec, seq)
        j = shortest_verified(e, sv)
        c = sv["cands"][j]
        seq = sig_seq(c["sig"])
        xr, yr = _row(v, "x", c["xi"]), _row(v, "y", c["yi"])
        with _swap(S, "OUT", OUT):
            _panel(row[2], E_, k, rec, {**c0, **dict(seq)}, f"shortest verified repair {c['sig']} (verified K = {e['verified_K']}"
                   f"{', certified' if per[k]['info']['certified'] else ''})", x=xr, ywit=yr.get("target_witness") if yr else None,
                   note="recorded witnesses: relocations blue, connector to q_ref pink, target from q_ref green")
    fig.suptitle(f"P24 verified K3/K4 roots where D and DIRECT-GEO differ in outcome ({len(wins[1])} D-only successes, {len(wins[0])} DIRECT-only): "
                 "sealed choices vs physical teacher outcome", x=0.01, ha="left")
    return _save(fig, "05_choices_D_vs_DIRECT.png")


def storyboard(Cx, k, name, j=None):
    """One verified repair, step by step from the recorded witnesses: q0 scene, each relocation (robot not reset in between), the terminal connector
    to q_ref, then Y: the target from q_ref in the edited scene."""
    v, E_ = Cx["by"][k], TT.env()
    rec, sv, e = v["rec"], v["sv"], v["ev"]
    j = shortest_verified(e, sv) if j is None else j
    c = sv["cands"][j]
    seq = sig_seq(c["sig"])
    xr, yr, y0r = _row(v, "x", c["xi"]), _row(v, "y", c["yi"]), _row(v, "y", sv["cands"][0]["yi"])
    c0 = bd.cells0(rec)
    n = len(seq) + 3
    cols = min(n, 4)
    fig, ax = plt.subplots(-(-n // cols), cols, figsize=(5.0 * cols, 5.0 * -(-n // cols)), constrained_layout=True, squeeze=False)
    ax = ax.ravel()
    y0s = (y0r or {}).get("teacher_status", "unobserved")
    with _swap(S, "OUT", OUT):
        _panel(ax[0], E_, k, rec, c0, "0. initial scene, robot at q0", q=np.asarray(xr["q0"]),
               note=f"Y(empty) from q_ref: {y0s} -> target blocked")
        done = {}
        for t, st in enumerate(xr["steps"]):
            done[st["object"]] = st["dest"]
            _panel(ax[t + 1], E_, k, rec, {**c0, **done}, f"{t + 1}. relocate {st['object']} -> cell {st['dest']}",
                   partial=st["witness"], note=f"recorded witness of this relocation ({st['via']}); starts where step {t} ended (no reset)")
        _panel(ax[len(seq) + 1], E_, k, rec, {**c0, **dict(seq)}, f"{len(seq) + 1}. connector to q_ref (end of X prefix)", x=xr,
               note=f"X = {xr['y']} ({xr['teacher_status']})")
        _panel(ax[len(seq) + 2], E_, k, rec, {**c0, **dict(seq)}, f"{len(seq) + 2}. Y: target from q_ref in the edited scene", q=TT.qref(rec),
               ywit=yr.get("target_witness"), note=f"Y = {yr['y']} ({yr['teacher_status']}); success = X * Y = {xr['y'] * yr['y']}")
    for a_ in ax[n:]:
        a_.axis("off")
    fig.suptitle(f"{k}: verified repair {c['sig']} (verified K = {e['verified_K']}), every panel drawn from recorded teacher witnesses", x=0.01, ha="left")
    return _save(fig, name)


def write_all() -> dict:
    t0, w0 = time.process_time(), time.time()
    Cx = context()
    T = tables(Cx)
    TAB.mkdir(parents=True, exist_ok=True)
    (TAB / "P24_TABLES.json").write_text(json.dumps(T, indent=1, sort_keys=True, default=str))
    figs = [fig_funnel(T), fig_endpoints(T), fig_contrasts(T), fig_strata(T), fig_choices(Cx, T)]
    per = Cx["eval"]["per_root"]
    for K in (4, 3):
        k = min((k for k in per if per[k]["info"]["available"] and per[k]["info"]["K"] == K and per[k]["info"]["certified"]), default=None)
        if k:
            figs.append(storyboard(Cx, k, f"06_storyboard_K{K}_{k[-4:]}.png"))
    return {"tables": str(TAB / "P24_TABLES.json"), "figures": [f for f in figs if f], "cpu_s": round(time.process_time() - t0, 1), "wall_s": round(time.time() - w0, 1)}


if __name__ == "__main__":
    import os
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = "1"
    import torch
    torch.set_num_threads(1)
    print(json.dumps(write_all(), indent=1))
