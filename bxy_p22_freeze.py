"""BXY-P22 final evidence freeze (no teacher query, no training, no cohort): K0-K4 evidence matrix, frozen candidate / challenger / DIRECT
(P21 cross-fit ensembles, second-copy checkpoint custody), a NEW independent K0-K4 confirmation proposal (namespace bxyg34confirm, never
generated; the P18 300-slot plan stays immutable and unexecuted) sized from realized development rates and paired disagreement, and the
one-shot preregistration.
    python3 bxy_p22_freeze.py"""
from __future__ import annotations

import collections
import hashlib
import json
import math
import shutil
import time
from pathlib import Path

import numpy as np

import bxy_p16 as G
import bxy_p17 as M
import bxy_p20_k34 as Z
import bxy_p21_k34 as H

OUT = Path("runs/approach_b/bxy_p22_v1")
BACKUP = Path("/home/naren/bxy_checkpoint_backup/p21_v1")
CONFIRM_NS = "bxyg34confirm"
FROZEN = ("D:XYQ-GEO-SYM", "E:XY-UNC-SA-GEO-SYM", "A:DIRECT-GEO")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def evidence_matrix() -> dict:
    """Independent-root counts per verified K across P16 (V21) and P20 (K34) development waves, with certification and negative kinds."""
    rows = []
    for w in ("wA", "wB", "wC"):
        for r in json.loads((G.wdir(w) / "SUMMARY.json").read_text())["rows"]:
            rows.append(("V21", r, None))
    kc16 = {r["root"]: r["K_cert"] for r in json.loads(Path("runs/approach_b/bxy_p19_v1/KGEOM_AUDIT.json").read_text())["rows"]}
    for w in ("k1", "k2", "k3"):
        for r in json.loads((Z.wdir(w) / "SUMMARY.json").read_text())["rows"]:
            rows.append(("K34", r, r.get("K_cert")))
    out = {}
    for K in range(5):
        sel = [(c, r, kc) for c, r, kc in rows if (r.get("verified_K_claim", r["verified_K"]) == K)]
        cert = sum(1 for c, r, kc in sel if K >= 2 and ((kc if c == "K34" else kc16.get(r["root"])) or 0) >= K)
        neg = collections.Counter()
        for _, r, _ in sel:
            for side in ("x_neg", "y_neg"):
                for k, v in r[side].items():
                    neg[f"{side[0]}:{k}"] += v
        out[f"K{K}"] = {"independent_roots": len(sel), "by_corpus": dict(collections.Counter(c for c, _, _ in sel)),
                        "certified_necessary": cert if K >= 2 else None, "negatives": dict(neg)}
    strict = sum(len(r.get("strict_discordant", [])) for c, r, _ in rows if c == "K34")
    out["order_twins_strict_K34"] = strict
    out["harmful_roots"] = sum(bool(r["harmful"]) for _, r, _ in rows)
    out["no_verified_repair_infeasible"] = sum(1 for _, r, _ in rows if r["y0"] == 0 and r.get("verified_K") is None)
    return out


def freeze_models(ev) -> dict:
    """Candidate / challenger / DIRECT as P21 cross-fit 15-checkpoint ensembles; checkpoint bytes copied to a second location and verified."""
    F = {}
    for f in sorted((H.OUT / "runs").glob("*/RESULT.json")):
        r = json.loads(f.read_text())
        F[r["rid"]] = (r, f.parent)
    arms = {}
    for arm in FROZEN:
        runs = sorted(rid for rid, (r, _) in F.items() if r["spec"]["arm"] == arm)
        ck = {}
        for rid in runs:
            r, d = F[rid]
            dst = BACKUP / d.name
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(d / "best.pt", dst / "best.pt")
            ck[rid] = {"sha256": r["files"]["best.pt"], "repo_copy_ok": sha(d / "best.pt") == r["files"]["best.pt"],
                       "backup_copy_ok": sha(dst / "best.pt") == r["files"]["best.pt"]}
        arms[arm] = {"runs": runs, "complete": len(runs) == 15, "checkpoints": ck}
    c = ev["contrasts"]["OB"]
    return {"version": "BXY_P22_FROZEN_MODELS_V1", "basis": "P21 OOF evaluation (development only)", "candidate": "D:XYQ-GEO-SYM",
            "challenger": "E:XY-UNC-SA-GEO-SYM", "matched_direct": "A:DIRECT-GEO",
            "coupling": "P21 P3 (D vs E): " + json.dumps({k: c["P3_COUPLING"]["succ_inf"][k] for k in ("diff", "ci95")}) + "; deployment preference follows the frozen P17 rule (E unless D's coupling is confirmed)",
            "arms": arms, "backup": str(BACKUP), "backup_gap": "same physical disk as the repository; no off-machine copy",
            "design_sha256": sha(H.OUT / "TRAINING_DESIGN_P21.json"), "evaluation_sha256": sha(H.OUT / "EVALUATION_P21.json"),
            "deployment_form": "mean of the 15 cross-fit checkpoints' p (p_succ; no-op P(Y0)) and J_hat per candidate; F1 first; one rule per arm chosen on pooled early-stop predictions (bxy_p18.pooled_rule procedure)"}


