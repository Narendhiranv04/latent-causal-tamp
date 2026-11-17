# V3.3 data audit — positive corrective-assignment supervision (TRAIN only)

**Scope.** TRAIN supervision for the two scratch samplers.
- VAL and TEST rows were only checked for byte identity; none of their outcomes were read for training.
- Machine-readable source: `DATA_AUDIT.json`, produced by `scripts/v33_data_audit.py`.

## Snapshots

| Role | Snapshot | `data2d.jsonl` sha256 | `data3d.jsonl` sha256 | Lock check |
|---|---|---|---|---|
| VAL / TEST rows; checkpoint VAL ELBO | `abf_9de85710c2a7103f` (base) | `16222ff8…` | `1627f34b…` | OK |
| S-control TRAIN | `abf_v3_e8a496bc66266fca` (pre-expansion V3) | `a10aeba8…` | `fcb30732…` | OK |
| S-expanded TRAIN | `abf_v32_fb0eef4f5ff433ee` (V3.2 expanded) | `963c16b2…` | `bc03d897…` | OK |

All three hash pairs match `reports/v3_2_stage2/resolved_config.json`, on both the user's laptop and girish.

## Split hygiene

| Check | 2D | 3D |
|---|---|---|
| Roots (train / val / test) | 3,500 / 751 / 749 | 1,766 / 364 / 370 |
| Same root set in all three snapshots | yes | yes |
| Split label changed vs base | 0 | 0 |
| VAL rows changed vs base (control / expanded) | 0 / 0 | 0 / 0 |
| TEST rows changed vs base (control / expanded) | 0 / 0 | 0 / 0 |
| TRAIN rows changed, expanded vs control | 449 | 305 |
| `parent_family_id` in more than one split | 0 | 0 |
| `layout_root_id` in more than one split | 0 | 0 |
| New positive assignments on non-TRAIN roots | 0 | 0 |

## What a sampler target is

A target is an assignment returned by `contracts.positive_assignments` that passes `contracts.v3_grammar`:
- its canonical endpoint has Y = 1;
- at least one ordered execution of it has X = 1.

Rules applied:
- **Order dedup:** every successful order of the same assignment counts as **one** target.
- **Never positive:** X = 0, Y = 0, a missing Y, or an unresolved label.
- **Training examples:** one per (object, destination) action of each target, with each root's weights summing to 1. This is `placement.repair_data`, `assign="all"`, unchanged.
- **Checks:** test `test_positive_assignments_dedup_orders_and_require_x_and_y` covers the rules. The audit also asserts Y = 1 and at least one X = 1 for every target.

## Positive assignments

| | 2D S-control | 2D S-expanded | 3D S-control | 3D S-expanded |
|---|---|---|---|---|
| TRAIN roots with ≥ 1 positive | 1,913 | 1,938 | 1,136 | 1,158 |
| Unique positive assignments | 3,530 | 4,409 | 2,178 | 3,032 |
| … of length 1 / 2 / 3 | 860 / 1,279 / 1,391 | 1,017 / 1,464 / 1,928 | 434 / 884 / 860 | 538 / 1,213 / 1,281 |
| Successful orders (before dedup) | 5,123 | 6,394 | 3,702 | 4,890 |
| Successful orders per assignment | 1.45 | 1.45 | 1.70 | 1.61 |
| Distinct (root, object, destination) actions | 6,651 | 8,120 | 3,980 | 5,046 |
| Grammar-excluded positives | 0 | 0 | 0 | 0 |
| `repair_data` training examples | **7,591** | **9,729** | **4,782** | **6,807** |
| `repair_data` targets sha256 | `1d94a3b1…` | `4c84e827…` | `0d3cbde0…` | `0dae8dc5…` |

**What the expansion added (S-expanded minus S-control, TRAIN only):**

| | 2D | 3D |
|---|---|---|
| New unique positive assignments | **879** (length 1/2/3: 157 / 185 / 537) | **854** (104 / 329 / 421) |
| Roots that gained assignments | 272 | 254 |
| Newly positive roots | 25 (legacy K0 21, K1 2, K3 1, NONE 1) | 22 (all legacy K0) |
| New distinct actions | 1,469 | 1,066 |
| Control positives missing in expanded | 0 | 0 |

**Comparison with the V3.2 candidate labels.** V3.2 labelled 4,477 (2D) and 2,680 (3D) candidates. After requiring X = Y = 1 and deduplicating orders and existing positives, only 879 (2D) and 854 (3D) of them are new sampler targets.

**Newly positive K0 roots.** Most newly positive roots are legacy K0 (no-op) roots on which a repair also succeeds. They are valid repair-destination evidence under the unchanged supervision rule. Under the locked weighting, each enters with total weight 1, as in `EXPERIMENT_REGISTRY.json`.

## Normalization provenance

Both arms use the Q2 TRAIN feature scaler `data/q2_<dom>/scalers.json`. These are deterministic per-feature mean and std constants, not model weights.
- **2D sha256:** `884b3567…`
- **3D sha256:** `36a94926…`

No Q2 or other pretrained weights are loaded: tests `test_fixed_step_scratch_arms_match_and_never_load_q2` and `test_scratch_init_identical_per_seed_and_device_independent`.

## Production reference data (for context only)

The historical `q2init_all` sampler was Q2-pretrained and then fine-tuned on the V2 snapshot `abf_v2_7d146b53e4b92fe4`. That snapshot is neither of the V3.3 arms' training sets, so comparisons with it change initialization **and** data.
