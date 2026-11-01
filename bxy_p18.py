"""BXY-P18 final research readiness: honest model freeze, a NEW outcome-blind V2.1 confirmatory-cohort plan (never generated), the frozen
one-shot confirmatory analysis, the compliance checklist and the go / no-go decision. No teacher query, no training, no cohort.

Model freeze. A frozen predictor = the 15 P17 cross-fit checkpoints (5 folds x 3 seeds) of an arm, scored as an ensemble (mean of the 15
p_succ / P(Y0) per candidate), with ONE selection rule chosen by bxy_p17.choose_rule on the early-stop predictions pooled over every fold
and seed of that arm (development data only). Frozen: the candidate (primary hypothesis arm D unless the P17 decision says otherwise), the
challenger, matched DIRECT and the matched uncoupled control; checkpoint sha256s, design / data / input / map hashes, feature and output
semantics. If no arm met the development gate the freeze is labelled a NEGATIVE result plus the best diagnostic model, never 'final'.
Cohort plan. Namespace bxyg21confirm (BXY_GEN_V21B construction, new seeds); the P15 CONFIRM_PLAN.json stays immutable and is superseded,
not edited. Composition and size come from the P16 development realization only (no model output)."""
from __future__ import annotations

import collections
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

import bxy_p16 as G
import bxy_p17 as M

OUT = Path("runs/approach_b/bxy_p18_v1")
CONFIRM_NS = "bxyg21confirm"
FROZEN_ARMS = ("D:XYQ-GEO-SYM", "A:DIRECT-GEO", "E:XY-UNC-SA-GEO-SYM", "C:XYQ-GEO-CON", "B:XYQ-BASE", "G:XYQ-GEO-SYM-ORDINV")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pooled_rule(arm, C) -> dict:
    """The single confirmatory rule of an arm: choose_rule on the early-stop predictions of all its folds and seeds."""
    rows = []
    for fo in range(M.FOLDS):
        for s in M.SEEDS:
            for k, pr in C["es"].get((arm, fo, s), {}).items():
                ev = C["by"][k][2]
                if ev["y0"] is not None:
                    rows.append((k, ev["y0"], pr["cands"], {c["sig"]: c["success"] for c in ev["cands"]}))
    return M.choose_rule(arm, rows)


def freeze_models(ev, C) -> dict:
    """FROZEN_MODELS.json content (checkpoint hashes; rules; decision label)."""
    F = C["F"]
    arms = {}
    for arm in FROZEN_ARMS:
        runs = sorted(r for r, v in F.items() if v["spec"]["arm"] == arm)
        arms[arm] = {"runs": runs, "complete": len(runs) == M.FOLDS * len(M.SEEDS),
                     "checkpoints": {r: F[r]["files"].get("best.pt") for r in runs}, "rule": pooled_rule(arm, C),
                     "ensemble": "mean over the 15 cross-fit checkpoints of p (p_succ; no-op P(Y0)) and J_hat per candidate; F1 first; then the rule"}
    return arms


def development_rates(waves=("wA", "wB", "wC")) -> dict:
    """Per (generator, mechanism, K_intent): acceptance rate, Y0 = 0 rate, verified-repair rate, verified K >= 2 rate, teacher CPU per root."""
    acc, real = collections.defaultdict(lambda: [0, 0]), collections.defaultdict(list)
    for w in waves:
        g = json.loads((G.wdir(w) / "GENERATION.json").read_text())
        for a in g["attempts"]:
            key = (w if w == "wA" else "V21B", a["spec"]["mechanism"], a["spec"]["K_intent"])
            acc[key][0] += a["accepted"]
            acc[key][1] += 1
        for r in json.loads((G.wdir(w) / "SUMMARY.json").read_text())["rows"]:
            real[(w if w == "wA" else "V21B", r["spec"]["mechanism"], r["spec"]["K_intent"])].append(r)
    out = {}
    for key in sorted(set(acc) | set(real), key=str):
        rs = real.get(key, [])
        n = len(rs)
        out["|".join(map(str, key))] = {"slots": acc[key][1], "accepted": acc[key][0], "accept_rate": acc[key][0] / max(acc[key][1], 1), "roots": n,
                                        "y0_0": sum(r["y0"] == 0 for r in rs) / n if n else None,
                                        "verified_repair_given_y0_0": (sum(r["y0"] == 0 and r["verified_repairs"] > 0 for r in rs) / max(sum(r["y0"] == 0 for r in rs), 1)) if n else None,
                                        "K_ge2": sum(isinstance(r["verified_K"], int) and r["verified_K"] >= 2 for r in rs) / n if n else None,
                                        "harmful_root": sum(bool(r["harmful"]) for r in rs) / n if n else None,
                                        "cpu_per_root": float(np.mean([r["cpu_s"] for r in rs])) if n else None}
    return out


