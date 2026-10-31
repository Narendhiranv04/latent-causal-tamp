"""BXY-P-MIN-COLLECT figures, drawn only from BXY_SIDECAR_V2_PMIN rows, the collection ledger and the stored, re-verified witnesses:
coverage by stratum / prefix length (1, certified 0, budget 0, censored, not attempted kept distinct), four-cell table by query class,
CPU / worker timeline against the authorized caps, travel decomposition, and scene panels / a GIF for an order effect, an omission
effect, failed attempts and a complete multi-move joint witness."""
from __future__ import annotations

import collections
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_pmin_collect as C  # noqa: E402
import bxy_pmin_sidecar as S  # noqa: E402
import bxy_teacher as T  # noqa: E402
from bxy_pilot_viz import _scene, _tool  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_pmin_v1")
CAT = {"VERIFIED (1)": "#1baf7a", "certified 0": "#b4441c", "budget / planner 0": "#f2a33a", "censored": "#8c8c8c", "not attempted": "#e4e4e0"}
INK2 = "#52514e"


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return str(FIG / name)


def cat(r):
    if r.get("observed") and r.get("y") == 1:
        return "VERIFIED (1)"
    if r.get("observed") and r.get("y") == 0:
        return "certified 0" if r.get("negative_kind") == "CERTIFIED" else "budget / planner 0"
    return "censored" if r.get("teacher_status") in ("CENSORED", "CORRUPT_RESULT", "WITNESS_VERIFICATION_FAILED", "VERIFICATION_FAILED") else "not attempted"


def _stack(ax, groups, rows_by, title):
    x = np.arange(len(groups))
    bottom = np.zeros(len(groups))
    for c, col in CAT.items():
        v = np.array([sum(cat(r) == c for r in rows_by[g]) for g in groups], float)
        ax.bar(x, v, bottom=bottom, color=col, width=0.72, label=c, edgecolor="white", linewidth=1.5)
        for i, (b, h) in enumerate(zip(bottom, v)):
            if h >= max(12, 0.06 * max(len(rows_by[g]) for g in groups)):
                ax.text(i, b + h / 2, int(h), ha="center", va="center", fontsize=7, color="#0b0b0b")
        bottom += v
    ax.set_xticks(x, groups, fontsize=8)
    ax.set_title(title, loc="left", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)


def fig_coverage(sc, D):
    X, Y = sc["x_queries"], sc["y_queries"]
    st = lambda r: D["roots"][r["root"]]["stratum"]  # noqa: E731
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
    ks = ["K0", "K1", "K>=2", "None"]
    _stack(ax[0], ks, {k: [r for r in X if st(r) == k] for k in ks}, f"(a) X queries by verified-K stratum (n = {len(X)})")
    _stack(ax[1], ks, {k: [r for r in Y if st(r) == k] for k in ks}, f"(b) Y queries by verified-K stratum (n = {len(Y)})")
    L = sorted({len(r.get("ordered_actions") or D["roots"][r["root"]]["queries"][r["design_key"]]["seq"]) for r in X})
    ln = lambda r: len(r.get("ordered_actions") or D["roots"][r["root"]]["queries"][r["design_key"]]["seq"])  # noqa: E731
    _stack(ax[2], [str(v) for v in L], {str(v): [r for r in X if ln(r) == v] for v in L}, "(c) X queries by prefix length (relocations)")
    ax[0].set_ylabel("queries")
    ax[2].legend(fontsize=7, frameon=False, loc="upper right")
    fig.suptitle("BXY-P-MIN-COLLECT coverage: every frozen PMIN_DEV_MATCHED query (incl. reused P9) and its outcome class", x=0.01, ha="left", fontsize=10)
    return _save(fig, "01_coverage.png")


def fig_four_cell(sc):
    dec = [p for p in sc["paired"] if p.get("full_joint_success") is not None]
    cls = [("all", dec)] + [(c, [p for p in dec if c in (p.get("x_classes") or [])]) for c in ("complete", "reversal", "omission")]
    fig, ax = plt.subplots(1, 4, figsize=(14, 3.6), constrained_layout=True)
    for a, (name, ps) in zip(ax, cls):
        m = np.array([[sum(1 for p in ps if p["x"] == x and p["y"] == y) for y in (1, 0)] for x in (1, 0)])
        a.imshow(m, cmap="Greys", vmin=0, vmax=max(1, m.max()) * 1.6)
        for i in range(2):
            for j in range(2):
                a.text(j, i, f"{m[i, j]}", ha="center", va="center", fontsize=12, color="#0b0b0b", fontweight="bold" if (i, j) == (0, 0) else None)
        a.set_xticks([0, 1], ["Y=1", "Y=0"])
        a.set_yticks([0, 1], ["X=1", "X=0"])
        a.set_title(f"{name} (n = {len(ps)})", loc="left", fontsize=9)
    fig.suptitle("Matched decided (X, Y) pairs: X = prefix + connector to q_ref, Y = target from q_ref in the same edited scene; "
                 "bold = full joint success", x=0.01, ha="left", fontsize=10)
    return _save(fig, "02_four_cell.png")


