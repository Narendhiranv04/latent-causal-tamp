# RSS final architectural ablations: structured energy readouts and execution-order sensitivity

**Scope:** existing 2D and 3D K≤3 datasets only. Frozen inference and evaluation; no learning, no new scenes, no training interventions, no auxiliary losses, no MCTS. This is a separate work package from the completed complete-repair cVAE study and the ongoing K4/K5 3D study. Version 1.0, 2026-11-26.

## 1. Scientific objective and context

Approach B solves manipulation among movable objects: given a scene and an original target pick-and-place task, propose corrective relocations, construct legal ordered repairs, and evaluate whether the repair can be executed (X) and whether its final object arrangement permits the original target task (Y). The released method uses a per-object task-conditioned cVAE, frozen top-four destination proposals and exhaustive enumeration of legal K≤3 ordered repairs, followed by a learned structured energy model. Use this terminology in the paper; do not call the method Boltzmann. The robot and physical teacher contracts remain unchanged.

Two questions remain:

- RQ2a: Does combining execution and target feasibility improve *physically verified repair selection* over either readout alone, holding the proposal pool fixed?
- RQ2b: Does the frozen model meaningfully distinguish different execution orders of exactly the same object-to-destination assignment, and does using its order predictions improve order choice over a blind order?

These are distinct from the previously trained independent-X/Y, order-invariant and direct-Z architecture ablations. Do not claim inference-time readout masking is equivalent to retraining those alternatives. A successful repair is not proof that every moved object was necessary or a causal blocker.

### Historical evidence to preserve

- The complete-repair cVAE study (branch `naren/rss27-complete-repair-cvae`, final `c50a2ebb19`) established a 3D improvement from 50.7% to 74.7% when its fixed candidate pool was reranked with frozen X/Y. The released system achieved 75.3%. In 2D the corresponding rates were 39.3%, 47.3% and 54.7%; UNKNOWN was 24–35%, so comparisons were inconclusive. This justifies feasibility evaluation in 3D, not the necessity of each X/Y component or of the per-object proposal design. The study is locked retrospective, not a newly independent benchmark.
- Earlier 2D ranking diagnostics, `repair_ranking/reports/P1_DIAGNOSTICS.md` at `87ebf65d24`, reported within-root Z concordance .718 for joint, .706 for Y, .451 for conditional X1 on 165 K1/K2 VAL roots. The latter is **not** a diagnostic of X conditional-label accuracy: the target was Z across both Y classes, not X restricted to Y=1. The same report gives global conditional-X AUROC .714 against actual X on Y=1 rows. Only two same-endpoint different-order discordant pairs were available in that diagnostic. These are exposed VAL and selectively labelled candidates. Do not reproduce the misleading claim that X anti-ranks its own label. This work must cover K3 and 3D and avoid conflating these labels.
- The existing draft's historical 2D ablations report full 51.8%, w/o coupling 49.4%, w/o ordering 47.2%, direct Z 38.5%. Audit exact source, cohort, checkpoint and rule before using them in a table. Do not compare historical full-cohort percentages directly against a stratified 150-root cohort. New comparisons below address the remaining readout and mechanistic questions, not replacement of existing ablations.

## 2. Repository and immutability

Repo `Narendhiranv04/latent-causal-tamp`. Suggested independent branch `naren/rss27-xy-order-ablation` and worktree `.claude/worktrees/xy-order`, based on the verified remote final CR commit `c50a2ebb19` (resolve full SHA and check ancestry of `87ebf65d24`). If unavailable, stop and report rather than silently use a different release. Do not merge. Existing worktrees, frozen code, checkpoints, datasets, caches and historical predictions are read-only. Do not kill unrelated jobs or consume resources reserved for K4/K5. Use a new run directory and an evaluator-private location outside tracked code. No copying large datasets or GPU caches. No protected historical TEST access.

Source landmarks (read actual code on host, not assumptions):