def plan(rates, n_slots=None) -> dict:
    """V2.1 confirmatory plan from V21B development rates only. Slot composition targets >= 60 initially infeasible roots WITH a verified
    repair (the population of the primary endpoint) and >= 24 verified K >= 2 roots, plus >= 40 initially feasible roots (unnecessary-repair
    endpoint, with harmful-edit alternatives)."""
    r = {k: v for k, v in rates.items() if k.startswith("V21B|")}
    mix = {"near_closed|0": 0.30, "goal_occupant|1": 0.06, "place|1": 0.06, "mixed|2": 0.22, "nested|2": 0.14, "pick|2": 0.10, "mixed|3": 0.06, "nested|3": 0.06}
    def exp(n):
        e = collections.Counter()
        for k, f in mix.items():
            v = r.get(f"V21B|{k}")
            if not v or not v["roots"]:
                continue
            roots = n * f * v["accept_rate"]
            e["roots"] += roots
            e["infeasible"] += roots * v["y0_0"]
            e["repairable"] += roots * v["y0_0"] * v["verified_repair_given_y0_0"]
            e["K_ge2"] += roots * v["K_ge2"]
            e["feasible"] += roots * (1 - v["y0_0"])
            e["harmful_roots"] += roots * v["harmful_root"]
            e["teacher_cpu"] += roots * v["cpu_per_root"]
        return dict(e)
    n = n_slots
    if n is None:
        n = 60
        while n < 2000:
            e = exp(n)
            if e.get("repairable", 0) >= 60 and e.get("K_ge2", 0) >= 24 and e.get("feasible", 0) >= 40:
                break
            n += 10
    e = exp(n)
    hw = lambda m: 1.96 * 0.5 / math.sqrt(max(m, 1))  # noqa: E731
    return {"version": "BXY_P18_CONFIRM_PLAN_V21_V1", "namespace": CONFIRM_NS, "generator": "BXY_GEN_V21B (bxy_p16 construct / validate, REV['wB'])",
            "slots": n, "mix": mix, "expected": e, "construction_cpu_s_estimate": n * 85.0, "teacher_cpu_s_estimate": e.get("teacher_cpu", 0),
            "precision": {"primary_population": "initially infeasible roots WITH a verified repair (availability reported separately)",
                          "paired_half_width_95_worst_case": hw(e.get("repairable", 0)), "K_ge2_half_width_95_worst_case": hw(e.get("K_ge2", 0))},
            "rules": {"rejects": "a rejected slot is NOT replaced by a different spec; every construction attempt and validation reject is recorded",
                      "shortfall": "if realized repairable < 60 or K>=2 < 24 the confirmatory analysis is still run once on what exists and labelled "
                                   "UNDERPOWERED; no additional wave may be generated after any test-model look",
                      "censored": "administrative kills are CENSORED (absent), never 0; attempted budget failures are operational 0",
                      "budget_failures": "certified vs fixed-budget negatives reported per stratum; no impossibility claim from budget failures",
                      "clustering": "each root is its own family; paired family bootstrap B = 10000",
                      "stops": "fixed slot count; one collection; one evaluation; no interim look at labels or model outputs"},
            "custody": "generated only after FROZEN_MODELS.json and CONFIRM_ANALYSIS.json are committed; disjoint from BD_GEN_V1, the 34 exposed "
                       "test roots, bxyg2pilot, bxyg2confirm (P15 plan, superseded, never generated) and bxyg21dev",
            "supersedes": {"runs/approach_b/bxy_p15_v1/CONFIRM_PLAN.json": sha("runs/approach_b/bxy_p15_v1/CONFIRM_PLAN.json")},
            "basis": "P16 development realization rates of BXY_GEN_V21B (waves wB, wC); no model output was used"}


def analysis(frozen, ev) -> dict:
    return {"version": "BXY_P18_CONFIRM_ANALYSIS_V1", "population": "the generated bxyg21confirm cohort, every root, one evaluation",
            "models": {a: {"rule": v["rule"]["rule"], "checkpoints": v["checkpoints"]} for a, v in frozen["arms"].items()},
            "primary": {"endpoint": "verified corrective-selection success on initially infeasible roots (availability-conditioned and unconditioned)",
                        "test": "candidate - matched baseline, paired family bootstrap, two-sided 95% CI; IMPROVES if CI lower > 0, point >= 0.10 and "
                                "unnecessary-repair point increase <= 0.05",
                        "candidate_vs": ["B:XYQ-BASE", "A:DIRECT-GEO", "E:XY-UNC-SA-GEO-SYM"]},
            "secondary": ["unnecessary repairs (harmful vs harmless)", "Y0 / edited-Y AUROC, ECE, Brier", "edit sign by transition", "order "
                          "concordance on measured discordant pairs", "omission sign", "K strata with n", "witnessed J on matched successes",
                          "catalogue availability", "teacher / verification CPU", "no-op, shortest, displacement, analytic-access references, "
                          "verify-first ceiling"],
            "corpus_shift": "report P-min / P15 / V2.1-dev / confirm performance side by side; no re-tuning on confirm",
            "multiplicity": "three primary comparisons, Bonferroni 98.3% CIs reported alongside 95%",
            "zero_test_look": True}




