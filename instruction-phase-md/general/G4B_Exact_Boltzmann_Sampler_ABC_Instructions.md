# G4B — Exact Boltzmann Sampler Verification for the 2D A/B/C Study

**Execution contract for Claude Opus 5.5 High · prepared 20 October 2026**  
**Next stage: G4B only · implement, test, report, STOP**

> **IMPORTANT UPDATE.** G4D is now **PASS**, not BLOCKED. Its completed evidence run is documented in `responses-phases/0011_G4D_corrections_and_collection.md` (19 October 2026), ending at commit `eb4e661aaaeb90a76cc02bb66d77cbb4a9567303` (135 passing tests; six archived replays; 20 completed collection units using 133.8 CPU-seconds). The prior Guide v1.9 and Methodology v1.7 were drafted **before** this successful collection and contain outdated G4D status paragraphs. Treat report 0011 as authoritative for *current evidence*, Methodology v1.7 as the proposed *new A/B/C scientific definitions*, Guide v1.9 as the proposed *future implementation stage requirements*, and actual checked-in code as the source of truth about currently implemented interfaces. Do not rewrite G4D history or misreport an old blocked state as current.

## 0. The one-sentence deliverable

Implement and **mathematically prove by finite enumeration** a small, CPU-only Boltzmann sampler that correctly explores **ordered, move-once corrective sequences** for architecture **A**, and the exact **bounded intervention-outcome marginal** required by proposed architectures **B/C**. **Do not train neural models. Do not run new robot planners.**

## 1. Mandatory state reconciliation before touching code

1. Inspect the real repository, `git status`, HEAD/branch/upstream, repo instructions, test commands, and the actual G4D implementation. Confirm (or clearly report a mismatch with) the claimed commit `eb4e661aaaeb90a76cc02bb66d77cbb4a9567303` and 135 passing tests/six archived replays. **Do not hard-reset, rebase away changes, delete user files, or modify old results.**
2. Read in full: `responses-phases/0011_G4D_corrections_and_collection.md`, the G4D code/tests (`sequences.py`, `ordered.py`, `effects.py`, `verify.py`, and relevant config/data helpers), *Methodology v1.7* and *Implementation Guide v1.9* **if actually available in the repo**. The v1.7/v1.9 documents may exist only as files supplied by the user. If unavailable, identify that in your report and use this self-contained G4B contract for the sampler; **do not silently claim to have read missing documents**. Keep the v1.6/v1.8 execution and evidence semantics inherited by the newer A/B/C design.
3. Confirm the G4D evidence inventory without replanning it: R4 same-endpoint positive/negative order contrast, R2 fixed-robot scene effects, R4 omission labels, first-witness joint costs; preserve the R2 unresolved executable chain, R5 unknown baseline and R1 zero robot-start effect. These are **not** G4B sampler training labels.
4. Write a compact baseline-to-change map and identify the smallest reusable interfaces. Reuse strict canonical sequence parsing, per-object destination maps, physical signatures, move count and cost definitions. No production planner/target import may enter sampler scoring.
5. Check any untracked PDFs/prompts and existing working-tree modifications; treat them as user-owned. If conflicts or a newer G4B implementation exist, **STOP and report the conflict before changing anything**.

## 2. Non-negotiable scope and prohibitions

**Allowed:** 2D mathematical microdomains, immutable G4D scene reads for visualization, deterministic synthetic **energy functions** for sampler verification, one compact sampler module (or an equally small addition to an existing unbloated solver file), focused tests, small run/figure/manifest/report files, and the minimum CLI hook consistent with the repo. CPU float64 reference calculations.

**Not allowed:** starting G4C/G4E/G5/G6, implementing or training A/B/C MLPs/GRUs, computing new teacher labels, launching full robot motion or target-evaluation jobs, launching dense data generation, changing physical oracle or robot contact policy, changing G4D or V1 archives, using raw teacher outcomes in the scorer, creating another framework or nested package, adding a classical Hopfield/RBM library, claiming causal learning or hardware success, or redesigning the already frozen scientific hypotheses.

