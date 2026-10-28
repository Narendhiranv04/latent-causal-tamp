"""P15 figures: lookup top-K certification curves, root-paired anytime success (incl. D inference), cost / status breakdowns, co-solved
lexicographic outcomes, and one case figure + GIF per selected root. Every drawn trajectory is a recorded / certified array of a plan
that passed the independent replay; failures are shown with their recorded reason, never with an invented motion."""
from __future__ import annotations

import collections
import json
from pathlib import Path

import numpy as np

OUT, DST = Path("runs/p15"), Path("visualizations/p15")
ARM_COL = {"D": "#2a6fdb", "D-norec": "#7fa7ec", "D-pairless": "#8e5bd0", "geometry": "#e07b00", "uniform": "#7a7975", "oracle": "#2e9e5b"}


def rd(p):
    return json.loads(Path(p).read_text())


def _ok(v):
    return bool(v["found"] and v["replay_success"])


def topk_curve() -> None:
    """Held-out (leave-one-root-out) fraction of queries with >= 1 VERIFIED candidate among the first K, per ranking."""
    import p6_viz as pv
    from viz import plt
    rows = rd(OUT / "lookup" / "TRANSFER.json")["rows"]
    f, ax = plt.subplots(figsize=(6.4, 4.2))
    K = range(1, 16)
    for name, col in (("combined", "#2a6fdb"), ("global", "#e07b00"), ("local", "#2e9e5b")):
        y = [np.mean([any(r["status"].get(e) == "VERIFIED" for e in r["ranking"][name][:k]) for r in rows]) for k in K]
        ax.plot(K, y, color=col, lw=2, marker="o", ms=4, label=f"{name} (top1 {y[0]:.2f})")
    ceil = np.mean([any(s == "VERIFIED" for s in r["status"].values()) for r in rows])
    ax.axhline(ceil, color="#7a7975", lw=1, ls="--")
    ax.text(15, ceil + 0.01, f"any candidate {ceil:.2f}", ha="right", fontsize=8, color="#52514e")
    ax.set(xlabel="certifier calls (top-K candidates tried)", ylabel="queries with a certified other-root motion", ylim=(0, 1),
           title=f"P15-2 sweep transfer, {len(rows)} held-out queries")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8)
    DST.mkdir(parents=True, exist_ok=True)
    pv.png(f, DST / "P15_lookup_topk.png", "P15-2 leave-one-root-out top-K certification by ranking")


