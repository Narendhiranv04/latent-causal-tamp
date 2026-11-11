# 0017 — G4C-D2-P2: certificate soundness and scene-construction review (read-only)

| Field | Value |
|---|---|
| Report number | 0017 (new; 0001–0016 unchanged) |
| Date | 20 October 2026 |
| Stage | **G4C-D2-P2 — design and analysis only.** Read-only audit of source code and saved evidence, plus this one report. No code, test, configuration, plan or run was changed. No project module was imported, and no planner, target, relocation, IK, replay or test process was run. |
| Execution contract | `instruction-phase-md/G4C_D2_P2_Certificate_Soundness_and_Scene_Construction_Review.md` (208 lines, read in full; your file, left untracked) |
| Previous turn sync | Report 0016 was committed as `cd4e9fd8fcf044419b266ab3359faa630326e6a0`. HEAD and `origin/main` both equal it. |
| Starting revision | `cd4e9fd8fcf044419b266ab3359faa630326e6a0` |
| Ending revision | **Not committed.** Two tracked files were deleted in the working tree before this stage; see §11. |

---

## 1. Decision banner

| | |
|---|---|
| **Route** | **`A_CERTIFICATE_FIRST`**, with one conditional follow-up: `B_CONSTRUCTION_FIRST` (static-certifiability-first constructor), only after A's static validation. |
| **Certificate verdict** | **`CONDITIONAL`**. The proposed link-0-sector theorem (§6) is **`SOUND_AS_SCOPED`**. Its scope is: fixed start state, the declared six-phase skill with its 48-grasp family, 2D, pick side. Whether it decides any of the 15 fast UNKNOWNs is **`NOT_VERIFIABLE_FROM_AVAILABLE_REPO`**, because per-grasp rejection data was never saved. |
| **Reason** | The saved records and the code show that the 15 fast UNKNOWNs fail one premise short of a sound proof. Every connector failure was already a sound link-0 sweep certificate, but at least one grasp-screen rejection per query was uncertified. A theorem that excludes candidates by link-0 sector *regardless* of their screen status can close that gap. It can be validated with **zero planner calls**, and it bears directly on Q2, Q3, a fixed-robot scene effect and an access-based order contrast. |
| **Authorization** | **STOP. NO COLLECTION AUTHORIZED. NO CODE CHANGED.** |

---

## 2. Authority, sources and cleanliness

- **Repository.** Branch `main`; HEAD = `origin/main` = `cd4e9fd`.
- **Working tree before and after this stage.** The tracked root files `latent_causal_tamp_implementation_guide_v1_8.pdf` and `latent_causal_tamp_specification_v1_6.pdf` show as **deleted** (`git diff --name-status`: two `D` lines).
  - Their HEAD blobs are byte-identical to the untracked copies in `instruction-phase-md/`: sha256 prefixes `702637b8b695f1f3` and `a4dcda1b308c4fbe`. So this looks like a move.
  - It was not done in this session, and I left it untouched.
  - Everything else is untracked and yours: `instruction-phase-md/*` (now including the P2 contract), plus `latent_causal_tamp_2D_ABC_guides_v1_7_v1_9/` and its zip.
- **Authority.**
  - `latent_causal_tamp_methodology_v1_7.md` (normative semantics) and `latent_causal_tamp_implementation_guide_v1_9.md`, read from your bundle.
  - No newer local methodology exists; the bundle also has `START_HERE_2D_COMPARISON.md` and the v1.7/v1.9 PDFs.
- **Evidence read.**
  - Report 0016.
  - `runs/g4c_d2_poc_s/`: `final_plan.json`, `ledger.json`, `unit_evidence.json`, `poc_result.json`, `per_root_coverage.json`, and per-unit `final.json`, `certificates.json`, `relocation.json` and `target_witness.npz`.
  - `runs/g4c_pilot/`: `pilot_plan.json`, `unit_evidence.json`, `pilot_coverage.json` and `bc_pool_coverage.json`.
  - `runs/g4c_d2_precheck/precheck_coverage.json`.
  - The archived witnesses `runs/g4c_pilot/units/seq__g4c_r00__empty/target_witness.npz` and `runs/g4d_evidence/units/seq__R1__empty/target_witness.npz`.
- **Source read (definitions cited below).**
  - `skill.py`, `planner.py`, `motion.py`, `geometry.py`, `certificates.py`, `ordered.py`, `evaluate.py`, `g4d_run.py`, `g4c_pilot.py`, `d2.py`.
  - `config.toml`, sections `[suite]`, `[arm2d]`, `[gripper2d]`, `[geometry]`, `[planner2d]` and `[skill2d]`.
- **How saved data was parsed.** Python `json` and `numpy` only, with `python3 -I`. No project import.
- **Not available.**
  - **Per-candidate screen verdicts** (stage, reason, definite or uncertified for each of the 48 pick and 48 place candidates).
  - **The connector log** for every POC_S target evaluation.

  The worker drops `SkillResult` before checkpointing (`g4d_run.py:171`: `"target": {k: v ... if k not in ("result",)}`). Only `termination`, `normalized_reason`, `unresolved_connectors`, `seconds` and the invocation state were saved.

## 3. Invariants and the fixed POC_S ledger (verified, not changed)

- **Labels.**
  - 68 frozen units: **30 VERIFIED_FEASIBLE / 6 CERTIFIED_INFEASIBLE / 32 UNKNOWN / 0 NOT_RUN**.
  - Fresh bases: 2 feasible.
  - Q2 = `TRIVIAL_ONLY`.
  - Nothing is relabelled in this report.
- **Resources.**

  | Resource | Used | Note |
  |---|---|---|
  | CPU | 12,666 CPU-s | 12,622.1 in units + 44.0 coordinator |
  | Wall | 12,634 s | |
  | Relocation calls | **40 / 46** | 39 recorded + 1 completed inside a cancelled unit |
  | Target evaluations | **63 / 70** | 61 recorded + 2 in flight at cancellation |
  | CPU-censored units | 2 | |

**UNKNOWN composition** (`unit_evidence.json`, normalized reasons):

