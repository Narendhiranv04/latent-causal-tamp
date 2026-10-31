"""BXY-P15 figures: pilot scenes with their construction geometry and outcome-blind catalogue, recorded pilot witnesses, catalogue / query
composition, realized pilot outcomes and the frozen confirmatory plan. Development pilot only; nothing from the confirmatory namespace."""
from __future__ import annotations

import collections
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_p15 as G  # noqa: E402
import bxy_pmin_sidecar as S  # noqa: E402
import bxy_teacher as T  # noqa: E402
from bxy_p11_viz import _arrows  # noqa: E402
from bxy_p12_viz import _clean  # noqa: E402
from bxy_p14_run import _swap  # noqa: E402
from bxy_pmin_viz import _panel  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_p15_v1")
INK = "#222"
KC = {0: "#9e9e9e", 1: "#8fb8e8", 2: "#2a78d6", 3: "#f2a33a", 4: "#b4441c"}


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def _cells(ax, cells, color, alpha):
    for c in cells:
        ax.add_patch(matplotlib.patches.Rectangle(((c % 8) * 0.08, (c // 8) * 0.08), 0.08, 0.08, color=color, alpha=alpha, lw=0, zorder=0.5))


def fig_pilot_scenes(R):
    """Six pilot roots across K_intent / trap: S0, reference target sweep (green tint), q_ref footprint (pink tint), intended blockers,
    and the first outcome-blind catalogue candidates as numbered arrows."""
    E = T.env()
    pick, seen = [], set()
    for k, r in sorted(R.items(), key=lambda kv: (kv[1]["spec"]["K_intent"], kv[1]["spec"]["trap"], kv[0])):
        key = (r["spec"]["K_intent"], r["spec"]["trap"])
        if key not in seen:
            seen.add(key)
            pick.append(k)
    pick = pick[:6]
    fig, ax = plt.subplots(2, 3, figsize=(18, 11.5), constrained_layout=True)
    for a, k in zip(ax.flat, pick):
        r = R[k]
        c0 = bd.cells0(r)
        with _swap(S, "OUT", G.OUT / "pilot"):
            _panel(a, E, k, r, c0, f"{k}\nK_intent {r['spec']['K_intent']} / {r['spec']['mechanism']} / trap {r['spec']['trap']} / "
                   f"{len(r['catalogue_v2'])} candidates, {len(r['design_v2']['queries'])} queries", q=T.qref(r))
        _cells(a, set().union(*map(set, r["construction"]["reference_sweep"].values())), "#1baf7a", 0.12)
        _cells(a, r["construction"]["q_ref_footprint"], "#e87ba4", 0.25)
        multi = next((c for c in r["catalogue_v2"] if len(c["seq"]) >= 2), r["catalogue_v2"][0] if r["catalogue_v2"] else None)
        if multi:
            _arrows(a, r, [tuple(x) for x in multi["seq"]])
            a.text(0.01, 0.01, f"arrows: {multi['kind']} {multi['sig']}", transform=a.transAxes, fontsize=7.5, color=INK)
    for a in ax.flat[len(pick):]:
        a.axis("off")
    fig.suptitle("BXY_GEN_V2 development pilot scenes (construction geometry: green = target-only reference sweep, pink = q_ref arm footprint; "
                 "no teacher outcome used)", x=0.01, ha="left")
    return _save(fig, "01_pilot_scenes.png")


def fig_catalogue(R, gen):
    kinds = collections.Counter(c["kind"] for r in R.values() for c in r["catalogue_v2"])
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.8))
    ks = sorted(kinds, key=lambda x: -kinds[x])
    ax[0].barh(range(len(ks)), [kinds[k] for k in ks], color="#2a78d6")
    ax[0].set_yticks(range(len(ks)), ks, fontsize=8)
    ax[0].invert_yaxis()
    ax[0].set(xlabel="candidates over all pilot roots", title="outcome-blind catalogue: candidate kinds")
    acc = [a for a in gen["attempts"] if a["accepted"]]
    ax[1].scatter([a["candidates"] for a in acc], [a["queries"] for a in acc], c=[KC[a["spec"]["K_intent"]] for a in acc], s=40, edgecolor=INK, lw=0.5)
    ax[1].axhline(G.MAX_QUERIES, color="#b4441c", ls="--", lw=1)
    ax[1].legend(handles=[matplotlib.patches.Patch(color=KC[k], label=f"K_intent {k}") for k in KC], frameon=False, fontsize=7.5)
    ax[1].set(xlabel="complete candidates per root", ylabel="teacher queries per root (X + Y)", title=f"query design per root (cap {G.MAX_QUERIES})")
    rej = collections.Counter(a["reject"].split(":")[0] for a in gen["attempts"] if not a["accepted"])
    lab = ["accepted"] + sorted(rej)
    ax[2].bar(range(len(lab)), [len(acc)] + [rej[x] for x in lab[1:]], color=["#1baf7a"] + ["#b4441c"] * len(rej))
    ax[2].set_xticks(range(len(lab)), lab, rotation=20, fontsize=7.5)
    ax[2].set(title=f"construction attempts ({len(gen['attempts'])} slots, every rejection recorded)")
    for a in ax:
        _clean(a)
    fig.tight_layout()
    return _save(fig, "02_catalogue_and_queries.png")


def fig_outcomes(Sm):
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.8))
    levels = ["0", "1", "2", "3", "4", "5", "6", "None", "UNOBSERVED_Y0"]
    col = {"0": "#d8d8d2", "1": "#8fb8e8", "2": "#2a78d6", "3": "#f2a33a", "4": "#b4441c", "None": "#7d3c98", "UNOBSERVED_Y0": "#9e9e9e"}
    for i, kint in enumerate(sorted(Sm["by_K_intent"], key=int)):
        c = Sm["by_K_intent"][kint]
        left = 0
        for lv in levels:
            v = c.get(lv, 0)
            if v:
                ax[0].bar(i, v, bottom=left, color=col.get(lv, "#555"), edgecolor="white", label=lv if lv not in ax[0].get_legend_handles_labels()[1] else None)
                left += v
    ax[0].set_xticks(range(len(Sm["by_K_intent"])), [f"K_intent {k}" for k in sorted(Sm["by_K_intent"], key=int)])
    ax[0].legend(title="realized K (fewest verified moves;\nNone = no verified repair in catalogue)", frameon=False, fontsize=7, title_fontsize=7)
    ax[0].set(ylabel="pilot roots", title="construction intent vs realized catalogue K (teacher-verified)")
    rows = Sm["rows"]
    ax[1].hist([r["cpu_s"] for r in rows], bins=12, color="#2a78d6")
    ax[1].set(xlabel="teacher CPU-s per root (process time of its queries)", ylabel="roots",
              title=f"collection cost: {Sm['collection_cpu_s']:.0f} CPU-s workers + {Sm['construction_cpu_s']:.0f} construction")
    neg = collections.Counter()
    for r in rows:
        for side in ("x_neg", "y_neg"):
            for k, v in r[side].items():
                neg[f"{side[0].upper()}: {k}"] += v
    ks = sorted(neg)
    ax[2].bar(range(len(ks)), [neg[k] for k in ks], color="#7d3c98")
    ax[2].set_xticks(range(len(ks)), ks, rotation=20, fontsize=7.5)
    ax[2].set(title="negative labels: certified vs fixed-budget planner failure (not impossibility)")
    for a in ax:
        _clean(a)
    fig.tight_layout()
    return _save(fig, "03_pilot_outcomes.png")