**Resource contract:** No new expensive experiment or GPU work. **New G4B sampler/test/demo code must invoke zero motion planners, teacher or target callbacks.** Prior historical regression tests or archive replay commands may exercise the previously implemented planner; if so, run only the established regression procedure and report those calls **separately** from the G4B sampler budget. Do not initiate new data-collection planning.

## 3. Shared repair state and energy definitions

The **only primary search state** is a canonical, ordered, move-once repair

\[
r=((i_1,k_1),\dots,(i_m,k_m)),\qquad 0\le m\le b,
\]

where IDs are distinct, each non-stay candidate is an actual **physical** destination for that object, and `[]` is the unique no-repair state. Current/stay poses remain in scene context. No NOOP padding or duplicate permutations of inactive objects are distinct states. Swapped selected actions are distinct **even when the final assignment is the same**. All other objects remain present and stay.

For every eligible object `i`, let `K_i` be the number of **distinct non-stay** destinations. Let `N` be the count of objects eligible for birth (`K_i >= 1`), not the total object count; zero-candidate objects remain in scene context. Tests must include unequal `K_i`. The finite feasible-for-sampler state space includes temporarily static-invalid repair assignments: **do not hard-mask static collisions inside the Markov chain**. Physical static screening occurs only when collecting/ranking proposals for a later independent verifier.

For A's toy microdomain define a finite deterministic `E_A(r)` with nontrivial unary, pair, **order-sensitive** and optional known displacement/predicted-cost toy terms. For the Markov chain, energy `E(r)` is the **sampling** energy (and must be evaluated in full whenever relevant), not a misuse of trained feasibility-only energy. At temperature `T > 0`:

\[
\pi_A(r)=\frac{\exp[-E_A(r)/T]}{\sum_{v\in\mathcal R_b}\exp[-E_A(v)/T]}.
\]

Synthetic toy scores are **mathematical test fixtures**, never model predictions, learned results or physical evidence. A real trained network is not required at G4B.

## 4. Implement exactly four fixed-probability sequence kernels

Default kernel probabilities = `(1/4, 1/4, 1/4, 1/4)` for `DESTINATION`, `SWAP`, `BIRTH`, `DEATH`. Do not renormalize these when a move is unavailable: an unavailable move becomes a **self-transition**. If probabilities become configurable, check they are finite, nonnegative and sum to one, and rederive any proposal ratios if birth/death kernel probabilities differ. Freeze the rule and log it.

1. **Destination Gibbs:** If `m=0`, self-transition. Otherwise uniformly choose one selected action position and sample its destination among that object's `K_i` non-stay physical destinations, **including its current candidate**, from the exact conditional proportional to `exp(-E(new_r)/T)`. All factors affected by the destination, all relevant ordered-prefix factors, and any B/C marginalization must be recomputed. A fixed existing destination is not an extra self-penalty.
2. **Order swap Metropolis:** If `m<2`, self-transition. Otherwise uniformly choose an unordered pair of distinct action positions and swap them. Accept with `min(1, exp(-(E_new-E_old)/T))`. The proposal is symmetric. Its final assignment remains unchanged, its **ordered signature differs** and its energy can differ.
3. **Birth Metropolis–Hastings:** If `m=b` or no eligible unused objects remain, self-transition. Otherwise choose an unused eligible object uniformly from `N-m`, a destination uniformly from its `K_i`, and an insertion index uniformly from `m+1`. Evaluate the full proposed energy. For equal birth/death kernel probabilities, the reverse/forward proposal ratio is **`(N-m)*K_i`**. More generally multiply by `p_death/p_birth`.
4. **Death Metropolis–Hastings:** If `m=0`, self-transition. Otherwise choose one of the `m` selected action positions uniformly and remove that action, leaving the removed object at its original **stay** pose in *every recomputed prefix*. For equal birth/death probabilities, the reverse/forward ratio is **`1/((N-m+1)*K_i)`**, where `i` is the deleted object. More generally multiply by `p_birth/p_death`.

