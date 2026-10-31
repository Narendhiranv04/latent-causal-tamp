"""BXY-P9 figures from the actual pilot evidence only: per-query status grid (1 / 0 / censored / not attempted kept distinct), CPU ledger,
scene panels and a GIF drawn from the stored, independently replayed witness records (relocations, connector, target). Nothing is drawn
for a query without a witness except its failure annotation."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_pilot as P  # noqa: E402
import bxy_teacher as T  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_teacher_pilot_v1")
C1, C0, CC, CN, INK2 = "#1baf7a", "#eb6834", "#8c8c8c", "#ffffff", "#52514e"


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return str(FIG / name)


def fig_status(sc):
    R = bd.roots()
    rows = sorted({r["root"] for r in sc["x_queries"] + sc["y_queries"]}, key=lambda k: (P.stratum(R[k]), k))
    byk = {(r["root"], r["type"], s): r for s, rs in (("x", sc["x_queries"]), ("y", sc["y_queries"])) for r in rs}
    cols = [(t, s) for t in P.TYPES for s in ("x", "y") if any(kk[1:] == (t, s) for kk in byk)]       # only predeclared query kinds
    fig, ax = plt.subplots(figsize=(13, 0.34 * len(rows) + 1.8))
    for i, k in enumerate(rows):
        for j, (t, s) in enumerate(cols):
            r = byk.get((k, t, s))
            if r is None:
                continue
            st = r["teacher_status"]
            col, txt = (C1, "1") if r["y"] == 1 else (C0, "0") if r["y"] == 0 else (CC, "cens") if st == "CENSORED" else (CN, "n/a")
            ax.add_patch(plt.Rectangle((j, i), 0.94, 0.88, fc=col, ec=INK2 if col == CN else "none", lw=0.6, hatch="///" if st == "CENSORED" else None))
            lab = txt if r["y"] != 0 else (r.get("failed_phase") or "")[:14]
            ax.text(j + 0.47, i + 0.44, lab, ha="center", va="center", fontsize=6, color="#0b0b0b")
    ax.set(xlim=(0, len(cols)), ylim=(len(rows), 0))
    ax.set_xticks(np.arange(len(cols)) + 0.47, [f"{t.replace('intermediate_', 'interm. ').replace('_', ' ')}\n{s.upper()}" for t, s in cols], fontsize=7)
    ax.set_yticks(np.arange(len(rows)) + 0.44, [f"{k[-4:]} {P.stratum(R[k])}" for k in rows], fontsize=7)
    ax.tick_params(length=0)
    for s_ in ax.spines.values():
        s_.set_visible(False)
    ax.set_title("BXY-P9 pilot: every predeclared query (green 1, orange 0 with failed phase, grey hatched censored, white not attempted)",
                 loc="left", fontsize=9)
    return _save(fig, "01_query_status.png")


def fig_cpu(sc):
    led = sc["manifest"]["measured"]["ledger"]
    fig, ax = plt.subplots(1, 2, figsize=(13, 3.8), constrained_layout=True)
    ax[0].bar(range(len(led)), [x["cpu_s"] for x in led], color="#2a78d6")
    ax[0].axhline(P.CAPS["root_cpu_s"], color=C0, ls="--", lw=1)
    ax[0].text(0, P.CAPS["root_cpu_s"] + 4, "per-root cap 300 CPU-s", fontsize=7, color=INK2)
    ax[0].set_xticks(range(len(led)), [x["root"][-4:] for x in led], rotation=90, fontsize=7)
    ax[0].set(ylabel="worker process CPU-s (RUSAGE)")
    ax[0].set_title(f"(a) per-root worker CPU, total {sum(x['cpu_s'] for x in led):.0f} of {P.CAPS['cpu_s']:.0f} CPU-s", loc="left", fontsize=9)
    for j, (nm, rs) in enumerate((("X", sc["x_queries"]), ("Y", sc["y_queries"]))):
        v = [(len(r.get("ordered_actions") or r.get("hypothetical_poses") or []), r["process_cpu_s"], r["y"]) for r in rs if r.get("process_cpu_s") is not None]
        ax[1].scatter([a + (j - 0.5) * 0.18 for a, _, _ in v], [b for _, b, _ in v], s=14, color=["#2a78d6", "#e87ba4"][j], label=f"{nm} queries")
    ax[1].set(xlabel="relocations in the prefix (X) / moved objects in the edited scene (Y)", ylabel="query process CPU-s")
    ax[1].set_title("(b) per-query teacher CPU", loc="left", fontsize=9)
    ax[1].legend(fontsize=7)
    return _save(fig, "02_cpu.png")


def _scene(k, rec, cells, q):
    import p16_motion as pm
    return pm.DetPhysics(T.task_of(k, rec), None).scene(cells, q)


def _tool(ax, E, recs, color, lw=1.4):
    import geometry as ge
    import motion as mo
    for a in recs:
        pts = np.array([ge.fk(E["robot"], qq)[0][-1] for qq, _, _ in mo.samples(a, 80)])
        ax.plot(pts[:, 0], pts[:, 1], color=color, lw=lw, zorder=7)


def fig_root(sc, k, name):
    """(a) S0 with the arm at q0; (b) X: relocation tool paths, arm at q_final (light) and after the connector at q_ref, connector path;
    (c) Y: hypothetical edited scene, target trace from q_ref. Status text from the sidecar rows."""
    import bd_viz as BV
    import viz
    E, rec = T.env(), bd.roots()[k]
    X = [r for r in sc["x_queries"] if r["root"] == k and r["observed"] and r["type"] in ("old_success", "intermediate_prefix", "old_fail")]
    x = next((r for r in X if r["y"] == 1), X[0] if X else None)
    y = next((r for r in sc["y_queries"] if x and r.get("y_key") == x["parent_y_key"]), None)
    fig, ax = plt.subplots(1, 3, figsize=(16, 5.2), constrained_layout=True)
    c0 = bd.cells0(rec)
    BV._scene2d(ax[0], _scene(k, rec, c0, T.qref(rec)), rec["goal_cell"], E["robot"], rec["roles"], rec["fixed_ids"], (), (),
                f"(a) {k[-9:]} S0, robot at q0 = q_ref (verified K {rec['verified_K']})", q=T.qref(rec))
    seq = [tuple(a) for a in x["ordered_actions"]] if x else []
    cells = {**c0, **bd.endpoint(rec, seq)}
    s1 = _scene(k, rec, cells, T.qref(rec))
    BV._scene2d(ax[1], s1, rec["goal_cell"], E["robot"], rec["roles"], rec["fixed_ids"], (), (), "", q=None)
    if x and x.get("witness_relocations"):
        _tool(ax[1], E, [T.load_w(P.OUT, w) for w in x["witness_relocations"]], "#2a78d6")
    if x and x.get("witness_connector"):
        _tool(ax[1], E, [T.load_w(P.OUT, x["witness_connector"])], "#e87ba4", 2.2)
        viz.draw_robot(ax[1], E["robot"], x["final_q_before_connector"], E["robot"].open_gap, alpha=0.25, zorder=6)
        viz.draw_robot(ax[1], E["robot"], x["final_q_after_connector"], E["robot"].open_gap, alpha=0.6, zorder=6)
    elif x and x.get("final_q_before_connector"):
        viz.draw_robot(ax[1], E["robot"], x["final_q_before_connector"], E["robot"].open_gap, alpha=0.45, zorder=6)
    xs = "no X query" if not x else f"X = {x['y']} ({x['teacher_status']}{', ' + x['failed_phase'] if x.get('failed_phase') else ''})"
    ax[1].set_title(f"(b) X {seq}: relocations (blue), connector (pink)\n{xs}; replay {x.get('independent_replay') if x else None}", loc="left", fontsize=8.5)
    BV._scene2d(ax[2], s1, rec["goal_cell"], E["robot"], rec["roles"], rec["fixed_ids"], (), (), "", q=T.qref(rec))
    if y and y.get("target_witness"):
        _tool(ax[2], E, [T.load_w(P.OUT, y["target_witness"])], "#1baf7a", 2.0)
    ys = "no Y query" if not y else f"Y = {y['y']} ({y['teacher_status']}); replay {y.get('independent_replay')}; J_target {y.get('J_target')}"
    ax[2].set_title(f"(c) Y from q_ref in the hypothetical scene S^q (target trace green)\n{ys}", loc="left", fontsize=8.5)
    return _save(fig, name)


def gif_root(sc, k, name):
    """Animation of one matched full-joint-success witness: relocations, connector, then the Y target from q_ref (all stored records)."""
    import geometry as ge
    import motion as mo
    import bd_viz as BV
    import viz
    from PIL import Image
    E, rec = T.env(), bd.roots()[k]
    p = next(p_ for p_ in sc["paired"] if p_["root"] == k and p_["full_joint_success"] == 1)
    x = next(r for r in sc["x_queries"] if r["x_key"] == p["x_key"])
    y = next(r for r in sc["y_queries"] if r["y_key"] == p["y_key"])
    seq = [tuple(a) for a in x["ordered_actions"]]
    parts = [("relocation", o, T.load_w(P.OUT, w)) for (o, _), w in zip(seq, x["witness_relocations"])]
    parts += [("connector", None, T.load_w(P.OUT, x["witness_connector"])), ("Y target from q_ref", "t0", T.load_w(P.OUT, y["target_witness"]))]
    cells, frames = bd.cells0(rec), []
    f0, a0 = plt.subplots()
    BV._scene2d(a0, _scene(k, rec, cells, T.qref(rec)), rec["goal_cell"], E["robot"], rec["roles"], rec["fixed_ids"], (), (), "", q=T.qref(rec))
    plt.close(f0)
    pts = np.array([p_ for _, _, a in parts for qq, _, _ in mo.samples(a, 28) for p_ in ge.fk(E["robot"], qq)[0]])
    pad = 0.12                                                                      # one fixed view: scene + every arm joint of every frame
    lim = ((min(a0.get_xlim()[0], pts[:, 0].min() - pad), max(a0.get_xlim()[1], pts[:, 0].max() + pad)),
           (min(a0.get_ylim()[0], pts[:, 1].min() - pad), max(a0.get_ylim()[1], pts[:, 1].max() + pad)))
    for j, (lab, o, a) in enumerate(parts):
        for qq, g, ph in mo.samples(a, 28 if lab != "connector" else 14):
            held = o if ph == "carry" else None
            shown = {kk: v for kk, v in cells.items() if kk != held}
            fig, ax = plt.subplots(figsize=(6.2, 5))
            from dataclasses import replace
            s = _scene(k, rec, {**cells}, qq)
            s = replace(s, objects=tuple(ob for ob in s.objects if ob.id in shown))      # the carried disc is drawn at the tool point
            BV._scene2d(ax, s, rec["goal_cell"], E["robot"], rec["roles"], rec["fixed_ids"], (), (), f"{k[-9:]} {lab} {o or ''} [{ph}]  X=1, Y=1 (replayed)")
            viz.draw_robot(ax, E["robot"], qq, g, alpha=0.85, zorder=8)
            ax.set(xlim=lim[0], ylim=lim[1])
            if held:
                ax.add_patch(plt.Circle(ge.tool_point(E["robot"], qq, tuple(a["held_local"])), 0.024, fc="#f6b26b" if held != "t0" else "#1baf7a", ec="k", zorder=9))
            fig.canvas.draw()
            frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3]))
            plt.close(fig)
        if lab == "relocation":
            cells = {**cells, o: dict(seq)[o]}
        if lab == "connector":
            cells = {**cells}
    FIG.mkdir(parents=True, exist_ok=True)
    frames[0].save(FIG / name, save_all=True, append_images=frames[1:], duration=80, loop=0)
    return str(FIG / name)


def all_figures():
    sc = json.loads((P.OUT / "BXY_SIDECAR_V2_PILOT.json").read_text())
    out = [fig_status(sc), fig_cpu(sc)]
    full = [p["root"] for p in sc["paired"] if p["full_joint_success"] == 1]
    xfail = [r["root"] for r in sc["x_queries"] if r["observed"] and r["y"] == 0 and str(r.get("failed_phase")).startswith("connector")]
    rfail = [r["root"] for r in sc["x_queries"] if r["observed"] and r["y"] == 0 and str(r.get("failed_phase")).startswith("relocation")]
    pick = list(dict.fromkeys([*full[:1], *xfail[:1], *rfail[:1]]))
    for i, k in enumerate(pick):
        out.append(fig_root(sc, k, f"03_root_{i}_{k[-4:]}.png"))
    if full:
        out.append(gif_root(sc, full[0], f"04_full_joint_witness_{full[0][-4:]}.gif"))
    return out