- `approach_b_final/search.py`: Root, Sampler, Scorer.
- `placement.py`, `construct.py`, `contracts.py`, `exhaustive.py`: original proposal grammar and streaming selection. `exhaustive.proposals` calls top-6 at seed 0 then uses top-4; `exhaustive.stream`, `Selectors.update/finish`, `score_root` implement the production exhaustive path. `finish` permits the no-op to compete below the no-op gate when it meets eta. Preserve that exactly for deployment comparisons.
- `xy.py`: `make_view`, `collate`, `XYNet.coeffs`, `predict`, `marginals`, `choose`. `repair_ranking/rr.py::readout` is a useful adapter but inspect its domain assumptions and use correct 3D geometry; do not import its data paths or protected split routines blindly.
- `benchmark.py`, `evaluate.py`, `construct._boot`: teacher and cache interfaces. `benchmark.teach` uses exact ordered sequence keys. Read `complete_repair_cvae/reports/P0_DATA.md`, `P0_PREREG.md`, `P5_FINAL_DECISION.md`, root `AMENDMENTS.md` and actual code for cache resolution.
- Frozen bundle reported at `~/abf_v34/approach_b_bundle`; hash all manifest files. Released seed-0 coupled arm D in both domains, S1 sampler `scratch_all`, seed 0, 64 latents, M=4, Kmax=3; rule reported `noop_gate=.5, eta=.3, alpha=beta=gamma=0` in both domains. Verify actual domain settings rather than hardcode if provenance differs. Do not use recently warm-started ranking checkpoints.
- Released TRAIN snapshot `abf_v32_fb0eef4f5ff433ee`; base VAL `abf_9de85710c2a7103f`. VAL was used for checkpoint selection and is DEV only. TRAIN labels can be summarized as in-sample context, never primary evidence. The CR study found 15 2D/58 3D VAL layout overlaps with TRAIN; report sensitivity excluding those layouts.

Minimal additive package:
```
approach_b_final/xy_order_ablation/
  plan.md
  starting_prompt.md
  README.md
  protocol.json
  readout.py       # frozen adapter + streaming selectors
  labels.py        # evaluator-only exact-contract ledger
  ordering.py      # matched assignment/permutation analysis
  run.py           # audit, freeze, infer, seal, evaluate, report CLI
  viz.py
  tests/test_contracts.py
  reports/
    figures/
```
Keep files concise and reuse existing helpers. No unnecessary frameworks. Save manifests, hashes, compact per-root outcomes, statistics and visualizations; do not save millions of candidate rows. Distinguish code, public inputs, sealed predictions and private labels; planner must not see true K, witnesses, outcomes or teacher code/caches. A process allowlist or equivalent tested separation is required. Teacher is evaluation only.

## 3. Exact readouts and comparisons

For original root S0 and ordered repair r, let A=canonical sorted object-destination assignment, b_A endpoint logit, a_r ordered logit and w_r learned coupling. Verify tau from the frozen source (reported 1); write formulas for tau=1 or explicitly divide logits by actual tau.

```
pY(A) = sigmoid(b_A)
pX0(r) = sigmoid(a_r)             # P(X=1 | Y=0)
pX1(r) = sigmoid(a_r + w_r)       # P(X=1 | Y=1)
pX(r) = (1-pY)*pX0 + pY*pX1       # marginal P(X=1)
p11(r) = pY*pX1                  # P(X=1,Y=1)
```

Use stable log-sigmoid for logs; no division by small pY. Production scorer uses original-root endpoint and ordered ideal-prefix features, not a teacher rollout. All probabilities come from the same frozen forward pass, no weight edits. Important: marginal X depends on pY through marginalization, and conditional X1 retains the learned coupling; neither is a separately trained pure X-only model. This is a readout/decision ablation, not a removal of all Y information from training. Inference-time w=0 is not the historical independent trained model; do not add it as a primary arm.

### 3.1 Candidate pool and primary deployment arms

