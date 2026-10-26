"""P16 figures: scene-only family gallery (initial scene, pool, parking slots, lattice outcome), certified plan GIF (deterministic re-run,
plan must equal the recorded one; only replay-CLEAR arrays are drawn), B decision plots, D search comparison plots."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

DST = Path("visualizations/p16")
COL = {"LB": "#2a6fdb", "LB-F2": "#7fa7ec", "LC": "#8e5bd0", "LB+G": "#2e9e5b", "A": "#e07b00", "P13:K-B": "#52514e", "P13:A": "#c08a3e",
       "P13:SF": "#a7b4c2", "P13:K-C": "#b38bd6", "P13:B-F2": "#9fb7e8", "geometry": "#c0392b", "empty_always": "#7a7975", "random": "#d6d5d0",
       "Dp16": "#2a6fdb", "Dp16-norec": "#7fa7ec", "Dp": "#8e5bd0", "D": "#52514e", "geometry-norec": "#e8a090", "uniform": "#7a7975", "oracle": "#2e9e5b"}


def rd(p):
    return json.loads(Path(p).read_text())


def gallery(name="dev", out="shared/P16_dev_families.png") -> None:
    import p16_eval as pe
    import p6_viz as pv
    from scene import scene_from_dict
    from viz import plt
    import config as cf
    import geometry as ge
    plan, labs, tags = rd(pe.DATA / name / "plan.json"), pe.merged(name, "labels"), pe.merged(name, "tags")
    keys = sorted(labs)
    cfg = cf.load_config("config.toml")
    robot = ge.make_robot(cfg)
    n = len(keys)
    f, ax = plt.subplots(2, (n + 1) // 2, figsize=(4.2 * ((n + 1) // 2), 8.8), squeeze=False)
    for a, k in zip(ax.flat, keys):
        r, lab = plan["roots"][k], labs[k]
        s = scene_from_dict(r["scene"])
        t = tags.get(k, {})
        pv._panel(a, cfg, robot, s, r["goal_cell"], f"{k[-5:]} {r['family']}: y0={lab['original']['status'][:9]}")
        for o, d in lab["catalogue"]["parking"].items():
            x0, y0 = s.get(o).xy_m
            x1, y1 = s.lattice.center(d)
            a.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="->", color="#2a6fdb", lw=1.0, ls="--"))
        fixed = set(r.get("fixed", []))
        for o in s.objects:
            if o.cell in fixed:
                a.add_patch(plt.Circle(o.xy_m, o.radius_m * 1.25, fill=False, ec="#3b4a5a", lw=1.6, ls=":"))
        import p16_d as pdd
        d = pdd.lattice(lab, lab["catalogue"]["pool"])
        txt = f"pool {','.join(lab['catalogue']['pool'])}\nlattice: {d['type']}\nunion {d['mask']} nec {d['necessary']}"
        if t:
            txt += f"\nsearch: {'plan ' + str(t['moves']) + ' moves' if t.get('found') else 'no plan'}"
        a.text(0.02, 0.98, txt, transform=a.transAxes, va="top", fontsize=7, bbox=dict(fc="white", ec="#d6d5d0", alpha=0.9))
    for a in ax.flat[n:]:
        a.axis("off")
    (DST / out).parent.mkdir(parents=True, exist_ok=True)
    pv.png(f, DST / out, f"P16 {name} roots: scene-only pool (dashed = parking slot), dotted ring = fixed structure, lattice semantics, search result")


def plan_gif(name, key, out, n_max=4, per_obj=2, node_cap=500) -> dict:
    """Deterministic re-run of the uniform scene-only search on one root; GIF of the replay-CLEAR certified arrays + a static summary."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_eval as pe
    import p16_motion as pm
    import p6_viz as pv
    import p14_eval as p14
    from viz import COLORS, plt
    plan, idx = rd(pe.DATA / name / "plan.json"), pl.index_v2()[0]
    task = pc.task_from_root(plan["roots"][key], key)
    phys = pm.DetPhysics(task, idx)
    cells0 = {o.id: o.cell for o in phys.s0.objects}
    movers, _ = pc.propose_movers(task, cells0)
    r = pc.search(phys, pe.uniform_order, movers, pc.slot_fn(phys, idx), cells0, phys.s0.robot.q_rad, n_max, per_obj, node_cap)
    if not r["found"]:
        return {"found": False}
    rep = pm.replay(phys, r["plan"])
    if not rep["ok"]:
        return {"found": True, "replay": rep}
    steps, recs = r["plan"]["steps"], r["plan"]["records"]
    rel, i = [], 0
    for st in steps:
        rel.append(p14._merge(recs[i], recs[i + 1]) if st["via"] == "lookup" else recs[i])
        i += 2 if st["via"] == "lookup" else 1
    frames = []
    for qq, gp, pos, mv in pv.trace_frames(phys.robot, phys.s0, [(s["object"], s["dest"]) for s in steps], rel, recs[-1:], n_move=10, n_target=12):
        fg, a = plt.subplots(figsize=(5, 5))
        pv._panel(a, phys.cfg, phys.robot, phys.s0, phys.goal_cell, f"{key[-5:]} {plan['roots'][key]['family']}: {len(steps)} moves, travel "
                  f"{r['plan']['travel']:.2f}\n{r['claim'][:44]}", q=qq, gap=gp, pos=pos, held=mv)
        pv._tag(a, f"replayed certified motion {rep['traj']}", COLORS["valid"])
        frames.append(pv._rgb(fg))
    (DST / out).parent.mkdir(parents=True, exist_ok=True)
    pv.gif(DST / out, frames, f"P16 {name} {key}: certified scene-only plan replay")
    return {"found": True, "replay": rep, "steps": [(s["object"], s["dest"], s["via"], s.get("transit")) for s in steps], "claim": r["claim"]}
