#!/usr/bin/env python3
"""R1 figures (evaluator side).  Every figure states what it is:
  R1_fig3_synthetic.png   SYNTHETIC: recursion tree + dependency-preserving composition + chosen chunk boundaries of the literal Fig. 3
                          seven-action example under the declared fake scorer of tests/test_fig3.py (no model, no teacher, no success claim).
  R1_3d_home_returns.png  ACTUAL teacher witnesses (SHELF66V3 plans executed in MuJoCo, joint space; not a render): chunked (2,2) and local
                          paired (3,1) executions with the planned CONNECTOR_TO_QREADY_V1 path at every boundary.
  R1_2d_home_returns.png  ACTUAL certified 2D teacher records (geometry-certified joint paths, planar 3R; not a simulator render): (1,1)
                          chunked executions with the teacher connector to q_ref at every boundary, including the failed connector.
    python viz.py FIG3_DIR OUT_DIR      (FIG3_DIR holds runs/p3d.jsonl, runs/p2d.jsonl, store/witnesses, w2d/witnesses)"""
from __future__ import annotations

import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "tests"), str(HERE.parent)]
INK, MUTED, CONN, FAIL = "#1f2328", "#6e7781", "#d0d7de", "#cf222e"


def synthetic(out):
    import recursive as RC
    import test_fig3 as T
    p = RC.plan(T.Fake(T.LITERAL), T.row(), T.RULE, "R-FIG3", {"m_max": 7})
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.6), gridspec_kw={"height_ratios": [0.8, 1]})
    # recursion tree of the chosen seed [B, C, A] (first seed node)
    sn = next(c for c in p["tree"]["children"] if [k[0] for k in c["seed"]] == ["B", "C", "A"])
    pos, xs = {}, [0]

    def walk(n, depth, parent):
        for ch in n["children"]:
            if "action" not in ch:
                continue
            x = xs[0]; xs[0] += 1
            lab = f"{ch['action'][0]}\nY$_\\tau$={ch['y_temp']:.2f}" if ch.get("y_temp") is not None else ch["action"][0]
            pos[id(ch)] = (x, -depth)
            a1.text(x, -depth, lab, ha="center", va="center", fontsize=8, color=INK,
                    bbox=dict(boxstyle="round,pad=0.3", fc="#ffffff", ec=FAIL if ch.get("y_temp", 1) < 0.5 else MUTED))
            if parent is not None:
                a1.plot([parent[0], x], [parent[1] + (-0.18), -depth + 0.25], color=MUTED, lw=0.8)
            for r in ch.get("repairs", [])[:1]:
                walk(r, depth + 1, (x, -depth))
    walk(sn, 1, None)
    a1.text(-0.6, 0.0, "seed [B, C, A] (frozen p11 at S0); each node = one retargeted action (red = temporarily blocked, Y$_\\tau$ < 0.5);"
            " children = its admitted enabling group;\nrepeated nodes = the same action re-placed under each kept beam variant", fontsize=8.5, color=INK, va="center")
    a1.set_xlim(-0.8, max(xs[0], 8)); a1.set_ylim(-2.5, 0.4); a1.axis("off")
    a1.set_title("SYNTHETIC fixture - recursion tree (declared fake scorer; no model, no teacher)", fontsize=10, loc="left", color=INK)
    # composition with edges and chunk boundaries
    seq = [k for k, _ in [(T.NAMES[int(o)], d) for o, d in p["seq"]]]
    for i, n in enumerate(seq):
        a2.text(i, 0, n, ha="center", va="center", fontsize=12, color=INK, bbox=dict(boxstyle="round,pad=0.4", fc="#ffffff", ec=INK))
    col = {"PREREQ": "#0969da", "LOCAL": "#8250df", "SEED": "#1a7f37"}
    for x, y, k in p["edges"]:
        i, j = seq.index(x[0]), seq.index(y[0])
        h = 0.18 + 0.12 * (j - i)
        a2.annotate("", xy=(j, 0.22), xytext=(i, 0.22), arrowprops=dict(arrowstyle="->", color=col[k], lw=1.2, connectionstyle=f"arc3,rad=-{min(0.6, h)}"))
    s = 0
    for g in p["partition"][:-1]:
        s += g
        a2.axvline(s - 0.5, color=FAIL, lw=1.5, ls="--")
        a2.text(s - 0.5, -0.55, "return to q_ref", color=FAIL, fontsize=8, ha="center")
    for k, c in col.items():
        a2.plot([], [], color=c, label=k)
    a2.plot([], [], color=FAIL, ls="--", label="chunk boundary (DP-chosen partition)")
    a2.legend(loc="upper right", fontsize=8, frameon=False)
    a2.set_xlim(-0.8, 7.5); a2.set_ylim(-0.8, 1.4); a2.axis("off")
    a2.set_title(f"composed {seq}  partition {p['partition']}  E_home {p['E']:.3f}", fontsize=10, loc="left", color=INK)
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)
    return {"seq": seq, "partition": p["partition"], "edges": p["edges"]}


