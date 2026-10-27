"""PoC takeaway visuals for the 2D latent causal infeasibility / corrective-action proof of concept.

    python PoC-takeaway/build.py                 # render from authorized, committed results (P17 results stay PENDING)
    python PoC-takeaway/build.py --no-gifs       # tables + scenes only (GIFs re-verify physics and take minutes)
    python PoC-takeaway/build.py --refresh-p17   # after P17 is final: checks custody, then adds P17 results and re-selects GIFs

Reads only; writes only inside PoC-takeaway/. Never unseals, never edits P17 data."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
os.chdir(REPO)
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

S = json.loads((HERE / "sources.json").read_text())
AC, ST, INK = S["colors"]["approach"], S["colors"]["status"], S["colors"]["ink"]
W, H, DPI = 16, 9, 100
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15, "text.color": INK["primary"], "figure.facecolor": INK["surface"]})
DEC = ("VERIFIED", "CERTIFIED_INFEASIBLE", "STATIC_INVALID")
VIEW = ((-0.58, 0.70), (-0.08, 0.95))
VIEW_SCENE = ((-0.55, 0.68), (-0.03, 0.90))


def rd(p):
    return json.loads(Path(p).read_text())


def save(fig, name):
    fig.savefig(HERE / name, dpi=DPI, facecolor=INK["surface"])
    plt.close(fig)
    print("wrote", HERE / name)


def title(fig, t, sub=None):
    fig.text(0.04, 0.95, t, fontsize=30, weight="bold", va="top")
    if sub:
        fig.text(0.04, 0.885, sub, fontsize=15, color=INK["secondary"], va="top")


# ------------------------------------------------------------------ P17 custody (refresh only)
def p17_ready() -> tuple[bool, str]:
    p = S["results"]["p17"]
    if not Path(p["manifest"]).exists():
        return False, f"missing {p['manifest']}"
    if not Path(p["unsealed"]).exists():
        return False, f"missing {p['unsealed']} (P17 test not unsealed)"
    m = Path(p["sealed_manifest"])
    if not m.exists():
        return False, f"missing {m}"
    subprocess.run(["git", "fetch", "-q", "origin"], check=False)
    r = subprocess.run(["git", "show", f"origin/main:{m}"], capture_output=True)
    if r.returncode != 0 or r.stdout != m.read_bytes():
        return False, "sealed manifest not committed on origin/main (or differs)"
    for f in (p["prospective"], p["retrospective"]):
        if not Path(f).exists():
            return False, f"missing {f} (P17 analysis not run)"
    return True, "ok"


def dig(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


# ------------------------------------------------------------------ simulator drawing
def sim():
    import config as cf
    import geometry as ge
    cfg = cf.load_config("config.toml")
    return cfg, ge.make_robot(cfg)


def draw_scene(ax, s, goal, robot, fixed=(), q=None, gap=None, pos=None, held=None, robot_alpha=0.85, view=VIEW):
    import viz
    from viz import COLORS
    viz.draw_support(ax, s, cell_ids=False)
    pos = pos or {}
    for o in s.objects:
        xy = pos.get(o.id, o.xy_m)
        if o.kind == "target":
            fc, ec = COLORS["target"], COLORS["target_edge"]
        elif o.cell in fixed:
            fc, ec = "#52514e", "#22262e"
        else:
            fc, ec = COLORS["obstacle"], COLORS["obstacle_edge"]
        ax.add_patch(Circle(xy, o.radius_m, fc=fc, ec=ec, lw=0.9, zorder=8 if o.id == held else 3))
    ax.add_patch(Circle(s.lattice.center(goal), 0.028, fc="none", ec=COLORS["target_edge"], ls=(0, (3, 2)), lw=1.8, zorder=4))
    viz.draw_robot(ax, robot, s.robot.q_rad if q is None else q, s.robot.gripper_gap_m if gap is None else gap, alpha=robot_alpha, zorder=6)
    ax.set(xlim=view[0], ylim=view[1], aspect="equal")
    ax.axis("off")


def ghost(ax, xy, color, n=None, r=0.03, dashed=True):
    ax.add_patch(Circle(xy, r, fc="white", ec=color, lw=2.2, ls=(0, (2, 1.5)) if dashed else "-", zorder=10))
    if n is not None:
        ax.text(*xy, str(n), fontsize=12, weight="bold", color=color, ha="center", va="center", zorder=11)


def arrow(ax, a, b, color, n=None, dashed=False, lw=2.6, cross=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=18, color=color, lw=lw, ls=(0, (4, 3)) if dashed else "-", zorder=9,
                                 shrinkA=6, shrinkB=11))
    if n is not None:
        m = (np.asarray(a) + np.asarray(b)) / 2
        ax.text(*m, str(n), fontsize=12, weight="bold", color="white", ha="center", va="center", zorder=11,
                bbox=dict(boxstyle="circle,pad=0.25", fc=color, ec="white", lw=1.2))
    if cross:
        ax.text(*b, "✕", fontsize=22, weight="bold", color=ST["failed"], ha="center", va="center", zorder=12)


def records_from_npz(path):
    z = np.load(path, allow_pickle=True)
    n = 1 + max(int(k.split("_")[0][1:]) for k in z.files)
    return [{k.split("_", 1)[1]: z[k] for k in z.files if k.startswith(f"r{i}_")} for i in range(n)]


def merged_rel(steps, recs):
    import p14_eval as p14
    rel, i = [], 0
    for st in steps:
        lk = (st[2] if isinstance(st, (list, tuple)) else st["via"]) == "lookup"
        rel.append(p14._merge(recs[i], recs[i + 1]) if lk else recs[i])
        i += 2 if lk else 1
    return rel, recs[i:]


# ------------------------------------------------------------------ 01 scenes
def scenes():
    import p17_data as pdat
    from scene import scene_from_dict
    import motion as mo
    import viz
    cfg, robot = sim()
    ex = rd("runs/p17/mechanisms/EXEMPLARS.json")
    P = S["scenes"]["panels"]
    fig = plt.figure(figsize=(W, H))
    title(fig, "Scenes we construct", "Real simulator scenes · every plan shown is a physically verified, replayed witness")
    blue = viz.COLORS["hypothetical"]
    for i, p in enumerate(P):
        ev = rd(f"runs/p17/mechanisms/evidence/{p['tag']}.json")
        c = ex[p["tag"]]
        root = pdat._plan(c["split"])["roots"][ev["root"]]
        s = scene_from_dict(root["scene"])
        ax = fig.add_axes([0.02 + (i % 4) * 0.245, 0.43 - (i // 4) * 0.385, 0.23, 0.37])
        draw_scene(ax, s, root["goal_cell"], robot, set(root.get("fixed", [])), robot_alpha=0.55, view=VIEW_SCENE)
        cen, obj = s.lattice.center, {o.id: o for o in s.objects}
        cells = {o.id: o.cell for o in s.objects}
        if p.get("show") == "sweep":
            recs = records_from_npz(ev["positive"]["witness_file"])
            for q, g, _ in mo.samples(recs[-1], 7)[1:]:
                viz.draw_robot(ax, robot, q, g, alpha=0.10, zorder=5)
        seq = ev["positive"]["sequence"]
        for j, (o, d) in enumerate(seq):
            arrow(ax, cen(cells[o]), cen(d), blue)
            ghost(ax, cen(d), blue, j + 1 if len(seq) > 1 else None)
            cells[o] = d
        cf = [x for x in ev["counterfactuals"]]
        if p.get("show") == "decoy" and cf:
            o, d = cf[0]["sequence"][0]
            arrow(ax, obj[o].xy_m, cen(d), INK["muted"], dashed=True, lw=2)
            ghost(ax, cen(d), INK["muted"])
            ax.text(cen(d)[0], cen(d)[1] - 0.045, "unneeded", fontsize=12, color=INK["secondary"], va="top", ha="center", zorder=12)
        if p.get("show") == "alternative" and cf:
            o, d = cf[0]["sequence"][0]
            arrow(ax, obj[o].xy_m, cen(d), blue, dashed=True)
            ghost(ax, cen(d), blue)
            ax.text(cen(d)[0], cen(d)[1] - 0.045, "or", fontsize=13, color=INK["secondary"], va="top", ha="center", weight="bold", zorder=12)
        if p.get("show") == "conflict" and cf:
            o, d = cf[0]["sequence"][1]
            arrow(ax, obj[o].xy_m, cen(d), ST["failed"], dashed=True, lw=2, cross=True)
        if p.get("show") == "sweep":
            alt = ex["M5"]["instance"]
            arrow(ax, obj[alt["object"]].xy_m, cen(alt["slot_alt"]), ST["failed"], dashed=True, lw=2, cross=True)
        ax.set_title(p["caption"], fontsize=17, weight="bold", loc="left", pad=4)
    ly = 0.035
    items = [("●", viz.COLORS["target"], "target"), ("◌", viz.COLORS["target_edge"], "target goal"), ("●", viz.COLORS["obstacle"], "movable"),
             ("●", "#52514e", "fixed"), ("→", blue, "verified move"), ("①", blue, "destination, in order"), ("✕", ST["failed"], "rejected alternative")]
    for (sym, col, lab), x in zip(items, (0.04, 0.14, 0.28, 0.39, 0.48, 0.63, 0.81)):
        fig.text(x, ly, sym, color=col, fontsize=22, va="center", weight="bold")
        fig.text(x + 0.022, ly, lab, fontsize=15, va="center", color=INK["secondary"])
    save(fig, "01_scenes.png")


# ------------------------------------------------------------------ paper-style tables (02 / 03 / 04)
TXT, GREY, RULE = "#111111", "#6b6b6b", "#d9d9d9"


def paper_table(name, heading, cols, body, notes=(), fs=21, row_h=0.075):
    """Plain research-paper table on white: heading, thin light-grey horizontal rules only, optional italic group lines, small grey notes.
    cols = [(label, width as figure fraction, 'left' | 'center')]; body = rows (lists of str) or ('group', text) / ('rule',)."""
    fig = plt.figure(figsize=(W, H), facecolor="white")
    x0 = 0.06
    fig.text(x0, 0.90, heading, fontsize=40, color=TXT, va="baseline")
    xs = [x0]
    for _, w, _ in cols:
        xs.append(xs[-1] + w)
    x1 = xs[-1]
    line = lambda y, lw=1.0: fig.add_artist(plt.Line2D([x0, x1], [y, y], color=RULE, lw=lw))  # noqa: E731
    cell = lambda j, y, t, **k: fig.text(xs[j] if cols[j][2] == "left" else (xs[j] + xs[j + 1]) / 2, y, t, ha=cols[j][2],  # noqa: E731
                                         va="center", **k)
    y = 0.80
    line(y + row_h * 0.55, 1.4)
    for j, (lab, _, _) in enumerate(cols):
        cell(j, y, lab, fontsize=fs - 3, color=GREY)
    line(y - row_h * 0.5)
    y -= row_h
    for r in body:
        if r[0] == "group":
            y -= row_h * 0.12
            fig.text(x0, y, r[1], fontsize=fs - 4, color=GREY, style="italic", va="center")
            y -= row_h * 0.8
            continue
        if r[0] == "rule":
            line(y + row_h * 0.5)
            continue
        bold = r[0] == "Total"
        for j, t in enumerate(r):
            cell(j, y, t, fontsize=fs, color=TXT, weight="bold" if bold and j == 0 else "normal")
        y -= row_h
    line(y + row_h * 0.5, 1.4)
    for i, n in enumerate(notes):
        fig.text(x0, y + row_h * 0.5 - 0.06 - i * 0.036, n, fontsize=14, color=GREY, va="center")
    fig.savefig(HERE / name, dpi=DPI, facecolor="white")
    plt.close(fig)
    print("wrote", HERE / name)


def pct(k, n):
    return f"{k} / {n} ({round(100 * k / n)}%)"


# ------------------------------------------------------------------ 02 dataset
def dataset():
    D = S["dataset"]
    G = D["groups"]
    L = {}
    for s in ("train", "dev", "val", "calib", "p17train", "p17calib"):
        for f in sorted(glob.glob(f"runs/p17/data/{s}/labels_*.json")):
            for k, v in rd(f).items():
                L[(s, k)] = v
    order = list(dict.fromkeys(G.values()))
    agg = defaultdict(Counter)
    for v in L.values():
        a, st = agg[G[v["family"]]], v["original"]["status"]
        a["n"] += 1
        a["feas" if st == "VERIFIED" else "inf" if st in DEC[1:] else "unk"] += 1
        a["gen"] += sum(n for m, n in v["catalogue"]["generated"].items() if m != "0")
        a["tested"] += len(v["sequences"])
        if st in DEC[1:]:
            a["rep"] += any(x.get("y") == 1 for x in v["sequences"].values())
    tot = sum(agg.values(), Counter())
    test = {k: len(rd(p)["roots"]) for k, p in D["test_plans"].items()}
    row = lambda g, a: [g, f"{a['n']}", f"{a['feas']}", f"{a['inf']}", f"{a['unk']}", f"{a['tested']:,}", f"{a['rep']} / {a['inf']}" if a["inf"] else "–"]  # noqa: E731
    body = [row(g, agg[g]) for g in order] + [("rule",), row("Total", tot)]
    cols = [("Scene type", 0.25, "left"), ("Scenes", 0.07, "center"), ("Feasible\nas is", 0.11, "center"), ("Blocked", 0.10, "center"),
            ("Unknown", 0.10, "center"), ("Repair plans\nchecked", 0.12, "center"), ("Blocked scenes\nrepaired", 0.13, "center")]
    paper_table("02_dataset.png", "Our 2D dataset", cols, body, notes=[
        "Unknown: the planner could not prove success or failure.",
        f"Development scenes (training, validation, calibration). Held out for testing: {test['P16 test']} (P16) and {test['P17 test']} (P17) scenes.",
        f"Repair plans checked: physically simulated, out of about {round(tot['gen'], -3):,} generated."], fs=20, row_h=0.072)
    return {"dev": dict(tot), "groups": {g: dict(agg[g]) for g in order}, "test": test}


# ------------------------------------------------------------------ 03 results
def obs(t, P):
    """'{arm.key}' -> per_arm[arm][key] (P16 B_TEST); '{feasible}' / '{infeasible}' -> cohort sizes."""
    return re.sub(r"\{([^}]+)\}", lambda m: str(P["per_arm"][m.group(1).split(".")[0]][m.group(1).split(".")[1]]) if "." in m.group(1)
                  else str(P[m.group(1)]), t)


def results(p17=None):
    R = S["results"]
    B, Dd = rd(R["b_file"]), rd(R["d_file"])
    pend = "Pending"
    body = []
    for grp in R["groups"]:
        body.append(("group", grp["heading"]))
        for r in grp["rows"]:
            if grp["kind"] == "b":
                x = B["per_arm"][r["arm"]]
                v = pct(x["noop_correct"] + x["repair_success"], B["decided_roots"])
                y = dig(p17, "b", "analysis", "per_arm", r["p17_arm"])
                p = pct(round(y["strict_top1"] * y["n"]), y["n"]) if y and y.get("n") and y.get("strict_top1") is not None else pend
                o = obs(r["observation"], B)
            else:
                x = Dd["per_guide"][r["arm"]]
                v = pct(x["success"], x["n"])
                y = dig(p17, "d", "all_roots", "per_guide", r["p17_arm"])
                p = pct(y["success"], y["n"]) if y and y.get("n") else pend
                o = r["observation"]
            body.append([r["label"], v, o, p])
    cols = [("Approach", 0.15, "left"), ("Success rate", 0.19, "left"), ("Main observation", 0.44, "left"), ("P17 test", 0.10, "left")]
    nf, n = B["feasible"], B["decided_roots"]
    paper_table("03_results.png", "What worked", cols, body, fs=20, notes=[
        f"Doing nothing succeeds on {B['per_arm']['empty_always']['noop_correct']} / {n} (every feasible scene); A–C do not beat this baseline.",
        f"D solves a different task, so it is not comparable with A–C. {Dd['common_roots']} of 48 planned D scenes were run before the compute cap.",
        "Success: the chosen plan, or the choice to do nothing, is physically verified."], row_h=0.085)


# ------------------------------------------------------------------ 04 ablations
def ablations(p17=None):
    body = [[r["approach"], r["tested"], r["finding"]] for r in S["ablations"]["rows"]]
    cols = [("Approach", 0.15, "left"), ("What we tested", 0.40, "left"), ("Finding", 0.33, "left")]
    paper_table("04_ablations.png", "What the ablations taught us", cols, body, notes=S["ablations"]["notes"], fs=21, row_h=0.085)


# ------------------------------------------------------------------ GIFs (certified motion only)
def p16_panels(key, root, rec, seed_rows):
    """Per approach: frames source. B-type arms: recorded choice re-verified with the P16 verifier (status must match the record)."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_eval as pe
    import p16_motion as pm
    idx = pl.index_v2()[0]
    task = pc.task_from_root(root, key)
    out = {}
    for slot, (arm, lab) in S["gifs"]["panels"].items():
        if slot == "D":
            if "d" not in rec:
                out[slot] = {"label": lab, "status": "not_run", "text": "NOT RUN", "frames": None}
                continue
            r0 = rec["d"][arm]
            phys = pm.DetPhysics(task, idx)
            cells0 = {o.id: o.cell for o in phys.s0.objects}
            mv, _ = pc.propose_movers(task, cells0)
            r = pc.search(phys, pe.uniform_order, mv, pc.slot_fn(phys, idx), cells0, phys.s0.robot.q_rad, 4, 2, 500)
            rep = pm.replay(phys, r["plan"]) if r["found"] else None
            if not (rep and rep["ok"] and rep["traj"] == r0["traj"]):
                raise SystemExit(f"{key}: regenerated plan does not match the recorded {arm} trajectory")
            steps = r["plan"]["steps"]
            rel, tw = merged_rel(steps, r["plan"]["records"])
            out[slot] = {"label": lab, "status": "success" if r0["found"] and r0["replay"] else "failed", "phys": phys,
                         "seq": [(s["object"], s["dest"]) for s in steps], "rel": rel, "tw": tw,
                         "text": f"SUCCESS · {len(steps)} move{'s' if len(steps) != 1 else ''}", "nodes": r0["log"]["nodes"],
                         "checks": r0["used"]["motion_checks"]}
            continue
        x = rec["b"]["arms"][arm]
        phys = pm.DetPhysics(task, idx)
        sig = x["choice"].rsplit(":", 1)[1]
        seq = [] if sig == "empty" else [(a.split(">")[0], int(a.split(">")[1])) for a in sig.split(".")]
        cells, q = {o.id: o.cell for o in phys.s0.objects}, np.asarray(phys.s0.robot.q_rad, float)
        steps, recs, status = [], [], None
        for o, d in seq:
            e = pc.best_edge(phys.edges(cells, q, o, d))
            if e is None:
                status = "step"
                break
            st, rs, q2, _, meta = e
            steps.append({"object": o, "dest": d, **meta})
            recs += rs
            cells, q = {**cells, o: d}, q2
        tw = []
        if status is None:
            st, trec, _ = phys.goal(cells, q)
            status = st
            if st == "VERIFIED":
                tw = [trec]
        if status != x["status"]:
            raise SystemExit(f"{key} {arm}: re-verified status {status} != recorded {x['status']}")
        rel, _ = merged_rel(steps, recs + tw)
        s_, t_ = outcome(rec["b"]["y0_status"], seq, status)
        out[slot] = {"label": lab, "status": s_, "phys": phys, "seq": [(s["object"], s["dest"]) for s in steps], "rel": rel, "tw": tw, "text": t_}
    return out


