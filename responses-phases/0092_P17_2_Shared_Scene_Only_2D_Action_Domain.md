# 0092 — P17-2: one shared scene-only 2D action domain (B and D)

**Actual result**
- **Shared domain:** `p17_domain.py` (`P17_DOMAIN_V1`) is the single action domain for B's candidate generator and D's search. Tests show that B's 1-move candidate set equals D's root expansion set exactly.
- **Supported:**
  - 0–4 relocations;
  - multiple destinations per object, recomputed on every hypothetical state;
  - freed source cells;
  - repeats (≤ 2 per object, never consecutive);
  - multiple motion modes per move (provider, 0091).
- **Gate:** `runs/p17/P17_2_GATE.json`.

## 1. Interface

| function | what it does (from scene / task only) |
|---|---|
| `p16_common.task_from_root` | {scene, goal, fixed structure ids, target, key}. Deletion test: removing catalogue / parking / roles / predicates / ids gives an identical task |
| `p17_domain.movers` | **every** movable non-fixed non-target object, nearest the target first; `MOVER_CAP` = 8 is only a safety bound, with omissions recorded (0 in every DEV / test root so far) |
| `p17_domain.slot_fn` | on the current occupancy: free annulus-safe cells at Chebyshev ≥ 2 from the current target cell and the goal, nearest the object (width 4), widened to Chebyshev ≥ 1 when fewer exist; then **freed source cells** of earlier-moved objects; then ≤ 2 library-witnessed destinations |
| `p17_domain.repairs` | deterministic, model-free, label-free ordered repairs of length 0–4: each step's destinations come from `slot_fn` on the hypothetically updated occupancy; per-length caps with **deterministic stride sampling**; every discarded candidate is counted |
| `p17_domain.query_id` | physical-query identity = task key + full ordered (object, destination) list; omissions recompute every intermediate pose (the encoder replays actions from the initial poses) |

## 2. Coverage and declared limits

- **B catalogue** (`B_CAPS`): 1 / 6 / 8 / 4 / 3 candidates of length 0 / 1 / 2 / 3 / 4.
- **Generated before stride sampling**, e.g. DENSE DEV 10000: 1 / 12 / 124 / 1,359 / 4,443. The catalogue therefore covers only a declared fraction of long repairs, and the omission counts are published per root in the labels.
- **D's search** explores the full domain lazily, under node cap 500 and budget.
- **Proposal recall** against an exhaustive enumeration of the same domain on small scenes is computed in 0093 / 0094: the fraction of physically certified exhaustive ≤ 3-move solutions that also appear in the capped catalogue.

## 3. Tests (`tests/test_p17.py`)

- `test_domain_scene_only_and_all_movers`:
  - deletion test;
  - all 4 DENSE movers present;
  - deterministic generation;
  - lengths 3 and 4 present;
  - repeats present, never consecutive.
- `test_slots_recomputed_after_moves_and_freed_source`: across every DEV pilot root, after a hypothetical move the moved object's source cell is offered to every other mover and no occupied cell is ever offered.
- `test_b_and_d_share_one_action_domain`: B's 1-move candidates equal D's root expansions.
- Physical-query identity: reversed order gives a different query; duplicate references collapse to one keyed variable (P16 keyed tests, unchanged).
