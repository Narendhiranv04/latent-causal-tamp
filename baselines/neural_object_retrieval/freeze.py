#!/usr/bin/env python3
"""NOR-Grid P6 freeze manifest: every hash needed to re-run the frozen VALIDATION-selected configuration on a later common held-out
cohort WITHOUT retuning (primary = full_s0, rule NOR_RULE_V1, tau 0.5, calibrated T), plus the exact protocol commands.
    freeze.py OUT.json"""
import glob, hashlib, json, subprocess, sys
from pathlib import Path

S = Path.home() / "sorc_grid"
H = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(out):
    git = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True, cwd=H).stdout.strip()  # noqa: E731
    m = {"method": "NOR-Grid (adapted Ren & Qureshi ICRA 2024, arXiv:2402.06976)", "commit": git("git rev-parse HEAD"),
         "branch": git("git rev-parse --abbrev-ref HEAD"), "primary": "models/<dom>/full_s0, policy variant 'full', rule NOR_RULE_V1 (tau 0.5)",
         "code_sha256": {f: sha(H / f) for f in ("graph.py", "networks.py", "policy.py", "homotopy.py", "samples.py", "train.py", "nor_data.py")},
         "models": {}, "labels": {}, "tensors": {}, "seals": {}, "valsub_registration": sha(S / "eval/VALSUB_REGISTRATION.json")}
    for d in ("2d", "3d"):
        for v in ("full_s0", "full_s1", "full_s2", "nogoal_s0"):
            M = S / "models" / d / v
            m["models"][f"{d}/{v}"] = {**{f: sha(M / f) for f in ("os.pt", "rp.pt", "st.pt")}, "calibration": json.loads((M / "calibration.json").read_text())}
        m["labels"][d] = {"file": str(S / f"labels/homotopy_{d}_train.jsonl"), "sha256": sha(S / f"labels/homotopy_{d}_train.jsonl")}
        for k in ("full", "nogoal"):
            m["tensors"][f"{d}/{k}"] = sha(S / f"tensors/{k}_{d}.npz")
    for f in sorted(glob.glob(str(S / "eval/pred/*.SEAL.json"))):
        m["seals"][Path(f).name] = json.loads(Path(f).read_text())["sha256"]
    m["held_out_protocol"] = [
        "python3 approach_b_final/benchmark.py public PUBLIC.jsonl --index PRIVATE_INDEX.jsonl      # learner-visible rows only",
        "python3 baselines/neural_object_retrieval/policy.py predict PUBLIC.jsonl ~/sorc_grid/models/<dom>/full_s0 PRED.jsonl full cuda",
        "python3 approach_b_final/benchmark.py validate --public PUBLIC.jsonl --predictions PRED.jsonl",
        "python3 approach_b_final/benchmark.py seal PRED.jsonl --public PUBLIC.jsonl                 # BEFORE any teacher call",
        "python3 approach_b_final/benchmark.py queries/teach/evaluate/summarize ...                  # unchanged X/Y teachers",
        "No retraining, recalibration, threshold or variant change after seeing held-out outcomes."]
    m["not_accessed"] = "V3.4 1,120-root cohort expansion and historical TEST outcomes were never read"
    Path(out).write_text(json.dumps(m, indent=1))
    print(json.dumps({"commit": m["commit"], "n_models": len(m["models"]), "n_seals": len(m["seals"])}))


if __name__ == "__main__":
    main(sys.argv[1])
