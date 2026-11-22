#!/usr/bin/env python3
"""P5B — EVALUATOR ONLY.  Bounded physical validation of P5A static order recovery (same object->destination moves, new order).
  schedule  outcome-blind, frozen BEFORE any P5B teacher call: <=2 endpoints per root from the 13 P5A A-ORDER-RECOVERABLE endpoints,
            static-valid orders (P5A DP order, then deterministic different-first-mover alternatives), matched original-order controls;
            exact-query dedup against existing P4 teacher rows (reused, no call).  Writes P5B_SCHEDULE.json + its sha256.
  run       pinned long teacher (teacher_long.x_query, unchanged budgets, fixed order, carried q, terminal connector to q_ref, replay);
            hard caps: <=32 teacher calls (X and Y each count), <=2 workers, <=1800 s batch wall; append-only ledger; --dry-run.
            Y is reused only when the Y2 key (root|context|sorted endpoint) and the teacher version match the P4 VERIFIED row.
            Predeclared confirmation reserve (4 calls): for the first two X-positive endpoints, one fresh-process X repeat + one fresh Y.
    python p5b_physical.py schedule P5A_PER_ENDPOINT.jsonl VERIFY.jsonl DEV_PUBLIC TABLES OUT_SCHEDULE.json
    ABF_ROOT=... python p5b_physical.py run SCHEDULE.json SCALING_CODE DEV_PRIVATE RUN_DIR [--dry-run]"""
import hashlib, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CAPS = {"teacher_calls": 32, "workers": 2, "wall_s": 1800, "confirm_reserve": 4, "per_root_endpoints": 2}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jl(p):
    return [json.loads(l) for l in open(p)]


# ----------------------------------------------------------------------------------------------------------------------------- schedule
def good_masks(c0, acts, chk):
    """good[M] = some completion from completed-set M reaches the full set with the final target live (backward DP)."""
    from p5_order_audit import cells_of
    m = len(acts); full = (1 << m) - 1; good = {full: chk.final(cells_of(c0, acts, full))}
    for M in sorted(range(full), key=lambda x: -bin(x).count("1")):
        c = cells_of(c0, acts, M)
        good[M] = any(not M >> k & 1 and good[M | 1 << k] and chk.pick(c, acts[k][0]) and chk.place(c, acts[k][0], acts[k][1]) for k in range(m))
    return good


def order_first(c0, acts, chk, good, first):
    """Static-valid order starting with `first`, completed by the smallest live index that keeps a completion (deterministic)."""
    from p5_order_audit import cells_of
    m, M, order = len(acts), 0, []
    while M != (1 << m) - 1:
        c = cells_of(c0, acts, M)
        cand = [k for k in range(m) if not M >> k & 1 and good[M | 1 << k] and chk.pick(c, acts[k][0]) and chk.place(c, acts[k][0], acts[k][1])]
        k = first if not order and first in cand else cand[0]
        order.append(k); M |= 1 << k
    return order


