#!/usr/bin/env python3
"""Gate B: P4 variants on the symbolic mock (no K, no blocker labels; mock signals only).  Checks R1/R2/R3 compose K4/K6/K9/K12 dependency
chains in a valid order at minimum length, FLAT cannot (nested enablers), budgets/stop reasons are recorded, and a longer complete plan
outranks a shorter incomplete one under the R1 energy.
    python tests/test_p4_mock.py OUT.json"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import data as DA  # noqa: E402
import planner_r as PR  # noqa: E402
from mock_models import MockModels, make_row  # noqa: E402
from test_p1_p2 import CHAINS, valid  # noqa: E402

CFG = json.loads((HERE.parent / "p4_config.json").read_text())["arms"]


def main(out):
    R, FAIL, traces = {}, [], {}
    for name, (BLK, GB) in CHAINS.items():
        K = int(name[1:])
        for arm in ("R1", "R2", "R3", "F"):
            row = make_row(18, name=f"MOCK_{name}")
            M = MockModels(row, BLK, GB)
            log = {"local": [], "ytask": [], "insert": [], "rounds": [], "seeds": []}
            spec = CFG[arm]
            P = PR.PlannerR(row, M, spec["mode"], {**spec["cfg"], "max_wall_s": 120.0}, log)
            res = P.run()
            ok = res["decision"] == "REPAIR" and DA.check_sequence(row, res["seq"]) is None and valid(BLK, GB, res["seq"])
            cands = [json.loads(k) for k, v in P.cands.items() if v is not None]
            gen_complete = any(valid(BLK, GB, c) for c in cands)
            R[f"{name}.{arm}"] = {"solved": ok, "len": len(res["seq"]), "min_len": len(res["seq"]) == K if ok else False, "generated_complete": gen_complete,
                                  "stop": res["stop"], "local": res["budget"]["local"], "ytask": res["budget"]["ytask"], "rounds": res["rounds"],
                                  "n_cands": res["n_candidates"], "insertions": len(log["insert"]), "seeds": len(log["seeds"])}
            traces[f"{name}_{arm}"] = {"res": res, "log": log}
            if arm in ("R1", "R2", "R3") and not ok:
                FAIL.append(f"{name}.{arm}")
            if arm == "F" and ok and K > 4:
                FAIL.append(f"{name}.F_should_not_solve_nested")
    # energy property: complete longer plan must outrank a shorter incomplete plan (mock signals)
    BLK, GB = CHAINS["K12"]
    row = make_row(18, name="MOCK_E")
    P = PR.PlannerR(row, MockModels(row, BLK, GB), "REC", CFG["R1"]["cfg"])
    good = [(o, d) for o, d in zip([7, 4, 5, 1, 8, 9, 6, 2, 11, 10, 3, 12], [0, 8, 16, 24, 32, 40, 48, 56, 1, 9, 17, 25])]
    short = [(1, 0), (2, 8), (3, 16)]
    eg, es = P.energy([good, short])
    R["energy.longer_complete_beats_shorter_incomplete"] = {"C_long": eg["C"], "C_short": es["C"], "pass": eg["C"] < es["C"]}
    if not eg["C"] < es["C"]:
        FAIL.append("energy_order")
    R["_failed"] = FAIL
    Path(out).write_text(json.dumps(R, indent=1, default=str))
    (Path(out).parent / "p4_mock_traces.json").write_text(json.dumps(traces, default=str))
    for k, v in R.items():
        print(k, v)


if __name__ == "__main__":
    main(sys.argv[1])
