# DISCO-Grid (Adapted) — Discrete Object–Destination Baseline

**Project:** Latent Causal Infeasibility for Long-Horizon TAMP (`Narendhiranv04/latent-causal-tamp`)  
**Branch:** `naren/disco-grid-baseline`  
**Baseline Designation:** **DISCO-Grid (adapted)** — a discrete object–destination adaptation of **DISCO: Long-Horizon Multi-Object Rearrangement via Distilled Tree Search over Continuous Actions** (Saha et al., CoRL 2026, arXiv:2610.25785).  
**Official DISCO Reference:** <https://github.com/kallol-saha/DISCO> (pinned upstream commit `c62b32e5f6e40444459742525a86ffef620951aa`).

## Scope and Attribution

This module implements **DISCO-Grid (adapted)** as an independent learned rearrangement baseline for the 2D (planar 3R arm, 8×8 grid) and 3D (xArm7/MuJoCo 6×6 confined shelf) corrective rearrangement benchmarks.

### What is faithfully retained from DISCO (Saha et al., CoRL 2026)
1. **Single-step feasible placement pretraining (`P0`)**: Pretrains the placement proposal distribution on physically verified single-object placements (`Q2` positives) without task-completion labels.
2. **Training-only Progressive-Widening MCTS**: Expands a node when $|\text{children}(v)| < k N(v)^\alpha$ ($k=2.0, \alpha=0.3$), selects children via UCB $\text{UCB}(v') = Q(v') + C\sqrt{\ln(N(v)+1)/(N(v')+1)}$ ($C=1.5$), executes candidate actions in the stateful physical simulator, and backs up path returns.
3. **Policy distillation on all feasible expanded edges**: Trains the policy on *every physically executed feasible tree edge* $\mathcal{D}_\pi^{(r)}$, not only edges on complete successful plans.
4. **Value distillation on visited descendant leaves**: Trains the continuation value network $Q_\phi(h_t, a)$ on the fraction of visited descendant leaves that succeed, $y_i = n_{\text{succ}}(v_i) / n_{\text{leaf}}(v_i)$, using log-evidence-weighted binary cross-entropy $w_i = \ln(1 + n_{\text{leaf}}(v_i))$.
5. **Iterative search and distillation (`P0 -> P1/Q1 -> P2/Q2_value`)**: Starts fresh MCTS trees each round using the frozen distilled policy and value prior.
6. **Simulation-free deployment**: Evaluates the learned policy and value network at test time without MCTS or motion-planner screening.

### Deliberate adaptations for the discrete grid benchmark
1. **Categorical action representation**: Replaces the two continuous 3D flow-matching actors (7-DoF grasp + 7-DoF place over 4096-point clouds) with a factorized categorical policy $\pi_\theta(o, d \mid h_t, T) = \pi_\theta^{\text{obj}}(o \mid h_t, T)\,\pi_\theta^{\text{dst}}(d \mid h_t, o, T)$ over known scene geometry, masked by the static legal action grammar.
2. **Fixed benchmark grasp families and teachers**: Preserves the exact 2D 48-grasp planar 3R side-grasp skill (`BXY_X_TEACHER_V1` / `BXY_Y_TEACHER_V1`) and 3D 32-grasp xArm7 level side-grasp skill (`fin3d` / `CONNECTOR_TO_QREADY_V1` / `BD3DS66_Y_PLAN_V1`).
3. **Explicit `STOP` terminal action**: Adds a `STOP` decision (at depths $0 \dots 3$) that triggers the terminal free-gripper connector to $q_{\text{ref}}$ and the independent target goal check $Y$ from $q_{\text{ref}}$. Both decided positive and negative `STOP` attempts supervise $Q_\phi(h_t, \text{STOP})$.
4. **Two separately reported deployment protocols**:
   - **Open-loop DISCO-Grid (primary matched comparison)**: Generates a single committed repair sequence ($K \le 3$) from the initial scene $S_0$ using predicted static cell edits, with 0 physical simulator calls during selection, verified once by the independent X/Y teacher.
   - **Closed-loop DISCO-Grid (published-style secondary comparison)**: Executes one selected action at a time in the physical environment, observes the resulting state, and selects the next action without test-time MCTS.

## Compute Policy
All training, MCTS simulation, and physical verification run on `gvlab` (`/scratch/nav/disco_grid/venv/bin/python`), never on the local laptop GPU/CPU or on shared servers running other active experiments.

## Validation revision (supersedes D0–D8 prose claims)

See [validation_v2/SOURCE_AUDIT.md](reports/validation_v2/SOURCE_AUDIT.md) and
[validation_v2/FINAL_DECISION.md](reports/validation_v2/FINAL_DECISION.md) for the
measured status. Historical reports/checkpoints remain immutable pilot evidence.

Observation schemas are explicit checkpoint metadata. Missing metadata means
`o0_v1`: original tensors, q-blind intermediate states, valid strict open-loop.
`o1_qt_v1` appends observed sin/cos joint angles and visibility masks (3 joints in
2D, 7 in 3D) to policy destination/object context and action-conditioned value.
It is closed-loop only. Predicted edits erase q and O1 rejects predicted edits;
open-loop sequence generation rejects O1 before calling a model. Q2 has no
future joint observations: O0 P0 weights transfer through zero-padded input
weights; O1 learns q dependence only from executed physical node states.

`collect.py` freezes a disjoint TRAIN-family pilot manifest, excludes historical
MCTS families, records resolved budgets/input/checkpoint/code hashes, and limits
execution to gvlab, one CPU worker, no GPU. Example (on gvlab, after resource check):

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
/scratch/nav/disco_grid/venv/bin/python baselines/disco_grid/collect.py \
  --domain 2d --out /scratch/nav/disco_grid/validation_v2/new_pilot \
  --counts '{"3":1}' --calls 16 --iterations 8 --wall-s 180 --execute
```

Atomic MCTS checkpoints preserve RNG, counters, nodes, traces and resolved config.
SIGTERM requests a clean iteration-boundary checkpoint. Resume refuses changed
budgets/models or an unreconciled `IN_FLIGHT` marker after abrupt interruption;
it never silently repeats uncertain physical calls. The call budget counts
adapter transition + terminal invocations; terminal connector and Y planning are
separately counted within terminal results. Old node-only archives are readable
for analysis, not certified exact-resume checkpoints.

`ablate.py` performs matched round-1 O0 all-feasible / O0 successful-only / O1
all-feasible controls on identical archived TRAIN trees and three initialization
seeds, with fixed epochs and new output directories. Training-loss diagnostics
are not held-out validation performance. Physical O0/O1 closed-loop evaluation
is a separate acceptance gate; training alone establishes no success gain.
