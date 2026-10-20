# 0012 — G4B: exact Boltzmann sampler verification for the 2D A/B/C study

| Field | Value |
|---|---|
| Report number | 0012 (new; 0001–0011 unchanged) |
| Date | 20 October 2026 |
| Stage | **G4B only.** One sampler module; synthetic finite fixtures; exact proof by enumeration. **No** model training, teacher labels, planner or target calls by G4B code, data generation, G4C/G4E/G5/G6, 3D or hardware. |
| Execution contract | `instruction-phase-md/G4B_Exact_Boltzmann_Sampler_ABC_Instructions.md` (154 lines, read in full; your file, left untracked) |
| Documents read | Report 0011; the G4D code and tests; **Methodology v1.7 and Guide v1.9**, present only as your untracked `latent_causal_tamp_2D_ABC_guides_v1_7_v1_9/` (plus its `.zip`), read in full from their `.md` sources. Not committed or moved. |
| Known document exception | Guide v1.9 (and the start-here note) still describe G4D evidence as BLOCKED. As the contract directs, report 0011 is authoritative for current evidence: G4D PASS at `eb4e661`. Nothing historical was rewritten. |
| Previous turn sync | Report 0011 was committed as `eb4e661aaaeb90a76cc02bb66d77cbb4a9567303`, matching the contract's claimed baseline. At the start, `main`, HEAD and `origin/main` all equalled `eb4e661`, with no tracked modifications. The untracked items were your instruction files, PDF copies and the v1.7/v1.9 bundle. No newer or conflicting G4B implementation existed: there was no `sampler.py`, and no Gibbs/Hastings code anywhere. |
| Starting revision | `eb4e661aaaeb90a76cc02bb66d77cbb4a9567303` |
| Ending revision | The commit that carries this report; its hash is given in chat and recorded in report 0013. |
| Run directory | [`../runs/g4b_sampler_exact/`](../runs/g4b_sampler_exact/), produced by `python run.py g4b --out runs/g4b_sampler_exact` (exit 0) |
| **Decision** | **G4B PASS. STOP.** |

---

## 1. Baseline reconciliation (§1)

- **Tests and replays.** Before any change, the baseline had 135 passing tests and six archived replays (report 0011). After this stage: **157 passed** (135 earlier plus 22 new), and all six replays pass (77/77/2/50/20/257) into scratch paths.
- **G4D evidence inventory**, confirmed from `runs/g4d_evidence/result.json` without replanning:
  - R4: same-endpoint contrast, (o01→18, o00→29) POSITIVE vs (o00→29, o01→18) NEGATIVE by ORDER_FIRST_ACTION;
  - R2: fixed-robot scene effects o03→38 and o03→60, both Δ = +1;
  - R4: omission effects of +1, +1 and +1;
  - first-witness J values: 1.041, 1.021, 1.394 and 1.723;
  - still R2 chain UNRESOLVED, R5 baseline UNKNOWN, R1 robot-start Δ = 0.

  None of these is used as a sampler label.
- **Historical hashes unchanged** (tested): deployment config `sha256:a9f3f236…`; V2 overlay `sha256:fd721f15…`.

### Baseline-to-change map (smallest reusable interfaces)

| Need | Reused | Added |
|---|---|---|
| Strict canonical form (str IDs, int non-bool cells, never coerced) | `sequences.canonical` | `sampler.canonical_state` adds domain membership, distinct IDs and the move cap |
| Order-preserving omission, derived assignment | `sequences.omit`, `sequences.assignment` | — |
| Per-object non-stay destination maps, K_i, N | the semantics of `scene.candidate_map` (stay excluded) | `sampler.Domain`; `eligible` gives N (objects with K_i ≥ 1); K = 0 objects stay as context |
| Stable hashing | `config.stable_hash` | the catalogue hash on `MarginalEnergy` |
| Sampler and kernels | none existed | `sampler.py` |
| Fixtures, reference and proof | — | `g4b.py`; runner and figures in `g4b_figures.py` |

---

## 2. What was implemented

### `sampler.py` (280 lines / 220 logical)