| Cause | Units | CPU-s | Where |
|---|---|---|---|
| `SCHEDULE_COMPLETED_NO_WITNESS_UNCERTIFIED_REJECTIONS` (the "fast 15") | 15 | **69.6** | 14 × g4c_r00, 1 × g4d_R1 |
| Target `SEARCH_LIMIT_PLAN_FAILURES` | 12 | 8,188.5 | all g4d_R1 |
| Relocation `SEARCH_LIMIT_PLAN_FAILURES` | 1 | 103.4 | `seq:d2_g4c_r00_G:o04>18` |
| `SCHEDULE_COMPLETED_NO_WITNESS_WITH_UNRESOLVED_CONNECTORS` | 2 | 679.8 | g4d_R1 `+A+S` `o05>40` (seq + scene) |
| `CPU_CENSORED` | 2 | 1,740.3 | g4d_R1 `+A+B` `o04>41` (seq + scene) |
| **Total UNKNOWN** | **32** | **10,781.6 (85 % of the run)** | |

**Per family:**

| Family | Units | POS / NEG / UNK | CPU-s |
|---|---|---|---|
| g4c_r00 | 34 | 16 / 3 / 15 | 595.9 |
| g4d_R1 | 34 | 14 / 3 / 17 | 12,024.0 |
| fresh | 2 | 2 / 0 / 0 | 2.2 |

**Defensible empirical quantities (POC_S only).**

| Quantity | Value |
|---|---|
| Decided yield | 36/68 frozen units (52.9 %) |
| Nontrivial certified no-repair negatives | **0**, so CPU per nontrivial no-repair negative = **N/A** |
| Trivial (GOAL_OVERLAP) no-repair negatives | 2, unit CPU 0.54 and 0.68 s |
| Substantive complete pools | 3/10 eligible variant pools |
| CPU per substantive pool | 4,222 CPU-s (whole run / 3), or 131–243 CPU-s for each pool's own units |
| Variant roots with a decided nontrivial obstruction | 0/12 |
| Lineages with a substantive pool | 2/2 |

## 4. The mathematical task and the implemented domain

### 4.1 Three quantities that must not be conflated

| Quantity | Definition (Methodology v1.7 §"Three-valued source of truth", "Labelled quantities") | Implemented by |
|---|---|---|
| Original task $Y_0^*(S_0)$ | ∃ complete target execution from the exact $S_0$ (q0, gap, free attachment, all objects) reaching the goal with a checked safe retreat | `ordered.teach_sequence` with the empty sequence, then `evaluate.evaluate_safe_retreat` (`evaluate.py:67-103`). `plan_skill(..., q_start=state.q, q_goal=None)`: no HOME connector is required. |
| Ordered repair $Y^*(r\mid S_0)$ | ∃ relocation realization $w\in\mathcal W(r,S_0)$ ∃ target γ from **w's achieved state** | `verify.plan_fixed_order`, then one target evaluation from the achieved state (`ordered.py:155-205`) |
| γ0 diagnostic | Whether one archived trajectory collides | `d2.nominal_diagnostic` (`d2.py:93-101`), scoped "the single recorded witness path only; not a task-feasibility label" |
| Fixed-robot scene edit $Y_I^*$ | Target-only from q0 in the edited clone | `effects.pose_substitution` + `g4d_run.unit_scene` |

### 4.2 Domain inventory (what is included, what is excluded, and how exhaustive it is)

| Element | Implemented definition | Code | Exhaustive? |
|---|---|---|---|
| Start | Exact q, gap = open, attachment free. A target evaluation from a non-open gap is UNRESOLVED. | `evaluate.py:53-54`, `ordered.state_record` | Fixed by the query |
| Target action class | One **declared six-phase skill**: start → pregrasp (connector) → straight approach → close/attach → carry (connector) → release → straight retreat. SAFE_RETREAT ends after the retreat. | `skill.py:1-11, 165-240`; `evaluate.py:75-76` | Policy-defined |
| Grasp family | Tool axis φ ∈ {2πk/24}, elbow branch b ∈ {+1, −1}: **48 (φ, b)**. Grasp point fixed at local (grasp_x = 0.032 m, 0). | `config.toml:72`; `skill.directions` `skill.py:82-83`; `skill.py:91` | **Exhaustive by declaration**: every screen enumerates all 48 (`skill.py:88,122`); checkers demand 48 (`certificates.py:95-96,125-126`). Other angles, grasp depths and non-side grasps are **excluded by declaration, not by physics**. |
| IK | Closed form; both elbow branches; joint-limit filter; unique q per (φ, b) | `geometry.ik` `geometry.py:87-104` | Exact |
| Approach / retreat | Straight 0.06 m lines, IK-tracked at 5 mm steps. Joint jump > 0.1 rad → `IK_CONTINUATION_UNRESOLVED` (**uncertified**). `NO_IK` and `JOINT_LIMIT_CROSSING` are definite. | `skill.py:99-100,137-138`; `motion.py:111-114`; `skill._fail` `skill.py:63-73` | Fixed path per candidate |
| Closure | Contact-model geometry (exact) plus a certified closure sweep | `skill.py:105-115` | Per candidate |
| Placement | **Exact goal-cell centre** with nominal local (grasp_x, 0), gap 2r. Success test: placement ≤ goal tolerance = `release_xy_tolerance_m` = **0.002 m**. | `skill.py:186-188`; `data.py:37`; `evaluate.py:90` | Discrete in the skill; the task predicate accepts a 2 mm disc |
| Collision semantics | COLLISION (definite) iff clearance < δ − ε; gray band ±ε → UNRESOLVED; per-segment budget 4,000 evaluations → UNRESOLVED. δ = 0.005 m, ε = 0.0002 m. | `config.toml:12,53,56`; `geometry.certify` | Sound per segment |
| Connectors | Direct → guide line → **link-0 sweep certificate (COLLISION)** → seeded RRT-Connect (4,000 nodes; 300 s wall cap flagged). Budget end = UNRESOLVED. | `planner.plan` `planner.py:211-253` | **Only the link-0 test is a continuous-domain statement** (`planner.py:41-59`). RRT is not exhaustive. |
| Skill schedule | Up to 64 direct pick–place pairs, then RRT over every screen-passing pick (pregrasp) and every screen-passing place (carry). Stops at **4 UNRESOLVED RRT connectors**. | `config.toml:77-78`; `skill.py:194-240` | Exhaustive over screen-passing pairs only when failures < 4 |
| Skill terminations | `SEARCH_LIMIT_PLAN_FAILURES`; `SCHEDULE_COMPLETED_ALL_CERTIFIED_BLOCKED` (status INFEASIBLE, scope `DECLARED_GRASP_SET+LINK0_SWEEP`); `SCHEDULE_COMPLETED_NO_WITNESS` | `skill.py:230-240`; normalized in `ordered.py:130-140` | — |
| What becomes a label | Only checker-accepted certificates with scope ASSIGNMENT or ORDER. The skill's own INFEASIBLE verdicts are **not** labels. | `g4c_pilot.SOUND` `g4c_pilot.py:37`; `adjudicate` `:115-132`; `certificates.check` `certificates.py:172-184` | Kinds: GOAL_OVERLAP, STATIC_ENDPOINT_INVALID, TARGET_PICK, FIRST_MOVER (ASSIGNMENT), ORDER_FIRST_ACTION (ORDER) (`certificates.py:165-169`) |

