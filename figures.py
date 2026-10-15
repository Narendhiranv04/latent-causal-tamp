"""G1 stage figures and animations, built only from recorded results (Guide v1.6 §3).

Split from viz.py (size): viz.py holds drawing primitives and the G0 overview; this
module composes G1 figures and GIFs. Every robot pose drawn is either a screened
candidate pose or a configuration on a stored joint-linear segment (the executed
path itself); object poses follow from the phase context and the attachment.
"""
from __future__ import annotations

import math

import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle, Wedge
from PIL import Image

import geometry as ge
import motion as mo
import planner as pn
import skill as sk
import viz
from viz import COLORS, plt

STATUS = {"VERIFIED_FEASIBLE": ("VERIFIED", COLORS["valid"]),
          "CERTIFIED_INFEASIBLE": ("INFEASIBLE", COLORS["invalid"]),
          "UNRESOLVED": ("UNRESOLVED", COLORS["unresolved"])}


# ------------------------------------------------------------------ panels
LIMITS = {"grid": ((-0.56, 0.68), (-0.06, 0.80))}  # audit view: support, base and home pose


def scene_panel(ax, scene, cfg, title: str, hide=(), limits="robot"):
    lim = (cfg["render"]["overview_xlim_m"], cfg["render"]["overview_ylim_m"]) if limits == "robot" \
        else LIMITS[limits]
    ax.set(xlim=lim[0], ylim=lim[1], aspect="equal", xlabel="x [m]", ylabel="y [m]")
    ax.set_title(title, fontsize=9, loc="left")
    ax.tick_params(labelsize=7)
    viz.draw_support(ax, scene, cell_ids=False)
    for o in scene.objects:
        if o.id not in hide:
            fc, ec = ((COLORS["target"], COLORS["target_edge"]) if o.kind == "target"
                      else (COLORS["obstacle"], COLORS["obstacle_edge"]))
            ax.add_patch(Circle(o.xy_m, o.radius_m, fc=fc, ec=ec, lw=0.8, zorder=3))


def status_tag(ax, status: str, text: str = "", loc=(0.02, 0.02)):
    tag, color = STATUS[status]
    ax.text(*loc, f"{tag}  {text}".strip(), transform=ax.transAxes, fontsize=8, color="white",
            weight="bold", va="bottom", bbox=dict(fc=color, ec="none", pad=3), zorder=20)


def task_frame(ax, robot, scene, cfg, arrays, frames, k: int, title: str, status: str, dest_xy):
    """Robot, target and traces at frame k of a recorded task trajectory."""
    t = next(o for o in scene.objects if o.kind == "target")
    scene_panel(ax, scene, cfg, title, hide=(t.id,))
    ax.add_patch(Circle(dest_xy, t.radius_m, fc="none", ec=COLORS["target_edge"], ls="--", lw=1.0))
    tcp = np.array([ge.fk(robot, f[0])[0][3] for f in frames[:k + 1]])
    obj = np.array([mo.target_xy(robot, arrays, f[2], f[0], t.xy_m) for f in frames[:k + 1]])
    ax.plot(tcp[:, 0], tcp[:, 1], color=COLORS["hypothetical"], lw=1.0, zorder=6)
    ax.plot(obj[:, 0], obj[:, 1], color=COLORS["target"], lw=1.4, zorder=6)
    q, gap, phase = frames[k]
    viz.draw_robot(ax, robot, q, gap, zorder=8)
    ax.add_patch(Circle(obj[-1], t.radius_m, fc=COLORS["target"], ec=COLORS["target_edge"], zorder=9))
    ax.text(0.98, 0.98, phase.upper(), transform=ax.transAxes, ha="right", va="top", fontsize=9,
            weight="bold", bbox=dict(fc="white", ec=COLORS["muted"], pad=2), zorder=20)
    status_tag(ax, status)


def keyframe_panel(ax, robot, scene, cfg, arrays, title: str, status: str, dest_xy):
    """Whole task in one panel: TCP/object traces plus ghosts at phase ends."""
    frames = mo.samples(arrays, 240)
    task_frame(ax, robot, scene, cfg, arrays, frames, len(frames) - 1, title, status, dest_xy)
    phase = arrays["phase"]
    for name, alpha in (("approach", 0.35), ("carry", 0.55)):
        last = int(np.flatnonzero(phase == name)[-1]) + 1
        held = (None, 0.024, tuple(arrays["held_local"])) if name == "carry" else None
        viz.draw_robot(ax, robot, arrays["q"][last], arrays["gap"][last], held=held, alpha=alpha, zorder=7)


