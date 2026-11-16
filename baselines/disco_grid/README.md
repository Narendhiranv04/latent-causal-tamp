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
