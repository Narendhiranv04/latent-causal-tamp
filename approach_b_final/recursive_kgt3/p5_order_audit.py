#!/usr/bin/env python3
"""P5A — EVALUATOR ONLY, post-seal.  Exhaustive STATIC same-endpoint order audit of P4 Y-positive endpoints.
For each endpoint (root, canonical {object -> destination} assignment) recovered from the sealed P4 R2/R3/F committed plans and candidate
pools, a subset DP over completed-action masks (<= 2^12 = 4096 nodes) decides whether ANY ordering of the same moves is statically
executable under the construction-time grasp-screen kill tables (dev_eval.Static, MINK_STATIC_V2), followed by the final target pick/goal
place.  Scope: object arrangement only.  It is NOT a robot-motion proof (no carried q, no connector, no swept volumes).
Never imported by planners/models; no teacher queries; no training; release_v2 TEST is never opened.
    python p5_order_audit.py P4_DIR VERIFY.jsonl DEV_PUBLIC DEV_PRIVATE_DIR TABLES_DIR TEACHER_LONG.py OUT_DIR [--workers 4]"""
import argparse, collections, hashlib, itertools, json, os, platform, random, subprocess, sys, time
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ARMS = ("R2", "R3", "F")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jl(p):
    return [json.loads(l) for l in open(p)]


class Chk:
    """Static kill-table liveness on a full cell list (index = object).  None = object deleted (structural probes only)."""
    def __init__(s, ST, T0, goal):
        s.ST, s.T0, s.goal = ST, T0, goal

    def _oth(s, cells, i):
        return [c for j, c in enumerate(cells) if j != i and c is not None]

    def pick(s, cells, i):
        return bool(s.ST.pick(cells[i], s._oth(cells, i)))

    def place(s, cells, i, d):
        return bool(s.ST.place(d, s._oth(cells, i)))

    def final(s, cells):                                   # == Static.feasible(cells, T0, goal)
        return s.pick(cells, s.T0) and s.place(cells, s.T0, s.goal)

    def blockers(s, cells, i, d=None):
        """Objects whose kill bits hit the base pick (d None) / place-at-d liveness; 'BASE' if the base itself is dead."""
        tab, x = ("pick", cells[i]) if d is None else ("place", d)
        base = int(s.ST.T[tab + "0"][str(x)])
        return ["BASE"] if not base else [j for j, c in enumerate(cells) if j != i and c is not None and base & int(s.ST.T[tab + "kill"][str(x)].get(str(c), 0))]


def cells_of(c0, acts, M, absent=()):
    c = list(c0)
    for k, (o, d) in enumerate(acts):
        if M >> k & 1:
            c[o] = d
    for o in absent:
        c[o] = None
    return c


def run_order(c0, acts, order, chk):
    """Sequential static check of one ordering -> status, first failing step (pick/place flags)."""
    c = list(c0)
    for t, k in enumerate(order):
        o, d = acts[k]; p, q = chk.pick(c, o), chk.place(c, o, d)
        if not (p and q):
            return {"status": "FAIL_" + ("BOTH" if not (p or q) else "PICK" if not p else "PLACE"), "step": t, "object": o, "dest": d,
                    "pick_live": p, "place_live": q}
        c[o] = d
    ok = chk.final(c)
    return {"status": "STATIC_VALID" if ok else "FAIL_FINAL_TARGET", "step": None if ok else len(order), "object": None if ok else chk.T0,
            "dest": None if ok else chk.goal, "pick_live": None, "place_live": None}


