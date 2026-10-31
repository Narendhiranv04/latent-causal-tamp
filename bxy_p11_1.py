"""BXY-P11.1 amendment: a minimal adapter over the frozen P11 design (bxy_p11 / bxy_p11_prereg and TRAINING_DESIGN 24ffa822 are NOT edited).
Three prospective corrections, frozen before any real-data training:
  A  primary selection = pure cost minimization over every F1-admissible candidate (the no-op is an ordinary candidate); the unconditional
     P(Y0) >= 0.5 no-op gate survives only as the labelled secondary ablation GATED.
  B  cross-fit claims: lambda* is chosen on val21 and val21 roots reappear as cross-fit held-out roots, so the PRIMARY development comparison
     is out-of-fold on the 176 original TRAIN roots only; all-197 OOF is supplementary / exploratory, SPLIT val21 descriptive, and the
     definitive confirmation is the future independent outcome-blind cohort (not part of P12).
  C  travel: evaluation-only decomposition of the combined travel effect into auxiliary travel TRAINING (gamma = 0 on both sides) and
     travel-aware RANKING (same checkpoint, gamma 0.05 vs 0). No training run is added, nothing is tuned."""
from __future__ import annotations

import copy
import json
import subprocess as sp
import sys
import time
from pathlib import Path

import bxy_data as bd
import bxy_p11 as P
import bxy_pmin as PM

OUT = Path("runs/approach_b/bxy_p11_1_v1")
P11_DESIGN = P.OUT / "TRAINING_DESIGN.json"
P11_DESIGN_SHA = "24ffa822ac57c1ff33b0c20b52cbd7cbebfa975df74db1e1f14f8f2fec5782cf"
ENTRY = ("bxy_p11_1.py",)
PRIMARY = {"noop_gate": None, "eta": 0.0, "alpha": 0.1, "beta": 0.0, "gamma": 0.05}
GATED = dict(P.RULE)                                                      # secondary ablation: the superseded P11 rule (no-op gate 0.5)
GAMMA = {"XY-quadratic": 0.05, "XY-uncoupled": 0.05, "XY-uncoupled-SA": 0.05, "XY-quadratic-noJ": 0.0, "DIRECT": 0.0, "LB": 0.0}
EVAL_SETS = {"PRIMARY_DEV": "CROSSFIT out-of-fold predictions on the 176 original TRAIN roots (never used for lambda* selection)",
             "SUPPLEMENTARY_DEV": "CROSSFIT out-of-fold predictions on all 197 roots (exploratory: val21 roots also chose lambda*)",
             "DESCRIPTIVE_VAL": "SPLIT checkpoints (train176 / early-stop val21) on the 21 VAL roots (LB comparable only here)",
             "CONFIRMATORY": "future independent outcome-blind cohort, evaluated once; NOT part of P12"}
TRAVEL_CONTRASTS = [
    {"id": "TRAVEL_TRAINING", "a": ("XY-quadratic", 0.0), "b": ("XY-quadratic-noJ", 0.0),
     "meaning": "auxiliary travel-training effect: lambda* vs 0 with identical (travel-blind) selection"},
    {"id": "TRAVEL_RANKING", "a": ("XY-quadratic", 0.05), "b": ("XY-quadratic", 0.0),
     "meaning": "travel-aware selection effect: the SAME travel-trained checkpoints, gamma 0.05 vs 0 (probabilities identical by construction)"},
    {"id": "TRAVEL_COMBINED", "a": ("XY-quadratic", 0.05), "b": ("XY-quadratic-noJ", 0.0),
     "meaning": "combined effect (training + ranking), the superseded P11 travel ablation; explicitly labelled combined"}]


def rule(arm, gamma=None, base=PRIMARY) -> dict:
    """The selection rule of an arm: the frozen weights with the arm's gamma (or an explicit evaluation-only gamma)."""
    return dict(base, gamma=GAMMA[arm] if gamma is None else gamma)


def choose(rows, r=PRIMARY):
    """F1 screen, no gate, eta = 0 (never abstains), argmin -log p + 0.1 m + 0 C_d + gamma J_hat, ties (m, C_d, signature); the frozen
    P11 implementation with the gate switched off (its cost and tie order are unchanged)."""
    if r.get("noop_gate") is not None:
        raise ValueError("the primary rule has no no-op gate; use GATED explicitly for the secondary ablation")
    return P.choose(rows, r)