def fig_cpu(sc):
    led = sc["manifest"]["collection"]["ledger"]
    fin = [e for e in led if e["event"] == "finish"]
    st = [e for e in led if e["event"] == "start"]
    t0 = min(e["t"] for e in st)
    fig, ax = plt.subplots(1, 3, figsize=(16, 4), constrained_layout=True)
    cpu = collections.defaultdict(float)
    for e in fin:
        cpu[e["root"]] += e["cpu_s"]
    v = sorted(cpu.values(), reverse=True)
    ax[0].bar(range(len(v)), v, color="#2a78d6", width=1.0)
    ax[0].axhline(C.LIMITS["root_cpu_s"], color="#b4441c", ls="--", lw=1)
    ax[0].text(len(v) * 0.4, C.LIMITS["root_cpu_s"] * 0.93, f"per-root cap {C.LIMITS['root_cpu_s']:.0f} CPU-s", fontsize=8, color=INK2)
    ax[0].set(xlabel="roots (sorted)", ylabel="worker CPU-s (RUSAGE)")
    ax[0].set_title(f"(a) per-root CPU, max {max(v):.0f}", loc="left", fontsize=9)
    fe = sorted(fin, key=lambda e: e["t"])
    ax[1].plot([(e["t"] - t0) / 60 for e in fe], np.cumsum([e["cpu_s"] for e in fe]), color="#2a78d6", lw=2)
    ax[1].axhline(C.LIMITS["cpu_s"], color="#b4441c", ls="--", lw=1)
    ax[1].text(1, C.LIMITS["cpu_s"] * 0.95, f"aggregate cap {C.LIMITS['cpu_s']:.0f}", fontsize=8, color=INK2)
    ax[1].axvline(C.LIMITS["wall_s"] / 60, color="#b4441c", ls=":", lw=1)
    ax[1].set(xlabel="wall minutes since first launch", ylabel="cumulative worker CPU-s")
    ax[1].set_title(f"(b) spend {sum(v):.0f} CPU-s of {C.LIMITS['cpu_s']:.0f}", loc="left", fontsize=9)
    ev = sorted([(e["t"], 1) for e in st] + [(e["t"], -1) for e in fin])
    tt, ww = [0.0], [0]
    for t, d in ev:
        tt += [(t - t0) / 60, (t - t0) / 60]
        ww += [ww[-1], ww[-1] + d]
    ax[2].plot(tt, ww, color="#2a78d6", lw=1.5)
    ax[2].axhline(C.LIMITS["workers"], color="#b4441c", ls="--", lw=1)
    ax[2].set(xlabel="wall minutes", ylabel="concurrent workers")
    ax[2].set_title("(c) workers (ramp 2 -> 4 -> 8)", loc="left", fontsize=9)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    return _save(fig, "03_cpu_and_workers.png")