For each public root: use original top-four candidates per movable object, all legal distinct objects/destinations, not originally occupied or target goal, exclude fixed objects and original target, lengths 1–3, all permutations. Keep all scene objects visible. No true K input; K only for evaluator stratification. Include identical no-op candidate `p_noop = pY(empty)` across all deployment arms. All arms share candidate order, pool hash/count, cVAE checkpoint and seed, score tensors, cost and tie-breaking. Stream once, update selectors per readout; chunk 8192 or audited memory-safe size; validate chunk parity and no silent truncation. The original selector must reproduce exact archived joint decisions, including competitive NOOP below gate. Use the same gate .5 and eta .3 for every arm; these are production-rule controls, **not** equivalent calibrated confidence thresholds for different events.

| ID | Repair ranking/admission score | Interpretation |
|---|---|---|
| J | p11 | original production method |
| X | marginal pX | execution-feasibility readout only for nonempty repairs |
| Y | pY | endpoint-feasibility readout only; order tie resolved using the same deterministic production rule |
| XC | pX1 | conditional execution readout; secondary diagnostic, not another primary arm |

All use original rule, tie keys and no-op handling. X-only no-op uses the common target gate/readout, **not** pX(empty)=1, which would trivialize the decision. Y-only must not choose an order using X or any hidden physical labels. If floating numerical differences in pY across permutations break ties, group by canonical A and reuse one exactly shared pY; check endpoint equality to tolerance before canonicalizing, and log any meaningful discrepancy. Check no-op score semantics and all selectors against production for J. Avoid rounding scores differently from production. Do not introduce cost weights or thresholds. XC is model-only/cache-only by default.

### 3.2 Ranking-only control

To separate score ranking from gates, also save the argmax nonempty repair under J/X/Y/XC with production deterministic tie-break, no admission threshold, no no-op competition. This is a diagnostic assuming a repair is requested, not a deployment method; no true K supplied. Report common-gate decisions and whether rankings differ. Use exact compatible cached physical outcomes; new queries for this control only after primary deployment and matched-order obligations. If incomplete, report coverage, bounds and model-only results, not a definitive physical ranking-only comparison. On VAL, compare labelled-only rank concordance and top-1 across all four readouts (same decided candidate set). No threshold tuning on cohort. Do not call pX1 vs overall Z a conditional-X calibration metric.

### 3.3 Factor-specific diagnostics

For each domain on existing labelled DEV rows (also report compatible locked-cohort labelled subset after sealing):

- pY vs Y at unique endpoints; pX vs X over decided X; pX1 vs X only where Y=1; pX0 vs X only where Y=0; p11 vs Z on decided logical conjunction. Report AUROC, AUPRC, Brier, log loss, counts, prevalence; if one class absent, N/A. Root-balanced within-root concordance where both classes exist, family-cluster intervals; pooled metrics secondary. Do not duplicate endpoint labels across permutations. Cross-head score-vs-Z is a repair-ranking diagnostic, not calibration for that head. Report label selection bias, and results on TRAIN only as in-sample context. Existing labels with no resolution provenance may be reported separately as snapshot-operational, not strict.
- Within-root Z+ versus Z− concordance for J/X/Y/XC on identical labelled sequences, top-1 of known labelled set (not exhaustive physical oracle), failure decomposition and known-witness lower-bound coverage. Show K1/K2/K3 and repair length if meaningful. Existing historical same-order and independent/direct-Z results: audit archived matching cohort and protocol; reuse if exact-compatible, otherwise report separately. No new fits.

## 4. Cohorts and label contract

### 4.1 Locked cohort

Reuse the exact CR-study roster: 210 roots/domain (50 each legacy K1,K2,K3, 30 K0, 30 NONE), same IDs, family IDs, public inputs, immutable V3.4 base release. Verify `P0_COHORT.json`, private roster and seals; if not present on host, recover from exact artifacts, not a replacement cohort. Main task success denominator 150 K1–K3 roots per domain. K0/NONE safeguards separately. C0 reference 82/150 2D and 113/150 3D (54.7/75.3%); validate exact root decisions and label mapping; report any mismatches before proceeding. These are retrospective outcomes previously exposed, not independent test results. Preserve old CR study; no new CR inference needed. Report family counts and any overlap with TRAIN/VAL. Use available existing VAL for order audit and diagnostics with its DEV status; never open protected TEST. Cohort selection, method protocol and new labels are frozen before accessing new physical outcomes.

