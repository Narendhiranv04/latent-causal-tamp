# 0093 — P17-3: physically realized 2D mechanisms, counterfactuals and the M7 finite-domain check

**Actual result**
- **Realized:** 9 of 10 mechanism families each have a physically VERIFIED, independently replayed witness and a physical counterfactual contrast (M0–M6, M8 at 3 and 4 moves, M9). Each has a rendered 2D scene and a GIF built from the replayed trajectory.
- **M7 (buffer reuse / repeated object) is PARTIAL.**
  - A physically verified A→u, B→v, A→w witness exists (M8_3, replayed).
  - The required finite-domain proof that no allowed no-repeat plan reaches the goal was not obtained on any of the 8 candidate roots.
  - On 5 of the 8 roots, the finite library domain contains a no-repeat plan (4 proven minimal). On the other 3 it cannot decide either class.
- **Gate P17-3: PARTIAL (M7).** M5 is realized, at the level of the recorded trajectory.
- **Tag provenance:** every tag is assigned post hoc from physics labels only; no model output is involved. Natural (NAT) and constructed families are recorded separately.

## 1. Coverage matrix (`runs/p17/mechanisms/evidence/<tag>.json`, figures in `visualizations/p17/mechanisms/`)

- **Mining** (`MINED.json`): physics-only rules over the full existential labels of p17train / p17calib / P16 train / dev / val / calib.
- **Exemplar selection** (`EXEMPLARS.json`): deterministic rules.
- **Evidence:** each exemplar was re-verified with `p17_verify.verify_existential` and replayed with `p16_motion.replay`.

| tag | mined | exemplar (split, root, family) | witness (VERIFIED + replay CLEAR) | counterfactual (physical status, certificate scope) |
|---|---|---|---|---|
| M0 feasible original + decoy | 101 | p17calib p13_2026280002, DENSE | empty sequence (no relocation) | relocating the nearby decoy o00→28 is also VERIFIED, i.e. redundant |
| M1 single blocker | 57 | p17calib p13_2026281001, NAT | o00→59 | original CERTIFIED_INFEASIBLE (LINK0_SECTOR_PICK at q0); alternative destination o00→36 VERIFIED |
| M2 complementary blockers | 38 | calib p13_2026234000, PC_SG | o00→52, o01→29 | o01 alone: UNKNOWN_PLANNER; o00 alone: CERTIFIED (TARGET_PICK). Lattice MINIMAL_SETS, proof-grounded |
| M3 alternative clearing sets | 27 | calib p13_2026231009, NAT | o02→47 | {o00} alone VERIFIED; moving both {o00, o02} VERIFIED but redundant (union ≠ intersection) |
| M4 ordered access chain | 18 | p17calib p13_2026282000, OMIT_OPT | o01→52, then o00→36 | reversed order CERTIFIED_INFEASIBLE (ORDER_FIRST_ACTION: motion-independent, not a timeout) |
| M5 intermediate swept obstruction | 15 strong candidates | dev p13_2026218000 | o01→59, o00→52 (3 verified branches) | o00→36 instead: the recorded later target-pick sweep collides with o00 at slot 36 (link1 and link2, 83 segments) |
| M6 joint slot assignment | 83 | p17calib p13_2026280000, DENSE | o00→59, o03→44 | both movers to slot 59, in either order: CERTIFIED (DESTINATION_OCCUPIED, after the occupancy update) |
| M8 ≥ 3 moves | 100 | p17train p13_2026271039, NAT | o02→59, o00→36, o02→52 (A–B–A repeat) | no-op baseline: CERTIFIED (LINK0_SECTOR_PICK at q0) |
| M8 ≥ 4 moves | 96 | p17calib p13_2026280009, DENSE | o01→52, o03→59, o00→44, o03→60 | no-op baseline: CERTIFIED (LINK0_SECTOR_PICK at q0) |
| M9 difficult negative vs UNKNOWN | 82 | calib p13_2026230001, DENSE | o03→59 | similar geometry: o00→23 and o00→15, o01→60 are CERTIFIED (ORDER_FIRST_ACTION); o01→14 and o01→14, o00→23 are UNKNOWN_PLANNER (budget) and stay unknown, never 0 |

- **M5 detail:** the alternative-slot sequence has status UNKNOWN_PLANNER, not CERTIFIED. The obstruction is demonstrated on the recorded later sweep; other trajectories that might avoid it are not excluded. The contract asks for a later-sweep obstruction with a verified alternative slot, and the evidence meets that at trajectory level. It is not a certificate.
- **Empty-sequence fix:** before the freeze, a q-dependent certificate on the empty sequence (realizable only at q0) was found to be reported UNKNOWN. This affected M1, M8_3 and M8_4. The verifier was fixed (with a test) and the evidence re-run; the earlier files are kept in `evidence/superseded/`.
- **Saved per family:** initial / intermediate / final occupancy, robot q, object poses, goal, accepted and rejected sequences, status and certificate scope, a witness `.npz`, the replay trajectory hash, and the scene fingerprint.

