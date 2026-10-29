"""Approach D G2a figures. Every robot drawn here is a STORED joint configuration rendered with viz.draw_robot (exactly the certifier's
collision bodies), and every shaded cell is the absolute swept set of that stored path (p14 swept_cells); nothing is a shifted or cartoon
sweep. Status colours always come with a written label."""
from __future__ import annotations

import collections
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

import ad_compile as ac  # noqa: E402
import ad_pilot as ap  # noqa: E402
import geometry as ge  # noqa: E402
import motion as mo  # noqa: E402
import viz  # noqa: E402

DST = Path("visualizations/approach_d/g2a")
SWEEP, PATH, SEED = "#9ec5f0", "#1f5fa8", "#7a52b3"
POL = ["REL_K1", "REL_3x2", "REL_6x1", "DIRECT_ORDER_K1", "DIRECT_ORDER_K6", "DIRECT_SPREAD_K6", "EXACT_CELL_K2", "UNION_ALL"]


def _key_frames(a):
    ph = [str(x) for x in a["phase"]]
    return [ph.index("close_attach"), ph.index("release")] if "close_attach" in ph else []


def _held(a, k):
    return ("held", 0.024, tuple(a["held_local"])) if 0 < k <= len(a["attached"]) and a["attached"][k - 1] else None


