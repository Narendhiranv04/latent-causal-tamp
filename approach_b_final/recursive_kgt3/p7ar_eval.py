#!/usr/bin/env python3
"""P7A-R — EVALUATOR ONLY, run ONCE on sealed new-root predictions (P7AR_PREREG sections 6-7).  Static checker (P5A Chk / run_order /
classify over the construction-time kill tables) gives the primary root-level metric; K_lb strata from the private root file.
    python p7ar_eval.py analyze PREDICTIONS.jsonl ROOTS_PUBLIC ROOTS_PRIVATE TABLES REPORT_DIR
    python p7ar_eval.py figure  PREDICTIONS.jsonl ROOTS_PUBLIC REPORT_DIR"""
import collections, hashlib, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ARMS = ("ORIG", "DEST_ONLY", "FULL_R", "FULL_R_GEOM", "FLAT_STRONG", "RANDOM_MATCHED")
CONTROLS = ("FLAT_STRONG", "RANDOM_MATCHED", "ORIG", "DEST_ONLY")
STAGES = ("suspect", "generated", "scored", "survivor", "complete", "top5", "committed")


def jl(p):
    return [json.loads(l) for l in open(p)]


def analyze(pred, roots_public, roots_private, tables, rep):
    from dev_eval import Static
    from p5_order_audit import Chk, run_order, classify
    rep = Path(rep); rep.mkdir(parents=True, exist_ok=True)
    pub = {r["root_id"]: r for r in jl(roots_public)}; priv = {r["root_id"]: r for r in jl(roots_private)}; ST = Static(tables)
    P = jl(pred)

    def judge(rid, plan):
        inp = pub[rid]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; chk = Chk(ST, int(inp["tid"]), int(inp["goal_cell"]))
        acts = sorted(tuple(m) for m in plan); r = run_order(c0, acts, [acts.index(tuple(m)) for m in plan], chk); cells = list(c0)
        for o, d in plan:
            cells[o] = d
        return {"valid": r["status"] == "STATIC_VALID", "status": r["status"], "exists": classify(c0, acts, chk, do_brute=False)["exists"],
                "final_live": bool(ST.feasible(cells, int(inp["tid"]), int(inp["goal_cell"])))}
    rows = []
    for r in P:
        rid = r["root_id"]; rec = {"root_id": rid, "K_lb": priv[rid]["K_lb"], "n_objects": priv[rid]["n_objects"]}
        for arm in ARMS:
            com = r["arms"][arm]["committed"]
            if not com:
                rec[arm] = {"available": False, "valid": False, "exists": False, "final_live": False}; continue
            j = judge(rid, com["plan"]); A = json.loads(com["endpoint_signature"]); Ao = {o for o, _ in A}; Po = {o for o, _ in com["plan"]}
            top5 = [t for e in r["arms"][arm]["per_endpoint"] for t in e["top"]]
            rec[arm] = j | {"available": True, "len": len(com["plan"]), "novel": len(com.get("novel", [])), "novel_valid": bool(com.get("novel")) and j["valid"],
                            "retention": round(len(Ao & Po) / len(Ao), 3), "replaced": len(Ao - Po), "dest_changed": sum(1 for o, d in com["plan"] if o in Ao and [o, d] not in A),
                            "y_end": com.get("y_end"), "endpoint_rank": r["endpoints"].index(com["endpoint_signature"]),
                            "top5_valid": sum(judge(rid, t["plan"])["valid"] for t in top5), "n_cands": len(top5)}
        rows.append(rec)
    N = len(rows); S = {"stage": "P7A-R", "evaluator_only": True, "run_once": True, "roots": N,
                       "predictions_sha256": hashlib.sha256(Path(pred).read_bytes()).hexdigest(),
                       "by_K": dict(collections.Counter(r["K_lb"] for r in rows))}
    S["primary_static_valid"] = {a: sum(r[a]["valid"] for r in rows) for a in ARMS}
    S["secondary"] = {a: {"static_order_exists": sum(r[a]["exists"] for r in rows), "final_target_live": sum(r[a]["final_live"] for r in rows),
                          "novel_enabler_roots": sum(1 for r in rows if r[a].get("novel")), "novel_and_valid_roots": sum(1 for r in rows if r[a].get("novel_valid")),
                          "mean_len": round(sum(r[a].get("len", 0) for r in rows) / N, 2), "mean_retention": round(sum(r[a].get("retention", 0) for r in rows) / N, 3),
                          "mean_dest_changed": round(sum(r[a].get("dest_changed", 0) for r in rows) / N, 2),
                          "roots_with_any_top5_valid": sum(1 for r in rows if r[a].get("top5_valid")),
                          "valid_by_K": dict(collections.Counter(r["K_lb"] for r in rows if r[a]["valid"]))} for a in ARMS}
    pair = {}
    for c in CONTROLS + ("FULL_R_GEOM",):
        w = sum(1 for r in rows if r["FULL_R"]["valid"] and not r[c]["valid"]); l = sum(1 for r in rows if r[c]["valid"] and not r["FULL_R"]["valid"])
        we = sum(1 for r in rows if r["FULL_R"]["exists"] and not r[c]["exists"]); le = sum(1 for r in rows if r[c]["exists"] and not r["FULL_R"]["exists"])
        rng, bs = random.Random(0), []
        for _ in range(2000):
            sm = [rng.choice(rows) for _ in rows]; bs.append(sum(int(x["FULL_R"]["valid"]) - int(x[c]["valid"]) for x in sm))
        bs.sort()
        pair[c] = {"wins": w, "losses": l, "net": w - l, "exists_net": we - le, "root_bootstrap_net_95": [bs[50], bs[1949]]}
    S["paired_FULL_R_vs"] = pair
    nv = S["secondary"]["FULL_R"]["novel_and_valid_roots"]
    passed = all(pair[c]["net"] >= 3 for c in CONTROLS) and nv >= 2
    S["gate"] = {"rule": "net >= 3 vs each of FLAT_STRONG, RANDOM_MATCHED, ORIG, DEST_ONLY and >= 2 roots with novel enabler AND static-valid",
                 "nets": {c: pair[c]["net"] for c in CONTROLS}, "novel_valid_roots": nv,
                 "decision": "PASS" if passed else "BLOCKED_FROZEN_KGT3",
                 "learned_contribution": {"FULL_R_valid": S["primary_static_valid"]["FULL_R"], "FULL_R_GEOM_valid": S["primary_static_valid"]["FULL_R_GEOM"],
                                          "note": "if GEOM >= FULL_R any success is an analytical geometry baseline"}}
    fun = {}
    for arm in ("FULL_R", "FULL_R_GEOM", "RANDOM_MATCHED"):
        cnt, last = collections.Counter(), collections.Counter()
        for r in P:
            v = r["arms"][arm]; com = v["committed"] or {}
            comm = {o for o, _ in com.get("plan", [])} - {o for o, _ in json.loads(com["endpoint_signature"])} if com else set()
            for e in v["per_endpoint"]:
                A = {o for o, _ in json.loads(e["endpoint_signature"])}; f = {k: set(x) for k, x in e["funnel"].items() if k != "generated_actions"}
                f["top5"] = {o for t in e["top"] for o, _ in t["plan"] if o not in A}
                f["committed"] = comm if com and com["endpoint_signature"] == e["endpoint_signature"] else set()
                for st in STAGES:
                    cnt[st] += len(f.get(st, set()))
                cnt["generated_actions"] += e["funnel"]["generated_actions"]
                for o in f["suspect"]:
                    lastst = max((i for i, st in enumerate(STAGES) if o in f.get(st, set())), default=0); last[STAGES[lastst]] += 1
        fun[arm] = {"stage_object_counts": {k: cnt[k] for k in STAGES}, "generated_enabler_actions": cnt["generated_actions"],
                    "suspects_last_seen_at": dict(last)}
    S["funnel"] = fun
    led = {}
    for arm in ARMS[1:]:
        u = collections.Counter(); stops = collections.Counter(); wall = 0.0
        for r in P:
            wall += r["arms"][arm]["wall_s"]
            for e in r["arms"][arm]["per_endpoint"]:
                u.update(e["used"]); stops[e["stop"]] += 1
        led[arm] = {"model_calls": u["model"], "geo_evals": u["geo"], "expansions": u["expansions"], "layers": u["layers"], "wall_s": round(wall, 1),
                    "stops": dict(stops), "caps_per_endpoint": {"model": 6000, "yend": 200, "geo": 3000000, "layers": 24}}
    S["resource_ledger"] = led
    S["committed_atomic_replacements"] = {a: sum(r[a].get("replaced", 0) for r in rows) for a in ARMS}
    (rep / "P7AR_EVAL.json").write_text(json.dumps(S, indent=1))
    (rep / "P7AR_PER_ROOT.json").write_text(json.dumps(rows, indent=1))
    keys = ("valid", "exists", "final_live", "novel", "len")
    hdr = ["root_id", "K_lb", "n_objects"] + [f"{a}:{k}" for a in ARMS for k in keys]
    lines = [",".join(hdr)] + [",".join([r["root_id"], str(r["K_lb"]), str(r["n_objects"])] + [str(r[a].get(k, "")) for a in ARMS for k in keys]) for r in rows]
    (rep / "P7AR_PER_ROOT.csv").write_text("\n".join(lines) + "\n")
    print(json.dumps({"primary": S["primary_static_valid"], "gate": S["gate"]}))