**$\Gamma(S_0)$ used in this report (INFERENCE, needs your confirmation).** The permitted target-execution domain is the declared skill: the 48 (φ, b) pick configurations, the fixed approach line, any continuous certified connector, and the 48 exact-centre place configurations with the fixed release/retreat line.

This is supported by three things:
- Methodology v1.7 retains the "recorded 48-candidate grasp family".
- Every accepted kind is scoped `PLANAR_ARM_KINEMATIC_SKILL/DECLARED_GRASP_SET`.
- The skill docstring defines it so.

Any certificate below is therefore **"infeasible for the declared skill"**. It is never "physically impossible". If you intend a wider domain (other grasp depths or angles, curved approaches, off-centre placements within 2 mm), all pick/place-screen-based kinds, including the existing TARGET_PICK and FIRST_MOVER, would need re-scoping.

## 5. Unit-by-unit audit of the 15 fast UNKNOWNs

### 5.1 What every row's saved record proves (deduced from `skill.py:183-240`)

Every one of the 15 has: termination `SCHEDULE_COMPLETED_NO_WITNESS`, normalized `..._UNCERTIFIED_REJECTIONS`, `unresolved_connectors = 0`, no witness, and CPU 0.36–13.9 s. From the code this implies:

- **D1.** At least one declared pick candidate passed the pick screen, and at least one place candidate passed the place screen. Otherwise the termination would be `PICK/PLACE_SCREEN_EXHAUSTED` (`skill.py:183-191`).
- **D2.** No RRT-pass connector returned UNRESOLVED. In `planner.plan` the only non-CLEAR, non-UNRESOLVED outcome is the link-0 certificate (`planner.py:230-232`). So **every connector failure was a sound `LINK0_SWEEP` exclusion** for its fixed endpoint pair.
- **D3.** Failures < 4, so the loop over every screen-passing pick (and, after a clear pregrasp, every screen-passing place) completed (`skill.py:204-229`).
- **D4.** Not `ALL_CERTIFIED_BLOCKED`, so **at least one rejected screen candidate was uncertified**: gray band, IK continuation or evaluation budget (`skill.py:233-239`). *Which candidate is not recorded.*

Equivalently, no pair (screen-passing pick, screen-passing place) lay in the same link-0 free sector as the start (§6). What is missing is the fate of the uncertified candidates.

### 5.2 The 15 rows

Notation and conventions:
- "Sector" is the link-0 free interval of q[0] around the recorded start (§6.1), computed from the saved invocation objects with ρ < R0 = 0.4608 m.
- "Recorded in-sector configurations" are the **declared** pick/place configurations of the same target and goal actually seen in POC_S positive witnesses. They are identical in every scene of the family, because IK depends only on target and goal poses:
  - g4c_r00: pick q[0] = 78.0°; place 59.0° and 61.2°.
  - g4d_R1: pick 66.1°, 69.3°, 73.7°; place 60.5°, 69.6°.
- The number after each is a **link-axis clearance diagnostic**: link segments, half-widths and housings only, no palm, fingers or held disc, by hand forward kinematics on saved joint values (INFERENCE, not a collision check, not a certificate). Negative means the obstacle disc overlaps a link body. The validity threshold is δ − ε = +4.8 mm.
- Evidence for each row is in `runs/g4c_d2_poc_s/units/<unit with ':'→'__', '>'→'-'>/{final,certificates,relocation}.json` and in `unit_evidence.json`.
- Every row's CPU is in seconds and every row's original label is UNKNOWN.

| # | Unit | Query type | Q2? | CPU s | Start q[0] | Sector (annulus blockers) | Recorded in-sector configurations (diagnostic) | Certifiability | Scope if accepted |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `scene:d2_g4c_r00_AB:o05>41` | fixed-robot scene edit | no (Δ side) | 2.31 | 90.0 | (47.1, 180) (o04 47.1°, o05 24.8°) | pick78 −9 mm (o04); place59 −12, place61 −30 (o04) | CONDITIONAL | target-only $Y_I$ |
| 2 | `scene:d2_g4c_r00_AS:o04>56` | fixed-robot scene edit | no | 3.02 | 90.0 | (57.3, 180) (o04 57.3°, o05 37.6°) | **pick78 +24 (axis-clear)**; place59 −23, place61 −10 (o04) | CONDITIONAL on the place side (§6.3 A7) | target-only $Y_I$ |
| 3 | `scene:d2_g4c_r00_AS:o05>48` | fixed-robot scene edit | no | 2.37 | 90.0 | (48.0, 180) (o04 47.1°, o05 48.0°) | pick78 −9; place59 −12, place61 −30 | CONDITIONAL | target-only $Y_I$ |
| 4 | `seq:d2_g4c_r00_A:empty` | **original no-repair** | **yes** | 2.52 | 90.0 | (47.1, 180) (o04) | pick78 −9; place59 −12, place61 −30 | CONDITIONAL | **ORIGINAL_TARGET** |
| 5 | `seq:d2_g4c_r00_A:o04>56` | ordered repair, target stage | no | 7.13 | 136.3 | (57.3, 180) | pick78 +24; place59 −23, place61 −10 | NOT_CERTIFIABLE for $Y_r$ (C6) | diagnostic only |
| 6 | `seq:d2_g4c_r00_AB:empty` | **original no-repair** | **yes** | 2.25 | 90.0 | (47.1, 180) (o04; o05 at 19.4° lies below) | pick78 −9; place59 −12, place61 −30 | CONDITIONAL | **ORIGINAL_TARGET** |
| 7 | `seq:d2_g4c_r00_AB:o04>56` | ordered repair | no | 4.10 | 136.3 | (57.3, 180) | pick78 +24; place59 −23, place61 −16 (o05) | NOT_CERTIFIABLE for $Y_r$ | diagnostic only |
| 8 | `seq:d2_g4c_r00_AB:o05>34` | ordered repair | no | 8.14 | 107.9 | (47.1, 180) | pick78 −9; place59 −12, place61 −30 | NOT_CERTIFIABLE for $Y_r$ | diagnostic only |
| 9 | `seq:d2_g4c_r00_AB:o05>41` | ordered repair | no | 5.36 | 132.9 | (47.1, 180) | pick78 −9; place59 −12, place61 −30 | NOT_CERTIFIABLE for $Y_r$ | diagnostic only |
| 10 | `seq:d2_g4c_r00_AS:empty` | **original no-repair** | **yes** | 2.87 | 90.0 | (47.1, 180) (o04; o05 at 37.6° lies below) | pick78 −9; place59 −12, place61 −30 | CONDITIONAL | **ORIGINAL_TARGET** |
| 11 | `seq:d2_g4c_r00_AS:o04>56` | ordered repair | no | 6.15 | 136.3 | (57.3, 180) | pick78 +24; place59 −23, place61 −10 | NOT_CERTIFIABLE for $Y_r$ | diagnostic only |
| 12 | `seq:d2_g4c_r00_AS:o04>58` | ordered repair | no | 3.26 | 116.6 | (39.5, 180) | pick78 −14; **place59 +9, place61 +9 (axis-clear)** | NOT_CERTIFIABLE for $Y_r$ | diagnostic only |
| 13 | `seq:d2_g4c_r00_AS:o05>41` | ordered repair | no | 4.04 | 149.4 | (47.1, 180) | pick78 −9; place59 −12, place61 −30 | NOT_CERTIFIABLE for $Y_r$ | diagnostic only |
| 14 | `seq:d2_g4c_r00_AS:o05>48` | ordered repair | no | 13.93 | 179.5 | (48.0, 180) | pick78 −9; place59 −12, place61 −30 | NOT_CERTIFIABLE for $Y_r$ | diagnostic only |
| 15 | `seq:d2_g4d_R1_AB:o05>56` | ordered repair | no | 2.20 | 136.3 | (57.3, 180) (o05 57.3°; o04 19.4°, t0 −19.4° lie below) | pick66 −24 (o05), pick69 −28 (o04), pick74 −28 (o05); place60 −20, place70 −28 (o04) | NOT_CERTIFIABLE for $Y_r$ | diagnostic only |