def k34_rates() -> dict:
    """Realized per-slot rates of the last development version (BXY_GEN_K34C, wave k3) per family x K_intent."""
    g = json.loads((Z.wdir("k3") / "GENERATION.json").read_text())
    S = {r["root"]: r for r in json.loads((Z.wdir("k3") / "SUMMARY.json").read_text())["rows"]}
    out = collections.defaultdict(lambda: {"slots": 0, "accepted": 0, "verified_K": collections.Counter(), "cpu": []})
    for a in g["attempts"]:
        key = f"{a['spec']['family']}|K{a['spec']['K_intent']}"
        out[key]["slots"] += 1
        out[key]["cpu"].append(a["cpu_s"])                                  # construction CPU of every slot, rejected ones included
        if a["accepted"]:
            r = S[a["root_id"]]
            out[key]["accepted"] += 1
            out[key]["verified_K"][str(r["verified_K_claim"])] += 1
            out[key]["cpu"].append(r["cpu_s"])
    return {k: {"slots": v["slots"], "accept_rate": v["accepted"] / v["slots"], "verified_K_per_slot": {kk: n / v["slots"] for kk, n in v["verified_K"].items()},
                "cpu_per_slot": float(np.sum(v["cpu"]) / v["slots"])} for k, v in out.items()}


def plan(rates, sd_paired) -> dict:
    """Smallest slot count (multiple of 20) reaching >= 40 verified K3, >= 40 verified K4 and a paired 95% half-width <= 0.10 on the
    repairable K3/K4 stratum under the observed paired SD; composition fixed in advance (mostly K4-intent doorway roots)."""
    mix = {"local_mixed|K4": 0.45, "local_pick|K4": 0.10, "local_mixed|K3": 0.15, "local_pick|K3": 0.10, "local_mixed|K2": 0.05, "v21b_near_closed|K0": 0.15}
    def exp(n):
        e = collections.Counter()
        for k, f in mix.items():
            r = rates.get(k)
            if not r:
                continue
            for kk, p in r["verified_K_per_slot"].items():
                e[f"K{kk}"] += n * f * p
            e["cpu"] += n * f * r["cpu_per_slot"]
        e["repairable_K34"] = e.get("K3", 0) + e.get("K4", 0)
        e["half_width_K34"] = 1.96 * sd_paired / math.sqrt(max(e["repairable_K34"], 1))
        return dict(e)
    n = 100
    while n <= 3000:
        e = exp(n)
        if e.get("K3", 0) >= 40 and e.get("K4", 0) >= 40 and e["half_width_K34"] <= 0.10:
            break
        n += 20
    return {"version": "BXY_P22_CONFIRM_PLAN_K04_V1", "namespace": CONFIRM_NS, "generator": "BXY_GEN_K34C (bxy_p20_k34.construct, REV34['k3']) + P16 V21B controls",
            "slots": n, "mix": mix, "expected": exp(n), "basis": "P20 wave k3 realization per family x K_intent (development only; no model output)",
            "paired_sd_assumption": sd_paired, "power_note": "half-width = 1.96 * s_D / sqrt(n_repairable) with s_D the P21 paired SD (D vs DIRECT-GEO, repairable "
            "K3/K4 OOF roots); a different true disagreement rate changes the width -- report the realized width", "includes_distinct_family": "v21b controls (P16 "
            "construction logic) alongside the doorway family; a geometrically distinct K3/K4 family remains a gap (not available under the unchanged robot)",
            "stops": "fixed slots, one collection, one evaluation, no interim look; shortfall -> labelled UNDERPOWERED, no extra wave",
            "custody": "generated only after FROZEN_MODELS_P22.json and CONFIRM_ANALYSIS_P22.json are committed; disjoint from every development and P18 namespace",
            "p18_plan": {"path": "runs/approach_b/bxy_p18_v1/CONFIRM_PLAN_V21.json", "sha256": sha("runs/approach_b/bxy_p18_v1/CONFIRM_PLAN_V21.json"), "status": "immutable, not executed"}}


def analysis(fz) -> dict:
    return {"version": "BXY_P22_CONFIRM_ANALYSIS_V1", "models": {a: list(v["checkpoints"]) for a, v in fz["arms"].items()},
            "primary": {"endpoints": ["unconditional repair success on initially infeasible roots", "availability-conditioned repair success"],
                        "strata": ["K1", "K2", "K3", "K4"], "comparisons": ["D vs DIRECT-GEO", "E vs DIRECT-GEO", "D vs E"],
                        "test": "paired family bootstrap B = 10000, two-sided 95% CI; Holm across the three comparisons per endpoint",
                        "gate": "IMPROVES if CI lower > 0, point >= 0.10 and unnecessary-repair increase <= 0.05"},
            "secondary": ["unnecessary repairs (harmful / harmless)", "no-op correctness", "strict order (all / certified)", "omission sign", "prefix Y patterns",
                          "witnessed J on matched successes", "certified vs budget negatives", "catalogue availability", "references: no-op, shortest, analytic access, verify-first"],
            "action_costs": "rule as frozen per arm (no re-tuning)", "zero_test_look": True}