Compute MH acceptance in **log space**. The precise acceptance probability for proposal `r->r'` is `min(1, exp(-(E(r')-E(r))/T) * Q(r|r')/Q(r'|r))`. Use the declared fixed kernel probabilities and candidate counts; do not omit reverse-proposal terms. A rejected proposal stays in its original state. Use explicit seeded RNG injection, not hidden global randomness. Keep the sampler and reference-energy interface planner-free.

## 5. Required architecture B/C exact intervention-outcome marginal

The proposed JOINT-CAUSAL-EBM and HYBRID-JOINT use a **joint** conditional energy `E_M(r,z | c0,Q)` where `M in {B,C}` and `z` consists of *typed binary outcomes for predeclared eligible queries*: original target `z0`, fixed-robot scene substitutions `z_I^S`, complete proposed repair `z_r`, and repair-omission outcomes `z_A^O`. An outcome variable denotes the specified query's binary task feasibility when the oracle can decide it; **it is not a magical culprit node or an inferred causal arrow**.

At G4B, no learned model exists. Implement the **mathematical interface and deterministic coupled toy energies** only. A micro-layout must include at least: a nonconstant `z0`/scene-edit pair; a repair-conditioned `z_r`; a repair-omission outcome; and a genuine coupling where changing `z` changes energy differently for different repairs. Avoid a trivial separable energy in which z cancels from the repair distribution. Keep original appearance/robot state and query catalogues conceptually fixed; never read oracle labels as sampler inputs.

For a **fixed predeclared query layout** `Q` (including candidate-dependent omission layouts with a deterministic mask), enumerate all *active compatible* binary vectors `z` when active dimension `<= 8`. Inactive slots have **one deterministic value** and are excluded from both energy and the state count; they must not yield a factor-of-two entropy bonus. For larger dimensions, **return unsupported/not-run for exact enumeration** rather than silently enumerating `2^n` or enabling an unverified approximate z-chain.

\[
\bar E_M(r)=-T\log\!\sum_{z\in\mathcal Z(r,Q)}\exp[-E_M(r,z)/T],
\]

\[
\pi_M(r)=\frac{\exp[-\bar E_M(r)/T]}{\sum_v\exp[-\bar E_M(v)/T]}.
\]

Use stable `logsumexp`, with **the same `T`** in marginalization and the outer sampler. If deterministic known displacement/toy cost is added, add it once **after** marginalizing the feasibility/outcome energy, or equivalently as a z-independent term inside the sum; verify both agree. For A, `E(r)` is direct. For B/C, all four **same** sequence kernels operate on the exact marginal `\bar E_M(r)`; after sampling `r`, one may enumerate or sample `z|r` exactly for diagnostics. A full joint `(r,z)` approximate Markov chain remains **DISABLED** at this gate unless it receives its own separate exact stationary/mixing proof and authorization; the intended G4B deliverable is exact bounded-z marginal inference.

**Invariance requirement:** adding a logically inapplicable/inactive outcome slot or permuting equivalent inactive metadata must not change relative marginal repair probabilities. Test numerical equality after handling the fixed masks. Test that a change in the *meaningful* scene query catalogue is accounted for and recorded, not silently treated as the same conditional model. Explicitly test the `[]` repair and omitted-action positions.

**Training is NOT in G4B:** B/C joint-energy potentials and joint finite-pool likelihood will be trained only at G4E/G5. No BCE, joint-training optimizer or GRU creation at this gate. If a tiny automatic-differentiation gradient sanity check is feasible with the environment's existing library, it is a purely mathematical diagnostic, not model training.

## 6. Exact finite-space certification: pass/fail gate

Use an independently written **reference enumerator**, not just the same production sampler kernel loop under a different name. A reference implementation must generate every canonical ordered state directly, including `[]`, respecting per-object destination domains and move cap. At minimum:

- **Toy A1:** `N=2`, `K=[2,2]`, `b=2`, giving exactly **13 canonical states** (`1` empty + `4` one-move + `8` two-move). Include a score that changes when the two actions swap.
- **Toy A2:** `N=3`, `K=[1,2,3]`, `b=2`, giving exactly **29 canonical states** (`1 + 6 + 22`). Check nontrivial birth/death ratios with unequal `K_i` and a context object with `K=0`.
- **Toy A3:** degenerate edges: no birth candidates, `b=0`, `m=0`, `m=b`, `m=1`, `K_i=1`, and a case with a proposed static-invalid endpoint that stays searchable inside the chain.
- **Toy B1/C1:** at least one small **repair-dependent, z-coupled** energy and a mixed active/inactive outcome layout. Fully enumerate `(r,z)` to provide an independent gold-standard `P(r,z)`, marginal `P(r)` and conditional `P(z|r)`; ensure it is not equivalent to an uncoupled constant offset. Test B/C with distinct mathematical energy fixtures. At most 8 active binary z variables.

Build the **full one-step transition matrix** `P[r,r']` analytically from the implemented proposal rules and acceptance/conditional formulas (including self-transition mass and all four kernel selection probabilities). On every microdomain verify:

1. all state counts, valid signatures, unique canonical sequences, and exact conditional Gibbs normalization;
2. `sum_{r'} P[r,r']=1` to tight numerical tolerance, no negative/NaN/infinite transitions;
3. **detailed balance** `pi[r] P[r,r'] = pi[r'] P[r',r]` for every state pair;
4. **stationarity** `pi @ P = pi` and nontrivial swap/destination/birth/death transitions;
5. exact reference `pi` agrees with a stable `logsumexp` computation;
6. changing the order changes energy when the toy factor demands, but consistent renaming of object records does **not** change the physical distribution;
7. fixed RNG seeds reproduce chains, different seeds can change trajectories, and a sufficiently long histogram is supplementary **only** (not the proof);
8. B/C `sum_z P(r,z) = P(r)` for every r, `P(z|r)` normalizes, and inactive-slot insertion does not alter `P(r)`;
9. finite-difference checks for `d(\bar E)/d\vartheta = \sum_z P(z|r) dE(r,z)/d\vartheta` on a differentiable *toy parameter* if practical, with a precise reason if the current environment has no autograd dependency;
10. cost-added-once and T-consistency checks; no static-mask-in-chain shortcut, and no dependence on teacher fields or simulator/target calls.

Record max absolute errors and declared tolerances (e.g. `1e-10` in float64 reference tests, tightened or adjusted based on demonstrable numerical evidence). Include negative/mutation tests: **deliberately wrong** Hastings ratio, flipped acceptance sign, missing order-energy recomputation, and inactive-z multiplicity each must be caught by at least one assertion. Do not mark an incomplete proof PASS merely because empirical histograms look good.

## 7. Keep code minimal and isolated

Inspect existing repository and choose the smallest possible edit set. Preferred ownership after confirmation:

- One `sampler.py` (or existing `solve.py` extension if cleaner) for immutable canonical state updates, fixed kernel mixture, energies supplied as a callback, exact tiny z marginal utility, seeded sampling and returned proposal/diagnostic records.
- One focused `tests/test_sampler.py` for finite-space reference enumeration, exact transition matrix, B/C coupled layouts, detailed balance/stationarity, invariances and mutation guards. Split into a second focused test file **only** when clarity warrants it.
- Minimal `run.py` dispatch such as `g4b`/`sampler-test` only if the existing CLI pattern requires it.
- Reuse existing `sequences.py` parser/maps and strict V2 config overlay; append a **separate new stage-scoped** config if needed, never mutate the historical G4D config hash.

Ordinary source modules should stay near 120–280 logical lines; >300 requires a documented responsibility review. Don't refactor existing long `verify.py` (reported 365 logical lines) or `skill.py` (311) unless absolutely necessary for this isolated stage, in which case stop and explain first.