### 4.2 Label ledger

Join by (domain, canonical root geometry/ID, original task, exact ordered sequence, robot reference, teacher version/configuration). X attaches to order; Y attaches to canonical assignment under original task. Cache reuse only for verified exact contracts (including grid, q_ref, collision model, planner budget, seeds where applicable). Retain source/status/resolution, never reinterpret missing as failure. If Y disagrees across equivalent endpoints or decided X labels conflict under same contract, quarantine affected factor/key and report. Can reuse a verified Y endpoint across orders only when exact task/teacher endpoint contract matches and no conflict. No labels passed to inference. Legacy `labels.B` witnesses must be audited for exact teacher compatibility; otherwise only coverage metadata, not ground truth for new order contrasts.

- 2D strict: `VERIFIED`/`EMPTY` positive, `CERTIFIED_INFEASIBLE` negative (check value and factor); `UNKNOWN_PLANNER`/`UNKNOWN_TRANSIT` unresolved even if stored 0. Operational sensitivity reproduces V3.4 stored-0 convention. Raw statuses retained. Do not promote a planner give-up to a certified failure.
- 3D: `resolution=EVALUATED`, value 0/1 is the teacher-budget outcome; unresolved admin/error stays UNKNOWN. Existing teacher conflates geometric and budget failure, so call negative *budget-defined execution/target failure*, never a proof of physical impossibility. Audit host `fin3d.py` and exact env hashes against CR P0; if mismatched, stop/reconcile before new queries. Do not change robot, physics, grasp counts or time/iteration limits.
- Z=1 iff both X and Y decided 1; Z=0 iff either decided 0; otherwise UNKNOWN. Separate missing/not-queried from attempted unresolved and conflicts. For K1–K3 no-op/abstain count as unsuccessful repair decisions (also report actual known Y(empty) and anomalies). K0 correct NOOP, NONE correct benchmark-relative ABSTAIN; verified success on NONE overrides impossibility claims. Report unnecessary successful repairs separately.

## 5. Execution-order sensitivity (the essential matched experiment)

### 5.1 Match exactly, not approximately

Use K=2 and K=3 **assignment lengths**, same root S0, target, goal, object identities, destinations and final edited arrangement. Only permute the ordered relocations. For m=2 there are 2 permutations; m=3 there are 6. Never compare different destinations, object sets, initial scenes or tasks as order contrasts. Same-endpoint Y must be invariant (predictions and cached teacher label consistency). Both positive and negative X under the exact contract are required to claim an observed order-sensitive endpoint. Do not manufacture negatives by assuming an unverified permutation fails. Do not use ideal edit/static check as physical X. Use original teacher from the same reference pose for each complete sequence, not successive execution from a previous permutation. Preserve trajectory metadata when already available.

### 5.2 Two evidence panels (keep separate)

**O-A: existing-label retrospective analysis.** Audit all compatible existing VAL and locked-cohort labels, including earlier ordering/ablation caches, CR and V3.4 caches, historical records with resolution provenance. Enumerate each canonical assignment and all potential orders; report coverage of X+/X−/UNKNOWN/missing and Y. Groups with at least one strict X+ and X− support within-endpoint contrast; fully decided groups support oracle-free top-order and random-order success. Report VAL and locked cohort separately, by domain and m; TRAIN optionally descriptive. Existing queried orders are selection-biased, so mixed-group incidence and selected-order success on these groups are conditional, not population prevalence. Include off-top4 groups for mechanistic diagnostic but separately report membership in original pool.

