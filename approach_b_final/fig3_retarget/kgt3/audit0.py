#!/usr/bin/env python3
"""KGT3 P0 runtime provenance audit (gvlab2 GPU; model-only, no teacher).
  * physical modules poisoned: any import of a teacher / simulator / planner module raises (meta-path guard installed before any import)
  * field tracking: every row / inputs key the planners read is logged (dict subclass); allowlist checked
  * metadata invariance: the same plan from a row stripped to {root_id, domain, inputs}
  * relabelling: non-target object slots permuted -> identical X / Y / p11 readouts for mapped sequences and mapped cVAE proposals
  * witness vs ID order: Kendall tau between verified witness order and object index order (are IDs a hint?)
    python audit0.py run DOM N_ROOTS ARMS(comma) OUT.json"""
from __future__ import annotations

import importlib.abc, json, sys, time
from pathlib import Path

POISON = {"fin3d", "bd_3dt", "bd_3dt_plus", "bwlphys", "bxy_teacher", "teacher2d", "teacher_long", "physical2d", "physical3d", "evaluate_k45",
          "bd_2d", "motion", "geometry", "skill", "p15_search", "p16_common", "p15_retarget", "mujoco", "pybullet", "generate", "witness_v3", "mink", "cert"}


class _Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name.split(".")[0] in POISON:
            raise ImportError(f"PHYSICAL MODULE IMPORT BLOCKED: {name}")
        return None


sys.meta_path.insert(0, _Guard())
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]

LOG = {"row": set(), "inputs": set()}


class TD(dict):
    tag = "inputs"

    def __getitem__(self, k):
        LOG[self.tag].add(k); return super().__getitem__(k)

    def get(self, k, d=None):
        LOG[self.tag].add(k); return super().get(k, d)

    def __deepcopy__(self, memo):
        import copy
        return TD({k: copy.deepcopy(v, memo) for k, v in dict.items(self)})


class TR(TD):
    tag = "row"


ALLOW_ROW = {"root_id", "domain", "inputs"}
ALLOW_INPUTS = {"ids", "xy0", "cells0", "attrs", "tid", "goal", "goal_cell", "base", "ctx", "grid", "legal_cells", "q_ref", "cell_xy"}


def rows_for(dom, n):
    import common3 as K
    if dom == "2d":
        R = [json.loads(l) for l in open(K.O / "coh2d" / "rows.jsonl")]
    else:
        R = [json.loads(l) for l in open(K.C.R2 / "r23" / "roster_3d.jsonl")]
    return R[:int(n)]


def strip(r):
    return {"root_id": r["root_id"], "domain": r["domain"], "inputs": r["inputs"]}


def relabel(row, perm):
    """perm: new slot -> old slot (target kept at its slot)."""
    import copy
    r = copy.deepcopy(strip(row)); inp = r["inputs"]
    for k in ("ids", "xy0", "cells0", "attrs"):
        inp[k] = [row["inputs"][k][perm[i]] for i in range(len(perm))]
    inp["tid"] = perm.index(row["inputs"]["tid"])
    return r


def kendall(a, b):
    n, s = len(a), 0
    for i in range(n):
        for j in range(i + 1, n):
            s += 1 if (a[i] - a[j]) * (b[i] - b[j]) > 0 else -1
    return s / max(1, n * (n - 1) / 2)


