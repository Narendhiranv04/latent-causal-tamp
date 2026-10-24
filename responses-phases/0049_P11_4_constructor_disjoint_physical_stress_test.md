# 0049 — P11-4: constructor-disjoint stress test — BLOCKED (external generalization remains open)

**Actual result.**
- **Gate:** `runs/p11/new_holdout/P11_NEW_HOLDOUT_GATE.json` → **BLOCKED**.
- **No new holdout was frozen and no new test label was collected.** The confirmatory constructor-disjoint test was not run.
- **Reasons:**
  - The genuinely new, **non-adaptive** families mostly generate scenes whose original task is already feasible.
  - Making them hard would require certificate-targeted (adaptive) selection, which the contract forbids for this test.
  - The measured teacher cost puts a 40-root test at about 3× the authorized cap.
- **Consequence:** generalization beyond the P10b constructor families is **NOT ESTABLISHED**.

## 1. Families (development only; `p11_holdout.py`, `P11_NEW_FAMILIES_V1`)

Neither family uses any P10a / P10b template, certificate targeting or pose screen.

- **NF1_CLUTTER:** 4–7 obstacles at uniformly random annulus-safe cells within Chebyshev 3 of a random target; random goal and start stratum.
- **NF2_RING:** each of the target's 8 neighbours occupied with probability 0.6, plus 1–3 random cells within Chebyshev 3.
- **Catalogue (generic, outcome-blind):** movers = the 3 nearest obstacles; empty, singles, all ordered pairs and triples, edits A / B / A+B, all D parking subsets (23 queries per root).

## 2. Development evidence (budget `newcon_dev`: 1,123 / 1,200 CPU-s)

**Teacher pilot** (`runs/p11/new_holdout/dev`):

| dev root | family | original task | other queries | cost (CPU-s) |
|---|---|---|---|---|
| `p11_2026129000` | NF1 | VERIFIED (feasible) | 16 VERIFIED, 7 UNKNOWN (censored at 95 s) | 571 |
| `p11_2026129001` | NF2 | VERIFIED (feasible) | 22 VERIFIED | — |
| 2 further roots | — | NOT_RUN (budget) | — | — |

**Zero-teacher static diagnostic** (`STATIC_OBSTRUCTION_RATE.json`): fraction of generated roots whose original task has an accepted sound static certificate, i.e. is certifiably obstructed.

| family | obstructed | generated |
|---|---|---|
| NF1 | 3 | 40 |
| NF2 | 7 | 39 |

## 3. Why the test was stopped rather than adapted

- **Hard cases need adaptive selection.** A holdout of mostly feasible originals would test only "choose the empty repair". Making the families hard requires filtering by certificates, which repeats the adaptive construction of P10b. The contract explicitly prefers a documented limitation to a selected, favourable holdout.
- **Cost.** At about 570 teacher CPU-s per root, 40 roots ≈ 23k CPU-s, against a cap of 8,000.
  - A cheaper seed policy (shorter seed guards) would turn more queries UNKNOWN.
  - It would have to be justified and frozen before labels, and still could not make the families hard.

## 4. Status for the final decision

**External (constructor-disjoint) generalization: OPEN / NOT EVALUATED.** All P10 / P11 results hold for the P10b constructor families only.
