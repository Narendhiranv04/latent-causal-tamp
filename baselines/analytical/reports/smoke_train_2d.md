| run (2d) | n | decisions | verified outcomes | Task % [95% CI] | by K | CPU mean / median / p90 s | phys calls | transitions | connector | Y | ref plans |
|---|---|---|---|---|---|---|---|---|---|---|---|
| em4m_paper_s0_b120 | 6 | {'REPAIR': 5, 'ABSTAIN': 1} | {'SUCCESS': 5, 'ABSTAIN': 1} | [83.33, 66.67, 100.0] | {'1': 100.0, '2': 100.0, '3': 50.0} | 61.4 / 85.295 / 120.001 | 71.83 | 47.83 | 9.5 | 8.5 | 6 |
| em4m_paper_s0_b60_cut120 | 6 | {'REPAIR': 3, 'ABSTAIN': 3} | {'SUCCESS': 3, 'ABSTAIN': 3} | [50.0, 33.33, 66.67] | {'1': 50.0, '2': 100.0, '3': 0.0} | 38.5 / 60 / 60 | 71.83 | 47.83 | 9.5 | 8.5 | 6 |
| mosegman_paper_s0_b120 | 6 | {'REPAIR': 2, 'ABSTAIN': 4} | {'SUCCESS': 2, 'ABSTAIN': 4} | [33.33, 33.33, 33.33] | {'1': 100.0, '2': 0.0, '3': 0.0} | 61.6 / 58.399 / 120.003 | 35 | 21.67 | 4 | 3.33 | 6 |
| mosegman_paper_s0_b60_cut120 | 6 | {'REPAIR': 2, 'ABSTAIN': 4} | {'SUCCESS': 2, 'ABSTAIN': 4} | [33.33, 33.33, 33.33] | {'1': 100.0, '2': 0.0, '3': 0.0} | 51.4 / 58.399 / 60 | 35 | 21.67 | 4 | 3.33 | 6 |
| msmcts_paper_s0_b120 | 6 | {'REPAIR': 3, 'ABSTAIN': 3} | {'SUCCESS': 3, 'ABSTAIN': 3} | [50.0, 33.33, 66.67] | {'1': 100.0, '2': 50.0, '3': 0.0} | 23.3 / 28.692 / 44.451 | 13.33 | 11.33 | 0.5 | 1.5 | 0 |
| msmcts_paper_s0_b60_cut120 | 6 | {'REPAIR': 3, 'ABSTAIN': 3} | {'SUCCESS': 3, 'ABSTAIN': 3} | [50.0, 33.33, 66.67] | {'1': 100.0, '2': 50.0, '3': 0.0} | 23.3 / 28.692 / 44.451 | 13.33 | 11.33 | 0.5 | 1.5 | 0 |

CPU is capped at the cut for `_cut` rows; the call columns of `_cut` rows are those of the full source run (an upper bound).
