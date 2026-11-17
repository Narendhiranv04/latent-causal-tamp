# SORC-Grid fidelity audit: Tang & Sukhatme (CoRL 2022) → our K≤3 target-repair task

**Source.** The paper and supplement were read from the PMLR PDFs. Local copies with sha256 are under `~/sorc_grid/paper/`; text was extracted with `pdftotext`. The method is **SORC-Grid (adapted Tang & Sukhatme 2022; grasp-only, target-goal-conditioned)**. It is **not** an exact SORC reproduction, and **not** Ren & Qureshi's OSNet/RPNet.

## What the paper does (§3, Fig. 2–3, Alg. 1–2)

| Part | Paper mechanism |
|---|---|
| Observation | RGB-D (simulated RealSense D415, 640×480). Objects come from UOIS-Net-3D segmentation. The goal is an RGB-D **goal image** of the selected objects. |
| Sequencing (§3.3) | **Accessibility graph** (Alg. 1): a robot vertex plus object vertices. An edge means a collision-free straight end-effector path. For each object v_i, the sub-graph G_t − {v_i} is compared to the goal graph G_g by a pretrained **SimGNN** that approximates graph edit distance. The **argmax-similarity** object goes next (Alg. 2). SimGNN is trained supervised on GED-similarity labels. |
| Action (§3.1) | POMDP with **PUSH and GRASP** Q-maps. A DenseNet-121 (ImageNet) feature extractor feeds FCN heads (three 1×1 conv layers with BN+ReLU) over 16 rotations, giving 32 maps. The GRASP maps are **masked by the sequencer's chosen object**, and the robot takes the action with the highest Q-value. Reward is 1.0 for a successful GRASP (gripper feedback) and 0.5 for a successful PUSH (depth change). Loss is Huber TD on the selected pixel/pose only. |
| Placement (§3.2) | A template of the grasped object (ResNet feature crop) is cross-correlated with the **goal image** features, then a depth-occupancy cross-correlation is subtracted. The argmax over non-occupied locations is chosen; below a threshold the object goes to the **bin**. Loss is cross-entropy with one positive pixel (the simulator goal pose). |
| Termination | The episode ends when the goal arrangement is reached. Evaluation uses task completion and position error (Table 2). |

## Adaptation (forced by the benchmark contract; nothing re-added silently)

| SORC part | SORC-Grid | Why / disclosure |
|---|---|---|
| RGB-D, UOIS segmentation | Public structured geometry: object pose, cell, shape attributes, target, goal, robot context (`contracts.view2d/3d`). No images. | No RGB-D exists in the benchmark. There is no image-equivalence claim. |
| Accessibility graph: collision-free straight paths | Same construction on public geometry. Edge feature `clear(i, j)` = no other object's disc or footprint within the clearance radius of the straight segment i→j. Plus relative pose features. | This is a geometric proxy for a collision-free end-effector path. It uses no planner and no teacher. |
| SimGNN similarity of G_t − v_i vs the goal graph | **Learned task-conditioned graph difference.** One shared graph encoder, with node i removed (masked from attention and pooling). It is compared to a **task-goal graph** (robot, target at its goal cell, fixed structure) by a SimGNN-style head (NTN-like bilinear plus MLP). The choice is the argmax. | Our task has no goal arrangement for non-target objects, so a GED label cannot be defined without leaking repaired scenes. The similarity head is trained from **verified successful repairs**, using a multi-positive listwise loss on the next object. |
| PUSH + GRASP Q-maps (TD, reward from feedback) | **GRASP-only relocation-step executability** head, p(step executes \| hypothetical prefix, object, destination). It is trained with BCE (supervised TD-0 with terminal reward and no bootstrap) on **physically localized step outcomes**: `x_phase` relocation:j gives earlier steps = 1 and step j = 0; X = 1 gives all steps = 1. Unattributed failures are masked. | PUSH is forbidden by the benchmark. The phase log covers a whole relocation (pick, transport, place), not the grasp alone. This is a supervised replay classifier, **not** deep Q-learning with online exploration. As in SORC, it re-weights the sequencer's choice and never overrides legality. |
| Template × goal-image cross-correlation for PLACE (one positive pixel, plus bin) | Correspondence-style PLACE. The selected object's template embedding is dot-producted with scene-conditioned **cell** features. Cell features cover occupancy, distance to the target, the goal and the base, plus target/goal corridor proxies. The output is masked to statically legal original-empty cells, and the loss is **multi-positive** cross-entropy over observed successful destinations. **No bin.** | There is no desired position for non-target objects, so destinations proven useful by successful repairs serve as a set of positives. The occupancy penalty becomes a hard legality mask, since S0-occupied, vacated and goal cells are illegal. |
| Swap, bin, stacking | Absent. | Forbidden by the contract: zero push/swap/bin actions by design. |
| Closed-loop re-observation after each action | **Open-loop, one-shot.** The policy updates only hypothetical object positions, emits one ordered K ≤ 3 sequence, and the sequence is sealed and verified once. | Primary-comparison rule shared with Approach B, DISCO-Grid and REAP. |
| Goal-reached termination | Learned **STOP** head, p(target task from q_ref feasible \| hypothetical endpoint scene), trained on deduplicated endpoint Y labels. NOOP / REPAIR / ABSTAIN uses a fixed rule on calibrated probabilities (see policy.py). | There is no simulator to check termination at inference. The same learned head decides how far to go. |
| ImageNet DenseNet-121 / ResNet backbones | A compact graph/attention encoder, width 128, trained from scratch per domain. | No images exist, and model size is kept modest (contract §5.3). |

**Still the paper's method:** the three-part learned decomposition (which object → how → where), graph-difference sequencing over an accessibility graph, sequencer-masked action-value selection, correspondence-based placement, and Huber/BCE-style supervised heads.

**Not the paper's method:** goal images, perception, PUSH, swap, bin, online RL exploration, and the GED-supervised SimGNN.
