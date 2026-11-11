# 0061 — P13-2: physical mechanism constructors (DEV) and pilot

**Previous turn sync:** P13-1 pushed as `efc685474fe1b633423648bc202a981c66474fb5`.

**Actual result.**
- **Gate:** `runs/p13/P13_2_GATE.json` → **PASS** (scientific limitations listed below).
- **Grammar:** `p13_scenes.py`, `P13_MECH_V1_1`.
  - **What it is:** new physics-first 2D mechanism grammars, plus one unconditioned natural-mix stream.
  - **Built on:** two primitives with *sound* certificates, a link-0 sweep barrier (`LINK0_SECTOR_PICK`) and a grasp-side occluder (`TARGET_PICK`). Order and omission chains use `ORDER_FIRST_ACTION`.
- **Authentic examples on DEV roots**, every one adjudicated by the teacher:
  - κ = +1: PC_SG ×1, PC_SERIAL ×2 (both single edits certified, A+B witnessed);
  - κ = −1: PR_SIDES (all three edits witnessed);
  - κ = 0: PN_SIMP, PN_GIMP, NAT;
  - a witnessed 3-move order chain with certified reversed orders;
  - necessary omissions (certified) and an optional omission (witnessed);
  - complete 8-subset triple lattices with Δ_ABC = +1 (TRI_SERIAL) and Δ_ABC = 0 (TRI_CTRL ×2).
- **Not constructible within the budget:**
  - **TRI_OR (Δ_ABC = −1):** 0 / 2 complete lattices, so Δ = −1 stays **NOT_EVALUATED**;
  - **executable PC_SERIAL barrier relocations:** 3 / 3 were UNKNOWN or BUDGET at 275–287 CPU-s, so PC_SERIAL is prediction-only.
- **Spend:** DEV 3,921 / 10,000 CPU-s, of which the teacher accounts for 3,015 across 16 roots.

## 1. Mechanism grammar (link 0 cannot wrap)

**Where barriers must go.** The free link-0 sector between the start angle a₀ and the target is the only route. A barrier must separate a₀ from *every* target pick angle, not only from the target bearing. The first probe failed exactly on this: the original was "z₀ certified" on only 10 / 30 attempts. The DEV fix draws barriers from the arc cells closest to a₀.

| family | layout | intent (sound certificate / pose screen) | catalogue (outcome-blind) |
|---|---|---|---|
| PC_SERIAL | A, B both sweep barriers | z₀, A, B certified; A+B open | empty, edits A, B, A+B (prediction-only, V1.1) |
| PC_SG | A barrier, B sole open-side occluder | A edit TARGET_PICK, B edit sector | AB, BA, A, empty, edits |
| PR_SIDES | A, B occlude two open sides, third fixed | A, B, A+B open | A, B, AB, BA, empty, edits |
| PN_SIMP | A barrier, B impostor just outside the arc | B edit sector-certified; A open | AB, BA, empty, edits |
| PN_GIMP | A sole open-side occluder, B far-side decoy | B edit TARGET_PICK; A open | A, B, AB, BA, empty, edits |
| ORD_CHAIN | T ← A ← B (← C) toward the base | inner first ORDER_FIRST_ACTION; chain pickable | good order, reversed orders, omissions, edits |
| OMIT_OPT | 2-chain + far object D; repair "B A D" | chain + D pickable | B A D, B A, A D, B D, A B D, empty, edits |
| TRI_SERIAL / TRI_CTRL | 3 barriers / 2 barriers + impostor | all 8 subsets: certified / open as intended | empty + all 7 edits |
| NAT | 3 movers near the target / sweep window | **none** (natural stream) | A, B, AB, BA, empty, edits |

**Other design choices:**
- **Exact attribution:** every scene edit uses the D parking destination, so each edit *is* a D lattice query.
- **Avoiding unprovable negatives:** single relocations whose failure would rest only on a *remaining* sweep barrier have no static certificate, so they are left as unlabelled omission slots and never queried.
- **Disclosure:** construction is a mechanism-conditioned case-control (certificate intent recorded per root); NAT is unconditioned.

**Static constructibility on DEV seeds** (`PROBE.json`):

| family | acceptance |
|---|---|
| PC_SERIAL | 17 % |
| PC_SG | 33 % |
| PR_SIDES | 80 % |
| PN_SIMP | 40 % |
| PN_GIMP | 70 % |
| ORD_CHAIN | 40 % |
| OMIT_OPT | 37 % |
| TRI_SERIAL | 10 % |
| TRI_CTRL | 27 % |
| TRI_OR | 37 % |
| NAT | 83 % |

