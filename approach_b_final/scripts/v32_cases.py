"""V3.2 failure / repair case figures (2D VALIDATION), drawn from the snapshot scene record (object discs at their initial positions, target, goal,
robot base) and each arm's selected ordered relocations (numbered arrows to destination cell centres) with its PHYSICALLY VERIFIED outcome.
Schematic: no robot poses or planner trajectories are drawn (teacher witnesses are stored in the verify records, not rendered here).
Cases (deterministic, first by root id): (a) K3 roots where capped V3 fails, frozen exhaustive M4 selects an endpoint-infeasible repair (Y=0) and
D-expanded s0 M4 succeeds; (b) NONE roots where frozen exhaustive M6 selects a Y=0 repair and D-expanded s0 M6 correctly abstains.
usage: v32_cases.py SNAP FROZEN_RUNDIR TRAINED_RUNDIR OUTDIR CACHE_GLOB_2D"""
import glob, json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v32b_phys import GRID, RULE, labels, outcome  # noqa: E402

RI = GRID.index(RULE)


def jl(p):
    return [json.loads(l) for l in open(p)]


def dec(rec, M):
    d = rec["per_M"][str(M)]["decisions"][RI]
    return None if d is None else d["seq"], (None if d is None else d["p11"])


def draw(ax, row, sel, title):
    inp = row["inputs"]; xy = inp["xy0"]; tid = int(inp["tid"]); cxy = inp["cell_xy"]
    for i, (x, y) in enumerate(xy):
        r = inp["attrs"][i][0] if inp["attrs"][i][0] > 0 else 0.024
        ax.add_patch(plt.Circle((x, y), r, color="#D55E00" if i == tid else "#999999", alpha=0.85, zorder=2))
        ax.text(x, y, str(i), ha="center", va="center", fontsize=6, color="white", zorder=3)
    gx, gy = inp["goal"]; bx, by = inp["base"]
    ax.plot(gx, gy, marker="*", ms=14, color="#009E73", zorder=4); ax.plot(bx, by, marker="s", ms=9, color="#0072B2", zorder=4)
    for k, (o, c) in enumerate(sel or []):
        x0, y0 = xy[o]; x1, y1 = cxy[str(c)]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", color="#CC79A7", lw=1.8), zorder=5)
        ax.text(x1, y1 + 0.02, f"{k + 1}", color="#CC79A7", fontsize=8, ha="center", zorder=6)
    ax.set_xlim(-0.2, 0.7); ax.set_ylim(-0.05, 0.7); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=7)


def main():
    snap, frozen, trained, outdir, g2 = sys.argv[1:6]
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    rows = {r["root_id"]: r for r in jl(Path(snap) / "data2d.jsonl") if r["split"] == "val"}
    lab = labels("2d", g2)
    capped = {r["root_id"]: r["selected"] for r in jl(Path(frozen) / "2d/old_M4_B4096_val.jsonl")}
    ex = {r["root_id"]: r for r in jl(Path(frozen) / "2d/ex_M6_val.jsonl")}
    tr = {a: {} for a in ("control", "expanded")}
    for a in tr:
        for p in glob.glob(f"{trained}/2d/{a}_s0_M6_val*.jsonl"):
            tr[a].update({r["root_id"]: r for r in jl(p)})
    cases = []
    for k in sorted(rows):
        r = rows[k]
        if r["masks"]["eval_task"] and r["K_legacy"] == "3":
            fe, _ = dec(ex[k], 4); te, _ = dec(tr["expanded"][k], 4)
            if outcome(capped[k], lab, k) != "SUCCESS" and outcome(fe, lab, k) == "FAIL_Y" and outcome(te, lab, k) == "SUCCESS":
                cases.append(("a", k, 4))
        if r["masks"]["eval_abstain"]:
            fe, _ = dec(ex[k], 6); te, _ = dec(tr["expanded"][k], 6)
            if outcome(fe, lab, k) == "FAIL_Y" and te is None:
                cases.append(("b", k, 6))
    pick = [c for c in cases if c[0] == "a"][:2] + [c for c in cases if c[0] == "b"][:2]
    for kind, k, M in pick:
        fig, axs = plt.subplots(1, 4, figsize=(13, 3.6))
        arms = [("capped V3 (M4, B=4,096)", capped[k], None)]
        for nm, rec in (("frozen V3 D s0, exhaustive", ex[k]), ("D-control s0, exhaustive", tr["control"][k]), ("D-expanded s0, exhaustive", tr["expanded"][k])):
            s, p = dec(rec, M); arms.append((f"{nm} M{M}", s, p))
        for ax, (nm, s, p) in zip(axs, arms):
            o = outcome(s, lab, k)
            draw(ax, rows[k], s, f"{nm}\n{'ABSTAIN' if s is None else ('NOOP' if s == [] else o)}" + (f"  (p11 {p:.2f})" if p is not None else ""))
        fig.suptitle(f"{k}  (K_legacy {rows[k]['K_legacy']}; {'case a: K3 repair' if kind == 'a' else 'case b: NONE root, should abstain'}; outcomes physically verified)\n"
                     "grey = movable objects (index), orange = target, green star = goal, blue square = robot base, magenta arrows = selected ordered relocations "
                     "(schematic; no robot poses)", fontsize=7)
        fig.tight_layout(rect=(0, 0, 1, 0.86)); fig.savefig(out / f"case_{kind}_{k}.png", dpi=150); plt.close(fig)
    print(json.dumps({"cases_found": {"a": sum(c[0] == "a" for c in cases), "b": sum(c[0] == "b" for c in cases)}, "drawn": [c[1] for c in pick]}))


if __name__ == "__main__":
    main()
