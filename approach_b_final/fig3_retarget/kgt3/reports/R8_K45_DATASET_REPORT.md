# R8B: independent 3D long-horizon cohort (sealed)

**Result.** 99 fresh, physically verified 3D roots: **68 with L_ref 4** and **31 with L_ref 5**. They come from 99 distinct fresh families. The target was 200; this report gives the size achieved under the frozen budget.

Sealed 2026-11-28 07:47 IST:
- public sha256 `9e8d6a7e…`
- private sha256 `45977948…`

Raw records are in `reports/final/r8b/`:
- `SEAL.json`, `PUBLIC_r8b.jsonl`, `PRIVATE_r8b.jsonl`
- `BUDGET_FREEZE.txt`, `R8B_STATS.json`

## Pipeline (the established route; no new generator)

**1. Fresh K3 parents.** The unchanged production SHELF66V3 generator (`v34_gen.py`, teacher config 8d521b1f) was run under new name and seed namespaces:

| Namespace | Host |
|---|---|
| `r8bp` | gvlab2 |
| `r8bl` | laptop |
| `r8bw` | Blackwell |
| `r8bg` | gvlab |

- The generator code was sha-identical across hosts (one 3D-irrelevant trim utility differs).
- Slots use only factor templates (the V3.4 3D K3 specs). No reference roots were used.

**2. Derivation.** Unchanged `generate_a4.attempt_x` DERIVE, mode v2: the parent plus **one** physically necessary enabler, certified from scratch:
- initial target y = 0;
- continuous replayed witness X = Y = 1;
- a (K−1)-subset shorter probe; a verified shorter repair is rejected.

Each family is assigned in advance to pool A or pool B by `sha256('R8B-pool|'+parent)` parity:
- **Pool A:** K3 → K4 child, which is the roster root.
- **Pool B:** K3 → K4 intermediate (never in the roster) → K5 child, which is the roster root.

Each step gets ≤ 9 attempts. A family stops at its first accepted roster child, so there is at most one root per family.

**3. Labels.** Every root carries `WITNESS_LEN_{4,5}_MIN_UNKNOWN`:
- an independently replayed reference of length L_ref;
- **no certified minimum K**, since no sound lower bound exists.

**4. Quarantine.** References were never visible to any planner. The private index was committed only after the R8C plans were sealed.

**5. Budget, frozen prospectively and time-based only.**
- Generation dispatch stopped at 06:25 IST; in-flight attempts were allowed to finish.
- Derivation was hard-stopped at 07:45 IST; no family was still in flight at the stop.
- The rule does not depend on any outcome, so there was no cherry-picking.

## Yield and cost (attempted and rejected, all ledgered)

| Host | Generation attempts | Accepted roots | Of which K3 parents | Worker-h |
|---|---|---|---|---|
| gvlab2 | 160 | 99 | 57 | 100.6 |
| laptop | 277 | 122 | 63 | 199.5 |
| Blackwell | 152 | 87 | 56 | 84.9 |
| gvlab | 130 | 44 | 27 | 111.4 |
| **total** | **719** | **352** | **205** (incl. drain) | **496.4** |

Derivation: **1,993 attempts on 205 families, 86.0 CPU-h** (about 2.6 CPU-min per attempt).

- **K3 → K4:** the main rejections are DERIVE_NO_SINGLE_COVER (one enabler does not block every feasible grasp), no verified target-length witness, and no such destination.
- **K4 → K5:** lower acceptance, because it needs a second success.

**Composition of the roster:**
- by host family: r8bl 32, r8bw 28, r8bp 23, r8bg 16;
- objects per scene: 5 (21), 6 (33), 7 (23), 8 (13), 9 (7), 10 (2);
- figure: `reports/final/figures/e_dataset_r8b.png`.

**Disjointness.** Every family seed is new (new namespaces). No parent is a TRAIN, VAL, V3.4 or exposed-DEV root. The 20 exposed DEV roots are excluded by construction: they come from a different generator namespace (k45).

**Why it is short of 200.**
- K3 parent production was the bottleneck: about 26 minutes per attempt on the laptop, slower elsewhere, with a ~57% K3 rate among accepted roots.
- gvlab2's generator was paused most of the night by an over-conservative 92 °C guard. Its AMD CPU regulates at 95 °C by design, and the guard was raised at 01:30.
- girish was unusable: it reached 96 °C on 2 workers.