## 2. Teacher pilots (`runs/p13/dev/half{0,1}`, `runs/p13/dev/pilot2`)

**Pilot 1** (P10B_S100_V1; 10 roots, 1,215 CPU-s):
- **Proof-grounded as intended:** PC_SG κ = +1, PR_SIDES κ = −1, PN_SIMP and NAT κ = 0, ORD_CHAIN (15 CPU-s), OMIT_OPT (28 CPU-s) and TRI_SERIAL (2 CPU-s).
- **No answers:** PC_SERIAL, PN_GIMP and TRI_OR had their feasible-intent queries **UNKNOWN**. The first 100 CPU-s seed was censored, which ended the query, so these roots spent 287–479 CPU-s and produced no ground truth. Pose-screen counts do not separate the outcomes (for example, 25 pick candidates → UNKNOWN versus 1 → VERIFIED), so this is planner censoring, not geometry.

**Policy P13_S100_V2:**
- **What changed:** a censored seed no longer ends the query; the remaining declared seeds run. Seeds stay at 100 CPU-s each, queries at 330 CPU-s and roots at 900 CPU-s, and the adjudication is unchanged.
- **Code:** a one-line backward-compatible change in `p10b_dataset.collect`, which now reads the existing `POLICY["stop_after_censored_seed"]` flag.
- **Test:** the P10b policy is unchanged.

**Pilot 2** (V2; 6 roots, 1,800 CPU-s):
- **PC_SERIAL ×2:** κ = +1 is proof-grounded on both, with A+B witnessed in 3 s. The executable barrier orders were UNKNOWN or BUDGET, which led to V1.1 (prediction-only).
- **TRI_CTRL ×2:** complete lattices, Δ = 0, ~2 CPU-s each.
- **TRI_OR:** A+C and A+B+C UNKNOWN, so the family is dropped.
- **PN_GIMP:** fully decided under V2 (A and A+B witnessed), 18 CPU-s.

**Physics finding:** removing only the inner chain blocker is BUDGET (operational). The gripper needs two free approach cells, so chain edits are not proof-grounded κ examples.

## 3. Erratum to 0060 §3 (keying)

0060 compared block *counts* and reported that keyed and unkeyed instantiation differ on 18 / 65 P10b and 0 / 80 P12 roots. **That is wrong.** Compared by F5 scene–query pair instances (`KEYED_ERRATUM.json`), they differ on **65 / 65** and **80 / 80** roots:

| cohort | unkeyed instances | keyed instances |
|---|---|---|
| P10b blind | 3,792 | 2,108 |
| P12 holdout | 14,400 | 4,800 |

Unkeyed B instantiates every listed slot with its parent's context and role. B-U is therefore a real control on every root.

## 4. Design fixed for P13-3 (`runs/p13/PREREG.json`, sha256:7dbcb3a9…)

**Roster:** 370 new roots, interleaved, in batches of ≤ 16. Train 160, validation 40, blind challenge 122, natural blind 48.

| family | blind challenge roots |
|---|---|
| PC_SERIAL | 16 |
| PC_SG | 16 |
| PR_SIDES | 14 |
| PN_SIMP | 12 |
| PN_GIMP | 12 |
| ORD_CHAIN | 14 |
| OMIT_OPT | 14 |
| TRI_SERIAL | 12 |
| TRI_CTRL | 12 |

**Arms (3 seeds each):** K-B, K-C, A, SF, B-F2, B-F3, **B-F3pm**, B-F4, B-F5s, **B-F5spm**, B-F5q, **B-F5qpm**, **B-F1off**, B-V0, B-U. The parameter-matched off arms are within 0.06 % of K-B's parameter count. D / D-pairless are trained alongside.

**Primary family** (Holm over 4):

| test | comparison | endpoint |
|---|---|---|
| F3 | B vs B-F3pm | joint four-bit log-loss under P_S |
| F5 | B vs B-F5spm | joint four-bit log-loss under P_S |
| F2 | B vs B-F2 | order accuracy |
| F4 | B vs B-F4 | omission log-loss |

**Minimal meaningful effects:** NLL 0.05; order accuracy 0.10; omission log-loss 0.05; κ = +1 MAE 0.10.

**Verdict rule:** a factor is SUPPORTED only if it clears Holm *and* the minimal effect, and does not significantly harm the κ = 0 false-interaction rate or the natural-mix replication.

**Teacher estimate:** under 60 CPU-s per root on the pilot families.