def figure(pred, roots_public, rep):
    """Real geometry, clearly HYPOTHETICAL: FULL-R committed plans; enabler access before/after for the dependent moves (public proxy)."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from p4_viz import grid, BLUE, RED, GREEN, ORANGE, MUTED
    import p7ar_repair as RP
    pub = {r["root_id"]: r for r in jl(roots_public)}; per = {r["root_id"]: r for r in json.loads((Path(rep) / "P7AR_PER_ROOT.json").read_text())}
    P = jl(pred)
    pick = sorted(P, key=lambda r: (-(r["arms"]["FULL_R"]["committed"] or {}).get("novel", []).__len__(), not per[r["root_id"]]["FULL_R"]["valid"], r["root_id"]))[:3]
    fig, axs = plt.subplots(len(pick), 3, figsize=(18, 6 * len(pick)), squeeze=False)
    for row, r in zip(axs, pick):
        rid = r["root_id"]; inp = pub[rid]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; T0, G0 = int(inp["tid"]), int(inp["goal_cell"])
        com = r["arms"]["FULL_R"]["committed"]; orig = r["arms"]["ORIG"]["committed"]; g = RP.Geo(pub[rid])
        grid(row[0], c0, T0, G0, [(orig["plan"], RED, 0.0)], [])
        row[0].set_title(f"{rid} (new DEV root, K stratum hidden from planner)\n(1) ORIG P4 order; static: {'VALID' if per[rid]['ORIG']['valid'] else per[rid]['ORIG']['status']}", fontsize=8, loc="left")
        grid(row[1], c0, T0, G0, [], [])
        for e in com.get("novel", []):
            row[1].scatter(c0[e[0]] % 8, c0[e[0]] // 8, s=430, facecolors="none", edgecolors=GREEN, lw=2, zorder=5)
            row[1].scatter(e[1] % 8, e[1] // 8, s=90, marker="*", color=GREEN, zorder=6)
        A = json.loads(com["endpoint_signature"]); txt = []
        for o, d in A[:12]:
            before = g.acc(c0, o, d); c1 = list(c0)
            for m in com["plan"]:
                if m[0] == o:
                    break
                c1[m[0]] = m[1]
            after = g.acc(c1, o, [x for x in com["plan"] if x[0] == o][0][1]) if any(x[0] == o for x in com["plan"]) else None
            if after is not None and abs(after - before) > 1e-9:
                txt.append(f"o{o:02d}: access {before:.2f} -> {after:.2f}")
                row[1].scatter(c0[o] % 8, c0[o] // 8, s=430, facecolors="none", edgecolors=ORANGE, lw=1.6, zorder=5)
        row[1].set_title("(2) public directional access proxy (HEURISTIC): novel enablers (green ring -> star),\nanchor moves whose access changed before execution (orange)", fontsize=8, loc="left")
        row[1].text(0.01, 0.01, "\n".join(txt[:8]) or "no access change", transform=row[1].transAxes, fontsize=7, color=MUTED, va="bottom")
        grid(row[2], c0, T0, G0, [(com["plan"], BLUE, 0.0)], [])
        row[2].set_title(f"(3) FULL-R committed HYPOTHETICAL plan, {len(com['plan'])} moves, +{len(com.get('novel', []))} novel enablers\n"
                         f"UNVERIFIED physically; offline static: {'VALID' if per[rid]['FULL_R']['valid'] else per[rid]['FULL_R']['status']}", fontsize=8, loc="left")
    fig.tight_layout(); fig.savefig(Path(rep) / "p7ar_examples.png", dpi=110); plt.close(fig)
    S = json.loads((Path(rep) / "P7AR_EVAL.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(15, 4.6))
    arms = list(ARMS); v = [S["primary_static_valid"][a] for a in arms]
    axs[0].bar(range(len(arms)), v, color=[GREEN if a == "FULL_R" else MUTED for a in arms], width=0.6)
    for i, x in enumerate(v):
        axs[0].text(i, x + 0.1, str(x), ha="center", fontsize=9)
    axs[0].set_xticks(range(len(arms))); axs[0].set_xticklabels(arms, rotation=20, fontsize=8); axs[0].set_ylabel(f"roots (of {S['roots']})")
    axs[0].set_title("primary: committed plan passes the offline static check (NOT physical)", fontsize=9, loc="left")
    F = S["funnel"]["FULL_R"]["stage_object_counts"]; axs[1].bar(range(len(STAGES)), [F[k] for k in STAGES], color=BLUE, width=0.6)
    axs[1].set_xticks(range(len(STAGES))); axs[1].set_xticklabels(STAGES, rotation=20, fontsize=8)
    axs[1].set_title("FULL-R enabler funnel (object counts summed over endpoints)", fontsize=9, loc="left")
    for a in axs:
        for s_ in ("top", "right"):
            a.spines[s_].set_visible(False)
    fig.tight_layout(); fig.savefig(Path(rep) / "p7ar_primary_funnel.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"analyze": lambda: analyze(*a[1:6]), "figure": lambda: figure(*a[1:4])}[a[0]]()
