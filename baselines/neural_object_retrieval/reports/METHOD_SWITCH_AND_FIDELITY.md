# METHOD_SWITCH and paper fidelity: NOR-Grid (adapted Ren & Qureshi, ICRA 2024)

## Method switch, 2026-11-18

**Correction.** The first contract named Tang & Sukhatme's SORC (CoRL 2022). The user replaced it with **Ren & Qureshi, "Neural Rearrangement Planning for Object Retrieval from Confined Spaces Perceivable by Robot's In-hand RGB-D Sensor", ICRA 2024, arXiv:2402.06976** (OSNet + RPNet). The baseline ID is **NOR-Grid**.

**Preserved.** Commit `efa1b8da4f` was kept unchanged in git history. The worktree was moved from `baselines/sorc_grid` to `baselines/neural_object_retrieval`.
- **Reused, paper-agnostic:**
  - `nor_data.py`: snapshot loader, X/Y deduplication, the Y-label provenance used by the STOP adapter, and the P0 audit. It was renamed from `data.py` because that name shadowed the teacher's own `data` module.
  - `graph.py`: public object/cell features and the legality adapter (identical to `benchmark.legality`).
  - The P0 audit (`DATA_AUDIT_P0_paper_agnostic.md`, `dataset_manifest.json`).
- **Superseded, kept for the record in `reports/superseded/`:** the SORC plan, the SORC fidelity audit, and the SORC resource note (which allowed the gvlab2 GPU; NOR-Grid is laptop-only).
- **Never implemented:** SimGNN, graph-edit sequencing, GRASP-Q and correspondence placement. No SORC module exists in NOR-Grid.

## Paper sources

- `~/sorc_grid/paper_nor/ren_qureshi_2402.06976v1.pdf` (text extracted with `pdftotext`).
- The arXiv HTML v1.

The paper describes architecture, labels and losses (§III-C, D, E). It gives **no** training hyperparameters, data scale, path counts, grid size or cost constants. Every such value below is NOR-Grid's own declared choice, not the paper's.

## Mechanism fidelity

| Paper (§) | NOR-Grid | Status |
|---|---|---|
| **OSNet (III-C, eq. 2).** MLP token embeddings of robot base, gripper pose, target and non-target 6D boxes; multi-head self-attention Transformer; MLP head giving the "categorical" blocking distribution; argmax selection. | MLP token embeddings of robot context (base, q_ref), the declared target side-grasp summary, the target, its goal, and every object (2D: pose, radius, fixed/moved flags; 3D: box/cylinder size, height, pose); Transformer encoder; per-object MLP score; masked softmax over eligible movable, not-yet-moved objects; argmax. | Faithful architecture, with structured instead of perceived boxes. |
| **OSNet labels.** RRTConnect plus smoothing gives multiple paths to the target "without considering collisions with other objects"; count how often each object blocks; normalize; MSE. | `homotopy.py`: multiple reference paths of the **full target-to-goal task** from the **unchanged benchmark planners**, in a scene where the movable non-target objects are absent. Robot, structure/fixed obstacles, the side-grasp family and the 3D arm ceiling are kept. Each path is one grasp homotopy, chosen in seeded order. Blocking means full-arm / gripper / carried-target geometry comes within the planner's own margin. Counts are normalized; MSE. | Adapted: target-to-goal instead of reach-to-grasp, and grasp homotopies instead of RRT re-samples. Labels come from the frozen teacher geometry and are never invented. |
| **RPNet (III-D, eq. 3, 4).** Encoder over robot, gripper, target and region tokens (4D: x, y, z, observed flag); decoder queries = region embedding + selected-object embedding; MLP gives cost per region; argmin selection. | Encoder over robot, grasp, target, goal, object and cell tokens (cell features: position, static legality, occupancy now and at S0, goal flag). Decoder queries = cell embedding + selected-object embedding. Per-cell scalar cost; argmin over statically legal cells. | Faithful architecture. All cells are observed (no active sensing). |
| **RPNet labels.** Occupied, unobserved and path-blocking regions get maximum cost; others are ranked by distance from the object's initial location; MSE. | Cost 1.0 for statically illegal cells (occupied now or at S0, goal, undeclared) and for cells in the union sweep of the reference paths. Otherwise 0.9 × distance to the source / maximum legal distance. MSE over all cells. | Faithful principle. Constants are declared, since the paper gives none. |
| **Loop (III-E).** RRTConnect reachability check before each step; physically relocate; up to 5 steps; stop when reachable. | **Primary open-loop:** up to K = 3 hypothetical OSNet → RPNet steps; one sealed ordered proposal; independent post-seal X/Y verification. The termination signal is the added **OSRP-openloop-adapter** STOP head (target Y on the hypothetical endpoint), *not* part of the paper. | Adapted to the shared one-shot protocol. The native closed-loop variant is not run (NOT_RUN, optional secondary). |
| **Perception.** In-hand active RGB-D, Detectron2, GraspNet grasps. | Ground-truth structured poses and shapes, plus the benchmark's fixed side-grasp family. | Privileged structured observation. Not the paper's perception. |

**Prohibited and absent:** an extra TAMP framework, Approach B models (cVAE, XYNet, Q2 weights), DISCO/REAP components, test-time physics, and any SORC module.
