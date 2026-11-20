#!/usr/bin/env python3
"""FINAL_ABLATION_PROTOCOL_LOCK.json: registered arms, specs, checkpoint SHAs, rules and the SEALED prediction hashes of SPLIT, written before any
teacher call on SPLIT; plus the G3 fairness invariant (scorer arms share FULL's exact per-root candidate pool hashes).
    python lock.py SPLIT ARM...      (refuses to overwrite an existing lock of SPLIT)"""
import json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import benchmark as BM  # noqa: E402
import run as RN  # noqa: E402

K3 = Path(os.environ["K3"])
SCORER_ARMS = ("FULL_", "E_", "G_", "DIRECT_", "DREFIT_")


def main(split, arms):
    out = K3 / "runs/manifests" / f"FINAL_ABLATION_PROTOCOL_LOCK_{split}.json"
    if out.exists():
        raise SystemExit(f"REFUSED: {out} exists")
    L = {"split": split, "registered_utc": time.strftime("%FT%TZ", time.gmtime()), "rule": RN.RULE,
         "proposal": {"cvae": "S1: 64 prior draws, MC marginal, top-6 per object (M4 prefix), per-root CUDA generator seed 0",
                      "taskfm": "64 endpoints x 32 Euler steps, nearest legal centre, histogram top-4, ties by mean squared distance then cell index, seed 0",
                      "uniform4": "numpy default_rng(sha256('UNIFORM4|r|root|obj')) choice of 4 distinct legal cells without replacement",
                      "M1": "frozen cVAE top-1 per object, all legal K1-K3 sequences over those", "C1": "label-blind: K uniform over lengths with >=1 legal "
                      "sequence in the M4 pool, then a uniform legal sequence of that length (rng sha256('C1|r|root')); D scored once + no-op"},
         "construction": "every statically legal ordered K1-K3 sequence over the per-object lists (exhaustive.stream), no cap, chunk 8192",
         "statistics": {"bootstrap": 2000, "seed": 0, "cluster": "layout_root_id lineage", "paired": "identical roots, both decided"},
         "arms": {}}
    pools = {}
    for arm in arms:
        for dom in ("2d", "3d"):
            sp = RN.spec(arm, dom)
            pred = K3 / "runs/predictions" / arm / f"{split}_{dom}.jsonl"
            seal = Path(str(pred) + ".SEAL.json")
            assert seal.exists() and json.loads(seal.read_text())["sha256"] == BM.sha(pred), f"{arm} {dom}: not sealed"
            rows = BM.jl(pred)
            kind, arg = sp["sampler"]
            L["arms"][f"{arm}|{dom}"] = {"scorer": str(sp["scorer"]), "scorer_sha256": BM.sha(sp["scorer"]), "sampler": kind,
                                          "sampler_sha256": BM.sha(arg) if kind in ("cvae", "taskfm") else None, "M": sp["M"], "c1_seed": sp["c1"],
                                          "predictions_sha256": BM.sha(pred), "n": len(rows),
                                          "decisions": {k: sum(r["decision"] == k for r in rows) for k in ("REPAIR", "NOOP", "ABSTAIN")}}
            if arm.startswith(SCORER_ARMS):
                pools[(arm, dom)] = {r["root_id"]: r["pool_hash"] for r in rows}
    ref = {d: pools.get(("FULL_s0", d)) for d in ("2d", "3d")}
    L["G3_scorer_arms_share_FULL_pool"] = {f"{a}|{d}": (p == ref[d]) for (a, d), p in pools.items()} if all(ref.values()) else "FULL_s0 missing"
    out.write_text(json.dumps(L, indent=1, sort_keys=True) + "\n")
    os.chmod(out, 0o444)
    bad = [k for k, v in L["G3_scorer_arms_share_FULL_pool"].items() if v is not True] if isinstance(L["G3_scorer_arms_share_FULL_pool"], dict) else ["FULL_s0"]
    print(json.dumps({"lock": str(out), "arms": len(L["arms"]), "G3_failures": bad}))
    return not bad


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1], sys.argv[2:]) else 1)