def fig_travel(sc):
    xs = {r["design_key"]: r for r in sc["x_queries"]}
    J = [(p, xs[p["x_key"]]) for p in sc["paired"] if p.get("full_joint_success") == 1 and p.get("J_total") is not None]
    by = collections.defaultdict(list)
    for p, x in J:
        mv, cn = sum(x["travel_parts"]["J_move"]), x["travel_parts"]["J_connector"]
        by[len(x["ordered_actions"])].append((mv, cn, p["J_total"] - mv - cn))
    y0 = [r["J_target"] for r in sc["y_queries"] if r.get("observed") and r.get("y") == 1 and not r["hypothetical_poses"] and r.get("J_target")]
    ms = sorted(by)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4), constrained_layout=True)
    lab = ["relocations (incl. between-action)", "connector to q_ref", "target from q_ref"]
    col = ["#2a78d6", "#e87ba4", "#1baf7a"]
    xs_ = ["no-op"] + [str(m) for m in ms]
    parts = [[0.0] + [np.mean([t[i] for t in by[m]]) for m in ms] for i in range(3)]
    parts[2][0] = float(np.mean(y0)) if y0 else 0.0
    b = np.zeros(len(xs_))
    for i in range(3):
        ax[0].bar(xs_, parts[i], bottom=b, color=col[i], label=lab[i], edgecolor="white", linewidth=1.5)
        b += np.array(parts[i])
    for i, m in enumerate(["no-op"] + ms):
        n = len(y0) if m == "no-op" else len(by[m])
        ax[0].text(i, b[i] + 0.1, f"n={n}", ha="center", fontsize=7, color=INK2)
    ax[0].set(xlabel="corrective relocations m", ylabel="mean joint travel J (range-normalized L1)")
    ax[0].set_title("(a) complete-witness travel decomposition (full joint successes; no-op = Y0 target)", loc="left", fontsize=9)
    ax[0].legend(fontsize=7, frameon=False)
    tot = [p["J_total"] for p, _ in J]
    sh = [x["travel_parts"]["J_connector"] / p["J_total"] for p, x in J]
    ax[1].scatter(tot, sh, s=10, color="#e87ba4", alpha=0.7)
    ax[1].set(xlabel="J_total", ylabel="connector share of J_total")
    ax[1].set_title(f"(b) connector share per witness (median {np.median(sh):.2f}, n = {len(J)})", loc="left", fontsize=9)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    return _save(fig, "04_travel.png")


def done_steps(r):
    """Witness ids of the relocations that completed before an X failure (bxy_teacher records them per step)."""
    return [w for st in (r.get("steps") or []) for w in st["witness"]]


def _fit(ax, pad=0.04):
    xs = np.concatenate([ln.get_xdata() for ln in ax.lines] or [np.zeros(0)])
    ys = np.concatenate([ln.get_ydata() for ln in ax.lines] or [np.zeros(0)])
    if len(xs):
        (a, b), (c, d) = ax.get_xlim(), ax.get_ylim()
        ax.set(xlim=(min(a, xs.min() - pad), max(b, xs.max() + pad)), ylim=(min(c, ys.min() - pad), max(d, ys.max() + pad)))


def _panel(ax, E, k, rec, cells, title, q=None, x=None, ywit=None, note="", partial=None):
    import bd_viz as BV
    import viz
    s = _scene(k, rec, cells, T.qref(rec))
    BV._scene2d(ax, s, rec["goal_cell"], E["robot"], rec["roles"], rec["fixed_ids"], (), (), "", q=q)
    if x is not None and x.get("witness_relocations"):
        _tool(ax, E, [T.load_w(S.OUT, w) for w in x["witness_relocations"]], "#2a78d6")
    if x is not None and x.get("witness_connector"):
        _tool(ax, E, [T.load_w(S.OUT, x["witness_connector"])], "#e87ba4", 2.2)
        viz.draw_robot(ax, E["robot"], x["final_q_before_connector"], E["robot"].open_gap, alpha=0.25, zorder=6)
    if ywit:
        _tool(ax, E, [T.load_w(S.OUT, ywit)], "#1baf7a", 2.0)
    if partial:
        ws = [T.load_w(S.OUT, w) for w in partial]
        _tool(ax, E, ws, "#2a78d6")
        viz.draw_robot(ax, E["robot"], np.asarray(ws[-1]["q"][-1]), E["robot"].open_gap, alpha=0.45, zorder=6)
    _fit(ax)
    ax.set_title(title + ("\n" + note if note else ""), loc="left", fontsize=8)


