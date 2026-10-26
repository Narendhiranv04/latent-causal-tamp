"""P17 figures: mechanism panels (initial / after each certified relocation / final with the target at its goal) and GIFs drawn ONLY
from replay-certified recorded arrays; B and D result plots."""
from __future__ import annotations

from pathlib import Path

import numpy as np

DST = Path("visualizations/p17")


def mechanism(phys, root, plan, tag, rec) -> dict:
    import geometry as ge
    import motion as mo
    import p14_eval as p14
    import p6_scenes as p6
    import p6_viz as pv
    from viz import COLORS, plt
    steps, recs = plan["steps"], plan["records"]
    rel, i = [], 0
    for st in steps:
        rel.append(p14._merge(recs[i], recs[i + 1]) if st["via"] == "lookup" else recs[i])
        i += 2 if st["via"] == "lookup" else 1
    s0, goal = phys.s0, phys.goal_cell
    n = len(steps) + 2
    f, ax = plt.subplots(1, n, figsize=(4.6 * n, 4.8), squeeze=False)
    pv._panel(ax[0][0], phys.cfg, phys.robot, s0, goal, f"{tag}: initial ({rec['original_status'][:9]})")
    cells = {o.id: o.cell for o in s0.objects}
    for j, (st, a) in enumerate(zip(steps, rel)):
        cells[st["object"]] = st["dest"]
        sj = p6.moved(s0, {o: c for o, c in cells.items() if o != "t0"})
        pv._panel(ax[0][j + 1], phys.cfg, phys.robot, sj, goal, f"after {j + 1}: {st['object']}->{st['dest']} ({st['via']})")
        pts = np.array([ge.fk(phys.robot, q)[0][-1] for q, _, _ in mo.samples(a, 60)])
        ax[0][j + 1].plot(pts[:, 0], pts[:, 1], color="#2a6fdb", lw=1.4)
    sN = p6.moved(s0, {o: c for o, c in cells.items() if o != "t0"})
    pv._panel(ax[0][-1], phys.cfg, phys.robot, sN, goal, f"target action (travel {plan['travel']:.2f})")
    pts = np.array([ge.fk(phys.robot, q)[0][-1] for q, _, _ in mo.samples(recs[-1], 60)])
    ax[0][-1].plot(pts[:, 0], pts[:, 1], color=COLORS["target"], lw=1.4)
    (DST / "mechanisms").mkdir(parents=True, exist_ok=True)
    png = DST / "mechanisms" / f"{tag}.png"
    pv.png(f, png, f"P17 mechanism {tag}: certified ordered repair (tool paths from replayed arrays)")
    frames = []
    for qq, gp, pos, mv in pv.trace_frames(phys.robot, s0, [(s["object"], s["dest"]) for s in steps], rel, recs[-1:], n_move=10, n_target=12):
        fg, a = plt.subplots(figsize=(5, 5))
        pv._panel(a, phys.cfg, phys.robot, s0, goal, f"{tag}: {len(steps)} moves\nRECORDED / CERTIFIED arrays", q=qq, gap=gp, pos=pos, held=mv)
        pv._tag(a, f"replay CLEAR {rec['positive']['replay']['traj']}", COLORS["valid"])
        frames.append(pv._rgb(fg))
    gif = DST / "mechanisms" / f"{tag}.gif"
    pv.gif(gif, frames, f"P17 mechanism {tag}: certified replay")
    return {"png": str(png), "gif": str(gif)}
