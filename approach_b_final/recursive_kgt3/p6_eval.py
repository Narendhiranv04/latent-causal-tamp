#!/usr/bin/env python3
"""P6A — EVALUATOR ONLY (offline).  Labels enter only here, AFTER p6_order.py has produced its orders:
  static validity / static prefix depth (P5A kill-table checker, dev_eval.Static) and physical progress depth of ALREADY-tested orders
  (P4 verify rows + P5B new calls; no new teacher call).  Nothing here is imported by p6_order.py.
    python p6_eval.py prep     P5A_PER_ENDPOINT P5B_ATTEMPTS VERIFY OUT_DIR
    python p6_eval.py analyze  OUT_DIR DEV_PUBLIC DEV_PRIVATE TABLES P5B_ATTEMPTS VERIFY REPORT_DIR
    python p6_eval.py schedule OUT_DIR VERIFY REPORT_DIR          (frozen P6B proposal; NOT executed)"""
import collections, hashlib, json, math, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
EXPOSED = {"ENG2_e3c632c779c0"}                        # P5B physical witness root: previously exposed DEV evidence


def jl(p):
    return [json.loads(l) for l in open(p)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prep(p5a, p5b, verify, out):
    """Evaluator-selected DIAGNOSTIC endpoints (the 53 teacher-Y=1 P5A endpoints) and the list of physically tested orders.  Both files carry
    only (root, assignment/order) - no label - so the public search never sees why they were chosen."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    D = []
    for r in jl(p5a):
        if r["Y_source"] != "teacher" or r.get("static_order_exists") is None:
            continue
        so = r["source_orders"]
        ref = next((o for o in so if any(":committed" in z for z in o["roles"])), None) or min(so, key=lambda o: (o["energy_C"] is None, o["energy_C"] or 0))
        D.append({"root_id": r["root_id"], "endpoint_signature": r["endpoint_signature"], "src_order": ref["seq"], "set": "DIAG_TEACHER_Y"})
    (out / "endpoints_diag.jsonl").write_text("".join(json.dumps(x) + "\n" for x in D))
    seen, O = set(), []
    for r in jl(verify):
        k = (r["root_id"], json.dumps(r["seq"]))
        if k not in seen:
            seen.add(k); O.append({"key": f"V{len(O)}", "root_id": r["root_id"], "order": r["seq"]})
    for a in jl(p5b):
        k = (a["root_id"], json.dumps(a["seq"]))
        if a["X"]["evidence"] == "P5B_NEW_TEACHER_CALL" and k not in seen:
            seen.add(k); O.append({"key": f"B{len(O)}", "root_id": a["root_id"], "order": a["seq"]})
    (out / "tested_orders.jsonl").write_text("".join(json.dumps(x) + "\n" for x in O))
    print(json.dumps({"diag_endpoints": len(D), "tested_orders": len(O)}))


def physical_labels(verify, p5b):
    """(root, order) -> (depth, status): depth = relocations executed before the first failure (m if all relocations executed)."""
    L = {}
    for r in jl(verify):
        ph = r["x_phase"] or ""; m = len(r["seq"])
        d = int(ph.split(":")[1]) if ph.startswith("relocation:") else m
        L[(r["root_id"], json.dumps(r["seq"]))] = (d, r["x_status"], m)
    for a in jl(p5b):
        if a["X"]["evidence"] == "P5B_NEW_TEACHER_CALL":
            L[(a["root_id"], json.dumps(a["seq"]))] = (a["failed_step"] if a["failed_step"] is not None else a["m"], a["X"]["teacher_status"], a["m"])
    return L


def strat_auroc(rows):
    """Position-stratified AUROC: P(feature of an executed step > feature of a failed step) over pairs at the SAME step index."""
    by = collections.defaultdict(lambda: ([], []))
    for pos, y, f in rows:
        by[pos][0 if y else 1].append(f)
    num = den = 0.0
    for P, N in by.values():
        for p in P:
            for n in N:
                num += 1.0 if p > n else 0.5 if p == n else 0.0
                den += 1
    return round(num / den, 4) if den else None, int(den)


def public_step_feats(row0, order, j):
    """Model-free per-step features in the hypothetical scene before move j (public geometry only)."""
    inp = row0["inputs"]; xy = {int(k): v for k, v in inp["cell_xy"].items()}; cells = [int(c) for c in inp["cells0"]]
    for o, d in order[:j]:
        cells[o] = d
    o, d = order[j]; pitch = abs(xy[1][0] - xy[0][0])
    nb = lambda c: sum(1 for i, x in enumerate(cells) if i != o and math.dist(xy[x], xy[c]) <= 1.5 * pitch + 1e-9)  # noqa: E731
    return {"src_base_dist": math.dist(xy[cells[o]], inp["base"]), "dst_base_dist": math.dist(xy[d], inp["base"]),
            "src_clutter": nb(cells[o]), "dst_clutter": nb(d), "step_index": j}


def analyze(out, dev_public, priv, tables, p5b, verify, rep):
    from dev_eval import Static, sha as _s  # noqa: F401
    from p5_order_audit import Chk, run_order, classify
    out, rep = Path(out), Path(rep); rep.mkdir(parents=True, exist_ok=True)
    pub = {r["root_id"]: r for r in jl(dev_public)}; K = {r["root_id"]: r["K"] for r in jl(Path(priv) / "dev_private.jsonl")}
    ST = Static(tables); S = {"stage": "P6A", "evaluator_only": True}
    strip = lambda R: [{k: v for k, v in r.items() if k != "wall_s"} for r in R]  # noqa: E731
    S["reproducible_method_rerun"] = strip(jl(out / "p6_method.jsonl")) == strip(jl(out / "p6_method_rep.jsonl"))
    S["compute"] = {n: {"wall_s": round(sum(r["wall_s"] for r in jl(out / f"p6_{n}.jsonl")), 1),
                        "frozen_calls": dict(sum((collections.Counter(r["frozen_calls"]) for r in jl(out / f"p6_{n}.jsonl")), collections.Counter()))}
                    for n in ("method", "diag")}
    S["input_sha256"] = {f: sha(out / f)[:16] for f in ("endpoints_method.jsonl", "endpoints_diag.jsonl", "tested_orders.jsonl", "p6_method.jsonl",
                                                        "p6_diag.jsonl", "p6_tested_scores.jsonl")}
    chk = lambda rid: Chk(ST, int(pub[rid]["inputs"]["tid"]), int(pub[rid]["inputs"]["goal_cell"]))  # noqa: E731
    c0 = lambda rid: [int(c) for c in pub[rid]["inputs"]["cells0"]]  # noqa: E731

    def stat(rid, order):
        acts = sorted(tuple(a) for a in order); r = run_order(c0(rid), acts, [acts.index(tuple(a)) for a in order], chk(rid))
        return r["status"] == "STATIC_VALID", (len(order) if r["step"] is None else r["step"]) / len(order)

    # ---- D4 / D6: order quality of every arm on both endpoint sets (offline static checker) --------------------------------------
    for name in ("method", "diag"):
        R = jl(out / f"p6_{name}.jsonl"); arms = list(R[0]["arms"]); blk = {"endpoints": len(R), "roots": len({r["root_id"] for r in R})}
        ex = {}
        for r in R:
            acts = [tuple(a) for a in json.loads(r["endpoint_signature"])]
            ex[(r["root_id"], r["endpoint_signature"])] = classify(c0(r["root_id"]), acts, chk(r["root_id"]), do_brute=False)["exists"]
        rec = [r for r in R if ex[(r["root_id"], r["endpoint_signature"])]]
        blk["static_order_exists_endpoints"] = len(rec); blk["static_order_exists_roots"] = len({r["root_id"] for r in rec})
        A = {}
        for a in arms:
            v1 = [stat(r["root_id"], r["arms"][a]["top"][0]["order"]) for r in R]
            vr = [stat(r["root_id"], r["arms"][a]["top"][0]["order"])[0] for r in rec]
            vr_noexp = [stat(r["root_id"], r["arms"][a]["top"][0]["order"])[0] for r in rec if r["root_id"] not in EXPOSED]
            any5 = [any(stat(r["root_id"], t["order"])[0] for t in r["arms"][a]["top"]) for r in rec]
            A[a] = {"top1_static_valid_on_recoverable": f"{sum(vr)}/{len(vr)}", "top1_static_valid_recoverable_excl_exposed": f"{sum(vr_noexp)}/{len(vr_noexp)}",
                    "any_top5_static_valid_on_recoverable": f"{sum(any5)}/{len(any5)}", "mean_static_prefix_frac_all": round(sum(x[1] for x in v1) / len(v1), 3),
                    "mean_W3_C_top1": round(sum(r["arms"][a]["top"][0]["C"] for r in R) / len(R), 3),
                    "mean_window_calls": round(sum(r["arms"][a]["window_calls"] for r in R) / len(R), 1),
                    "top1_differs_from_ORIG": sum(r["arms"][a]["top"][0]["order"] != r["arms"]["ORIG"]["top"][0]["order"] for r in R)}
        blk["arms"] = A
        rk = collections.Counter()                           # D6 ranking effect: fixed candidate pool, different selectors
        for r in rec:
            pool = {json.dumps(t["order"]): t for a in arms for t in r["arms"][a]["top"]}
            P = list(pool.values())
            for sel, key in (("W3", lambda t: t["C"]), ("P4CHUNK", lambda t: t["P4CHUNK"]), ("bottleneck", lambda t: t["bottleneck"])):
                rk[sel] += stat(r["root_id"], min(P, key=lambda t: (key(t), json.dumps(t["order"])))["order"])[0]
            rk["uniform_expected"] += sum(stat(r["root_id"], t["order"])[0] for t in P) / len(P)
            rk["pool_any_valid"] += any(stat(r["root_id"], t["order"])[0] for t in P)
        blk["ranking_effect_fixed_pool_on_recoverable"] = {k: round(v, 2) for k, v in rk.items()} | {"n": len(rec)}
        sp = [r["arms"]["ORIG"]["top"][0]["C"] - r["arms"]["W3_B16"]["top"][0]["C"] for r in R]          # D1 same-endpoint spread
        blk["W3_gain_over_ORIG_nats"] = {"mean": round(sum(sp) / len(sp), 3), "min": round(min(sp), 3), "max": round(max(sp), 3)}
        blk["distinct_top5_orders_W3_B16"] = round(sum(len({json.dumps(t["order"]) for t in r["arms"]["W3_B16"]["top"]}) for r in R) / len(R), 2)
        blk["by_K_static_recoverable"] = dict(collections.Counter(K[r["root_id"]] for r in rec))
        S[name] = blk
    # ---- D5: discrimination on ALREADY physically tested orders (P4 verify + P5B), beyond public heuristics -------------------------
    L = physical_labels(verify, p5b); sc = {r["key"]: r for r in jl(out / "p6_tested_scores.jsonl")}
    to = {r["key"]: r for r in jl(out / "tested_orders.jsonl")}
    feats = collections.defaultdict(list); feats_noexp = collections.defaultdict(list); first = collections.defaultdict(list)
    for k, o in to.items():
        d, st, m = L[(o["root_id"], json.dumps(o["order"]))]; row0 = pub[o["root_id"]]
        for j in range(min(d + 1, m)):
            y = j < d
            f = {"px_W1": sc[k]["W1"][j], "px_W2": sc[k]["W2"][j], "px_W3": sc[k]["W3"][j]}
            f |= {kk: (-v if kk in ("src_base_dist", "dst_base_dist", "src_clutter", "dst_clutter") else v) for kk, v in public_step_feats(row0, o["order"], j).items()}
            for kk, v in f.items():
                feats[kk].append((j, y, v))
                if o["root_id"] not in EXPOSED:
                    feats_noexp[kk].append((j, y, v))
                if j == 0:
                    first[kk].append((0, y, v))
    S["physical_step_discrimination"] = {"note": "position-stratified AUROC; executed step vs first failed step (UNKNOWN or scoped CERTIFIED); "
                                         "public features oriented so that 'nearer base / less clutter' scores higher",
                                         "all": {k: strat_auroc(v) for k, v in feats.items()}, "excl_exposed_root": {k: strat_auroc(v) for k, v in feats_noexp.items()},
                                         "first_move_only": {k: strat_auroc(v) for k, v in first.items()},
                                         "tested_orders": len(to), "steps": len(feats["px_W3"])}
    by_ep = collections.defaultdict(list)                    # within-endpoint order concordance (same assignment, different orders)
    for k, o in to.items():
        d, st, m = L[(o["root_id"], json.dumps(o["order"]))]
        by_ep[(o["root_id"], json.dumps(sorted(o["order"])))].append((d, k))
    conc = collections.Counter()
    for (rid, _), V in by_ep.items():
        for (d1, k1), (d2, k2) in ((a, b) for i, a in enumerate(V) for b in V[i + 1:]):
            if d1 == d2:
                continue
            deep, shal = (k1, k2) if d1 > d2 else (k2, k1)
            for nm, fn in (("W3_C", lambda kk: sum(-math.log(max(1e-4, x)) for x in sc[kk]["W3"])), ("W1_C", lambda kk: sum(-math.log(max(1e-4, x)) for x in sc[kk]["W1"])),
                           ("P4CHUNK_C", lambda kk: sum(-math.log(max(1e-4, x)) for x in sc[kk]["P4CHUNK"]))):
                conc[nm] += fn(deep) < fn(shal)
            conc["pairs"] += 1; conc["pairs_excl_exposed"] += rid not in EXPOSED
    S["within_endpoint_order_concordance"] = dict(conc)
    q = [r for r in jl(p5b) if r["root_id"] in EXPOSED and r["m"] == 10]   # exposed P5B endpoint: reported, never used to tune
    S["exposed_P5B_endpoint_rank"] = sorted(((round(sum(-math.log(max(1e-4, x)) for x in sc[k]["W3"]), 3), r["qid"], r["X_class"])
                                             for r in q for k, o in to.items() if o["root_id"] == r["root_id"] and o["order"] == r["seq"]))
    (rep / "P6A_SUMMARY.json").write_text(json.dumps(S, indent=1))
    print(json.dumps({k: S[k] for k in ("within_endpoint_order_concordance",)}))


def schedule(out, verify, rep):
    """PROPOSED frozen P6B schedule (NOT executed): per DEV root the public rank-0 endpoint; arms P6A (W3_B16 top-1) and the predeclared
    public control CLUTTER_LOW_FIRST; ORIG reused only if already tested.  Y needed once per endpoint unless a VERIFIED Y row exists."""
    R = [r for r in jl(Path(out) / "p6_method.jsonl") if r["rank_public"] == 0]
    tested = {(r["root_id"], json.dumps(r["seq"])) for r in jl(verify)}
    yv = {(r["root_id"], json.dumps(sorted(r["seq"]))) for r in jl(verify) if r["y"] == 1 and r["y_status"] == "VERIFIED"}
    Q = []
    for r in R:
        for arm in ("W3_B16", "CLUTTER_LOW_FIRST", "ORIG"):
            o = r["arms"][arm]["top"][0]["order"]
            if any(x["root_id"] == r["root_id"] and x["seq"] == o for x in Q):
                continue
            reuse = (r["root_id"], json.dumps(o)) in tested
            if arm == "ORIG" and not reuse:
                continue
            Q.append({"qid": f"p{len(Q):02d}", "root_id": r["root_id"], "arm": arm, "seq": o, "m": r["m"], "kind": "X", "reuse_existing": reuse,
                      "exposed_root": r["root_id"] in EXPOSED})
        if (r["root_id"], json.dumps(sorted(json.loads(r["endpoint_signature"])))) not in yv:
            Q.append({"qid": f"p{len(Q):02d}", "root_id": r["root_id"], "arm": "Y_ENDPOINT", "seq": json.loads(r["endpoint_signature"]), "m": r["m"],
                      "kind": "Y", "reuse_existing": False, "exposed_root": r["root_id"] in EXPOSED})
    calls = sum(1 for q in Q if not q["reuse_existing"])
    S = {"stage": "P6B (PROPOSED, NOT EXECUTED)", "caps": {"teacher_calls": calls + 4, "workers": 2, "wall_s": 2700, "confirm_reserve": 4},
         "rules": ["one public rank-0 endpoint per DEV root (frozen hY over sealed P4 pools)", "arms: P6A W3_B16 top-1, CLUTTER_LOW_FIRST control; "
                   "ORIG only when already teacher-tested (reused)", "one Y per endpoint unless a VERIFIED Y row with matching Y2 key exists",
                   "queue order fixed; confirmation reserve 4 (fresh X repeat + fresh Y for first 2 X-positives)", "exposed root ENG2_e3c632c779c0 "
                   "reported separately", "UNKNOWN stays UNKNOWN; scoped certificates only from the teacher's CERTIFIED status"],
         "new_calls": calls, "queue": Q}
    p = Path(rep) / "P6B_PROPOSED_SCHEDULE.json"; p.write_text(json.dumps(S, indent=1)); Path(str(p) + ".sha256").write_text(sha(p) + "\n")
    print(json.dumps({"queue": len(Q), "new_calls": calls, "caps": S["caps"]}))


def figure(out, dev_public, rep):
    """Model-only / static-only P6A figure (no physical claim): (a) top-1 static validity on statically recoverable DIAG endpoints per arm,
    (b) position-stratified physical-step AUROC of frozen vs public features on already-tested orders, (c) budget curve, (d) one
    non-exposed DEV endpoint: ORIG vs P6A order on real geometry."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from p4_viz import grid, BLUE, RED, GREY, GREEN, INK, MUTED, ORANGE
    S = json.loads((Path(rep) / "P6A_SUMMARY.json").read_text()); pub = {r["root_id"]: r for r in jl(dev_public)}
    fig, axs = plt.subplots(1, 4, figsize=(22, 5.2))
    A = S["diag"]["arms"]; arms = [a for a in A if not a.startswith("W3_B") or a == "W3_B16"]
    v = [int(A[a]["top1_static_valid_on_recoverable"].split("/")[0]) for a in arms]; n = int(A[arms[0]]["top1_static_valid_on_recoverable"].split("/")[1])
    cols = [BLUE if a.startswith(("W1", "W2", "W3")) else (GREY if a == "RANDSCORE_B16" else ORANGE) for a in arms]
    axs[0].barh(range(len(arms)), v, color=cols, height=0.6); axs[0].set_yticks(range(len(arms))); axs[0].set_yticklabels(arms, fontsize=8)
    for i, x in enumerate(v):
        axs[0].text(x + 0.1, i, f"{x}/{n}", va="center", fontsize=8, color=INK)
    axs[0].set_xlabel(f"top-1 order statically valid (of {n} statically recoverable teacher-Y endpoints)", color=MUTED, fontsize=8)
    axs[0].set_title("(a) static validity of the selected order (offline checker; NOT physical)", fontsize=8.5, loc="left")
    D = S["physical_step_discrimination"]["all"]; ks = ["px_W3", "px_W2", "px_W1", "src_clutter", "dst_clutter", "src_base_dist", "dst_base_dist"]
    axs[1].barh(range(len(ks)), [D[k][0] for k in ks], color=[BLUE] * 3 + [ORANGE] * 4, height=0.6); axs[1].axvline(0.5, color=MUTED, ls=":")
    axs[1].set_yticks(range(len(ks))); axs[1].set_yticklabels(ks, fontsize=8); axs[1].set_xlim(0.3, 0.9)
    for i, k in enumerate(ks):
        axs[1].text(D[k][0] + 0.005, i, f"{D[k][0]:.2f}", va="center", fontsize=8, color=INK)
    axs[1].set_title(f"(b) executed vs failed step, position-stratified AUROC\n{S['physical_step_discrimination']['tested_orders']} already-tested orders (P4+P5B)", fontsize=8.5, loc="left")
    Bs = [int(a[4:]) for a in A if a.startswith("W3_B")]; Bs.sort()
    for nm, col in (("method", BLUE), ("diag", GREEN)):
        axs[2].plot(Bs, [S[nm]["arms"][f"W3_B{b}"]["mean_W3_C_top1"] for b in Bs], "-o", color=col, label=f"{nm} set")
    axs[2].set_xscale("log", base=2); axs[2].set_xlabel("beam width B"); axs[2].set_ylabel("mean W3 cost of top-1 (nats, lower = better)")
    axs[2].legend(frameon=False, fontsize=8); axs[2].set_title("(c) search budget: cost found vs beam width", fontsize=8.5, loc="left")
    R = [r for r in jl(Path(out) / "p6_diag.jsonl") if r["root_id"] not in EXPOSED]
    r = max(R, key=lambda r: (r["arms"]["ORIG"]["top"][0]["C"] - r["arms"]["W3_B16"]["top"][0]["C"], r["root_id"]))
    inp = pub[r["root_id"]]["inputs"]; c0 = [int(c) for c in inp["cells0"]]
    grid(axs[3], c0, int(inp["tid"]), int(inp["goal_cell"]), [(r["arms"]["ORIG"]["top"][0]["order"], RED, -0.12), (r["arms"]["W3_B16"]["top"][0]["order"], BLUE, 0.12)], [])
    axs[3].set_title(f"(d) {r['root_id']} m={r['m']} (DEV, not exposed) - STATIC-ONLY diagram\nred ORIG C={r['arms']['ORIG']['top'][0]['C']:.1f}  "
                     f"blue P6A W3_B16 C={r['arms']['W3_B16']['top'][0]['C']:.1f} nats", fontsize=8, loc="left")
    for a in axs[:3]:
        for s_ in ("top", "right"):
            a.spines[s_].set_visible(False)
    fig.tight_layout(); fig.savefig(Path(rep) / "p6a_overview.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"prep": lambda: prep(*a[1:5]), "analyze": lambda: analyze(*a[1:8]), "schedule": lambda: schedule(*a[1:4]), "figure": lambda: figure(*a[1:4])}[a[0]]()
