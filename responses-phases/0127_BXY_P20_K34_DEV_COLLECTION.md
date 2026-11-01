# 0127 — BXY-P20: physically executable K3/K4 development scenes

Date: 2026-11-01. Gate: BXY-P20 (plan frozen in P19, commit `023faf19`). Namespace `bxyg34dev`, development only.
- Generator: [bxy_p20_k34.py](../bxy_p20_k34.py).
- Figures: [visualizations/approach_b/bxy_p20_v1/](../visualizations/approach_b/bxy_p20_v1/).

## Result

| Measure | Value | Frozen target (P19 plan) |
|---|---|---|
| labelled development roots | **86** (k1 29, k2 28, k3 29); 2,202 frozen queries, 2,174 labelled, 0 censored, 0 replay failures | ≤ 150 |
| **verified K3** (K_catalogue = 3, every shorter catalogue candidate decided) | **14** — **all 14 certified K3-necessary** (K_cert = 3) | ≥ 20 ready / ≥ 12 limited |
| **verified K4** | **7** — **all 7 certified K4-necessary** (K_cert = 4), 2 mechanisms (local_mixed 5, local_pick 2) | ≥ 20 ready / ≥ 10 limited |
| strict same-endpoint permutation X-discordant contrasts (K3/K4 roots) | **39** (15 with a certified failing order) | ≥ 10 |
| harmful (Y0 = 1 → Y_edit = 0) controls | 11 roots | ≥ 10 |
| neutral controls | 57 roots | ≥ 10 |
| CPU / wall | **23,909 / 60,000 CPU-s**, **7,052 / 28,800 s** | — |

**Frozen verdict:**
- **K3 meets the LIMITED threshold** (14 ≥ 12).
- **K4 does not** (7 < 10), so the frozen rule returns **`K4_PHYSICAL_DATA_NOT_ESTABLISHED`** for stratum-level K4 inference.

**K4 is nonetheless physically verified as a phenomenon.** Seven independent roots each have:
- a replayed 4-move relocation chain from q0, with the achieved state carried between moves;
- the connector to q_ref;
- an independent target witness from q_ref;
- Y = 0 after one, two and three moves (figure 00);
- a certificate that **no correction moving fewer than four objects can succeed** within the declared grasp family.

Seven roots are too few for per-stratum statistics, so K4 is reported descriptively in P21. **No K4 count was inflated and no criterion relaxed.** The three permitted waves were used; 36k CPU-s and 64 roots of headroom were left unused rather than adding an unplanned fourth wave.

## 1. Construction (geometry only; no populated-scene planning, no teacher call)

- **Doorway closure** (`_niche_side`):
  - a doorway of 3–6 angularly adjacent declared target modes stays the only fixed-free set;
  - fixed walls are chosen only from cells that kill modes **outside** the doorway and no doorway mode;
  - the k movable blockers lie in the intersection of the doorway modes' kill sets, so each doorway mode is covered exactly k times.
- **Sides and splits:**
  - pick side (`local_pick`) or pick + place (`local_mixed`);
  - K3 = 2+1 / 1+2, K4 = 2+2 / 3+1 / 1+3;
  - cross-side constraints: place walls never touch the pick doorway, and pick walls already killing place modes count.
- **Acceptance:**
  - exact order-free lower bound = K;
  - **K_cert = K** (real-screen certificate, P19 §3);
  - an intended order in which each blocker's pick screen is open (≥ 2, from k2 on ≥ 3 modes);
  - no analytic edge certificate;
  - short-carry parking (Chebyshev ≤ 2) with ≥ 3 open place modes off the reopened modes' kill cells;
  - after the full repair, ≥ 3 / ≥ 3 open target modes and no analytic certificate.
- **Controls:** P16 V21B `near_closed` K0 roots, plus V21B `nested` K3, the second geometry family.

| Wave | Version | Change (evidence) | Slots → roots | Construction CPU |
|---|---|---|---|---|
| k1 | BXY_GEN_K34 | P19 plan | 40 → 29 | 1,077 |
| k2 | BXY_GEN_K34B | k1: 50 of 216 relocation failures were planner-**certified** (link-0 sector / pick certificates from the achieved state), 152 search-budget → added the teacher's analytic per-step pick + place certificate check (`p15_retarget.certified`) and ≥ 3 open blocker modes | 55 → 28 | 3,172 |
| k3 | BXY_GEN_K34C | P16 + k1 per-cell evidence: relocations into / out of rows 0–2 succeed 0.1–0.6 vs 0.75–1.0 in rows ≥ 3 → task and parking cells in rows ≥ 3, intended blockers not in rows 0–1; K4-weighted composition | 55 → 29 | 4,141 |

- **Pre-freeze dry runs: 1,083 CPU-s,** charged in EXTRA_CPU.json. They exposed three problems:
  - the first enumeration required |M| = k, a bug;
  - strict local or annulus-free walls cannot close the modes;
  - only ~11% of modes are closable solely inside the link-0 annulus.
- **Every rejection is recorded** (NO_VALID_LAYOUT with reason counts).
- **k1 and k2 roots regenerate byte-identically** after each later revision (test).

### Realized physics per wave