# ------------------------------------------------------------------ figures
def audit_figure(rows: list[dict], scene, robot, cfg, n_dirs: int):
    """64-cell reachability: complete-skill status and the candidate breakdown."""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12.5))
    counts = {s: sum(r["status"] == s for r in rows) for s in STATUS}
    short = {"VERIFIED_FEASIBLE": "OK", "CERTIFIED_INFEASIBLE": "INF", "UNRESOLVED": "UNR"}
    panels = [("status", "A. Complete six-phase skill, pick c -> place 63-c (obstacle-free)\n   "
               + ", ".join(f"{STATUS[s][0]} {n}" for s, n in counts.items())),
              ("n_ik", f"B. Grasp candidates with exact IK inside joint limits (of {n_dirs})"),
              ("n_pose", f"C. ... whose open-finger grasp pose is collision-free (of {n_dirs})"),
              ("n_grasp", f"D. ... with certified approach and contact closure (of {n_dirs});\n"
                          "   ticks = certified tool-axis directions")]
    for ax, (key, title) in zip(axes.flat, panels):
        scene_panel(ax, scene, cfg, title, hide=[o.id for o in scene.objects], limits="grid")
        for r in rows:
            x, y = scene.lattice.center(r["cell"])
            if key == "status":
                ax.add_patch(Rectangle((x - 0.04, y - 0.04), 0.08, 0.08, fc=STATUS[r["status"]][1], alpha=0.5, zorder=2))
                ax.text(x, y, short[r["status"]], ha="center", va="center", fontsize=7, weight="bold", zorder=4)
                continue
            ax.add_patch(Rectangle((x - 0.04, y - 0.04), 0.08, 0.08, fc=COLORS["hypothetical"],
                                   alpha=0.08 + 0.55 * r[key] / n_dirs, zorder=2))
            if key != "n_grasp":
                ax.text(x, y, str(r[key]), ha="center", va="center", fontsize=8, zorder=4)
                continue
            ax.text(x - 0.036, y + 0.036, str(r[key]), ha="left", va="top", fontsize=6, zorder=5)
            for phi in r["ok_phis"]:
                u = np.array([math.cos(phi), math.sin(phi)])
                ax.plot(*np.array([(x, y) - 0.03 * u, (x, y) - 0.016 * u]).T, color=COLORS["text"], lw=0.6, zorder=4)
        viz.draw_robot(ax, robot, robot.q_home, robot.open_gap, alpha=0.35, zorder=5)
        ax.plot(*robot.base, "k+", ms=10, zorder=6)
        ax.text(robot.base[0], robot.base[1] - 0.03, "base", ha="center", va="top", fontsize=7)
    fig.tight_layout()
    return fig


def corners_figure(tasks: list[dict], robot, cfg):
    """One keyframe panel per recorded corner task (rows: scene families)."""
    cols = 4
    fig, axes = plt.subplots(math.ceil(len(tasks) / cols), cols, figsize=(5.2 * cols, 5.4 * math.ceil(len(tasks) / cols)),
                             squeeze=False)
    for ax, t in zip(axes.flat, tasks):
        title = f"{t['label']}: cell {t['src']} -> {t['dst']}"
        if t["arrays"] is None:
            scene_panel(ax, t["scene"], cfg, title)
            status_tag(ax, t["status"], t["reason"])
        else:
            keyframe_panel(ax, robot, t["scene"], cfg, t["arrays"], title, t["status"],
                           t["scene"].lattice.center(t["dst"]))
    return fig


def write_gif(fig, draw, n: int, path, ms: int = 70) -> None:
    """Render draw(k) for k < n into a looping GIF with one shared palette."""
    imgs = []
    for k in range(n):
        draw(k)
        imgs.append(Image.fromarray(viz.figure_rgba(fig)[..., :3]))
    pal = imgs[0].quantize(colors=128)
    frames = [im.quantize(palette=pal) for im in imgs]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=ms, loop=0, optimize=True)
    plt.close(fig)


