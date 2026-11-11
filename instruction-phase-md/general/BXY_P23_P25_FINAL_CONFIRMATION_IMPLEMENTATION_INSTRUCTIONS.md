# Approach B — P23–P25: Final 2D K0–K4 Confirmation and Methodology Closure

**Execution contract for Claude Opus 5.5 High**  
**Prepared:** 2026-11-01  
**Repository:** `Narendhiranv04/latent-causal-tamp`, branch `approach-b-xy-v1`  
**Start and immutable evidence anchor:** `bcad58e68c09f5d7ec3cc5942f5fc7a40c9315a4` (P22)  
**Status of independent cohorts:** `bxyg21confirm` and `bxyg34confirm` have NOT been generated according to P22. Verify anew before work.  
**Purpose:** Finish the already-implemented 2D Approach B methodology with **correct one-shot independent K0–K4 testing**, not more architecture engineering.

> **Hard gate:** P23 is an implementation/validation stage with **no new physical teacher labels, no training, no confirmation scene generation, and no test predictions**. P24's costly independent collection is **NOT authorized by possession of this file or by completion of P23**: require a new explicit human approval for its frozen CPU/wall/worker budget. Prepare all machinery to run P24 automatically upon such approval; do not request serial permission for innocuous P23 work. P25 analyzes exactly the one preauthorized P24 cohort, without a second test look or unregistered retuning.

## 0. Read authoritative material in order

1. `Approach_B_Final_Methodology_2026-10-31.pdf` (historical frozen intended specification).
2. `responses-phases/0129A_APPROACH_B_IMPLEMENTED_METHOD_ADDENDUM.md` (authoritative *implemented* GEO2/SYM extensions).
3. Reports `0126`, `0127`, `0128`, `0129` in `responses-phases/`, including incident, lower-bound and negative findings; also `0123`–`0125` for provenance.
4. Frozen P21/P22 design, evaluations and artifacts: `TRAINING_DESIGN_P21.json`, `EVALUATION_P21.json`, `FROZEN_MODELS_P22.json`, `CONFIRM_PLAN_K04.json`, `CONFIRM_ANALYSIS_P22.json`, P20 readiness and wave summaries.
5. Inspect *actual source*, including `bxy_teacher.py`, `bxy_p19_audit.py`, `bxy_p20_k34.py`, `bxy_p21_k34.py`, `bxy_p21_eval.py`, `bxy_p17.py`, `bxy_p17_eval.py`, `bxy_p18.py`, `bxy_p22_freeze.py`, local checkpoint availability and the existing tests. Do not rely solely on prose summaries.

Use a new versioned namespace (`bxy_p23_v1`, `bxy_p24_v1`, `bxy_p25_v1`) for files and evidence. Preserve all P-min through P22 artifacts byte-identically. Commit at each gate; verify local HEAD = origin and preserve exact SHA and SHA256 provenance.

## 1. Scientific facts already established — preserve these exactly