def load_member(arm, rid):
    """One frozen cross-fit checkpoint (state dict verified against its RESULT.json sha256)."""
    import torch
    rd = M.OUT / "runs" / rid.replace("/", "__")
    r = json.loads((rd / "RESULT.json").read_text())
    if sha(rd / "best.pt") != r["files"]["best.pt"]:
        raise RuntimeError(f"{rid}: checkpoint hash mismatch")
    m = M.build_model(arm, 0)
    m.load_state_dict(torch.load(rd / "best.pt", weights_only=False))
    return m.eval()


def ensemble_rows(arm, sv, members=None) -> list:
    """Frozen-ensemble candidate rows for one scorer view: mean p and J_hat over the arm's 15 checkpoints (F1-screened rows carry none)."""
    import bxy_p11 as P
    if members is None:
        members = [load_member(arm, f"cv/f{f}/{arm.split(':')[0]}/s{s}") for f in range(M.FOLDS) for s in M.SEEDS]
    preds = [P.predict_all(m, sv)["cands"] for m in members]
    rows = []
    for j, c in enumerate(sv["cands"]):
        r = dict(c)
        if c["admissible"]:
            r["p"] = float(np.mean([pr[j]["p"] for pr in preds]))
            r["J_hat"] = float(np.mean([pr[j]["J_hat"] for pr in preds]))
        rows.append(r)
    return rows


def choose_frozen(arm, sv, frozen, members=None):
    import bxy_p11 as P
    rows = ensemble_rows(arm, sv, members)
    i = P.choose(rows, frozen["arms"][arm]["rule"]["rule"])
    return i, rows


def compliance() -> list:
    """Implementation-vs-methodology checklist (methodology 2026-10-31 sections; evidence = file / test / report)."""
    rows = [
        ("§1.1 ordered relocations r = (a1..am), m <= 6, one target action", "bd_core.check_sequence; F1 LENGTH; phi_x / F2 accept 6 actions",
         "tests/test_bxy_p17.py::test_six_step_prefix_features_and_encoding", "IMPLEMENTED; labelled lengths <= 5 only (P16 §1)"),
        ("§1.1 achieved state carried, no reset between relocations", "bxy_teacher.x_query / replay_x continuity", "tests/test_bxy_teacher.py", "IMPLEMENTED + EVIDENCE"),
        ("§2.1 / §2.2 Y from fixed q_ref in the hypothetical edited scene", "bxy_teacher.y_query", "tests/test_bxy_teacher.py", "IMPLEMENTED + EVIDENCE"),
        ("§2.2.1 X includes the terminal connector to q_ref", "bxy_teacher.x_query connector + replay", "P16 §1: 20 connector-phase negatives", "IMPLEMENTED + EVIDENCE"),
        ("§2.3 all four X/Y cells", "P-min + V2.1 data", "P16 §1: 66 / 28 / 68 / 42 roots", "EVIDENCE"),
        ("§2.3 attempted failure = 0, unattempted = absent, censored = absent", "bxy_v2 / bxy_p17_data._obs", "tests/test_bxy_p11.py; test_bxy_p17.py", "IMPLEMENTED"),
        ("§3.1 F1 analytic screen only", "bxy_f1 (BXY_F1_V1)", "tests/test_bxy_p11.py", "IMPLEMENTED"),
        ("§3.1 F2 predecessor-aware prefix unary", "abc7 ModelBC7 order='pred'; G control order-invariant", "P17 P5 contrast", "IMPLEMENTED; benefit: see P17"),
        ("§3.1 F3 hypothetical-scene unary", "ModelXY2 scene head + geoY", "P17 representation metrics", "IMPLEMENTED"),
        ("§3.1 F4 omissions via the same networks, no pair head", "query design + evaluation omission metric", "P17 omission sign", "IMPLEMENTED"),
        ("§3.1 F5 one quadratic XY coupling", "bxy_core.ModelXY xy head; E control w = 0", "P17 P3 contrast", "IMPLEMENTED; benefit: see P17"),
        ("§3.2 / §4.2 root-consistent normalization, shared Y", "bxy_core.log_evidence / marginals", "tests: marginal invariant to appended X; brute-force microcases", "IMPLEMENTED"),
        ("§5.3 exact marginalization of unobserved queries", "bxy_p11.log_evidence", "tests/test_bxy_p11.py", "IMPLEMENTED"),
        ("§6.1 m, C_d exact; J full witness incl. connector and target", "bxy_p11.cd_cells; bxy_p17_data travel", "P16 / P17", "IMPLEMENTED"),
        ("§6.2 L_B = L_joint + lambda_J L_J; no J for failures", "bxy_p11 / bxy_p17.batch_loss", "logged separately in history.json", "IMPLEMENTED (+ separately stated CON / SYM auxiliaries)"),
        ("§6.3 F1 first, marginalize, no-op rule, frozen eta / cost rule, abstention", "bxy_p11.choose; bxy_p17.choose_rule", "P17 inner rules", "IMPLEMENTED"),
        ("§8.1 minimal code boundaries; historical modules frozen", "new bxy_p16* / bxy_p17* / bxy_p18* modules", "hash guard", "IMPLEMENTED"),
        ("§8.2 matched XY-uncoupled, XY-quadratic, DIRECT, analytic / shortest, no-op, verify-first", "P17 arms + references", "EVALUATION_P17.json", "IMPLEMENTED"),
        ("§8.2 acceptance 6: coupling must beat uncoupled before attributing value", "P17 P3", "0124", "TESTED (see verdict)"),
        ("§8.2 acceptance 8: independent end-to-end evaluation", "confirmatory plan (not generated)", "CONFIRM_PLAN_V21.json", "PLANNED ONLY"),
        ("§9 no causal claim from w; budget-relative zeros; catalogue recall separate", "reports 0123-0125", "-", "HONOURED"),
    ]
    return [{"methodology": a, "implementation": b, "evidence": c, "status": d} for a, b, c, d in rows]