def animate_tasks(tasks: list[dict], robot, cfg, path, n: int = 90) -> None:
    """2x2 (or 1xN) synchronised animation of recorded tasks."""
    cols = 2 if len(tasks) == 4 else len(tasks)
    rows = math.ceil(len(tasks) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5.0 * cols, 5.0 * rows), squeeze=False)
    sampled = [mo.samples(t["arrays"], n) for t in tasks]

    def draw(k):
        for ax, t, fr in zip(axes.flat, tasks, sampled):
            ax.clear()
            task_frame(ax, robot, t["scene"], cfg, t["arrays"], fr, k,
                       f"{t['label']}: {t['src']} -> {t['dst']}", t["status"],
                       t["scene"].lattice.center(t["dst"]))
        fig.tight_layout()
    write_gif(fig, draw, n, path)


def skill_filmstrip(robot, scene, cfg, arrays, status: str, dest_xy):
    """One panel per phase, robot at the end of that phase, traces so far."""
    frames, phases = mo.samples(arrays, 400), list(mo.PHASES)
    fig, axes = plt.subplots(2, 4, figsize=(18, 10.5))
    axes.flat[-1].axis("off")
    for ax, ph in zip(axes.flat, phases):
        k = max(i for i, f in enumerate(frames) if f[2] == ph)
        task_frame(ax, robot, scene, cfg, arrays, frames, k, ph, status, dest_xy)
        ax.set(xlabel="", ylabel="")
    return fig


def _pair_bodies(pair: str) -> tuple[str, ...]:
    return tuple(pair.split("|")) if pair else ()


def _obstacle_ring(ax, scene, pair: str):
    for o in scene.objects:
        if o.id in _pair_bodies(pair):
            ax.add_patch(Circle(o.xy_m, o.radius_m + 0.006, fc="none", ec=COLORS["invalid"], lw=2, zorder=9))


def diagnostics_figure(robot, cfg, ex: dict):
    """A: rejected candidate pose; B: segment with clear endpoints but a certified
    interior collision; C: link-0 sweep certificate; D: planner budget exhausted."""
    fig, axes = plt.subplots(2, 2, figsize=(15, 14))
    for ax, key in zip(axes.flat, ("pose", "segment", "sweep", "budget")):
        if ex.get(key) is None:
            ax.text(0.5, 0.5, f"no '{key}' example produced in this run", ha="center", transform=ax.transAxes)
    if ex.get("pose") is None:
        return fig
    sc_, q, gap, v = ex["pose"]
    ax = axes[0, 0]
    scene_panel(ax, sc_, cfg, f"A. Rejected grasp pose: {v.pair}  d = {v.distance * 1000:.1f} mm < delta")
    viz.draw_robot(ax, robot, q, gap, highlight=_pair_bodies(v.pair), zorder=8)
    _obstacle_ring(ax, sc_, v.pair)
    status_tag(ax, "CERTIFIED_INFEASIBLE", "definite collision at this pose")
    if ex.get("segment") is None:
        return fig
    sc_, qa, qb, gap, v = ex["segment"]
    ax = axes[0, 1]
    scene_panel(ax, sc_, cfg, f"B. Joint-linear segment: both ends clear, collision at s = {v.s:.3f}")
    for qq, a in ((qa, 0.25), (qb, 0.25)):
        viz.draw_robot(ax, robot, qq, gap, alpha=a, zorder=7)
    viz.draw_robot(ax, robot, qa + v.s * (qb - qa), gap, highlight=_pair_bodies(v.pair), zorder=8)
    _obstacle_ring(ax, sc_, v.pair)
    status_tag(ax, "CERTIFIED_INFEASIBLE", f"{v.pair} (found by interval certifier, {v.evals} evals)")
    if ex.get("sweep") is None:
        return fig
    sc_, qa, qb, pl = ex["sweep"]
    ax = axes[1, 0]
    scene_panel(ax, sc_, cfg, f"C. Link-0 sweep certificate: {pl.reason.split(':', 1)[1]}")
    lo, hi = sorted((qa[0], qb[0]))
    ax.add_patch(Wedge(robot.base, robot.lengths[0], math.degrees(lo), math.degrees(hi),
                       fc=COLORS["invalid"], alpha=0.15, zorder=2))
    for qq in (qa, qb):
        viz.draw_robot(ax, robot, qq, robot.open_gap, alpha=0.45, zorder=7)
    _obstacle_ring(ax, sc_, pl.reason)
    status_tag(ax, "CERTIFIED_INFEASIBLE", "every path sweeps link 0 through this disc")
    if ex.get("budget") is None:
        return fig
    sc_, qa, qb, pl = ex["budget"]
    ax = axes[1, 1]
    scene_panel(ax, sc_, cfg, f"D. {pl.nodes}-node search ({pl.seconds:.0f} s): no path; dots = tree vertices")
    ax.plot(pl.tree_xy[:, 0], pl.tree_xy[:, 1], ".", ms=1.5, color=COLORS["hypothetical"], alpha=0.5, zorder=4)
    for qq in (qa, qb):
        viz.draw_robot(ax, robot, qq, robot.open_gap, alpha=0.45, zorder=7)
    status_tag(ax, "UNRESOLVED", "budget exhausted: NOT a proof of infeasibility")
    ax.text(0.02, 0.1, pl.reason, transform=ax.transAxes, fontsize=7, wrap=True, zorder=20,
            bbox=dict(fc="white", ec=COLORS["muted"], pad=2))
    return fig


