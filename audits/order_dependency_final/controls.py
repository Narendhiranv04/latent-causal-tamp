#!/usr/bin/env python3
"""Controlled counterfactual queries for the order-dependency audit (P2 / P3 / P4).  IMPLEMENTED, NOT EXECUTED.

Reuses the unchanged DISCO stage-2 adapter (RepairEnv: BXY DetPhysics 2D, fin3d / MuJoCo 3.16 3D) read-only.  Two starts for the SAME action in
the SAME ideal object state S_P (P = set of already-relocated movers at their selected destinations):
  REF      F(a | S_P, q_ref)        state rewritten to S_P with the robot at q_ref (2D: payload cells / q; 3D: bd_3dt.settle = reset to
                                    q_ready + teleport, the primitive used by the generators' own independence checks)
  CARRIED  F(a | S_P, q(prefix))    reset, execute the predecessor ORDER with carried state, then the action (= the finalized-X protocol)
Only the robot start differs between REF and CARRIED for a matched (a, P).  A REF start is a diagnostic intervention: whether the real arm
could reach q_ref inside S_P is NOT asserted (a q_ref-in-collision result is recorded as such, never as a label).

Physics is refused unless ORDER_AUDIT_EXECUTION_APPROVED is set to the approval token written by the user into COUNTERFACTUAL_AUDIT_PLAN.md
(no such approval exists yet).  Without it only `--dry-run` works: it builds the REF states (2D) and checks them, with no planner call.
    python controls.py --dry-run [N_ROOTS]
    ORDER_AUDIT_EXECUTION_APPROVED=<token> python controls.py --run PILOT.jsonl OUT.jsonl --seeds 0,1,2"""
import copy, dataclasses, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DISCO = Path(os.environ.get("DISCO_CODE", "/home/naren/Desktop/boltzmann_lfd/.claude/worktrees/disco-grid-stage2/baselines/disco_grid"))
sys.path.insert(0, str(DISCO))


def env_for(dom):
    import env as E                                                             # noqa: E402  (DISCO RepairEnv, unchanged)
    return E, E.RepairEnv(dom.lower())


def ref_state(E, env, root_id, P, seed=0):
    """FullState for S_P with the robot at q_ref.  P: [(obj_idx, dest_cell), ...] (order irrelevant: canonical sort)."""
    P = sorted((int(o), int(c)) for o, c in P)
    s = env.reset(root_id, seed=seed)
    row, rec = env._get_row_and_raw(root_id)
    ids = row["inputs"]["ids"]
    cells, moved, pay = list(s.cells), list(s.moved_mask), copy.deepcopy(s.physics_payload)
    for o, c in P:
        cells[o], moved[o] = c, True
    if s.domain == "2d":
        for o, c in P:
            pay["cells_dict"][ids[o]] = c                                       # q stays q_ref (reset), budgets fresh
    else:
        b = env.backend
        e = b._get_env(root_id, rec)
        cd = copy.deepcopy(rec["initial_cells"])
        for o, c in P:
            cd[ids[o]] = [c // 6, c % 6]
        b.A.settle(e, cd)                                                       # reset arm to q_ready, teleport objects (bd_3dt.settle)
        pay = b._snap_env(e, [])
    return dataclasses.replace(s, depth=len(P), prefix=P, cells=cells, moved_mask=moved, used_dests=[c for _, c in P], physics_payload=pay)


def query(E, env, q, seed=0):
    """One controlled query from MISSING_COUNTERFACTUALS.jsonl -> outcome record (physics)."""
    a = tuple(q["action"])
    if q["query"] == "REF":
        st = ref_state(E, env, q["root_id"], q["pred_set"], seed)
    else:
        st = env.reset(q["root_id"], seed=seed)
        for p in q["prefix"]:
            r = env.transition(st, tuple(p))
            if r.status != "EXECUTED":
                return {**q, "seed": seed, "outcome": "PREFIX_FAILED", "failure_kind": r.failure_kind, "teacher_status": r.teacher_status}
            st = r.next_state
    r = env.transition(st, a)
    return {**q, "seed": seed, "outcome": 1 if r.status == "EXECUTED" else 0, "failure_kind": r.failure_kind, "teacher_status": r.teacher_status,
            "time_s": r.time_s, "start_q": [round(float(v), 6) for v in st.q_t]}


def dry_run(n=3):
    """No planner / transition call: build REF states for the first N 2D queries and check S_P cells, q = q_ref, P = {} == reset."""
    E, env = env_for("2D")
    qs = [json.loads(l) for l in open(HERE / "MISSING_COUNTERFACTUALS.jsonl") if '"2D"' in l and '"REF"' in l][:n]
    ok = True
    for q in qs:
        s0, s = env.reset(q["root_id"]), ref_state(E, env, q["root_id"], q["pred_set"])
        z = ref_state(E, env, q["root_id"], [])
        exp = list(s0.cells)
        for o, c in q["pred_set"]:
            exp[o] = c
        chk = {"cells_S_P": s.cells == exp, "q_is_q_ref": s.q_t == s0.q_t == s.physics_payload["q"],
               "payload_cells_match": all(s.physics_payload["cells_dict"][env._get_row_and_raw(q["root_id"])[0]["inputs"]["ids"][o]] == c for o, c in q["pred_set"]),
               "empty_P_equals_reset": z.state_hash() == s0.state_hash(), "action_legal_after_P": tuple(q["action"]) in
               {tuple(x) for x in env.legal_actions(s, include_stop=False).get("relocation_actions", [])} or None}
        ok &= all(v in (True, None) for v in chk.values())
        print(q["root_id"], q["action"], q["pred_set"], chk)
    print("DRY_RUN_OK" if ok else "DRY_RUN_FAILED")
    return ok


if __name__ == "__main__":
    if sys.argv[1:2] == ["--dry-run"]:
        sys.exit(0 if dry_run(int(sys.argv[2]) if len(sys.argv) > 2 else 3) else 1)
    if sys.argv[1:2] == ["--run"]:
        tok = (HERE / "COUNTERFACTUAL_AUDIT_PLAN.md").read_text().split("APPROVAL_TOKEN:")[-1].split()[0] if "APPROVAL_TOKEN:" in (HERE / "COUNTERFACTUAL_AUDIT_PLAN.md").read_text() else None
        if not tok or os.environ.get("ORDER_AUDIT_EXECUTION_APPROVED") != tok:
            sys.exit("REFUSED: counterfactual physics not authorized (no user approval token in COUNTERFACTUAL_AUDIT_PLAN.md)")
        jobs, out = [json.loads(l) for l in open(sys.argv[2])], open(sys.argv[3], "a")
        seeds = [int(x) for x in sys.argv[sys.argv.index("--seeds") + 1].split(",")] if "--seeds" in sys.argv else [0]
        for q in jobs:
            E, env = env_for(q["domain"])
            for sd in seeds:
                out.write(json.dumps(query(E, env, q, sd), sort_keys=True) + "\n"); out.flush()
    else:
        print(__doc__)
