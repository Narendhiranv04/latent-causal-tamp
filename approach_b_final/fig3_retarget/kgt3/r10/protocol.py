#!/usr/bin/env python3
"""Assemble R10_PROTOCOL_FREEZE.json from sealed artefacts (all hashes computed here).  Run on gvlab2 BEFORE any new TEST outcome is read.
    python3 protocol.py OUT.json"""
import glob, hashlib, json, sys, time
from pathlib import Path

W = Path("/home/projects/long-horizon/naren_workspace/r10")
REL = W / "release/LEGOLAS_FINAL_v1"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


SHORT_ARMS = {
    "primary": ["FINAL"],
    "reference_qualified": ["B0"],
    "scoring": ["UNCOUPLED", "ORDINV", "DIRECT", "YONLY", "YONLY_CAL"],
    "diagnostic_rank_only": ["FINAL_RANK", "YONLY_RANK"],
    "placement": ["UNIFORM4", "TASKFM", "NOTASK"],
    "selection": ["M1", "C1"],
    "generative": ["CR", "CRXY", "FC4"],
    "representation": ["REP_A1", "REP_M1", "REP_G0"],
    "seeds": ["FINAL_X<other two G1 seeds>", "SEED0", "SEED1", "SEED2"]}
COMP_RUNS = {
    "main": ["B0", "H3", "FLAT-INSERT", "REC-ORDERED", "GA"],
    "g0": ["REC-ORDERED", "GA"],
    "yonly": ["GA-YPURE", "GA-YONLY (labelled: Y-selected endpoints + X-DP ordering)"],
    "notask": ["H3", "REC-ORDERED", "GA"],
    "x<s> (alternate feasibility bundles)": ["H3", "REC-ORDERED", "GA"],
    "seed<s> (full seed-matched bundles)": ["H3", "REC-ORDERED", "GA"],
    "cr": ["REC-ORDERED (prop CR8)", "GA (prop CR4)"],
    "propmatch": ["REC-ORDERED (prop S1)", "GA (prop ANC64)"]}


