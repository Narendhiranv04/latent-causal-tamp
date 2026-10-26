# 0075 — P15-2: scene-similarity retrieval, swept-motion transfer and motion modes

**Actual result.**
- **Gate:** `runs/p15/P15_2_GATE.json` → **PASS**.
- **Benchmark size:** held-out transfer statistics come from **330 leave-one-root-out queries** and **6,890 exact certifications** on real scenes.
- **Threshold decision:** the DEV-fitted similarity threshold is **rejected**. It loses 12 % of available motions on the TEST half. The deployed index stays un-thresholded (ranking only).
- **Spend:** `index` 1,676 / 6,000 CPU-s.

## 1. Index v2 (`p15_lookup.index_v2`, `MODE_STATS_V2.json`)

| item | value |
|---|---|
| P14 entries kept | 4,821 |
| additional leakage exclusions by **geometry fingerprint** (an entry whose root shares a fingerprint with an excluded evaluation-pool root) | **17** (P14 had excluded by root id only) |
| absolute (source, destination) keys | 277 |
| motion modes (canonical, deterministic; whole-path swept IoU ≥ 0.6 **and** terminal q within 0.3 rad) | **1,163** |
| modes supported by ≥ 2 independent roots | 328 |
| keys with ≥ 2 modes | 211 |
| clustering invariant to record permutation | 277 / 277 keys |
| object kinds / grasp-offset classes in the library | obstacle only / 1 class |

**Hard filters:**
- absolute source and destination, and footprint;
- the start configuration is handled by the certified transit;
- kind and grasp offset are recorded but not filtered: one class each, and `check_record` verifies that the grasp holds the object where it rests.

**Support** counts independent roots (one per root), never raw records.

## 2. Leave-one-root-out transfer benchmark (`TRANSFER.json`, `TRANSFER_SUMMARY.json`)

**Design:**
- **Query:** a held-out witness's own reconstructed scene and start q. Its existence proves the move was physically available there.
- **Candidates:** every witness of the same absolute move from **other roots**.
- **Adjudication:** each candidate gets the certified joint-linear transit from the query q to the candidate start, then `motion.certify_trajectory` in the query scene.

**Results by ranking:**

| ranking | top-1 certifies | any candidate certifies | mean certifier calls | first − best certified travel | rare-mode rescues |
|---|---|---|---|---|---|
| combined (local + 0.25 × global) | 167 / 330 (50.6 %) | 239 / 330 (72.4 %) | 6.37 | 0.159 | 53 |
| global only | 170 (51.5 %) | 239 | 6.19 | 0.143 | 49 |
| local only | 157 (47.6 %) | 239 | 6.83 | 0.117 | 57 |

**Candidate outcomes (all 6,890):**

| status | count |
|---|---|
| VERIFIED | 2,926 |
| UNKNOWN_TRANSIT (the straight transit from the query q is not certified) | **2,603** |
| COLLISION (in the new scene) | 1,347 |
| UNRESOLVED | 14 |

**Readings:**
- **Coverage is not reuse.** Even when a key matches, only 72.4 % of queries get *any* reusable other-root motion, and top-1 works about half the time.
- **The start-configuration mismatch, not scene collisions, is the largest failure source.** It is a failure of that particular straight transit, not proof that the witness start is unreachable.
- **Rare modes are real.** In **53** queries, the top-ranked mode's representative failed and a witness from a **different** mode certified, in a real held-out scene.
- **Multimodality changes cost.** The first certified candidate averages 0.159 more joint travel than the best certified one, so first-certified-only (P14) is not travel-optimal.
- **Rankings:** global-only and combined are close; local-only finds cheaper first-certified motions but needs more calls. No ranking dominates.

## 3. Similarity threshold (cost control only)

- **Fitting rule:** on the DEV half (keys alternating), the largest combined-score threshold that keeps ≥ 95 % of DEV availability: **1.050**.

| TEST half (164 queries) | available motions found | mean calls | top-1 |
|---|---|---|---|
| no threshold | 121 | 6.38 | 80 |
| threshold 1.050 | 107 (**88.4 %**) | 3.87 | 77 |

- **Decision: REJECTED.** On TEST it loses 11.6 % of available motions. A threshold controls cost, never physical possibility. The deployed retrieval stays un-thresholded; the threshold is evaluated only as a lookup ablation (0079).

## 4. Required checks

| check | status |
|---|---|
| free endpoints but mid-path link collision | 1,347 real collisions; also the P14 unit test |
| popular mode collides, rare mode valid | 53 real cases |
| new start q cannot transit to the recorded start | 2,603 real cases |
| index build cost | P14 build 1,143 CPU-s; v2 statistics 1.5 CPU-s; transfer benchmark 1,674 CPU-s; reported separately from per-query cost (~6 certifier calls per query) |