This is the single production sampler. It imports only `sequences`, `config`, `numpy` and the standard library. A test confirms in a subprocess that importing it, or `g4b.py`, loads none of the planner, skill, verify, evaluate, ordered, certificates, teacher or `g4d_run` modules.

**State.** Canonical `((obj, dest), …)` with length at most the cap; `()` is the empty repair. There is no static masking: every canonical state is searchable.

**Kernels.** The fixed probabilities default to 1/4 each. An unavailable move is a **self-transition** and nothing is renormalized. `check_probs` requires four finite nonnegative values summing to 1, with birth and death both enabled or both disabled.

| Kernel | Behaviour | Acceptance |
|---|---|---|
| DESTINATION | Choose one of the m positions uniformly; exact Gibbs over that object's K_i destinations, **current one included**, using the full energy of each candidate sequence | Always (exact conditional) |
| SWAP | Choose one of the C(m,2) position pairs uniformly | min(1, e^{−ΔE/T}) |
| BIRTH | Choose an unused eligible object (1/(N−m)) × destination (1/K_i) × insertion index (1/(m+1)) | Log ratio −ΔE/T + log((N−m)K_i) + log(p_death/p_birth) |
| DEATH | Choose one of the m positions (1/m); the object returns to stay | Log ratio −ΔE/T − log((N−m+1)K_i) + log(p_birth/p_death) |

**Exact transitions.** `transition_row` and `transition_matrix` compute exact one-step probabilities per kernel: selection × proposal × acceptance, plus rejection and unavailable-move self mass. Sampling (`step`, `run_chain`) uses **the same proposal-list functions**, with only an injected seeded `numpy` Generator.

**B/C marginal.** `Layout`, `z_states` (raises `Unsupported` above 8 active slots, so nothing is silently enumerated or approximated) and `MarginalEnergy`:
- Ē(r) = −T logsumexp(−E(r,z)/T) over active z only;
- the catalogue hash is recorded;
- `conditional(r)` gives the exact P(z | r);
- `same_temperature` refuses a marginal built at a different T from the chain.

**Joint chain.** A full joint (r, z) Markov chain is **not implemented (disabled)**, as the contract requires.

### `g4b.py` (220 / 180)

- **Synthetic fixtures**, explicitly labelled as such: seeded unary, symmetric-pair, predecessor-order and position terms, plus move count and known displacement. A finite static penalty marks an "invalid" endpoint pair, which stays searchable.
- **Spaces:** A1, A2 and four A3 edge spaces.
- **B and C joint energies** E = static(r) + θ·φ(r, z). The terms are:
  - a z0 prior;
  - a scene-query factor coupled to z0;
  - an order-sensitive repair factor (B: predecessor pair order; C: a recurrent tanh toy standing in for the GRU);
  - zR-tied omission factors;
  - a repair-dependent coupling of z0, zS1 and zR.
- **Deterministic mask rule** (`layout_fn`), known before any outcome:
  - z0 and the catalogue's scene queries are always active;
  - zR is active only for m ≥ 1 (for the empty repair the outcome is z0);
  - zO[t] is active only when m ≥ 2 (omitting the only action is the empty repair again);
  - every other slot is inactive with value 0.

  At most **5 active** slots (6 with the second scene query), within the bound of 8.
- **Independent reference enumerator.** `reference_states` builds every state directly with `itertools.permutations` × destination products and shares no code with the kernels. `reference_pi` is a direct float64 exp/normalize. `gold_joint` enumerates (r, z) with its own product.
- **`certify`, `certify_bc`, `gradient_check`.**

### `g4b_figures.py` (262 / 242)

- `guards()` holds the mutation and invariance checks.
- The stage runner wraps every **loaded** planner, skill, target and teacher entry point with a call counter. Those modules are imported by `run.py` but never called by G4B.
- It writes `config.json`, `result.json`, `arrays.npz`, `manifest.json` and the two figures.

### Other files

- `tests/test_sampler.py` (167 / 143): 22 tests.
- `run.py`: `g4b` subcommand (+5 lines).

No existing source file was refactored.

---

## 3. Exact proof results (`result.json`, tolerance 1e-10 in float64)

