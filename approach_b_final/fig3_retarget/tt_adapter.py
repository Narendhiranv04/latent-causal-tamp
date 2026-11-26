"""TT_ADAPTER_V1, extracted VERBATIM (adapt, new_ids) from validation_k3/ttarget.py @ e9fa587c3b (naren/k3-postablation-validation) so the
Fig. 3 physical adapters reuse the already-validated temporary-target record adaptation (C3 / C3b: identity parity 2D 109/109, 3D 82/82;
RNG-key noise floor unchanged; semantic first-move cross-check 101/109, 75/82) instead of rebuilding it.  The unchanged teachers are then
called on the adapted raw record (temporary target A carries id 't0'; the original target takes A's id as an ordinary obstacle body).
Source sha256 (ttarget.py @ e9fa587c3b) is recorded in R1_MANIFEST.json.  Do not edit below this docstring."""
import copy

ADAPTER = "TT_ADAPTER_V1"


def adapt(raw, dom, A_id, goal_cell, tag=True):
    """raw record -> temporary-task raw record (A_id becomes 't0'; the original target takes A_id).  A_id == 't0' and the original goal
    returns an identical record (identity)."""
    r = copy.deepcopy(raw)
    goal_cell = int(goal_cell)
    if dom == "2d":
        if A_id != "t0":
            for o in r["scene"]["objects"]:
                if o["id"] == A_id:
                    o["id"], o["kind"] = "t0", "target"
                elif o["id"] == "t0":
                    o["id"], o["kind"] = A_id, "obstacle"
            r["roles"] = {(A_id if k == A_id else k): v for k, v in r["roles"].items() if k != A_id}
            r["roles"][A_id] = "temporary_obstacle"
            assert A_id not in r["fixed_ids"]
        r["goal_cell"] = goal_cell
    else:
        if A_id != "t0":
            for o in r["objects"]:
                if o["id"] == A_id:
                    o["id"] = "t0"
                elif o["id"] == "t0":
                    o["id"] = A_id
            ic = r["initial_cells"]
            ic["t0"], ic[A_id] = ic[A_id], ic["t0"]
            r["roles"] = {k: v for k, v in r.get("roles", {}).items() if k != A_id}
            r["roles"][A_id] = "temporary_obstacle"
        r["goal"] = [goal_cell // 6, goal_cell % 6]
    if tag and (A_id != "t0" or goal_cell != (raw["goal_cell"] if dom == "2d" else raw["goal"][0] * 6 + raw["goal"][1])):
        r["ids"] = {**r["ids"], "root_id": f"{raw['ids']['root_id']}~TT~{A_id}~{goal_cell}"}
        if dom == "2d":
            r["scene"]["root_id"] = r["ids"]["root_id"]
    r["tt_adapter"] = {"version": ADAPTER, "A": A_id, "goal_cell": goal_cell, "source_root": raw["ids"]["root_id"]}
    return r


def new_ids(ids, A, tid):
    return ["t0" if i == A else (ids[A] if i == tid else x) for i, x in enumerate(ids)]
