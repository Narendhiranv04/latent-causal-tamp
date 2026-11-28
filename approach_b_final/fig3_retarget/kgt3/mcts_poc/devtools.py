#!/usr/bin/env python3
"""DEV-only evaluator helpers (never imported by the planners).
    python devtools.py prep OUT_DIR             -> OUT_DIR/PUBLIC_dev_3d.jsonl (public rows of the 20 exposed DEV roots, r53.panel('3d'),
                                                   schema-checked) + DEV_SEAL.json; the planner reads ONLY this file
    python devtools.py parity ANY.jsonl REF.jsonl OUT.json
                                                -> GA plan parity: harness GA final (= planners.plan) vs the sealed R8C DEV GA plans
                                                   (exact on roots where neither run hit the deadline; timeout roots reported separately)
    python devtools.py tests OUT.json           -> runs the existing + new pytest suites and records the result"""
from __future__ import annotations

import hashlib, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KG = HERE.parent
sys.path[:0] = [str(HERE), str(KG), str(KG.parent), str(KG.parent.parent)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prep(out):
    import r6
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for rid, row, _meta in r6.roots("3d"):                               # evaluator-side read; meta (witness, L_ref) is discarded here
        r = {"root_id": rid, "domain": "3d", "inputs": row["inputs"]}
        assert set(r["inputs"]) <= r6.INPUT_KEYS, (rid, sorted(set(r["inputs"]) - r6.INPUT_KEYS))
        rows.append(r)
    f = out / "PUBLIC_dev_3d.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "DEV_SEAL.json").write_text(json.dumps({"public": sha(f), "n": len(rows), "source": "r6.roots('3d') = r53.panel('3d') public fields only"}, indent=1))
    print(len(rows), sha(f))


def parity(any_path, ref_path, out):
    A = {r["root_id"]: r for r in (json.loads(l) for l in open(any_path)) if r["arm"] == "GA"}
    R = {r["root_id"]: r["arms"]["GA"] for r in (json.loads(l) for l in open(ref_path))}
    rows, exact_ok, exact_n, to = [], 0, 0, []
    for rid in sorted(R):
        if rid not in A:
            rows.append({"root_id": rid, "status": "MISSING"}); continue
        g, r = A[rid]["final"], R[rid]
        same = (g["decision"], g["seq"], g["partition"]) == (r["decision"], r["seq"], r["partition"]) and (g["E"] is None and r["E"] is None or abs(g["E"] - r["E"]) < 1e-9)
        timeout = bool(g["budget_stop"] or r["budget_stop"])
        row = {"root_id": rid, "same_plan": same, "timeout_any": timeout, "mode_now": g["mode"], "mode_ref": r.get("mode"), "E_now": g["E"], "E_ref": r["E"],
               "wall_now": g["wall_s"], "wall_ref": r["wall_s"], "len_now": len(g["seq"] or []), "len_ref": len(r["seq"] or [])}
        rows.append(row)
        if not timeout:
            exact_n += 1; exact_ok += same
        else:
            to.append(row)
    res = {"non_timeout_roots": exact_n, "non_timeout_identical": exact_ok, "PASS": exact_n > 0 and exact_ok == exact_n,
           "timeout_roots": len(to), "timeout_identical": sum(r["same_plan"] for r in to), "rows": rows,
           "note": "plans under a budget stop depend on wall-clock progress (completed sizes) and are not expected to be bitwise reproducible"}
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}))


def tests(out):
    res = {}
    for name, args in (("kgt3_tests", [str(KG / "tests")]), ("r10_public_loader", [str(KG / "r10" / "test_public_loader.py")]),
                       ("mcts_poc_unit", [str(HERE / "tests" / "test_mcts_ga.py")])):
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args], capture_output=True, text=True)
        res[name] = {"rc": p.returncode, "tail": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-400:]}
    Path(out).write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"prep": lambda: prep(sys.argv[2]), "parity": lambda: parity(*sys.argv[2:5]), "tests": lambda: tests(sys.argv[2])}[sys.argv[1]]()
