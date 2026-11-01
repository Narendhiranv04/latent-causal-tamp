"""BXY-P20 figures. Scene panels are either recorded teacher evidence (replayed witnesses: relocations blue, connector to q_ref pink, target
green) or explicitly labelled geometric proposals (construction intent, ideal scenes). Reuses the P16 figure helpers on the P20 run tree."""
from __future__ import annotations

import collections
import glob
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_p16 as G  # noqa: E402
import bxy_p16_viz as V16  # noqa: E402
import bxy_p20_k34 as Z  # noqa: E402
import bxy_pmin_sidecar as S  # noqa: E402
import bxy_teacher as T  # noqa: E402
from bxy_p11_viz import _arrows  # noqa: E402
from bxy_p12_viz import _clean  # noqa: E402
from bxy_p14_run import _swap  # noqa: E402
from bxy_pmin_viz import _panel, done_steps  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_p20_v1")
KC = V16.KC


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def _summ(waves):
    return {w: json.loads((Z.wdir(w) / "SUMMARY.json").read_text()) for w in waves if (Z.wdir(w) / "SUMMARY.json").exists()}


def _rows(S_):
    return [(w, r) for w, s in S_.items() for r in s["rows"] if r["results"]]


def fig_construction(S_):
    """Geometric proposal of a certified K4 (else K3) root: walls (fixed, dark), blockers, the reopened mode's kill cells, intended order."""
    import viz
    E = T.env()
    cand = sorted(((w, r) for w, r in _rows(S_) if r["K_cert"] and r["K_cert"] >= 3), key=lambda wr: (-wr[1]["K_cert"], wr[1]["verified_K_claim"] is None, wr[1]["root"]))
    if not cand:
        return None
    w, row = cand[0]
    rec = Z.roots_of(w)[row["root"]]
    C, c0 = rec["construction"], bd.cells0(rec)
    seq = [tuple(a) for a in C["intended"]]
    fig, ax = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
    with _swap(S, "OUT", Z.wdir(w)):
        _panel(ax[0], E, row["root"], rec, c0, f"{row['root']}  S0 (geometric proposal): K_cert = {C['K_cert']} certified, split pick/place {C.get('split_pick_place')}",
               q=T.qref(rec), note=f"S0 open modes: pick {C['S0_open']['pick']}, place {C['S0_open']['place']}; dark discs = fixed walls")
        opt = C["options"][0]
        V16._cells(ax[0], G.access_map("pick", c0["t0"])["kill"][str(opt["pick"])], "#b4441c", 0.16)
        V16._cells(ax[0], G.access_map("place", rec["goal_cell"])["kill"][str(opt["place"])], "#7d3c98", 0.16)
        _arrows(ax[0], rec, seq)
        cells = {**c0, **dict(seq)}
        _panel(ax[1], E, row["root"], rec, cells, "ideal scene after the intended repair (geometry only): reopened grasp pose drawn", q=T.qref(rec))
    q = V16._grasp_q(rec, cells, opt["pick"])
    if q is not None:
        viz.draw_robot(ax[1], E["robot"], q, E["robot"].open_gap, alpha=0.55, zorder=7)
    fig.suptitle("BXY_GEN_K34 doorway closure: red / purple = kill cells of the reopened pick / place mode; blockers lie in every doorway mode's kill set", x=0.01, ha="left")
    return _save(fig, "01_k34_construction.png")


def fig_story(S_, K, name):
    """Every prefix of a verified K-move repair: hypothetical Y and physical X at each stopping prefix, replayed witnesses."""
    for w, r in _rows(S_):
        if r["verified_K_claim"] == K:
            Sm = {"rows": [r]}
            with G_paths():
                V16.FIG = FIG
                p = V16.fig_prefix_story(w, Z.roots_of(w), Sm)
            if p:
                q = Path(p)
                tgt = FIG / name
                q.rename(tgt)
                return str(tgt)
    return None