def bench(cohort) -> None:
    """Anytime success vs CPU (root-paired common roots, D inference included), cost breakdown, status counts, co-solved outcomes."""
    import p6_viz as pv
    from viz import plt
    s = rd(OUT / "eval" / f"{cohort}_SUMMARY.json")
    runs = {a: rd(OUT / "search" / f"{cohort}_{a}.json") for a in s["arms"]}
    ks = s["common_roots"]
    f, ax = plt.subplots(1, 4, figsize=(24, 5.2))
    grid = np.linspace(0, 340, 341)
    for a, v in runs.items():
        y = [sum(_ok(v[k]) and v[k]["log"].get("anytime") and v[k]["log"]["anytime"][0]["cpu_s"] <= t for k in ks) for t in grid]
        ax[0].step(grid, y, where="post", color=ARM_COL[a], lw=2 if a in ("D", "geometry") else 1.2, label=f"{a} ({y[-1]}/{len(ks)})")
    ax[0].axvline(150, color="#7a7975", lw=1, ls=":")
    ax[0].set(xlabel="CPU-s per root (search incl. D inference; soft cap 150 s, dotted)", ylabel="roots solved (replay CLEAR)", title=f"{cohort}: anytime success, {len(ks)} common roots")
    ax[0].grid(alpha=0.25)
    ax[0].legend(frameon=False, fontsize=8, loc="lower right")
    arms = list(runs)
    x = np.arange(len(arms))
    m = np.array([[np.mean([runs[a][k]["used"][c] for k in ks]) for c in ("motion_checks", "online_moves", "goal_plans")] for a in arms])
    for j, (c, col) in enumerate(zip(("motion checks", "online moves (x10)", "goal plans (x10)"), ("#2a6fdb", "#e07b00", "#2e9e5b"))):
        ax[1].bar(x + (j - 1) * 0.27, m[:, j] * (1 if j == 0 else 10), 0.25, color=col, label=c)
    ax[1].set_xticks(x, arms, rotation=25, ha="right")
    ax[1].set(ylabel="mean calls per root", title="planner / certifier calls")
    ax[1].legend(fontsize=7, loc="lower right", framealpha=0.95, edgecolor="#d6d5d0")
    cpu = np.array([np.mean([runs[a][k]["cpu_s"] for k in ks]) for a in arms])
    dcpu = np.array([np.mean([runs[a][k]["d_cpu_s"] for k in ks]) for a in arms])
    ax[2].bar(x, cpu - dcpu, 0.6, color="#a7b4c2", label="search + certification")
    ax[2].bar(x, dcpu, 0.6, bottom=cpu - dcpu, color="#2a6fdb", label="D inference")
    tr = [sum(bool(runs[a][k]["truncated"]) for k in ks) for a in arms]
    for i, t in enumerate(tr):
        ax[2].text(i, cpu[i] + 1, f"{t} capped", ha="center", fontsize=7, color="#52514e")
    ax[2].set_xticks(x, arms, rotation=25, ha="right")
    ax[2].set(ylabel="mean CPU-s per root", title="runtime breakdown (soft cap 150 s)")
    ax[2].legend(fontsize=7, loc="lower right", framealpha=0.95, edgecolor="#d6d5d0")
    if "D" in runs and "geometry" in runs:
        co = [k for k in ks if _ok(runs["D"][k]) and _ok(runs["geometry"][k])]
        a_, b_ = [runs["geometry"][k]["plan"]["travel"] for k in co], [runs["D"][k]["plan"]["travel"] for k in co]
        cm = ["#2e9e5b" if runs["D"][k]["plan"]["moves"] == runs["geometry"][k]["plan"]["moves"] else "#e34948" for k in co]
        ax[3].scatter(a_, b_, c=cm, s=36, edgecolor="white", linewidth=0.8, zorder=3)
        lim = max(a_ + b_ + [1.0]) * 1.05
        ax[3].plot([0, lim], [0, lim], color="#7a7975", lw=1, ls="--")
        ax[3].set(xlim=(0, lim), ylim=(0, lim), xlabel="geometry: plan travel", ylabel="D: plan travel",
                  title=f"co-solved roots ({len(co)}): green = same move count")
        ax[3].grid(alpha=0.25)
    DST.mkdir(parents=True, exist_ok=True)
    pv.png(f, DST / f"P15_{cohort}_benchmark.png", f"P15-5 {cohort}: anytime success, calls, runtime, co-solved travel")
    f, ax = plt.subplots(figsize=(10, 4.6))
    cats = ["VERIFIED", "CERTIFIED_INFEASIBLE", "STATIC_INVALID", "UNKNOWN_PLANNER", "UNKNOWN_BUDGET"]
    cols = ["#008300", "#3b4a5a", "#a7b4c2", "#eda100", "#e34948"]
    bot = np.zeros(len(arms))
    for c, col in zip(cats, cols):
        v = np.array([sum(runs[a][k]["log"][kind].get(c, 0) for k in ks for kind in ("edges", "goals")) / len(ks) for a in arms])
        ax.bar(x, v, 0.6, bottom=bot, color=col, label=c, edgecolor="white", linewidth=1)
        bot += v
    ax.set(xticks=x, xticklabels=arms, ylabel="adjudications per root (edges + goals)", title=f"{cohort}: tri-state outcome counts")
    ax.legend(frameon=False, fontsize=8, ncol=3)
    pv.png(f, DST / f"P15_{cohort}_statuses.png", f"P15-5 {cohort}: VERIFIED / CERTIFIED / UNKNOWN counts per arm")