def choose_gated(rows, arm):
    return P.choose(rows, rule(arm, base=GATED))


def eval_roots(D, R) -> dict:
    """Root sets of the four evaluation tiers (the confirmatory cohort does not exist yet)."""
    split = {s: sorted(k for k in D["root_order"] if bd.split_of(R[k]) == s) for s in ("train", "val")}
    return {"PRIMARY_DEV": split["train"], "SUPPLEMENTARY_DEV": sorted(split["train"] + split["val"]), "DESCRIPTIVE_VAL": split["val"], "CONFIRMATORY": []}


# ------------------------------------------------------------------ successor design and lock
def design() -> dict:
    if P.sha(P11_DESIGN) != P11_DESIGN_SHA:
        raise RuntimeError("P11 design hash drift")
    base = json.loads(P11_DESIGN.read_text())
    sc, D, R, _ = P.load()
    if json.loads(json.dumps(P.roster(D, R))) != base["roster"] or json.loads(json.dumps(P.folds(D, R))) != base["folds"]:
        raise RuntimeError("roster / folds differ from the frozen P11 design")
    roots = eval_roots(D, R)
    new = copy.deepcopy(base)
    sel, ev = new["selection"], new["evaluation"]
    new.update(version="BXY_P11_1_TRAINING_DESIGN_V2", gate="BXY-P11.1-AMENDMENT", date="2026-10-31",
               parent={"design": str(P11_DESIGN), "design_sha256": P11_DESIGN_SHA, "lock_sha256": P.sha(P.OUT / "TRAINING_LOCK.json")})
    new["selection"] = {
        "primary": PRIMARY, "gamma_by_arm": GAMMA, "steps": ["F1 screen (zero-move always admissible)", "every admissible candidate, the no-op included, "
                        "gets C = -log p_succ + 0.1 m + 0 C_d + gamma J_hat (no-op: p = P(Y0=1), m = 0, J_hat = J(empty))", "eta = 0: never abstain",
                        "argmin C; ties by (m, C_d, canonical signature)"],
        "secondary_ablations": {"GATED_NOOP": GATED | {"note": "superseded P11 rule: zero-move whenever P(Y0=1) >= 0.5, report only"},
                                "ABSTAINING": PRIMARY | {"eta": 0.5}, "LEXICOGRAPHIC_LENGTH_FIRST": PRIMARY | {"alpha": 100.0},
                                "sensitivity_grid_report_only": sel["sensitivity_grid_report_only"]},
        "not_tuned": sel["not_tuned"], "cost": sel["cost"], "selection_vs_training_weights": sel["selection_vs_training_weights"],
        "superseded_p11": sel}
    new["evaluation"] = ev | {
        "tiers": EVAL_SETS, "tier_roots": {k: len(v) for k, v in roots.items()},
        "development_primary": EVAL_SETS["PRIMARY_DEV"] + "; per-root metrics averaged over the 3 seeds, paired root-cluster bootstrap (B = 10000)",
        "development_supplementary": EVAL_SETS["SUPPLEMENTARY_DEV"], "development_split": EVAL_SETS["DESCRIPTIVE_VAL"],
        "confirmatory": EVAL_SETS["CONFIRMATORY"] + " (frozen SPLIT checkpoints)",
        "claims": "cross-fit gains are development evidence, never final generalization results",
        "coupling_decision": ev["coupling_decision"] | {"evaluated_on": "PRIMARY_DEV (train176 OOF); SUPPLEMENTARY_DEV and DESCRIPTIVE_VAL reported alongside",
                                                        "selection_metric_rule": "PRIMARY rule with each arm's gamma"},
        "travel_contrasts": TRAVEL_CONTRASTS,
        "travel_decision": {"TRAVEL_COMBINED": ev["travel_decision"] + " [combined training + ranking effect]",
                            "TRAVEL_TRAINING": "auxiliary training effect, both sides gamma = 0: Delta success logloss CI upper < 0.02 and Delta success "
                                               "on infeasible roots CI lower > -0.05 (descriptive: J of successful choices with paired CI)",
                            "TRAVEL_RANKING": "same checkpoints: Delta witnessed J of successful choices CI upper < 0 and Delta success on infeasible roots "
                                              "CI lower > -0.05 (probabilities identical by construction)",
                            "metrics": "success logloss (root), success on initially infeasible roots, witnessed J_total of successful choices "
                                       "(paired where both succeed), on PRIMARY_DEV"},
        "direct_decision": ev["direct_decision"] + " (on PRIMARY_DEV, PRIMARY rule)",
        "superseded_p11": {k: ev[k] for k in ("development_primary", "development_split", "confirmatory", "travel_decision")}}
    new["amendments"] = {
        "A_selection": "removed the unconditional no-op gate from the primary rule (it overrode a better-cost correction whenever P(Y0) >= 0.5); "
                       "kept as GATED_NOOP secondary ablation",
        "B_crossfit_claims": "PRIMARY development = OOF on train176; all-197 OOF supplementary; val21 descriptive; confirmation = future cohort. "
                             "Folds and the 108-run roster are unchanged",
        "C_travel": "evaluation-only decomposition (training / ranking / combined); no added training run",
        "unchanged": ["evidence", "custody", "interface", "objective", "arms", "training", "roster", "folds", "budget", "fresh_cohort_protocol"],
        "timing": "frozen before any real-data optimizer step"}
    new["limitations"] = base["limitations"] + [
        "P11.1: the no-op gate was removed after the P11 freeze but before any training or outcome inspection (prospective correction)"]
    new["stop"] = "P11.1 performs no training, tuning, teacher query, scene generation or test evaluation"
    return new