class G_paths:
    def __enter__(self):
        self.c = Z.p16_paths()
        self.c.__enter__()

    def __exit__(self, *a):
        self.c.__exit__(*a)


def fig_failed_k4(S_):
    """Recorded K4 attempts that failed, with the failing phase: completed relocations (blue witnesses) and where X stopped."""
    E = T.env()
    rows = [(w, r) for w, r in _rows(S_) if r["K_geom"] == 4 and r["verified_K_claim"] != 4][:3]
    if not rows:
        return None
    fig, ax = plt.subplots(1, len(rows), figsize=(6 * len(rows), 6), constrained_layout=True, squeeze=False)
    for a_, (w, r) in zip(ax[0], rows):
        rec = Z.roots_of(w)[r["root"]]
        res = G.results(w, r["root"]) if False else {}
        with Z.p16_paths():
            res = G.results(w, r["root"])
        seq = [tuple(x) for x in rec["construction"]["intended"]]
        xr, yr = res.get(T.xkey(r["root"], rec, seq), {}), res.get(T.ykey(r["root"], rec, seq), {})
        ws = done_steps(xr)
        done = len(xr.get("steps") or [])
        with _swap(S, "OUT", Z.wdir(w)):
            _panel(a_, E, r["root"], rec, {**bd.cells0(rec), **dict(seq[:done])}, f"{r['root'][-8:]} intended 4-move repair (recorded)", q=T.qref(rec) if not ws else None,
                   partial=ws, note=f"X = {xr.get('y')} at {xr.get('failed_phase')} ({xr.get('teacher_status')}, {xr.get('negative_kind')}); {done}/4 relocations witnessed\n"
                   f"Y(hypothetical full repair) = {yr.get('y')} ({yr.get('teacher_status')})")
        _arrows(a_, rec, seq)
    fig.suptitle("Failed K4 attempts: the physical relocation chain stops under the fixed planner budget (phase labels from the teacher record)", x=0.01, ha="left")
    return _save(fig, "04_failed_k4_attempts.png")


def fig_confusion(S_):
    rows = [r for _, r in _rows(S_)]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
    for a_, key, t in ((ax[0], "K_intent", "K_intent (construction request)"), (ax[1], "K_cert", "K_cert (certified necessity bound)")):
        lv = sorted({r["spec"]["K_intent"] if key == "K_intent" else (r["K_cert"] or 0) for r in rows})
        cols = ["0", "1", "2", "3", "4", "None"]
        M_ = np.array([[sum(1 for r in rows if (r["spec"]["K_intent"] if key == "K_intent" else (r["K_cert"] or 0)) == a and str(r["verified_K_claim"]) == b) for b in cols] for a in lv])
        a_.imshow(M_, cmap="Blues")
        for i in range(len(lv)):
            for j in range(len(cols)):
                a_.text(j, i, M_[i, j], ha="center", va="center", fontsize=9, color="black" if M_[i, j] < M_.max() / 2 else "white")
        a_.set_xticks(range(len(cols)), [f"K_cat {c}" for c in cols], fontsize=8)
        a_.set_yticks(range(len(lv)), [f"{key} {a}" for a in lv], fontsize=8)
        a_.set_title(t + " vs verified K_catalogue")
    fig.tight_layout()
    return _save(fig, "05_k_confusion.png")


def fig_counts(waves):
    fig, ax = plt.subplots(figsize=(12, 4.6))
    labels, acc, rej = [], [], []
    for w in waves:
        g = json.loads((Z.wdir(w) / "GENERATION.json").read_text())
        c = collections.Counter((a["spec"]["family"], a["spec"]["K_intent"], a["accepted"]) for a in g["attempts"])
        for fam, K in sorted({(f, k) for f, k, _ in c}):
            labels.append(f"{w} {fam} K{K}")
            acc.append(c[(fam, K, True)])
            rej.append(c[(fam, K, False)])
    x = np.arange(len(labels))
    ax.bar(x, acc, color="#2a78d6", label="accepted (frozen, labelled)")
    ax.bar(x, rej, bottom=acc, color="#c9c9c3", label="rejected (geometry / certificate; recorded)")
    ax.set_xticks(x, labels, rotation=60, ha="right", fontsize=7)
    ax.legend(frameon=False)
    ax.set(ylabel="construction slots", title="P20 generator denominator by wave, family and K_intent")
    _clean(ax)
    return _save(fig, "06_generator_denominator.png")