Recorded trace common to all 15:
- Pick and place screens each enumerated 48 candidates (code).
- At least one candidate passed each screen (D1).
- Every connector failure was a link-0 certificate (D2).
- At least one rejection was uncertified, unrecorded which (D4).
- Number of connectors attempted: not recorded. RRT nodes spent ≈ 0, consistent with 2–14 s.

**Minimal missing proof artifact.** For the first two certifiability classes:
- *CONDITIONAL* (rows 1–4, 6, 10): the per-(φ, b) list of declared IK q[0], screen stage and the definite/uncertified flag, for the 48 pick and 48 place candidates in each scene. This is a deterministic, pose-only recomputation with **zero planner calls**. It was prohibited in this stage.
- *NOT_CERTIFIABLE for $Y_r$* (rows 5, 7–9, 11–15): the target start is the achieved state of **one** relocation realization. A fixed-start theorem cannot exclude the realizations $w\in\mathcal W(r,S_0)$ that end in another link-0 sector (counterexample C6).

### 5.3 Failure modes ranked by coverage and by whether they can ever support Q2

| Rank | Missing premise | Rows | Can support Q2? |
|---|---|---|---|
| F1 | Unknown fate of uncertified screen rejections inside the free sector | all 15 | **Yes, the only route.** Rows 4, 6, 10 are the three g4c_r00 `+A*` no-repair queries. Rows 1–3 decide scene-edit sides. |
| F2 | Realization-dependent start after relocation | 9 (rows 5, 7–9, 11–15) | No. These are repairs, not no-repair queries. A start-independent "every sector excluded" variant would be needed, and the recorded lower-sector configurations look axis-clear (pick −27° +64 mm, place −87° +26 mm), so that variant **likely fails** (INFERENCE). |
| F3 | Goal-tolerance robustness of place-side exclusions | row 2, plus any row that needs the place side | Indirectly |

### 5.4 The expensive UNKNOWNs (17 units, 10,712 CPU-s) are a different problem

The 12 target search limits, 2 unresolved-connector units and 2 censored units are all g4d_R1, plus one g4c_r00 relocation search limit:
- By the same code logic, a **screen-passing pick/place pair inside the start's free sector existed**, and its RRT connectors ran out of nodes four times. No static screen or link-0 theorem can exclude a pair that passed both screens and is not link-0-separated. Deciding them needs either a witness or a continuous configuration-space impossibility proof, and no such proof exists in the code.
- **Geometry (observed).**
  - g4d_R1's target is at ρ = 0.361 m, **inside the link-0 length** L1 = 0.42 m, at −19.4°. A sits at 19.4° (ρ 0.361) and B at 47.1° (ρ 0.382).
  - The archived nominal witness grasps with q[0] = 69.3° (`runs/g4d_evidence/units/seq__R1__empty`), inside every `+A*` free sector. Recorded in-sector configurations exist.
- **Narrow passages (HYPOTHESIS).** Folded arm configurations near the base create narrow passages for the 4,000-node RRT.
- **A local grasp certificate would not apply** to these units. That is why `g4d_R1 +A+B` cost 6,655 CPU-s with zero decided units.

## 6. The certificate: theorem, assumptions and falsification

### 6.1 Link-0 sector lemma

- **Definitions.**
  - Base $b$, link-0 length $L_1$ = 0.42, half-width $w_0/2$ = 0.009, housing radius $r_h$ = 0.012 at the link-0 end (`geometry.bodies` `geometry.py:140`), disc radius $r$ = 0.024.
  - $R_0 = L_1+\max(w_0/2,r_h)+r+\delta-\varepsilon$ = 0.4608 m (as in `planner.py:53`).
  - For a world $W$ (resting discs) and an obstacle $o$ with polar coordinates $(\rho_o,\alpha_o)$ about $b$, the annulus set is $\mathcal A(W)=\{o:\rho_o<R_0\}$.
  - For a start $q_s$ with $q_s[0]\notin\{\alpha_o\}$, the free sector is

$$I(W,q_s)=\Bigl(\max\{\alpha_o:o\in\mathcal A(W),\alpha_o<q_s[0]\},\ \min\{\alpha_o:o\in\mathcal A(W),\alpha_o>q_s[0]\}\Bigr)$$

  intersected with the joint-1 limits. An empty max or min gives the joint limit.

