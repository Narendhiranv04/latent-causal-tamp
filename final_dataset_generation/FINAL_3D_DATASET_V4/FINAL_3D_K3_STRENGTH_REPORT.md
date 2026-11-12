# FINAL 3D K3 order-strength report

Strength = successful orders of the 6 orderings of one K3 assignment, executed sequentially in a FRESH MuJoCo env (carried arm state, no reset; target planned from the achieved pose = legacy full-task strength). Finalized-X strength = orders whose relocations + connector to q_ref succeed.

| strength | natural (original assignment) | selected (hard-order view, legacy) | target | selected, finalized X |
|---|---|---|---|---|
| 1/6 | 4 | 210 | 214 | 203 |
| 2/6 | 17 | 112 | 184 | 114 |
| 3/6 | 50 | 53 | 92 | 57 |
| 4/6 | 121 | 46 | 61 | 54 |
| 5/6 | 225 | 121 | 31 | 116 |
| 6/6 | 195 | 70 | 30 | 68 |
| 0/6 | 0 | 0 | 0 | 0 |

Legacy -> finalized-X strength of the selected K3 rows:

| legacy->X | rows |
|---|---|
| 1->1 | 203 |
| 1->2 | 5 |
| 1->3 | 2 |
| 2->2 | 108 |
| 2->3 | 1 |
| 2->4 | 2 |
| 2->5 | 1 |
| 3->3 | 52 |
| 3->5 | 1 |
| 4->2 | 1 |
| 4->4 | 45 |
| 5->3 | 2 |
| 5->4 | 4 |
| 5->5 | 113 |
| 5->6 | 2 |
| 6->4 | 3 |
| 6->5 | 1 |
| 6->6 | 66 |

Published K3 originals whose teacher label disagreed with the fresh env on >= 1 order: 2 (fresh-env strength used).

New-layout pool: [[["PUBLISHED_RUN_DEPENDENT_K3", true], 50], [["GENERATED_V4_K3", true], 45], [["GENERATED_V4_K3", false], 2]]