**O-B: fixed-roster complete permutation panel, evaluation only if needed.** Before any new teacher results, choose 20 canonical assignments/domain, ten of length 2 and ten of length 3, at most one per root and prefer distinct families, from pre-existing legacy witness assignments on the locked cohort. Choose deterministically by SHA256 `XYORDER_PANEL_V1|domain|root|canonical_assignment`, sorted within m; use legacy witness metadata only to identify a repair endpoint, never model scores or order disagreement or X failure outcomes to choose. Prefer exact-contract known Y=1; if legacy witness provenance differs, verify endpoint once or label missing. Do not condition on top4 membership. If a stratum is short, keep actual count and report, no post-outcome replacement. Lock all IDs and all permutations before new queries. The evaluator may know the assignment but the ordering ranker receives only S0 and unordered A, no witness order, K_legacy or labels. Primary purpose: conditional on a candidate repair endpoint, can the model choose a successful order? Not full planning or proof of minimum K. Reuse compatible labels; fill missing permutation X values within cap. Maximum 80 ordered requests per domain before reuse (10*2 + 10*6). If exact labels already fully cover panel, zero new queries. No retry of unresolved outcomes. If teacher interface always calls Y as well, log its cost and endpoint reuse; don't alter physical protocol for efficiency. Panel is small; if <10 mixed groups or <10 independent families per domain, mark discordant discrimination descriptive/underpowered, no broad claim. A lack of observed order sensitivity could mean either benign scenes or insufficient labels; not proof ordering never matters.

### 5.3 Order selection and metrics

For each fixed A, score every permutation with frozen readouts. Report pY range (must be ~0, tolerance 1e-6 or justified audited float precision), pX1 and pX ranges, p11 range. For fixed pY>0, ranking by p11 and pX1 is mathematically identical (unless numerical ties); do not treat them as independent competing methods. Compare:

- learned top-order via pX1 (equivalent p11 on fixed endpoint), deterministic tie rule;
- marginal-X top-order as secondary;
- canonical/lexicographic order independent of scores (also Y-only tie baseline; ensure exact same tie ordering, displacement/length constant);
- uniform random order analytically, success = number of X=1 orders / m! on fully decided groups, no simulated random cherry-picks;
- optional archived order-invariant G model if exact matching checkpoint available, no training. Oracle any-X-positive and best-order reachability are upper bounds, not deployable methods.

Report mixed-group X+ vs X− concordance (ties .5), group-macro then root/family aggregation, conditional on Y=1 (primary pX1), Y=0 separately with pX0 if adequate and marginal X on all groups. Report learned top-order X success vs canonical and analytic random on fully decided Y=1 panel; all-roster verified success (unresolved not verified), partial-group random bounds [n_positive/m!, (n_positive+n_unknown)/m!], chosen-order unknown rates, oracle conditional success and coverage. Do not silently restrict primary panel to mixed groups; mixed-only results are diagnostic. A complete-order panel can legitimately contain all-success/all-failure groups; report them. Score ranges alone are not evidence of correct order reasoning. For learned vs random, use paired per-group fractional differences; family-cluster intervals. For full repair order-control label Z use Y=1 restriction or logical conjunction, not X alone otherwise. Record whether the top-order differs from blind ordering. Visualize both successful and failing orders for the same A; show same final ideal arrangement, and where physical failure occurred only if trace supports it.

## 6. Phase schedule and acceptance gates

### P0 — audit and preregistration (no new teacher queries)

Read current branch/source, reports, all bundle hashes, roster and teachers. Inventory available labels by split, factor, domain, m, status, pool membership, provenance; report count of mixed and complete groups, including existing order labels outside top4. Check disk and GPU/CPU availability. Freeze `protocol.json`, resource counters, roster hash, data access boundary and statistical choices. Verify historical results and distinguish what is already available from new work. P0 report `P0_AUDIT.md` + JSON and figures coverage. Stop only for missing immutable bundle/roster, unsafe resource situation, or incompatible teacher without workaround; no extra experiments without authorization.

### P1 — adapter, selectors and tests