def candidates_panel(ax, robot, scene, cfg, result, title: str):
    """Every declared pick candidate as a short ray at the target, coloured by its
    first failed check; the closest-to-home OK candidate's pose is drawn."""
    t = next(o for o in scene.objects if o.kind == "target")
    scene_panel(ax, scene, cfg, title)
    color = {"OK": COLORS["valid"]}
    for c in result.picks:
        u = np.array([math.cos(c.phi), math.sin(c.phi)])
        tone = color.get(c.stage, COLORS["invalid"] if c.certified else COLORS["unresolved"])
        a = np.asarray(t.xy_m) - (0.03 + 0.012 * (c.branch > 0)) * u
        ax.add_patch(FancyArrowPatch(a - 0.05 * u, a, arrowstyle="-|>", mutation_scale=6, lw=0.8,
                                     color=tone, zorder=6))
    viz.draw_robot(ax, robot, robot.q_home, robot.open_gap, alpha=0.6, zorder=7)
    ok = [c for c in result.picks if c.stage == "OK"]
    if ok:
        viz.draw_robot(ax, robot, ok[0].q_end, robot.open_gap, alpha=0.35, zorder=7)


# ------------------------------------------------------------------ G1 orchestration
def diagnostic_examples(robot, cfg, done: dict) -> dict:
    """First real example of each rejection kind, preferring the clutter scene."""
    order = sorted(done, key=lambda k: (not k.startswith("G1_CLUTTER"), not k.startswith("G1_S2"), k))
    ex = {"pose": None, "segment": None, "sweep": None, "budget": None}
    delta, eps = cfg["suite"]["margin_m"], cfg["geometry"]["numeric_margin_band_m"]
    for tid in order:
        s, res, _ = done[tid]
        for c in res.picks:
            if ex["pose"] is None and c.stage == "GRASP_POSE" and c.certified:
                ck = mo.checkers(robot, s, "t0", None, None, delta, eps)[("start", False)]
                ex["pose"] = (s, c.q_end, robot.open_gap, ck.status_at(c.q_end, robot.open_gap))
        for label, pl in res.plans:
            d = pl.direct
            if ex["segment"] is None and label.startswith("pregrasp") and d and d.status == ge.COLLISION \
                    and 0 < d.s < 1:
                ex["segment"] = (s, *pl.ends, robot.open_gap, d)
            if ex["sweep"] is None and pl.reason.startswith("LINK0_SWEEP") and label.startswith("pregrasp"):
                ex["sweep"] = (s, *pl.ends, pl)
            if ex["budget"] is None and pl.reason == "BUDGET_EXHAUSTED":
                ex["budget"] = (s, *pl.ends, pl)
    if ex["budget"] is None:  # none occurred: rerun a solved RRT query with a deliberately tiny budget
        for tid in order:
            s, res, _ = done[tid]
            hit = next((pl for lb, pl in res.plans if lb.startswith("pregrasp") and pl.reason == "RRT_JOINT"), None)
            if hit:
                ck = mo.checkers(robot, s, "t0", None, None, delta, eps)[("start", False)]
                small = {**cfg["planner2d"], "max_nodes": 40}
                pl = pn.plan(ck, *hit.ends, robot.open_gap, small, cfg["geometry"]["certify_max_evals"], "demo")
                pl.reason += f" (node budget cut to 40 for illustration; full budget: {hit.reason}, VERIFIED)"
                ex["budget"] = (s, *hit.ends, pl)
                break
    return ex