def fig_order(sc, summ):
    """One discordant same-endpoint order group, preferring a certified failure."""
    E, R = T.env(), bd.roots()
    ex = summ["order"]["examples"]
    if not ex:
        return None
    g = next((e for e in ex if any(o[2] == "CERTIFIED_INFEASIBLE" for o in e["orders"])), ex[0])
    k, rec = g["root"], R[g["root"]]
    X = {tuple(map(tuple, r["ordered_actions"])): r for r in sc["x_queries"] if r["root"] == k and r.get("observed")}
    rows = [X[tuple(map(tuple, o[0]))] for o in g["orders"]][:3]
    y = next((r for r in sc["y_queries"] if r["design_key"] == rows[0]["parent_y_key"]), None)
    fig, ax = plt.subplots(1, len(rows) + 1, figsize=(5.2 * (len(rows) + 1), 5), constrained_layout=True)
    c0 = bd.cells0(rec)
    for a, r in zip(ax, rows):
        seq = [tuple(s) for s in r["ordered_actions"]]
        ws = done_steps(r) if r["y"] == 0 else []
        cells = {**c0, **dict(seq[:len(r.get("steps") or [])])} if r["y"] == 0 else {**c0, **dict(seq)}
        note = "X = 1: relocations (blue) + connector (pink)" if r["y"] == 1 else \
            f"X = 0 at {r['failed_phase']}: {r['teacher_status']} {r.get('detail') or ''}\n{len(r.get('steps') or [])} relocation(s) completed (blue), arm where it stopped"
        _panel(a, E, k, rec, cells, f"order {seq}", q=T.qref(rec) if r["y"] == 0 and not ws else None, x=r if r["y"] == 1 else None, note=note, partial=ws)
    yv = "unobserved" if y is None or not y.get("observed") else f"Y = {y['y']} ({y['teacher_status']})"
    _panel(ax[-1], E, k, rec, {**c0, **dict(tuple(s) for s in rows[0]["ordered_actions"])}, "shared Y node: same endpoint, target from q_ref",
           q=T.qref(rec), ywit=y.get("target_witness") if y else None, note=yv)
    fig.suptitle(f"Order effect at {k[-4:]}: same edited scene (one Y), different relocation orders (different X)", x=0.01, ha="left", fontsize=10)
    return _save(fig, f"05_order_effect_{k[-4:]}.png")


def fig_omission(sc, summ):
    """A 2-move candidate with a nonadditive target interaction (Y_AB = 1, both single omissions 0), else any Y 1 -> 0 omission."""
    E, R = T.env(), bd.roots()
    ex = [e for e in summ["omission"]["two_move_nonadditive_examples"] if e["Y_AB"] == 1 and e["Y_A"] == 0 and e["Y_B"] == 0]
    if not ex:
        return None
    e = ex[0]
    k, rec, s = e["root"], R[e["root"]], [tuple(a) for a in e["seq"]]
    Y = {r["design_key"]: r for r in sc["y_queries"]}
    c0 = bd.cells0(rec)
    fig, ax = plt.subplots(1, 4, figsize=(20, 5), constrained_layout=True)
    for a, (lab, q) in zip(ax, [("S0 (no edit)", []), (f"omit {s[0][0]}: only {s[1]}", [s[1]]), (f"omit {s[1][0]}: only {s[0]}", [s[0]]), (f"both {s}", s)]):
        y = Y.get(T.ykey(k, rec, q))
        _panel(a, E, k, rec, {**c0, **dict(q)}, lab, q=T.qref(rec), ywit=y.get("target_witness") if y else None,
               note=f"Y = {y['y']} ({y['teacher_status']})" if y else "unobserved")
    fig.suptitle(f"Omission contrast at {k[-4:]}: target from q_ref succeeds only when both relocations are applied (interaction +1)", x=0.01, ha="left", fontsize=10)
    return _save(fig, f"06_omission_{k[-4:]}.png")


def fig_failures(sc):
    """A relocation failure (X) and a target failure (Y) with their recorded phase / kind."""
    E, R = T.env(), bd.roots()
    xf = next((r for r in sc["x_queries"] if r.get("observed") and r["y"] == 0 and len(r.get("steps") or []) >= 1), None)
    yf = next((r for r in sc["y_queries"] if r.get("observed") and r["y"] == 0 and r.get("negative_kind") == "CERTIFIED"), None) or \
        next((r for r in sc["y_queries"] if r.get("observed") and r["y"] == 0), None)
    fig, ax = plt.subplots(1, 2, figsize=(11, 5), constrained_layout=True)
    if xf:
        rec, seq = R[xf["root"]], [tuple(a) for a in xf["ordered_actions"]]
        _panel(ax[0], E, xf["root"], rec, {**bd.cells0(rec), **dict(seq[:len(xf["steps"])])}, f"X failure {xf['root'][-4:]} {seq}", q=None,
               note=f"X = 0 at {xf['failed_phase']} ({xf['teacher_status']}, {xf['negative_kind']})\n{len(xf['steps'])} completed relocation(s) (blue), arm where it stopped",
               partial=done_steps(xf))
    if yf:
        rec = R[yf["root"]]
        _panel(ax[1], E, yf["root"], rec, {**bd.cells0(rec), **{o: int(c) for o, c in yf["hypothetical_poses"].items()}},
               f"Y failure {yf['root'][-4:]} edit {yf['hypothetical_poses']}", q=T.qref(rec), note=f"Y = 0 ({yf['teacher_status']}, {yf['negative_kind']}); no target witness exists")
    return _save(fig, "07_failed_attempts.png")