Implement stable frozen readout and single streamed pool; tests for algebra, original-root semantics, no-op behavior incl .3≤p_noop<.5, empty/no-legal pool, identical pool hashes/counts, top4 prefix parity, endpoints invariant across permutations and batches, exact ties, deterministic canonical order, K2/K3 grammar, label joining and conflicts, UNKNOWN mapping, analytic random order bounds, no leakage, cap reservation and resume. Audit 20 VAL roots/domain (4 per legacy stratum) using previous CR parity roster if available; J must exactly match historical decisions, proposal lists, p11 within 1e-6 (or explain numerical precision; exact decisions required). Compare pX/pY/p11 to Scorer.score, readout conditional identity, and endpoint permutation equality. No protected TEST. Report `P1_PARITY.md`, test logs, compact demo visuals. If parity fails fix adapter on DEV only; no evaluation until passes.

### P2 — frozen DEV analysis and seal cohort predictions

Run readouts on all compatible existing labelled VAL K≤3 rows (no new DEV teacher queries). Report corrected calibration and ranking, existing order evidence. Run full original pool on fixed 210 roots/domain, stream readouts once, seal J/X/Y/XC deployment and ranking-only predictions with pool hash/count, no-op score, chosen sequence/readouts, tie key, config/checkpoint hashes, timings, no teacher calls. Reproduce archived J picks on cohort before comparing; if mismatch stop and explain. Generate O-B panel manifest separately from evaluator metadata, score all permutations without seeing their labels, seal. Also lock new physical query manifests before any new results. Commit/push seals before teacher phase. Time GPU with synchronization, report joint shared pass time vs standalone readout latency only if actually measured; no claim that X/Y readout costs differ if same net executed.

### P3 — bounded physical evaluation, no adaptive retries

First join caches (read-only) to sealed picks and panel. Query exact missing unique ordered requests using existing teachers, no feedback into selection. Priority: (1) primary J/X/Y top-1 on K1–K3, all arms per root together in hash order; (2) reserved O-B permutation panel; (3) K0/NONE primary picks where physical verification relevant; (4) ranking-only controls and XC only from remaining capacity. Plan reserve up to 80 of 400 requests/domain for O-B, so initial primary allocation ≤320, unused reserve released after panel completion. J usually cached; worst-case new primary requests ~300 for X/Y plus any missing J. If over cap, use deterministic whole-root blocks, leave others UNQUERIED. Do not spend reserved panel budget on secondary controls. Preseal entire manifest (including tier order); if CPU cap requires truncation, stop deterministically, record unqueried. Use exact cache key and count each new ordered request even if unresolved; also report actual X and Y factor calls. No fresh training interventions, new scenes, increased per-query limits, or repeat attempts. Profile first 20 3D requests for accounting only. Reserve worst-case/in-flight CPU and wall headroom before dispatch; cap workers. Save `P3_VERIFY.md` and counters.

### P4 — statistics, visualizations, and paper-ready conclusions

Use per-domain primary K1–K3 all-root verified success (denominator 150, all unknown/unqueried not verified), decided-only descriptive and paired complete-case contrasts, UNKNOWN/UNQUERIED rates and partial identification bounds. Report 2D historical convention separately, never call operational failure certified. For deployment primary contrasts J−X and J−Y in each domain (four), family-cluster bootstrap 4,000 draws seed 0. Preserve all roots in a resampled family (including mixed-K families; do not split family across strata). Compute overall equal-K-stratum weighted metric within each replicate (handle absent strata explicitly, report method); paired differences and 95% intervals, Holm adjustment across four tests. Use centered bootstrap two-sided p approximation or paired cluster randomization test (specify before outcomes; recommended family-level arm swaps, exact when feasible, otherwise 20,000 fixed-seed permutations with plus-one correction). Do not treat raw candidate pairs as independent samples. Established improvement only if adjusted p<.05, CI excludes zero, direction positive, UNKNOWN ≤20% in each compared arm and ≥90% roster queried/evaluable (distinguish decided vs queried). Otherwise no established difference/inconclusive. 2D likely limited; no extra queries just to make it significant. Report effect sizes and intervals; no equivalence claim without predeclared equivalence test. Order primary: learned pX1 vs canonical and uniform random, per domain on presealed panel; separate Holm family of four comparisons if adequate, otherwise descriptive with intervals. Mixed-group concordance primary mechanistic metric, report interval vs .5 and group/family counts. All other diagnostics explicitly exploratory.

