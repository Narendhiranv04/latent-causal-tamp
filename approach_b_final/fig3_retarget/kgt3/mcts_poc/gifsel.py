#!/usr/bin/env python3
"""Predeclared GIF selection for the GA-MCTS evaluation (evaluator; after analyze.py).  Writes a kgt3/gifs.py 3D spec (stored teacher
witnesses re-executed, never re-planned).  Rule: at the 30 s budget, the first 2 roots (sha256('MCTSGIF|' + root) order) where only GA-MCTS s0
verifies, the first 2 where only GA verifies (one each shows the failing arm, ending on its captioned still), and the first root where
both verify different plans.
    $PY3D gifsel.py EVAL_DIR SPEC.json ;  MUJOCO_GL=egl $PY3D ../gifs.py 3d SPEC.json OUT_DIR"""
from __future__ import annotations

import hashlib, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent), str(HERE.parent.parent.parent)]
import evaljobs as EJ  # noqa: E402


def main(ev, out, bud=30):
    import r6
    ev = Path(ev)
    R = json.loads((ev / "EVAL_RESULTS.json").read_text())["per_root"]
    sel = {(s["root_id"], s["method"]): s for s in json.loads((ev / "selection_eval.json").read_text())}
    ph = {r["key"]: r for r in EJ.jl(ev / "phys_eval.jsonl")}
    arc = {v["src"]: v["rec"] for v in r6.archive_r10().values()}
    meta = {rid: m for rid, _, m in r6.roots("r10comp")}

    def rec(rid, lab):
        s = sel[(rid, lab)]
        if s["status"] == "SAME_AS":
            s = next(x for x in sel.values() if x.get("job") == s["job"] and x["status"] in ("QUEUED", "REUSED"))
        return arc[s["src"]] if s["status"] == "REUSED" else ph.get(s.get("job"))
    order = sorted(R, key=lambda r: hashlib.sha256(f"MCTSGIF|{r}".encode()).hexdigest())
    a, b = f"GA-MCTS-s0@{bud}", f"GA@{bud}"
    only_m = [r for r in order if R[r][a]["succ"] and not R[r][b]["succ"]][:2]
    only_g = [r for r in order if R[r][b]["succ"] and not R[r][a]["succ"]][:2]
    both = [r for r in order if R[r][a]["succ"] and R[r][b]["succ"] and sel[(r, a)].get("job") != sel[(r, b)].get("job")][:1]
    spec = []
    for rid, labs in [(r, (a, b)) for r in only_m + only_g + both]:
        for lab in labs:
            x = rec(rid, lab)
            if x and (x.get("X") or {}).get("trace"):
                spec.append({"path": meta[rid]["path"], "x": x["X"], "title": f"{rid} | {lab} | {'VERIFIED' if R[rid][lab]['succ'] else 'NOT VERIFIED'}"})
    Path(out).write_text(json.dumps(spec, indent=1)); print(len(spec), "clips ->", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
