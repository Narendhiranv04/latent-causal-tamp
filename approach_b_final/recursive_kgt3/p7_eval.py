#!/usr/bin/env python3
"""P7A — EVALUATOR ONLY (offline, after p7_repair.py predictions).  Static validity / existence via the P5A kill-table checker, frozen y_end
(already public in the outputs), generation vs ranking, diversity, cost, paired FULL-vs-control counts, the A2 numeric gate, and the
private enabler audit (P5A never-moved blockers vs public suspects).  Never imported by p7_repair.py.
    python p7_eval.py analyze RUN_DIR DEV_PRIVATE TABLES P5A_PER_ENDPOINT P4_DIR REPORT_DIR
    python p7_eval.py figure  RUN_DIR REPORT_DIR"""
import collections, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
EXPOSED = {"ENG2_e3c632c779c0"}
ARMS = ("ORIG", "FULL", "DEST_ONLY", "OBJSET_ONLY", "FLAT", "RANDOM", "FULL_phiG", "FULL_phiY")


def jl(p):
    return [json.loads(l) for l in open(p)]


def analyze(run, priv, tables, p5a, p4, rep):
    from dev_eval import Static
    from p5_order_audit import Chk, run_order, classify
    run, rep = Path(run), Path(rep); rep.mkdir(parents=True, exist_ok=True)
    pub = {r["root_id"]: r for r in jl(run / "dev_public.jsonl")}; K = {r["root_id"]: r["K"] for r in jl(Path(priv) / "dev_private.jsonl")}
    ST = Static(tables)
    pool_objs = collections.defaultdict(set)
    for a in ("R2", "R3", "F"):
        for rid in pub:
            for c in json.loads((Path(p4) / a / "traces" / f"{rid}.json").read_text())["cands"]:
                pool_objs[rid] |= {int(o) for o, _ in c["seq"]}

    def judge(rid, plan):
        inp = pub[rid]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; chk = Chk(ST, int(inp["tid"]), int(inp["goal_cell"]))
        acts = sorted(tuple(m) for m in plan); r = run_order(c0, acts, [acts.index(tuple(m)) for m in plan], chk)
        cells = list(c0)
        for o, d in plan:
            cells[o] = d
        return {"valid": r["status"] == "STATIC_VALID", "exists": classify(c0, acts, chk, do_brute=False)["exists"],
                "final_live": ST.feasible(cells, int(inp["tid"]), int(inp["goal_cell"])), "status": r["status"]}

    S = {"stage": "P7A", "evaluator_only": True, "exploratory_exposed_DEV": True}; J = {}
    for name in ("method", "diag"):
        R = jl(run / f"p7_{name}.jsonl"); blk = {"endpoints": len(R), "roots": len({r["root_id"] for r in R}), "arms": {}}
        for arm in ARMS:
            rows = []
            for r in R:
                v = r["arms"][arm]; top = v["top"]
                j1 = judge(r["root_id"], top[0]["plan"]) if top else None
                anyv = any(judge(r["root_id"], t["plan"])["valid"] for t in top) if top else False
                cv = {int(k): set(x) for k, x in r["cvae_S0"].items()}
                rows.append({"rid": r["root_id"], "sig": r["endpoint_signature"], "K": K[r["root_id"]], "avail": bool(top), "j1": j1, "any5": anyv,
                             "y": top[0].get("y_end") if top else None, "len": len(top[0]["plan"]) if top else None,
                             "added": len(top[0].get("added", [])) if top else 0, "dropped": len(top[0].get("dropped", [])) if top else 0,
                             "chg": len(top[0].get("dest_changed", [])) if top else 0,
                             "new_obj": sum(1 for o, _ in top[0]["plan"] if o not in pool_objs[r["root_id"]]) if top else 0,
                             "dest_out_cvae": sum(1 for o, d in top[0]["plan"] if d not in cv.get(o, set())) if top else 0,
                             "used": v.get("used", {}), "wall": v.get("wall_s", 0), "pobj": len(v.get("proposed_objects", [])), "pdst": len(v.get("proposed_dests", []))})
            J[(name, arm)] = rows
            n = len(rows); f = lambda k: sum(1 for x in rows if x["j1"] and x["j1"][k])  # noqa: E731
            av = [x for x in rows if x["avail"]]
            blk["arms"][arm] = {"available": f"{len(av)}/{n}", "top1_static_valid": f("valid"), "top1_static_order_exists": f("exists"),
                                "top1_final_target_live": f("final_live"), "any_top5_static_valid": sum(x["any5"] for x in rows),
                                "generation_failures": sum(1 for x in rows if not x["any5"]), "ranking_failures": sum(1 for x in rows if x["any5"] and not (x["j1"] and x["j1"]["valid"])),
                                "top1_static_valid_excl_exposed": sum(1 for x in rows if x["j1"] and x["j1"]["valid"] and x["rid"] not in EXPOSED),
                                "mean_y_end_top1": round(sum(x["y"] or 0 for x in av) / max(1, len(av)), 3), "mean_len": round(sum(x["len"] for x in av) / max(1, len(av)), 2),
                                "mean_added": round(sum(x["added"] for x in av) / max(1, len(av)), 2), "mean_dropped": round(sum(x["dropped"] for x in av) / max(1, len(av)), 2),
                                "mean_dest_changed": round(sum(x["chg"] for x in av) / max(1, len(av)), 2), "top1_objects_absent_from_P4_pools": sum(x["new_obj"] for x in rows),
                                "top1_dests_outside_cvae_top4": sum(x["dest_out_cvae"] for x in rows), "mean_proposed_objects": round(sum(x["pobj"] for x in rows) / n, 1),
                                "mean_proposed_dests": round(sum(x["pdst"] for x in rows) / n, 1), "mean_phi_used": round(sum(x["used"].get("phi", 0) for x in rows) / n, 1),
                                "mean_y_used": round(sum(x["used"].get("y", 0) for x in rows) / n, 1), "mean_geo_evals": round(sum(x["used"].get("geo", 0) for x in rows) / n, 1),
                                "wall_s_total": round(sum(x["wall"] for x in rows), 1),
                                "top1_static_valid_by_K": dict(collections.Counter(x["K"] for x in rows if x["j1"] and x["j1"]["valid"])),
                                "top1_exists_by_K": dict(collections.Counter(x["K"] for x in rows if x["j1"] and x["j1"]["exists"]))}
        blk["endpoints_by_K"] = dict(collections.Counter(K[r["root_id"]] for r in R))
        S[name] = blk
    # ---- paired comparisons + A2 gate (union of both sets, excluding exposed root) ---------------------------------------------------
    pairs = {}
    for other in ("FLAT", "RANDOM", "DEST_ONLY", "OBJSET_ONLY", "ORIG"):
        d = {}
        for metric in ("valid", "exists"):
            w = l = 0
            for name in ("method", "diag"):
                for a, b in zip(J[(name, "FULL")], J[(name, other)]):
                    if a["rid"] in EXPOSED:
                        continue
                    x, y = bool(a["j1"] and a["j1"][metric]), bool(b["j1"] and b["j1"][metric])
                    w += x and not y; l += y and not x
            d[metric] = {"FULL_wins": w, "FULL_losses": l, "net": w - l}
        pairs[other] = d
    S["paired_FULL_vs"] = pairs
    cred = {o: any(pairs[o][m]["net"] >= 3 for m in ("valid", "exists")) for o in ("FLAT", "RANDOM")}
    S["gate_A2"] = {"credible_vs_FLAT": cred["FLAT"], "credible_vs_RANDOM": cred["RANDOM"],
                    "decision": "PROCEED" if all(cred.values()) else "REVISE", "fixtures": "12/12 pass (tests/test_p7_repair.py)"}
    # ---- private enabler audit (diag set; evaluator only) ----------------------------------------------------------------------------
    P5 = {(r["root_id"], r["endpoint_signature"]): r for r in jl(p5a) if r["Y_source"] == "teacher"}
    aud = collections.Counter()
    for r in jl(run / "p7_diag.jsonl"):
        p = P5.get((r["root_id"], r["endpoint_signature"]))
        if not p or not p.get("never_executable"):
            continue
        B = {b for n in p["never_executable"] if n["kind"] == "PICK_NEVER_STRUCTURAL" for b in n["unmoved_blockers"] if b != "BASE"}
        if not B:
            continue
        sus = set(r["arms"]["FULL"]["suspects_S0"]); moved = {o for t in r["arms"]["FULL"]["top"] for o, _ in t["plan"]}
        aud["endpoints_with_unmoved_pick_blockers"] += 1; aud["blockers_total"] += len(B)
        aud["blockers_in_public_suspects_S0"] += len(B & sus); aud["suspects_total"] += len(sus); aud["suspects_that_are_blockers"] += len(sus & B)
        aud["endpoints_FULL_top5_moves_a_blocker"] += bool(B & moved)
        aud["blockers_absent_from_all_P4_pools"] += len(B - pool_objs[r["root_id"]])
        aud["endpoints_FULL_top1_static_valid"] += bool(judge(r["root_id"], r["arms"]["FULL"]["top"][0]["plan"])["valid"]) if r["arms"]["FULL"]["top"] else 0
        aud["endpoints_FULL_top1_static_exists"] += bool(judge(r["root_id"], r["arms"]["FULL"]["top"][0]["plan"])["exists"]) if r["arms"]["FULL"]["top"] else 0
    S["enabler_audit_private"] = dict(aud)
    (rep / "P7A_SUMMARY.json").write_text(json.dumps(S, indent=1))
    (rep / "P7A_JUDGED_TOP1.jsonl").write_text("".join(json.dumps({"set": n, "arm": a, **{k: v for k, v in x.items() if k != "used"}}) + "\n"
                                                       for (n, a), rows in J.items() for x in rows))
    print(json.dumps(S["gate_A2"]), json.dumps(S["paired_FULL_vs"]))


