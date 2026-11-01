"""BXY-P18 figures: final architecture (data custody -> learner inputs -> F1..F5 + travel -> root-consistent likelihood -> selection ->
independent verification), and the frozen V2.1 confirmatory plan (composition, expected strata, precision)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mp  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

import bxy_p18 as Z  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_p18_v1")
INK, MUTED = "#222", "#666"


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def _box(ax, x, y, w, h, title, body, fc):
    ax.add_patch(mp.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012", fc=fc, ec=INK, lw=0.8))
    ax.text(x + 0.012, y + h - 0.025, title, fontsize=9, weight="bold", va="top", color=INK)
    ax.text(x + 0.012, y + h - 0.065, body, fontsize=7.2, va="top", color=INK, linespacing=1.35)


def _arrow(ax, a, b):
    ax.annotate("", b, a, arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 1.0})


def fig_architecture(frozen=None):
    fig, ax = plt.subplots(figsize=(17, 9.5))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    _box(ax, 0.01, 0.70, 0.21, 0.27, "Offline teacher (evaluator side)", "BXY_X_TEACHER_V1: ordered relocations from q0,\nachieved state carried, ONE connector to q_ref\n"
         "BXY_Y_TEACHER_V1: target from fixed q_ref in the\nhypothetical edited scene\nP-min budgets QB; certified vs budget negatives;\nindependent replay of every witness", "#f3e9d8")
    _box(ax, 0.01, 0.38, 0.21, 0.27, "Development data (custody)", "P-min 197 (outcome-guided catalogues)\nP15 pilot 28 (outcome-blind V2)\nP16 V2.1 87 (access closure: wA/wB/wC)\n"
         "excluded: 34 exposed test roots,\nbxyg2confirm, bxyg21confirm (plan only)", "#e8eef7")
    _box(ax, 0.01, 0.06, 0.21, 0.27, "Outcome-blind catalogue", "geometry + construction intent only:\nrepair, reversed, every prefix, omissions,\nwrong destination, alternative repair,\n"
         "interference order twins, harmful / neutral\nedits, redundant moves; F1 screen", "#e8eef7")
    _box(ax, 0.27, 0.56, 0.22, 0.30, "Label-free scorer input", "bxy_p16_inputs: scene, goal, q0 = q_ref only\nlearner tensors + frozen DINOv2-small tokens\n"
         "(exact P-min reproduction)\nGEO2 (analytic, scorer tensors + access maps):\n  phi_Y: 8 clearances + open T-pick / place modes\n  phi_X: per-action pick / place modes in the\n  ideal predecessor scene (S0 for ORDINV)", "#e6f2ea")
    _box(ax, 0.27, 0.12, 0.22, 0.36, "Factor families", "F1  analytic endpoint screen (no learning)\nF2  ordered-prefix X unary a_q (predecessor-aware;\n     G: order-invariant, same capacity)\n"
         "F3  hypothetical-scene Y unary b_s (+ geoY)\nF4  omissions = recomputed queries, same F2 / F3\nF5  ONE quadratic coupling w_q x y\n     (E: w = 0 + scene-aware xs head)\n"
         "travel head J_hat (complete witnesses only)\nDIRECT (A): one success logit, same inputs", "#e6f2ea")
    _box(ax, 0.54, 0.50, 0.21, 0.36, "Root-consistent likelihood", "P(Y_s=1) = sigma(b_s)\nP(X_q=1 | Y=y) = sigma(a_q + w_q y)\none Y node per endpoint, shared by orders\n"
         "unobserved queries marginalized exactly\nL = L_joint + lambda_J L_J (+ kappa CON / SYM aux,\nlogged separately, labels only in the loss)\n"
         "SYM: (0->1), (1->0) and concordant edit pairs\nbalanced within root", "#efe6f5")
    _box(ax, 0.54, 0.12, 0.21, 0.32, "Selection (frozen rule)", "F1 first; no-op = P(Y0); p_succ = sigma(b)sigma(a+w)\ncost = -log p + alpha m + beta C_d + gamma J_hat\n"
         "rule chosen on early-stop roots only\n(grid: no-op gate x alpha; unnecessary <= 0.10)\nabstain if nothing admitted\nensemble of 15 cross-fit checkpoints", "#efe6f5")
    _box(ax, 0.80, 0.50, 0.19, 0.36, "Independent verification", "chosen proposal executed by the versioned\nphysical provider (teacher policy);\nsuccess = X = 1 AND Y = 1 with composable\n"
         "witnesses (connector end = target start = q_ref)\nverify-first and analytic-access references;\nno label ever reaches the scorer", "#f3e9d8")
    status = ("decision: " + frozen["decision"] + "\ncandidate " + frozen["candidate"] + "\nchallenger " + frozen["challenger"] + "\n" +
              "\n".join(f"{a}: {'15 ckpts' if v['complete'] else 'INCOMPLETE'}, gate {v['rule']['rule']['noop_gate']}, alpha {v['rule']['rule']['alpha']}"
                        for a, v in frozen["arms"].items())) if frozen else "(filled at freeze)"
    _box(ax, 0.80, 0.12, 0.19, 0.32, "Frozen models (P18)", status, "#fbf6e6")
    for a, b in (((0.22, 0.83), (0.27, 0.75)), ((0.22, 0.51), (0.27, 0.66)), ((0.22, 0.20), (0.27, 0.28)), ((0.49, 0.70), (0.54, 0.70)), ((0.49, 0.30), (0.54, 0.62)),
                 ((0.645, 0.50), (0.645, 0.44)), ((0.75, 0.28), (0.80, 0.68)), ((0.75, 0.25), (0.80, 0.25))):
        _arrow(ax, a, b)
    ax.text(0.01, 1.03, "Approach B as implemented (methodology 2026-10-31): prefix-wise physical X, fixed-reference counterfactual Y, root-consistent "
            "quadratic Boltzmann model, cost-aware selection", fontsize=10, va="top", weight="bold")
    return _save(fig, "01_architecture.png")


def fig_plan(pl):
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.6))
    ks = list(pl["mix"])
    ax[0].barh(range(len(ks)), [pl["mix"][k] * pl["slots"] for k in ks], color="#2a78d6")
    ax[0].set_yticks(range(len(ks)), ks, fontsize=8)
    ax[0].invert_yaxis()
    ax[0].set(xlabel="planned construction slots", title=f"V2.1 confirmatory plan: {pl['slots']} slots in {pl['namespace']} (NOT generated)")
    e = pl["expected"]
    lab = ["roots", "infeasible", "repairable", "K_ge2", "feasible", "harmful_roots"]
    ax[1].bar(range(len(lab)), [e.get(k, 0) for k in lab], color=["#9e9e9e", "#8fb8e8", "#2a78d6", "#f2a33a", "#c9c9c3", "#b4441c"])
    ax[1].set_xticks(range(len(lab)), lab, rotation=15)
    ax[1].set(title=f"expected from P16 development rates (95% half-width on repairable ≈ {pl['precision']['paired_half_width_95_worst_case']:.3f})")
    for a in ax:
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    fig.tight_layout()
    return _save(fig, "02_confirm_plan_v21.png")


def all_figures():
    fz = json.loads((Z.OUT / "FROZEN_MODELS.json").read_text()) if (Z.OUT / "FROZEN_MODELS.json").exists() else None
    pl = json.loads((Z.OUT / "CONFIRM_PLAN_V21.json").read_text()) if (Z.OUT / "CONFIRM_PLAN_V21.json").exists() else Z.plan(Z.development_rates())
    return [fig_architecture(fz), fig_plan(pl)]


if __name__ == "__main__":
    print("\n".join(all_figures()))