def subset_dp(c0, acts, chk):
    """Complete fixed-assignment DP: edge M -> M|k iff action k is pick+place live in cells_of(M).  BFS by layer, ascending k
    (deterministic parent = first discovery).  Every edge of every reachable node is tested; dead-end nodes give frontier reasons."""
    m = len(acts); full = (1 << m) - 1
    par, layer, tests, front = {0: None}, [0], 0, collections.Counter()
    while layer:
        nxt = []
        for M in layer:
            c, live, why = cells_of(c0, acts, M), False, []
            for k in range(m):
                if M >> k & 1:
                    continue
                o, d = acts[k]; p, q = chk.pick(c, o), chk.place(c, o, d); tests += 1
                if p and q:
                    live = True
                    if M | 1 << k not in par:
                        par[M | 1 << k] = (M, k); nxt.append(M | 1 << k)
                else:
                    why.append("BOTH_DEAD" if not (p or q) else "PICK_DEAD" if not p else "PLACE_DEAD")
            if not live and M != full:
                front.update(why)
        layer = sorted(nxt)
    order, M = None, full
    if full in par:
        order = []
        while par[M]:
            M, k = par[M]; order.append(k)
        order = order[::-1]
    fin = chk.final(cells_of(c0, acts, full))
    return {"exists": order is not None and fin, "reach_full": order is not None, "final_ok": fin, "order": order, "nodes": len(par),
            "tests": tests, "max_depth": max(bin(x).count("1") for x in par), "frontier": dict(front)}


def brute(c0, acts, chk):
    """Independent reference: first valid permutation (m <= 6 only)."""
    for perm in itertools.permutations(range(len(acts))):
        if run_order(c0, acts, perm, chk)["status"] == "STATIC_VALID":
            return list(perm)
    return None


def profile(c0, acts, chk):
    """Per action, over ALL 2^(m-1) states of the other movers: is pick ever live, place ever live, both together?  Never-executable
    actions make the assignment irreparable by permutation; 'structural' = still dead with every other mover deleted."""
    m, out = len(acts), []
    for k, (o, d) in enumerate(acts):
        oth, pk, pl, bt = [j for j in range(m) if j != k], False, False, False
        for bits in range(1 << (m - 1)):
            c = cells_of(c0, acts, sum(1 << oth[b] for b in range(m - 1) if bits >> b & 1))
            p, q = chk.pick(c, o), chk.place(c, o, d); pk, pl, bt = pk or p, pl or q, bt or (p and q)
            if bt:
                break
        if not bt:
            cs = cells_of(c0, acts, 0, absent=[acts[j][0] for j in oth])
            kind = ("PICK_NEVER_" + ("STRUCTURAL" if not chk.pick(cs, o) else "MOVERS")) if not pk else \
                   ("PLACE_NEVER_" + ("STRUCTURAL" if not chk.place(cs, o, d) else "MOVERS")) if not pl else "JOINT_NEVER"
            b = chk.blockers(cs, o, None if kind.startswith("PICK") else d) if kind.endswith("STRUCTURAL") else []
            solo = [None if j not in (o, chk.T0) else c for j, c in enumerate(c0)]    # only this object + the (never-moved) target
            live_solo = chk.pick(solo, o) if kind.startswith("PICK") else chk.place(solo, o, d)
            out.append({"k": k, "object": o, "dest": d, "kind": kind, "pick_ever": pk, "place_ever": pl, "unmoved_blockers": b,
                        "cause": None if not kind.endswith("STRUCTURAL") else ("NEEDS_EXTRA_MOVERS" if live_solo else "TARGET_OR_BASE")})
    return out


def classify(c0, acts, chk, do_brute=True):
    dp, nev = subset_dp(c0, acts, chk), profile(c0, acts, chk)
    codes = sorted({n["kind"] for n in nev}) + ([] if dp["final_ok"] else ["FINAL_TARGET_DEAD"])
    if not dp["reach_full"] and not nev:
        codes.append("ORDER_CONFLICT")                    # every move executable somewhere, but no linear extension (cycle / reversal)
    r = {"exists": dp["exists"], "dp": dp, "never_executable": nev, "reason_codes": codes or ["NONE"]}
    if do_brute and len(acts) <= 6:
        b = brute(c0, acts, chk); r["brute_force_agrees"] = (b is not None) == dp["exists"]
    return r