- **Lemma.** Every continuous path $q(t)$, $t\in[0,1]$, $q(0)=q_s$, whose every configuration is not COLLISION in $W$ satisfies $q(t)[0]\in I(W,q_s)$ for all $t$.

- **Proof.**
  1. Joint 1 is confined to $[-3.14159265, 3.14159265]\subset(-\pi,\pi)$ (`config.toml:25-29`), so $q[0]$ is a continuous real function with no wrap.
  2. If it left $I$, by the intermediate value theorem it would equal some $\alpha_o$, $o\in\mathcal A(W)$, at some $t^*$.
  3. Link 0 then points at the centre of $o$. If $\rho_o\le L_1$ the link-0 axis passes through that centre. Otherwise the nearest body point is on the housing, at distance $\rho_o-L_1-r_h$.
  4. Either way the clearance is below $\delta-\varepsilon$, i.e. COLLISION, a contradiction. ∎

This is the same argument as the existing pairwise `link0_sweep_blocker` (`planner.py:41-59`), lifted from one endpoint pair to the whole reachable set.

### 6.2 Theorem: target excluded for the declared skill from a fixed start

Notation:
- Moved object $m$ (the target, or the first relocated object) and destination cell $d$.
- For each $(\varphi,b)\in D$ (48): the pick configuration $q^{\mathrm{pk}}_{\varphi b}$ from exact IK at grasp local $(x_g,0)$, its fixed approach line, and the place configuration $q^{\mathrm{pl}}_{\varphi b}$ at the exact centre of $d$.
- $W$ is the start world (all resting objects, $m$ included). $W_h = W\setminus\{m\}$ is the carry world.
- Define

$$X^{\mathrm{pk}}_{\varphi b}\;\equiv\;\neg\mathrm{IK}\ \lor\ \mathrm{DefPick}_{\varphi b}(W)\ \lor\ q^{\mathrm{pk}}_{\varphi b}[0]\notin I(W,q_s)$$

$$X^{\mathrm{pl}}_{\varphi b}\;\equiv\;\neg\mathrm{IK}\ \lor\ \mathrm{DefPlace}_{\varphi b}(W_h,d)\ \lor\ q^{\mathrm{pl}}_{\varphi b}[0]\notin I(W_h,q_s)$$

  where Def… means a **definite** rejection of the existing pose-only screen (`skill.screen_pick`, `skill.screen_place`, with `certified=True`).

**Theorem.**

$$\bigl(\forall(\varphi,b)\in D: X^{\mathrm{pk}}_{\varphi b}\bigr)\ \lor\ \bigl(\forall(\varphi,b)\in D: X^{\mathrm{pl}}_{\varphi b}\bigr)\ \Longrightarrow\ \nexists\,\gamma\in\Gamma_{\text{skill}}(W,q_s)\ \text{valid}.$$

**Proof sketch.**
1. Every declared-skill execution passes through some $q^{\mathrm{pk}}_{\varphi b}$ (reached from $q_s$ in $W$) and some $q^{\mathrm{pl}}_{\varphi'b'}$ (reached while carrying, in $W_h$) (`skill.py:165-229`).
2. IK absence and definite screen rejections exclude a candidate in every realization. These screens are pose-only and start-independent, as already relied on by TARGET_PICK and FIRST_MOVER.
3. By the lemma, the pick configuration must lie in $I(W,q_s)$.
4. Since $\mathcal A(W_h)\subseteq\mathcal A(W)$, $I(W,q_s)\subseteq I(W_h,q_s)$, so the place configuration must lie in $I(W_h,q_s)$.
5. If every pick candidate, or every place candidate, is excluded, no execution exists. ∎

**Valid uses (fixed start):**

| Use | $q_s$, $W$ | Resulting scope |
|---|---|---|
| Original no-repair | q0, $S_0$ | **ORIGINAL_TARGET** (declared skill), i.e. $Y_0^*=0$ |
| Fixed-robot scene edit | q0, $S_0^I$ | target-only $Y_I^*=0$ |
| Robot-start variant | $q_{\text{start}}$ | target-only |
| **First action** of an ordered $r$ | q0, $S_0$, $m$ = first object | **ORDER**: nothing has moved, so it covers every realization of this order |

**Invalid uses:** a later action or the target after relocations (the start depends on the realization; C6). Old-path collision is never usable (C1).

### 6.3 Assumption ledger

| # | Assumption | Status |
|---|---|---|
| A1 | $\Gamma$ = the declared six-phase skill with 48 grasps (§4.2) | **INFERENCE, documented.** Same scope as accepted kinds. **Needs your explicit confirmation.** |
| A2 | IK exact and unique per (φ, b) | Verified in code (`geometry.py:87-104`) |
| A3 | Joint 1 cannot wrap | Verified (`config.toml:25-29`; also guarded in `planner.py:49`) |
| A4 | Link-0 and housing geometry as used in R0 | Verified (`geometry.py:140`) |
| A5 | A COLLISION verdict is sound (conservative certifier) | Inherited; already relied on by every accepted kind |
| A6 | Exact, static initial poses | Verified (`state_pose_uncertainty_m = 0`, `config.toml:115`) |
| A7 | Place side: the skill places at the exact centre, but the success predicate accepts **2 mm** | **OPEN.** A definite place collision does not carry a depth, so it may not hold over the 2 mm disc. **Pick side and sector-only place exclusions with an angular margin are unaffected.** |
| A8 | Fixed start | A scope restriction, not an assumption |

### 6.4 Relation to existing code

- **Generalizes TARGET_PICK** by adding the sector exclusion.
- **Generalizes the skill's internal `ALL_CONNECTORS_CERTIFIED_BLOCKED`** (`skill.py:233-237`). That verdict is sound by D2/D3 but has **no checker**, so it was never a label; it is the special case in which every screen rejection is definite.
- The theorem drops the requirement for definite rejections **outside** the free sector, which is exactly the gap D4 identified.

### 6.5 Falsification attempts

**(a) Necessary-condition test on all recorded positives.** All **32** POC_S positive target witnesses (`target_witness.npz`; `r0__q`, `r0__phase`) keep q[0] strictly inside the predicted free sector of their own start and world. **0 violations.** Consistent with soundness; not a proof.

**(b) Counterexample sketches.** Each breaks a different premise; the theorem as scoped survives all of them.

