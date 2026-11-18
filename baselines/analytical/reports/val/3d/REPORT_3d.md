| run (3d) | n | decisions | verified outcomes | Task % [95% CI] | by K | CPU mean / median / p90 s | phys calls | transitions | connector | Y | ref plans |
|---|---|---|---|---|---|---|---|---|---|---|---|
| em4m_paper_s0_b300 | 364 | {'NOOP': 83, 'REPAIR': 149, 'ABSTAIN': 132} | {'NOOP': 83, 'SUCCESS': 149, 'ABSTAIN': 132} | [67.27, 61.36, 72.73] | {'1': 90.57, '2': 72.16, '3': 42.86} | 163.2 / 154.413 / 300.002 | 24.86 | 7.31 | 2.53 | 3.35 | 11.51 |
| em4m_paper_s0_b60_cut300 | 364 | {'NOOP': 83, 'ABSTAIN': 246, 'REPAIR': 35} | {'NOOP': 83, 'ABSTAIN': 246, 'SUCCESS': 35} | [15.45, 11.36, 20.0] | {'1': 39.62, '2': 11.34, '3': 2.86} | 50.2 / 60 / 60 | 24.86 | 7.31 | 2.53 | 3.35 | 11.51 |
| mosegman_paper_s0_b300 | 364 | {'NOOP': 83, 'REPAIR': 88, 'ABSTAIN': 193} | {'NOOP': 83, 'SUCCESS': 87, 'ABSTAIN': 193, 'FAIL_X': 1} | [39.09, 34.09, 45.0] | {'1': 77.36, '2': 37.11, '3': 12.86} | 173.3 / 182.56 / 300.002 | 23.9 | 9.23 | 1.06 | 1.99 | 11.51 |
| mosegman_paper_s0_b60_cut300 | 364 | {'NOOP': 83, 'ABSTAIN': 268, 'REPAIR': 13} | {'NOOP': 83, 'ABSTAIN': 268, 'SUCCESS': 13} | [5.45, 2.73, 8.19] | {'1': 18.87, '2': 1.03, '3': 1.43} | 49.8 / 60 / 60 | 23.9 | 9.23 | 1.06 | 1.99 | 11.51 |
| msmcts_paper_s0_b300 | 364 | {'NOOP': 85, 'REPAIR': 101, 'ABSTAIN': 178} | {'NOOP': 85, 'SUCCESS': 101, 'ABSTAIN': 178} | [45.45, 39.55, 51.36] | {'1': 84.91, '2': 38.14, '3': 25.71} | 138.5 / 109.559 / 300.002 | 13.32 | 7.11 | 2.54 | 3.5 | 0 |
| msmcts_paper_s0_b60_cut300 | 364 | {'NOOP': 85, 'ABSTAIN': 244, 'REPAIR': 35} | {'NOOP': 85, 'ABSTAIN': 244, 'SUCCESS': 35} | [15.45, 11.36, 20.0] | {'1': 39.62, '2': 12.37, '3': 1.43} | 45.3 / 60 / 60 | 13.32 | 7.11 | 2.54 | 3.5 | 0 |
| msmcts_paper_s1_b300 | 364 | {'NOOP': 84, 'REPAIR': 102, 'ABSTAIN': 178} | {'NOOP': 84, 'SUCCESS': 102, 'ABSTAIN': 178} | [45.45, 39.53, 51.82] | {'1': 83.02, '2': 41.24, '3': 22.86} | 126.8 / 111.946 / 300.001 | 14.58 | 7.45 | 3.04 | 4 | 0 |
| msmcts_paper_s1_b60_cut300 | 364 | {'NOOP': 84, 'ABSTAIN': 237, 'REPAIR': 43} | {'NOOP': 84, 'ABSTAIN': 237, 'SUCCESS': 43} | [19.55, 15.0, 24.09] | {'1': 52.83, '2': 15.46, '3': 0.0} | 43.8 / 60 / 60 | 14.58 | 7.45 | 3.04 | 4 | 0 |
| msmcts_paper_s2_b300 | 364 | {'NOOP': 84, 'REPAIR': 102, 'ABSTAIN': 178} | {'NOOP': 84, 'SUCCESS': 102, 'ABSTAIN': 178} | [45.45, 39.55, 51.82] | {'1': 83.02, '2': 40.21, '3': 24.29} | 128.0 / 100.537 / 300.001 | 15.06 | 7.54 | 3.23 | 4.19 | 0 |
| msmcts_paper_s2_b60_cut300 | 364 | {'NOOP': 84, 'ABSTAIN': 237, 'REPAIR': 43} | {'NOOP': 84, 'ABSTAIN': 237, 'SUCCESS': 43} | [19.09, 14.55, 23.64] | {'1': 52.83, '2': 14.43, '3': 0.0} | 43.6 / 60 / 60 | 15.06 | 7.54 | 3.23 | 4.19 | 0 |

CPU is capped at the cut for `_cut` rows; the call columns of `_cut` rows are those of the full source run (an upper bound).