- Physical teacher: planar 3R, finite-width links, 8x8 resting lattice, declared 24 approach directions x 2 elbows; up to six corrective relocations, then target action. Relocation `a_(t+1)` starts at **the achieved robot configuration** after `a_t`. **No interim homing.** After the last relocation only, connect from its achieved state to fixed `q_ref`, free gripper, then compose the separately verified target motion from `q_ref`.
- `X_q` = operational executability of the entire *ordered* corrective prefix **including terminal connector**. `Y_s` = feasibility of the target in the hypothetically edited scene from common `q_ref`, independent of whether that edit can physically be achieved. Shared endpoint -> shared Y, separate X for different orders. `X_empty=1` and no-op success = `Y0`.
- Root-consistent model: `P(Y_s=1)=sigmoid(b_s)`; `P(X_q=1|Y_s=y)=sigmoid(a_q+w_q*y)`; candidate success = `sigmoid(b_s)*sigmoid(a_q+w_q)`. Uncoupled E uses `w_q=0` and capacity-matched scene-aware X head. Keep F1–F5 testable; **do not assert F5 is helpful**.
- Base loss in October 31 document: `L_joint + lambda_J L_J`. Implemented D/E use **an explicit documented extension** `L_joint + lambda_J L_J + kappa L_SYM` (GEO2 + SYM). Travel regression uses *only* completed, independently replayed witnesses and includes relocation, connector, and target travel. No supervised trajectory synthesis.
- P20: 86 independent new development scenes, 2,174 labelled of 2,202 planned queries (28 unattempted on an incomplete root), 14 **certified necessary K3**, 7 **certified necessary K4**. Physical K4 demonstrated, but below frozen 10-root threshold for inferential K4 claims; `K4_PHYSICAL_DATA_NOT_ESTABLISHED` is a **threshold verdict**, not a denial of 7 witnessed K4 examples.
- `K_intent` is only a construction goal. `K_LB` uses the union access abstraction. `K_cert` enumerates all sets of `K-1` removed movable obstacles and requires a definite target-side pick or placement closure for each. `K_catalogue` is shortest replayed successful candidate, with shorter admissible candidates decided. **Certified-necessary K requires both**. This lower bound is scoped to the declared grasp family and monotonic collision assumptions; never claim universal global minimality.
- P21 five-fold family-grouped, three seeds, **398 total development roots**; outcome-blind population `OB` = 201 roots / 150 initially infeasible / 63 with a verified repair. D 0.289 unconditional repair, 0.688 availability-conditioned, unnecessary 0.140. E 0.287 / 0.683 / 0.160. Matched DIRECT-GEO 0.258 / 0.614 / 0.193. XYQ-BASE 0.056 unconditional. Geometric analytic rule 0.207 / 0.000; verify-first evaluator-only ceiling 0.420.
- D−DIRECT: +0.031 [−0.002,+0.064], **not established**. D−E: +0.002, no meaningful coupling benefit. D−G (order-invariant): strong strict-order and exploratory K3/K4 selection advantage; 46 strict order pairs on K34 roots (not independent root count), 33 distinct roots and 3 repeated seed predictions in the strict evaluator. On 14 K3 roots, D conditional 0.74; on 7 K4 roots, D conditional 0.95 — **descriptive** and conditioned on known repair availability, not general success probabilities.
- P22 froze 15-checkpoint **D/E/A ensembles**, not G; P21 development numbers are **OOF 3-model, fold-rule** estimates and are NOT performance estimates for the 15-member pooled-rule ensemble. Existing second copies of checkpoints on the **same disk** do not satisfy off-machine/independent-volume durability.
- P22 proposes 440 ungenerated construction slots under `bxyg34confirm` (55% K4 intent, 25% K3, 5% K2, 15% K0), expected ~50 verified K3/~41 K4/~40 K0, about 70k CPU-seconds, but these are uncertain *development-based projections*, not known test outcomes. No geometrically distinct K3/K4 generator is established.

**Treat statements above as provenance, never as additional training labels or as independent-test results.**

## 2. Fixed scope and prohibition on changing the science midstream

**Do:** freeze/evaluate existing arms and approved analytical reference rules; harden the collector; correct protocol ambiguities openly *before test scene generation*; collect exactly one locked outcome-blind confirmatory cohort if approved; produce honest final paper-quality evidence and figures.

**Do NOT:** change neural architecture, introduce another latent variable, add a new learned factor, tune GEO2/SYM, tune hyperparameters on confirm, increase robot/planner capabilities, silently alter F1, X/Y meaning, `q_ref`, `K_cert`, any teacher budget, candidate grammar, or select an easier sample after seeing outcomes. No 3D, no external APIs, no new training unless a separately named follow-on exploratory study *after* the registered result. Never reclassify budget failure as certified impossibility. Do not hide failed/negative results.

### Essential fairness/attribution