def run(dom, n, arms, out):
    import random
    import planners as PL
    import rank as RK
    from models import Frozen
    fz = Frozen(dom)
    res = {"dom": dom, "arms": arms, "roots": [], "poisoned": sorted(POISON),
           "loaded": {"sampler_task_on": bool(fz.samp.m.task_on), "sampler_rule": fz.samp.rule, "scorer_vis_dim": int(getattr(fz.net, "vis_dim", -1)),
                      "manifest_config": fz.man["config"]}}
    for row in rows_for(dom, n):
        LOG["row"].clear(); LOG["inputs"].clear()
        tr = TR({**row, "inputs": TD(row["inputs"])})
        floor = RK.b0(fz, strip(row), PL.CFG["rule"])
        floor = {"seq": floor["seq"]} if floor["decision"] == "REPAIR" else None
        rec = {"root_id": row["root_id"], "N": len(row["inputs"]["ids"]), "arms": {}}
        for arm in arms:
            p1 = PL.plan(fz, tr, arm, floor)
            p2 = PL.plan(fz, strip(row), arm, floor)
            rec["arms"][arm] = {"decision": p1["decision"], "seq": p1["seq"], "partition": p1["partition"], "E": p1["E"], "kind": p1["kind"],
                                "wall_s": p1["wall_s"], "stop": p1["stop"], "mode": p1["arm"], "n_candidates": p1["n_candidates"],
                                "scores": (p1["info"] or {}).get("scores"), "per_size": (p1["info"] or {}).get("per_size"),
                                "metadata_invariant": (p1["seq"], p1["partition"], p1["E"]) == (p2["seq"], p2["partition"], p2["E"])}
            print(row["root_id"], arm, rec["arms"][arm]["mode"], p1["decision"], p1["partition"], p1["wall_s"], "inv", rec["arms"][arm]["metadata_invariant"], flush=True)
        rec["fields_row"], rec["fields_inputs"] = sorted(LOG["row"]), sorted(LOG["inputs"])
        rng = random.Random(row["root_id"])
        tid = row["inputs"]["tid"]
        others = [i for i in range(len(row["inputs"]["ids"])) if i != tid]
        sh = list(others); rng.shuffle(sh)
        perm = list(range(len(row["inputs"]["ids"])))
        for i, j in zip(others, sh):
            perm[i] = j
        inv = {old: new for new, old in enumerate(perm)}
        r2 = relabel(row, perm)
        el = [o for o in others][:4]
        D1 = fz.proposals(strip(row), el); fz.reset()
        D2 = fz.proposals(r2, [inv[o] for o in el]); fz.reset()
        seqs = [[[o, d]] for o in el for d in D1.get(o, [])][:6]
        seqs += [[[el[0], D1[el[0]][0]], [el[1], D1[el[1]][0]]]] if len(el) > 1 and D1.get(el[0]) and D1.get(el[1]) and D1[el[0]][0] != D1[el[1]][0] else []
        a = fz.score(strip(row), seqs); fz.reset()
        b = fz.score(r2, [[[inv[o], d] for o, d in s] for s in seqs]); fz.reset()
        rec["relabel"] = {"proposals_equal": all(sorted(D1[o]) == sorted(D2[inv[o]]) for o in el),
                          "max_abs_dpx": max([abs(x["px"] - y["px"]) for x, y in zip(a, b)] or [0]),
                          "max_abs_dp11": max([abs(x["p11"] - y["p11"]) for x, y in zip(a, b)] or [0])}
        res["roots"].append(rec)
    res["fields_row_union"] = sorted(set().union(*[set(r["fields_row"]) for r in res["roots"]]))
    res["fields_inputs_union"] = sorted(set().union(*[set(r["fields_inputs"]) for r in res["roots"]]))
    res["row_fields_outside_allowlist"] = sorted(set(res["fields_row_union"]) - ALLOW_ROW)
    res["input_fields_outside_allowlist"] = sorted(set(res["fields_inputs_union"]) - ALLOW_INPUTS)
    Path(out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ("loaded", "fields_row_union", "fields_inputs_union", "row_fields_outside_allowlist", "input_fields_outside_allowlist")}, default=str))


def witness_ids():
    """Kendall tau between verified witness order and object index order (2D cohort, 3D DEV_ORDER witnesses)."""
    import common3 as K
    C = K.C
    out = {}
    coh = json.loads((HERE.parent / "r3" / "reports" / "r31" / "DEV_ORDER_2D_cohort.json").read_text())["cohort"]
    R = {json.loads(l)["root_id"]: json.loads(l) for l in open(K.O / "coh2d" / "rows.jsonl")}
    out["2d"] = [kendall(list(range(len(L["witness"]))), [R[L["root_id"]]["inputs"]["ids"].index(o) for o, _ in L["witness"]]) for L in coh]
    ros = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / "roster_3d.jsonl")}
    t3 = []
    for rid, r in ros.items():
        rec = json.loads((C.NW / "k45/cohort/roots" / f"{rid}.json").read_text())
        t3.append(kendall(list(range(len(rec["k45"]["witness"]["order"]))), [r["inputs"]["ids"].index(o) for o, _ in rec["k45"]["witness"]["order"]]))
    out["3d"] = t3
    out["mean"] = {d: sum(v) / len(v) for d, v in out.items() if isinstance(v, list)}
    print(json.dumps(out["mean"]))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3], sys.argv[4].split(","), sys.argv[5])
    elif sys.argv[1] == "witness_ids":
        Path(sys.argv[2]).write_text(json.dumps(witness_ids(), indent=1))
