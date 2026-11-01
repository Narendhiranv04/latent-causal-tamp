"""BXY-P16 figures: access-closure construction geometry, realized difficulty (intended vs analytic vs verified K) against P-min / P15,
prefix-complete physical stories from recorded witnesses, same-endpoint order twins, harmful vs neutral edits, X/Y cells, negative kinds
(certified vs budget), connector failures, and the P16 compute ledger. Every 'realized motion' drawn is a replayed teacher witness."""
from __future__ import annotations

import collections
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_p16 as G  # noqa: E402
import bxy_pmin_sidecar as S  # noqa: E402
import bxy_teacher as T  # noqa: E402
from bxy_p11_viz import _arrows  # noqa: E402
from bxy_p12_viz import _clean  # noqa: E402
from bxy_p14_run import _swap  # noqa: E402
from bxy_pmin_viz import _panel, done_steps  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_p16_v1")
INK, MUTED = "#222", "#777"
KC = {"0": "#c9c9c3", "1": "#8fb8e8", "2": "#2a78d6", "3": "#f2a33a", "4": "#b4441c", "None": "#7d3c98", "UNOBSERVED_Y0": "#9e9e9e"}


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def _cells(ax, cells, color, alpha, z=0.5):
    for c in cells:
        ax.add_patch(matplotlib.patches.Rectangle(((c % 8) * 0.08, (c // 8) * 0.08), 0.08, 0.08, color=color, alpha=alpha, lw=0, zorder=z))


def _summ(waves):
    return {w: json.loads((G.wdir(w) / "SUMMARY.json").read_text()) for w in waves if (G.wdir(w) / "SUMMARY.json").exists()}


def _res(w, k):
    return G.results(w, k)


def _grasp_q(rec, cells, idx, kind="pick"):
    """Arm configuration of declared candidate idx (skill.directions order) for T's pick at its source / place at the goal."""
    import geometry as ge
    import skill as sk
    E = T.env()
    rob, p = E["robot"], sk.params(E["cfg"])
    phi, b = sk.directions(p)[idx]
    s = G._ideal_scene(rec, cells)
    xy = s.get("t0").xy_m if kind == "pick" else s.lattice.center(rec["goal_cell"])
    return sk._ik(rob, xy, (rob.grasp_x, 0.0), phi).get(b)


# ------------------------------------------------------------------ 1. access-closure construction
def fig_construction(w, R):
    """S0 (all T grasp modes closed), the analytic kill cells of the reopened pick candidate, and the intended repair (ideal scene, grasp pose)."""
    import viz
    E = T.env()
    pick = [k for k in sorted(R) if R[k]["construction"]["K_geom"] >= 3 and R[k]["construction"]["forced_order"]][:1] + \
        [k for k in sorted(R) if R[k]["spec"]["mechanism"] == "near_closed"][:1]
    fig, ax = plt.subplots(len(pick), 2, figsize=(12, 5.6 * len(pick)), constrained_layout=True, squeeze=False)
    for row, k in zip(ax, pick):
        rec, C = R[k], R[k]["construction"]
        c0 = bd.cells0(rec)
        with _swap(S, "OUT", G.wdir(w)):
            _panel(row[0], E, k, rec, c0, f"{k[-8:]}  S0: {C['S0_open']['pick']} open T-pick modes, {C['S0_open']['place']} open place modes "
                   f"(mechanism {rec['spec']['mechanism']}, K_geom {C['K_geom']})", q=T.qref(rec))
        if C["options"] and C["options"][0]["order"]:
            o = C["options"][0]
            km = G.access_map("pick", c0["t0"])
            _cells(row[0], km["kill"][str(o["pick"])], "#b4441c", 0.18)
            rep = next(c for c in rec["catalogue_v21"] if c["kind"] == "repair")
            seq = [tuple(a) for a in rep["seq"]]
            _arrows(row[0], rec, seq)
            cells = {**c0, **dict(seq)}
            with _swap(S, "OUT", G.wdir(w)):
                _panel(row[1], E, k, rec, cells, f"ideal scene after the intended {len(seq)}-move repair (geometry only):\nreopened grasp "
                       f"candidate {o['pick']} drawn at its grasp pose", q=T.qref(rec))
            q = _grasp_q(rec, cells, o["pick"])
            if q is not None:
                viz.draw_robot(row[1], E["robot"], q, E["robot"].open_gap, alpha=0.55, zorder=7)
            row[0].text(0.01, 0.01, "red cells: discs there kill the reopened pick candidate (analytic kill set)", transform=row[0].transAxes, fontsize=7.5)
        else:
            harm = [h["cell"] for h in C["harmful_cells"]]
            _cells(row[0], harm, "#b4441c", 0.35)
            row[0].text(0.01, 0.01, f"red: harmful cells (occupying one closes every open {C['harmful_cells'][0]['closes'] if harm else ''} mode)",
                        transform=row[0].transAxes, fontsize=7.5)
            hc = next((c for c in rec["catalogue_v21"] if c["kind"] == "harmful_edit"), None)
            if hc:
                seq = [tuple(a) for a in hc["seq"]]
                _arrows(row[0], rec, seq)
                with _swap(S, "OUT", G.wdir(w)):
                    _panel(row[1], E, k, rec, {**c0, **dict(seq)}, "ideal scene after the designed harmful edit (geometry only)", q=T.qref(rec))
    fig.suptitle("BXY_GEN_V21 access closure: blockers chosen from analytic grasp-mode kill sets (no teacher label used)", x=0.01, ha="left")
    return _save(fig, "01_access_closure_construction.png")


# ------------------------------------------------------------------ 2. realized difficulty vs P-min / P15
def fig_difficulty(S_):
    rows = [r for s in S_.values() for r in s["rows"] if r["results"]]
    p15 = json.loads(Path("runs/approach_b/bxy_p15_v1/PILOT_SUMMARY.json").read_text())["verified_K"]
    pmin = collections.Counter(str(r["verified_K"]) if r["verified_K"] is not None else "None" for r in bd.roots().values()
                               if bd.split_of(r) in ("train", "val") and r.get("verified_K") is not None) if False else None
    v21 = collections.Counter(str(r["verified_K"]) for r in rows)
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.8))
    levels = ["0", "1", "2", "3", "4", "None", "UNOBSERVED_Y0"]
    for i, (name, c) in enumerate((("P15 V2 pilot (28)", p15), (f"P16 V2.1 ({len(rows)})", v21))):
        n, left = sum(c.values()), 0
        for lv in levels:
            v = c.get(lv, 0)
            if v:
                ax[0].barh(i, v / n, left=left, color=KC[lv], edgecolor="white", label=lv if i == 1 else None)
                left += v / n
    ax[0].set_yticks([0, 1], ["P15 V2 pilot", "P16 V2.1"])
    ax[0].legend(title="verified K (fewest verified moves\nwithin the finite catalogue)", fontsize=7, title_fontsize=7, frameon=False, ncol=4)
    ax[0].set(xlabel="fraction of labelled roots", title="realized difficulty (teacher-verified)")
    kg = collections.Counter((r["K_geom"], str(r["verified_K"])) for r in rows)
    ks = sorted({a for a, _ in kg})
    for i, a in enumerate(ks):
        left = 0
        for lv in levels:
            v = kg.get((a, lv), 0)
            if v:
                ax[1].bar(i, v, bottom=left, color=KC[lv], edgecolor="white")
                left += v
    ax[1].set_xticks(range(len(ks)), [f"K_geom {a}" for a in ks])
    ax[1].set(ylabel="roots", title="analytic intent (K_geom) vs verified K")
    mech = collections.defaultdict(collections.Counter)
    for r in rows:
        mech[r["spec"]["mechanism"]][str(r["verified_K"])] += 1
    ms = sorted(mech)
    for i, m in enumerate(ms):
        left = 0
        for lv in levels:
            v = mech[m].get(lv, 0)
            if v:
                ax[2].bar(i, v, bottom=left, color=KC[lv], edgecolor="white")
                left += v
    ax[2].set_xticks(range(len(ms)), ms, rotation=20)
    ax[2].set(ylabel="roots", title="verified K by construction mechanism")
    for a in ax:
        _clean(a)
    fig.tight_layout()
    return _save(fig, "02_realized_difficulty.png")


# ------------------------------------------------------------------ 3. prefix-complete physical story
def fig_prefix_story(w, R, Sm):
    """original infeasibility -> each correction prefix (ideal scene, independently queried Y) -> complete repair with the recorded
    relocation + connector (X) and target-from-q_ref (Y) witnesses."""
    E = T.env()
    cand = [r for r in Sm["rows"] if r["y0"] == 0 and r["repair"] and r["repair"]["x"] == 1 and r["repair"]["y"] == 1 and r["repair"]["m"] >= 2]
    if not cand:
        return None
    r = max(cand, key=lambda r: (r["repair"]["m"], r["root"]))
    k, rec = r["root"], R[r["root"]]
    res = _res(w, k)
    rep = next(c for c in rec["catalogue_v21"] if c["kind"] == "repair")
    seq = [tuple(a) for a in rep["seq"]]
    c0 = bd.cells0(rec)
    n = len(seq) + 1
    fig, ax = plt.subplots(1, n, figsize=(5.0 * n, 5.4), constrained_layout=True)
    with _swap(S, "OUT", G.wdir(w)):
        y0 = res.get(T.ykey(k, rec, []), {})
        _panel(ax[0], E, k, rec, c0, f"S0: Y0 = {y0.get('y')} ({y0.get('teacher_status')})", q=T.qref(rec))
        _arrows(ax[0], rec, seq)
        for t in range(1, n):
            pre = seq[:t]
            xr, yr = res.get(T.xkey(k, rec, pre), {}), res.get(T.ykey(k, rec, pre), {})
            full = t == n - 1
            note = f"X(prefix + connector) = {xr.get('y')} [{xr.get('teacher_status')}]\nY(hypothetical, from q_ref) = {yr.get('y')} [{yr.get('teacher_status')}]"
            _panel(ax[t], E, k, rec, {**c0, **dict(pre)}, f"prefix {t}/{len(seq)}: " + " -> ".join(f"{o}@{d}" for o, d in pre), q=None if xr.get("y") == 1 else T.qref(rec),
                   x=xr if xr.get("y") == 1 else None, ywit=yr.get("target_witness") if yr.get("y") == 1 else None, note=note + ("\nfull repair: witnesses compose at q_ref" if full else ""))
    fig.suptitle(f"{k}: prefix-complete supervision of a verified {len(seq)}-move repair (blue relocations, pink connector to q_ref, green target; "
                 "all recorded, replayed witnesses)", x=0.01, ha="left", fontsize=10)
    return _save(fig, f"03_prefix_story_{k[-4:]}.png")


# ------------------------------------------------------------------ 4. order twins
def fig_order_twins(w, R, Sm):
    E = T.env()
    ex = [(r, d) for r in Sm["rows"] for d in r["discordant"]]
    if not ex:
        return None
    ex.sort(key=lambda rd: (not any(o[2] == "CERTIFIED" for o in rd[1]["orders"]), rd[0]["root"]))
    r, d = ex[0]
    k, rec = r["root"], R[r["root"]]
    res = _res(w, k)
    cats = {c["sig"]: [tuple(a) for a in c["seq"]] for c in rec["catalogue_v21"]}
    orders = [cats[o[0]] for o in d["orders"]][:2]
    c0 = bd.cells0(rec)
    fig, ax = plt.subplots(1, 3, figsize=(16, 5.4), constrained_layout=True)
    with _swap(S, "OUT", G.wdir(w)):
        for a, seq in zip(ax, orders):
            xr = res.get(T.xkey(k, rec, seq), {})
            if xr.get("y") == 1:
                _panel(a, E, k, rec, {**c0, **dict(seq)}, "order " + " -> ".join(f"{o}@{dd}" for o, dd in seq), x=xr, note="X = 1 (relocations + connector replayed)")
            else:
                ws = done_steps(xr)
                done = len(xr.get("steps") or [])
                _panel(a, E, k, rec, {**c0, **dict(seq[:done])}, "order " + " -> ".join(f"{o}@{dd}" for o, dd in seq), q=T.qref(rec) if not ws else None, partial=ws,
                       note=f"X = 0 at {xr.get('failed_phase')}: {xr.get('teacher_status')} ({xr.get('negative_kind')})")
            _arrows(a, rec, seq)
        yr = res.get(T.ykey(k, rec, orders[0]), {})
        _panel(ax[2], E, k, rec, {**c0, **dict(orders[0])}, "shared Y node (same endpoint, target from q_ref)", q=T.qref(rec),
               ywit=yr.get("target_witness") if yr.get("y") == 1 else None, note=f"Y = {yr.get('y')} ({yr.get('teacher_status')})")
    fig.suptitle(f"{k}: F1-admissible same-endpoint orders with different measured X (one shared Y)", x=0.01, ha="left")
    return _save(fig, f"04_order_twins_{k[-4:]}.png")


# ------------------------------------------------------------------ 5. harmful vs neutral
def fig_harmful(w, R, Sm):
    E = T.env()
    for r in Sm["rows"]:
        if r["y0"] != 1:
            continue
        rows = {x["kind"]: x for x in r["rows"]}
        h, n = rows.get("harmful_edit"), rows.get("neutral_edit")
        if h and n and h["y"] == 0 and n["y"] == 1:
            break
    else:
        return None
    k, rec = r["root"], R[r["root"]]
    res, c0 = _res(w, k), bd.cells0(rec)
    cats = {c["sig"]: [tuple(a) for a in c["seq"]] for c in rec["catalogue_v21"]}
    fig, ax = plt.subplots(1, 3, figsize=(16, 5.4), constrained_layout=True)
    with _swap(S, "OUT", G.wdir(w)):
        y0 = res.get(T.ykey(k, rec, []), {})
        _panel(ax[0], E, k, rec, c0, f"S0: Y0 = 1 (target from q_ref)", q=T.qref(rec), ywit=y0.get("target_witness"))
        for a, row, lab in ((ax[1], h, "harmful edit"), (ax[2], n, "neutral edit")):
            seq = cats[row["sig"]]
            yr = res.get(T.ykey(k, rec, seq), {})
            _panel(a, E, k, rec, {**c0, **dict(seq)}, f"{lab}: " + " ".join(f"{o}@{d}" for o, d in seq), q=T.qref(rec),
                   ywit=yr.get("target_witness") if yr.get("y") == 1 else None, note=f"Y_edit = {yr.get('y')} ({yr.get('teacher_status')}, {yr.get('negative_kind')})")
            _arrows(a, rec, seq)
    fig.suptitle(f"{k}: same object, two destinations -- a harmful (Y 1 -> 0) and a neutral (Y stays 1) edit, both teacher-labelled", x=0.01, ha="left")
    return _save(fig, f"05_harmful_vs_neutral_{k[-4:]}.png")


# ------------------------------------------------------------------ 6-8. cells, negatives, ledger
def fig_cells_negatives(S_):
    rows = [r for s in S_.values() for r in s["rows"] if r["results"]]
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.8))
    mech = sorted({r["spec"]["mechanism"] for r in rows})
    cols = {"00": "#c9c9c3", "01": "#8fb8e8", "10": "#f2a33a", "11": "#1baf7a"}
    for i, m in enumerate(mech):
        c = collections.Counter()
        for r in rows:
            if r["spec"]["mechanism"] == m:
                c.update(r["cells"])
        left = 0
        for cell in ("00", "01", "10", "11"):
            ax[0].bar(i, c.get(cell, 0), bottom=left, color=cols[cell], edgecolor="white", label=f"(X,Y)=({cell[0]},{cell[1]})" if i == 0 else None)
            left += c.get(cell, 0)
    ax[0].set_xticks(range(len(mech)), mech, rotation=20)
    ax[0].legend(frameon=False, fontsize=7.5)
    ax[0].set(ylabel="matched candidate (X, Y) pairs", title="all four X/Y cells by mechanism")
    roots_cell = {cell: sum(r["cells"].get(cell, 0) > 0 for r in rows) for cell in cols}
    ax[1].bar(range(4), [roots_cell[c] for c in cols], color=list(cols.values()))
    ax[1].set_xticks(range(4), [f"({c[0]},{c[1]})" for c in cols])
    ax[1].set(ylabel="independent roots containing the cell", title="X/Y cells: independent-root coverage")
    neg = collections.Counter()
    for r in rows:
        for side in ("x_neg", "y_neg"):
            for k, v in r[side].items():
                neg[f"{side[0].upper()}: {k}"] += v
    ks = sorted(neg)
    ax[2].bar(range(len(ks)), [neg[k] for k in ks], color="#7d3c98")
    ax[2].set_xticks(range(len(ks)), ks, rotation=20, fontsize=7.5)
    ax[2].set(title=f"negatives: certified vs fixed-budget planner failure\n(connector failures: {sum(r['connector_failures'] for r in rows)})")
    for a in ax:
        _clean(a)
    fig.tight_layout()
    return _save(fig, "06_xy_cells_and_negatives.png")


