# Finalized X/Y evidence coverage

**Summary: Stage E (finalized X/Y promotion) was NOT run in this phase.** Every order label produced tonight is a **legacy complete-task** outcome: relocations with the arm state carried forward, then the target from the achieved pose. None of it is promoted to X or Y, and no legacy contrast is claimed as an X contrast.

## Table D: what exists

| | 2D | 3D |
|---|---|---|
| **Historical finalized X/Y** | BXY sidecars (separate corpus, 635 roots): 7,701 X / 6,608 Y; development part 4,443 X / 3,831 Y; P24 sealed. Not on the class-quota scenes. | Sidecar V1 on the published cohort: **7,656 X / 7,072 Y**, 0 conflicts. X1/Y0 1,402 · X1/Y1 1,119 · X0/Y0 203 · X0/Y1 120 (train; val 295 / 253 / 43 / 25). 692 same-endpoint order groups decided, 25 X-discordant. |
| Same-endpoint X contrasts on selected K2/K3 orders | none measured | 16 dependent scenes have finalized-X discordance on the minimal and reverse orders. Only those 2 of 6 K3 orders are covered |
| **Newly promoted records (tonight)** | **0** | **0** |
| Omission contrasts (new) | 0 | 0 |

## Missing coverage for the final selections

| Item | 2D (selection V2) | 3D (selection V2, published) |
|---|---:|---:|
| Order records needing a connector-valid X | 800 × 2 + 1,150 × 6 = **8,500** | about 1,450 on original scenes + 476 K2 + 132 K3 on new scenes |
| Unique endpoints needing an independent Y | 1,950 | 714 (294 original endpoints have no Y record yet, plus 260 new) |
| Roots | 1,950 K2+ (train / val / test by the existing split) | 714 K2+ |

**Priority order for Stage E**, once you authorize it:
1. Selected dependent scenes in 3D (500), then 2D (1,170).
2. Within those, 1/6 and 2/6 K3 and K2 scenes whose failing order fails at a relocation step. These are the most likely to stay X-discordant once the target is no longer planned from the achieved pose.

**Estimated cost:** about one connector plan per order plus one Y per endpoint. That is roughly 15–25 CPU-hours for 2D and 20–40 for 3D on the same machines, so tonight's throughput suggests about one evening.