def case(cohort, key, guides=("D", "geometry")) -> dict:
    """Re-run the frozen search for `key` under each guide (same budget / cap), check the plan equals the benchmark record, then draw
    initial scores, retrieved modes, per-step occupancy with certified tool paths, cost, and a GIF of the replay-certified arrays."""
    import torch
    import geometry as ge
    import motion as mo
    import p14_eval as pe
    import p15_bench as pb
    import p15_lookup as pl
    import p15_search as ps
    import p6_scenes as p6
    import p6_viz as pv
    from viz import COLORS, plt
    pre = rd(OUT / "P15_PREREG.json")["search"]
    rs, P, D = pe._roots("test") if cohort == "RETRO" else pb._prosp_roots()
    idx, _ = pl.index_v2()
    root, rr = P[key], rs[key]
    movers = sorted({o for it in root["items"] if it["kind"] == "ORDERED_TEACHER" for o, _ in it["sequence"]})
    out = {}
    for g in guides:
        phys = ps.Physics(root, idx, "combined", False, pre["budget"], 150.0)
        gd = pb.Guide(g, root, rr, True)
        r = ps.search(phys, gd.order(phys, movers), movers, pb._slots(phys, idx), {o.id: o.cell for o in phys.s0.objects}, phys.s0.robot.q_rad)
        rec = rd(OUT / "search" / f"{cohort}_{g}.json")[key]
        same = r["found"] == rec["found"] and (not r["found"] or [(s["object"], s["dest"]) for s in r["plan"]["steps"]] == [(s["object"], s["dest"]) for s in rec["plan"]["steps"]])
        out[g] = {"phys": phys, "guide": gd, "res": r, "replay": ps.replay(phys, r["plan"]) if r["found"] else None, "matches_benchmark": same, "rec": rec}
    phys = out[guides[0]]["phys"]
    s0, goal, ids = phys.s0, phys.goal_cell, rr["ids"]
    cells0, q0 = {o.id: o.cell for o in s0.objects}, np.asarray(s0.robot.q_rad, float)
    sc = {}
    for g in guides:
        gd = out[g]["guide"]
        if g == "geometry":
            sc[g] = gd._geo(phys, cells0, q0, "t0", movers)
        elif g in ("D", "D-pairless"):
            p_ = gd._d(phys, cells0, q0, "t0", goal, movers)
            sc[g] = {o: (1 - p_["p_feasible"]) * m for o, m in zip(p_["pool"], p_["marg"])}
    n_steps = max((len(out[g]["res"]["plan"]["steps"]) for g in guides if out[g]["res"]["found"]), default=0)
    f, ax = plt.subplots(len(guides), 3 + n_steps, figsize=(5.2 * (3 + n_steps), 5.2 * len(guides)), squeeze=False)
    for gi, g in enumerate(guides):
        r = out[g]["res"]
        a0 = ax[gi][0]
        pv._panel(a0, phys.cfg, phys.robot, s0, goal, f"{key[-3:]} {root['family']} | {g}: initial blocker scores")
        for o in movers:
            x, y = s0.get(o).xy_m
            a0.text(x, y, o[1:], ha="center", va="center", fontsize=6, color="#0b0b0b")
        a0.text(0.02, 0.98, "blocker score (higher = moved first)\n" + "\n".join(f"{o}: {float(sc.get(g, {}).get(o, 0)):.2f}" for o in movers),
                transform=a0.transAxes, va="top", fontsize=8, color=ARM_COL[g], bbox=dict(fc="white", ec="#d6d5d0", alpha=0.9))
        if not r["found"]:
            why = collections.Counter({k: v for kind in ("edges", "goals") for k, v in r["log"][kind].items() if k != "VERIFIED"}).most_common(3)
            for j in range(1, 3 + n_steps):
                ax[gi][j].axis("off")
            ax[gi][1].text(0.0, 0.5, f"{g}: NO PLAN ({r['claim']})\ncapped: {out[g]['phys']._trunc}\nnon-verified outcomes: {why}\n"
                           f"calls: {out[g]['phys'].used}", fontsize=9, va="center")
            continue
        steps, recs = r["plan"]["steps"], r["plan"]["records"]
        st0 = steps[0]
        lk = ps.__dict__.get("sx") or __import__("p14_sweep_index")
        lk = lk.lookup_candidates(idx, st0["object"], cells0[st0["object"]], st0["dest"], s0, goal, s0.get(st0["object"]).radius_m)
        pv._panel(ax[gi][1], phys.cfg, phys.robot, s0, goal, f"first move {st0['object']}->{st0['dest']} via {st0['via']}: {lk.get('modes', 0)} modes")
        for mi, c in enumerate([c for c in lk.get("candidates", []) if c["rank_in_mode"] == 0][:3]):
            for cell in c["entry"]["_all"]:
                ax[gi][1].add_patch(plt.Rectangle(((cell % 8) * 0.08, (cell // 8) * 0.08), 0.08, 0.08, fc=["#2a6fdb", "#e07b00", "#2e9e5b"][mi], alpha=0.16, zorder=1))
            ax[gi][1].text(0.02, 0.98 - 0.06 * mi, f"mode {mi}: {c['support']} roots, travel {c['travel_J']:.2f}" + (" (used)" if st0.get("mode") == mi else ""),
                           transform=ax[gi][1].transAxes, va="top", fontsize=8, color=["#2a6fdb", "#e07b00", "#2e9e5b"][mi])
        rel, i, cells = [], 0, dict(cells0)
        for j, st in enumerate(steps):
            a = pe._merge(recs[i], recs[i + 1]) if st["via"] == "lookup" else recs[i]
            i += 2 if st["via"] == "lookup" else 1
            rel.append(a)
            cells[st["object"]] = st["dest"]
            sj = p6.moved(s0, {o: c for o, c in cells.items() if o != "t0" and c != cells0[o]})
            pv._panel(ax[gi][2 + j], phys.cfg, phys.robot, sj, goal, f"after step {j + 1}: {st['object']}->{st['dest']} ({st['via']}"
                      + (f", mode {st['mode']}" if st["via"] == "lookup" else "") + ")")
            pts = np.array([ge.fk(phys.robot, q)[0][-1] for q, _, _ in mo.samples(a, 60)])
            ax[gi][2 + j].plot(pts[:, 0], pts[:, 1], color=ARM_COL[g], lw=1.4)
        pts = np.array([ge.fk(phys.robot, q)[0][-1] for q, _, _ in mo.samples(recs[-1], 60)])
        ax[gi][2 + len(steps) - 1 if steps else 1].plot(pts[:, 0], pts[:, 1], color=COLORS["target"], lw=1.4)
        for j in range(2 + len(steps), 2 + n_steps):
            ax[gi][j].axis("off")
        ac = ax[gi][-1]
        tv = [__import__("ordered").joint_travel(phys.robot, [a])["J"] or 0.0 for a in rel] + [__import__("ordered").joint_travel(phys.robot, recs[-1:])["J"] or 0.0]
        ac.bar(range(len(tv)), tv, color=[ARM_COL[g]] * len(rel) + [COLORS["target"]])
        ac.set(xticks=range(len(tv)), xticklabels=[f"{s['object']}->{s['dest']}" for s in steps] + ["target"], ylabel="joint travel",
               title=f"{g}: {r['plan']['moves']} moves, travel {r['plan']['travel']:.2f}\n{r['claim'][:40]}  replay {'CLEAR' if out[g]['replay'] else 'FAIL'}")
        if out[g]["replay"]:
            frames = []
            for qq, gp, pos, mv in pv.trace_frames(phys.robot, s0, [(s["object"], s["dest"]) for s in steps], rel, recs[-1:], n_move=10, n_target=12):
                fg, a = plt.subplots(figsize=(5, 5))
                pv._panel(a, phys.cfg, phys.robot, s0, goal, f"{key[-3:]} {g}: {r['plan']['moves']} moves\nRECORDED / CERTIFIED arrays", q=qq, gap=gp, pos=pos, held=mv)
                pv._tag(a, "replayed certified motion", COLORS["valid"])
                frames.append(pv._rgb(fg))
            DST.mkdir(parents=True, exist_ok=True)
            pv.gif(DST / f"P15_{cohort}_case_{key[-3:]}_{g}.gif", frames, f"P15-5 {key} {g}: certified plan replay")
    DST.mkdir(parents=True, exist_ok=True)
    pv.png(f, DST / f"P15_{cohort}_case_{key[-3:]}.png", f"P15-5 {cohort} case {key}: guides {guides}")
    meta = {g: {"matches_benchmark": out[g]["matches_benchmark"], "found": out[g]["res"]["found"], "replay": out[g]["replay"],
                "steps": [(s["object"], s["dest"], s["via"]) for s in out[g]["res"]["plan"]["steps"]] if out[g]["res"]["found"] else None,
                "scores": {o: float(v) for o, v in sc.get(g, {}).items()}} for g in guides}
    import config as cf
    cf.write_json(DST / f"P15_{cohort}_case_{key[-3:]}.json", meta)
    return meta


# ------------------------------------------------------------------ Approach D G1: relative retrieval evidence (no adaptation, no certification)
PATCH_COL = {-1: "#52514e", 0: "#fcfcfb", 1: "#a7b4c2", 2: "#eb6834", 3: "#f6c7ad", 4: "#2a78d6"}


def _cellbox(ax, c, n, color, ls):
    """n x n window as stored: 3x3 centred on c, 4x4 anchored with c at local (1, 1)."""
    from matplotlib.patches import Rectangle
    r, k = divmod(c, 8)
    ax.add_patch(Rectangle(((k - 1) * 0.08, (r - 1) * 0.08), n * 0.08, n * 0.08, fill=False, ec=color, ls=ls, lw=1.3, zorder=12))


def _patches(ax, e, ref=None, title=""):
    """W3_src | W4_src || W3_dst | W4_dst as categorical grids; cells differing from the query's (ref) are crossed."""
    img = np.full((4, 17, 3), 1.0)
    for x0, k in ((0, "w3_src"), (4, "w4_src"), (9, "w3_dst"), (13, "w4_dst")):
        n = 3 if k.startswith("w3") else 4
        for i, v in enumerate(e[k]):
            r, c = divmod(i, n)
            img[r, x0 + c] = [int(PATCH_COL[v][j:j + 2], 16) / 255 for j in (1, 3, 5)]
            if ref is not None and ref[k][i] != v:
                ax.plot(x0 + c, r, "x", color="#d03b3b", ms=7, mew=1.6)
    ax.imshow(img, interpolation="nearest")
    ax.set_xticks([1, 5.5, 10, 14.5], ["3x3 src", "4x4 src", "3x3 dst", "4x4 dst"], fontsize=7)
    ax.set_yticks([])
    ax.set_title(title, fontsize=8)


def g1_figures(dst=Path("visualizations/approach_d/g1")) -> dict:
    import config as cf
    import geometry as ge
    import motion as mo
    import p14_sweep_index as sx
    import p15_lookup as pl
    import p6_viz as pv
    from viz import COLORS, plt
    dst.mkdir(parents=True, exist_ok=True)
    rows = rd(pl.G1_OUT / "RETRIEVAL_ROWS.json")["rows"]
    S, cov = rd(pl.G1_OUT / "RETRIEVAL_SUMMARY.json"), rd(pl.G1_OUT / "DOMAIN_COVERAGE.json")
    idx, _ = pl.index_v2()
    ri, P = pl.RelIndex(idx, pl.rel_cfg()), sx._plans()
    cfg = cf.load_config("config.toml")
    robot = ge.make_robot(cfg)
    by = {f"{e['file']}#{e['index']}": e for es in idx.by_key.values() for e in es}
    fp = {}
    for es in idx.by_key.values():
        for e in es:
            fp.setdefault(pl.json_fp(P[e["root"]]), set()).add(e["support_id"])
    pick = sorted((r for r in rows if r["proto"] == "LOKO" and r["variants"]["legacy_weights"]["hit1"]),
                  key=lambda r: (-r["variants"]["legacy_weights"]["abs_keys"], -r["variants"]["legacy_weights"]["modes"], r["query"]))[0]
    qe = by[pick["query"]]
    excl = frozenset(fp[pl.json_fp(P[qe["root"]])] | {qe["root"]})
    res = pl.lookup_relative(ri, qe, qe["radius"], excl, True)
    cands, seen = [], set()
    for c in res["candidates"]:
        if tuple(c["abs_key"]) not in seen and len(cands) < 3:
            seen.add(tuple(c["abs_key"]))
            cands.append(c)
    need = {(qe["file"], qe["index"])} | {(c["entry"]["file"], c["entry"]["index"]) for c in cands}
    prov = {}
    for p, a, r in sx.records():
        if (p["file"], p["index"]) in need:
            prov[(p["file"], p["index"])] = (sx.scene_at(r, p["prefix"]), r["goal_cell"], p["moved"], a)
            if len(prov) == len(need):
                break
    f, ax = plt.subplots(2, 1 + len(cands), figsize=(4.9 * (1 + len(cands)), 6.6), gridspec_kw={"height_ratios": [4, 1]}, squeeze=False)
    for j, (e, c) in enumerate([(qe, None)] + [(c["entry"], c) for c in cands]):
        s, goal, oid, a = prov[(e["file"], e["index"])]
        grasp = next(i for i, ph in enumerate(map(str, a["phase"])) if ph == "carry")
        hold = s.get(oid).xy_m
        if c is None:
            title = (f"QUERY (held out, LOKO): {e['src']}->{e['dst']}  delta {tuple(e['delta_rc'])}\nexact-cell witnesses and same-fingerprint roots "
                     "excluded")
        else:
            title = (f"RETRIEVED #{cands.index(c) + 1} (mode {c['mode']}): {e['src']}->{e['dst']}\nR={c['total']:.3f}  sim3={c['sim3']:.2f} "
                     f"sim4={c['sim4']:.2f}  base residual {c['residual_m']:.3f} m")
        pv._panel(ax[0][j], cfg, robot, s, goal, title, q=a["q"][grasp], gap=float(a["gap"][grasp]))
        pts = np.array([ge.fk(robot, qq)[0][-1] for qq, _, _ in mo.samples(a, 80)])
        ax[0][j].plot(pts[:, 0], pts[:, 1], color=COLORS["muted"] if c is None else COLORS["hypothetical"], lw=1.3, ls="--" if c is None else "-", zorder=11)
        for cell, col in ((e["src"], COLORS["hypothetical"]), (e["dst"], COLORS["target_edge"])):
            _cellbox(ax[0][j], cell, 3, col, "-")
            _cellbox(ax[0][j], cell, 4, col, ":")
        ax[0][j].annotate("", sx.center(e["dst"]), sx.center(e["src"]), arrowprops=dict(arrowstyle="-|>", color="#0b0b0b", lw=1.6), zorder=13)
        ax[0][j].plot(*hold, "o", ms=3, color="#0b0b0b", zorder=13)
        pv._tag(ax[0][j], "held-out witness: VERIFIED here, hidden from retrieval" if c is None else
                "own scene: VERIFIED | query scene: NOT adapted, NOT verified",
                COLORS["muted"] if c is None else COLORS["unresolved"], size=6.5)
        _patches(ax[1][j], e, None if c is None else qe, "query patches" if c is None else "patches (x = differs from query)")
    f.suptitle("Approach D G1: relative retrieval - same displacement and footprint, different absolute cells (3x3 solid / 4x4 dotted windows; "
               "blue = source, brown = destination)", fontsize=10)
    f.tight_layout()
    p1 = dst / "G1_relative_match.png"
    pv.png(f, p1, "Approach D G1: held-out query and top cross-location retrieved witnesses (retrieval only)")
    # coverage / ranking ablation / residual / family map
    f, ax = plt.subplots(1, 4, figsize=(22, 5.2))
    groups = [("dev-root candidate moves", cov["absolute"], cov["relative"], cov["moves"]),
              ("held-out LORO", S["LORO"]["absolute_coverage"], S["LORO"]["relative_coverage"], S["LORO"]["queries"]),
              ("held-out LOKO\n(new location)", S["LOKO"]["absolute_coverage"], S["LOKO"]["relative_coverage"], S["LOKO"]["queries"])]
    x = np.arange(len(groups))
    for k, (lab, col, i) in enumerate((("absolute (src, dst) key", "#a7a6a1", 1), ("relative (drow, dcol, footprint) family", "#2a78d6", 2))):
        v = [g[i] / g[3] for g in groups]
        ax[0].bar(x + (k - 0.5) * 0.36, v, 0.34, color=col, label=lab)
        for xx, g, vv in zip(x, groups, v):
            ax[0].text(xx + (k - 0.5) * 0.36, vv + 0.01, f"{g[i]}/{g[3]}", ha="center", fontsize=7)
    ax[0].set(xticks=x, ylim=(0, 1.12), ylabel="fraction with >= 1 indexed witness", title="a. candidate coverage (NOT motion availability)")
    ax[0].set_xticklabels([g[0] for g in groups], fontsize=8)
    ax[0].legend(fontsize=7, loc="upper left")
    L = S["LOKO"]
    names = list(pl.G1_VARIANTS)
    n = L["relative_coverage"]
    y = np.arange(len(names))
    ax[1].barh(y + 0.18, [L["variants"][v]["hit1"] / n for v in names], 0.34, color="#2a78d6", label="top-1 same pattern")
    ax[1].barh(y - 0.18, [L["variants"][v]["hitK"] / n for v in names], 0.34, color="#9ec2ee", label="any of shortlist (<= 6)")
    ax[1].axvline(L["chance_hit1"], color="#52514e", ls="--", lw=1)
    ax[1].text(L["chance_hit1"] + 0.01, len(names) - 0.4, f"random top-1 {L['chance_hit1']:.2f}", fontsize=7)
    ax[1].set(yticks=y, xlim=(0, 1), xlabel=f"fraction of {n} covered LOKO queries", title="b. ranking / shortlist ablation (pattern proxy)")
    ax[1].set_yticklabels(names, fontsize=8)
    ax[1].invert_yaxis()
    ax[1].legend(fontsize=7, loc="lower right")
    ax[2].barh(y, [L["variants"][v]["mean_res1_m"] for v in names], 0.5, color="#a7a6a1")
    ax[2].set(yticks=y, xlabel="mean base-rotation residual of top-1 (m)", title="c. robot-relative mismatch of the top-1 witness")
    ax[2].set_yticklabels(names, fontsize=8)
    ax[2].invert_yaxis()
    fam = ri.fam[sx.rel_key(qe["src"], qe["dst"], qe["radius"])]
    keys = sorted({(e["src"], e["dst"]) for e in fam})
    base = cfg["arm2d"]["base_xy_m"]
    rs = {k: sx.base_residual(base, *k, qe["src"], qe["dst"])[0] for k in keys}
    import matplotlib as mpl
    cm, nm = mpl.colors.ListedColormap(mpl.colormaps["Blues_r"](np.linspace(0, 0.7, 64))), mpl.colors.Normalize(0, max(rs.values()))
    for r_ in range(9):
        ax[3].plot([0, 0.64], [r_ * 0.08] * 2, color="#d6d5d0", lw=0.6)
        ax[3].plot([r_ * 0.08] * 2, [0, 0.64], color="#d6d5d0", lw=0.6)
    for k in keys:
        ax[3].annotate("", sx.center(k[1]), sx.center(k[0]), arrowprops=dict(arrowstyle="-|>", color=cm(nm(rs[k])), lw=2.2 if k == (qe["src"], qe["dst"]) else 1.4))
    ax[3].plot(*base, "s", color="#22262e", ms=9)
    ax[3].text(base[0] + 0.02, base[1], "robot base", fontsize=7, va="center")
    ax[3].set(xlim=(-0.2, 0.66), ylim=(-0.02, 0.66), aspect="equal", title=f"d. family {tuple(qe['delta_rc'])}: {len(keys)} absolute keys\n(thick = query; colour = base residual)")
    f.colorbar(mpl.cm.ScalarMappable(nm, cm), ax=ax[3], fraction=0.04, label="residual (m)")
    f.suptitle("Approach D G1 retrieval evidence - real witnesses, held out by root and geometry fingerprint; no motion adapted or certified", fontsize=10)
    f.tight_layout()
    p2 = dst / "G1_coverage_ablation.png"
    pv.png(f, p2, "Approach D G1: coverage, ranking ablation, residuals and a relative family map")
    return {"match": str(p1), "summary": str(p2), "query": pick["query"], "candidates": [f"{c['entry']['file']}#{c['entry']['index']}" for c in cands]}