FAM = {"PICK_NEVER_STRUCTURAL": "PICKUP_BLOCKED_BY_UNMOVED", "PICK_NEVER_MOVERS": "PICKUP_BLOCKED_BY_MOVERS",
       "PLACE_NEVER_STRUCTURAL": "PLACEMENT_BLOCKED_BY_UNMOVED", "PLACE_NEVER_MOVERS": "PLACEMENT_BLOCKED_BY_MOVERS",
       "JOINT_NEVER": "PICK_PLACE_NEVER_JOINT", "ORDER_CONFLICT": "DEPENDENCY_CYCLE", "FINAL_TARGET_DEAD": "FINAL_TARGET"}


def failure_family(codes):
    return "+".join(sorted({FAM.get(c, "OTHER") for c in codes}))


_G = {}


def _init(tables):
    from dev_eval import Static
    _G["ST"] = Static(tables)


def _work(e):
    chk = Chk(_G["ST"], e["T0"], e["G0"]); acts = [tuple(a) for a in e["acts"]]
    r = classify(e["c0"], acts, chk)
    r["orders"] = [run_order(e["c0"], acts, [acts.index(tuple(a)) for a in s], chk) for s in e["orders"]]
    rng, sub = random.Random(e["sig"]), []                 # real-table brute-force cross-check on random sub-assignments (m<=6)
    for _ in range(3 if len(acts) > 6 else 0):
        a2 = rng.sample(acts, rng.randint(2, 6)); sub.append(subset_dp(e["c0"], a2, chk)["exists"] == (brute(e["c0"], a2, chk) is not None))
    r["sub_brute"] = sub
    return e["key"], r