def _base(ax, robot, scene, title, sweep=(), src=None, dst=None):
    viz.draw_support(ax, scene, cell_ids=False)
    for c in sweep:
        ax.add_patch(Rectangle(((c % 8) * 0.08, (c // 8) * 0.08), 0.08, 0.08, fc=SWEEP, ec="none", alpha=0.55, zorder=1))
    viz.draw_objects(ax, scene, labels=False)
    for c, lab in ((src, "src"), (dst, "dst")):
        if c is not None:
            x, y = (c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08
            ax.add_patch(Rectangle(((c % 8) * 0.08, (c // 8) * 0.08), 0.08, 0.08, fill=False, ec=viz.COLORS["text"], lw=1.4, zorder=6))
            ax.text(x, (c // 8) * 0.08 + 0.004, lab, fontsize=6.5, ha="center", va="bottom", color=viz.COLORS["text"], zorder=7)
    ax.add_patch(Circle(robot.base, 0.012, fc=viz.COLORS["housing"], zorder=6))
    ax.set(xlim=(-0.26, 0.68), ylim=(-0.24, 0.69), aspect="equal", xticks=[], yticks=[])
    ax.set_title(title, fontsize=8.5, loc="left")


def _motion(ax, robot, a, color=PATH, frames=None, alpha=0.35, highlight=(), hl_frames=()):
    pts = np.array([ge.fk(robot, q)[0][-1] for q, _, _ in mo.samples(a, 160)])
    ax.plot(pts[:, 0], pts[:, 1], color=color, lw=1.4, zorder=8)
    for k in (frames if frames is not None else _key_frames(a)):
        viz.draw_robot(ax, robot, a["q"][k], float(a["gap"][k]), _held(a, k), alpha=alpha, zorder=5)
    for k in hl_frames:
        viz.draw_robot(ax, robot, a["q"][k], float(a["gap"][k]), _held(a, k), alpha=0.9, zorder=9, highlight=highlight)


def _tag(ax, text, status):
    ax.text(0.0, -0.025, text, transform=ax.transAxes, fontsize=7.2, va="top", ha="left", zorder=20, clip_on=False,
            bbox={"fc": "white", "ec": viz.COLORS[status], "lw": 1.2, "boxstyle": "round,pad=0.3"})


def figures(dst=DST) -> dict:
    import p14_sweep_index as sx
    import p15_lookup as pl
    dst.mkdir(parents=True, exist_ok=True)
    res = ap.rd(ac.OUT / "PILOT_ROWS.json")
    T = ac.load_catalog()
    cfg, robot, p = ac.setup()
    P = sx._plans()
    idx, _ = pl.index_v2()
    Q = [r for r in res["rows"] if r["qid"].startswith("Q")]
    scene = lambda r: ap.witness_scene({**r["witness"], "root": r["root"], "src": r["src"]}, P)[0]  # noqa: E731
    near = lambda c, x: max(abs(c // 8 - x // 8), abs(c % 8 - x % 8)) <= 2  # noqa: E731
    out = {}

    # (a) exact-cell witness completed offline; (b) genuine shifted transfer; (c) whole-arm collision; (d) no compiled template
    ex = next(r for r in Q if r["policies"].get("EXACT_CELL_K2", {}).get("status") == "SUCCESS")
    sh = sorted(((r, T[r["policies"][p_]["template_id"]]) for p_ in ("REL_3x2", "REL_6x1", "REL_K1") for r in Q
                 if r["policies"][p_]["status"] == "SUCCESS" and (_fam(T[r["policies"][p_]["template_id"]]) or {}).get("residual_m", 0) > 0.02),
                key=lambda x: x[0]["qid"] == ex["qid"])[0]                 # prefer a query other than panel (a)'s
    col = next((r, T[t], v) for r in Q for t, v in r["templates"].items() if not v["verified"] and v["rejection"]
               and v["rejection"]["verdict"] == ge.COLLISION and _fam(T[t]) is not None
               and not any(o in v["rejection"]["pair"] for o in ("finger", "palm"))
               and all(not near(c, r["src"]) and not near(c, r["dst"]) for c in _obstacle_cells(scene(r), v["rejection"]["pair"])))
    nt = next(r for r in Q if r["policies"]["DIRECT_ORDER_K6"]["reason"] == "NO_TEMPLATE")
    cat = ap.rd(ac.OUT / "catalog" / "CATALOG.json")
    fails = sorted({a["termination_reason"] for a in cat["attempts"] if a["origin"] == "DIRECT_OFFLINE:order" and (a["src"], a["dst"])
                    == (nt["src"], nt["dst"]) and not a["compiled"] and not a["termination_reason"].startswith("DUP")})
    fig, axs = plt.subplots(1, 5, figsize=(20, 5.4), constrained_layout=True)
    t = T[ex["policies"]["EXACT_CELL_K2"]["template_id"]]
    _base(axs[0], robot, scene(ex), f"(a) exact-cell witness, completed offline\n{ex['src']}->{ex['dst']}, held-out scene ({ex['root']})",
          t["swept"], ex["src"], ex["dst"])
    _motion(axs[0], robot, t["arrays"])
    _tag(axs[0], f"VERIFIED in held-out scene from q_home\nstored core kept verbatim + offline home connectors", "valid")
    r, t = sh
    lin = _fam(t)
    f, i = lin["ref"].rsplit("#", 1)
    se = next(e for e in idx.by_key[(lin["seed_src"], lin["seed_dst"])] if e["file"] == f and e["index"] == int(i))
    sa = idx.arrays(se)
    _base(axs[1], robot, ap.witness_scene(se, P)[0], f"(b1) relative seed: stored witness, OTHER cells\n{se['src']}->{se['dst']} in its own scene "
          f"({se['root']})", sorted(set().union(*map(set, se["swept"].values()))), se["src"], se["dst"])
    _motion(axs[1], robot, sa, SEED, frames=_key_frames(sa))
    _tag(axs[1], "pattern only: not executable at the query cells", "unresolved")
    _base(axs[2], robot, scene(r), f"(b2) compiled OFFLINE at the query cells\n{r['src']}->{r['dst']}, held-out scene ({r['root']})",
          t["swept"], r["src"], r["dst"])
    _motion(axs[2], robot, t["arrays"])
    sh_deg = [round(math.degrees(x)) for x in lin["grasp_shift_rad"]]
    _tag(axs[2], f"VERIFIED from q_home | base-rotation residual {lin['residual_m'] * 100:.1f} cm\nseed branches kept; grasp shift "
                 f"{sh_deg[0]}/{sh_deg[1]} deg", "valid")
    r, t, v = col
    rej, k = v["rejection"], v["rejection"]["segment"]
    body = rej["pair"].split("|")[0]
    _base(axs[3], robot, scene(r), f"(c) same local pattern, whole-arm collision\n{r['src']}->{r['dst']}, held-out scene ({r['root']})",
          t["swept"], r["src"], r["dst"])
    _motion(axs[3], robot, t["arrays"], frames=[], highlight=(body,), hl_frames=[k, k + 1])
    for c in _obstacle_cells(scene(r), rej["pair"]):
        axs[3].add_patch(Circle(((c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08), 0.03, fill=False, ec=viz.COLORS["invalid"], lw=2, zorder=12))
    _tag(axs[3], f"REJECTED by the frozen-trajectory certifier\n{rej['pair']} in phase '{rej['phase']}' (segment {k}); obstacle outside\n"
                 f"both 3x3/4x4 windows", "invalid")
    import p6_scenes as p6
    scr = p6.Screens(cfg, robot)
    _base(axs[4], robot, scene(nt), f"(d) no compiled template under the planner-order policy\n{nt['src']}->{nt['dst']}, held-out scene "
          f"({nt['root']})", (), nt["src"], nt["dst"])
    axs[4].add_patch(Circle(robot.base, scr.r0, fill=False, ec=viz.COLORS["muted"], ls="--", lw=1.1, zorder=4))
    viz.draw_robot(axs[4], robot, robot.q_home, robot.open_gap, alpha=0.5)
    why = "; ".join(f.replace("CONNECTOR_PREGRASP:", "pregrasp ") for f in fails)
    _tag(axs[4], f"FAILURE: NO_TEMPLATE (6/6 offline compiles: {why})\nruntime stops; no IK / planner rescue. Not impossibility:\n"
                 f"other declared grasp classes do compile here", "invalid")
    axs[4].text(robot.base[0] + scr.r0 * 0.75, robot.base[1] - scr.r0 * 0.8, "link-0 annulus", fontsize=6.5, color=viz.COLORS["muted"])
    p = dst / "G2a_cases.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    out["cases"] = {"path": str(p), "exact": ex["qid"], "shifted": sh[0]["qid"], "collision": col[0]["qid"], "probe": nt["qid"]}
    out["summary"] = str(summary_figure(dst))
    return out


def _fam(t):
    """The template's relative-family derivation (largest base-rotation residual if several seeds compile to it), else None."""
    fs = [d["lineage"] for d in t.get("derivations", []) if d["origin"] == "FAMILY_RETARGET"]
    return max(fs, key=lambda x: x["residual_m"]) if fs else None


def _obstacle_cells(scene, pair):
    ids = set(pair.split("|"))
    return [o.cell for o in scene.objects if o.id in ids]


def summary_figure(dst=DST) -> Path:
    """Left: physical outcome per runtime policy on the 36 dev queries (template available, success from q_home) next to G1's retrieval
    proxy. Right: why the remaining moves failed."""
    s = ap.rd(ac.OUT / "PILOT_SUMMARY.json")["relocation"]
    rows = [r for r in ap.rd(ac.OUT / "PILOT_ROWS.json")["rows"] if r["qid"].startswith("Q")]
    n = s["queries"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.0), constrained_layout=True, gridspec_kw={"width_ratios": [1.5, 1]})
    names = [p_ for p_ in POL if p_ in s["policies"]]
    y = np.arange(len(names))
    av = [s["policies"][p_]["with_template"] for p_ in names]
    ok = [s["policies"][p_]["success"] for p_ in names]
    a1.barh(y, av, height=0.62, color="#d9e3ef", label="template available (compiled)")
    a1.barh(y, ok, height=0.62, color=viz.COLORS["valid"], label="SUCCESS: frozen template certified in held-out scene")
    for yi, p_, o in zip(y, names, ok):
        a1.text(o + 0.4, yi, f"{o}/{s['policies'][p_]['queries']}", va="center", fontsize=8, color=viz.COLORS["text"])
    g1 = [("G1 pattern top-1 (proxy)", sum(r["g1"]["hit1_3x2"] for r in rows)), ("G1 pattern in 3x2 (proxy)", sum(r["g1"]["hitK_3x2"] for r in rows)),
          ("G1 pattern in 6x1 (proxy)", sum(r["g1"]["hitK_6x1"] for r in rows))]
    yy = np.arange(len(names), len(names) + len(g1)) + 0.6
    a1.barh(yy, [v for _, v in g1], height=0.62, color="none", ec=viz.COLORS["muted"], hatch="///", label="retrieval proxy (not physical)")
    for yi, (_, v) in zip(yy, g1):
        a1.text(v + 0.4, yi, f"{v}/{n}", va="center", fontsize=8, color=viz.COLORS["muted"])
    a1.set_yticks(list(y) + list(yy), names + [k for k, _ in g1], fontsize=8)
    a1.invert_yaxis()
    a1.set_xlim(0, n + 4)
    a1.set_xlabel(f"dev LOKO queries (n = {n}; EXACT_CELL_K2 only where exact-cell witnesses exist); <= 6 exact checks from q_home, "
                  f"zero IK / planner calls", fontsize=8)
    a1.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)
    a1.set_title("(a) physical outcome per runtime policy vs G1 retrieval proxy", fontsize=9, loc="left")
    for side in ("top", "right"):
        a1.spines[side].set_visible(False)
    reasons = sorted({k for p_ in names for k in s["policies"][p_]["reasons"]})
    left = np.zeros(len(names))
    shades = ["#e34948", "#f0a08f", "#eda100", "#8d8c88", "#3b4351"]
    for j, rs in enumerate(reasons):
        v = np.array([s["policies"][p_]["reasons"].get(rs, 0) for p_ in names])
        a2.barh(y, v, left=left, height=0.62, color=shades[j % len(shades)], label=rs, ec="white", lw=1)
        left += v
    a2.set_yticks(y, names, fontsize=8)
    a2.invert_yaxis()
    a2.set_xlabel("failed queries (finite-library failures,\nnot impossibility)", fontsize=8)
    a2.legend(fontsize=7, loc="lower right", frameon=False)
    a2.set_title("(b) failure reasons", fontsize=9, loc="left")
    for side in ("top", "right"):
        a2.spines[side].set_visible(False)
    p = dst / "G2a_pilot_summary.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


if __name__ == "__main__":
    print(json.dumps(figures(), indent=1))


# ------------------------------------------------------------------ G2b: multi-action chains and the controlled comparison
CONN = "#6f6f6f"


def _chain_panels(axs, robot, prov, row, title_prefix):
    """One panel per provider step: scene BEFORE the step, stored connectors (grey tool path, robot at their end nodes), the stored action
    (blue tool path, robot at grasp and release, its absolute swept cells), the exact start / end node ids."""
    import ad_provider as pv  # noqa: F401
    g, cells = prov.g, {o.id: o.cell for o in prov.s0.objects}
    for ax, st in zip(axs, row["log"]):
        s = prov.scene(cells)
        recs = st["steps"]
        act = next((i for k, i in recs if k == "action"), None)
        A = g.actions.get(act) if act else None
        _base(ax, robot, s, f"{title_prefix} step {row['log'].index(st) + 1}: {st['object']} -> {st['dest']}  [{st['status']}]",
              A["swept"] if A else (), cells.get(st["object"]), st["dest"])
        for k, i in recs:
            a = g.arrays[i]
            if k == "connector":
                pts = np.array([ge.fk(robot, qq)[0][-1] for qq, _, _ in mo.samples(a, 80)])
                ax.plot(pts[:, 0], pts[:, 1], color=CONN, lw=1.1, ls="--", zorder=7)
                viz.draw_robot(ax, robot, a["q"][-1], float(a["gap"][-1]), alpha=0.18, zorder=4)
            else:
                _motion(ax, robot, a)
        nodes = [g.connectors[i]["from"] if k == "connector" else g.actions[i]["from"] for k, i in recs[:1]] + \
                [g.connectors[i]["to"] if k == "connector" else g.actions[i]["to"] for k, i in recs]
        text = " -> ".join(f"{i.split(':')[0]}:{i.split(':')[1][:6]}" for _, i in recs) if recs else "no accepted record"
        if st["status"] == "SUCCESS":
            _tag(ax, f"stored records: {text}\nq: {' -> '.join(n[2:8] for n in nodes)}\norigins: {', '.join(A['origins'])}", "valid")
            cells = {**cells, st["object"]: st["dest"]}
        else:
            a0 = next((x for x in st["attempts"] if x.get("pair")), None)
            if a0:
                i = a0["action"]
                k = None
                aa = g.arrays[i]
                body = a0["pair"].split("|")[0]
                seg = next((j for j, ph in enumerate(aa["phase"]) if str(ph) == a0["phase"]), 0)
                _motion(ax, robot, aa, frames=[], highlight=(body,), hl_frames=[seg, seg + 1])
                for c in [o.cell for o in s.objects if o.id in a0["pair"].split("|")]:
                    ax.add_patch(Circle(((c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08), 0.03, fill=False, ec=viz.COLORS["invalid"], lw=2, zorder=12))
            rc = ", ".join(f"{k}: {v}" for k, v in sorted(collections.Counter(x["reason"] for x in st["attempts"]).items()))
            _tag(ax, f"FAILURE: {st['reason']}  ({st['checks']} exact checks)\nattempts: {rc}\n"
                     + (f"first collision: {a0['pair']} in '{a0['phase']}'" if a0 else ""), "invalid")
    return cells


def g2b_figures(dst=Path("visualizations/approach_d/g2b")) -> dict:
    import ad_g2b as g2
    import ad_provider as pv
    from scene import scene_from_dict
    dst.mkdir(parents=True, exist_ok=True)
    cfg, robot, _ = ac.setup()
    g = pv.Graph(g2.OUT / "catalog")
    P = g2.rd(g2.DEV_PLAN)["roots"]
    C = g2.rd(g2.OUT / "CHAINS.json")["rows"]
    out = {}
    for name, key in (("G2b_chain_success.png", "F12|EXACT+REL_6x1+CATALOG"), ("G2b_chain_failure.png", "F03|EXACT+REL_6x1")):
        row = C[key]
        s = scene_from_dict(P[row["root"]]["scene"])
        prov = pv.Precompiled(cfg, robot, s, P[row["root"]]["goal_cell"], g, lambda *a: [], 6)
        n = len(row["log"])
        fig, axs = plt.subplots(1, n + 1, figsize=(4.6 * (n + 1), 5.6), constrained_layout=True)
        _base(axs[0], robot, s, f"{row['fixture']} root {row['root']} (start {row['stratum']})\ninitial scene, robot at q_initial", (),
              s.get("t0").cell, P[row["root"]]["goal_cell"])
        viz.draw_robot(axs[0], robot, s.robot.q_rad, robot.open_gap, alpha=0.9)
        _tag(axs[0], f"original target t0 {s.get('t0').cell} -> goal {P[row['root']]['goal_cell']}\nsequence {row['sequence'] if isinstance(row['sequence'], list) else 'from declared candidate list'}"
                     f"\npolicy {row['policy']}; zero runtime IK / planner calls", "unresolved")
        _chain_panels(axs[1:], robot, prov, row, row["fixture"])
        if row.get("replay"):
            rp = row["replay"]
            axs[-1].text(0.98, 0.98, f"independent replay: {rp['status']}\n{rp['records']} stored records, hash {rp['trajectory_hash']}",
                         transform=axs[-1].transAxes, ha="right", va="top", fontsize=7.2, bbox={"fc": "white", "ec": viz.COLORS["valid"]})
        fig.savefig(dst / name, dpi=140)
        plt.close(fig)
        out[name] = key
    out["G2b_pilot.png"] = str(_pilot_figure(dst))
    return out


def _pilot_figure(dst):
    import ad_g2b as g2
    A = g2.rd(g2.OUT / "ANALYSIS.json")
    S, n = A["summary"], A["queries"]
    pols = ["EXACT_ONLY", "EXACT+REL_3x2", "EXACT+REL_6x1", "EXACT+GEOMETRY_6x1", "EXACT+RANDOM_6x1", "UNION_TRAVEL", "REL_6x1", "G2A_DIRECT_SPREAD_K6"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(17, 4.8), constrained_layout=True, gridspec_kw={"width_ratios": [1.6, 0.9, 1.0]})
    y = np.arange(len(pols))
    st = [S[f"{p}|K6|OFF|strict"]["success"] for p in pols]
    rl = [S[f"{p}|K6|OFF|relaxed"]["success"] for p in pols]
    a1.barh(y, rl, height=0.62, color="#9fd09f", label="ends at retreat node (return home optional)")
    a1.barh(y, st, height=0.62, color=viz.COLORS["valid"], label="home -> home (G2a contract)")
    for yi, a, b in zip(y, st, rl):
        a1.text(b + 0.4, yi, f"{a} / {b}", va="center", fontsize=8)
    a1.set_yticks(y, [p + (" *" if p == "G2A_DIRECT_SPREAD_K6" else "") for p in pols], fontsize=8)
    a1.invert_yaxis()
    a1.set_xlim(0, n + 5)
    a1.set_xlabel(f"dev relocation queries verified (n = {n}); <= 6 exact certifications, prefilter OFF\n* different template universe (G2a unseeded)",
                  fontsize=8)
    a1.legend(fontsize=7.5, loc="lower right", frameon=False)
    a1.set_title("(a) retrieval policies on one shared template universe", fontsize=9, loc="left")
    d = A["home_leg_diagnosis"]
    keys = [("verified_home_to_home", viz.COLORS["valid"]), ("exit_leg_only", "#9fd09f"), ("entry_leg_only", "#eda100"),
            ("entry_and_exit_legs", "#f0a08f"), ("core_fails", viz.COLORS["invalid"])]
    left = 0
    for k, c in keys:
        a2.barh([0], [d[k]], left=left, color=c, ec="white", height=0.5, label=f"{k.replace('_', ' ')} ({d[k]})")
        left += d[k]
    a2.set_yticks([])
    a2.set_xlabel(f"(query, template) checks in held-out scenes (n = {sum(d[k] for k, _ in keys)})", fontsize=8)
    a2.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.25), frameon=False)
    a2.set_title("(b) where G2a home->home templates fail\n(exact certifier per piece)", fontsize=9, loc="left")
    pp = ["EXACT+REL_6x1", "EXACT+REL_3x2", "REL_6x1", "REL_3x2"]
    x = np.arange(len(pp))
    for j, (m, c) in enumerate((("OFF", "#3b4351"), ("HARD", "#2a78d6"))):
        v = [S[f"{p}|K6|{m}|strict"]["checks"] for p in pp]
        a3.bar(x + (j - 0.5) * 0.36, v, width=0.34, color=c, label=f"{m}: exact certifications")
        for xi, p in zip(x, pp):
            a3.text(xi + (j - 0.5) * 0.36, S[f"{p}|K6|{m}|strict"]["checks"] + 2, str(S[f"{p}|K6|{m}|strict"]["success"]), ha="center", fontsize=8)
    a3.set_xticks(x, pp, fontsize=7.5, rotation=15)
    a3.set_ylabel("exact certifications (36 queries)")
    a3.legend(fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    a3.set_title("(c) prefilter OFF vs HARD (labels = successes;\nADVISORY = OFF)", fontsize=9, loc="left")
    for ax in (a1, a2, a3):
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    p = dst / "G2b_pilot.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


# ------------------------------------------------------------------ G3: D_CAUSAL_G3 figures (from saved traces; robots drawn from stored arrays)
def _g3_setup(root, cat="C3"):
    import ad_causal as C
    import ad_g2b as g2
    import ad_local as L
    import ad_provider as pv
    st = L.Stub(root)
    g = pv.Graph(L.OUT / "catalog", f"GRAPH_{cat}")
    ri, member = g2._ri()
    prov = pv.Precompiled(st.cfg, st.robot, st.s0, st.goal_cell, g, g2.Ranker(ri, member, g2._excl(root), **g2.POLICIES["EXACT+REL_6x1+CATALOG"]),
                          6, 2, "OFF", "g3-fig")
    return C, L, st, g, prov, C.Geo(g, L._catalog_all(), st)


def g3_figures(dst=Path("visualizations/approach_d/g3"), root="p13_2026216000", contrast="p13_2026219000") -> dict:
    import ad_causal as Cz
    import ad_runtime as ar
    dst.mkdir(parents=True, exist_ok=True)
    B = json.loads((Cz.OUT / "VIEW_B_C3.json").read_text())
    out = {}
    # ---- 01 pipeline on one real DEV root (D_CAUSAL_G3 trace)
    C, L, st, g, prov, geo = _g3_setup(root)
    cells0 = {o.id: o.cell for o in st.s0.objects}
    tr = B["rows"][root]["D_CAUSAL_G3"]["trace"]
    fr = next(t for t in tr if t["event"] == "frontier")
    dor = C.DOracle(st, fr["eligible"], 10 ** 6)
    d0 = dor.predict(cells0, st.s0.robot.q_rad)
    fig, axs = plt.subplots(1, 4, figsize=(22, 5.8), constrained_layout=True, gridspec_kw={"width_ratios": [1, 1, 1.1, 1.05]})
    _base(axs[0], st.robot, st.s0, f"(1) D on the ORIGINAL target t0 (learned)\np_T = {d0['p']:.3f} -> blocked; blocker marginals:", (),
          cells0["t0"], st.goal_cell)
    viz.draw_robot(axs[0], st.robot, st.s0.robot.q_rad, st.robot.open_gap, alpha=0.5)
    for o in st.s0.objects:
        if o.id in d0["marg"]:
            c = o.cell
            axs[0].text((c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08 + 0.045, f"{o.id}: {d0['marg'][o.id]:.2f}", ha="center", fontsize=9, weight="bold",
                        color=COL_G3["D"], zorder=20)
            if o.id in fr["frontier"]:
                axs[0].add_patch(Circle(o.xy_m, 0.034, fill=False, ec=COL_G3["D"], lw=2.5, zorder=19))
    _tag(axs[0], f"frontier (top-2 by D): {', '.join(fr['frontier'])}", "valid")
    _base(axs[1], st.robot, st.s0, "(2) Geometry proposes WHERE (non-learned)\nshade = share of stored T actions sweeping the cell", (), cells0["t0"],
          st.goal_cell)
    for c in range(64):
        v = geo.conflict(cells0, c)
        if v > 0:
            axs[1].add_patch(Rectangle(((c % 8) * 0.08, (c // 8) * 0.08), 0.08, 0.08, fc="#e34948", alpha=0.35 * v, ec="none", zorder=1))
    best = {}
    for c in fr["candidates"]:
        best[(c["object"], c["dest"])] = max(best.get((c["object"], c["dest"]), 0), c.get("p_after", 0))
    for (o, d), p in best.items():
        xy = ((d % 8 + 0.5) * 0.08, (d // 8 + 0.5) * 0.08)
        axs[1].add_patch(Circle(xy, 0.03, fill=False, ec=COL_G3["D"], lw=2, ls="--", zorder=12))
        axs[1].annotate("", xy, st.s0.get(o).xy_m, arrowprops=dict(arrowstyle="->", color="#7a7975", lw=1.2), zorder=11)
    _tag(axs[1], "proposals = scene-only slots with a stored relocation motion,\nranked by sweep conflict (evidence, never a veto)", "unresolved")
    cs = sorted(fr["candidates"], key=lambda c: -c.get("p_after", 0))
    labels = [f"{c['object']}->{c['dest']}  [{c['action'][2:8]}]" for c in cs]
    axs[2].barh(range(len(cs)), [c["p_after"] for c in cs], color=[COL_G3["D"] if c["object"] == fr["frontier"][0] else "#9ec5f0" for c in cs], height=0.6)
    axs[2].axvline(fr["p_before"], color="#7a7975", ls="--", lw=1)
    axs[2].text(fr["p_before"] + 0.01, len(cs) - 0.5, f"p_T now {fr['p_before']:.3f}", fontsize=8, color="#7a7975")
    axs[2].set_yticks(range(len(cs)), labels, fontsize=8)
    axs[2].invert_yaxis()
    axs[2].set_xlim(0, 1)
    axs[2].set_xlabel("D's predicted p_T for the ORIGINAL target after the hypothetical edit,\nat the stored motion's own end configuration q_end")
    axs[2].set_title("(3) D evaluates each counterfactual (learned, inferred)", fontsize=9.5, loc="left")
    axs[3].axis("off")
    lines = [("(4) Provider checks stored motions (physical, verified)", True)]
    for t in tr:
        if t["event"] == "certify" and t["depth"] == 0:
            lines.append((f"{t['object']} -> {t['dest']} [{t['action'][2:8]}]: {t['status']}" + (f" ({t['reason']})" if t["reason"] else ""), False))
        if t["event"] == "verify_T" and t["depth"] == 1:
            lines.append((f"after {', '.join(t['moved'])} moved: original T -> {t['status']} ({t['reason']})", False))
    r = B["rows"][root]["D_CAUSAL_G3"]
    lines += [("", False), (f"result: {r['status']} ({r['reason']}); {r['budget']['reloc']} relocation checks, {r['d_calls']} D calls", True),
              ("D's best edit (o00 out of the way) IS physically realisable", False), ("as a stored relocation, but no stored T action then certifies:", False),
              ("a motion-library limit, not a wrong diagnosis (historical", False), ("teacher: o00 -> 59 then T is VERIFIED).", False)]
    y = 0.98
    for t, b in lines:
        axs[3].text(0, y, t, fontsize=8.8, weight="bold" if b else "normal", va="top", transform=axs[3].transAxes)
        y -= 0.058
    fig.suptitle(f"G3 D_CAUSAL_G3 on DEV root {root}: learned diagnosis builds the frontier, geometry proposes, D scores counterfactuals, the "
                 "provider verifies (frozen catalog C3; zero runtime IK / planning)", fontsize=11, x=0.01, ha="left")
    p = dst / "01_causal_pipeline.png"
    fig.savefig(p, dpi=135)
    plt.close(fig)
    out["01"] = str(p)
    # ---- 02 one-scene D vs geometry contrast (candidate frontier differs)
    C, L, st2, g2_, prov2, geo2 = _g3_setup(contrast)
    cells = {o.id: o.cell for o in st2.s0.objects}
    fig, axs = plt.subplots(1, 2, figsize=(14, 6.4), constrained_layout=True)
    for ax, pol, col in ((axs[0], "D_CAUSAL_G3", COL_G3["D"]), (axs[1], "GEOM_CAUSAL", "#6f6f6f")):
        rr = B["rows"][contrast][pol]
        f0 = next(t for t in rr["trace"] if t["event"] == "frontier")
        _base(ax, st2.robot, st2.s0, f"{pol}: frontier {f0['frontier']} (eligible {f0['eligible']})", (), cells["t0"], st2.goal_cell)
        viz.draw_robot(ax, st2.robot, st2.s0.robot.q_rad, st2.robot.open_gap, alpha=0.45)
        for o in f0["frontier"]:
            ax.add_patch(Circle(st2.s0.get(o).xy_m, 0.034, fill=False, ec=col, lw=2.6, zorder=19))
        certs = [t for t in rr["trace"] if t["event"] == "certify" and t["depth"] == 0][:4]
        for j, t in enumerate(certs):
            d = t["dest"]
            xy = ((d % 8 + 0.5) * 0.08, (d // 8 + 0.5) * 0.08)
            ax.annotate("", xy, st2.s0.get(t["object"]).xy_m, arrowprops=dict(arrowstyle="->", color=col if t["status"] == "SUCCESS" else "#e34948",
                                                                               lw=1.6), zorder=12)
            ax.text(*xy, str(j + 1), fontsize=9, weight="bold", ha="center", va="center", color=col, zorder=13,
                    bbox=dict(boxstyle="circle,pad=0.15", fc="white", ec=col))
        txt = "\n".join(f"{j + 1}. {t['object']}->{t['dest']}: {t['status']}" + (f" ({t['reason']})" if t["reason"] else "") for j, t in enumerate(certs))
        sc = ", ".join(f"{c['object']} {c['mover_score']:.2f}" for c in {c["object"]: c for c in f0["candidates"]}.values()) if f0["candidates"] else ""
        _tag(ax, f"mover scores: {sc}\nfirst checks:\n{txt}\nresult: {rr['status']} ({rr['reason']})", "unresolved")
    fig.suptitle(f"G3, DEV root {contrast} (same universe, catalog, budget): D's blocker marginals and geometry's\n"
                 "stored-sweep relevance build DIFFERENT candidate frontiers", fontsize=11, x=0.01, ha="left")
    p = dst / "02_one_scene_trace.png"
    fig.savefig(p, dpi=135)
    plt.close(fig)
    out["02"] = str(p)
    out["03"] = str(_g3_ablation(dst, B))
    # ---- 04 failure case: D's best counterfactual realised, original T still not certifiable from stored motions
    cert = next(t for t in tr if t["event"] == "certify" and t["status"] == "SUCCESS")
    A = prov.g.actions[cert["action"]]
    cells1 = {**cells0, cert["object"]: cert["dest"]}
    q1 = prov.g.q[A["to"]]
    with ar.forbid("raise") as calls:
        gr = prov.goal(cells1, q1)
        p1 = dor.predict(cells1, q1)
    fig, axs = plt.subplots(1, 3, figsize=(19, 6.2), constrained_layout=True)
    _base(axs[0], st.robot, st.s0, f"(a) D's top edit, realised: stored motion {cert['action'][2:10]}\n{cert['object']} {cells0[cert['object']]} -> "
          f"{cert['dest']} (certified in the current scene)", A["swept"], cells0[cert["object"]], cert["dest"])
    _motion(axs[0], st.robot, prov.g.arrays[cert["action"]])
    _tag(axs[0], "VERIFIED stored relocation (core + stored connectors)", "valid")
    s1 = prov.scene(cells1)
    _base(axs[1], st.robot, s1, f"(b) after the edit: D predicts p_T = {p1['p']:.2f} for the ORIGINAL T\n(at the motion's real end configuration q_end)",
          (), cells1["t0"], st.goal_cell)
    viz.draw_robot(axs[1], st.robot, q1, st.robot.open_gap, alpha=0.8)
    _tag(axs[1], "inferred by D, NOT a certificate", "unresolved")
    att = next((a for a in gr["attempts"] if a.get("pair")), None)
    _base(axs[2], st.robot, s1, f"(c) stored original-T actions checked: {gr['status']} ({gr['reason']})\nreasons: {gr.get('reason_counts')}",
          prov.g.actions[att["action"]]["swept"] if att else (), cells1["t0"], st.goal_cell)
    if att:
        aa = prov.g.arrays[att["action"]]
        seg = next((j for j, ph in enumerate(aa["phase"]) if str(ph) == att["phase"]), 0)
        _motion(axs[2], st.robot, aa, frames=[], highlight=(att["pair"].split("|")[0],), hl_frames=[seg, seg + 1])
        _tag(axs[2], f"first rejected T action: {att['pair']} in phase '{att['phase']}'\nfinite-library failure, not physical impossibility", "invalid")
    fig.suptitle(f"G3 failure case ({root}): a causally sensible, physically realised edit, yet no stored T motion certifies afterwards "
                 f"(forbidden calls: {sum(calls.values())})", fontsize=11, x=0.01, ha="left")
    p = dst / "04_failure_case.png"
    fig.savefig(p, dpi=135)
    plt.close(fig)
    out["04"] = str(p)
    return out


COL_G3 = {"D": "#1baf7a"}


def _g3_ablation(dst, B):
    import ad_causal as Cz
    VA = {s: json.loads((Cz.OUT / f"VIEW_A_{s}.json").read_text()) for s in ("dev", "calib")}
    S = B["summary"]
    fig, axs = plt.subplots(1, 3, figsize=(19, 5.4), constrained_layout=True)
    x = np.arange(2)
    for j, (p, c) in enumerate((("D", COL_G3["D"]), ("geometry", "#9a9890"), ("uniform", "#c3c2b7"))):
        v = [VA[s]["edit_auroc"][p] for s in ("dev", "calib")]
        axs[0].bar(x + (j - 1) * 0.26, v, 0.24, color=c, label=p)
        for xi, vi in zip(x, v):
            axs[0].text(xi + (j - 1) * 0.26, vi + 0.01, f"{vi:.2f}", ha="center", fontsize=8.5)
    n = {s: VA[s]["edit_counts"]["verified"] + VA[s]["edit_counts"]["certified_infeasible"] for s in ("dev", "calib")}
    axs[0].set_xticks(x, [f"DEV (in D training)\n{n['dev']} decided edits", f"P16 calib (HELD OUT)\n{n['calib']} decided edits"])
    axs[0].set_ylim(0.4, 1.05)
    axs[0].set_ylabel("AUROC: does the score predict that the edit makes T feasible?")
    axs[0].legend(fontsize=8, frameon=False, loc="lower right")
    axs[0].set_title("(a) WHERE / WHETHER: counterfactual edit evaluation\n(saved labels, original q; UNKNOWN excluded)", fontsize=9.5, loc="left")
    rows = B["rows"]
    diff_set = diff_first = n_blk = 0
    elig = []
    for k, r in rows.items():
        fd = [t for t in r["D_CAUSAL_G3"]["trace"] if t["event"] == "frontier"]
        fg = [t for t in r["GEOM_CAUSAL"]["trace"] if t["event"] == "frontier"]
        if not fd:
            continue
        n_blk += 1
        elig.append(len(fd[0]["eligible"]))
        diff_set += set(fd[0]["frontier"]) != set(fg[0]["frontier"])
        a = next((t for t in r["D_CAUSAL_G3"]["trace"] if t["event"] == "certify"), {})
        b = next((t for t in r["GEOM_CAUSAL"]["trace"] if t["event"] == "certify"), {})
        diff_first += (a.get("object"), a.get("dest")) != (b.get("object"), b.get("dest"))
    vals = [("root frontier SET differs", diff_set), ("first checked candidate differs", diff_first),
            ("roots with <= 2 eligible movers\n(top-2 frontier = all movers)", sum(e <= 2 for e in elig))]
    axs[1].barh(range(3), [v for _, v in vals], color=[COL_G3["D"], "#86b6ef", "#c3c2b7"])
    for i, (_, v) in enumerate(vals):
        axs[1].text(v + 0.1, i, f"{v}/{n_blk}", va="center", fontsize=9)
    axs[1].set_yticks(range(3), [k for k, _ in vals], fontsize=8.5)
    axs[1].invert_yaxis()
    axs[1].set_xlim(0, n_blk + 1.5)
    axs[1].set_title(f"(b) WHICH: does D change what is explored? (D vs geometry,\n{n_blk} blocked DEV roots; eligible movers {min(elig)}-{max(elig)})",
                     fontsize=9.5, loc="left")
    pols = list(S)
    axs[2].bar(range(len(pols)), [S[p]["success"] for p in pols], color=[COL_G3["D"] if p.startswith("D") else "#9a9890" for p in pols], width=0.6)
    for i, p in enumerate(pols):
        axs[2].text(i, S[p]["success"] + 0.15, f"{S[p]['success']}/12\n{S[p]['reloc_certifications']} checks\n{S[p]['d_calls']} D calls", ha="center",
                    fontsize=7.8)
    axs[2].set_xticks(range(len(pols)), [p.replace("_", "\n") for p in pols], fontsize=8)
    axs[2].set_ylim(0, 6)
    axs[2].set_ylabel("DEV roots repaired end to end (stored motions, replayed)")
    axs[2].set_title("(c) WHETHER it executes: matched end-to-end (catalog C3)\nonly the directly feasible root succeeds -> catalog ceiling",
                     fontsize=9.5, loc="left")
    fig.suptitle("G3 ablation — engineering works; scientific advantage INCONCLUSIVE on repair success (motion-library ceiling), "
                 "positive on counterfactual evaluation", fontsize=11, x=0.01, ha="left")
    p = dst / "03_ablation.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p
