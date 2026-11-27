# V3.4 3D target-feasibility (395 roots)

**Label:** y = 1 iff PRIVATE_INDEX 3D `K == "0"` (93 roots); K1/K2/K3/NONE give y = 0 (302 roots). The labels agree with the root files' `labels.original.y` and `verified_K` on 395/395 roots. All 93 K0 roots have `y_empty = 1`. Eight negatives are budget-limited (NO_PLAN_FOUND); they count as 0, and the JSON also gives results without them.

**Protocol:** p >= 0.5 means feasible for every method, as fixed in the CF/NULL lock. Seed s0 is primary. TPR and TNR intervals are Wilson 95%. AUROC intervals come from a 2,000-replicate bootstrap over 181 families.

| Method (s0) | TP | FP | TN | FN | TPR /93 | TNR /302 | Prec | Acc | AUROC |
|---|---|---|---|---|---|---|---|---|---|
| PIGINet (no image) | 83 | 12 | 290 | 10 | .892 [.813,.941] | .960 [.932,.977] | .874 | .944 | .989 [.976,.997] |
| GRN | 77 | 13 | 289 | 16 | .828 [.739,.891] | .957 [.928,.975] | .856 | .927 | .961 [.925,.986] |
| SCNet | 72 | 4 | 298 | 21 | .774 [.679,.847] | .987 [.966,.995] | .947 | .937 | .974 [.956,.988] |
| Ours, production D (not final) | 81 | 10 | 292 | 12 | .871 [.788,.925] | .967 [.940,.982] | .890 | .944 | .964 [.920,.991] |

AUROC, mean ± sd over seeds s0–s2: PIGINet .988 ± .002, GRN .960 ± .001, SCNet .974 ± .001, Ours .971 ± .006.

**Notes:**
- All four methods use the unchanged CF-audit adapters in `cf_infer.py` (sha 259a3b57…).
- The PIGINet and SCNet checkpoint sha256 values match lock amendment 2 exactly. The GRN checkpoints come from git 986cce3a and also match. GRN reproduces its V4 VAL AUROC to within 0.0002.
- SCNet's grasp poses were rebuilt in env3d. The stored-roots parity check was not re-run because `roots_scn.pkl` is not on the laptop.
- 348 roots have a `ref_root_id` in V4 VAL (used to select the baseline checkpoints) and none in V4 train.