def _joint_panel(ax, items, title, nj):
    t, spans, cols = 0, [], plt.cm.viridis(np.linspace(0.05, 0.9, nj))
    first = True
    for it in items:
        q = it["q"]
        x = np.arange(t, t + len(q))
        for k in range(nj):
            ax.plot(x, q[:, k], color=cols[k], lw=1.1, label=f"joint {k + 1}" if first else None)
        first = False
        if it["kind"] == "connector":
            spans.append((t, t + len(q) - 1, it.get("label", "")))
        t += len(q)
    for a, b, lab in spans:
        ax.axvspan(a, max(b, a + 0.8), color=CONN, alpha=0.8, lw=0)
        ax.text(a - 1, 0.04, lab, transform=ax.get_xaxis_transform(), ha="right", va="bottom", fontsize=7, color=INK)
    ax.set_title(title, fontsize=9, loc="left", color=INK)
    ax.set_xlabel("waypoint index (moves and connectors concatenated in execution order)", fontsize=8, color=MUTED)
    ax.set_ylabel("joint angle [rad]", fontsize=8, color=MUTED)
    ax.tick_params(labelsize=7, colors=MUTED)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def actual3d(fig3, out):
    rows = {r["key"]: r for r in map(json.loads, open(fig3 / "runs/p3d.jsonl"))}
    keys = ["X3CH22|b2c2-035", "X3LOC31|b2c2-035"]
    fig, axs = plt.subplots(len(keys), 1, figsize=(11, 6.4))
    meta = {}
    for ax, k in zip(axs, keys):
        r = rows[k]; items = []
        for st in r["X"]["trace"]:
            z = np.load(fig3 / "store/witnesses" / st["witness"][:2] / f"{st['witness']}.npz")
            if st["kind"] == "move":
                items.append({"kind": "move", "q": z["q"]})
            else:
                items.append({"kind": "connector", "q": z["connector_q"], "label": f"q_ready  |dq| {st['dq_ready']:.4f}"})
        order = " -> ".join(f"{o}" for o, _ in [(s["object"], s["dest"]) for s in r["X"]["trace"] if s["kind"] == "move"])
        _joint_panel(ax, items, f"{k}: {order}; bounds {[s['after_move'] for s in r['X']['trace'] if s['kind'] == 'connector']}; "
                                 f"X={r['X']['x']} Y={r['Y']['y']} replay={r['REPLAY']['replay']}"
                                 + (f"; inner connectors removed -> replay {r['FIXTURE_DISCONNECTED']['failure']}" if r.get("FIXTURE_DISCONNECTED") else ""), 7)
        meta[k] = {"x": r["X"]["x"], "y": r["Y"]["y"], "replay": r["REPLAY"]["replay"]}
    axs[0].legend(ncol=7, fontsize=7, frameon=False, loc="lower left", bbox_to_anchor=(0, 1.08))
    fig.suptitle("ACTUAL 3D teacher witnesses (MuJoCo-executed plans, joint space; grey = planned connector back to q_ready). Not a render.",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)
    return meta


def actual2d(fig3, out):
    rows = [r for r in map(json.loads, open(fig3 / "runs/p2d.jsonl")) if r["kind"] == "X_CHUNKED"]
    fig, axs = plt.subplots(len(rows), 1, figsize=(11, 2.4 * len(rows)))
    meta = {}
    for ax, r in zip(np.atleast_1d(axs), rows):
        items = []
        for st in r["X"]["trace"]:
            z = np.load(fig3 / "w2d/witnesses" / st["witness"][:2] / f"{st['witness']}.npz")
            items.append({"kind": st["kind"], "q": z["q"], "label": f"q_ref ({st.get('how')})" if st["kind"] == "connector" else ""})
        X = r["X"]
        title = (f"{r['key']}: {[a[0] for a in X['ordered_actions']]} bounds {X['bounds']}; X={X['x']} ({X['teacher_status']}"
                 + (f" at {X.get('failed_phase')}" if X.get("failed_phase") else "") + f"), endpoint Y={r['Y']['y']}"
                 + (f"; inner connector removed -> {r['FIXTURE']['replay']['why']}" if r.get("FIXTURE") else ""))
        _joint_panel(ax, items, title, 3)
        if X["x"] == 0:
            ax.text(0.99, 0.9, "connector to q_ref NOT found (budgeted RRT) -> X = 0", transform=ax.transAxes, ha="right", fontsize=8, color=FAIL)
        meta[r["key"]] = {"x": X["x"], "status": X["teacher_status"], "phase": X.get("failed_phase")}
    np.atleast_1d(axs)[0].legend(ncol=3, fontsize=7, frameon=False, loc="lower left", bbox_to_anchor=(0, 1.12))
    fig.suptitle("ACTUAL 2D certified teacher records (planar 3R, joint space; grey = teacher connector to q_ref). Geometric certification, not a simulator render.",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)
    return meta


if __name__ == "__main__":
    fig3, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    res = {"synthetic": synthetic(out / "R1_fig3_synthetic.png"), "actual3d": actual3d(fig3, out / "R1_3d_home_returns.png"),
           "actual2d": actual2d(fig3, out / "R1_2d_home_returns.png")}
    (out / "R1_FIGURES.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, default=str)[:1500])