def schedule(p5a, verify, dev_public, tables, out):
    from dev_eval import Static
    from p5_order_audit import Chk, run_order
    import data as DA
    ST = Static(tables); pub = {r["root_id"]: r for r in jl(dev_public)}
    tested = {(r["root_id"], json.dumps(r["seq"])) for r in jl(verify)}
    ver = jl(verify)
    E = [r for r in jl(p5a) if r["Y_source"] == "teacher" and r["static_order_exists"]]
    assert len(E) == 13 and len({r["root_id"] for r in E}) == 6 and max(r["K_certified"] for r in E) <= 6, "P5A scope mismatch"
    sel = []
    for rid in sorted({r["root_id"] for r in E}):            # rule S1: per root, committed-origin first (smallest m, then signature);
        R = sorted((r for r in E if r["root_id"] == rid), key=lambda r: (r["committed_order_status"] == "NOT_COMMITTED", r["m"], r["endpoint_signature"]))
        first = R[0]; rest = R[1:]                           # rule S2: second = opposite origin if any, else next; smallest m, signature
        rest.sort(key=lambda r: ((r["committed_order_status"] == "NOT_COMMITTED") == (first["committed_order_status"] == "NOT_COMMITTED"), r["m"], r["endpoint_signature"]))
        sel += [(first, 0)] + ([(rest[0], 1)] if rest else [])
    Q, seen, eps = [], set(), []
    for tier_name, pick in (("T1_DP_ORDER_FIRST_ENDPOINT", lambda j, rank: rank == 0), ("T2_DP_ORDER_SECOND_ENDPOINT", lambda j, rank: rank == 1),
                            ("T3_ALT_FIRST_MOVER_A", None), ("T4_ALT_FIRST_MOVER_B", None), ("T5_ORIGINAL_ORDER_CONTROL", None)):
        for r, rank in sel:
            if pick is not None and not pick(None, rank):
                continue
            inp = pub[r["root_id"]]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; chk = Chk(ST, int(inp["tid"]), int(inp["goal_cell"]))
            acts = [tuple(a) for a in json.loads(r["endpoint_signature"])]; dp = [tuple(a) for a in r["static_valid_witness_order"]]
            if tier_name.startswith("T1") or tier_name.startswith("T2"):
                seqs = [dp]
            elif tier_name.startswith("T5"):
                ref = next((o for o in r["source_orders"] if any(":committed" in z for z in o["roles"])), None) or \
                    min(r["source_orders"], key=lambda o: (o["energy_C"] is None, o["energy_C"] or 0))
                seqs = [[tuple(a) for a in ref["seq"]]]
            else:
                good = good_masks(c0, acts, chk); c = [int(x) for x in c0]
                firsts = [k for k in range(len(acts)) if good[1 << k] and chk.pick(c, acts[k][0]) and chk.place(c, acts[k][0], acts[k][1])]
                used = [acts.index(dp[0])]
                for q in Q:
                    if q["endpoint_signature"] == r["endpoint_signature"] and q["root_id"] == r["root_id"] and q["tier"].startswith("T3"):
                        used.append(acts.index(tuple(q["seq"][0])))
                alt = [k for k in firsts if k not in used]
                if not alt:
                    eps.append({"root_id": r["root_id"], "sig": r["endpoint_signature"], "tier": tier_name, "skipped": "NO_ALTERNATIVE_FIRST_MOVER"}); continue
                seqs = [[acts[k] for k in order_first(c0, acts, chk, good, alt[0])]]
            for s in seqs:
                key = (r["root_id"], json.dumps([list(a) for a in s]))
                if key in seen:
                    continue
                seen.add(key)
                st = run_order(c0, acts, [acts.index(a) for a in s], chk)["status"]
                assert sorted(s) == sorted(acts) and DA.check_sequence(pub[r["root_id"]], [list(a) for a in s]) is None
                assert st == "STATIC_VALID" or tier_name.startswith("T5")
                yrow = next(v for v in ver if v["root_id"] == r["root_id"] and v["y"] == 1 and v["y_status"] == "VERIFIED"
                            and sorted(map(tuple, v["seq"])) == sorted(acts))
                Q.append({"qid": f"q{len(Q):02d}", "tier": tier_name, "root_id": r["root_id"], "K_certified": r["K_certified"], "endpoint_signature": r["endpoint_signature"],
                          "m": r["m"], "endpoint_origin": "committed" if r["committed_order_status"] != "NOT_COMMITTED" else "pool_only",
                          "source_arms": r["source_arms"], "seq": [list(a) for a in s], "static_status": st,
                          "reuse_existing_X": key in tested, "y_reuse_seq": yrow["seq"], "y_reuse_teacher": yrow["y_teacher"]})
    calls_main = sum(1 for q in Q if not q["reuse_existing_X"])
    budget_main = CAPS["teacher_calls"] - CAPS["confirm_reserve"]
    S = {"stage": "P5B", "frozen_utc": time.strftime("%FT%TZ", time.gmtime()), "caps": CAPS, "p5a_per_endpoint_sha256": sha(p5a), "verify_sha256": sha(verify),
         "selection_rules": ["S1 per root (6 roots): first endpoint = committed-origin if any, smallest m, then signature",
                             "S2 second endpoint = opposite origin if available, smallest m, then signature (max 2 per root)",
                             "T1/T2: P5A deterministic DP static order of first/second endpoints (root coverage first)",
                             "T3/T4: static-valid orders with the smallest different feasible first mover (good-mask completion, smallest index)",
                             "T5: matched original order (committed, else lowest-energy pool order) - descriptive control only",
                             "exact (root, ordered seq) already teacher-tested in P4 verify.jsonl -> reused, no call",
                             f"execution strictly in queue order until {budget_main} main calls; no adaptive selection by outcome",
                             "confirmation reserve 4 calls: for the first 2 X-VERIFIED endpoints (queue order), a fresh-process X repeat and a fresh Y; "
                             "inserted at queue front when triggered; never used for new candidates",
                             "stop: call cap, 1800 s batch wall (running jobs terminated -> ABORTED_CAP = UNKNOWN), or any hash/scope mismatch"],
         "selected_endpoints": [{"root_id": r["root_id"], "endpoint_signature": r["endpoint_signature"], "m": r["m"], "rank": k,
                                 "origin": "committed" if r["committed_order_status"] != "NOT_COMMITTED" else "pool_only"} for r, k in sel],
         "skipped": eps, "queue": Q, "main_calls_needed": calls_main, "main_call_budget": budget_main,
         "queue_truncated_to_budget": [q["qid"] for q in Q if not q["reuse_existing_X"]][budget_main:]}
    Path(out).write_text(json.dumps(S, indent=1))
    Path(str(out) + ".sha256").write_text(sha(out) + "\n")
    print(json.dumps({"endpoints": len(sel), "queries": len(Q), "new_calls": calls_main, "reused": len(Q) - calls_main, "sha": sha(out)[:16]}))


