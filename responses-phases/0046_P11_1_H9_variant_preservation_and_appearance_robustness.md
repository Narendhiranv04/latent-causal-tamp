# 0046 — P11-1: H9 variant preservation and appearance robustness (evaluation-only correction)

**Actual result.**
- **Gate:** `runs/p11/h9/P11_H9_GATE.json` → **PASS**.
- **The suspected overwrite existed.** `_recolor` keeps the base `audit.root`, and `freeze()` stores `per[split][key]`, so palette **P2 overwrote P1**. The snapshot holds 100 H9 entries per run where 200 records exist.
- **The correction is evaluation-only:**
  - compound key `root#palette`;
  - no retraining;
  - no change to the frozen snapshot or to any P10 record.
- **Coverage:** both palettes evaluated for all 33 full-regime checkpoints (A, B, C, SF, 7 ablations × 3 seeds) on all 100 validation and blind roots. 0 physical calls.
- **Corrected conclusion: appearance sensitivity is larger and more consequential than P10e reported.**
  - Keyed B: per-root mean |Δp| = **0.248** [0.216, 0.282]. Its TOP1 choice changes on **77 %** of roots, and its H1 κ̂ moves by **0.62** on H1 roots.
  - The visual-zero control is exactly 0.
  - P10e's 0.165 for B is reproduced exactly as the P2-only, query-pooled blind value. The lost P1 value is 0.177.

This is a POST-HOC diagnostic on disclosed roots. It does not alter the P1 / P2 primaries; it bounds them, because B's choices are not appearance-invariant.

## 1. Integrity of the variants (`h9_integrity`)

- **Records:** 200 H9 records = 100 roots × 2 palettes. Compound keys are unique.
- **Inputs:** every non-visual input (object xy, radius, flags, robot q / FK, goal) and every candidate query ID is **bit-identical** to the original record.
- **Visual features:** differ from the original for all 200 records, and P1 ≠ P2 for all 100 roots.
- **Recolouring rule:** uses the recorded observation's own instance mask (instance > 0 → object RGB, 0 → support RGB). Masks, ids and geometry are untouched, and no label or certificate is read.
- **Static veto:** no H9 base root has a vetoed candidate, so TOP1 recomputed with an empty veto set equals the deployed rule.

## 2. Results (seed mean per root; root-bootstrap 95 % CI; 100 roots unless noted)

| arm | mean \|Δp\| P1 | mean \|Δp\| P2 | threshold crossings (frac. queries) | TOP1 changed | H1 \|Δκ̂\| (13 roots) | order flip (40 roots) |
|---|---|---|---|---|---|---|
| **K-B** | 0.254 [0.222, 0.287] | 0.242 [0.210, 0.277] | 0.265 | **0.770** [0.710, 0.827] | **0.616** | 0.042 |
| K-C | 0.229 | 0.225 | 0.238 | 0.668 | 0.478 | 0.089 |
| A | 0.238 | 0.238 | 0.271 | 0.635 | 0.350 | 0.058 |
| SF | 0.209 | 0.218 | 0.243 | 0.488 | 0.354 | 0.037 |
| B-F2 | 0.210 | 0.211 | 0.244 | 0.602 | 0.084 | 0.404 |
| B-F3 | 0.238 | 0.226 | 0.241 | 0.655 | 0.177 | 0.097 |
| B-F4 | 0.246 | 0.241 | 0.250 | 0.712 | 0.390 | 0.024 |
| B-F5s | 0.253 | 0.250 | 0.254 | 0.725 | 0.516 | 0.003 |
| B-F5q | 0.213 | 0.210 | 0.213 | 0.602 | 0.056 | 0.000 |
| B-U | 0.204 | 0.205 | 0.216 | 0.607 | 0.114 | 0.008 |
| **B-V0** (visual-zero) | **0.000** | **0.000** | 0.000 | 0.000 | 0.000 | 0.000 |

**Before and after** (blind roots; `H9_RESULTS.json → before_after`):

| arm | P10e (P2 only, query-pooled) | recomputed P2 query-pooled | P1 query-pooled (lost) | both palettes, per-root |
|---|---|---|---|---|
| K-B | 0.165 | 0.165 | 0.177 | 0.242 |
| A | 0.167 | 0.167 | 0.169 | 0.234 |
| SF | 0.153 | 0.153 | 0.145 | 0.208 |
| K-C | 0.157 | 0.157 | 0.163 | 0.226 |

**Reading.**
- Every DINOv2 arm is appearance-sensitive. Order choices are mostly stable (flip 0–9 %), except for the order-invariant ablation F2.
- B's complementarity estimates (κ̂) and TOP1 choices are **not** stable under recolouring.
- B's executed TOP1 advantage (P1) was measured on the original palette only. It should not be read as appearance-robust.
- The per-root mean is higher than the query-pooled mean because roots with fewer queries shift more.

**Affected P10e claims:** the H9 numbers in 0043 §3 and 0044 are superseded by this report. The primary results P1 and P2 are unaffected.

**Artifacts:**
- `runs/p11/h9/h9_predictions.json`
- `runs/p11/h9/H9_RESULTS.json`
- `visualizations/p11/P11_H9_two_palettes.png`
- `tests/test_p11_h9.py` (3 tests: collision-free keys, geometry identity, documented old collision)
