"""P10b-P10e figures and report tables (recorded data only; P6.7 conventions via p6_viz: motion only from recorded witnesses,
CERTIFIED as static panels with certificate kind, BUDGET / UNKNOWN as NO VERIFIED TRACE, edits HYPOTHETICAL, proposals PROPOSED)."""
from __future__ import annotations

import json
from pathlib import Path

import config as cf
import geometry as ge
import p6_viz as pv
from scene import scene_from_dict
from viz import COLORS, plt

DST = Path("visualizations/p10b")


def _rd(p):
    return json.loads(Path(p).read_text())


def _roles(ax, s, ids):
    inv = {v: k for k, v in ids.items()}
    for o in s.objects:
        if o.id in inv:
            ax.text(o.xy_m[0], o.xy_m[1] + 0.03, inv[o.id], ha="center", fontsize=8, weight="bold", color="#c0392b", zorder=12)


def _status_tag(ax, st, kind=None):
    txt = {"VERIFIED_FEASIBLE": "VERIFIED (recorded witness)", "CERTIFIED_INFEASIBLE": f"CERTIFIED ({kind})",
           "BUDGET_INFEASIBLE": "BUDGET (operational) - NO VERIFIED TRACE", "UNKNOWN": "UNKNOWN - NO VERIFIED TRACE"}.get(st, st)
    pv._tag(ax, txt, pv.COL.get(st, "#999"), size=6)


def p10b0_designs() -> None:
    """Dev-seed H10_3 / H10_4 designs (PROPOSED) + dev H7 / H8 pilot roots and P10a H1 / H3 / H4 roots with actual statuses."""
    import p10_scenes as ps
    import p10b_dataset as d
    import p10b_scenes as pb
    DST.mkdir(parents=True, exist_ok=True)
    cfg = cf.load_config("config.toml")
    robot = ge.make_robot(cfg)
    cx = ps.Ctx(cfg, robot)
    f, ax = plt.subplots(2, 4, figsize=(22, 11))
    for j, fam in enumerate(("H10_3", "H10_4")):
        rec = next(r for a in range(400) for r in [pb.try_root(cx, {"family": fam, "seed": d.DEV_SEED0 + 7000 + j, "index": -1, "wave": 0}, a, set())[0]] if r)
        s, ids, dest = rec["scene"], rec["ids"], rec["dest"]
        main = pb.CATALOGUE[fam][0].split()
        pv._panel(ax[0, j], cfg, robot, s, rec["goal_cell"], f"DEV {fam} (seed {rec['seed']}, attempt {rec['attempt']}): main repair {' -> '.join(main)}")
        _roles(ax[0, j], s, ids)
        pv._arrows(ax[0, j], s, [(ids[t], dest[t][0]) for t in main], COLORS["hypothetical"])
        pv._tag(ax[0, j], "PROPOSED, NOT EXECUTED (development seed; never in the dataset)", COLORS["hypothetical"], size=6)
    dev = _rd("runs/p10b/dev_h7h8/plan.json")
    rec = d.records("runs/p10b/dev_h7h8", ("dev",))
    for j, k in enumerate(("p10b_2026124000", "p10b_2026124003")):
        r = dev["roots"][k]
        s = scene_from_dict(r["scene"])
        tok = {q["token"]: q for q in dev["queries"] if q["root"] == k}
        q = tok["M"]
        x = rec[q["query"]]
        pv._panel(ax[0, 2 + j], cfg, robot, s, r["goal_cell"], f"DEV {r['family']} {k[-4:]}: physical 'M' -> {x['teacher_status'][:9]}; "
                  f"edit A -> {rec[tok['edit:A']['query']]['teacher_status'][:9]}")
        _roles(ax[0, 2 + j], s, r["ids"])
        pv._arrows(ax[0, 2 + j], s, [tuple(a) for a in q["sequence"]], pv.COL[x["teacher_status"]])
        _status_tag(ax[0, 2 + j], x["teacher_status"], (x.get("static_certificate") or {}).get("kind"))
    pa = _rd("runs/p10/p10a/plan.json")
    dec = _rd("runs/p10/p10a/decisions.json")
    for j, (k, want) in enumerate((("p10a_2026102801", "edit:A+B"), ("p10a_2026102803", "B A"), ("p10a_2026102804", "C A"))):
        r = pa["roots"][k]
        s = scene_from_dict(r["scene"])
        import p10_collect as pc
        q = next(q for q in pa["queries"] if q["root"] == k and pc._tok(pa, q) == want)
        x = dec[q["query"]]
        pv._panel(ax[1, j], cfg, robot, s, r["goal_cell"], f"P10a {r['mechanism']} {k[-2:]}: '{want}' -> {x['teacher_status'][:9]}")
        _roles(ax[1, j], s, r["ids"])
        if q["sequence"]:
            pv._arrows(ax[1, j], s, [tuple(a) for a in q["sequence"]], COLORS["valid"])
        _status_tag(ax[1, j], x["teacher_status"])
    ax[1, 3].axis("off")
    ax[1, 3].text(0, 0.95, "Recorded witness trajectories for the P10a roots:\nvisualizations/p10/roots/<root>_evidence.gif\n\n"
                  "Top row: development seeds only (P10b-0).\nH7: edit VERIFIED vs physical relocation CERTIFIED\n(FIRST_MOVER placement screen; scope ASSIGNMENT).\n"
                  "H8: original CERTIFIED by the sector checker;\nbarrier removal VERIFIED (edit and relocation).", fontsize=9, va="top")
    pv.png(f, DST / "P10b0_designs_and_dev_pilot.png", "P10b-0: H10 designs (PROPOSED), dev H7 / H8 pilot statuses, P10a H1 / H3 / H4 VERIFIED repairs")
    cf.write_json(DST / "INDEX_p10b0.json", pv.INDEX)