- Main claim to test is **whole-system repair selection** by X/Y against matched geometry-informed DIRECT. A positive whole-system difference would not prove *factorization alone* caused it because X/Y also has different component labels and auxiliary supervision; explain this in final report.
- F2 order-awareness is an important **separate, prespecified** hypothesis, so include the trained matched G arm in final frozen comparison or clearly document why impossible. Do not relabel DIRECT as order-invariant: DIRECT has ordered features.
- Keep F5 quadratic coupling D vs E; a positive point estimate below the frozen meaningful-effect criterion is not a supported F5 result. No causal edge interpretation of `w`.
- GEO2 is analytic and label-free, but it shares geometry with the K34 scene generator; a new-seed test from the same generator cannot prove cross-generator transfer.

---

## 3. P23 — Final protocol, frozen control, durability and execution preflight

**Authorization:** this file authorizes *read-only and synthetic-test* work only, with a proposed administrative budget **<= 3,000 CPU-s, <= 5,400 s wall**, CPU-only, max four 1-thread workers; no physical teacher, dataset generation, training or confirmation evaluation. All outputs must be reproducible from P22. If a local disk operation is not safe, report blocker and stop at this gate.

### P23.1 Reproduce and lock custody

1. Verify exact P22 HEAD before modifying new files; check all P-min–P22 immutable hashes and six archived replays. Reproduce P21 `EVALUATION_P21.json` (ignore only documented machine-dependent process-time entries).
2. Check all 90 P21 checkpoints with hashes and *test-load* selected members for D, E, A, **G**, compare stored held-out predictions bit-for-bit or to frozen numeric tolerance. Do not infer checkpoint paths from filenames blindly; verify `RESULT.json` hash + run ID.
3. Create durable second-copy custody on a physically different volume or an approved off-machine location, **only if available, with exact hash verification and a restore test**. Never upload model binaries to public GitHub by default; do not include credentials or private paths in shared reports. If no independent storage exists, issue `BLOCKED_CHECKPOINT_CUSTODY` with clear steps for the user; same-NVMe duplicate is not an acceptable substitute. Do not mark P23 PASS on this item until complete.
4. Verify `q_ref=q0` assumption remains true for all frozen input caches, and confirm all features come only from `scene`, `goal`, `q0/q_ref`, proposed candidate actions and geometry. Add mutation/invariance tests to ensure teacher labels, constructed K intention, certificate flags and witness content never enter scorer inputs.
5. Preserve P22 frozen manifests; make **new append-only successor manifests** for amendments. Record reason, parent SHA, checksum, machine software/config, evaluator code hashes, checkpoint hashes and actor selection rules.

### P23.2 Include the important G control without retraining

- Recover P21's 15 existing `G:XYQ-GEO-SYM-ORDINV` checkpoints, validate their hashes and build one P23-frozen G predictor using **exactly the same 15-member averaging semantics** as P22 D/E/A.
- Compute G's single pooled rule from *P21 early-stop/development predictions only*, using the already frozen grid and criterion; no new rule search or P24/test data. State its chosen alpha, no-op gate, beta, gamma.
- Create `FROZEN_MODELS_P23_APPEND.json` that references immutable D/E/A from P22 and adds G, with all SHA256s. If anyone suggests a method change, first explain why the frozen D/E/A/G system cannot be executed; do not modify it silently.
- G is a **secondary mechanistic control**. Pre-register exact-permutation, same-endpoint, F1-admissible, X-discordant order concordance, including a certified-negative subset, using tie tolerance `1e-8`. Aggregate *per root before inference*: do not count pair×seed as independent test samples.

### P23.3 Resolve any protocol ambiguity *before test generation*

Create successor files `CONFIRM_PLAN_P23_LOCK.json` and `CONFIRM_ANALYSIS_P23_LOCK.json`, referencing SHA256 of the untouched P22 originals. They must unambiguously specify:

- one fixed 440-slot population (no slot replacement, no adaptive sampling); the P22 mix and K34C/V21B generator are unchanged; all attempts/rejections recorded;
- two outcomes with explicit denominators: **unconditional** correction success over all initially infeasible roots (including those with no verified candidate), and **availability-conditioned** success only among initially infeasible roots with at least one verified candidate; report both, and predeclare one authoritative inferential priority/hierarchy so no favorable post-test endpoint switching; reconcile `CONFIRM_ANALYSIS_P22.json` wording rather than quietly changing it;
- primary comparisons D vs A, E vs A, D vs E, with Holm correction across the prespecified family; exact decision threshold (paired CI lower > 0, point improvement >= 0.10, unnecessary-repair increase <= 0.05). If deciding one endpoint primary and one secondary, make it explicit; otherwise use a prespecified gate requiring consistency across both without post-hoc choice. **Preserve historical thresholds; changes require an explicitly versioned rationale and pre-test approval**;
- an additional, separately declared order test D vs G (and optionally E vs G), root-clustered confidence intervals for strict pair rankings, actual selection on K3/K4 repairable roots and unnecessary-repair guardrail, with declared multiplicity family. Do not count 309 pair×seed comparisons as 309 independent samples;
- K label determination: `K_cert==K_catalogue` for certified necessity; report K3/K4 with and without requirement; show per-generator accepted/rejected strata, witnessed X+connector+Y and Y prefix pattern;
- certified vs fixed-budget negative kinds, observed/unobserved/censored semantics, presence/absence of complete travel witness, no-op handling and initial q_ref;
- per-arm ensemble averaging: `mean p_succ`/`mean J_hat` over 15 models, F1 first, frozen rule, *no* calibration/rule tuning on any test records;
- reference baselines: no-op; shortest and displacement; geometry-access rule; verified-first **evaluator-only** oracle upper bound with verification calls (never deployed or described as learned);
- paired bootstrap B=10,000 at **root family** level, seed fixed; prespecified missingness/failed collection rules and Holm comparison corrections; confidence-interval method and handling of near-ties;
- practical meaning of “success”: teacher-verified candidate (X = 1 and Y = 1) including connector, with replay hashes, not merely model's predicted success;
- power diagnostic using P21 paired *difference* SD (approx 0.30) and sensitivity analysis (0.3, 0.5, 1.0); realized K3/K4 sample may be below forecast. The P22 0.062 half-width is a projection, not a guarantee.

**No changing the dataset after seeing any P24 label, candidate success or model prediction.** If substantive corrections to the locked P22 analysis are necessary, document explicitly that they are prospective amendments, not the original preregistration; commit and hash them *before* P24 generation.

### P23.4 Make the one-shot engine resilient — fix the P20 duplicate-supervisor failure

- Implement *one shared-filesystem authoritative supervisor lock* (OS `flock`/atomic lock + owner UUID + manifest + heartbeat), not a process-ID-only check. Host/bwrap/PID namespaces can make `ps` incomplete. A second launch MUST refuse to supervise if a valid lock or reservation exists.
- Stable per-root work reservations and atomic result writes with compare-and-swap/no-overwrite; stale ownership requires explicit documented manual recovery, not blind restart; no simultaneous workers for the same root.
- Persistent append-only ledger with CPU and wall accounting for construction, labelling, cache creation and evaluation; double-counting conservative when uncertain; per-root and aggregate limits; `RLIMIT` semantics verified.
- Durably checkpoint each completed query; on crash, reconstruct from manifest + result hashes and resume unattempted queries only, without changing the frozen catalogue or budget disposition. If a root exhausts its cap, distinguish `UNATTEMPTED` from `CENSORED` and operational `0`.
- Add deterministic *simulated/mocked teacher* smoke tests for: duplicate supervisors; kill+restart; partial results; duplicate worker requests; corrupt hash; out-of-order finishes; exhausted root; total budget stop; mismatched scene identity; full eligibility and no-label-peeking. No real confirm root or teacher query during smoke tests.
- Validate P24 runner can **load all frozen models and compute features for a synthetic scene** with the same input contract. No test scores and no hand-picked P24 geometry required.