def gif_full(sc):
    """A complete multi-move joint witness: relocations, connector, then the target from q_ref (all stored, re-verified records)."""
    import bd_viz as BV
    import geometry as ge
    import motion as mo
    import viz
    from dataclasses import replace
    from PIL import Image
    E, R = T.env(), bd.roots()
    xs = {r["design_key"]: r for r in sc["x_queries"]}
    ys = {r["design_key"]: r for r in sc["y_queries"]}
    cand = [p for p in sc["paired"] if p.get("full_joint_success") == 1 and len(xs[p["x_key"]]["ordered_actions"]) >= 3]
    if not cand:
        return None
    p = max(cand, key=lambda p: (len(xs[p["x_key"]]["ordered_actions"]), -p["J_total"]))
    x, y, k = xs[p["x_key"]], ys[p["y_key"]], p["root"]
    rec = R[k]
    seq = [tuple(a) for a in x["ordered_actions"]]
    parts = [("relocation", o, T.load_w(S.OUT, w)) for (o, _), w in zip(seq, x["witness_relocations"])]
    parts += [("connector", None, T.load_w(S.OUT, x["witness_connector"])), ("target from q_ref", "t0", T.load_w(S.OUT, y["target_witness"]))]
    pts = np.array([pp for _, _, a in parts for qq, _, _ in mo.samples(a, 24) for pp in ge.fk(E["robot"], qq)[0]])
    f0, a0 = plt.subplots()
    BV._scene2d(a0, _scene(k, rec, bd.cells0(rec), T.qref(rec)), rec["goal_cell"], E["robot"], rec["roles"], rec["fixed_ids"], (), (), "", q=T.qref(rec))
    lim = ((min(a0.get_xlim()[0], pts[:, 0].min() - 0.12), max(a0.get_xlim()[1], pts[:, 0].max() + 0.12)),
           (min(a0.get_ylim()[0], pts[:, 1].min() - 0.12), max(a0.get_ylim()[1], pts[:, 1].max() + 0.12)))
    plt.close(f0)
    cells, frames = bd.cells0(rec), []
    for lab, o, a in parts:
        for qq, g, ph in mo.samples(a, 22 if lab != "connector" else 12):
            held = o if ph == "carry" else None
            fig, ax = plt.subplots(figsize=(6.2, 5))
            s = _scene(k, rec, cells, qq)
            s = replace(s, objects=tuple(ob for ob in s.objects if ob.id != held))
            BV._scene2d(ax, s, rec["goal_cell"], E["robot"], rec["roles"], rec["fixed_ids"], (), (),
                        f"{k[-4:]} {lab} {o or ''} [{ph}]  X=1, Y=1 (re-verified), J_total {p['J_total']:.2f}")
            viz.draw_robot(ax, E["robot"], qq, g, alpha=0.85, zorder=8)
            if held:
                ax.add_patch(plt.Circle(ge.tool_point(E["robot"], qq, tuple(a["held_local"])), 0.024, fc="#f6b26b" if held != "t0" else "#1baf7a", ec="k", zorder=9))
            ax.set(xlim=lim[0], ylim=lim[1])
            fig.canvas.draw()
            frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3]))
            plt.close(fig)
        if lab == "relocation":
            cells = {**cells, o: dict(seq)[o]}
    FIG.mkdir(parents=True, exist_ok=True)
    name = f"08_full_joint_witness_{k[-4:]}_m{len(seq)}.gif"
    frames[0].save(FIG / name, save_all=True, append_images=frames[1:], duration=80, loop=0)
    return str(FIG / name)


def all_figures():
    sc = json.loads((S.OUT / f"{S.SIDECAR}.json").read_text())
    summ = json.loads((S.OUT / "PMIN_EVIDENCE_SUMMARY.json").read_text())
    D = C.design()
    cls = {key: q["classes"] for d in D["roots"].values() for key, q in d["queries"].items()}
    sc["paired"] = [p | {"x_classes": cls[p["x_key"]]} for p in sc["paired"]]            # P9-reused rows carry no class: frozen design
    return [f for f in (fig_coverage(sc, D), fig_four_cell(sc), fig_cpu(sc), fig_travel(sc), fig_order(sc, summ), fig_omission(sc, summ),
                        fig_failures(sc), gif_full(sc)) if f]


if __name__ == "__main__":
    print(all_figures())