# ----------------------------------------------------------------------------------------------------------------------------------- run
_W = {}


def _teacher_path(code):
    """Teacher modules must never resolve to this folder (it has its own planner.py / data.py / models.py): drop it from sys.path and
    evict any already-imported shadowing modules before booting the frozen teacher.  (P5B batch-1 harness defect, see report.)"""
    sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != HERE]
    for m in ("planner", "data", "models", "geometry", "motion"):
        f = getattr(sys.modules.get(m), "__file__", None) or ""
        if f and Path(f).resolve().parent == HERE:
            del sys.modules[m]
    sys.path.insert(0, code)


def _boot(code):
    _teacher_path(code)
    import mink as MK
    MK.boot("original")
    import teacher_long as TL
    _W.update(MK=MK, TL=TL, E=MK._M["E"])


def tjob(a):
    """One teacher call in a worker: kind X (fixed order) or Y (endpoint), witnesses under out_dir."""
    code, priv, kind, qid, rid, seq, outd = a
    if not _W:
        _boot(code)
    rec = json.loads((Path(priv) / "dev_records" / f"{rid}.json").read_text())
    names = [o["id"] for o in rec["scene"]["objects"]]; s = [(names[i], int(d)) for i, d in seq]
    t0 = time.time(); Path(outd).mkdir(parents=True, exist_ok=True)
    row = (_W["TL"].x_query if kind == "X" else _W["TL"].y_query)(_W["E"], rid, rec, s, {}, out=outd)
    keep = ("teacher", "teacher_status", "negative_kind", "failed_phase", "y", "detail", "independent_replay", "replay_why", "connector_how", "budget_spent",
            "budget", "process_cpu_s", "virtual_cpu_s", "witness_relocations", "witness_connector", "final_q_before_connector", "final_q_after_connector", "y_key", "x_key")
    r = {k: row.get(k) for k in keep}
    r["steps"] = [{k: st.get(k) for k in ("object", "dest", "via", "J_record", "witness")} for st in row.get("steps") or []]
    return {"qid": qid, "kind": kind, "root_id": rid, "seq": seq, "wall_s": round(time.time() - t0, 2), "pid": os.getpid(), **r}


def ykeys(code, priv, q):
    """Order-invariance check (pure function, no teacher call): Y2 key of the scheduled order == key of the P4 VERIFIED Y row."""
    _teacher_path(code)
    import mink as MK
    MK.boot("original")
    import bxy_teacher as BT
    rec = json.loads((Path(priv) / "dev_records" / f"{q['root_id']}.json").read_text()); names = [o["id"] for o in rec["scene"]["objects"]]
    f = lambda s: BT.ykey(q["root_id"], rec, [(names[i], int(d)) for i, d in s])  # noqa: E731
    return f(q["seq"]), f(q["y_reuse_seq"])