def main(out):
    mf = json.loads((W / "R10_MODEL_FREEZE.json").read_text()) if (W / "R10_MODEL_FREEZE.json").exists() else None
    P = {
        "version": "R10_PROTOCOL_FREEZE_V1", "frozen_utc": time.strftime("%FT%TZ", time.gmtime()), "host": "gvlab2 (all computation)",
        "release": {"id": "LEGOLAS_FINAL_v1", "seal_sha256": json.loads((REL / "R10_DATASET_SEAL.json").read_text())["release_sha256"]},
        "models": {"freeze_file_sha256": sha(W / "R10_MODEL_FREEZE.json") if mf else None, "summary": mf and mf.get("summary")},
        "rosters": {
            "r10u_short": json.loads((W / "k3eval/ROSTER_r10u.json").read_text()),
            "bench_comp_3d": {"public": str(W / "comp/PUBLIC_bench_comp_3d.jsonl"), "public_sha256": sha(W / "comp/PUBLIC_bench_comp_3d.jsonl") if (W / "comp/PUBLIC_bench_comp_3d.jsonl").exists() else None,
                              "source": "R8B sealed roster (99; 68 L_ref 4 / 31 L_ref 5), fixed previously evaluated benchmark"},
            "test_feas_3d": {"protocol": "r10/FEAS_PROTOCOL.json (frozen before the first generation job)", "annex": "sealed on completion; predictions sealed before labels are joined"},
            "val_calibration": {f"public_val10_{d}": sha(W / f"k3eval/runs/public/public_val10_{d}.jsonl") for d in ("2d", "3d")}},
        "short_horizon": {
            "arms": SHORT_ARMS, "rule": {"noop_gate": 0.5, "eta": 0.3, "M": 4, "proposals": "S1 top-4", "search": "exhaustive ordered K <= 3"},
            "yonly": "p11 := pY(endpoint); identical pool / enumeration / rule; deterministic X-independent tie-break key(cost, m, D, canonical seq)",
            "yonly_cal": "VAL-only operating point: on the canonical VAL roster, noop gate g and admission eta for pY chosen so that Y-only's NOOP and "
                         "ABSTAIN rates equal FINAL's VAL NOOP and ABSTAIN rates (quantile matching of p_noop and best-endpoint pY); frozen before TEST",
            "rank_only": "corrective roots only: top-ranked nonempty sequence of the same pool (FINAL by p11, YONLY by pY); no stop rule",
            "verification": "ablations_k3/verify.py seal -> teach (union, dedup) -> evaluate; unchanged finalized teacher (evaluate._verify_job, V3.4 benchmark contract); "
                            "exact cache reuse only after sealing, keyed by root file + ordered sequence; UNKNOWN stays UNKNOWN; no retries",
            "metrics": {"task": "K1-K3 roots: verified X=1 and Y=1 (intent-to-evaluate; unverified = not verified)", "noop": "K0 roots: NOOP",
                        "abstain": "NONE roots: ABSTAIN", "strata": "K1 / K2 / K3, K1+K2, executed length, X/Y/joint", "denominators": "fixed per track"},
            "tracks": {"primary": "TEST_SHORT (held out from all training and selection; historically outcome-exposed, not blind)",
                       "supplementary": "BENCH_SHORT (V3.4, exposed) and the pooled descriptive union (canonical successes / eligible denominators)"}},
        "baselines_3d": {"analytical": "E-M4M, MO-SeGMan, MS-MCTS: paper config, seed 0, 300 CPU-s budget (+ exact 60 s cut of the same runs); sanitized raw scenes",
                         "learned": "DISCO-Grid R1_ALL_succonly s0-s2, NOR-Grid full_s0 (frozen weights)", "reap": "teammate SHELF66V3 adaptation of REAP v1.0 (d2ba23d + patch), 12 h model, faithful protocol",
                         "primary_roster": "TEST_SHORT_3D"},
        "feasibility_3d": {"methods": ["PIGINet (no image)", "GRN", "SCNet", "ours: final stage-B Y (p_noop of the initial scene)"], "threshold": 0.5,
                           "metrics": ["TP/FP/TN/FN", "TPR/TNR (Wilson)", "AUROC/AUPRC (family bootstrap)", "calibration (ECE, 10 bins)", "paired differences"],
                           "unknown": "UNKNOWN labels excluded from primary, reported separately"},
        "composition_3d": {"runs": COMP_RUNS, "policy": {"selection": "S0", "admission": "A1 margin 0.10", "REC": "ANC64", "GA": "S1 top-4", "H": 5, "has_multi": True,
                                                         "deadline_s": 180, "deadline_scope": "end-to-end incl. floor and selection", "floor": "same-model H<=3 (R6_FLOOR=final)"},
                           "verification": "X_CHUNKED + endpoint Y + continuous replay (physical3d.py work, unchanged); one sealed plan per root and arm; no retries",
                           "timing_lane": "one composition run at a time, 4 concurrent shards x 2 dedicated CPUs (36-43), exclusive GPU; other CPU jobs on disjoint cores; host load logged"},
        "statistics": {"paired": "root-level pairing, exact two-sided sign/McNemar test", "ci": "family-cluster bootstrap 95% (2,000 resamples, seed 0)",
                       "multiplicity": "Holm within families: short ablations (per domain), Y-only, CR/CRXY/FC4, baselines (3D), native composition, long supervision (G0), task conditioning, seeds",
                       "rule": "nonsignificance is not equivalence; seeds are not independent roots"},
        "budget": {"cpu_core_h": 500, "gpu_process_h": 40, "priorities": ["integrity", "clean training", "primary short", "native composition", "independent feasibility", "Y-only", "secondary controls"]},
        "code": {f: sha(f) for f in sorted(glob.glob(str(W / "code/approach_b_final/fig3_retarget/kgt3/r10/*.py"))) +
                 [str(W / "code/approach_b_final/fig3_retarget/kgt3/" + x) for x in ("r6.py", "planners.py", "learn.py", "xlearn.py", "r7.py", "r8a.py")] +
                 [str(W / "code/approach_b_final/fig3_retarget/models.py"), str(W / "code/approach_b_final/ablations_k3/verify.py"), str(W / "code/approach_b_final/benchmark.py")]}}
    Path(out).write_text(json.dumps(P, indent=1))
    print(hashlib.sha256(Path(out).read_bytes()).hexdigest())


if __name__ == "__main__":
    main(sys.argv[1])