def gif_render(slot, panels, fname, header, sub, side, fixed=()):
    import p6_viz as pv
    frames_by = {}
    for k, p in panels.items():
        if p.get("frames") is None and "seq" in p:
            ph = p["phys"]
            p["frames"] = pv.trace_frames(ph.robot, ph.s0, p["seq"], p["rel"], p["tw"], n_move=10, n_target=12) or [(None, None, None, None)]
        frames_by[k] = p.get("frames")
    T = max(len(f) for f in frames_by.values() if f) + 6
    any_ph = next(p["phys"] for p in panels.values() if p.get("phys") is not None)
    imgs = []
    for t in range(T):
        fig = plt.figure(figsize=(W, H))
        fig.text(0.03, 0.95, header, fontsize=26, weight="bold", va="top")
        fig.text(0.03, 0.895, sub, fontsize=14, color=INK["secondary"], va="top")
        for i, k in enumerate(("A", "B", "C", "D")):
            p = panels[k]
            ax = fig.add_axes([0.0 + (i % 2) * 0.335, 0.435 - (i // 2) * 0.425, 0.335, 0.37])
            fr = frames_by[k]
            ph = p.get("phys") or any_ph
            if fr:
                q, g, pos, held = fr[min(t, len(fr) - 1)]
                draw_scene(ax, ph.s0, ph.goal_cell, ph.robot, fixed, q=q, gap=g, pos=pos, held=held)
            else:
                draw_scene(ax, ph.s0, ph.goal_cell, ph.robot, fixed, robot_alpha=0.85 if p["status"] != "not_run" else 0.25)
                cells = {o.id: o.cell for o in ph.s0.objects}
                for o, d in p.get("proposal") or []:
                    arrow(ax, ph.s0.lattice.center(cells[o]), ph.s0.lattice.center(d), INK["muted"], dashed=True, lw=2)
                    cells[o] = d
                if p["status"] == "not_run":
                    ax.add_patch(Rectangle((VIEW[0][0], VIEW[1][0]), VIEW[0][1] - VIEW[0][0], VIEW[1][1] - VIEW[1][0], fc="white", alpha=0.55, ec="none", zorder=15))
            fam = {"A": "A", "B": "B", "C": "C", "D": "D"}[k]
            ax.add_patch(FancyBboxPatch((0.0, 1.02), 0.05, 0.075, transform=ax.transAxes, boxstyle="round,pad=0,rounding_size=0.01", fc=AC[fam],
                                        ec="none", clip_on=False))
            ax.text(0.07, 1.055, p["label"], transform=ax.transAxes, fontsize=16, weight="bold", va="center")
            done = fr is None or t >= len(fr) - 1
            txt, col = (p["text"], ST[p["status"]]) if done else ("executing certified motion …", INK["muted"])
            ax.text(0.02, 0.03, txt, transform=ax.transAxes, fontsize=14, weight="bold", color="white", va="bottom", zorder=20,
                    bbox=dict(boxstyle="round,pad=0.35", fc=col, ec="none"))
        fig.text(0.69, 0.80, "\n".join(side), fontsize=15, color=INK["secondary"], va="top", linespacing=1.45)
        yy = 0.30
        for lab, c in (("SUCCESS", ST["success"]), ("NEEDLESS MOVE", ST["needless"]), ("FAILED", ST["failed"]), ("UNKNOWN", ST["unknown"]), ("NOT RUN", ST["not_run"])):
            fig.text(0.70, yy, f"  {lab}  ", fontsize=12, weight="bold", color="white", bbox=dict(boxstyle="round,pad=0.3", fc=c, ec="none"))
            yy -= 0.05
        fig.canvas.draw()
        imgs.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()).resize((1280, 720), Image.LANCZOS))
        plt.close(fig)
    q = quantize(imgs)
    dur = [110] * (len(q) - 1) + [2500]
    q[0].save(HERE / fname, save_all=True, append_images=q[1:], duration=dur, loop=0, optimize=False)
    print("wrote", HERE / fname, len(imgs), "frames")


def quantize(imgs):
    """One global palette for every frame: the exact approach / status / ink colours first, then median-cut colours of the last frame."""
    keys = list(dict.fromkeys([*AC.values(), *ST.values(), *INK.values(), "#ffffff"]))
    rgb = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in keys]
    base = imgs[-1].quantize(colors=256 - len(rgb), method=Image.Quantize.MEDIANCUT).getpalette()[: 3 * (256 - len(rgb))]
    pal = Image.new("P", (1, 1))
    pal.putpalette([v for c in rgb for v in c] + base)
    return [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]