def main(p4, verify, dev_public, priv_dir, tables, teacher, out, workers):
    t0, out = time.time(), Path(out)
    need = [Path(p4) / a / f for a in ARMS for f in ("predictions.jsonl", "SEAL.json")] + [Path(x) for x in (verify, dev_public)] + \
           [Path(priv_dir) / "dev_private.jsonl", Path(tables) / "MINK_TABLE_original.json", Path(tables) / "QCLEAR_original.json", Path(teacher)]
    miss = [str(p) for p in need if not p.exists()]
    if miss:
        sys.exit(f"FAIL-CLOSED missing inputs: {miss}")
    seals = {}
    for a in ARMS:                                        # sealed predictions must match both the run SEAL and the committed copy
        s = json.loads((Path(p4) / a / "SEAL.json").read_text()); h = sha(Path(p4) / a / "predictions.jsonl")
        cc = HERE / "reports" / f"SEAL_P4_{a}.json"
        assert h == s["predictions_sha256"] and (not cc.exists() or json.loads(cc.read_text())["predictions_sha256"] == h), f"seal mismatch {a}"
        seals[a] = h
    import data as DA
    from dev_eval import Static
    ST = Static(tables)
    pub = {r["root_id"]: r for r in jl(dev_public)}
    Kof = {r["root_id"]: r["K"] for r in jl(Path(priv_dir) / "dev_private.jsonl")}     # certified K: reporting strata only
    VER = collections.defaultdict(list)
    for r in jl(verify):
        VER[(r["root_id"], json.dumps(r["seq"]))].append(r)
    E = collections.defaultdict(lambda: {"src": collections.defaultdict(set), "hY": [], "C": {}})
    for a in ARMS:                                        # committed plans + full recorded candidate pools
        for p in jl(Path(p4) / a / "predictions.jsonl"):
            tr = json.loads((Path(p4) / a / "traces" / f"{p['root_id']}.json").read_text())
            items = [(p["seq"], "committed", None, None)] + [(c["seq"], "pool", c.get("hY"), c.get("C")) for c in tr["cands"]]
            for seq, role, hy, C in items:
                if not seq:
                    continue
                sig = json.dumps(sorted([int(o), int(d)] for o, d in seq)); e = E[(p["root_id"], sig)]
                e["src"][json.dumps(seq)].add(f"{a}:{role}")
                if hy is not None:
                    e["hY"].append(hy); e["C"][json.dumps(seq)] = min(C, e["C"].get(json.dumps(seq), 1e9))
    rows, jobs, excl = {}, [], collections.Counter()
    for (rid, sig), e in sorted(E.items()):
        inp = pub[rid]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; T0, G0 = int(inp["tid"]), int(inp["goal_cell"])
        acts = [tuple(a) for a in json.loads(sig)]; orders = sorted(e["src"])
        tv = [v for s in orders for v in VER.get((rid, s), [])]
        ys = {v["y"] for v in tv if v["y_status"] == "VERIFIED" or str(v["y_status"]).startswith("CERTIFIED")}
        st_end = ST.feasible(cells_of(c0, acts, (1 << len(acts)) - 1), T0, G0)
        if ys == {1}:
            ysrc, ystat = "teacher", "VERIFIED_Y1"
        elif len(ys) > 1:
            ysrc, ystat = "teacher", "INCONSISTENT"
        elif ys:
            excl["teacher_Y_negative"] += 1; continue
        elif st_end:                                       # never promoted to teacher Y; hY is recorded only as a diagnostic
            ysrc, ystat = "static_endpoint", "TEACHER_UNKNOWN" if tv else "UNVERIFIED"
        else:
            excl["not_Y_positive_by_any_evidence"] += 1; continue
        illegal = sorted({x for s in orders for x in [DA.check_sequence(pub[rid], json.loads(s))] if x})
        roles = sorted({x for s in orders for x in e["src"][s]})
        key = f"{rid}|{sig}"
        rows[key] = {"root_id": rid, "K_certified": Kof[rid], "source_arms": sorted({x.split(":")[0] for x in roles}), "source_roles": roles, "endpoint_signature": sig,
                     "m": len(acts), "Y_source": ysrc, "Y_status": ystat, "teacher_rows": len(tv), "static_endpoint_y": st_end,
                     "hY_frozen_max": max(e["hY"]) if e["hY"] else None, "illegal": illegal,
                     "teacher_X1_orders": sum(1 for v in tv if v["x"] == 1), "_orders": orders, "_C": e["C"],
                     "source_hashes": {a: seals[a][:16] for a in sorted({x.split(":")[0] for x in roles})} | {"verify": sha(verify)[:16]}}
        if not illegal and ystat != "INCONSISTENT":
            jobs.append({"key": key, "sig": sig, "c0": c0, "T0": T0, "G0": G0, "acts": [list(a) for a in acts], "orders": [json.loads(s) for s in orders]})
    with get_context("fork").Pool(workers, initializer=_init, initargs=(tables,)) as P:
        res = dict(P.imap_unordered(_work, jobs, chunksize=4))
    per = []
    for key, r in rows.items():
        orders, C = r.pop("_orders"), r.pop("_C")
        if key not in res:
            r.update(static_order_exists=None, p5a_class="INCOMPLETE_OR_INCONSISTENT", status="STATIC_UNRESOLVED",
                     reason_codes=["ILLEGAL_GRAMMAR"] if r["illegal"] else ["INCONSISTENT_TEACHER_Y"])
            per.append(r | {"evaluator_only": True}); continue
        x, dp = res[key], res[key]["dp"]; acts = [tuple(a) for a in json.loads(r["endpoint_signature"])]
        so = []
        for s_, o in zip(orders, x["orders"]):
            tv = VER.get((r["root_id"], s_), [])
            so.append({"seq": json.loads(s_), "roles": sorted(E[(r["root_id"], r["endpoint_signature"])]["src"][s_]), "energy_C": C.get(s_), **o,
                       "teacher_x": tv[0]["x"] if tv else None, "teacher_x_status": tv[0]["x_status"] if tv else None,
                       "teacher_x_phase": tv[0]["x_phase"] if tv else None})
        cm = [o for o in so if any(":committed" in z for z in o["roles"])]
        com = cm[0] if cm else min(so, key=lambda o: (o["energy_C"] is None, o["energy_C"] or 0))   # pool-only: lowest-energy recorded order
        r.update(status="STATIC_ORDER_EXISTS" if x["exists"] else "STATIC_ORDER_NONE", static_order_exists=x["exists"],
                 p5a_class=("ORDER_EXISTS_PHYSICAL_UNKNOWN" if r["teacher_X1_orders"] == 0 else "ORDER_EXISTS_PHYSICAL_VERIFIED") if x["exists"]
                 else "NO_STATIC_ORDER", committed_order_status=com["status"] if cm else "NOT_COMMITTED",
                 reference_order=("committed" if cm else "lowest_energy_pool"), reference_order_status=com["status"],
                 teacher_x_on_static_valid_orders=[o["teacher_x_status"] for o in so if o["status"] == "STATIC_VALID" and o["teacher_x_status"]],
                 static_valid_witness_order=[list(acts[k]) for k in dp["order"]] if x["exists"] else None,
                 subset_nodes_visited=dp["nodes"], static_transition_tests=dp["tests"], max_static_prefix_depth=dp["max_depth"],
                 reach_all_moves=dp["reach_full"], first_failed_pick=com["step"] if com["status"] in ("FAIL_PICK", "FAIL_BOTH") else None,
                 first_failed_place=com["step"] if com["status"] in ("FAIL_PLACE", "FAIL_BOTH") else None, frontier_reason_counts=dp["frontier"],
                 reason_codes=x["reason_codes"], failure_family=failure_family(x["reason_codes"]) if not x["exists"] else None,
                 never_executable=x["never_executable"], brute_force_agrees=x.get("brute_force_agrees"), sub_assignment_brute_agree=x["sub_brute"],
                 source_orders=so, evaluator_only=True)
        per.append(r)
    per.sort(key=lambda r: (r["Y_source"] != "teacher", r["root_id"], r["endpoint_signature"]))
    W = witness_control(ST, pub, priv_dir)
    S = summarize(per, excl, W)
    out.mkdir(parents=True, exist_ok=True)
    (out / "P5A_PER_ENDPOINT.jsonl").write_text("".join(json.dumps(r) + "\n" for r in per))
    (out / "P5A_SUMMARY.json").write_text(json.dumps(S, indent=1))
    figure(per, pub, out / "p5a_examples.png")
    head = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    prov = {"utc": time.strftime("%FT%TZ", time.gmtime()), "git_head_at_run": head, "argv": sys.argv, "host": platform.node(), "workers": workers,
            "wall_s": round(time.time() - t0, 1), "teacher_queries": 0, "training": False, "release_v2_test_opened": False,
            "inputs": {"p4_predictions_sha256": seals, "verify_sha256": sha(verify), "dev_public_sha256": sha(dev_public),
                       "dev_private_sha256": sha(Path(priv_dir) / "dev_private.jsonl"), "mink_table_sha256": sha(Path(tables) / "MINK_TABLE_original.json"),
                       "qclear_sha256": sha(Path(tables) / "QCLEAR_original.json"), "teacher_long_sha256": sha(teacher),
                       "p4_config_sha256": sha(HERE / "p4_config.json")},
            "code_sha256": {f: sha(HERE / f) for f in ("p5_order_audit.py", "dev_eval.py", "data.py", "p4_viz.py")},
            "abstraction": "MINK_STATIC_V2 construction-time grasp-screen kill tables via dev_eval.Static (pick at source, place at destination, "
                           "given all other objects' current cells); final = Static.feasible(target, goal). Object arrangement only; not robot motion."}
    (out / "P5A_PROVENANCE.json").write_text(json.dumps(prov, indent=1))
    print(json.dumps({k: S[k] for k in ("gate", "teacher_Y_positive_unique_endpoints", "teacher_Y_positive_static_order_exists")}))
    return per, S


