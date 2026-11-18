| run (3d) | n | decisions | verified outcomes | Task % [95% CI] | by K | CPU mean / median / p90 s | phys calls | transitions | connector | Y | ref plans |
|---|---|---|---|---|---|---|---|---|---|---|---|
| em4m_paper_s0_b120 | 6 | {'REPAIR': 4, 'ABSTAIN': 2} | {'SUCCESS': 4, 'ABSTAIN': 2} | [66.67, 33.33, 100.0] | {'1': 100.0, '2': 50.0, '3': 50.0} | 73.5 / 91.297 / 120.002 | 21.67 | 6 | 1.83 | 2.83 | 11 |
| em4m_paper_s0_b60_cut120 | 6 | {'REPAIR': 3, 'ABSTAIN': 3} | {'SUCCESS': 3, 'ABSTAIN': 3} | [50.0, 33.33, 66.67] | {'1': 100.0, '2': 0.0, '3': 50.0} | 48.3 / 60 / 60 | 21.67 | 6 | 1.83 | 2.83 | 11 |
| mosegman_paper_s0_b120 | 6 | {'REPAIR': 2, 'ABSTAIN': 4} | {'SUCCESS': 2, 'ABSTAIN': 4} | [33.33, 33.33, 33.33] | {'1': 100.0, '2': 0.0, '3': 0.0} | 90.9 / 120.001 / 120.02 | 23.33 | 9.33 | 1 | 2 | 11 |
| mosegman_paper_s0_b60_cut120 | 6 | {'REPAIR': 2, 'ABSTAIN': 4} | {'SUCCESS': 2, 'ABSTAIN': 4} | [33.33, 33.33, 33.33] | {'1': 100.0, '2': 0.0, '3': 0.0} | 50.9 / 60 / 60 | 23.33 | 9.33 | 1 | 2 | 11 |
| msmcts_paper_s0_b120 | 6 | {'REPAIR': 3, 'ABSTAIN': 3} | {'SUCCESS': 3, 'ABSTAIN': 3} | [50.0, 33.33, 66.67] | {'1': 100.0, '2': 50.0, '3': 0.0} | 90.6 / 120.003 / 120.035 | 15.5 | 7.17 | 3.67 | 4.67 | 0 |
| msmcts_paper_s0_b60_cut120 | 6 | {'REPAIR': 2, 'ABSTAIN': 4} | {'SUCCESS': 2, 'ABSTAIN': 4} | [33.33, 33.33, 33.33] | {'1': 100.0, '2': 0.0, '3': 0.0} | 51.5 / 60 / 60 | 15.5 | 7.17 | 3.67 | 4.67 | 0 |

CPU is capped at the cut for `_cut` rows; the call columns of `_cut` rows are those of the full source run (an upper bound).
