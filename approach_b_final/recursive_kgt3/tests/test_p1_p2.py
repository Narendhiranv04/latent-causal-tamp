#!/usr/bin/env python3
"""P1 (adapters / reservation mask) and P2 (planner on mocks) tests.  Plain-python asserts; writes a JSON report.  No TEST data, no physics.
    python tests/test_p1_p2.py OUT.json"""
import copy, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import data as DA  # noqa: E402
import planner as PLN  # noqa: E402
from mock_models import MockModels, make_row  # noqa: E402

VAL_IN = Path.home() / "abf_v34/parity/public_val_2d.jsonl"
R, FAIL = {}, []


def check(name, cond, info=None):
    R[name] = {"pass": bool(cond), **({"info": info} if info is not None else {})}
    if not cond:
        FAIL.append(name)


def p1():
    rows = DA.jl(VAL_IN)
    n_id = n_rt = n_t0 = n_g0 = n_ctx = n_res = tot = 0
    for r in rows:
        inp = r["inputs"]
        if DA.retarget2d(inp, inp["tid"], inp["goal_cell"]) == inp:
            n_id += 1
        h0 = DA.HypoRoot(r)
        for A in h0.movable[:3]:
            for dA in h0.legal_dests(h0.cells0)[:2]:
                tot += 1
                v = DA.retarget2d(inp, A, dA)
                if DA.retarget2d(v, inp["tid"], inp["goal_cell"]) == inp:
                    n_rt += 1
                h = DA.HypoRoot(r, (), (A, dA), reserved={h0.movable[-1]}, rcells={h0.legal_dests(h0.cells0)[-1]})
                legal = h.legal_dests(h.cells0)
                n_t0 += int(inp["tid"] not in h.movable and A not in h.movable)
                n_g0 += int(inp["goal_cell"] not in legal and dA not in legal)
                n_res += int(h0.movable[-1] not in h.movable and h0.legal_dests(h0.cells0)[-1] not in legal)
                hi = h.row["inputs"]
                n_ctx += int(hi["tid"] == A and hi["goal_cell"] == dA and hi["ctx"][6:8] == list(map(float, inp["cell_xy"][str(dA)]))
                             and hi["attrs"][A][1:3] == [1.0, 0.0] and hi["attrs"][inp["tid"]][1:3] == [0.0, 1.0] and not set(legal) & set(inp["cells0"]))
    check("P1.identity_exact", n_id == len(rows), f"{n_id}/{len(rows)}")
    check("P1.round_trip_exact", n_rt == tot, f"{n_rt}/{tot}")
    check("P1.original_target_never_movable", n_t0 == tot, f"{n_t0}/{tot}")
    check("P1.original_goal_and_temp_goal_illegal", n_g0 == tot, f"{n_g0}/{tot}")
    check("P1.reserved_objects_and_cells_excluded", n_res == tot, f"{n_res}/{tot}")
    check("P1.task_context_consistent_and_no_S0_cell_legal", n_ctx == tot, f"{n_ctx}/{tot}")
    r = rows[0]; inp = r["inputs"]; T0, G0, o = inp["tid"], inp["goal_cell"], DA.HypoRoot(r).movable
    free = DA.HypoRoot(r).legal_dests(inp["cells0"])
    cases = {"TARGET_MOVED": [(T0, free[0])], "OBJECT_TWICE": [(o[0], free[0]), (o[0], free[1])], "ORIGINALLY_OCCUPIED": [(o[0], inp["cells0"][o[1]])],
             "GOAL_CELL": [(o[0], G0)], "OCCUPIED_NOW": [(o[0], free[0]), (o[1], free[0])], "LENGTH": [(o[0], free[0])] * 13 if len(o) else []}
    got = {k: DA.check_sequence(r, v) for k, v in cases.items()}
    check("P1.legality_rejections", all(got[k] == k or (k == "LENGTH" and got[k] in ("LENGTH", "OBJECT_TWICE")) for k in got), got)
    check("P1.legal_sequence_accepted", DA.check_sequence(r, [(o[0], free[0]), (o[1], free[1])]) is None)


CHAINS = {
    "K4": ({1: [3], 0: [1, 2]}, [4]),
    "K6": ({0: [1, 2], 1: [4], 4: [5], 3: [6]}, [3]),
    "K9": ({0: [1, 2, 3], 1: [4, 5], 4: [6], 2: [7], 3: [8]}, [9]),
    "K12": ({0: [1, 2, 3], 1: [4, 5], 4: [7], 2: [6], 6: [8, 9], 3: [10], 10: [11]}, [12]),
}


def valid(BLK, GB, seq):
    done = set()
    for o, _ in seq:
        if not set(BLK.get(o, [])) <= done:
            return False
        done.add(o)
    return (set(BLK.get(0, [])) | set(GB)) <= done


def p2(out_dir):
    traces = {}
    for name, (BLK, GB) in CHAINS.items():
        K = int(name[1:])
        row = make_row(18, name=f"MOCK_{name}")
        for arm in ("REC", "FLAT"):
            M = MockModels(row, BLK, GB)
            log = {"local": [], "ytask": [], "insert": [], "rounds": []}
            res = PLN.Planner(row, M, arm, {"max_wall_s": 60.0}, log).run()
            ok = res["decision"] == "REPAIR" and DA.check_sequence(row, res["seq"]) is None and valid(BLK, GB, res["seq"])
            traces[f"{name}_{arm}"] = {"res": res, "log": log}
            R[f"P2.{name}.{arm}"] = {"pass": ok if arm == "REC" else True, "solved": ok, "len": len(res["seq"]), "seq_objs": [o for o, _ in res["seq"]],
                                     "stop": res["stop"], "local_calls": res["budget"]["local"], "ytask": res["budget"]["ytask"], "cands": res["n_candidates"]}
            if arm == "REC" and not ok:
                FAIL.append(f"P2.{name}.REC")
            if arm == "REC":
                check(f"P2.{name}.REC.min_length", len(res["seq"]) == K, len(res["seq"]))
    BLK, GB = CHAINS["K12"]
    row = make_row(18, name="MOCK_K12_HIDE")
    res = PLN.Planner(row, MockModels(row, BLK, GB, hide={11}), "REC", {"max_wall_s": 60.0}).run()
    check("P2.K12.hidden_enabler_not_solved", not valid(BLK, GB, res["seq"]), {"stop": res["stop"], "len": len(res["seq"]), "local": res["budget"]["local"]})
    good = [(o, 0) for o in [7, 4, 5, 1, 8, 9, 6, 2, 11, 10, 3, 12]]
    bad = [(o, 0) for o in [1, 7, 4, 5, 8, 9, 6, 2, 11, 10, 3, 12]]
    M = MockModels(row, BLK, GB)
    check("P2.same_endpoint_same_Y_diff_X", M.y_end(row, [good])[0] == M.y_end(row, [bad])[0] and M.x_chunk(DA.HypoRoot(row), [x for x in bad[:3]]) < M.x_chunk(DA.HypoRoot(row), good[:3]))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / "p2_mock_traces.json").write_text(json.dumps(traces, default=str))


if __name__ == "__main__":
    out = Path(sys.argv[1])
    p1(); p2(out.parent)
    R["_summary"] = {"failed": FAIL, "n_checks": len(R)}
    out.write_text(json.dumps(R, indent=1, default=str))
    for k, v in R.items():
        if k != "_summary":
            print(("PASS " if v.get("pass") else "FAIL ") + k, {kk: vv for kk, vv in v.items() if kk != "pass"})
    print("FAILED:", FAIL)
