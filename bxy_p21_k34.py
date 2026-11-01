"""BXY-P21 K3/K4 learning design: the SAME six P17 arms (bxy_p17.ARMS / Model / batch_loss / SYM / GEO2 / inner rule grid), retrained on all
development corpora including the P20 K34 corpus; frozen before any P21 optimizer step.

Data: PMIN 197 + P15 28 + V21 87 (bxy_p17_data.build_all) + K34 (every collected, frozen P20 wave; same view contract, label-free inputs).
Folds: bxy_p17.folds procedure (5 family-grouped folds, outcome-free strata: PMIN design stratum, P15 K_intent, V21 mechanism x K_intent,
K34 family x K_intent), early-stop subset ~1/5 of each fold's training families. Training config = P11 TRAIN (unchanged).
Endpoints (frozen here): unconditional repair success on initially infeasible roots; availability-conditioned success (>= 1 verified
candidate); unnecessary repairs on feasible roots; per-stratum K1..K4 with n; strict order; omission; travel on matched successes.
K3/K4 hypotheses (targets, frozen): H1 D vs DIRECT-GEO on repairable K3+K4 roots: Delta >= 0.10, paired 95% CI lower > 0, unnecessary-repair
Delta <= +0.05 (all corpora feasible roots); H2 E vs DIRECT-GEO likewise; H3 D vs E (coupling) on the same subset; H4 D vs G strict-order
concordance on K3/K4 roots. Insufficient n is reported as such; no retry."""
from __future__ import annotations

import json
import time
from pathlib import Path

import bxy_p11 as P
import bxy_p17 as M
import bxy_p17_data as DATA
import bxy_p20_k34 as K34

OUT = Path("runs/approach_b/bxy_p21_v1")
ARMS = M.ARMS
INPUTS_K34 = OUT / "INPUTS_K34.pt"
LIMITS = {"aggregate_cpu_s": 65000, "per_run_cpu_s": 2000, "workers": 4, "wall_s": 30000, "runs": 90, "torch_threads": 1}
RESERVE = {"evaluation_cpu_s": 4000, "evaluation_wall_s": 1800}
HYPOTHESES = {"H1_D_vs_DIRECT_K34": ("D:XYQ-GEO-SYM", "A:DIRECT-GEO"), "H2_E_vs_DIRECT_K34": ("E:XY-UNC-SA-GEO-SYM", "A:DIRECT-GEO"),
              "H3_COUPLING_K34": ("D:XYQ-GEO-SYM", "E:XY-UNC-SA-GEO-SYM"), "H4_ORDER_K34": ("D:XYQ-GEO-SYM", "G:XYQ-GEO-SYM-ORDINV"),
              "P2_D_vs_DIRECT_ALL": ("D:XYQ-GEO-SYM", "A:DIRECT-GEO"), "P1_D_vs_BASE_ALL": ("D:XYQ-GEO-SYM", "B:XYQ-BASE")}
CRITERION = {"success_gain": 0.10, "ci_lower_gt": 0.0, "unnecessary_max_increase": 0.05,
             "populations": {"K34": "initially infeasible K34-corpus roots with verified K_catalogue in {3, 4} (repairable K3/K4 subset)",
                             "ALL_OB": "all outcome-blind corpora (P15, V21, K34)"}}


def k34_rows():
    out = []
    for w in sorted(K34.WAVES):
        d = K34.wdir(w)
        if not (d / "DESIGN.json").exists() or not (d / "SUMMARY.json").exists():
            continue
        D, R = json.loads((d / "DESIGN.json").read_text()), K34.roots_of(w)
        for k in D["root_order"]:
            out.append(("K34", w, k, R[k], D["roots"][k], d / "results" / k))
    return out


def build_all() -> list:
    import torch
    V = DATA.build_all()
    inp = torch.load(INPUTS_K34, weights_only=False)["roots"] if INPUTS_K34.exists() else {}
    for corpus, wave, k, rec, d, rdir in k34_rows():
        sv, lab, ev = DATA.view(corpus, wave, k, rec, d, rdir, inp[k])
        ev["mechanism"] = rec["construction"].get("family")
        ev["K_cert"] = rec["construction"].get("K_cert")
        V.append((sv, lab, ev))
    return V


def roster() -> list:
    return M.roster()


def design(V=None) -> dict:
    V = V if V is not None else build_all()
    fo = M.folds(V)
    keys = sorted(ev["key"] for _, _, ev in V)
    if sorted(k for f in fo["folds"] for k in f["heldout"]) != keys:
        raise RuntimeError("folds must hold out every development root exactly once")
    corp = {}
    for _, _, ev in V:
        c = corp.setdefault(ev["corpus"], {"roots": 0, "y0_0": 0, "families": set(), "vK": {}})
        c["roots"] += 1
        c["y0_0"] += ev["y0"] == 0
        c["families"].add(ev["family"])
        c["vK"][str(ev["verified_K"])] = c["vK"].get(str(ev["verified_K"]), 0) + 1
    corp = {k: dict(v, families=len(v["families"])) for k, v in corp.items()}
    return {"version": "BXY_P21_DESIGN_V1", "gate": "BXY-P21", "date": "2026-11-01", "p20_readiness": json.loads((K34.OUT / "READINESS.json").read_text()),
            "data": {"corpora": corp, "roots_sha256": P.PM.bc.sha(keys), "inputs_k34_sha256": P.sha(INPUTS_K34)},
            "arms": ARMS, "unchanged_from_P17": ["bxy_p17.Model", "bxy_p17.batch_loss", "bxy_p17.sym", "GEO2 (bxy_p17_data)", "P11 TRAIN", "inner rule GRID / U_MAX"],
            "folds": fo, "roster": roster(), "limits": LIMITS, "reserve_inside_limits": RESERVE, "hypotheses": HYPOTHESES, "criterion": CRITERION,
            "evaluation": {"primary": ["unconditional repair success (initially infeasible)", "availability-conditioned repair success"],
                           "secondary": ["unnecessary repairs (harmful / harmless)", "K1..K4 strata with n", "strict order (all / certified)", "omission sign",
                                         "travel on matched successes", "P18 pooled rule on OOF scores (read-only diagnostic)"],
                           "bootstrap": {"B": 10000, "unit": "family", "seed": 0}},
            "budget": {"per_run_expected_cpu_s": {a: 550.0 for a in ARMS}, "basis": "P17 median 401 CPU-s per run; ~45% more roots, larger early-stop set"}}


def freeze() -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "TRAINING_DESIGN_P21.json"
    txt = json.dumps(design(), indent=1, sort_keys=True, default=str)
    if f.exists() and f.read_text() != txt:
        raise FileExistsError("P21 design already frozen with different content")
    f.write_text(txt)
    return P.sha(f)


def frozen() -> dict:
    d = json.loads((OUT / "TRAINING_DESIGN_P21.json").read_text())
    if d["roster"] != roster():
        raise RuntimeError("P21 design drift")
    return d


arm_hooks = M.arm_hooks


if __name__ == "__main__":
    t = time.time()
    print(freeze(), time.time() - t)
