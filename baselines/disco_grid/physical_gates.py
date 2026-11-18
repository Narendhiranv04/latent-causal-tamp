#!/usr/bin/env python3
"""DISCO-Grid physical gates (TRAIN roots only, real finalized teachers through RepairEnv; one process, one thread).

For each selected root (hash order within K strata) and each certificate order in the snapshot labels (x = finalized X of that
order, legacy_y / y_selected_endpoint = endpoint Y):
  G1 adapter-vs-teacher : execute the order through RepairEnv.transition, then STOP; DISCO's EXECUTED/X and Y agree with the label
  G2 restore determinism: restore(blob after step 1) and re-execute step 2 -> identical next-state hash
  G3 carryover / gripper: q_t after step i is the start q of step i+1 (continuous), gripper released (held None) after each move
  G4 legality           : a moved object leaves eligible_objects; a used destination leaves legal_destinations
  G5 STOP connector + Y : STOP result carries connector + independent Y outcome; K0 root STOP = NOOP success (Y(empty)=1)
  G6 failed STOP        : STOP after the first move of a K>=2 order is DECIDED z=0, and the same depth-1 state is then expanded
                          further and reaches a successful STOP (failed STOP leaves a valid intermediate state)
UNRESOLVED / timeouts are reported as such (censored), never as physical negatives.

    physical_gates.py DOM N_K2 OUT.json [N_K0=1] [N_K3=1]"""
import ast, hashlib, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data as D  # noqa: E402
import env as E  # noqa: E402


def lab(r, k):
    v = r[k]
    return ast.literal_eval(v) if isinstance(v, str) else v


def pick(rows, K, n, salt="gates"):
    sub = [r for r in rows if r["K_legacy"] == K]
    sub.sort(key=lambda r: hashlib.sha256(f"{salt}|{r['root_id']}".encode()).hexdigest())
    return sub[:n]


def run_order(env, root, seq):
    st = env.reset(root, seed=0)
    out = {"steps": [], "calls": 0}
    blobs = [env.clone_or_serialize(st)]
    for i, a in enumerate(seq):
        q_before = list(st.q_t)
        obs = env.observe(st)
        legal = a[0] in obs.eligible_objects and a[1] in obs.legal_destinations
        t0 = time.time(); sr = env.transition(st, tuple(a)); out["calls"] += 1
        step = {"action": a, "legal_in_obs": legal, "status": sr.status, "failure_kind": sr.failure_kind, "time_s": round(time.time() - t0, 2)}
        if sr.status == "EXECUTED":
            nx = sr.next_state
            o2 = env.observe(nx)
            step.update(moved_left_eligible=a[0] not in o2.eligible_objects, dest_left_legal=a[1] not in o2.legal_destinations,
                        gripper_released=(nx.gripper_state or {}).get("held") is None, q_changed=list(nx.q_t) != q_before,
                        next_hash=nx.state_hash())
            st = nx; blobs.append(env.clone_or_serialize(st))
        out["steps"].append(step)
        if sr.status != "EXECUTED":
            break
    else:
        t0 = time.time(); sp = env.terminal_query(st); out["calls"] += 1
        out["stop"] = {"status": sp.status, "success": sp.success, "x": sp.x_terminal, "y": sp.y_target, "z": sp.z_outcome,
                       "connector_status": sp.connector_status, "y_status": sp.y_status, "has_connector_witness": bool(sp.witness_connector),
                       "failed_phase": sp.failed_phase, "time_s": round(time.time() - t0, 2)}
    out["blobs"] = blobs
    return out


def main(dom, n2, outp, n0=1, n3=1):
    rows = D.load_snapshot_rows(dom, "train", D.BASE_SNAP)
    env = E.RepairEnv(dom, witness_dir=Path(outp).parent / f"witnesses_{dom}")
    res = {"domain": dom, "split": "train", "roots": [], "utc_start": time.strftime("%FT%TZ", time.gmtime())}
    T0 = time.time()
    for r in pick(rows, "0", n0) + pick(rows, "2", n2) + pick(rows, "3", n3):
        X = lab(r, "labels")["X"]; meta = lab(r, "meta")
        rr = {"root_id": r["root_id"], "K": r["K_legacy"], "orders": []}
        if r["K_legacy"] == "0":
            st = env.reset(r["root_id"], seed=0); sp = env.terminal_query(st)
            rr["noop_stop"] = {"status": sp.status, "z": sp.z_outcome, "y": sp.y_target, "has_connector_witness": bool(sp.witness_connector)}
            rr["G5_noop_ok"] = sp.status == "UNRESOLVED" or (sp.z_outcome == 1)
        for o in X:
            seq = [list(map(int, a)) for a in o["seq"]]
            ex = run_order(env, r["root_id"], seq)
            blobs = ex.pop("blobs")
            lab_x = o.get("x")
            ykey = sorted(map(tuple, seq))                                # finalized endpoint Y is keyed by the edit SET (labels["Y"])
            lab_y = next((y["y"] for y in lab(r, "labels").get("Y", []) if sorted(map(tuple, y["edit"])) == ykey), None)
            executed_all = all(s["status"] == "EXECUTED" for s in ex["steps"]) and len(ex["steps"]) == len(seq)
            unresolved = any(s["status"] == "UNRESOLVED" for s in ex["steps"]) or ex.get("stop", {}).get("status") == "UNRESOLVED"
            disco_x = int(executed_all and ex.get("stop", {}).get("x") == 1)
            rec = {"seq": seq, "label_x": lab_x, "label_y": lab_y, **ex, "disco_x": disco_x, "unresolved": unresolved,
                   "G1_agree": None if unresolved or lab_x is None else disco_x == int(lab_x)}
            if executed_all and lab_x == 1 and ex.get("stop", {}).get("status") == "DECIDED":
                rec["G1_y_agree"] = None if lab_y is None else ex["stop"]["y"] == int(lab_y)
            if len(blobs) >= 3:                                           # G2 determinism of step 2 from restored step-1 state
                s1 = env.restore(blobs[1]); sr = env.transition(s1, tuple(seq[1]))
                rec["G2_restore_same_hash"] = sr.status == "EXECUTED" and sr.next_state.state_hash() == ex["steps"][1].get("next_hash")
                rec["G3_q_continuity"] = list(env.restore(blobs[1]).q_t) == list(s1.q_t)
            if len(seq) >= 2 and len(blobs) >= 2 and lab_x == 1:          # G6 failed STOP at depth 1, then continue to success
                s1 = env.restore(blobs[1]); sp1 = env.terminal_query(s1)
                cont = env.transition(env.restore(blobs[1]), tuple(seq[1]))
                rec["G6"] = {"stop_depth1": {"status": sp1.status, "z": sp1.z_outcome, "phase": sp1.failed_phase},
                             "continue_status": cont.status}
            rr["orders"].append(rec)
        res["roots"].append(rr)
        print(json.dumps({"root": r["root_id"], "K": r["K_legacy"], "orders": [(o["label_x"], o["disco_x"], o["G1_agree"]) for o in rr["orders"]],
                          "elapsed_s": round(time.time() - T0)}), flush=True)
    res["wall_s"] = round(time.time() - T0, 1)
    Path(outp).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[1]), a[2], *(int(x) for x in a[3:5]))