def figures() -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig_dir = Path("visualizations/approach_b/bxy_p22_v1")
    fig_dir.mkdir(parents=True, exist_ok=True)
    em = json.loads((OUT / "EVIDENCE_MATRIX_K04.json").read_text())
    pl = json.loads((OUT / "CONFIRM_PLAN_K04.json").read_text())
    ev = json.loads((H.OUT / "EVALUATION_P21.json").read_text())
    fig, ax = plt.subplots(1, 3, figsize=(19, 4.8))
    ks = [f"K{k}" for k in range(5)]
    v21 = [em[k]["by_corpus"].get("V21", 0) for k in ks]
    k34 = [em[k]["by_corpus"].get("K34", 0) for k in ks]
    ax[0].bar(range(5), v21, color="#8fb8e8", label="V2.1 (P16)")
    ax[0].bar(range(5), k34, bottom=v21, color="#2a78d6", label="K34 (P20)")
    for i, k in enumerate(ks):
        c = em[k]["certified_necessary"]
        ax[0].text(i, v21[i] + k34[i] + 0.4, f"{v21[i] + k34[i]}" + (f"\n({c} certified)" if c is not None else ""), ha="center", fontsize=8)
    ax[0].axhline(10, color="#b4441c", ls="--", lw=0.8)
    ax[0].set_xticks(range(5), ks)
    ax[0].legend(frameon=False, fontsize=8)
    ax[0].set(ylabel="independent roots with a verified repair", title="K0-K4 physical evidence (dashed: K4 limited-data threshold 10)")
    st = ev["strata"]["K34"]
    for j, arm in enumerate(st):
        ax[1].bar([x + (j - 2.5) * 0.13 for x in range(4)], [st[arm][f"K{K}"]["success"] or 0 for K in (1, 2, 3, 4)], 0.13, label=arm.split(":")[0])
    ax[1].set_xticks(range(4), [f"K{K} (n = {st['D:XYQ-GEO-SYM'][f'K{K}']['n']})" for K in (1, 2, 3, 4)])
    ax[1].legend(frameon=False, fontsize=7, ncol=3)
    ax[1].set(ylim=(0, 1), title="P21 held-out selection on K34 roots with a verified repair (K3 exploratory, K4 descriptive)")
    mix = pl["mix"]
    ax[2].barh(range(len(mix)), [pl["slots"] * f for f in mix.values()], color="#2a78d6")
    ax[2].set_yticks(range(len(mix)), list(mix), fontsize=8)
    ax[2].invert_yaxis()
    e = pl["expected"]
    ax[2].set(xlabel="construction slots", title=f"independent K0-K4 plan {pl['namespace']}: {pl['slots']} slots (NOT generated)\nexpected K3 {e['K3']:.0f}, K4 {e['K4']:.0f}, "
              f"~{e['cpu']:.0f} CPU-s")
    for a in ax:
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.tight_layout()
    p = fig_dir / "01_k04_evidence_and_plan.png"
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return [str(p)]


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.process_time()
    ev = json.loads((H.OUT / "EVALUATION_P21.json").read_text())
    hy = ev["hypotheses_K34"]["H1_D_vs_DIRECT_K34"]["success_repairable_K34"]
    import bxy_p21_eval as E2
    import bxy_p17_eval as E
    C = E2.context()
    T = E.tables(C, E.rules(C))
    rep = lambda k: C["corpus"][k] == "K34" and C["by"][k][2]["verified_K"] in (3, 4)  # noqa: E731
    da = E.seed_mean(T, "D:XYQ-GEO-SYM", E.METRICS["succ_inf"]("RULE"), rep)
    db = E.seed_mean(T, "A:DIRECT-GEO", E.METRICS["succ_inf"]("RULE"), rep)
    d = np.array([da[k] - db[k] for k in sorted(set(da) & set(db))])
    sd = float(d.std(ddof=1)) if len(d) > 1 else 0.5
    objs = {"EVIDENCE_MATRIX_K04.json": evidence_matrix(), "FROZEN_MODELS_P22.json": freeze_models(ev), "K34_RATES.json": k34_rates()}
    objs["CONFIRM_PLAN_K04.json"] = plan(objs["K34_RATES.json"], max(sd, 0.3))
    objs["CONFIRM_ANALYSIS_P22.json"] = analysis(objs["FROZEN_MODELS_P22.json"])
    for name, obj in objs.items():
        (OUT / name).write_text(json.dumps(obj, indent=1, sort_keys=True, default=str))
    print(json.dumps({"slots": objs["CONFIRM_PLAN_K04.json"]["slots"], "expected": objs["CONFIRM_PLAN_K04.json"]["expected"], "sd_paired": sd, "n_pairs": len(d),
                      "cpu_s": round(time.process_time() - t0, 1)}, default=str))
