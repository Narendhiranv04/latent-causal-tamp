# SCALING2D_K4_12_TEST_V1

17 test-only 2D scenes with a certified minimum number of obstacle relocations K:

| K | Scenes |
|---|---|
| 4 | 5 |
| 5 | 5 |
| 6 | 5 |
| 9 | 2 |
| 12 | 0 (blocked by the 20-object cap) |

Scope: 8×8 original geometry, ≤ 20 objects, frozen K≤3 teacher (long-horizon wrapper for 7–12 relocations).

- `public/`: the inference inputs only (raw records). Feed these to models.
- `private/`: certified K, verified witnesses, minimum-K certificates, teacher replay hashes, G5 audit, and coverage of every candidate. **Never a model input.**

Full method, gates and shortfalls: `../FINAL_REPORT.md`. Figures: `../figures/`.