def g1_figures(out, robot, cfg, fixtures: dict, done: dict) -> None:
    """Write every G1 figure and animation into the flat run directory."""
    d0 = done["audit_c00"][0]
    f = audit_figure(sk.audit_rows(done), d0, robot, cfg, 2 * cfg["skill2d"]["approach_dirs"])
    f.savefig(out / "overview.png", dpi=100)
    plt.close(f)
    task = lambda tid: {"label": tid.replace("G1_", ""), "scene": done[tid][0],  # noqa: E731
                        "status": done[tid][1].status, "reason": done[tid][1].reason,
                        "arrays": None if done[tid][1].traj is None else done[tid][1].traj.arrays(),
                        "src": fixtures[tid.rsplit("_t", 1)[0]]["tasks"][int(tid.rsplit("_t", 1)[1])][0],
                        "dst": fixtures[tid.rsplit("_t", 1)[0]]["tasks"][int(tid.rsplit("_t", 1)[1])][1]}
    rows = {case: [task(f"{case}_t{i}") for i in range(4)] for case in ("G1_D0", "G1_S1", "G1_S2")}
    f = corners_figure(rows["G1_D0"] + rows["G1_S1"] + rows["G1_S2"], robot, cfg)
    f.savefig(out / "corners.png", dpi=80)
    plt.close(f)
    for case, name in (("G1_D0", "corners_d0.gif"), ("G1_S1", "corners_s1.gif")):
        ok = [t for t in rows[case] if t["arrays"] is not None]
        if ok:
            animate_tasks(ok, robot, cfg, out / name)
    s1 = fixtures["G1_S1"]
    nominal = task("G1_S1_t%d" % s1["tasks"].index(s1["nominal_task"]))
    if nominal["arrays"] is not None:
        f = skill_filmstrip(robot, nominal["scene"], cfg, nominal["arrays"], nominal["status"],
                            nominal["scene"].lattice.center(nominal["dst"]))
        f.savefig(out / "skill.png", dpi=80)
        plt.close(f)
        animate_tasks([nominal], robot, cfg, out / "trace.gif", n=140)
    f = diagnostics_figure(robot, cfg, diagnostic_examples(robot, cfg, done))
    f.savefig(out / "diagnostics.png", dpi=90)
    plt.close(f)
    clutter = task("G1_CLUTTER_t0")
    f, axes = plt.subplots(1, 2, figsize=(16, 8))
    res = done["G1_CLUTTER_t0"][1]
    candidates_panel(axes[0], robot, clutter["scene"], cfg, res,
                     f"A. 48 declared pick candidates for t0 (green OK, red certified, amber unresolved)")
    if clutter["arrays"] is not None:
        keyframe_panel(axes[1], robot, clutter["scene"], cfg, clutter["arrays"], "B. Verified skill",
                       clutter["status"], clutter["scene"].lattice.center(clutter["dst"]))
    else:
        rejection_panel(axes[1], robot, clutter["scene"], cfg, res)
    f.savefig(out / "clutter.png", dpi=90)
    plt.close(f)


def rejection_panel(ax, robot, scene, cfg, result):
    """Representative rejected pick poses (one per stage, offending pair in red) and
    the count of every stage / most frequent offending pair, for a failed query."""
    from collections import Counter
    scene_panel(ax, scene, cfg, "B. Why no pick survives: representative rejected poses")
    shown = set()
    for c in result.picks:
        if c.q_end is not None and c.stage not in shown and c.stage != "OK":
            shown.add(c.stage)
            viz.draw_robot(ax, robot, c.q_end, robot.open_gap, alpha=0.55, zorder=7,
                           highlight=_pair_bodies(c.reason))
            _obstacle_ring(ax, scene, c.reason)
    stages = Counter(c.stage for c in result.picks)
    pairs = Counter(c.reason for c in result.picks if c.reason)
    lines = [f"{s}: {n}" for s, n in stages.most_common()] + ["most frequent offending pairs:"]
    lines += [f"  {pr}: {n}" for pr, n in pairs.most_common(6)]
    ax.text(0.02, 0.98, "\n".join(lines), transform=ax.transAxes, va="top", fontsize=7,
            family="monospace", bbox=dict(fc="white", ec=COLORS["muted"]), zorder=20)
    status_tag(ax, result.status, result.reason)
