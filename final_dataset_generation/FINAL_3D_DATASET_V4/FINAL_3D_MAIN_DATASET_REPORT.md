# FINAL 3D main dataset (V4)

Shelf 6×6 open-sided, xArm7, without home position, no overpass. Source: `rss-ebm-infeasibility` @ `yadu/dataset-3d` fb1120a30 (published selection: NONE 408, K0 511, K1 357, K2 612, K3 517, K4 9 archived).

## Final counts (exactly 2,500 main scenes; K4 archived separately)

| class | scenes |
|---|---|
| NONE | 408 |
| 0 | 511 |
| 1 | 357 |
| 2 | 612 |
| 3 | 612 |

## Where the 95 additional K3 scenes come from

| layout origin | K3 layouts |
|---|---|
| PUBLISHED_K3 | 517 |
| PUBLISHED_RUN_DEPENDENT_K3 | 50 |
| GENERATED_V4_K3 | 45 |

- PUBLISHED_RUN_DEPENDENT_K3: teacher-verified K = 3 scenes of the published run that the published independent-moves rule did not count (a relocation needs another one first). Every one passed the published no-fixed-object rule and has >= 1 successful order in a fresh env.
- GENERATED_V4_K3: new layouts from the unmodified published generator (`run_shelf66_full.py`, K3 requests only) run locally (laptop lap4 / lap5, gvlab srv5); all passed the same checks.

## Selection rule

```
FINAL_3D_SELECTION_V4: the 2,500-scene 3D main selection (NONE 408, K0 511, K1 357, K2 612, K3 612); K4 archived separately.

* NONE / K0 / K1 / K2: the published selection (rss-ebm-infeasibility @ yadu/dataset-3d fb1120a30, selected.json) verbatim, frozen.
* K3 layouts: the 517 published K3 layouts + exactly 95 NEW layouts.  New layouts come only from (a) the published run's DEPENDENT scenes
  with verified K = 3 (raw/, not counted by the published independent-moves rule; admitted here under the order-dependence contract) and
  (b) layouts generated locally by the published generator (K3 requests only, namespace lap4).  A new layout is eligible only when its
  6 orders were all evaluated in a fresh env with >= 1 success and every non-target object passed the published no-fixed-object rule
  (none_dense.pickable_alone).  The 95 are the eligible new layouts with the strongest available order dependence (min n_success), then
  DEPENDENT before generated, then hash.
* One assignment per K3 layout: the original (strength = FRESH-env 6-order outcome), a DEPSEEK V1 re-parking child (fresh-env gate
  passed), a HARDK3 V3 child (gvlab, fresh-env gate) or a HARDK3 V4 child (laptop, fresh-env gate).  Chosen by an optimal assignment
  (scipy linear_sum_assignment) to target slots 1/6..6/6 = 214/184/92/61/31/30 (35/30/15/10/5/5 % of 612) with lexicographic weights:
  6/6 control quota protected, then 1/6 > 2/6 > 3/6 > 4/6 > 5/6; layouts beyond the targets keep their strongest assignment.
  Ties: assignment already finalized-X/Y-verified at its strength, fewer changed destinations, hash.
* Splits: the frozen first-cohort split manifest (SHELF66V3 placement extension) for every root it covers; every other root by
  SHELF66V3_PLACE_SPLIT_EXTENSION_V1 (union-find over the manifest groups + parent_family_id + identical layout; inherit; new groups
  by the V1 rule sha256("SHELF66V3_PLACE_ROSTER_V1|split|min root") < 0.70 train, < 0.85 val, else test).  Re-parked assignments share
  their layout's split.
  select_final3d.py OUT.json
```

## K3 source of the selected assignment

| source | rows |
|---|---|
| NEW_HARD_ORDER_V3 | 202 |
| PUBLISHED_ORIGINAL | 235 |
| PUBLISHED_RUN_DEPENDENT_K3 | 22 |
| NEW_HARD_ORDER_V4 | 111 |
| GENERATED_V4_K3 | 5 |
| NEW_DEPENDENCE_SEEKING_V1 | 37 |

## Splits

| class | train | val | test |
|---|---|---|---|
| NONE | 288 | 58 | 62 |
| 0 | 358 | 86 | 67 |
| 1 | 251 | 53 | 53 |
| 2 | 429 | 97 | 86 |
| 3 | 440 | 70 | 102 |

New roots: 524 inherited through manifest groups, 189 new groups by the V1 hash rule; conflicts with the frozen manifest: 0.

## Views

- **Hard-order challenge view:** the selected K3 assignment of each layout (`rows`).
- **Natural-distribution view:** the original assignment of the same layouts (`natural_assignment` per row; test-split rows give the natural holdout).

## Training readiness

**TRAINING_READY_PENDING_APPROVAL** (integrity ok: True). No training was started.

Caveats:
- 50 K3 layouts are published-run DEPENDENT scenes (excluded by the published independent-moves rule; admitted under the order-dependence contract); 45 K3 layouts were generated locally with the unmodified published generator (namespaces lap4 / lap5 / srv5)
- K3 hard-order view: 1/6 is near target but 2/6 and 3/6 are short; 5/6 and 6/6 exceed target because many layouts have no stronger verified assignment
- the K3 selection uses re-parked (hard-order / dependence-seeking) assignments for many layouts; the natural (original) assignment of every layout is kept for the natural-distribution view
- 3D X/Y labels are teacher passes (fresh env) without an independent replay process
- EMPTY_SEQUENCE Y-negatives reuse the teacher's original T-direct check (fresh-verified on a sample)
- the gvlab hard-order pass was time-boxed (05:45 IST); 2 in-flight jobs were stopped (MISSING, not failure)
- 13 selected rows have an omission endpoint with Y = 1 (a shorter repair is feasible from q_ref, i.e. minimal K under the finalized protocol may be lower); listed in the Y-negative report
- 2 selected K2/K3 rows have endpoint Y = 0 from q_ref although their legacy full-task label succeeds (target only feasible from the carried arm pose); kept with their finalized labels