| # | Premise attacked | Concrete instance | Consequence |
|---|---|---|---|
| C1 | "Old nominal path blocked ⇒ infeasible" | The archived g4c_r00 witness sweeps q[0] ∈ [−94.6°, 121.9°] (pick −27.0°, place −86.7°). In `scene:d2_g4c_r00_A:o04>49` an annulus obstacle sits at 37.6°, so **by the lemma that nominal route is impossible**, yet the unit is **VERIFIED_FEASIBLE** via a different declared route (pick 78.0°, place 59.0°, q[0] ∈ [59.0°, 122.1°]). | Nominal collision is never a label (already policy; now with a recorded instance) |
| C2 | "All scheduled grasps fail ⇒ no grasp" | In the declared skill all 48 are always screened, but a grasp at φ = 7.5° or a deeper grasp point (local x ≠ 0.032 m) is physically plausible and outside the family | Certificates must say *declared skill*, never "physically impossible" (A1) |
| C3 | "Planner gave up ⇒ blocked" | `seq:d2_g4d_R1_A:empty`: screen-passing in-sector pairs existed (D-logic) and RRT hit 4 failures (441 CPU-s) | Search limits never certify; the theorem does not apply there |
| C4 | "Discrete set covers the continuum" | Placement within 2 mm of the centre is accepted by the goal predicate. A place configuration that is definitely colliding at the exact centre may be clear 2 mm away. | Place-side screen exclusions are CONDITIONAL (A7) |
| C5 | "Rejected ⇒ excluded" | Gray-band (±0.2 mm) or IK-continuation rejections (`skill.py:63-73`, `motion.py:113`) may hide a valid candidate | Uncertified rejections exclude nothing unless the sector excludes that candidate |
| C6 | "Target-stage proof ⇒ repair negative" | Rows 5, 7–9, 11–15: the recorded starts after relocation are q[0] = 107.9°–179.5°. Another realization of the same $r$ (other grasps or paths for the relocations) may end below the annulus obstacle, where recorded configurations look clear (pick −27° +64 mm). | No fixed-start theorem labels $Y_r$ |
| C7 | "Near the annulus counts" | Pilot r19 `o00` at ρ = 0.465 m > 0.4608: link 0 can sweep past it | The checker must use the strict ρ < R0 test |
| C8 | "Teleport proves executability" | `scene:d2_g4c_r00_AB:o04>49.o05>41` (teleport) is POSITIVE. That is not the ordered repair: `seq:...o04>49.o05>41` needed its own relocation witness. | Scene edits are target-only diagnostics, never repairs |

### 6.6 Sub-certificates and their status

| Sub-certificate | Quantifier | Evidence needed | Soundness | Code readiness | Applicability | Residual UNKNOWN |
|---|---|---|---|---|---|---|
| (i) **Pick side**: sector + definite pick screen | all 48 picks, fixed $q_s$ | 48 IK q[0] + 48 pick-screen verdicts + annulus set | **SOUND_AS_SCOPED** | New checker (not written) | Rows 1, 3, 4, 6, 10 likely candidates (recorded in-sector pick overlapped by −9 mm); unrecorded in-sector picks unknown | Any in-sector pick passing or uncertified |
| (ii) Place side, sector only, with an angular margin covering 2 mm | all 48 places | as (i), plus an IK-sensitivity bound | SOUND_AS_SCOPED once the margin is derived | Not written | Row 2 needs the place side | In-sector places |
| (iii) Place side via definite place screen | all 48 places | as (i) | **CONDITIONAL (A7)** | Not written | Rows 2, 12 | — |
| (iv) **First-action ORDER version** of (i)–(iii) | first object, $q_s$ = q0 | same, for the moved object | SOUND_AS_SCOPED (pick side) | Not written | **Pilot**: `seq:g4c_r19:o00>27`, `seq:g4c_r19:o00>27.o01>28`, `seq:g4c_r08:o00>15`, `o00>47`, `o00>47.o01>46`, `seq:g4c_r14:o02>39.o00>38`, `o02>39.o01>7.o00>38`, and `seq:g4c_r08:o01>46.o00>47`. All but the last were recorded `ALL_PAIRS_CERTIFIED_BLOCKED` (every rejection definite per the skill). Plus the fixed-robot `scene:g4c_r19:o00>9`. | Uncertified in-sector rejections |
| (v) Independent checker for the skill's `ALL_CONNECTORS_CERTIFIED_BLOCKED` | pairs | recompute pairs | Special case of (i)–(iii) | Not written | as (iv) | — |
| (vi) Sectorwise (start-independent) target exclusion | every sector of the final world | per-sector screens | Sound | Not written | Rows 5, 7–9, 11–15 | **Likely inapplicable** (INFERENCE, C6) |
| (vii) Continuous configuration-space barrier or corridor | full configuration space | interval or cell decomposition | Not specified | **NOT_READY** | the 17 expensive g4d_R1 units | All of them |
| (viii) Nominal-sweep collision | one path | — | **UNSOUND as a label (C1)** | — | none | — |

**Tests for a future, separately approved implementation:**
1. A synthetic single annulus obstacle between q0 and all grasps is accepted. Moving it to ρ = 0.465 m is refused (C7).
2. An in-sector candidate with a gray-band rejection is refused (C5).
3. A record with fewer than 48 candidates, a changed start q, a changed object pose or goal is refused as stale.
4. Use on a non-empty sequence's target stage is refused (C6).
5. Joint limits widened past ±π are refused.
6. **Every recorded positive witness** (POC_S, pilot, G4D) is never contradicted at its own start and world.
7. Place side is disabled until A7 is decided.
8. Checker and producer are independent: tampering with the producer's boolean is rejected.

## 7. Scene-constructor forensic review

**Why `+G` was trivial (observed).** G sits on the goal cell, so GOAL_OVERLAP (`certificates.py:51-75`), an endpoint-only static proof, decided it in 0.5–0.7 CPU-s. This says nothing about robot access.

**Why every `+A*` no-repair query stayed UNKNOWN (observed + code).**
- The frozen rule makes **A the earliest-interrupting non-goal cell of the archived path** (`d2.choose_blockers`, `d2.py:144-171`). The archived path starts with the home → pregrasp sweep from q0 = (90°, 90°, 90°).
- The earliest interruptions are therefore cells **near the base, in the link-0 annulus between q0[0] and the target and goal directions**:
  - g4c_r00 A: cell 57, ρ 0.382, 47.1°;
  - g4d_R1 A: cell 42, ρ 0.361, 19.4°;
  - B and S are also in the annulus.
