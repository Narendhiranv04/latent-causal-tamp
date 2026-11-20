# 2D K4–12 scaling TEST set: generation specification (G1 draft, DRAFT_V1)

**Scope**
- TEST-only roots for minimum-K strata K ∈ {4, 6, 9, 12}, with a target of 50 certified roots per K.
- No model is used anywhere in generation, labelling or acceptance.
- The engineering pilot roots (`ENG_*`, `ENG2_*`) are excluded from every release.

## 1. Layout proposal (static, no physics)

**Lattice and objects**
- The frozen 2D template lattice and robot profile (template root scene; q_ref = the template q0).
- Equal discs, r = 0.024 m: target `t0` plus movable obstacles `o00…`; no fixed objects; up to 20 objects.

**Proposal method**
- Simulated annealing (`gen_sa.py`, v2) over the layout. Moves: add, remove, or move one disc.
- Score: the **sound lower bound K_lb** (`cert.py` over the MINK_STATIC_V1 kill tables of the declared geometry), minus 0.02·n_objects.
- Seeded per run: `GENSA2|geom|seed`.

**Validity filters, applied before any teacher call**
- Every initial disc lies on a q_ref-clear cell (`G1/QCLEAR_original.json`: all cells except 50 and 58).
- Target and goal are distinct.
- The goal cell is placeable in the empty scene.
- The GEOM_V1 fingerprint is absent from `G0/HIST_EXCLUSIONS.json` and from every earlier accepted root.

## 2. Witness search (frozen teacher, unchanged; `witness.py` = the hosts' `witness_v2.py`, sha 3a25ef89cb0a5f04)

- **Teacher:** `bxy_teacher` c18ac91c89b9 / `p16_motion` 43f4c38c6418 under the frozen 2D environment. Host parity: G0 46/46 on girish and on enigma.
- **Search:** greedy prefix search over the bound's minimal goal set.
  - At each step, the relaxation-live (object, destination) pairs are ranked by the screen kills they add.
  - At most 6 candidates per step.
  - A prefix is kept when relocation j verifies, with failures attributed to the connector or a later relocation.
  - Then a final X query and a Y query on the full witness.
- **Contract:** at most 6 relocations (frozen teacher), so **K ∈ {9, 12} cannot be certified** without a versioned teacher extension (see `K_GT6_TEACHER_AUDIT.md` in the post-ablation validation).

## 3. Certification (minimum K)

A root is **CERTIFIED_MIN_K = K** iff all of the following hold:
- (i) K_lb = K under the sound static bound;
- (ii) a witness of length K has X = 1 with independent replay and Y = 1 with independent replay;
- (iii) Y(empty) = 0, observed.

Anything else is **WITNESS_ONLY_UNCERTIFIED** (quarantined, never released as K) or **NO_WITNESS_FOUND**.

## 4. Strata, budgets, splits

- Quota: K4 and K6 at 50 each. K9 and K12 are BLOCKED.
- The per-host and per-batch budgets are logged in the batch manifests.
- All accepted roots form one TEST split, with lineage = root id.