def fig_prefix_coverage(S_):
    rows = [r for s in S_.values() for r in s["rows"] if r["results"] and r["repair"] and r["repair"]["m"] >= 2]
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.8))
    for i, r in enumerate(sorted(rows, key=lambda r: (r["repair"]["m"], r["root"]))):
        ys = [r["y0"]] + r["repair"]["prefix_y"] + [r["repair"]["y"]]
        xs = [1] + r["repair"]["prefix_x"] + [r["repair"]["x"]]
        for t, (yv, xv) in enumerate(zip(ys, xs)):
            ax[0].scatter(t, i, s=60, marker="s", c={1: "#1baf7a", 0: "#b4441c", None: "#ddd"}[yv], edgecolor=INK, lw=0.4)
            ax[1].scatter(t, i, s=60, marker="o", c={1: "#2a78d6", 0: "#b4441c", None: "#ddd"}[xv], edgecolor=INK, lw=0.4)
    for a, t in zip(ax, ("Y at each stopping prefix (target from q_ref)", "X at each stopping prefix (relocations + connector)")):
        a.set(xlabel="prefix length (0 = S0 ... m = full intended repair)", ylabel="root (intended repair m >= 2)", title=t)
        _clean(a)
    ax[0].text(0.99, 0.01, "green 1 / red 0 / grey unobserved", transform=ax[0].transAxes, ha="right", fontsize=7.5)
    fig.tight_layout()
    return _save(fig, "07_prefix_coverage.png")