def freeze() -> dict:
    D = design()
    text = json.dumps(D, indent=1, sort_keys=True, default=str)
    f = OUT / "TRAINING_DESIGN_P11_1.json"
    if f.exists() and f.read_text() != text:
        raise FileExistsError(f"{f} is frozen and differs from the recomputed design")
    OUT.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    lock = {"design_sha256": P.sha(f), "parent_design_sha256": P11_DESIGN_SHA, "parent_lock_sha256": D["parent"]["lock_sha256"],
            "evidence_sha256": P.EVIDENCE, "sources": PM.sources(ENTRY), "git_head_at_freeze": PM.git("rev-parse", "HEAD"), "frozen_at": time.time(),
            "authorized": False, "note": "authorized stays false; training runs only under a separate committed authorization manifest"}
    lf = OUT / "TRAINING_LOCK_P11_1.json"
    if lf.exists():
        old = json.loads(lf.read_text())
        drop = ("frozen_at", "git_head_at_freeze")
        if {k: v for k, v in old.items() if k not in drop} != {k: v for k, v in lock.items() if k not in drop}:
            raise FileExistsError(f"{lf} is frozen and differs")
        return old
    lf.write_text(json.dumps(lock, indent=1, sort_keys=True))
    return lock


def assert_frozen(check_git=True) -> dict:
    """Launch guard: successor design == its lock, parent P11 design / lock untouched, evidence, no source drift, committed and clean."""
    import bxy_p11_prereg as Q
    lock, bad = json.loads((OUT / "TRAINING_LOCK_P11_1.json").read_text()), []
    Q.assert_frozen(check_git=check_git)
    if P.sha(OUT / "TRAINING_DESIGN_P11_1.json") != lock["design_sha256"]:
        bad.append("successor design differs from its lock")
    if P.sha(P11_DESIGN) != lock["parent_design_sha256"] or P.sha(P.OUT / "TRAINING_LOCK.json") != lock["parent_lock_sha256"]:
        bad.append("parent P11 design / lock changed")
    now = PM.sources(ENTRY)
    bad += [f"source drift: {f}" for f in sorted(set(now) | set(lock["sources"])) if now.get(f) != lock["sources"].get(f)]
    if check_git:
        for f in ("TRAINING_DESIGN_P11_1.json", "TRAINING_LOCK_P11_1.json"):
            p = str(OUT / f)
            if sp.run(["git", "ls-files", "--error-unmatch", p], capture_output=True).returncode or sp.run(["git", "diff", "--quiet", "HEAD", "--", p]).returncode:
                bad.append(f"{f} not committed / not clean")
    if bad:
        raise RuntimeError("; ".join(bad))
    return lock


if __name__ == "__main__":
    if sys.argv[1] == "freeze":
        print(json.dumps({k: v for k, v in freeze().items() if k != "sources"}, indent=1))
