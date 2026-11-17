#!/usr/bin/env python3
"""Minimal baseline-adapter contract for the V3.4 benchmark (HARNESS TESTS ONLY -- these two policies are not research baselines).

A method plugs in either as a Python PolicyAdapter (load + predict_one on ONE public root) or as any program that reads public_roots.jsonl and
writes one prediction line per root (benchmark.py docstring).  Public roots carry only learner-visible inputs; K, labels, masks and teacher
certificates live in the private index and are never passed to an adapter.

    python baseline_adapters.py ADAPTER PUBLIC OUT        ADAPTER = always_abstain | legal_fixed_repair"""
import json, sys, time


class PolicyAdapter:
    name = "abstract"

    def load(self, bundle_dir=None, device="cpu", config=None):
        return self

    def predict_one(self, public_root) -> dict:
        raise NotImplementedError


class AlwaysAbstain(PolicyAdapter):
    name = "always_abstain"

    def predict_one(self, r):
        return {"decision": "ABSTAIN", "moves": []}


class LegalFixedRepair(PolicyAdapter):
    """Moves the lowest-index movable non-target object to the lowest legal free cell (a deterministic, statically legal 1-move REPAIR)."""
    name = "legal_fixed_repair"

    def predict_one(self, r):
        inp = r["inputs"]
        fixed = [bool(a[3]) for a in inp["attrs"]] if r["domain"] == "2d" else [False] * len(inp["ids"])
        occ = set(int(c) for c in inp["cells0"])
        cells = [c for c in sorted(int(c) for c in inp["legal_cells"]) if c not in occ and c != int(inp["goal_cell"])]
        mov = [i for i in range(len(inp["ids"])) if i != inp["tid"] and not fixed[i]]
        if not mov or not cells:
            return {"decision": "ABSTAIN", "moves": []}
        return {"decision": "REPAIR", "moves": [{"object_id": inp["ids"][mov[0]], "object_index": mov[0], "destination_cell": cells[0]}]}


ADAPTERS = {a.name: a for a in (AlwaysAbstain, LegalFixedRepair)}


def run(adapter, public, out):
    pol = ADAPTERS[adapter]().load()
    with open(out, "w") as f:
        for l in open(public):
            r = json.loads(l)
            t0 = time.time()
            p = pol.predict_one(r)
            f.write(json.dumps({"root_id": r["root_id"], "domain": r["domain"], **p, "method": adapter, "harness_test_only": True,
                                "timing_s": {"total": round(time.time() - t0, 6)}}) + "\n")


if __name__ == "__main__":
    run(*sys.argv[1:4])