def fig_witness(R, Sm):
    """A pilot root with a verified multi-move repair: S0 and the repair's recorded relocation / connector / target witnesses."""
    row = next((r for r in Sm["rows"] if r["y0"] == 0 and isinstance(r["verified_K"], int) and r["verified_K"] >= 2), None) or \
        next((r for r in Sm["rows"] if r["y0"] == 0 and r["verified_repairs"]), None)
    if row is None:
        return None
    k, rec, E = row["root"], R[row["root"]], T.env()
    res = {json.loads(f.read_text())["design_key"]: json.loads(f.read_text()) for f in (G.OUT / "results" / k).glob("*.json")}
    best = None
    for c in rec["catalogue_v2"]:
        seq = [tuple(a) for a in c["seq"]]
        x, y = res.get(T.xkey(k, rec, seq)), res.get(T.ykey(k, rec, seq))
        if c["f1_complete_ok"] and x and y and x.get("y") == 1 and y.get("y") == 1 and (best is None or len(seq) > len(best[0])):
            best = (seq, x, y, c)
    if best is None:
        return None
    seq, x, y, c = best
    c0 = bd.cells0(rec)
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.8), constrained_layout=True)
    with _swap(S, "OUT", G.OUT):
        _panel(ax[0], E, k, rec, c0, f"{k}  S0 (recorded Y0 = {row['y0']}, K_intent {rec['spec']['K_intent']})", q=T.qref(rec))
        _arrows(ax[0], rec, seq)
        _panel(ax[1], E, k, rec, {**c0, **dict(seq)}, f"verified repair ({c['kind']}): {c['sig']}  (X = 1, Y = 1, recorded)", x=x,
               ywit=y.get("target_witness"), note="replayed witnesses: relocations blue, connector to q_ref pink, target green")
    fig.suptitle("Development pilot: a teacher-verified repair from the outcome-blind catalogue", x=0.01, ha="left")
    return _save(fig, "04_pilot_verified_repair.png")


def all_figures() -> list:
    R = G.pilot_roots()
    gen = json.loads((G.OUT / "PILOT_GENERATION.json").read_text())
    out = [fig_pilot_scenes(R), fig_catalogue(R, gen)]
    if (G.OUT / "PILOT_SUMMARY.json").exists():
        Sm = json.loads((G.OUT / "PILOT_SUMMARY.json").read_text())
        out += [fig_outcomes(Sm), fig_witness(R, Sm)]
    return [o for o in out if o]


if __name__ == "__main__":
    print("\n".join(all_figures()))
