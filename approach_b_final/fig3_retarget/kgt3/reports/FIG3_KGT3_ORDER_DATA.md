# FIG3_KGT3 P2 — matched ordered-chunk data on fresh families

**Contract:** `../FIG3_KGT3_PREREG.json` P2, committed in `f11230eb2d`. Builders were committed in `15e0076b5d` before any outcome.

**Sealed manifests** (`p2/`; every manifest guard-COMPLETE: one terminal record per sealed key):

| Manifest | Jobs | sha16 |
|---|---|---|
| `jobs_p2_2d.json` | 593 | `3f0010504382e010` |
| `jobs_p2x_2d.json` (2D expansion) | 439 | `76c5d3eba9a1a49a` |
| `jobs_p2_3d.json` | 288 | `7ebc4f6a861c74e3` |
| `jobs_p2x_3d.json` (3D expansion) | 237 | `346a66e62322d4c2` |

**Splits** are fixed by family before any label: generator seeds and original-VAL families feed TRAIN / SELECT / GATE; original-TRAIN families feed TRAIN only. Every exposed DEV root and lineage, and every R3.1, R3.3A, R3.1D and cohort family, is excluded. All queries are physical X-only chunk runs with a terminal connector, and **no home return inside a chunk**. Labels come from `labels.chunks_of`: no anchored singleton labels are derived from completed chunks, unobserved suffixes are dropped, and UNKNOWN is never a negative.

## Design (as pre-registered)

**2D**
- **Verified-chain stratum.** Clean R3COH2D generator layouts, one per seed family (102 families; the cohort and reserve seeds are excluded). The offline kill-table screen picks orders: per family, a discordant-screen pair (both orders), a discordant triple (3 orders) and a control pair at h0, then a pair and a triple at h ≥ 1.
  - The h ≥ 1 states follow a teacher-verified witness-search prefix (35 families) or the kill-table first action (the rest).
- **Ordinary stratum.** Clean original families with a v32 X = 1 prefix, using cVAE and random actions.

**3D**
- **Verified-chain stratum.** On clean original families, the teacher's own planner (`A.query`, the K4/K5 generator primitive) built one enabler chain per family:
  - body B → pB plans;
  - one new largest-size obstacle E next to B blocks it;
  - E → pE plans;
  - with E parked, B plans again;
  - a third body Z plans.
  - Queries: [E B] vs [B E], three g = 3 orders at h0, [Z | E B] vs [Z | B E] (h = 1), and the [Z E] / [E Z] control.
- **Ordinary stratum.** v32 X = 1 fragments (h0 pairs, h = 1 pairs).

## Results

| | 2D | 3D |
|---|---|---|
| Families (initial + expansion) | 121 (68 chain + 53 ordinary) | 128 distinct: 48 verified chains (54 attempted) + 97 ordinary. 17 families carry both a constructed and an ordinary root, always in the same split. |
| Teacher queries | 1,032 runs | 515 construction probes + 525 runs = 1,040 |
| CPU | 7.83 CPU-h | 1.22 (construction) + 2.24 (runs) CPU-h |
| UNKNOWN / ERROR / censored | **644 UNKNOWN** (591 UNKNOWN_PLANNER, 53 UNKNOWN_TRANSIT) / 0 / 0 | 0 / 0 / 0 |
| Exact labels | 712 | 621 |

**2D.** The bottleneck is teacher decidability in dense chain scenes.

| Screen verdict for the order | VERIFIED | CERTIFIED_INFEASIBLE | UNKNOWN |
|---|---|---|---|
| Screen-dead | **0** | 160 | 198 |
| Screen-live | 32 | **0** | 324 |

- The offline screen is sound: no screen-dead order verified.
- But the BXY teacher cannot decide most screen-live orders in these N 14–20 scenes. It reports UNKNOWN_PLANNER, mostly at relocation 0.
- So the executable member of a matched pair is rarely observed. Discordant pairs (one order X = 1, the other X = 0) are scarce: 6 GATE families.
- The ordinary stratum decides more often (VERIFIED 86, infeasible 110, UNKNOWN 122) but is rarely order-dependent.

**3D.** The constructed chains reproduce physically.

| Pair | Discordant (enabler first runs, blocker first fails) | Both fail | Both run |
|---|---|---|---|
| [E B] / [B E] at h0, continuous 2-action chunks | **47 of 48** families | 1 | 0 |
| [Z \| E B] / [Z \| B E] after the reached prefix | 16 of 26 | 6 | 4 |

- **Construction cost:** 515 probes over 54 families (about 9.5 per family; 6 had no verified chain).
- **Coverage gaps:**
  - h ≥ 1 multi-action labels come only from the 1-step reached prefix (no h ≥ 2);
  - there are no g = 3 chunks at h ≥ 1;
  - the "blocker introduced by a relocation" contrast was not constructed in 3D.

**Support** (independent families; floor 10 each on GATE):

| Domain / split | Mixed h ≥ 1, g = 2–3 | Discordant permutation families | Mixed h0 |
|---|---|---|---|
| 2D TRAIN / SELECT / GATE | 4 / 1 / **14** | 5 / 0 / **6** | 12 / 2 / **34** |
| 3D TRAIN / SELECT / GATE | 14 / 4 / **9** | 33 / 13 / **22** | 30 / 13 / **22** |

**Expansion** (pre-registered; triggered because GATE support was below 10 before any model read GATE):
- **2D:** +439 GATE queries. This used every eligible GATE generator seed and every clean VAL ordinary family under the sealed rules.
- **3D:** +510, allocated before outcomes as GATE +330, TRAIN +180, SELECT +90. The construction chain share closed GATE, and no eligible ordinary GATE family remained.
- Both expansions are exhausted. **Both domains are DATA_LIMITED** on the fresh gate:
  - 2D on discordant families (6 < 10);
  - 3D on mixed h ≥ 1 multi-action families (9 < 10).
- These are recorded as guard-bound decisions (`p2/gate_2d.json`; `p2/gate_3d.json`). Collection did not continue beyond the sealed rules.

## Figure

`figures/KGT3_P2.png`:
- (a) Teacher outcomes per domain, stratum and split.
- (b) GATE support against the floor.
- (c) 3D GATE model metrics.
- (d–g) Actual constructed 3D GATE scenes: enabler-first vs blocked-body-first at h = 0 and h = 1, with teacher outcomes.