- This produces **sector confinement plus body overlap**. That is a genuine access obstruction, but deciding it needs exactly the missing theorem (g4c_r00) or a motion proof (g4d_R1).
- **Reroutability is not established** on any `+A*` root: no no-repair witness exists. C1 shows reroutes exist in principle.

**Why g4c_r00 is fast and g4d_R1 slow.**
- **Observed:** g4c_r00's failing queries end with all connector failures link-0-certified (D2) in 2–14 s; g4d_R1's run four RRT failures at 441–870 CPU-s per unit.
- **Hypothesis:** in g4d_R1 the target is inside the L1 radius, and the inserted obstacles crowd the folded-arm workspace, so screen-passing in-sector pairs exist and the RRT faces narrow passages.

**Occupancy-only order contrasts (observed).** Both `+A+S` negatives are `ORDER_FIRST_ACTION` with **stage PLACE**: `seq:d2_g4c_r00_AS:o04>49.o05>48` and `seq:d2_g4d_R1_AS:o04>41.o05>40` (`certificates.json`). A's destination is occupied by S. That is occupancy, not access.

**A recorded access-order candidate already exists (pilot r19, observed).**
- `seq:g4c_r19:o01>28.o00>27` is **VERIFIED_FEASIBLE**.
- `seq:g4c_r19:o00>27.o01>28` is UNKNOWN only because its **first action from q0** ended `ALL_PAIRS_CERTIFIED_BLOCKED`.
- The destination cell 27 is free, and both screens passed (no ORDER_FIRST_ACTION was produced). o01 at cell 19 sits directly beside o00 (cell 11), and o02 at 6.7° bounds the free sector.
- If (iv) accepts that first action, the pair is a decided **same-endpoint, access-based** contrast (J2).
- The same certificate decides the omission `seq:g4c_r19:o00>27` (remainder after dropping `o01>28`), giving Δ^O = +1 against the positive.
- The other single omission `o01>28` is already NEGATIVE (GOAL_OVERLAP).

**Decided fixed-robot effects without a nominal-sweep explanation.**
- If (i) certifies `seq:d2_g4c_r00_A:empty`, then `scene:d2_g4c_r00_A:o04>49` (VERIFIED) gives **Δ_I = +1 decided**.
- On `+A+B`, the singleton `o04>49` and the joint `o04>49.o05>41` are VERIFIED. If row 1 (`o05>41`) and row 6 are certified, all four sides are decided and κ is measurable.
- Recovery witnesses already exist on the same roots:
  - `+A`: `o04>49`;
  - `+A+B`: `o04>49`, `o04>49.o05>41`, `o05>41.o04>49`;
  - `+A+S`: `o05>48.o04>49`.

  So Q3 would be met on a **nontrivially** blocked root, without new collection.