Do not introduce a general model framework, hidden torch dependency, new simulator dependency, per-architecture duplicated samplers, temporary dense cache of every real-world sequence, or speculative G4C/G5 files. The same kernel implementation should accept A's direct energy and B/C's exact marginal energy.

## 8. Output artifacts and visualization

Create **one flat run directory** such as `runs/g4b_sampler_exact/` following actual repo conventions, with at least:

- `config.json` or a resolved stage-config snapshot with hashes and sampler temperature;
- `result.json` with exact state counts, measured numerical error maxima, PASS/FAIL/UNRESOLVED for every check, RNG seeds, module/version and code/config provenance;
- `arrays.npz` containing enumerated energies, exact targets, transition matrices, conditional z distributions where appropriate (small only);
- `manifest.json` linking source hashes, tests, figures and scoped evidence;
- `overview.png` showing reference distributions vs empirical supplemental checks and a **clear G4D R4 scene-context panel** from immutable saved data, marked `CONTEXT ONLY — NO PLANNER/NEW EVIDENCE`. If archived scene is unavailable, explain and use a strictly marked mathematical toy visual instead; never fabricate a robot pose/path;
- `sampler_trace.png` or `.gif` showing true discrete proposals and energies (including accepted/rejected updates), labelled **SYNTHETIC ENERGY / MATHEMATICAL TEST**, not trained robot evidence;
- the next available `responses-phases/NNNN_G4B_sampler_exact.md` stage report; do **not** overwrite any prior numbered report.

The stage report must state: Git HEAD at start/end, latest G4D baseline and known exceptions, modules changed with approximate logical lines, exact commands and exit codes, all counts and maximum proof errors, tests/replay regression results, wall/CPU usage and **absence of planner/target calls by G4B sampler code** (separately disclose any planner calls in historical regressions), untracked-file treatment, any scoped limitations, and an explicit **G4B PASS/BLOCKED/FAILED + STOP** decision. A beautiful animation is not a substitute for detailed balance.

## 9. Acceptance criteria and final STOP contract

G4B **PASS** only if:

1. complete tiny ordered state spaces (13 and 29 states) are enumerated correctly and independently;
2. all four kernels meet exact transition-matrix detailed balance, normalization and stationarity for unequal `K_i` and edge cases;
3. B/C bounded-z joint distributions, `logsumexp` repair marginals, conditional outcomes, masks, temperature and inactive-slot invariance pass exact comparison;
4. no model training, planner/target invocation by new sampler code, oracle relabeling, evidence rewrite or target-feedback leakage occurred;
5. previous tests still pass and established archived replay checks still succeed without modifying archived inputs/outputs;
6. run artifacts, figures and scoped, source-hashed stage report exist, with explicit numerical pass/fail evidence.

If any mathematical test fails, **stop with BLOCKED**, preserve the failing fixture and numerical trace, and do not make the test less strict or relax its acceptance criteria to obtain a pass. If the repo is missing necessary files or documents, report precisely what is missing. No G4C, G4E-ABC, G5, G6, 3D or hardware work is authorized in this execution.

**Repository synchronization:** Follow the repo's established user-authorized commit/push workflow only after all gates pass, confirm branch/upstream and preexisting working tree, and never force-push. Leave unrelated untracked instructions and PDFs alone. If authorization for a remote write is unclear, prepare the local changes and ask rather than guessing. End with required stage summary and **STOP**.

## 10. What comes only after explicit new approval

- **G4C:** independent-root 2D teacher label-readiness audit and eventual dataset collection, with a separately frozen CPU/node/call plan.
- **G4E-ABC:** model interfaces, A/B/C tiny-data trainability.
- **G5-2D-ABC:** actual MLP/GRU and explicit joint-Boltzmann energy training; no gradient through IK/robot teacher.
- **G6-2D-DECISION:** matched 2D performance, explanation, order, cost and verifier-call comparisons; select architecture only from held-out evidence.

**The simulator teacher is not used in G4B. This gate verifies search mathematics, not causal learning.**