Paper-ready outputs:
1. Table: J/X/Y, 2D/3D, per K and pooled verified success, UNKNOWN, UNQUERIED, paired delta, CI, adjusted p; FAIL_X and FAIL_Y distinguished by actual factor outcomes (joint categories also report X0Y0/X0Y1/X1Y0/X1Y1/partial; never force single blame for dual failures). Include no-op/abstain, repair length, displacement, common pool count, teacher calls during inference=0.
2. Table: same-endpoint order results by domain, m=2/3, counts of endpoints/roots/families/mixed/complete, X concordance, top-order verified X, canonical, expected random, oracle upper bound, unknown/bounds. Distinguish O-A retrospective from O-B fixed panel. Report pY invariance.
3. Factor-specific diagnostics table and labelled-only rank diagnostics; include exact comparison to earlier 2D report with correction of pX1 vs Z interpretation.
4. Figures: paired success by K/domain with uncertainty; confusion/unknown and failure breakdown; X+ vs X− matched order scatter/rank; example 2D and 3D scenes with identical final arrangement and alternate orders, actual physics render if existing tooling supports it (otherwise label schematic). Show failed/neutral examples as well as wins, choose by fixed hash within outcome classes, no cherry-picking. No invented trajectories. Training curves unnecessary.
5. `P4_FINAL_DECISION.md`, `paper_tables.md`, machine-readable per-root and per-assignment metrics, reproducibility commands, source hashes and deviations in `AMENDMENTS.md`. State whether both factors improve end-to-end selection; distinguish order sensitivity from correct order discrimination, and report any negative/inconclusive outcome. Existing independent/uncoupled/direct-Z ablation answers different question; no claim the full architecture is necessary solely from readout comparisons.

## 7. Proposed hard resource envelope (requires owner authorization)

- New training / training interventions / new scenes / protected TEST access: **0**. X/Y, sampler and CR checkpoints unchanged. No new search algorithms, no K>3.
- Model inference+analysis ≤3 GPU-hours total, no training GPU hours. Prefer same laptop environment as CR; do not compete with other jobs. At most 16 CPU workers, ≥4 logical cores free, avoid simultaneous GPU runs. Check actual host and disk before work.
- New physical ordered-sequence requests ≤400/domain, including all evaluation-only panel queries and unresolved attempts; ≤8 teacher CPU-hours 2D and ≤16 teacher CPU-hours 3D. Up to two factor calls per request if teacher evaluates both; count and report X/Y separately (≤800 factor calls/domain), no hidden additional requests. No additional scene or training collection. Existing caches do not count as new requests. CPU caps are aggregate, not wall time; reserve in-flight headroom. Stop dispatch if no capacity remains, report partial data and no new authorization assumed.
- New disk use ≤200 MB, keep ≥1 GB free on target filesystem; last CR report had only ~1.2 GB free on /home. Check before every large write; use an approved existing mount if available and verified, otherwise stop if floor threatened. Never delete historical/other-session artifacts. Stream candidates and compact predictions. No large video export by default.
- These caps are proposals, not permission. P0 read-only audit and light CPU tests can run before approval; GPU inference and new physical requests only after explicit owner approval. If owner authorizes all, proceed P0–P4 without repeated requests unless hard cap or fundamental blocker. If labels suffice, use zero new queries. Never expand budget based on significance.

## 8. Scope closure for RSS

This closes the planned *new architectural ablations* for K≤3 if executed and reported, regardless of outcome. Complete-repair generator ablation remains closed; no reopening training. K4/K5 scalability is separate and must finish or be reported honestly. External baseline fairness (same scenes/contracts, planning vs execution time, K/object count, planner calls and repair cost) is a separate paper audit, not automatically solved here. Causal attribution/minimal necessity needs separate evidence if claimed; if no existing omission labels support it, describe selected corrective relocations rather than claim causal identification. Final paper should not claim energy coupling, order reasoning or either factor is essential when the corresponding evidence is null or underpowered. This plan cannot guarantee a positive result.