def run(sched_f, code, priv, rundir, dry=False, job=None, yk=None, ctx_name="spawn"):
    """job / yk / ctx_name are injection points for the mock tests only (real runs: pinned teacher, spawn workers)."""
    from multiprocessing import get_context
    S = json.loads(Path(sched_f).read_text())
    assert Path(str(sched_f) + ".sha256").read_text().strip() == sha(sched_f), "schedule hash mismatch"
    job, yk = job or tjob, yk or ykeys
    pins = {"teacher_long": sha(Path(code) / "teacher_long.py")[:16] if job is tjob else "MOCK"}
    assert job is not tjob or pins["teacher_long"] == "af0e9fd4ac94e13d", "teacher_long hash mismatch"
    rd = Path(rundir); rd.mkdir(parents=True, exist_ok=True); L = rd / "ledger.jsonl"
    led = jl(L) if L.exists() else []
    done = {(x["qid"], x["kind"]) for x in led if x["event"] == "RESULT"}
    calls = sum(1 for x in led if x["event"] == "LAUNCH")
    main = [q for q in S["queue"] if not q["reuse_existing_X"]][:S["main_call_budget"]]
    for q in S["queue"]:                                       # Y reuse precondition (no teacher call)
        a, b = yk(code, priv, q)
        q["y_key_match"] = a == b and (q["m"] > 6) == (q["y_reuse_teacher"] == "BXY_Y_TEACHER_V2_LONG")
        assert q["y_key_match"], f"Y reuse precondition failed {q['qid']}"
    print(json.dumps({"dry_run": dry, "schedule_sha": sha(sched_f)[:16], "pins": pins, "caps": S["caps"], "main_jobs": len(main),
                      "reused_X": sum(q["reuse_existing_X"] for q in S["queue"]), "already_done": len(done), "calls_so_far": calls,
                      "y_reuse_all_match": all(q["y_key_match"] for q in S["queue"])}))
    if dry:
        return
    say = lambda **k: open(L, "a").write(json.dumps({"utc": time.strftime("%FT%TZ", time.gmtime()), **k}) + "\n")  # noqa: E731
    say(event="BATCH_START", schedule_sha=sha(sched_f), pins=pins, caps=S["caps"])
    pending = [("X", q) for q in main if (q["qid"], "X") not in done]
    conf_used = sum(1 for x in led if x["event"] == "LAUNCH" and x.get("confirm"))
    conf_eps = {x["sig"] for x in led if x["event"] == "LAUNCH" and x.get("confirm")}
    ts = lambda x: time.mktime(time.strptime(x["utc"], "%Y-%m-%dT%H:%M:%SZ"))  # noqa: E731
    prior, b0 = 0.0, None                                     # wall cap is cumulative across resumed batches (crash-safe)
    for x in led:
        b0 = ts(x) if x["event"] == "BATCH_START" else b0
        if b0 is not None and x["event"] != "BATCH_START" and (x is led[-1] or led[led.index(x) + 1]["event"] == "BATCH_START"):
            prior += ts(x) - b0; b0 = None
    t0, run_ = time.time() - prior, {}
    ctx = get_context(ctx_name); P = ctx.Pool(S["caps"]["workers"], maxtasksperchild=None)
    try:
        while pending or run_:
            for k, (ar, q, kind, conf) in list(run_.items()):
                if ar.ready():
                    run_.pop(k)
                    try:
                        r = ar.get()
                    except Exception as e:                    # noqa: BLE001
                        r = {"qid": q["qid"], "kind": kind, "teacher_status": "WORKER_ERROR", "detail": repr(e)[:300]}
                    say(event="RESULT", confirm=conf, **r)
                    if kind == "X" and not conf and r.get("y") == 1 and len(conf_eps) < 2 and q["endpoint_signature"] not in conf_eps \
                            and conf_used + 2 <= S["caps"]["confirm_reserve"]:
                        conf_eps.add(q["endpoint_signature"]); conf_used += 2
                        pending[:0] = [("XC", q), ("YC", q)]
            if time.time() - t0 > S["caps"]["wall_s"]:
                say(event="WALL_CAP", running=[(q["qid"], kind) for _, q, kind, _ in run_.values()], pending=[(q["qid"], k) for k, q in pending])
                break
            while pending and len(run_) < S["caps"]["workers"] and calls < S["caps"]["teacher_calls"]:
                kind, q = pending.pop(0); conf = kind in ("XC", "YC")
                say(event="LAUNCH", qid=q["qid"], kind=kind, call_no=calls + 1, confirm=conf, sig=q["endpoint_signature"] if conf else None)
                calls += 1
                ar = P.apply_async(job, ((code, priv, kind[0], q["qid"] + ("c" if conf else ""), q["root_id"], q["seq"], str(rd / "witnesses" / (q["qid"] + kind)),),))
                run_[q["qid"] + kind] = (ar, q, kind, conf)
            if not run_ and pending and calls >= S["caps"]["teacher_calls"]:
                say(event="CALL_CAP", pending=[(q["qid"], k) for k, q in pending]); break
            time.sleep(1)
    finally:
        P.terminate(); P.join()
        for _, q, kind, conf in run_.values():
            say(event="RESULT", qid=q["qid"], kind=kind[0], confirm=conf, teacher_status="ABORTED_CAP", y=None)
        say(event="BATCH_END", wall_s=round(time.time() - t0, 1), calls=calls)
    print(json.dumps({"calls": calls, "wall_s": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    if sys.argv[1] == "schedule":
        schedule(*sys.argv[2:7])
    elif sys.argv[1] == "run":
        run(*sys.argv[2:6], dry="--dry-run" in sys.argv)
