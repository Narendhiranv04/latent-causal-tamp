# P3 DEV pre-registration (frozen before any DEV prediction)

**Scope.** Development diagnostics only. The 23-scene `release_v2` TEST set is **not touched**.

**DEV = 25 engineering scenes** from the scaling campaign, never released and novelty-separated from release_v2 (A5):

| Group | Scenes | Objects |
|---|---|---|
| G0 engineering, K4 / K5 / K6 | 8 / 4 / 4 | 16–20 |
| G3 engineering, K9 | 8 | 20 |
| ENG12, K12 | 1 | 25 |

Public inputs: `dev_public.jsonl`. Labels: `dev_private.jsonl`, plus the kill tables and the teacher. Labels are read **only** by `dev_eval.py`, after `SEAL.json` is written.

**Structural caveat:** the K9 engineering scenes use corner pairs (5,7) and (61,63), and ENG12 uses (61,63). release_v2 K12 also uses (61,63).

## Arms and frozen budgets (`dev_config.json`)

All arms use the same frozen bundle (sampler s0, scorer s0), the same top-level iterative loop, the same legality and reservation rules and the same final energy. Per-root caps for every arm: **≤150 local-generator calls, ≤4,000 temporary-target probes, ≤180 s wall time, ≤12 rounds, plan length ≤12.**

| Arm | Search | Local generator | Recursion gate | Final choice |
|---|---|---|---|---|
| **REC** (B4) | top beam B_top = 6, plus temporary-target recursion (D_max = 3, B_exp = 4, B_loc_tt = 4) | frozen: K1 over all movers, K2/K3 over top-L = 8 movers, B_loc = 6 with ≤2 per first mover | temporary-target Y, ŷ(A→d_A) < 0.5, plus the lowest-ŷ action of u if ŷ < 0.9 | min C(r), λ_X = 1, λ_m = 0, ε = 1e-6 |
| **FLAT** (B1, budget-matched) | same loop, **no** temporary targets or insertion; B_top = **12**, so its maximum local calls (12 rounds × 12 = 144) match REC's cap | frozen, same | none | same |
| **RAND** (matched random) | the REC recursion and budgets | **uniform random** legal destinations, random local scores | random ŷ | the **same frozen** final energy |
| B2 / B3 (re-ranking) | REC's candidate pool | – | – | min C_Yonly (λ_X = 0) / min C_Xonly |

**Decision rule (A8):** frozen original p_noop ≥ 0.5 gives NOOP. Otherwise REPAIR with argmin C if any candidate exists, else ABSTAIN. A plan shorter than its minimum K cannot succeed, but the planner does not know K. Thresholds were not tuned: 0.5 is the frozen gate, and 0.9 is a fixed fallback.

## Outcomes and definitions (fixed now)

**Primary (physical).** The committed plan is verified post-seal by `teacher_long`: X (chained relocations plus connector) and Y (original target from q_ref).
- **Success** = X = 1 and Y = 1. NOOP, ABSTAIN and any UNKNOWN_* count as failure; UNKNOWN is reported separately.
- **Paired comparisons:** REC vs FLAT and REC vs RAND, with discordant pairs and an exact two-sided McNemar (sign) test, **descriptive only** (n = 25).

**Diagnostics.** Labels come from the kill-table relaxation (MINK_STATIC_V2, the construction-time grasp-screen tables) and the certified witness. They are used only post-seal.

| ID | Measures | Definition |
|---|---|---|
| **D1** | Useful-mover ranking, original task at S0 | Frozen best K1 p11 per mover, from a label-free probe computed for every scene outside the budget. Report its AUROC for **U** (union of all minimal goal sets of the V2 relaxation) and for **W** (the witness movers), pooled over movers with a bootstrap CI over scenes, against the null 0.5. Also recall@L = \|top-8 ∩ W\| / \|W\| against the hypergeometric expectation. |
| **D2** | Final-Y signal | h_Y (Y-only vs S0) on the witness endpoint against 20 random same-size mover sets per scene (cVAE top-1 destinations): AUROC; plus h_Y along witness prefixes k = 0..K. |
| **D3** | Temporary-target signal | (i) Probe at S0: ŷ(A→d) for every mover A with its top-1 proposal d, against the static label "A pickable now AND d placeable now" (kill tables) → AUROC. (ii) All temporary-target probes logged by REC, against the same static label at their pre-scenes → AUROC, overall and by depth. |
| **D4** | Enabling-mover ranking inside temporary tasks | For REC's logged temporary-task local calls, K1 best p11 per mover against the label "mover's cell kills a live pick candidate of the temporary target A in that scene" → AUROC. |
| **D5** | Composition | For committed plans: static order validity (every pick and place live at its time in the kill tables, and final target pick plus goal place live). For REC insertions: the fraction of inserted enabling movers that are true kill-table pick blockers of their dependent action. |
| **D6** | Search exhaustion | Stop reasons, budget usage, candidates per root. |

**Failure breakdown** for each committed plan, mutually exclusive in this order:
1. NOOP / ABSTAIN;
2. **ingredient failure**: the committed movers do not cover any minimal goal set (static final-Y dead);
3. **composition failure**: static order invalid;
4. **execution failure**: static OK but teacher X = 0 (by phase and status);
5. **final-Y failure**: X = 1 but Y = 0;
6. success.

**Interpretation rule (fixed).** Recursive guidance is called **useful** only if:
- REC succeeds on more DEV scenes than **both** FLAT and RAND; **and**
- the D1 AUROC (U or W) has a 95% bootstrap lower bound above 0.5; **and**
- the D3 AUROC has a 95% lower bound above 0.5.

Anything less is reported as a negative or inconclusive result. No re-tuning after seeing labels.