if __name__ == "__main__":
    import sys
    import bxy_p17_eval as E
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.process_time()
    ev = json.loads((M.OUT / "EVALUATION_P17.json").read_text())
    C = E.context()
    c = ev["contrasts"]["OB"]
    gate = bool(c["P1_SYM_vs_BASE"].get("IMPROVES_WITHIN_GUARDRAIL")) and bool(c["P2_SYM_vs_DIRECT"].get("SUPERIOR_TO_DIRECT_criterion"))
    fz = {"decision": "CANDIDATE_MET_DEVELOPMENT_GATE" if gate else "NEGATIVE_RESULT_BEST_DIAGNOSTIC_MODEL",
          "candidate": "D:XYQ-GEO-SYM", "challenger": "E:XY-UNC-SA-GEO-SYM", "matched_direct": "A:DIRECT-GEO", "matched_uncoupled": "E:XY-UNC-SA-GEO-SYM",
          "coupling": "UNSUPPORTED in development (P3); deployment preference E unless confirmation shows D's coupling advantage",
          "evaluation_sha256": sha(M.OUT / "EVALUATION_P17.json"), "design_sha256": sha(M.OUT / "TRAINING_DESIGN_P17.json"),
          "inputs": {"P15": sha("runs/approach_b/bxy_p16_v1/inputs/INPUTS_P15_PILOT.pt"), "V21": sha("runs/approach_b/bxy_p16_v1/inputs/INPUTS_V21.pt")},
          "access_maps": {"p16": sha(G._maps_file()), "p17_extra_place": sha(M.DATA.EXTRA_MAPS)},
          "input_contract": "bxy_p16_inputs.view: scene, goal_cell, q0 = q_ref only; DINOv2-small rev ed25f3a3, 224 px, 16 x 16 grid",
          "output_semantics": "per candidate p (p_succ; no-op P(Y0)), px, py, w, J_hat; F1 first; rule cost -log p + alpha m + gamma J_hat",
          "arms": freeze_models(ev, C)}
    rates = development_rates()
    pl = plan(rates)
    an = analysis(fz, ev)
    for name, obj in (("COMPLIANCE.json", compliance()), ("FROZEN_MODELS.json", fz), ("DEVELOPMENT_RATES.json", rates), ("CONFIRM_PLAN_V21.json", pl), ("CONFIRM_ANALYSIS.json", an)):
        f = OUT / name
        txt = json.dumps(obj, indent=1, sort_keys=True, default=str)
        if f.exists() and f.read_text() != txt:
            raise FileExistsError(f"{f} already frozen with different content")
        f.write_text(txt)
    print(json.dumps({"slots": pl["slots"], "expected": pl["expected"], "cpu_s": round(time.process_time() - t0, 1)}, default=str))