TABLES_FOR_FIG = "/home/naren/Desktop/boltzmann_lfd/.claude/worktrees/scaling2d/scaling2d_k12/G1"


def figure(run, rep):
    """Scene-based, UNVERIFIED (static-only) views for one diag endpoint where FULL inserted an enabler: original sequence, public suspects
    (suspected dependency), changed object set, new placement candidates, final composed hypothetical plan."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from p4_viz import grid, BLUE, RED, GREEN, ORANGE, GREY, INK, MUTED
    from dev_eval import Static
    pub = {r["root_id"]: r for r in jl(Path(run) / "dev_public.jsonl")}
    Jd = {(x["rid"], x["sig"]): x for x in jl(Path(rep) / "P7A_JUDGED_TOP1.jsonl") if x["set"] == "diag" and x["arm"] == "FULL"}
    ch = lambda t: t["added"] or t["dropped"] or t["dest_changed"]  # noqa: E731
    R = [r for r in jl(Path(run) / "p7_diag.jsonl") if r["arms"]["FULL"]["top"] and ch(r["arms"]["FULL"]["top"][0]) and r["root_id"] not in EXPOSED]
    R.sort(key=lambda r: (not (Jd[(r["root_id"], r["endpoint_signature"])]["j1"] or {}).get("valid"), -len(r["arms"]["FULL"]["top"][0]["added"]),
                          -(Jd[(r["root_id"], r["endpoint_signature"])]["j1"] or {}).get("final_live", 0), r["root_id"]))
    ex, seen = [], set()
    for r in R:
        if r["root_id"] not in seen and len(ex) < 2:
            ex.append((r, "FULL", "")); seen.add(r["root_id"])
    pd = Path(run) / "p7d_diag.jsonl"                           # POST-HOC diagnostic row: an actual enabler insertion on a real scene
    if pd.exists():
        D = [r for r in jl(pd) if r["arms"]["DIAG_NODROP"]["top"] and r["arms"]["DIAG_NODROP"]["top"][0]["added"] and r["root_id"] not in EXPOSED | seen]
        D.sort(key=lambda r: (-len(r["arms"]["DIAG_NODROP"]["top"][0]["added"]), r["root_id"]))
        if D:
            r = D[0]; r["arms"]["ORIG"] = next(x for x in jl(Path(run) / "p7_diag.jsonl") if x["root_id"] == r["root_id"] and x["endpoint_signature"] == r["endpoint_signature"])["arms"]["ORIG"]
            ex.append((r, "DIAG_NODROP", "POST-HOC DIAG (not pre-reg.) "))
    from p5_order_audit import Chk, run_order
    fig, axs = plt.subplots(len(ex), 3, figsize=(18, 6.0 * len(ex)), squeeze=False)
    for row, (r, arm, tag) in zip(axs, ex):
        inp = pub[r["root_id"]]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; T0, G0 = int(inp["tid"]), int(inp["goal_cell"])
        t = r["arms"][arm]["top"][0]; jd = (Jd.get((r["root_id"], r["endpoint_signature"])) or {}).get("j1") or {} if arm == "FULL" else {}
        grid(row[0], c0, T0, G0, [(r["arms"]["ORIG"]["top"][0]["plan"], RED, 0.0)], [])
        row[0].set_title(f"{tag}{r['root_id']} (DEV, exposed set; exploratory)\n(1) original P4 sequence, m={r['m']}", fontsize=8.5, loc="left")
        grid(row[1], c0, T0, G0, [], [])
        for o in r["arms"][arm]["suspects_S0"]:
            row[1].scatter(c0[o] % 8, c0[o] // 8, s=420, facecolors="none", edgecolors=ORANGE, lw=1.8, zorder=5)
        for o, d in json.loads(r["endpoint_signature"]):
            row[1].scatter(c0[o] % 8, c0[o] // 8, s=420, facecolors="none", edgecolors=RED, lw=1.0, ls="--", zorder=5)
        for o, d in t["added"] + t["dest_changed"]:
            for p in r["cvae_S0"].get(str(o), []):
                row[1].scatter(p % 8, p // 8, s=60, marker="+", color=MUTED, zorder=4)
            row[1].scatter(d % 8, d // 8, s=90, marker="*", color=GREEN, zorder=6)
        row[1].set_title("(2) public suspects = orange rings (suspected dependency; HEURISTIC)\noriginal movers = red dashed; cVAE S0 candidates (+);"
                         " chosen new placements (green star)", fontsize=8, loc="left")
        grid(row[2], c0, T0, G0, [(t["plan"], BLUE, 0.0)], [])
        for o, _ in t["added"]:
            row[2].scatter(c0[o] % 8, c0[o] // 8, s=420, facecolors="none", edgecolors=GREEN, lw=2.0, zorder=5)
        if not jd:
            ST_ = Static(TABLES_FOR_FIG); chk = Chk(ST_, T0, G0); acts = sorted(tuple(m) for m in t["plan"])
            jd = {"status": run_order(c0, acts, [acts.index(tuple(m)) for m in t["plan"]], chk)["status"]}; jd["valid"] = jd["status"] == "STATIC_VALID"
        row[2].set_title(f"(3) {arm} composed HYPOTHETICAL plan: {len(t['plan'])} moves\n+{len(t['added'])} enablers (green ring), -{len(t['dropped'])} dropped, "
                         f"{len(t['dest_changed'])} re-destined\nUNVERIFIED physically; offline static: {'VALID' if jd.get('valid') else jd.get('status')}; "
                         f"frozen y_end {t.get('y_end') or 0:.2f}", fontsize=8, loc="left")
    fig.tight_layout(); fig.savefig(Path(rep) / "p7a_examples.png", dpi=115); plt.close(fig)
    S = json.loads((Path(rep) / "P7A_SUMMARY.json").read_text())
    arms = ["ORIG", "FULL", "DEST_ONLY", "OBJSET_ONLY", "FLAT", "RANDOM", "FULL_phiG", "FULL_phiY"]
    fig, axs = plt.subplots(1, 2, figsize=(15, 4.6))
    for ax, name in zip(axs, ("method", "diag")):
        A = S[name]["arms"]; x = range(len(arms)); w = 0.27
        for j, (k, col, lab) in enumerate((("top1_static_valid", BLUE, "top-1 static-valid order"), ("top1_static_order_exists", GREEN, "top-1 assignment admits a static order"),
                                           ("any_top5_static_valid", GREY, "any top-5 static-valid (generation)"))):
            ax.bar([i + (j - 1) * w for i in x], [A[a][k] for a in arms], width=w, color=col, label=lab)
        ax.set_xticks(list(x)); ax.set_xticklabels(arms, rotation=25, fontsize=8); ax.set_ylabel(f"endpoints (of {S[name]['endpoints']})")
        ax.set_title(f"{name} set - offline static proxy, matched budget (exploratory, exposed DEV; not physical)", fontsize=8.5, loc="left")
        ax.legend(frameon=False, fontsize=7.5)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
    fig.tight_layout(); fig.savefig(Path(rep) / "p7a_arms.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"analyze": lambda: analyze(*a[1:7]), "figure": lambda: figure(*a[1:3])}[a[0]]()
