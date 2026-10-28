"""Approach D G2a figures. Every robot drawn here is a STORED joint configuration rendered with viz.draw_robot (exactly the certifier's
collision bodies), and every shaded cell is the absolute swept set of that stored path (p14 swept_cells); nothing is a shifted or cartoon
sweep. Status colours always come with a written label."""
from __future__ import annotations

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
