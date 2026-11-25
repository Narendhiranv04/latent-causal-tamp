# P5: whole-pipeline model-only comparison (DEV, cached exact-contract labels)

**Outcome: no primary revised pipeline qualifies** (`P5_FINALIST.json`).

- **Rule applied:** P4 produced no A*, so under `P5_P6_PREREG.md` rule 1 no CONFIRM query was spent.
- **Diagnostic:** the best trained checkpoint (A4 seed 0) was still run end-to-end, as a diagnostic only.

**Setup:**
- **Roots:** 578 VAL roots (K0/K1/K2/NONE).
- **Constructors and parameters:** frozen constructors and the completed study's parameters; seed 0; frozen gate and admission.
- **Outcomes:** historical strict. An uncached pick is UNKNOWN, never a failure.
- **Paired cells:** deltas vs A0 + EXACT4 use only roots where both picks are decided.

## K1/K2 end-to-end (decided success / decided, UNKNOWN; paired vs A0 + EXACT4: wins / losses)

| Scorer + constructor | DEV_CAL (130 roots) | DEV_AUDIT (110 roots) |
|---|---|---|
| **A0 + EXACT4 (released)** | 80/94, 36 unk | 65/83, 27 unk |
| A0 + EXACT6 | 75/93, 37 unk; 0 / 4 | 66/82, 28 unk; 1 / 0 |
| A0 + BEAM_SEEDED4@1024 | 71/91, 39 unk; 0 / 5 | 65/81, 29 unk; 3 / 1 |
| A0 + BEAM_FULL@1024 | 69/86, 44 unk; 3 / 5 | 64/79, 31 unk; 2 / 1 |
| A0 + PW_MCTS_SEEDED4@1024 | 76/92, 38 unk; 1 / 2 | 65/83, 27 unk; 3 / 0 |
| A4s0 + EXACT4 | 70/80, **50 unk**; 3 / 1 | 57/72, **38 unk**; 1 / 0 |
| A4s0 + EXACT6 | 58/66, 64 unk; 2 / 2 | 52/65, 45 unk; 1 / 0 |
| A4s0 + BEAM_SEEDED4@1024 | 43/51, 79 unk; 0 / 3 | 42/57, 53 unk; 1 / 1 |
| A4s0 + BEAM_FULL@1024 | 34/40, 90 unk; 1 / 2 | 33/48, 62 unk; 1 / 1 |
| A4s0 + PW_MCTS_SEEDED4@1024 | 44/53, 77 unk; 1 / 2 | 44/53, 57 unk; 2 / 0 |

Budget-256 arms are in `P5_MATRIX.json`; they mostly yield unlabelled picks.

**Safeguards are identical for every scorer × constructor cell:** correct K0 NOOP 90/92 (DEV_CAL) and 92/96 (DEV_AUDIT); correct NONE ABSTAIN 75/79 and 69/71.

## Reading

- **With A0, wider search does not consistently beat EXACT4 on cached DEV evidence.**
  - On DEV_CAL it loses: EXACT6 0 wins / 4 losses, staged beam 0 / 5, MCTS 1 / 2.
  - On DEV_AUDIT it wins a few: MCTS 3 / 0, staged beam 3 / 1, EXACT6 1 / 0. Every interval includes 0.
  - This agrees with the completed study's null result.
- **The retrained scorer A4 changes many EXACT4 picks.** The changed picks it can be scored on show 3 wins / 1 loss (DEV_CAL) and 1 / 0 (DEV_AUDIT). But it moves **14 / 11 more roots onto picks without any label.** Its end-to-end effect is therefore unidentified without new physical queries.
- **With A4, expanded search leaves most picks unresolved,** so no expansion claim is possible.
- **MCTS vs beam:** with either scorer, MCTS is never distinguishable from the staged beam. No MCTS claim is made.

## Timing (`P5_TIMING.json`)

Live, CUDA-synchronized, 30 predeclared DEV roots, RTX 5060:

| | EXACT4 | EXACT6 | BEAM_SEEDED4@1024 | BEAM_FULL@1024 | PW_MCTS_SEEDED4@1024 |
|---|---|---|---|---|---|
| A0 median (p90) s | 0.034 (0.21) | 0.070 (0.45) | 0.173 | 0.181 | 0.170 |
| A4s0 median (p90) s | 0.034 (0.20) | 0.072 (0.43) | 0.170 | 0.181 | 0.170 |

The architecture is unchanged, so the latency is identical. EXACT4 is still about 5× faster than any search arm at 1024.