def fig_phase_cpu(waves):
    c = collections.Counter()
    for w in waves:
        for f in glob.glob(str(Z.wdir(w) / "results" / "*" / "*.json")):
            r = json.loads(Path(f).read_text())
            ph = "Y target" if r.get("side") == "y" else ("X verified" if r.get("y") == 1 else f"X fail @ {(r.get('failed_phase') or '?').split(':')[0]}")
            c[ph] += r.get("process_cpu_s") or 0.0
    fig, ax = plt.subplots(figsize=(8, 4))
    ks = sorted(c, key=lambda k: -c[k])
    ax.barh(range(len(ks)), [c[k] for k in ks], color="#2a78d6")
    ax.set_yticks(range(len(ks)), ks)
    ax.invert_yaxis()
    ax.set(xlabel="teacher CPU-s", title="P20 teacher CPU by query side / phase")
    _clean(ax)
    return _save(fig, "07_teacher_cpu_by_phase.png")


def fig_step_success(waves):
    """Per-relocation success by step index: P16 (all waves) vs each P20 wave."""
    def stats(root_dirs):
        ok, n = collections.Counter(), collections.Counter()
        for d in root_dirs:
            for f in glob.glob(str(d / "*" / "*.x.json")):
                r = json.loads(Path(f).read_text())
                if not r.get("attempted") or r.get("y") is None or not r.get("ordered_actions"):
                    continue
                m = len(r["ordered_actions"])
                fail = int(r["failed_phase"].split(":")[1]) if r["y"] == 0 and (r.get("failed_phase") or "").startswith("relocation") else None
                for t in range(m if fail is None else fail + 1):
                    n[t] += 1
                    ok[t] += fail is None or t < fail
        return {t: ok[t] / n[t] for t in sorted(n)}, n
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for lab, dirs in [("P16 (wA-wC)", [G.OUT / w / "results" for w in ("wA", "wB", "wC")])] + [(f"P20 {w}", [Z.wdir(w) / "results"]) for w in waves]:
        s, n = stats(dirs)
        ax.plot(list(s), list(s.values()), "-o", label=f"{lab} (n = {sum(n.values())})")
    ax.set(xlabel="relocation index within the prefix", ylabel="P(relocation verified | reached)", ylim=(0, 1), title="Physical relocation success by step (fixed teacher budget)")
    ax.legend(frameon=False, fontsize=8)
    _clean(ax)
    return _save(fig, "08_relocation_success_by_step.png")



