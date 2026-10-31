"""BXY-P-MIN-COLLECT evidence: immutable BXY_SIDECAR_V2_PMIN (reused P9 observations + collected rows), independent re-verification of
every stored witness, matched pairs, and the evidence summary. Reads results only; never calls the teacher planner.
  verification  every observed row: key re-derived from the root record, F1-admissible, frozen-design member; every positive: X relocations +
                connector re-certified from the stored files (bxy_teacher.replay_x), Y target re-certified from q_ref (replay_y); a positive that
                fails is demoted to unobserved (WITNESS_VERIFICATION_FAILED), never relabelled 0; every negative: a recorded failed phase / kind
  pairs         bxy_teacher.pair over each X and its shared Y node (J_total over the stitched relocations + connector + target)
    python3 bxy_pmin_sidecar.py build | summary"""
from __future__ import annotations

import collections
import json
import os
import shutil
import time
from pathlib import Path

import numpy as np

import bxy_data as bd
import bxy_f1 as F1
import bxy_pmin as PM
import bxy_pmin_collect as C
import bxy_teacher as T

OUT = C.OUT
P9_OUT = Path("runs/approach_b/bxy_teacher_pilot_v1")
SIDECAR = "BXY_SIDECAR_V2_PMIN"
NEG_KINDS = {"CERTIFIED", "NO_PLAN_FOUND", "TIMEOUT", "OTHER_FAILURE"}


def p9_reused(D) -> tuple:
    """(x rows, y rows) of P9 observations that the frozen design reuses in the phase; their witnesses are copied (content-addressed)."""
    sc = json.loads(PM.PILOT.read_text())
    keys = {key for k in D["root_order"] for key, q in D["roots"][k]["queries"].items() if q["reuse_p9"] and C.PHASE in q["phases"]}
    xs = [r | {"source": "P9_PILOT", "side": "x", "design_key": r["x_key"]} for r in sc["x_queries"] if r.get("x_key") in keys]
    ys = [r | {"source": "P9_PILOT", "side": "y", "design_key": r["y_key"]} for r in sc["y_queries"] if r.get("y_key") in keys]
    for r in xs + ys:
        for w in (r.get("witness_relocations") or []) + [r.get("witness_connector"), r.get("target_witness")]:
            if w:
                dst = OUT / "witnesses" / w[:2] / f"{w}.npz"
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    tmp = dst.with_suffix(f".{os.getpid()}.tmp.npz")
                    shutil.copyfile(P9_OUT / "witnesses" / w[:2] / f"{w}.npz", tmp)
                    os.replace(tmp, dst)                       # atomic, like bd_core.Store.witness
    return xs, ys


def verify(E, R, D, r) -> dict:
    """Independent checks of one row (see module doc). Returns the row with a 'verification' block (and demotion if a witness fails)."""
    k, side = r["root"], r["side"]
    v = {"identity": None, "f1": None, "member": None, "witness": None, "negative": None}
    if not (r.get("observed") and r.get("y") in (0, 1)):
        return r | {"verification": v}
    rec = R[k]
    if side == "x":
        seq = [tuple(a) for a in r["ordered_actions"]]
        v["identity"] = r["x_key"] == T.xkey(k, rec, seq) == r["design_key"] and r["parent_y_key"] == T.ykey(k, rec, seq)
        v["f1"] = F1.screen(rec, seq)["x_ok"]
    else:
        seq = sorted(r["hypothetical_poses"].items())
        v["identity"] = r["y_key"] == T.ykey(k, rec, edit=r["hypothetical_poses"]) == r["design_key"] and r["q_ref_hash"] == T.context(k, rec)
        v["f1"] = F1.endpoint(rec, r["hypothetical_poses"])["y_ok"]
    q = D["roots"][k]["queries"].get(r["design_key"])
    v["member"] = bool(q) and C.PHASE in q["phases"]
    if r["y"] == 1:
        try:
            if side == "x":
                ok = T.replay_x(E, rec, seq, [T.load_w(OUT, w) for w in r["witness_relocations"]], T.load_w(OUT, r["witness_connector"]))
            else:
                ok = T.replay_y(E, rec, seq, T.load_w(OUT, r["target_witness"]))
            v["witness"] = ok["ok"]
        except (OSError, ValueError, KeyError) as e:
            v["witness"] = False
            v["witness_error"] = str(e)
    else:
        v["negative"] = r.get("negative_kind") in NEG_KINDS and bool(r.get("failed_phase"))
    if not all(x is not False for x in v.values()):
        return r | {"verification": v, "observed": False, "y": None, "teacher_status": "WITNESS_VERIFICATION_FAILED" if v["witness"] is False
                    else "VERIFICATION_FAILED", "original_y": r["y"]}
    return r | {"verification": v}