**Spaces under default probabilities.** Each was also re-certified under unequal probabilities (0.4, 0.3, 0.2, 0.1), and every unequal-probability run passed with maximum error at most 2.2e-16.

| Space | Domain | States (expected) | Max error | Row sums | Detailed balance (all) | Stationarity | π reference vs logsumexp | Off-diagonal moves D/S/B/Dth |
|---|---|---|---|---|---|---|---|---|
| A1 | N=2, K=[2,2], b=2 | **13** (1+4+8) ✓ | 1.7e-16 | 1.1e-16 | 3.5e-18 | 5.6e-17 | 1.7e-16 | 20/8/20/20 |
| A2 | K=[1,2,3] + K=0 context object, b=2 | **29** (1+6+22) ✓ | 1.1e-16 | 1.1e-16 | 6.9e-18 | 6.9e-18 | 2.8e-17 | 60/22/50/50 |
| A3 b=0 | — | 1 ✓ | 0 | 0 | 0 | 0 | 0 | all self |
| A3 no birth candidates | all K=0 | 1 ✓ | 0 | 0 | 0 | 0 | 0 | all self |
| A3 K_i=1 | b=1 | 2 ✓ | 2.8e-17 | 0 | 0 | 0 | 2.8e-17 | 0/0/1/1 (Gibbs is a self-transition) |
| A3 static-invalid | a ∈ {9,1}, b ∈ {9}, b=2 | 8 ✓ | 1.1e-16 | 1.1e-16 | 3.5e-18 | 6.9e-18 | 1.1e-16 | 6/4/11/11 |

**Further exact checks** (tests and `result.json`):
- **Per-kernel normalization.** Each kernel's row mass equals its selection probability; maximum error 5.6e-17. This covers Gibbs normalization and unavailable-move self mass.
- **Detailed balance per reversible group.** DESTINATION alone, SWAP alone, and BIRTH+DEATH together each satisfy detailed balance.
- **Hastings ratios.** On A2, with unequal K and unequal kernel probabilities, `exp(log_hastings)` matches reverse/forward proposal probabilities derived **independently** from (N, m, K_i, p) for every birth and death move, within 1e-12.
- **Gibbs conditional.** Matches p_dest/m × softmax over all K_i candidates, current included.
- **Self-transitions.** The empty state and m = b give exact self-transitions.
- **Static-invalid endpoint.** It has π > 0 and nonzero in- and out-transitions.

### B/C bounded-z gold standard (A1 repair space, T = 1)

| Fixture | Joint (r,z) states | Max active z | Proof max error | P(z|r) error | P(z|r) normalization | Gradient error (r=(a2,b3) / r=()) | Coupling: std of Ē − static | Range of P(z0=1|r) |
|---|---|---|---|---|---|---|---|---|
| B1 | 292 | 5 | 4.4e-16 | 8.3e-17 | 4.4e-16 | 1.9e-10 / 6.7e-11 | 0.732 | 0.129 |
| C1 | 292 | 5 | 4.4e-16 | 1.1e-16 | 4.4e-16 | 1.1e-10 / 9.2e-11 | 0.754 | 0.192 |

- **Marginal route equals the gold standard.** The sum over z of P(r,z) from the independent (r,z) enumeration equals the sampler's marginal π(r). The exact transition matrix on Ē satisfies detailed balance and stationarity against that gold-standard marginal.
- **Gradient.** dĒ/dθ by central finite difference equals Σ_z P(z|r) ∂E/∂θ. Because E is linear in θ, ∂E/∂θ = φ exactly; no autograd dependency is needed.
  - The **gradient tolerance is 1e-7**, declared separately: central-difference truncation O(ε²) plus roundoff ≈ 1e-16/ε at ε = 1e-6. Observed errors are at most 1.9e-10.
- **Not a constant offset.** The coupling makes Ē(r) − static(r) vary across r, and P(z0=1|r) varies with r.

### Guards and invariances (all PASS)