### P23 exit gate

Deliver `responses-phases/0130_BXY_P23_FINAL_CONFIRMATION_PREFLIGHT.md`, versioned manifests, test logs, concise decision table (`P23_READY` or named blocker), exactly what changed and what is unchanged, and test snapshots. Pass only if checkpoint custody is durable; G is frozen; frozen P22 analyses still intact; exclusive collector/recovery tests pass; one-shot analysis is unambiguous; no confirm scenes generated. Commit/push and report SHA.

---

## 4. P24 — One-shot 440-slot independent K0–K4 confirmation (SEPARATE EXPLICIT AUTHORIZATION)

### Authorization boundary

**Do not start this section automatically.** P24 requires explicit human approval for a versioned `AUTHORIZATION_P24.json` with the precise compute ceilings and hashes. Proposed planning envelope based on P22: **90,000 aggregate CPU-s** (70,322 projected plus contingency), **40,000 s wall**, **4 single-thread workers**, **1,400 CPU-s max per accepted root**, P-min frozen per-query teacher budget, and a separately budgeted eval reserve included inside the aggregate limit. These are proposed ceilings, NOT already authorized. If these resources are not approved, stop after P23 ready with a one-line authorization request and exact manifest/estimates; do not partially generate cohort.

### P24 immutable protocol

1. Before generating any scene, freeze/commit `AUTHORIZATION_P24`, `CONFIRM_PLAN_P23_LOCK`, `CONFIRM_ANALYSIS_P23_LOCK`, `FROZEN_MODELS_P23_APPEND`, scorer/teacher/feature code versions, supervisor version and expected input hashes. Recheck absence of `bxyg34confirm` scenes. One preflight hash mismatch => STOP.
2. Generate the exact **440 predetermined slots**, using P22 mixture and frozen K34C/V21B construction logic, new disjoint namespace. Record every slot, accepted/rejected seed/spec and all construction attempts, without changing slot composition or replacing rejections.
3. Freeze each accepted root's outcome-blind finite candidate catalogue and query set **before** calling the teacher for that root; preserve analytic F1 and side X/Y query identities and shared-Y deduplication.
4. Label all frozen queries within fixed teacher budgets; store status, negative type, achieved-state continuity and terminal connector, replayed target witness, all prefix Y, omission queries and successful travel. No oracle outcomes enter model selection or candidate creation.
5. **One and only one** execution of frozen D/E/A/G on the entire cohort with no interim looks, threshold changes, checkpoint changes, per-stratum retuning or repeated post-test launches. Record input/view SHA, member hashes, predictions, selections and witness-backed outcomes.
6. If projected K4/K3 yield is not achieved, keep all data and label analysis UNDERPOWERED per locked rules; **no replacement wave** after any test-model look. Never selectively exclude a root based on failure or difficulty; only registered missing/censor cases are excluded from a specific denominator.
7. Report costs and operational failures including duplicate refusal, per-root exhausted budgets and physical teacher budget-limited negatives. No model updates, new scene difficulty tweaks or second test are permitted within P24.

Deliver `responses-phases/0131_BXY_P24_ONE_SHOT_CONFIRMATION.md`, locked result tables, per-scene source hashes, model and baseline predictions, cohort construction/label audit, one-shot status, verification and CPU ledgers, tests/replays, SHA. Stop on any custody or contamination event and disclose precisely what was exposed.

---

## 5. P25 — Final evidence, manuscript-ready figure set and verdict

P25 uses **only the one locked P24 output**, and the historical development artifacts separately. It may compute *registered* uncertainty/figures but must not train, retune or collect more scenes. If P24 has not been authorized/completed, P25 should **not invent an independent result**; deliver a paper-readiness report labelled `NO_CONFIRMATION_RUN`.

### Required results and separation