def fig_ledger(S_):
    sp = G.spent()
    rows = [r for s in S_.values() for r in s["rows"] if r["results"]]
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.6))
    parts = [("access maps", sp["maps_cpu_s"]), ("construction + audits", sp["construction_cpu_s"]), ("teacher workers", sp["collection_cpu_s"])]
    left = 0
    for (n, v), c in zip(parts, ("#8fb8e8", "#2a78d6", "#f2a33a")):
        ax[0].barh(0, v, left=left, color=c, label=f"{n}: {v:.0f}")
        left += v
    ax[0].axvline(G.LIMITS["cpu_s"], color="#b4441c", ls="--")
    ax[0].legend(frameon=False, fontsize=8)
    ax[0].set(xlabel="CPU-s", yticks=[], title=f"P16 aggregate CPU {sp['total_cpu_s']:.0f} / {G.LIMITS['cpu_s']:.0f} (wall {sp['total_wall_s']:.0f} / {G.LIMITS['wall_s']:.0f} s)")
    ax[1].hist([r["cpu_s"] for r in rows], bins=15, color="#2a78d6")
    ax[1].axvline(G.LIMITS["root_cpu_s"], color="#b4441c", ls="--")
    ax[1].set(xlabel="teacher CPU-s per labelled root", ylabel="roots", title="per-root cost (cap 800)")
    for a in ax:
        _clean(a)
    fig.tight_layout()
    return _save(fig, "08_compute_ledger.png")


def all_figures(waves) -> list:
    S_ = _summ(waves)
    out = []
    for w in waves:
        R = G.roots_of(w)
        if w == waves[0]:
            out.append(fig_construction(w, R))
    out += [fig_difficulty(S_), fig_cells_negatives(S_), fig_prefix_coverage(S_), fig_ledger(S_)]
    for w, Sm in S_.items():
        R = G.roots_of(w)
        out += [fig_prefix_story(w, R, Sm), fig_order_twins(w, R, Sm), fig_harmful(w, R, Sm)]
    return [o for o in out if o]


if __name__ == "__main__":
    import sys
    print("\n".join(all_figures(sys.argv[1:])))