**Small auditable constructor (DESIGN HYPOTHESIS — UNTESTED; only if route A's validation passes).** Each step is static and zero-planner unless stated.
1. Start from a fresh J0 base whose target lies at ρ ≈ 0.5–0.65 m, with predeclared seeds. Avoid targets inside the L1 radius, given the g4d_R1 cost.
2. Enumerate single and double insertions **in the link-0 annulus between q0[0] and the target and goal directions**, plus grasp-neighbour occluders.
3. Admit a variant **only if the static certificate (i)/(iv) or TARGET_PICK decides $Y_0=0$ before any planner call**.
4. Declare repairs that move a blocker out of the annulus (ρ > 0.4608) or out of the angular interval. Spend planner calls only on these positive sides.
5. For order: two annulus objects X and Y such that X's first action is sector- or screen-excluded with Y present.
6. For J1: two blockers that each keep the certificate valid when the other is removed. The singleton edits are then decided statically; the joint edit needs a witness.
7. Keep the full 3R arm, fingers, rigid attachment, 8×8 cells, 48 grasps, q0, SAFE_RETREAT and the UNKNOWN policy unchanged.

## 8. Evidence-to-learning impact (today)

- **Architecture A** (local/sequence) has 30 positive / 6 negative ordered and target labels.
- **B/C** have 3 substantive complete pools. All are on `+N`/`+G` variants, with no access obstruction. The only decided nonzero scene effects are the trivial `+G` Δ = +1 (×2), plus Δ = 0 on the nuisances.
- **No decided nonadditivity.** The only order contrasts are occupancy-based.
- Therefore methodology falsification items **1** (order learning) and **2** (explicit causal coupling) currently hold for the D2 data. Pool completeness here is **not** general causal coverage, and no B/C structural advantage could be attributed from these data.

## 9. Ranked options and the recommendation

**Decision rule applied:** choose the cheapest option that can turn an *existing* UNKNOWN into a sound, nontrivial, Q2-relevant label with recovery evidence already on disk, and whose failure is detectable without planner calls.

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A — certificate first** | The theorem is sound as scoped (§6). It targets the 3 Q2 rows, 3 scene-edit rows and 9 pilot first-action/fixed-robot units. Validation is **0 planner calls**. Same-root recovery witnesses and an access-order pair already exist. | Applicability is unverified (D4 data were not saved). It is a new certificate kind. One lineage (g4c_r00) for Q2. Place side open (A7). | **Chosen** |
| B — construction first | Fixes the root cause (earliest-interrupt rule) | Without (i), new blocked scenes face the same undecidability. It would spend planner CPU before knowing whether anything is certifiable. | Conditional follow-up after A |
| C — combined | — | The two bottlenecks are not *individually demonstrated* yet (A's applicability is unverified) | Rejected for now |
| D — blocked | — | The domain *was* reconstructable from code (§4) | Rejected |

**Risks:**
- (i) may certify **none** of the three, if unrecorded in-sector picks pass or are uncertified. That is detected statically, and route B then follows.
- If you reject A1 (declared-skill domain), every screen-based kind, including existing ones, must be re-scoped.
- Implementing inside `certificates.py` or `ordered.py` would break the source binding of the frozen POC_S plan. Hence the new-module requirement below.

## 10. Proposed next micro-pilot contract (all NOT_RUN until you approve)

### P3a — certificate implementation and static re-adjudication (zero oracle calls)

**Code allowed.** New `sector_cert.py` (producer + independent checker + scoped adjudication wrapper, target ≈ 150 logical lines), new `tests/test_sector_cert.py`, one `run.py` command and a new run directory `runs/g4c_d2_p3_static/`.

**Immutable.**
- Source: `skill.py`, `planner.py`, `motion.py`, `geometry.py`, `certificates.py`, `ordered.py`, `verify.py`, `evaluate.py`, `g4d_run.py`, `g4c_pilot.py`, `d2*.py`, `d2_poc*.py`, `config*.toml`.
- Data and reports: every existing `runs/` directory and reports 0001–0017.
- Historical labels are never rewritten. Output is a **separately versioned adjudication**.

**Frozen target list (declared now).**
- POC_S rows 1, 2, 3, 4, 6, 10 (fixed start).
- Pilot: `scene:g4c_r19:o00>9`; `seq:g4c_r19:o00>27`, `o00>27.o01>28`; `seq:g4c_r08:o00>15`, `o00>47`, `o00>47.o01>46`, `o01>46.o00>47`; `seq:g4c_r14:o02>39.o00>38`, `o02>39.o01>7.o00>38`.
- **Negative controls:** every recorded positive witness (POC_S 32, pilot 13, G4D), each at its own start and world.
- **Excluded by scope:** rows 5, 7–9, 11–15.

**Proposed limits.**

| Limit | Value |
|---|---|
| Planner, target-evaluation and relocation-skill calls | **0** (instrumented; any call fails the run) |
| Aggregate CPU | ≤ 900 CPU-s |
| Per query | ≤ 60 CPU-s |
| Workers | 1 |
| Wall | ≤ 1,800 s |
| Separately requested | One full regression suite and six replays (≈ 300 CPU-s; these make 621/60 historical in-process planner calls) |

Extrapolation: the 15 fast units spent 2–14 s *including* screens.

**Predeclared gates.**
- **G1:** checker independent of producer; tests pass.
- **G2:** zero contradictions with any recorded positive.
- **G3 (scientific):** ≥ 1 of rows 4, 6, 10 certified at ORIGINAL_TARGET scope. Then Q2 (nontrivial) and Q3 (same-root recovery) are re-evaluated on existing evidence.
- **G4:** report whether the r19 pair becomes a decided access-order contrast.
- **Futility:** 0/3 Q2 rows **and** 0/9 pilot units certified ⇒ stop the certificate line for this geometry and go to P3b.

**Isolation.** Identical evidence, identical units: the only change is the adjudication. So any change in decided counts is attributable to the certificate.

### P3b — construction micro-pilot (conditional on P3a; separate authorization)

**Scope.**
- 4 fresh independent bases (J0 rule, predeclared seeds, one lineage each).
- Per base, one statically certified "sector" variant and one "occluder" variant, admitted only if $Y_0$ is decided negative statically.
- Per admitted variant, ≤ 10 frozen units: 2 single-move repairs, 1 same-endpoint order pair, 2 singleton scene edits and 1 joint edit, 2 omissions, and 1 robot start.
- **Control:** each base also gets the old-rule "+A" (earliest interrupt), evaluated **statically only**, to compare certifiability rates on the same base, target and q0.

**Proposed limits.**

| Limit | Value |
|---|---|
| Units | ≤ 80 + 4 base-witness units |
| CPU per unit | 900 s, cancellation at 870 s |
| Aggregate CPU | ≤ 9,000 CPU-s |
| Workers | 1 |
| Wall | 1,800 s per unit / ≤ 12,000 s overall |
| Planner | 4,000 nodes unchanged |
| Calls | relocation ≤ 100, target ≤ 84 |

Extrapolation basis: g4c_r00-type units cost a median ≈ 5 CPU-s, a maximum of 103 CPU-s, and 596 CPU-s for 34 units. The cap covers ~10 tail units at 870 s. This is unverified.

**Futility.** Stop after 2 bases with no statically admitted variant; then no planner CPU is spent on the remaining bases.

**Acceptance gates (predeclared, per contract §6):**
1. One nontrivial ORIGINAL_TARGET certified negative.
2. A same-root complete relocation + target + SAFE_RETREAT witness.
3. A decided nonzero fixed-robot scene effect.
4. A decided positive-repair omission contrast regenerated from $S_0$.
5. An access-based same-endpoint order contrast, otherwise "order-access NOT_ESTABLISHED".
6. B/C completeness and nonadditivity only where genuinely decided.

Gates 1–2 are reported separately from 3–6.

**Expansion and stop rules.**
- Expansion (a re-scoped POC_F) only if gates 1–2 hold on **≥ 2 independent lineages**.
- **POC_F as specified in 0015 (194 units, nominal-sweep variants including `+A+B+C` on g4d R0/R1) should not be approved.** Its g4d-type units are predicted, from the observed 6,655 CPU-s for 0 decided, to concentrate cost on search limits.
- **Stop the D2 line** if P3a's G3 and P3b's gates 1–2 both fail. Then report, per methodology falsification items 1–2, that access-order and explicit-causal contrasts are not obtainable with sound certificates in this model.

## 11. Integrity and zero-call attestations

- `git diff --name-status`, before and after this stage: identical, `D latent_causal_tamp_implementation_guide_v1_8.pdf` and `D latent_causal_tamp_specification_v1_6.pdf` (pre-existing; not touched).
- The only new file is this report, untracked.
- No code, configuration, test, schema, plan, manifest, run artifact or earlier report was modified.
- No project module was imported.
- **Planner calls 0, target evaluations 0, relocation-skill calls 0, IK/oracle executions 0, new labels 0, training 0.**
- No project tests or replays were run, so no test or replay result is claimed for this stage.
- The axis-clearance figures in §5.2 are hand arithmetic on saved joint values and saved object poses. They are labelled INFERENCE.
- **Commit and push: not performed.** Contract §8: "If the working tree has unexpected tracked changes, do not commit; report blocker instead." The two tracked PDF deletions are such changes, even though they appear to be byte-identical moves. The report is ready to commit as a report-only commit once you confirm them.

## 12. Stop and handoff

**STOP.** At most two authorization decisions are requested:

1. **P3a.** Do you approve:
   - A1, the declared six-phase skill with 48 grasps as the permitted target domain for certificates;
   - the A7 position (pick side plus sector-only place side in v1; place-screen exclusions deferred);
   - the new-module code changes listed in §10;
   - the zero-oracle static budget (≤ 900 CPU-s, 1 worker, ≤ 1,800 s wall), plus the separately listed regression run?
2. **P3b**, only after P3a reports: the construction micro-pilot scope and budget in §10, or a stop.

Nothing else is authorized. POC_F, the remaining G4C roots, training, 3D and hardware are not started.
