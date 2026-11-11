# 0087 — P16: training, freezing and prospective evidence custody

## 1. Splits, labels and leakage

**Splits** (rosters frozen in `85a0eba` before any label; `runs/p16/data/SPLIT_COUNTS.json`):

| split | roots | labels | feasible / infeasible / UNKNOWN originals | use |
|---|---|---|---|---|
| dev | 24 built, 12 labelled | full (pairs) | 2 / 10 / 0 | development, also training |
| train | 80 (79 after exclusion) | 42 full + 37 lattice-only | 29 / 37 / 13 | training |
| val | 22 (21) | 5 full + 16 lattice-only | 6 / 11 / 4 | checkpoint selection, temporary-target validation |
| calib | 40 | full | 15 / 15 / 10 | thresholds, D0 diagnosis (clean) |
| test | 168 | sealed lattice-only (48 D roots) + y0 inside the sealed execution | B: 72 / 40 / 23 decided-or-not | prospective |

**Labelling rule.** Labels come from the deterministic certifier only:
- 1 = VERIFIED;
- 0 = a sound certificate;
- UNKNOWN is masked, never 0.

**Leakage.** Root ids are disjoint across splits. Two cross-split geometry duplicates were excluded before any label. No P16 root appears in the motion index (`LEAKAGE.json`, `EXCLUDED.json`).

## 2. Training, calibration and freeze

**B** (0085 §4–5):
- 15 runs (LB, LB-F2, LC, LB+G, A × seeds 0–2), 5,683 CPU-s in total including D;
- trained on 440 P13 + 91 P16 roots;
- checkpoints selected on 95 validation roots (74 P13 + 21 P16);
- no-op-first thresholds per arm on the 30 decided calibration roots.

**D:**
- 3 pairless retrains with the corrected label rule (0086 §5).

**Freeze.** Commit `437e771` pushed `P16_PREREG.json` (sha256 `ba17080d…`) before any test label. It records:
- code hashes, all 18 checkpoint hashes, training-data hash and policies;
- B and D hypotheses, scopes, the execution plan and analysis rules.

## 3. Prospective run and custody

| step | commit / file |
|---|---|
| pre-registration pushed | `437e771` |
| sealed run launched: per root, D guides then every B arm on one exact cache | `p16_eval.test_exec` |
| **amendment 1** (scheduling only; no outcome inspected): remaining NAT (B-only) roots first, then D roots in frozen order, shared claim queue | `0c8bd12` (`P16_PREREG_AMENDMENT_1.json`) |
| 24 sealed output files hashed, `SEALED_MANIFEST.json` pushed | `9389d34` |
| unsealed after the on-origin check | `runs/p16/data/test/UNSEALED` (sha256 `ead7da88…`) |
| analysis | `runs/p16/eval/{B_TEST,D_TEST}.json` |

**Coverage** (`execution` cap reached: 37,756 of 38,000 CPU-s):

| arm set | covered | by family / note |
|---|---|---|
| B | **135 / 144** | NAT 118 / 120; mechanism 17 / 24 |
| D | **21 / 48** | DENSE 4 / 24; PC_SG, PN_GIMP, PN_SIMP, PR_SIDES 3 / 3 each; ORD_CHAIN 2 / 3; TRI_OR 2 / 3; OMIT_OPT 1 / 3; TRI_CTRL 0 / 3 |
| oracle guide | **NOT_RUN** | needs post-unseal execution budget; none left. No cap was borrowed |

**Why coverage fell short.**
- Measured cost was about 550 CPU-s per 7-guide D root, and about 125 CPU-s per B-only NAT root.
- The cost pilots covered too few hard roots (the val pilot's DENSE roots were feasible originals), so they under-estimated.
- The first 33 roots took 19.2k CPU-s. Amendment 1 re-ordered the remaining work by cost only, which protected the B primary at the expense of D coverage.
- The 12 roots in progress at the cap were lost; 17 were never reached.

## 4. CPU accounting (CPU-s; all killed or censored jobs included)

| category | spent | cap | notes |
|---|---|---|---|
| audit (P16-0) | 828 | 3,000 | historical regression |
| motion (P16-1) | 8,160 | 9,000 | 4 default-profile runs stopped at the cap |
| shared (P16-2) | 6,299 | 10,000 | 5,450 of it on stopped default-profile DEV label / tag workers |
| b_dev | 1,203 | 10,000 | dev pilot, calibration, cost pilot |
| d_dev | **10,010** | 10,000 | +10 s overshoot: two concurrently launched temporary-lattice jobs (ledger since fixed with reservations) |
| data | 37,734 | 55,000 | about 25k on non-test labels, including 15k on killed slow workers |
| training | 5,683 | 20,000 | |
| execution | 37,756 | 38,000 | sealed test run and cost pilot |
| final | about 1,000 | 6,000 | analyses, figures, GIFs, final regression |
| **total** | **about 108.7k** | 161,000 | |

**Unledgered (operator errors):**
- two self-killing `pkill` shells, which ended < 1 min of worker CPU;
- 34 accidentally launched label jobs, each killed within seconds and guard-recorded.