def figure(per, pub, out):
    """Real logged DEV geometry only: one committed order-recoverable endpoint, one committed irreparable endpoint, counts by K and causes."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from p4_viz import grid, BLUE, RED, GREY, GREEN, ORANGE, INK, MUTED
    T = [r for r in per if r["Y_source"] == "teacher" and r.get("static_order_exists") is not None]
    com = [r for r in T if r["committed_order_status"] != "NOT_COMMITTED"]
    ex = [max((r for r in com if r["static_order_exists"]), key=lambda r: r["m"], default=None),
          max((r for r in com if not r["static_order_exists"]), key=lambda r: (any(n["kind"] == "PICK_NEVER_STRUCTURAL" for n in r["never_executable"]), len(r["source_arms"]), -r["m"]), default=None)]
    fig, axs = plt.subplots(1, 4, figsize=(21, 5.2))
    for ax, r in zip(axs[:2], ex):
        if r is None:
            ax.axis("off"); continue
        inp = pub[r["root_id"]]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; T0, G0 = int(inp["tid"]), int(inp["goal_cell"])
        o = next(o for o in r["source_orders"] if any(":committed" in z for z in o["roles"]))
        plans = [(o["seq"], RED, -0.12)] + ([(r["static_valid_witness_order"], BLUE, 0.12)] if r["static_order_exists"] else [])
        grid(ax, c0, T0, G0, plans, [])
        if o["object"] is not None:
            ax.scatter(c0[o["object"]] % 8, c0[o["object"]] // 8, s=420, facecolors="none", edgecolors=INK, lw=1.4, zorder=5)
        for n in r["never_executable"]:
            ax.scatter(c0[n["object"]] % 8, c0[n["object"]] // 8, s=330, marker="s", facecolors="none", edgecolors=ORANGE, lw=1.6, zorder=5)
            for b in n["unmoved_blockers"]:
                if b != "BASE":
                    ax.scatter(c0[b] % 8, c0[b] // 8, s=40, marker="x", color=INK, lw=0.8, zorder=6)
        ax.set_title(f"{r['root_id']}  K={r['K_certified']}  m={r['m']}  {'/'.join(r['source_arms'])} committed, teacher Y=1\n"
                     f"red = committed order: {o['status']} at step {None if o['step'] is None else o['step'] + 1} (black ring)\n"
                     + ("blue = DP static order (valid; physical X unknown)" if r["static_order_exists"] else
                        "orange square = never-executable mover; x = never-moved blockers"), fontsize=7.5, loc="left")
    Ks = sorted({r["K_certified"] for r in T}); ax = axs[2]
    yes = [sum(r["K_certified"] == k and r["static_order_exists"] for r in T) for k in Ks]; no = [sum(r["K_certified"] == k and not r["static_order_exists"] for r in T) for k in Ks]
    ax.bar(range(len(Ks)), yes, width=0.6, color=BLUE, label="static order exists"); ax.bar(range(len(Ks)), no, bottom=yes, width=0.6, color=GREY, label="no static order")
    for i, (a, b) in enumerate(zip(yes, no)):
        ax.text(i, a + b + 0.4, f"{a}/{a + b}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(len(Ks))); ax.set_xticklabels([f"K={k}" for k in Ks]); ax.set_ylabel("unique teacher-Y=1 endpoints")
    ax.legend(frameon=False, fontsize=8); ax.set_title("same-endpoint static reorderability by certified K", fontsize=8.5, loc="left")
    ax = axs[3]; c = collections.Counter(FAM[n["kind"]] + (" (" + n["cause"].lower().replace("_", " ") + ")" if n["cause"] else "") for r in T for n in r["never_executable"])
    c.update(FAM["ORDER_CONFLICT"] for r in T if "ORDER_CONFLICT" in r["reason_codes"])
    ks = sorted(c, key=c.get); ax.barh(range(len(ks)), [c[k] for k in ks], height=0.6, color=ORANGE)
    ax.set_yticks(range(len(ks))); ax.set_yticklabels([k.lower().replace("_", " ") for k in ks], fontsize=7.5)
    for i, k in enumerate(ks):
        ax.text(c[k] + 0.5, i, str(c[k]), va="center", fontsize=8, color=INK)
    ax.set_xlabel("never-executable actions (cycles: endpoints)", color=MUTED); ax.set_title(f"why {sum(1 for r in T if not r['static_order_exists'])} endpoints are irreparable by permutation", fontsize=8.5, loc="left")
    for a in axs[2:]:
        for s_ in ("top", "right"):
            a.spines[s_].set_visible(False)
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)


def witness_control(ST, pub, priv_dir):
    """Private certified DEV witnesses (CERTIFIED_MIN_K, teacher x=1/y=1 at construction): booleans only, sequences never written."""
    n = ok_order = ok_dp = brute_ok = 0; bad = []
    for pv in jl(Path(priv_dir) / "dev_private.jsonl"):
        inp = pub[pv["root_id"]]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; chk = Chk(ST, int(inp["tid"]), int(inp["goal_cell"]))
        acts = [(inp["ids"].index(o), int(d)) for o, d in pv["witness"]]
        v = run_order(c0, acts, list(range(len(acts))), chk)["status"] == "STATIC_VALID"; dp = subset_dp(c0, acts, chk)["exists"]
        n += 1; ok_order += v; ok_dp += dp
        brute_ok += (len(acts) > 6) or ((brute(c0, acts, chk) is not None) == dp)
        if not (v and dp):
            bad.append(pv["root_id"])
    return {"n": n, "witness_order_static_valid": ok_order, "witness_assignment_dp_exists": ok_dp, "brute_agree_or_m_gt_6": brute_ok, "failing_roots": bad,
            "teacher_replay_basis": "witness = teacher try with x=1 (and y=1 where final) from CERTIFIED_MIN_K construction records (dev_build.py); "
                                    "no new teacher query in P5A"}


def summarize(per, excl, W):
    T = [r for r in per if r["Y_source"] == "teacher"]; Sx = [r for r in per if r["Y_source"] == "static_endpoint"]

    def block(R):
        ok = [r for r in R if r.get("static_order_exists")]; no = [r for r in R if r.get("static_order_exists") is False]
        fam = collections.Counter(r["failure_family"] for r in no)
        nev = collections.Counter(n["kind"] for r in no for n in r["never_executable"])
        fr = collections.Counter()
        for r in no:
            fr.update(r["frontier_reason_counts"])
        unm = [n for r in no for n in r["never_executable"] if n["kind"].endswith("STRUCTURAL")]
        return {"unique_endpoints": len(R), "roots": len({r["root_id"] for r in R}), "static_order_exists": len(ok), "roots_with_static_order": len({r["root_id"] for r in ok}),
                "static_order_none": len(no), "unresolved": len(R) - len(ok) - len(no), "failure_family": dict(fam), "never_executable_action_kinds": dict(nev),
                "frontier_reasons_none": dict(fr), "unmoved_blocked_actions": len(unm),
                "unmoved_blocked_actions_by_cause": dict(collections.Counter(n["kind"] + ":" + n["cause"] for n in unm)),
                "endpoints_any_never_executable_action": sum(1 for r in no if r["never_executable"]),
                "endpoints_all_never_executable_are_pickup_by_unmoved": sum(1 for r in no if r["never_executable"] and all(n["kind"] == "PICK_NEVER_STRUCTURAL" for n in r["never_executable"])),
                "by_K": {str(k): {"endpoints": sum(r["K_certified"] == k for r in R), "static_order_exists": sum(r["K_certified"] == k for r in ok),
                                  "roots": len({r["root_id"] for r in R if r["K_certified"] == k}), "roots_with_static_order": len({r["root_id"] for r in ok if r["K_certified"] == k})}
                         for k in sorted({r["K_certified"] for r in R})}, "committed_order_status": dict(collections.Counter(r.get("committed_order_status") for r in R)),
                "reference_order_status": dict(collections.Counter(r.get("reference_order_status") for r in R)),
                "teacher_x_on_static_valid_orders": dict(collections.Counter(x for r in R for x in r.get("teacher_x_on_static_valid_orders") or [])),
                "by_m": dict(collections.Counter(r["m"] for r in R)),
                "reach_all_moves_but_final_dead": sum(1 for r in no if r["reach_all_moves"] and "FINAL_TARGET_DEAD" in r["reason_codes"]),
                "static_endpoint_false": sum(1 for r in R if not r["static_endpoint_y"]),
                "brute_force_checked": sum(1 for r in R if r.get("brute_force_agrees") is not None),
                "brute_force_agree": sum(1 for r in R if r.get("brute_force_agrees")),
                "sub_assignment_brute_checks": sum(len(r.get("sub_assignment_brute_agree") or []) for r in R),
                "sub_assignment_brute_agree": sum(sum(r.get("sub_assignment_brute_agree") or []) for r in R)}
    bt, bs = block(T), block(Sx)
    bt["committed"] = block([r for r in T if r["committed_order_status"] != "NOT_COMMITTED"])
    bt["pool_only"] = block([r for r in T if r["committed_order_status"] == "NOT_COMMITTED"])
    for b in (bt["committed"], bt["pool_only"]):
        b.pop("by_K"); b.pop("frontier_reasons_none")
    multi = [r for r in per if r.get("source_orders") and len(r["source_orders"]) > 1]
    rank = {"endpoints_with_multiple_pool_orders": len(multi), "of_which_any_pool_order_static_valid": sum(1 for r in multi if any(o["status"] == "STATIC_VALID" for o in r["source_orders"])),
            "of_which_lowest_energy_order_static_valid": sum(1 for r in multi if min((o for o in r["source_orders"] if o["energy_C"] is not None),
                                                                                     key=lambda o: o["energy_C"], default={"status": None})["status"] == "STATIC_VALID")}
    ph = collections.Counter()                            # static first-failure step vs teacher X failure phase on already-tested orders
    for r in per:
        for o in r.get("source_orders") or []:
            if o["teacher_x_status"] is None:
                continue
            tp = o["teacher_x_phase"] or ""; ti = int(tp.split(":")[1]) if tp.startswith("relocation:") else None
            ss = o["step"] if o["status"] != "STATIC_VALID" else None
            ph["teacher_X1" if o["teacher_x"] == 1 else "static_valid_teacher_fail" if ss is None else
               "teacher_non_relocation_phase" if ti is None else "same_step" if ti == ss else
               "teacher_earlier" if ti < ss else "TEACHER_PASSED_STATIC_DEAD_STEP"] += 1
    T_no = [r for r in T if r.get("static_order_exists") is False]
    repair = {"teacher_none_endpoints": len(T_no), "m_eq_12_cap": sum(r["m"] == 12 for r in T_no),
              "any_pickup_blocked_by_unmoved (needs object-set expansion)": sum(any(n["kind"] == "PICK_NEVER_STRUCTURAL" for n in r["never_executable"]) for r in T_no),
              "only_destination_type_causes (destination repair could suffice)": sum(bool(r["never_executable"] or "ORDER_CONFLICT" in r["reason_codes"]) and
                                                                                     not any(n["kind"] == "PICK_NEVER_STRUCTURAL" for n in r["never_executable"]) for r in T_no)}
    wit_ok = W["n"] > 0 and W["witness_order_static_valid"] == W["n"] == W["witness_assignment_dp_exists"]
    brute_ok = all(b["brute_force_checked"] == b["brute_force_agree"] and b["sub_assignment_brute_checks"] == b["sub_assignment_brute_agree"] for b in (bt, bs))
    if not wit_ok or not brute_ok or ph["TEACHER_PASSED_STATIC_DEAD_STEP"] or bt["unique_endpoints"] == 0 or bt["unresolved"]:
        gate = "A-INCONCLUSIVE"
    else:
        gate = "A-ORDER-RECOVERABLE" if bt["static_order_exists"] else "A-DESTINATION-BLOCKED"
    return {"stage": "P5A", "evaluator_only": True, "gate": gate, "teacher_Y_positive_unique_endpoints": bt["unique_endpoints"],
            "teacher_Y_positive_static_order_exists": bt["static_order_exists"], "teacher_Y_positive": bt, "static_endpoint_positive_unverified": bs,
            "excluded_endpoints": dict(excl), "witness_control": W, "brute_force_ok": brute_ok, "ranking_diagnostic": rank,
            "static_vs_teacher_X_phase": dict(ph), "repair_type_teacher_none": repair,
            "scope": "static object-arrangement abstraction only (MINK_STATIC_V2); an existing static order is NOT a robot-motion proof; "
                     "a missing static order is a statement under this abstraction, not a physical impossibility certificate"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for k in ("p4", "verify", "dev_public", "priv_dir", "tables", "teacher", "out"):
        ap.add_argument(k)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(); main(a.p4, a.verify, a.dev_public, a.priv_dir, a.tables, a.teacher, a.out, a.workers)