def pending_gif(fname, header, why):
    fig = plt.figure(figsize=(W, H))
    fig.text(0.5, 0.58, header, fontsize=30, weight="bold", ha="center")
    fig.text(0.5, 0.48, "PENDING", fontsize=44, weight="bold", ha="center", color=ST["unknown"])
    fig.text(0.5, 0.38, why, fontsize=16, ha="center", color=INK["secondary"])
    fig.canvas.draw()
    Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()).resize((1280, 720), Image.LANCZOS).save(HERE / fname)
    plt.close(fig)
    print("wrote", HERE / fname, "(pending)")


def outcome(y0, seq, status):
    if status == "VERIFIED" and not seq:
        return "success", "SUCCESS · no move needed"
    if status == "VERIFIED" and y0 == "VERIFIED":
        return "needless", "NEEDLESS MOVE · task was feasible"
    if status == "VERIFIED":
        return "success", f"SUCCESS · {len(seq)} move{'s' if len(seq) != 1 else ''}"
    if str(status).startswith("UNKNOWN"):
        return "unknown", "UNKNOWN · planner unresolved"
    if status == "ABSTAIN":
        return "unknown", "ABSTAINED"
    if not seq:
        return "failed", "FAILED · chose no move"
    return "failed", "FAILED · target still blocked"


