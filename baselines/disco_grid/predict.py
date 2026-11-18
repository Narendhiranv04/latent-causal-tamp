#!/usr/bin/env python3
"""DISCO-Grid one-shot inference for the common Approach B benchmark harness (approach_b_final/benchmark.py contract).

Input: PUBLIC rows {root_id, domain, inputs} only (no split, K, masks, labels or teacher output is read).  Output: one prediction per
root with decision REPAIR / NOOP / ABSTAIN, exact ordered object ids + object indices + destination cells, model/seed/config hashes,
timing and network-call counts; zero physical / planner calls during selection (strict open-loop O0).  Seal with
`benchmark.py seal` BEFORE any teacher call; verify with `benchmark.py queries/teach/evaluate`.

    predict.py --model-dir DIR --input PUBLIC.jsonl --output PRED.jsonl [--variant policy_value|policy_only] [--seed 0] [--B 16]
               [--rule RULE.json] [--device cpu]
DIR holds policy.pt (+ value.pt for policy_value) and scalers inside the policy checkpoint."""
import argparse, hashlib, json, resource, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import distill as DS  # noqa: E402
import evaluate as EV  # noqa: E402
import policy as P  # noqa: E402


STAGE2_RULE = dict(noop_q_gate=.55, stop_q_margin=.02, abstain_eta=0., policy_stop_thresh=.45, stop_q_min=.35, noop_pol_gate=.5)
B_DEFAULT = {"2d": 16, "3d": 12}                     # stage-2 frozen evaluation settings (prepare_evaluation.py RULE / B)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(a):
    md = Path(a.model_dir)
    pol, pck = P.load_policy_checkpoint(md / "policy.pt", device=a.device)
    val = DS.load_value_checkpoint(md / "value.pt", device=a.device)[0] if a.variant == "policy_value" else None
    if pol.observation_schema != P.O0:
        raise SystemExit("primary benchmark inference is O0 strict open-loop; O1 is closed-loop only")
    rule = json.loads(Path(a.rule).read_text()) if a.rule else dict(STAGE2_RULE)
    model_hash = hashlib.sha256((sha(md / "policy.pt") + (sha(md / "value.pt") if val is not None else "") + json.dumps(rule, sort_keys=True)
                                 ).encode()).hexdigest()
    rows = [json.loads(l) for l in open(a.input)]
    done = {json.loads(l)["root_id"] for l in open(a.output)} if Path(a.output).exists() else set()
    wraps = {}
    with open(a.output, "a") as f:
        for r in rows:
            if r["root_id"] in done:
                continue
            dom = r["domain"].lower()
            if dom not in wraps:
                wraps[dom] = P.PolicyProposalWrapper(dom, pol, pck["scalers"], device=a.device, mode="distilled", value_model=val)
            pub = {"root_id": r["root_id"], "inputs": r["inputs"], "split": None, "K_legacy": None, "masks": None}
            t0 = time.time()
            B = a.B or B_DEFAULT[dom]
            o = EV.predict_open_loop_sequence(pub, dom, wraps[dom], B_test=B, use_value=val is not None, rule=rule, seed=a.seed)
            ids = r["inputs"]["ids"]
            dec = o["status"]
            moves = [{"object_id": ids[i], "object_index": int(i), "destination_cell": int(c)} for i, c in (o["seq"] or [])] if dec == "REPAIR" else []
            f.write(json.dumps({"root_id": r["root_id"], "domain": dom, "decision": dec, "moves": moves,
                                "method": f"disco_grid_O0_{a.variant}", "model_hash": model_hash, "seed": a.seed, "B_test": B,
                                "rule": rule, "inference_mode": "open_loop_one_shot", "planner_calls_during_selection": 0,
                                "policy_calls": o["policy_calls"], "value_calls": o["value_calls"],
                                "timing_s": {"total": round(time.time() - t0, 5)}, "device": a.device,
                                "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                                "step_traces": o["step_traces"]}) + "\n")
            f.flush()
    print(json.dumps({"predictions": a.output, "n": sum(1 for _ in open(a.output)), "model_hash": model_hash}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True); ap.add_argument("--input", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--variant", default="policy_value", choices=["policy_value", "policy_only"])
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--B", type=int, default=0)
    ap.add_argument("--rule"); ap.add_argument("--device", default="cpu")
    main(ap.parse_args())