| | k1 | k2 | k3 |
|---|---|---|---|
| verified K3 / K4 | 3 / 0 | 5 / 2 | 6 / 5 |
| intended K3/K4 repair (X, Y) = (1, 1) | 3 of 15 | 4 of 19 | **10 of 22** |
| intended repair (0, 1): physical failure, target would succeed | 4 | 3 | 1 |
| strict order contrasts (certified) | 6 (1) | 19 (3) | 21 (11) |

- **The binding limitation is physical relocation under the fixed per-query planner budget,** not target feasibility.
- K4 attempts fail mostly at relocation index 0–2 by NO_PLAN_FOUND, with the hypothetical target scene often feasible (figure 04).
- Per-relocation success by step is in figure 08.
- **Cause (viii), partly intrinsic:** closing every declared target mode of the planar 3R arm needs discs along the arm's link paths. Only ~11% of modes can be closed outside the link-0 annulus, so K-level closure puts obstacles where they also obstruct relocation transits.

## 2. Catalogue and query design (frozen per wave before labels)

- **Caps:** 24 candidates / 60 queries.
- **For K ≥ 3 roots:**
  - repair;
  - parking variant;
  - reversed;
  - two further permutations (strict order twins);
  - every stopping prefix;
  - every non-trivial single omission;
  - every single partial move;
  - wrong final destination;
  - repair + unnecessary move;
  - repair then harmful move;
  - interference pair;
  - neutral edit.
- **Query set:** Y0, then X (including the connector) and Y for each candidate, with Y deduplicated by endpoint.
- **Completeness:**
  - every verified K3/K4 claim has X and Y at every prefix, and every shorter F1-admissible candidate decided;
  - K_cert additionally covers all shorter corrections in the declared grammar.

## 3. Incident: duplicate supervisors after a session restart, and the CPU charged for it

- **What happened.** The Claude session was killed during k2. The k2 supervisor kept running inside a bwrap PID namespace invisible to the new session. A second supervisor was started twice, and duplicate workers ran on 20 roots.
- **Effect on labels: none.**
  - The duplicate workers raced on in-progress marker files, so 20 workers crashed with EXIT_1.
  - Result files are written atomically, the teacher is deterministic, and every result file verified (identity and JSON).
- **Repair.** Append-only conservative ledger corrections:
  - unmatched worker starts are charged at their wall-clock upper bound;
  - one negative manual charge was cancelled;
  - roots crashed by the collision were marked resumable.
  - A single supervisor then completed k2.
- **Over-charge.** Incident-related charges total 2,642 CPU-s: correction entries plus one root charged its full 1,400 CPU-s allowance by the collector's built-in orphan rule. Part of this is real duplicate-worker CPU; the rest is conservative over-charge. All of it stays in the P20 total.
- **Lost root.** That root, **k2-s034 (a K3 root), remains incomplete**: 3 of 31 queries labelled, the rest unattempted and absent. Its per-root cap is exhausted under the frozen rule.
- **Prevention.** Recorded in memory: check the shared STATUS / ledger writes, not `ps`, before relaunching.

## 4. Figures

| File | Content |
|---|---|
| `00_verified_k4_2-s013.png`, `00_verified_k4_2-s017.png` | **Full K4 stories** from recorded witnesses: S0 → after each of the 4 moves (X with connector, independent Y) → the composed repair with the target witness, plus the same four moves in another order that fails physically (NO_PLAN_FOUND; shared Y = 1) |
| `01` | doorway construction (geometric proposal): walls, blockers, reopened pick / place kill cells, intended order, reopened grasp pose |
| `02`, `03` | prefix-complete K4 / K3 stories |
| `04` | failed K4 attempts with the recorded failing phase |
| `05` | K_intent / K_cert vs verified K_catalogue |
| `06` | generator denominator (accepted / rejected by wave × family × K) |
| `07` | teacher CPU by phase |
| `08` | relocation success by step: P16 vs k1 / k2 / k3 |
| `106`, `107` | X/Y cells and negatives; X / Y at every prefix |
| `04_order_twins_*` | strict order twins |
| `05_harmful_vs_neutral_*` | harmful vs neutral edits |

## 5. Files and hashes

| Item | sha256 |
|---|---|
| DESIGN k1 | `cd0a80e5…` |
| DESIGN k2 | `6e7fbebf…` |
| DESIGN k3 | `e5e5f165…` |

- **Per-wave records:** AUTHORIZATION.json, GENERATION.json, PRELABEL_AUDIT.json, LEDGER.jsonl, results/, witnesses/, SUMMARY.json.
- **Gate-level records:** READINESS.json, EXTRA_CPU.json, BUDGET_MANIFEST_P20.json.
- **Tests:** [tests/test_bxy_p20_p21.py](../tests/test_bxy_p20_p21.py) — certified necessity and validated intent, catalogue label-invariance and caps, k1 reproducibility, readiness counting, wave refusal, P21 arm reuse.

## 6. Decision for P21 (recorded before any P21 step)

- **Mode:** P21 runs as the contract's **bounded exploratory analysis**, because K3 is at LIMITED level and K4 is below threshold.
- **Arms and data:** the same six P17 arms, retrained with the 86 K34 roots added.
- **Strata:** K3 results are labelled exploratory; **K4 results are descriptive only (n = 7 independent roots), with no K4 inference or "learned K4" claim.**

**Regression:** see §7.

## 7. Regression

Recorded in `runs/approach_b/bxy_p20_v1/regression/`:
- full suite: **716 passed, 1 skipped**;
- six archived replays: exit 0;
- hash guard: clean.

STOP (gate P20).