| Check | Result |
|---|---|
| Inactive-slot insertion (`zS9`, `pad`) | max ΔP(r) = **0.0** |
| Permuting inactive metadata (reversed slot order, different fixed values) | **0.0** |
| Meaningful catalogue change (activating `zS2`) | recorded as a different catalogue hash; P(r) changes by up to 2.6e-3, so it is never treated as the same model |
| More than 8 active slots | `NOT_RUN (Unsupported raised)` |
| Cost added once (inside the z-sum vs after marginalizing) | difference 4.4e-16; adding it twice is detected |
| Temperature | a marginal at T = 0.5 inside a T = 1 chain is refused; computing it anyway deviates from the gold standard by 0.13 |
| Consistent object relabelling (a→z, b→y; reverses sort order) | transition-matrix difference **0.0** |
| Order sensitivity | swapped actions keep the same derived assignment but change the energy |
| Seeds | same seed reproduces the chain; a different seed differs |

### Mutation guards (each must be caught)

- a wrong Hastings ratio (+0.5 in log);
- a flipped acceptance sign;
- a missing order-energy recomputation (a stale order-free energy inside the kernel);
- inactive-z multiplicity (repair-dependent omission slots enumerated for every repair).

All four were caught.

Two additional **source-level** mutants of `sampler.py`, run temporarily on a backup and restored byte-identically (sha256 check OK), each made **11 of 22** tests fail:
- K_i dropped from the birth ratio;
- the current destination excluded from the Gibbs candidates.

### Supplementary only (not the proof)

Seeded chains of 200,000 steps give total-variation distances of 0.0057 (A1), 0.0204 (A2), 0.0042 (B1 marginal) and 0.0041 (C1 marginal). A one-step Monte Carlo of `step()` from a fixed A2 state matches the analytic row within 0.01, confirming that sampling uses the same rules as the matrix.

---

## 4. Figures

- [`overview.png`](../runs/g4b_sampler_exact/overview.png):
  - **A1 and A2:** exact π from the reference enumeration (dark bars) beside seeded-chain histograms (light bars, labelled supplementary).
  - **B1 and C1:** exact z-marginal π(r) with the same pairing.
  - **Top-right:** exact P(zR=1 | r) for B and C. The empty repair has no zR slot, so it shows 0.
  - **Bottom-right:** the **archived G4D R4 root**, drawn only from `runs/g4d_evidence/final_plan.json` and `unit_evidence.json`. It shows the full 3R arm at q0, the goal and both orders as numbered arrows: green (o01→18, o00→29) VERIFIED_FEASIBLE, red the swapped order CERTIFIED_INFEASIBLE by ORDER_FIRST_ACTION. It is tagged **CONTEXT ONLY - NO PLANNER/NEW EVIDENCE**; no robot path is drawn.

  Every sampler panel is titled SYNTHETIC ENERGY / MATHEMATICAL TEST.
- [`sampler_trace.png`](../runs/g4b_sampler_exact/sampler_trace.png): the first 160 updates of a seeded A2 chain.
  - **Top:** the current-state energy as a grey line; each true discrete proposal is a marker coloured by kernel, **filled if accepted, hollow if rejected**; unavailable moves (self-transitions) have no marker.
  - **Bottom:** the visited state's index in the reference enumeration.

  It is labelled SYNTHETIC ENERGY / MATHEMATICAL TEST and is not robot evidence.

---

## 5. Commands, exit codes, time and calls

| Command | Exit | Wall | CPU |
|---|---|---|---|
| `python run.py g4b --out runs/g4b_sampler_exact` (final run; regenerated after removing one unused constant, identical numbers) | 0 | 73.0 s | 72.5 s (in-process) |
| `python -m pytest -q tests/test_sampler.py` | 0 (22 passed) | 1.9 s | — |
| `python -m pytest -q` (full suite, with a scratch call-counting plugin, not committed) | 0 (157 passed) | 161.8 s | — |
| `python run.py replay --run runs/<run> --report <scratch>` ×6, in parallel | all 0; all `replay_passed` | 25.4 s | — |
| Mutation runs (two source mutants of `sampler.py`, temporary) | 1 each (11 failed, as intended), then restored | about 2 s each | — |

