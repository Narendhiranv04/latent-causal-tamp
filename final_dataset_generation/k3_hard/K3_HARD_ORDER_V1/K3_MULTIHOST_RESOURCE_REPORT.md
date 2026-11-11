# K3 Multi-Host Resource Report
Hosts: laptop (<= 27 logical CPUs, 5 left free) and gvlab (<= 20 CPUs, >= 4 left free). Enigma and Blackwell were not used; no GPU (would change the teacher). 2D ran on gvlab only after cross-host parity: 36/36 perm2d re-evaluations byte-identical to the laptop (incl. witness ids) and 4/4 hard2d jobs identical (root id, strength, path, evals). Two earlier gvlab parity attempts were invalid (missing scipy, then PIL in the 3D venv); fixed with a separate 2D venv pinned to the laptop freeze (Python 3.13.11, numpy 2.4.6, scipy 1.18.1).

## 2D
CPU by host:
| | cpu_h | first_utc | jobs_finished | last_utc | mean_cpu_s_per_job | median_cpu_s_per_job |
|---|---:|---:|---:|---:|---:|---:|
| GVLAB | 17.4 | 2026-11-11T02:10:28Z | 38 | 2026-11-11T10:32:45Z | 1653 | 1423 |
| LAPTOP | 301.7 | 2026-11-10T22:34:48Z | 1006 | 2026-11-11T10:28:26Z | 1079 | 904 |

CPU by final strength of the job:
| | cpu_h | jobs | mean_cpu_s |
|---|---:|---:|---:|
| 1/6 | 98.39 | 416 | 851 |
| 2/6 | 77.52 | 235 | 1188 |
| 3/6 | 49.14 | 134 | 1320 |
| 4/6 | 10.09 | 29 | 1253 |
| 5/6 | 1.04 | 3 | 1254 |
| no_accept | 82.64 | 227 | 1311 |

Yield by start strength:
| | cpu_h | jobs | to_1_6 | to_le_2_6 |
|---|---:|---:|---:|---:|
| start 2/6 | 16.4 | 79 | 39 | 39 |
| start 3/6 | 66.8 | 221 | 121 | 171 |
| start 4/6 | 63.1 | 187 | 72 | 113 |
| start 5/6 | 130.5 | 431 | 150 | 275 |
| start 6/6 | 41.9 | 126 | 34 | 53 |

Generation CPU-h total: 318.8; new gate-pass roots per strength: ```{"1/6": 417, "2/6": 368, "3/6": 288, "4/6": 99, "5/6": 3, "6/6": 0}```

## 3D
CPU by host:
| | cpu_h | first_utc | jobs_finished | last_utc | mean_cpu_s_per_job | median_cpu_s_per_job |
|---|---:|---:|---:|---:|---:|---:|
| GVLAB | 184.2 | 2026-11-10T22:51:43Z | 251 | 2026-11-11T10:28:38Z | 2631 | 2136 |

CPU by final strength of the job:
| | cpu_h | jobs | mean_cpu_s |
|---|---:|---:|---:|
| 1/6 | 86.7 | 144 | 2168 |
| 2/6 | 41.32 | 47 | 3165 |
| 3/6 | 11.21 | 8 | 5045 |
| 4/6 | 2.84 | 3 | 3404 |
| no_accept | 41.83 | 49 | 3073 |

Yield by start strength:
| | cpu_h | jobs | to_1_6 | to_le_2_6 |
|---|---:|---:|---:|---:|
| start 2/6 | 11.3 | 21 | 13 | 13 |
| start 3/6 | 29.0 | 44 | 29 | 35 |
| start 4/6 | 35.6 | 45 | 26 | 36 |
| start 5/6 | 85.9 | 116 | 65 | 91 |
| start 6/6 | 22.0 | 25 | 11 | 16 |

Generation CPU-h total: 183.9; new gate-pass roots per strength: ```{"1/6": 144, "2/6": 47, "3/6": 8, "4/6": 3, "5/6": 0, "6/6": 0}```

Window: both hosts stopped by STOP file at 2026-11-11T10:28Z (12 h cap incl. pilot); in-flight jobs are MISSING, not failures. Validation (consistency, X/Y) ran after the cap on the freed CPUs within the same caps.