## 2. M7: finite-domain no-repeat check (`runs/p17/mechanisms/M7_LIB_w{0,1,2}.json`)

- **Candidates:** roots whose only verified labelled plans contain a repeated object.
- **Domain** (`P17_LIBRARY_DOMAIN_V1`, `p17_mech.lib_domain`):
  - relocations use library trajectories plus direct transits only, with no online relocation planning, so the edge set is finite and fully adjudicable;
  - an edge with no realization is REFUTED_IN_LIBRARY_DOMAIN; this is scoped to the domain, never global;
  - the target action is planned. VERIFIED is sound; a planner failure is UNKNOWN.
- **Two searches per root:** per-object cap 1 (no repeat) and cap 2 (repeat allowed), same slots and modes. M7 needs "repeat-allowed finds a plan; no-repeat proven absent".

| root | no-repeat (cap 1) | repeat allowed (cap 2) | verdict |
|---|---|---|---|
| train p13_2026221033 | BEST_VERIFIED_WITHIN_BUDGET (found) | found | not M7: a no-repeat plan exists |
| p17train p13_2026270007 | MIN_MOVES_AND_MIN_TRAVEL (found) | same optimum | not M7: minimal plan has no repeat |
| p17train p13_2026271032 | MIN_MOVES (found) | same | not M7 |
| p17calib p13_2026280009 | MIN_MOVES_AND_MIN_TRAVEL (found) | same | not M7 (the M8_4 root) |
| train p13_2026222001 | MIN_MOVES_AND_MIN_TRAVEL (found) | same | not M7 |
| p17train p13_2026274003 | NO_PLAN_IN_FULLY_ADJUDICATED_FINITE_GRAPH | NO_PLAN | undecided: the real repeat witness needs online relocation motions the domain excludes |
| train p13_2026228002 | NO_PLAN_IN_FULLY_ADJUDICATED_FINITE_GRAPH | NO_PLAN | undecided (same reason) |
| p17calib p13_2026281010 | NO_PLAN_FOUND (every target goal UNKNOWN_PLANNER) | NO_PLAN_FOUND | undecided |

The first five rows have a no-repeat plan in the library domain: four are proven minimal and allowing repeats does not lower the minimum; on train p13_2026221033 the planner found a budget-best plan. The last three rows are undecided.

- **Why the witness fails in the domain:** in every root, the labelled repeat witness itself is not realizable in the library domain (UNKNOWN_CERTIFIED_INFEASIBLE). Its relocations use online-planned motions.
- **Conclusion:** within a finite domain small enough to adjudicate, repeats are either unnecessary or unrealizable.
- **Not attempted:** a proof in the full online-planning domain. The planner's failure there is UNKNOWN, not a refutation.
- **Cost:** 13.4 CPU-h over 3 workers.
- **Status: M7 PARTIAL/BLOCKED.**
  - Witness: p17train p13_2026271039 (o02→59, o00→36, o02→52, replay CLEAR).
  - Necessity: blocked on the 8 roots listed above.

## 3. Constructed screens (`runs/p17/mechanisms/screen/`, pose-level)

- **Generators:** corridor / corridor2 / reach generators targeting repeats and long chains.
- **Volume:** 137 attempts, 3 accepted at the pose level, 5.4 CPU-h.
- **Per screen** (accepted / attempts):

| repeat_corridor ×2 | repeat_corridor2 ×2 | repeat_reach ×2 | long3 / long4 corridor2 | long4 corridor |
|---|---|---|---|---|
| 0 / 44 | 1 / 42 | 0 / 40 | 1 / 5 and 1 / 4 | 0 / 2 |

- **Use:** accepted scenes are pose-level candidates only. They were stopped by the operator before physical verification and are **not** used as mechanism evidence.
- **Reported separately:** these constructed strata are reported apart from natural scenes. No test set was built by filtering for B or D success.

## 4. Visual evidence

- **Per mechanism:** `visualizations/p17/mechanisms/<tag>.png` shows the initial, intermediate and final occupancy, the link and carried-object swept trajectories, and accepted vs rejected destinations.
- **GIFs:** `visualizations/p17/mechanisms/<tag>.gif` for every tag, including M4–M8. They are rendered only from replayed verified trajectory records, with `.sha256` sidecars.
- **Repeated-object waypoints:** the repeated-object example with every actual waypoint is `M8_3.gif`.
- **Other figures:** B and D figures are in 0097 and 0098.