**Planner and target calls by G4B code: 0.** These entry points were instrumented in the stage run and each recorded 0 calls:
- `planner.plan`, `skill.plan_skill`;
- `evaluate.evaluate_target`;
- `verify.relocate`, `verify.plan_fixed_order`;
- `ordered.teach_sequence`.

`test_sampler.py` also recorded 0 calls under the regression counter.

**Historical regression tests, disclosed separately.** These are in-process counts from the scratch plugin. Worker subprocesses in `test_g4d_run.py` and `test_teacher.py` are not covered by it.

| File | `planner.plan` | `skill.plan_skill` |
|---|---|---|
| `test_arm2d.py` | 75 | 3 |
| `test_g4a.py` | 198 | 22 |
| `test_g4d.py` | 24 | 4 |
| `test_g4d_corrections.py` | 40 | 4 |
| `test_interventions.py` | 37 | 1 |
| `test_protocol.py` | 104 | 14 |
| `test_verify.py` | 143 | 12 |
| **Total** | **621** | **60** |

They are the established regressions, unchanged. No new data-collection planning occurred.

---

## 6. Provenance

| Item | Value |
|---|---|
| Stage config | hash `sha256:2e26d7bd4bfa914dd9903f91ec66ca7cc7b5611040a87e20a06afe55a6659fb0` (in `config.json`). T = 1, probabilities 1/4 each, unequal-probability check (0.4, 0.3, 0.2, 0.1), at most 8 active z, tolerance 1e-10, chain seed 20261020, 200,000 supplementary steps. |
| Config files | No TOML added. The historical `config.toml` and `config_v2.toml` hashes are unchanged (tested). |
| Source hashes (in `result.json` and `manifest.json`) | `sampler.py`, `g4b.py`, `g4b_figures.py`, `sequences.py`, `config.py`, `tests/test_sampler.py`, all re-verified equal to the committed files |
| Size | `runs/g4b_sampler_exact/` is 260 KB |

**Untracked files, all yours and all left untouched and uncommitted:**
- `instruction-phase-md/G4B_…md`, `instruction-phase-md/G4D_…md`, and the two PDF copies;
- `latent_causal_tamp_2D_ABC_guides_v1_7_v1_9/` and its `.zip`.

Consider adding the v1.7/v1.9 documents through the `docs/` versioning convention in a future, explicitly requested step.

---

## 7. Scope and limitations

- **What this proves.** The kernels and the bounded-z marginal define a π-reversible, normalized Markov chain on these **finite synthetic** spaces (up to 29 repair states and 292 joint states). It says nothing about learned energies, mixing time at 2D scale, or robot outcomes.
- **Joint chain.** A joint (r, z) Markov chain is disabled; larger z layouts return NOT_RUN.
- **Cache optimizations.** None exist: every energy is recomputed in full. Any future cache must first equal full recomputation, as guide v1.9 requires.
- **B/C fixtures.** They are hand-specified energies. B's "prefix pair order" and C's "GRU-like" factors are mathematical stand-ins for testing marginalization, not the G5 models.
- **Module sizes.** All new modules are within the guideline (220, 180 and 242 logical lines). `verify.py` and `skill.py` were not touched.

---

## 8. Decision

**G4B PASS.** Against the acceptance criteria:

1. The 13- and 29-state spaces are enumerated correctly and independently.
2. All four kernels satisfy exact normalization, detailed balance and stationarity, including unequal K_i, a context object, and the edge cases.
3. The B/C bounded-z joint, marginal, conditional, mask, temperature and inactive-slot checks match the exact gold standard.
4. There was no training, no planner or target call by G4B code, no relabelling, no evidence rewrite and no target feedback.
5. All 157 tests pass and the six archived replays succeed with archives unchanged.
6. The artifacts, figures and source-hashed report exist.

**STOP.** G4C, G4E-ABC, G5, G6, 3D and hardware are not started and need your explicit authorization.

---

## Repository synchronization

Before committing I checked for secrets and looked at the diff. The commit contains:
- `sampler.py`, `g4b.py`, `g4b_figures.py`, `tests/test_sampler.py`, and the edit to `run.py`;
- `runs/g4b_sampler_exact/`;
- this report.

It is pushed to `main` without force. The commit hash is given in chat and recorded in report 0013.