def build(write=True) -> dict:
    t0, c0 = time.time(), time.process_time()
    D, R, E = C.design(), bd.roots(), T.env()
    lock = PM.assert_frozen(check_git=write)
    auth = json.loads(C.auth_path(OUT).read_text())
    new = C.rows(OUT, D)
    px, py = p9_reused(D)
    X = [verify(E, R, D, r | {"source": r.get("source", "PMIN_COLLECT")}) for (k, i, s), r in sorted(new.items()) if s == "x"] + [verify(E, R, D, r) for r in px]
    Y = [verify(E, R, D, r | {"source": r.get("source", "PMIN_COLLECT")}) for (k, i, s), r in sorted(new.items()) if s == "y"] + [verify(E, R, D, r) for r in py]
    keys = collections.Counter(r["design_key"] for r in X + Y)
    if max(keys.values()) > 1:
        raise ValueError(f"duplicate query rows: {[k for k, n in keys.items() if n > 1][:5]}")
    ybk = {r["design_key"]: r for r in Y}
    P = []
    for x in X:
        y = ybk.get(x.get("parent_y_key") or D["roots"][x["root"]]["queries"].get(x["design_key"], {}).get("parent_y_key"))
        if x.get("observed") and y is not None and y.get("observed"):
            P.append(T.pair(E, x, y, OUT) | {"root": x["root"], "x_classes": x.get("classes"), "y_classes": y.get("classes")})
    led = C.ledger(OUT)
    fin = [e for e in led if e["event"] == "finish"]
    man = {"design_sha256": lock["design_sha256"], "lock_sha256": PM.sha_file(OUT / "PMIN_LOCK.json"), "authorization_sha256": PM.sha_file(C.auth_path(OUT)),
           "authorization": {k: auth[k] for k in ("limits", "per_query_budget", "runner_sha256", "executing_commit")}, "runner_version": C.VERSION,
           "teacher_hash": sorted({r["teacher_hash"] for r in X + Y if r.get("teacher_hash")}), "data_sha256": D["data_sha256"], "phase": C.PHASE,
           "p9_sidecar_sha256": PM.sha_file(PM.PILOT), "source_commit": PM.git("rev-parse", "HEAD"),
           "robot_profile_hash": sorted({R[k]["scene"]["robot_profile_hash"] for k in D["root_order"]}),
           "collection": {"aggregate_worker_cpu_s": round(sum(e["cpu_s"] for e in fin), 2), "roots_finished": len({e["root"] for e in fin}),
                          "exits": dict(collections.Counter(str(e["exit"]) for e in fin)), "ledger": led,
                          "state": json.loads((OUT / "COLLECT_STATE.json").read_text()) if (OUT / "COLLECT_STATE.json").exists() else None},
           "verification_cpu_s": None, "verification_wall_s": None}
    if len(man["teacher_hash"]) != 1:
        raise ValueError(f"mixed teacher hashes {man['teacher_hash']}")
    man["verification_cpu_s"], man["verification_wall_s"] = round(time.process_time() - c0, 1), round(time.time() - t0, 1)
    sc = {"version": SIDECAR, "manifest": man, "x_queries": X, "y_queries": Y, "paired": P}
    if not write:
        return sc
    f = OUT / f"{SIDECAR}.json"
    body = json.dumps(sc, indent=1, sort_keys=True, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    if f.exists():
        old = json.loads(f.read_text())
        strip = lambda s: {**s, "manifest": {k: v for k, v in s["manifest"].items() if k not in ("verification_cpu_s", "verification_wall_s", "source_commit")}}  # noqa: E731
        if strip(old) != strip(json.loads(body)):
            raise FileExistsError(f"{f} is immutable and differs from the rebuilt sidecar")
        return old
    f.write_text(body)
    return sc


# ------------------------------------------------------------------ evidence summary (no learning, no test data)
def _cnt(rows, key):
    return dict(sorted(collections.Counter(str(key(r)) for r in rows).items()))


def summary(sc=None) -> dict:
    sc = sc or json.loads((OUT / f"{SIDECAR}.json").read_text())
    D, R = C.design(), bd.roots()
    X, Y, P = sc["x_queries"], sc["y_queries"], sc["paired"]
    strat = lambda r: D["roots"][r["root"]]["stratum"]  # noqa: E731
    obs = lambda rs: [r for r in rs if r.get("observed") and r.get("y") in (0, 1)]  # noqa: E731
    cls = lambda r: D["roots"][r["root"]]["queries"][r["design_key"]]["classes"]  # noqa: E731
    X = [r | {"classes": cls(r)} for r in X]
    Y = [r | {"classes": cls(r)} for r in Y]
    xc = {r["design_key"]: r["classes"] for r in X}
    P = [p | {"x_classes": xc[p["x_key"]]} for p in P]
    Xo, Yo = obs(X), obs(Y)
    out = {"rows": {"x": len(X), "y": len(Y)}, "status": {"x": _cnt(X, lambda r: r["teacher_status"]), "y": _cnt(Y, lambda r: r["teacher_status"])},
           "observed": {"x": len(Xo), "y": len(Yo), "x_pos": sum(r["y"] for r in Xo), "y_pos": sum(r["y"] for r in Yo)},
           "source": {"x": _cnt(X, lambda r: r.get("source")), "y": _cnt(Y, lambda r: r.get("source"))},
           "x_by_len": _cross(Xo, lambda r: len(r["ordered_actions"])), "x_by_K": _cross(Xo, strat), "y_by_K": _cross(Yo, strat),
           "y_by_moved": _cross(Yo, lambda r: len(r["hypothetical_poses"])), "x_by_class": _cross(Xo, lambda r: "+".join(r.get("classes") or [])),
           "x_negatives": _cnt([r for r in Xo if r["y"] == 0], lambda r: (str(r["failed_phase"]).split(":")[0], r["negative_kind"])),
           "x_failed_step": _cnt([r for r in Xo if r["y"] == 0], lambda r: r["failed_phase"]),
           "y_negatives": _cnt([r for r in Yo if r["y"] == 0], lambda r: r["negative_kind"]),
           "verification": {"failed": [(r["design_key"], r["verification"]) for r in X + Y if r["teacher_status"] in ("WITNESS_VERIFICATION_FAILED", "VERIFICATION_FAILED")],
                            "positives_reverified": sum(1 for r in X + Y if (r.get("verification") or {}).get("witness") is True)}}
    dec = [p for p in P if p.get("full_joint_success") is not None]
    out["four_cell"] = _cnt(dec, lambda p: f"X={p['x']},Y={p['y']}")
    out["four_cell_by_class"] = {c: _cnt([p for p in dec if c in (p.get("x_classes") or [])], lambda p: f"X={p['x']},Y={p['y']}")
                                 for c in ("complete", "reversal", "omission")}
    out["four_cell_by_K"] = {s: _cnt([p for p in dec if D["roots"][p["root"]]["stratum"] == s], lambda p: f"X={p['x']},Y={p['y']}") for s in ("K0", "K1", "K>=2", "None")}
    out["pairs"] = {"matched_decided": len(dec), "roots_with_pair": len({p["root"] for p in dec}), "stitch_failed": sum(1 for p in P if p["x"] == 1 and p["y"] == 1 and p["full_joint_success"] is None)}
    reach = [r for r in Xo if r["y"] == 1 or str(r.get("failed_phase")) == "connector" or r.get("teacher_status") in ("TERMINAL_STATE_NOT_CLEAR", "Q_REF_NOT_CLEAR_IN_EDITED_SCENE")]
    out["connector"] = {"prefix_reached": len(reach), "verified": sum(r["y"] for r in reach), "how": _cnt([r for r in reach if r["y"] == 1], lambda r: r.get("connector_how")),
                        "failed": _cnt([r for r in reach if r["y"] == 0], lambda r: (r["teacher_status"], r["negative_kind"]))}
    out["order"] = order_contrasts(Xo, R)
    out["omission"] = omission_contrasts(Xo, Yo, D, R)
    out["travel"] = travel(P, X, Y)
    out["legacy"] = {"y_agree": _cnt([r for r in Yo if r.get("legacy_y") is not None], lambda r: r["legacy_y"] == r["y"]),
                     "x_legacy_witness_match": _cnt([r for r in Xo if r.get("legacy_witness_match") is not None], lambda r: r["legacy_witness_match"]),
                     "x_legacy_tolerance": legacy_tally(Xo, R)}
    led = [e for e in sc["manifest"]["collection"]["ledger"] if e["event"] == "finish"]
    cpu = collections.defaultdict(float)
    for e in led:
        cpu[e["root"]] += e["cpu_s"]
    out["cpu"] = {"aggregate": round(sum(cpu.values()), 1), "max_root": round(max(cpu.values()), 1) if cpu else None, "roots": len(cpu),
                  "x_query_cpu": round(sum(r.get("process_cpu_s") or 0 for r in X if r.get("source") == "PMIN_COLLECT"), 1),
                  "y_query_cpu": round(sum(r.get("process_cpu_s") or 0 for r in Y if r.get("source") == "PMIN_COLLECT"), 1),
                  "x_mean_by_len": {L: round(float(np.mean(v)), 2) for L, v in sorted(_group([r for r in X if r.get("process_cpu_s") is not None and r.get("source") == "PMIN_COLLECT"], lambda r: len(r["ordered_actions"]), lambda r: r["process_cpu_s"]).items())},
                  "y_mean_by_outcome": {L: round(float(np.mean(v)), 2) for L, v in sorted(_group([r for r in Y if r.get("process_cpu_s") is not None and r.get("source") == "PMIN_COLLECT"], lambda r: r["y"], lambda r: r["process_cpu_s"]).items(), key=str)},
                  "max_rss_mb": round(max((e.get("maxrss_kb") or 0) for e in led) / 1024, 1) if led else None,
                  "verification_cpu_s": sc["manifest"]["verification_cpu_s"]}
    return out


def legacy_tally(Xo, R) -> dict:
    """bxy_pilot.legacy_close (re-planned vs historical relocation records: exact / within 1e-12 / differs) against this witness store."""
    import bxy_pilot as BP
    old, BP.OUT = BP.OUT, OUT
    try:
        return _cnt([x for x in Xo if x.get("legacy_witness_match") is not None], lambda x: BP.legacy_close(R, x))
    finally:
        BP.OUT = old


def _group(rows, key, val):
    g = collections.defaultdict(list)
    for r in rows:
        g[key(r)].append(val(r))
    return g


def _cross(rows, key):
    g = _group(rows, key, lambda r: r["y"])
    return {str(k): {"n": len(v), "pos": int(sum(v)), "rate": round(float(np.mean(v)), 3)} for k, v in sorted(g.items(), key=lambda kv: str(kv[0]))}


def order_contrasts(Xo, R) -> dict:
    """Groups of decided X with the same root and shared Y node (same endpoint) but different orders."""
    g = collections.defaultdict(list)
    for r in Xo:
        if len(r["ordered_actions"]) >= 2:
            g[(r["root"], r["parent_y_key"])].append(r)
    groups = [v for v in g.values() if len(v) >= 2]
    disc = [v for v in groups if len({r["y"] for r in v}) == 2]
    fails = [r for v in disc for r in v if r["y"] == 0]
    cert = [r for r in fails if r["negative_kind"] == "CERTIFIED"]
    ex = [{"root": v[0]["root"], "orders": [[r["ordered_actions"], r["y"], r["teacher_status"], r.get("failed_phase"), r.get("detail")] for r in v]} for v in disc]
    return {"groups": len(groups), "concordant_1": sum(all(r["y"] == 1 for r in v) for v in groups), "concordant_0": sum(all(r["y"] == 0 for r in v) for v in groups),
            "discordant": len(disc), "discordant_roots": len({v[0]["root"] for v in disc}),
            "failing_orders": {"certified": len(cert), "budget_or_planner": len(fails) - len(cert),
                               "certificate_kinds": _cnt(cert, lambda r: r.get("detail")), "phase": _cnt(fails, lambda r: r.get("failed_phase"))},
            "discordant_groups_with_certified_failure": sum(any(r["y"] == 0 and r["negative_kind"] == "CERTIFIED" for r in v) for v in disc),
            "examples": ex}


def omission_contrasts(Xo, Yo, D, R) -> dict:
    """Complete multi-move candidates vs their single-action omissions (recomputed from S0): X and Y transitions, and for 2-move candidates
    with all four Y observed (Y_AB, Y_A, Y_B, Y_0) the binary interaction Y_AB - Y_A - Y_B + Y_0."""
    xk = {r["design_key"]: r["y"] for r in Xo}
    yk = {r["design_key"]: r["y"] for r in Yo}
    tx, ty, inter, rows = collections.Counter(), collections.Counter(), collections.Counter(), []
    for k in D["root_order"]:
        seen_y = set()                                       # Y is order-free: one contrast per (endpoint, omitted endpoint)
        rec = R[k]
        y0 = yk.get(T.ykey(k, rec, []))
        for c in bd.catalogue(rec)[1:]:
            s = [tuple(a) for a in c["seq"]]
            if len(s) < 2 or not F1.screen(rec, s)["x_ok"]:
                continue
            xf, yf = xk.get(T.xkey(k, rec, s)), yk.get(T.ykey(k, rec, s))
            ys = []
            for t in range(len(s)):
                om = [a for i, a in enumerate(s) if i != t]
                xo, yo = xk.get(T.xkey(k, rec, om)), yk.get(T.ykey(k, rec, om))
                if xf is not None and xo is not None:
                    tx[f"{xf}->{xo}"] += 1
                pair = (T.ykey(k, rec, s), T.ykey(k, rec, om))
                if yf is not None and yo is not None and pair not in seen_y:
                    ty[f"{yf}->{yo}"] += 1
                seen_y.add(pair)
                ys.append(yo)
            if len(s) == 2 and None not in (yf, y0, *ys) and ("I", T.ykey(k, rec, s)) not in seen_y:
                seen_y.add(("I", T.ykey(k, rec, s)))
                i = yf - ys[0] - ys[1] + y0                  # ys[0] = omit first = Y_B, ys[1] = omit second = Y_A
                inter[i] += 1
                if i != 0:
                    rows.append({"root": k, "seq": s, "Y_AB": yf, "Y_B": ys[0], "Y_A": ys[1], "Y_0": y0})
    return {"x_full_to_omitted": dict(tx), "y_full_to_omitted": dict(ty), "two_move_interaction": {str(a): b for a, b in sorted(inter.items())},
            "two_move_nonadditive_examples": rows[:20], "two_move_nonadditive_n": len(rows),
            "reading": "y 1->0: the omitted action was needed for the target in the edited-scene sense; y 1->1: not needed (redundant for Y); "
                       "interaction +1: both actions jointly needed (Y_AB = 1, Y_A = Y_B = Y_0 = 0)"}


def travel(P, X, Y) -> dict:
    xs = {r["design_key"]: r for r in X}
    J = [(p, xs[p["x_key"]]) for p in P if p.get("full_joint_success") == 1 and p.get("J_total") is not None]
    if not J:
        return {"n": 0}
    tot = np.array([p["J_total"] for p, _ in J])
    conn = np.array([x["travel_parts"]["J_connector"] for _, x in J])
    mv = np.array([sum(x["travel_parts"]["J_move"]) for _, x in J])
    tgt = tot - conn - mv
    m = collections.defaultdict(list)
    for p, x in J:
        m[len(x["ordered_actions"])].append(p["J_total"])
    y0 = [r["J_target"] for r in Y if r.get("observed") and r.get("y") == 1 and not r["hypothetical_poses"] and r.get("J_target") is not None]
    return {"n": len(J), "J_total": _stats(tot), "J_relocations": _stats(mv), "J_connector": _stats(conn), "J_target": _stats(tgt),
            "connector_share_median": round(float(np.median(conn / tot)), 3), "by_m": {k: _stats(np.array(v)) for k, v in sorted(m.items())},
            "noop_target_travel": _stats(np.array(y0)) if y0 else None, "max_abs_parts_gap": round(float(max(abs(p["J_total"] - p["J_parts_sum"]) for p, _ in J)), 12)}


def _stats(a):
    return {"n": int(len(a)), "mean": round(float(np.mean(a)), 3), "median": round(float(np.median(a)), 3), "min": round(float(np.min(a)), 3), "max": round(float(np.max(a)), 3)}


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "build":
        sc = build()
        print(json.dumps({k: v for k, v in sc["manifest"].items() if k != "collection"} | {"x": len(sc["x_queries"]), "y": len(sc["y_queries"]), "pairs": len(sc["paired"])}, indent=1))
    else:
        s = summary()
        (OUT / "PMIN_EVIDENCE_SUMMARY.json").write_text(json.dumps(s, indent=1, sort_keys=True, default=str))
        print(json.dumps({k: v for k, v in s.items() if k not in ("order", "omission")}, indent=1, default=str)[:6000])