- Primary paired comparisons D/A, E/A, D/E with exact registered multiplicity and false-repair guardrail, on explicitly defined unconditional/available subsets.
- Separate exact-action-multiset order comparison D/G (E/G if locked), same endpoint, both F1-admissible, X-discordant, all and certified subsets; independent root counts and root-level bootstrap; actual selection contribution on K3/K4 repairable roots.
- K0 no-op correctness and harmful false-repair rate; K1/K2/K3/K4 conditional success with n and uncertainty; **K3/K4 necessity** verified by both witness and K_cert; no inflation of per-seed n.
- Candidate availability, oracle verification cost and upper bound; compare to analytic geometry-access rule and DIRECT. Distinguish learning of Y, X and order effects; report loss/calibration/omission and witnessed travel on matched successful roots.
- Generator shift limitations: new seeds, **same K34 doorway family**; do not claim cross-generator or 3D generalization. No evidence of F5 coupling advantage unless the frozen tests genuinely establish it.
- Plot exact 2D stories from **actual independent replayed witnesses** (only when allowed by the registered display protocol), one K3 and one K4 if available, with q0 -> ordered moves -> one q_ref connector -> independent target. Visualization must not imply home resets, guaranteed global-minimum, or invented trajectories.
- **No fresh architectural complication**: model remains original X/Y, F1–F5 test with GEO2/SYM additions. If direct predictor ties/wins, say so. Final conclusion should tell user whether evidence supports whole-system advantage, ordering, coupling, K3/K4 and 2D readiness.

Create `responses-phases/0132_BXY_P25_FINAL_METHOD_AND_FINDINGS.md`, machine-readable decision manifest, a concise manuscript-ready `METHODOLOGY_FINAL_IMPLEMENTED.md` (original Oct31 spec unchanged, P22 addendum preserved and cited), table of claims supported/unsupported, and a printable results PDF generated from actual locked artifacts. Include at least: architecture+teacher protocol schematic, K-by-stratum coverage, success/false-repair frontier, paired CIs, strict order, omission, matched travel, failure breakdown and representative replay snapshots. Test/replay and commit/push.

### Mandatory stopping rules

- If P23 cannot verify truly independent checkpoint custody or cannot make the one-shot engine safe: stop before P24.
- If P24 is unauthorized: report `P23_READY_FOR_AUTHORIZATION`, do **not** generate even one confirmatory scene.
- If P24 loses blindness or frozen protocol integrity: stop and label compromised; do not silently rerun with a new seed.
- If P24 result is negative: preserve it. No additional model sweep on the confirmatory data.
- If K4 n is small: report uncertainty explicitly; do not claim complete long-horizon validation.

## 6. Deliverables, minimal code and quality bar

Keep new code limited to small modules such as `bxy_p23_preflight.py`, `bxy_p24_confirm.py`, `bxy_p25_report.py` and corresponding tests, **reuse** earlier generator/model/evaluator functions; avoid duplicating P20/P21 logic. Prefer <400 lines per new module; split only if truly needed. Separate config/manifests from executable logic. No change to previous code unless required for a documented, tested compatibility bug; never rewrite historical artifacts.

### Required per-gate report schema

1. Start HEAD and source hashes.
2. The exact original research hypothesis and relevant success/failure rule.
3. Implementation delta, including unchanged components.
4. Data custody, counts, strata, independent family IDs and censor/negative types.
5. Resource ledger (CPU, wall, workers, incidents, conservative charges).
6. Detailed results with **sample sizes and uncertainty**; no cherry-picked screenshots.
7. Explicit leakage and reproducibility checks; tests and six archived replays.
8. Failures/limitations, revised claim status, STOP/GO gate and pushed SHA.

### Final scientific principle

The aim is not to force an acceptance criterion. The aim is to **finish the promised 2D K0–K4 methodology faithfully, demonstrate what it genuinely learns, and obtain one defensible independent test**. The result may support only order-awareness, while matching DIRECT on success; that is a valid outcome and must not be hidden.