def fig_k4_full(S_, which=0):
    """A verified K4 root in full: S0, each stopping prefix (recorded X with connector, independently queried hypothetical Y), the composed
    repair with the target witness, and a failing alternative order of the same four moves (same endpoint, shared Y) with its phase."""
    E = T.env()
    cand = [(w, r) for w, r in _rows(S_) if r["verified_K_claim"] == 4]
    if len(cand) <= which:
        return None
    w, r = cand[which]
    k, rec = r["root"], Z.roots_of(w)[r["root"]]
    with Z.p16_paths():
        res = G.results(w, k)
    c0 = bd.cells0(rec)
    seq = [tuple(a) for a in rec["construction"]["intended"]]
    rep = next(c for c in rec["catalogue_v21"] if c["kind"] == "repair")
    seq = [tuple(a) for a in rep["seq"]]
    alt = None
    for c in rec["catalogue_v21"]:
        s2 = [tuple(a) for a in c["seq"]]
        if len(s2) == 4 and sorted(s2) == sorted(seq) and s2 != seq and (res.get(T.xkey(k, rec, s2)) or {}).get("y") == 0:
            alt = s2
            break
    fig, ax = plt.subplots(2, 3, figsize=(19, 12.5), constrained_layout=True)
    y0 = res.get(T.ykey(k, rec, []), {})
    with _swap(S, "OUT", Z.wdir(w)):
        _panel(ax[0, 0], E, k, rec, c0, f"S0: target infeasible (Y0 = {y0.get('y')}, {y0.get('teacher_status')}); K_cert = {r['K_cert']}", q=T.qref(rec),
               note="numbered arrows: the verified 4-move repair (order and destinations)")
        _arrows(ax[0, 0], rec, seq)
        for t, a_ in zip(range(1, 5), [ax[0, 1], ax[0, 2], ax[1, 0], ax[1, 1]]):
            pre = seq[:t]
            xr, yr = res.get(T.xkey(k, rec, pre), {}), res.get(T.ykey(k, rec, pre), {})
            _panel(a_, E, k, rec, {**c0, **dict(pre)}, f"after move {t}: " + " -> ".join(f"{o}@{d}" for o, d in pre), x=xr if xr.get("y") == 1 else None,
                   ywit=yr.get("target_witness") if yr.get("y") == 1 else None, q=None if xr.get("y") == 1 else T.qref(rec),
                   note=f"X (moves 1..{t} from q0 + connector to q_ref) = {xr.get('y')} [{xr.get('teacher_status')}]\n"
                        f"Y (target from q_ref in this edited scene) = {yr.get('y')} [{yr.get('teacher_status')}]")
        if alt:
            xr = res.get(T.xkey(k, rec, alt), {})
            ws = done_steps(xr)
            done = len(xr.get("steps") or [])
            _panel(ax[1, 2], E, k, rec, {**c0, **dict(alt[:done])}, "same four moves, different order: " + " -> ".join(f"{o}@{d}" for o, d in alt),
                   q=T.qref(rec) if not ws else None, partial=ws,
                   note=f"X = 0 at {xr.get('failed_phase')} ({xr.get('teacher_status')}, {xr.get('negative_kind')}); shared Y of the endpoint = 1")
            _arrows(ax[1, 2], rec, alt)
        else:
            ax[1, 2].axis("off")
    fig.suptitle(f"{k}: a physically verified, certified-necessary K4 repair (recorded replayed witnesses: relocations blue, connector to q_ref pink, "
                 "target green)", x=0.01, ha="left", fontsize=11)
    return _save(fig, f"00_verified_k4_{k[-6:]}.png")


def all_figures(waves) -> list:
    S_ = _summ(waves)
    out = [fig_k4_full(S_, 0), fig_k4_full(S_, 1), fig_construction(S_), fig_story(S_, 4, "02_k4_prefix_story.png"), fig_story(S_, 3, "03_k3_prefix_story.png"), fig_failed_k4(S_), fig_confusion(S_),
           fig_counts(waves), fig_phase_cpu(waves), fig_step_success(waves)]
    with Z.p16_paths():
        V16.FIG = FIG
        out += [V16.fig_cells_negatives(S_), V16.fig_prefix_coverage(S_)]
        for o in out[-2:]:
            if o:
                Path(o).rename(FIG / ("1" + Path(o).name))
        out[-2:] = [str(FIG / ("1" + Path(o).name)) if o else None for o in out[-2:]]
        for w, Sm in S_.items():
            R = Z.roots_of(w)
            Sm2 = dict(Sm, rows=[dict(r, discordant=r["strict_discordant"]) for r in Sm["rows"]])
            out += [V16.fig_order_twins(w, R, Sm2), V16.fig_harmful(w, R, Sm)]
    return [o for o in out if o]


if __name__ == "__main__":
    import sys
    print("\n".join(all_figures(sys.argv[1:])))