def strict_ok(b, arm):
    x, y0 = b["arms"].get(arm), b["y0_status"]
    if x is None or y0 not in DEC:
        return None
    if y0 == "VERIFIED":
        return x["choice"].endswith(":empty") and x["status"] == "VERIFIED"
    return not x["choice"].endswith(":empty") and x["status"] == "VERIFIED" and bool(x.get("replay"))


def p17_panels(key, root, rec):
    """P17 refresh: B-type panels re-verified with the frozen existential verifier (status must equal the record; failures are drawn as
    'not executed' proposals); D panel regenerated with the frozen P17 guide + corrected search, accepted only if its replay hash matches."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_motion as pm
    import p17_b as pb
    import p17_d as pd
    import p17_domain as dm
    import p17_exec as ex
    import p17_search as s17
    import p17_verify as pv
    idx = pl.index_v2()[0]
    task = pc.task_from_root(root, key)
    out = {}
    for slot, (arm, lab) in S["gifs"]["p17_panels"].items():
        if slot == "D":
            if "d" not in rec:
                out[slot] = {"label": lab, "status": "not_run", "text": "NOT RUN · not in the D roster", "frames": None}
                continue
            r0 = rec["d"][arm]
            if not r0["found"]:
                out[slot] = {"label": lab, "status": "failed", "frames": None,
                             "text": "NO PLAN · budget" if not r0["claim"].startswith("NO_PLAN_IN_FULLY") else "NO PLAN · proven in finite graph"}
                continue
            import learn_data as ld
            phys = pm.DetPhysics(task, idx, budget=ex.D_BUDGET)
            cells0 = {o.id: o.cell for o in phys.s0.objects}
            mv, _ = dm.movers(task, cells0)
            gd = pd.Guide(arm, task, phys, mv, None, ld.dino())
            r = s17.search(phys, gd.order, mv, dm.slot_fn(phys, idx, width=4, origin=cells0), cells0, phys.s0.robot.q_rad, 4, 2, 500)
            rep = pm.replay(phys, r["plan"]) if r["found"] else None
            if not (rep and rep["ok"] and rep["traj"] == r0["traj"]):
                raise SystemExit(f"{key}: regenerated {arm} plan does not match the recorded trajectory")
            steps = r["plan"]["steps"]
            rel, tw = merged_rel(steps, r["plan"]["records"])
            out[slot] = {"label": lab, "status": "success", "phys": phys, "seq": [(x["object"], x["dest"]) for x in steps], "rel": rel, "tw": tw,
                         "text": f"SUCCESS · {len(steps)} move{'s' if len(steps) != 1 else ''}", "nodes": r0["log"]["nodes"],
                         "checks": r0["used"]["motion_checks"]}
            continue
        x = rec["b"]["arms"][arm]
        phys = pm.DetPhysics(task, idx, budget=pb.SEQ_BUDGET)
        if x["choice"] == "ABSTAIN":
            out[slot] = {"label": lab, "status": "unknown", "text": "ABSTAINED", "frames": None, "phys": phys}
            continue
        sig = x["choice"].rsplit(":", 1)[1]
        seq = [] if sig == "empty" else [(a.split(">")[0], int(a.split(">")[1])) for a in sig.split(".")]
        v = pv.verify_existential(phys, seq, first=True)
        if v["status"] != x["status"] and not (x["status"] == "UNKNOWN_REPLAY_FAILED"):
            raise SystemExit(f"{key} {arm}: re-verified status {v['status']} != recorded {x['status']}")
        st_, txt = outcome(rec["b"]["y0_status"], seq, x["status"])
        if v["plan"] and x["status"] == "VERIFIED":
            rel, tw = merged_rel(v["plan"]["steps"], v["plan"]["records"])
            out[slot] = {"label": lab, "status": st_, "phys": phys, "seq": seq, "rel": rel, "tw": tw, "text": txt}
        else:
            out[slot] = {"label": lab, "status": st_, "phys": phys, "frames": None, "text": txt + (" (not executed)" if seq else ""), "proposal": seq}
    return out


def p17_select():
    """Deterministic P17 slot selection (plan order, first match; prefers roots executed by all four approaches)."""
    import p17_data as pdat
    rb, rdd = pdat.merged("p17test", "sealed_exec_b"), pdat.merged("p17test", "sealed_exec_d")
    plan = pdat._plan("p17test")["roots"]
    ap = {k: v[0] for k, v in S["gifs"]["p17_panels"].items()}
    rows = {k: {"b": rb[k]["b"], **({"d": rdd[k]["d"]} if k in rdd else {})} for k in plan if k in rb}
    okd = lambda r, g: bool(r.get("d", {}).get(g, {}).get("found") and r["d"][g].get("replay"))  # noqa: E731
    ok = {k: {s: (okd(r, ap[s]) if s == "D" else strict_ok(r["b"], ap[s])) for s in ap} for k, r in rows.items()}
    both = [k for k in rows if "d" in rows[k]]
    rules = [("05_all_succeed.gif", "All four succeed", lambda k: all(ok[k].values())),
             ("06_A_weakness.gif", "A fails, another approach succeeds", lambda k: ok[k]["A"] is False and any(ok[k][s] for s in "BCD")),
             ("07_B_weakness.gif", "B fails, another approach succeeds", lambda k: ok[k]["B"] is False and any(ok[k][s] for s in "ACD")),
             ("08_C_weakness.gif", "C fails, another approach succeeds", lambda k: ok[k]["C"] is False and any(ok[k][s] for s in "ABD")),
             ("09_D_weakness.gif", "D finds no plan, geometry does", lambda k: k in both and not ok[k]["D"] and okd(rows[k], "geometry"))]
    out = []
    for f, t, rule in rules:
        k = next((k for k in both if rule(k)), None) or next((k for k in rows if rule(k)), None)
        out.append({"file": f, "root": k, "title": t, "rows": rows, "plan": plan})
    return out


def gifs(p17=False):
    if p17:
        for sl in p17_select():
            k = sl["root"]
            if k is None:
                pending_gif(sl["file"], sl["title"], "no P17 test scene matches this contrast")
                continue
            pan = p17_panels(k, sl["plan"][k], sl["rows"][k])
            side = ["Same scene, same start, same", "certifier for all four panels.", "", "P17 frozen test · " + sl["plan"][k]["family"],
                    "Motion = certified replay only.", "", "First scene in plan order", "matching this contrast."]
            gif_render(sl, pan, sl["file"], sl["title"], "Hand-picked by a fixed rule · not a statistic", side, set(sl["plan"][k].get("fixed", [])))
        return
    rows = {}
    for f in glob.glob("runs/p16/data/test/sealed_exec_*.json"):
        rows.update(rd(f))
    plan = rd("runs/p16/data/test/plan.json")["roots"]
    for sl in S["gifs"]["slots"]:
        k = sl["root"]
        if k not in rows:
            pending_gif(sl["file"], sl["title"], "root not found in P16 execution records")
            continue
        pan = p16_panels(k, plan[k], rows[k], rows)
        if sl.get("d_note"):
            pan["D"]["text"] = "NOT RUN · D not tested on natural scenes"
        side = ["Same scene, same start, same", "certifier for all four panels.", "",
                "P16 frozen test · " + ("natural scene" if plan[k]["family"] == "NAT" else "constructed scene"), "Motion = certified replay only."]
        if sl.get("note"):
            side += ["", sl["note"] + "."]
        if sl.get("alternative"):
            d = pan["D"]
            g = rows[k]["d"]["geometry"]
            side += ["", "No D failure exists in P16", f"(all {rd(S['results']['d_file'])['common_roots']} D scenes solved).",
                     f"D search: {d['nodes']} nodes, {d['checks']} checks;", f"geometry: {g['log']['nodes']} nodes, {g['used']['motion_checks']} checks."]
        sub = "Hand-picked qualitative example · not a statistic"
        gif_render(sl, pan, sl["file"], sl["title"], sub, side, set(plan[k].get("fixed", [])))


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-p17", action="store_true")
    ap.add_argument("--no-gifs", action="store_true")
    a = ap.parse_args()
    p17 = None
    if a.refresh_p17:
        ok, why = p17_ready()
        if not ok:
            raise SystemExit(f"--refresh-p17 refused: {why}")
        pr, re_ = rd(S["results"]["p17"]["prospective"]), rd(S["results"]["p17"]["retrospective"])
        p17 = {"b": pr.get("b"), "d": pr.get("d"), "retro": re_}
    scenes()
    dataset()
    results(p17)
    ablations(p17)
    if not a.no_gifs:
        gifs(p17=a.refresh_p17)


if __name__ == "__main__":
    main()
