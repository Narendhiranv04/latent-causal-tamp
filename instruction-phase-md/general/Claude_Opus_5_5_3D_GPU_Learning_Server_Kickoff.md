# Claude Opus 5.5 High | Approach B | 3D GPU Learning-Server Kickoff

**Execution request:** This is an engineering kickoff, not another methodology redesign. Set up a separate, safe 3D training workspace on `user1@10.4.25.63`; audit and freeze a verified 3D dataset snapshot; implement and run a bounded, scientifically valid **cVAE versus conditional flow-matching placement sampler** experiment if the GPU and CPU-support envelope are demonstrably safe; locate and audit the **existing X/Y Boltzmann model** and 3D sequence-level supervision; prepare its 3D path without inventing X/Y labels. Deliver code, results, plots, and a clear go/no-go for next-stage training.

The project includes ongoing production collection on a **different machine** (`gvlab`) and a long-running 2D Q2 collection on the laptop. **Do not interrupt either.** Do not move training to `gvlab` or the laptop. The IP `10.4.25.63` previously hosted a 3D native scene generator, so **SSH access does not imply idleness**. Probe it first. If it is busy, preserve everything and stop before GPU training.

## 0. Authority and immutable scientific contract

Read before writing or executing training:

1. The actual repository, particularly `Narendhiranv04/rss-ebm-infeasibility`, branch `naren/3d-dataset-relocations`. Fetch the latest remote state. The last reviewed 3D v4 freeze was commit `83c1135f`, but do not assume the branch has not advanced.
2. `final-fixed-methodology-1.pdf` (Finalized Approach B, 5 Nov 2026) as scientific authority; also `Approach_B_Final_Methodology_2026-10-31.pdf`, the implementation guides, and the latest validated reports. Do not treat older specifications as permission to change the latest architecture.
3. `gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v2/production_v4/{Q2_PARITY_SPEC_AND_COVERAGE.md,V4_READINESS_DECISION.json,V4_VALIDATION_REPORT.md,V4_RUNBOOK.md,COVERAGE_REPORT_V4.json,production_policy_v4.TEMPLATE.json}`.
4. `production_v4/frozen/` roster, contexts, manifest, forecast; `production_v3/QC_ELIGIBLE_ROOTS.json`, frozen source pin, and inherited split; `code/{q2roster3d,placement3d,policy3d,collect4,prod4,replay3d}.py`.
5. Discover all **existing** Boltzmann X/Y source code, checkpoints, historical 2D runs, label schemas, and reports in the real workspace/repository. Their location and readiness must be established by inspection, not assumption. Read-only reference to 2D is allowed, but **do not develop/train/run 2D in this kickoff**.

The frozen distinction is mandatory:

- **Placement sampler:** given hypothetical scene `S_hyp` and already-held object `o`, propose destinations `d` with declared support/pose convention. Label `V_place` tests *conditional-on-grasp individual placement*. It does not test pick accessibility, action ordering, full robot state transitions, the terminal reference connector, or original target restoration.
- **X/Y:** for a *complete ordered correction* `r` from the original root, `X_r` is sequential physical executability (with robot state carried forward, all required phases and terminal connector); `Y_s` is original target-task feasibility from pinned `q_ref` in its edited endpoint scene `s`. Distinct orders with identical endpoint scenes can have different X but must share Y.
- The sampler learns destination proposals; X/Y scores and ranks *ordered repair sequences*. Neither should use privileged construction/repair labels at test time. A 3D placement negative is not automatically a complete-X negative; a placement positive is not X=1 or Y=1.
- Do not make unsupported claims of learned causal graphs or fully verified 3D ordered repairs.

**No changes** to the source generator, running collectors, frozen rosters, existing label definitions, scene QC, train/val/test assignments, teacher implementation, production files, or safety settings. Never overwrite real records.

## 1. Host access, ownership and HARD fail-closed resource gate (FIRST)

From the user's authorized SSH environment, inspect `ssh user1@10.4.25.63`. Do not request or print passwords, tokens, private keys, or other credentials. No sudo, drivers, kernel/cgroup modifications, global environment installs, daemon kills, force pushes, or edits to shared system settings.

Collect evidence before choosing a workspace: `hostname`, `whoami`, `uname`, `lscpu`, `free -h`, `df -h`, `lsblk`, `nvidia-smi -L`, full GPU process/VRAM/temperature/utilization reports, `ps`/`top` for other workloads, working CPU affinities, writable user-local storage, and whether the native 3D generator or others' jobs are active. Check how many GPUs are actually present, their models, current users and free memory; **do not assume this server has a particular GPU or that any GPU is available**. Check CUDA/PyTorch compatibility in a temporary user-owned isolated environment only if safe.

Write `reports/01_SERVER_AUDIT.md` + machine-readable `reports/01_SERVER_AUDIT.json` with timestamps and process summaries (avoid confidential information). Explicitly answer:

- Is a suitable NVIDIA GPU present and unused enough to train without degrading other workloads?
- Which physical/logical CPU(s) are genuinely unoccupied, and what *minimal* CPU allowance can we safely take? GPU training cannot use literally zero CPU for launch/data movement. Seek permission for **at most one reserved logical CPU thread** for the training process to start. If none is safely available, **do not train**. Never run CPU physics, IK, motion planning, model training, multiprocessing data-prep workers, or CPU-bound featurization jobs on the occupied host.
- Is host RAM / VRAM / disk headroom sufficient after reserving resources for existing work? Choose a conservative, measured GPU memory budget and record it. Prefer one GPU and one learner at a time.
- Are any of the generator's directories, processes, or user datasets mutable? Treat them as **read-only**.

A **guarded GPU smoke test** is allowed only after the audit passes, on a tiny synthetic GPU tensor or a few snapshot records. Use `CUDA_VISIBLE_DEVICES=<chosen_gpu>`, user-level `taskset`/affinity for a proven spare CPU, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `torch.set_num_threads(1)`, `torch.set_num_interop_threads(1)` where supported, `DataLoader(num_workers=0)`, `nice`, and a conservative VRAM allocation. Never run unrestricted GPU/CPU stress tests.

Implement an independent **training resource watchdog** and test a bounded self-stop. At minimum, check GPU memory and temperatures, one-thread CPU behavior and affinity, total host load, RAM/disk headroom, and competing process changes. Stop **only our training process** on a violation; do not signal other jobs. No GPU training if a sensor or health signal required by the guard is missing. Define conservative thresholds from measured host properties and show them in the config (do not blindly import laptop/gvlab thermal thresholds). Add a `--dry-run` that cannot allocate a GPU or do a training step.

If the host is unsuitable, deliver all code and audit reports and set `GPU_TRAINING_BLOCKED`, giving the exact observed blocker and safe next actions. Do not quietly switch to another host, CPU training or `gvlab`.

## 2. Minimal, isolated and reproducible workspace

Create a separate **user-owned** research workspace, e.g. `~/approachb_3d_learning/` (use an available storage mount only after verifying ownership and free capacity). Keep a minimal, clearly named layout:

```
approachb_3d_learning/
  src/           # compact loaders, encoders, sampler models, train/eval, X/Y adapter, guards
  configs/       # frozen experiment specs, seeds, limits, model settings
  snapshots/     # read-only, content-addressed 3D training data
  runs/          # checkpoints and figures, grouped by experiment ID
  reports/       # audits, tables, metrics, decisions
  tests/         # small, targeted invariants
```

Do **not** spread logic across dozens of files or make huge monolithic source files. Reuse the existing repository and X/Y model if found. Make a dedicated development branch, e.g. `naren/approachb-3d-learning`, from the verified code baseline, with clean provenance, and push **small source/config/report artifacts** only. Do not commit large NPZ snapshots, private paths, secret files or checkpoints to GitHub. Never force push; never mutate the collector branches.

Use a virtual environment or existing compatible user-local environment. Installation must not modify the generator's environment. Before a GPU framework installation, confirm driver/CUDA/GPU compatibility and that wheel downloads/cache will not exhaust disk. Avoid compiling CUDA extensions or doing other CPU-heavy installs on a busy server; if necessary, defer them and report why.

## 3. 3D data inventory, safe transfer and immutable snapshots

**Do not upload all 3D source files to GitHub.** The source generator may already be local on `10.4.25.63`; verify what is present and its hashes. Collection outputs, however, may currently live on `gvlab` and are not automatically part of this server. Transfer only what training needs through authorized `ssh`/`rsync` or an existing verified data mirror, preserving manifests, checksums and provenance. Do not change the collector's output in place. If direct server-to-server SSH is not configured, use an authorized laptop relay; do not alter SSH security settings just to make it work.

Frozen 3D v4 reference scope:
- 1,582 QC-eligible K0–K3 scene roots; 1,466 query-bearing roots;
- **59,972** physical queries: train **42,612**, val **8,752**, test **8,608**;
- **4,616** separate static contrasts, not physical training negatives;
- root, independent prefix1/prefix2, two-edit prefix3 contexts;
- policy `adaptive_v1`: `(4 poses, 500 iters) -> (8 poses, 1500) -> (16 poses, 5000)` with finite 32-pose reference used during prior validation; robot-held placement success under the pinned MuJoCo teacher.

First query, read-only, whether `production_v4/run_q2_parity` is **complete** on `gvlab`. Do not assume from time estimates. If complete, audit the data and verify recorded replay evidence (or safe offline replay performed on a host actually authorized for physics) before marking a full snapshot. If still collecting, **snapshot only fully committed, verified root units** (ledger ↔ JSON ↔ NPZ ↔ hashes), never open or temporary files, never partial roots, and maintain an immutable **train-only development snapshot**. A separate full snapshot may be published later when collection is complete.

A snapshot ID must bind: upstream commit SHA, source scene/root hashes, source QC, split manifest, Q2 roster and context hashes, physical teacher/protocol, policy and stages, exact included root IDs, unit hashes, timestamp, and label summary. Verify the copy byte-for-byte after transfer; set files read-only, and write a SHA256 manifest. Never join a record by list index; join by `root_id`, `qid`, and relevant `witness_id`. Never alter `qid` or split. Do not import v3 smoke/validation records into v4 training. Never use `K` or construction data as an input signal just because it exists for evaluation stratification.

Separate per query:
- `label=1 VERIFIED`, with stored independently verified witness;
- `label=0 NEG_CERTIFIED_GEOMETRY`, within its finite declared scope;
- `label=0 NEG_UNDER_POLICY` with `BOUNDED_SEARCH`, `DETERMINISTIC_PLAN`, etc. **operational**, not universal impossibility;
- `label=None` or `UNLABELED_*`, excluded from binary negative training;
- `static` occupied/out-of-bounds contrasts, a **separate auxiliary stream**, never relabeled as physical failures.

Audit effective counts by root/split/K (report only), shape, height, depth/block, source/destination bands, crowded vs sparse, and negative subtype. Check duplicated scenes/lineages across splits, missing NPZs, ghost witnesses, root hash mismatch, and any attempted test-label peeking. Produce `reports/02_3D_DATASET_AUDIT.md/json`. If current snapshot is too small or imbalanced for a useful generative pilot, clearly state this and still finish the loader/tests; do not fabricate additional physical labels or steal test queries.

## 4. Shared 3D feature encoder and dataset loaders

Build a small, interpretable feature pipeline from allowed structured geometry. **The encoder is learned**, but its inputs are supplied measured values, not hallucinated from images: object identity within the scene, shape (box/cylinder), dimensions/height, cell-centre 3D position, orientation/resting convention if actually provided, source pose, distances, relative object geometry, local occupancy/clutter, support/aperture geometry, and the pinned robot/tool capability descriptors available in the dataset. Handle variable numbers of objects by a permutation-invariant set encoder (simple pooling or small attention), with an object-of-interest token/embedding and scene context. State what is and isn't available; don't invent robot poses or true scene embeddings absent from the source. Avoid protected labels, intended fixes, repair roles, certified K, offline witness trajectories, and post-trial success as generator features.

Normalize continuous inputs using TRAIN statistics only, serialize scalers and encoding vocabularies, and unit-test permutation invariance, scene edit updates, split isolation and deterministic tensor shapes. The 6×6 current shelf supports a **support-constrained upright placement pose/cell**; do not claim arbitrary SE(3) pose generation. Provide a documented mapping from support-local coordinates to 3D destination poses and to the dataset's exact cell label, with validity checks shared by all sampler baselines. Distinguish trainable feature encoder vs the cVAE posterior encoder.

Data loading must not require MuJoCo/IK at training or inference. Prefer pre-verified compact feature tensors cached once in the immutable snapshot and GPU-friendly batches. For large transform work, use tiny chunks and a host utilization guard rather than many CPU workers. Set a deterministic sampling strategy and report any limits of biased Q2 query selection.

## 5. Sampler ablation: IMPLEMENT, TRAIN ON GPU WHEN SAFE, EVALUATE

Implement **both** primary learned sampler candidates with the same frozen training snapshot, scene encoder capacity budget, inference support/legality screen, sampling seeds where applicable, and equal **unique eligible** destination proposal budgets `M`. Begin with a *tiny proof-of-learning* GPU run after host guard passes; then execute a conservatively bounded first meaningful training/validation sweep. Do not claim full training from a tiny smoke or incompletely collected source. Freeze configs before comparing results. Require actual train/val metrics and seed variation rather than attractive samples alone.

**A. cVAE.** Condition on `(S_hyp,o)`; train on verified positive destination poses/cells. Posterior `q_psi(z | S,o,d)` and generator `p_phi(d | z,S,o)` with `z ~ N(0,I)`. Objective:

`L_cVAE = E_q[-log p_phi(d | z,S,o)] + beta_KL KL(q_psi(z | S,o,d) || N(0,I)).`

For the current finite shelf, a masked categorical distribution over legal cells is a sensible first decoder; if you instead generate continuous support poses, document the projection rule and orientation convention. Define reconstruction likelihood, KL weight/schedule, latent dimension, handling of multiple valid destinations, and stop/early-stop rule. The decoder's density is NOT a calibrated feasibility probability.

**B. Conditional flow matching.** Condition on the **same** `(S_hyp,o)` scene representation, learn a velocity field on a declared continuous support-local destination parameterization. For a simple chosen interpolant `x_t=(1-t)x_0 + t x_1`, `u_t=x_1-x_0`, train:

`L_FM = E || v_phi(x_t,t | S,o) - u_t ||^2.`

Specify how a supported 3D destination becomes its continuous coordinate, the source noise distribution, orientation/support treatment, ODE integration steps, and deterministic conversion to the same eligible destination cells/poses. If continuous-to-cell projection causes duplicates or out-of-domain samples, record them and spend the SAME raw/unique proposal budgets in every comparison, reporting both. Do not pretend a Gaussian-interpolated pose is automatically a physically valid intermediate robot motion; this is a **distributional generative interpolation**, not planning.

**C. Nonlearned controls.** Implement or reuse an exact legality-matched uniform/Sobol/stratified sampler. If a swept-volume sampler is not actually finalized/implemented, mark it `NOT_AVAILABLE`, don't invent one. Optionally compare a simple supervised feasibility-ranker trained on declared positive/negative placement trials; keep its scores distinct from the two generators' densities.

**D. Evaluation.** Require a reproducible held-out **validation-only** report first. Only evaluate TEST after configuration, hyperparameters and selected checkpoint are frozen. Under the exact same available labelled query support and unique proposal budget M, report: unique legal proposal rate, duplicate rate, coverage of recorded positives, empirical placement success among destinations with *known independent labels*, class/geometry/height/depth/distance stratification, diversity, repeated-seed variability, GPU inference latency and throughput, memory, and calibration (Brier/ECE) **only if a separately trained score is legitimately calibrated**. Do NOT call every untested destination negative or score a generated unseen destination as physically proven successful. If offline queries are too sparse for fair precision estimates, state the limitation and plan an explicitly separate teacher evaluation later on a safe machine, but do not run a new CPU-intensive planner now.

Construct clear figures: learning curves, sampled destinations overlaid on a few genuine scenes (both successful and failed placements), diversity/coverage vs M, per-stratum results, errors and failure examples. Keep visualizations faithful to real data; no fabricated physics.

Provide an evaluation comparing a frozen feature encoder to a jointly trainable encoder **only if compute permits**, and report a minimal ablation on object shape/height context vs geometry-only to test whether 3D features actually help. Do not increase model capacity until the baseline works.

## 6. Existing X/Y Boltzmann model: AUDIT, REUSE, VALIDATE, DO NOT FAKE LABELS

Find the actual existing model and label/training code. Record exact source path, commit, checkpoints, available root-level X and Y events, missingness, order-contrast evidence, and code/test status. Decide whether the present implementation already matches the latest finalized model, whether it is an older variant, or whether it is missing. No unsupported statement of "existing pretrained 3D X/Y".

The authoritative joint model is **scene-first, root-consistent**:

`P(Y_s=1) = sigmoid(b_s / tau)`

`P(X_r=1 | Y_s=y) = sigmoid((a_r + w_r*y) / tau)`

`P(X_r=1,Y_s=1) = sigmoid(b_s/tau) * sigmoid((a_r+w_r)/tau)`.

`b_s` is the **F3 scene** coefficient for target restoration at the endpoint; `a_r` is the **F2 ordered-prefix** physical executability coefficient; `w_r` is the narrowly defined **F5 quadratic X/Y interaction**. Do not replace this with independent BCE heads, an unnormalized `-aX-bY-wXY` model, or `p(X=1)*p(Y=1)` unless as a labeled ablation. Different ordered sequences reaching the same endpoint **reuse the same Y**, but keep distinct X labels/prefix representations. Use exact observed-data root-averaged marginal NLL for missing X/Y labels, root/scene deduplication, and optional complete-witness robot-joint travel Huber auxiliary `L_B = L_joint + lambda_J*L_J`; do not invent travel values for failures. No-op and score threshold/length/displacement/travel selector remain distinct inference decisions.

**Critical supervised-label gate:** a valid 3D X record must correspond to an **ordered complete physical sequence**, including sequential robot-state continuity and the declared terminal connector; Y must come from a **separate original-target attempt from q_ref in the edited endpoint scene**. Do not infer them from `V_place`, static source construction tags, or K labels. If such 3D X/Y supervision is absent or incomplete, implement the 3D feature/sequence adapter, numerically test normalization and gradients with **clearly labeled synthetic fixtures only**, and write a precise missing-label plan. **Do not launch a misleading real X/Y training run.** If valid 3D X/Y records are already available, audit and train a **tiny safe GPU-only proof-of-learning** under the same resource guard, with held-out roots and baseline checks.

For eventual proper 3D X/Y training/ablation, require (i) coupled model `w_r` learned, (ii) uncoupled `w_r=0`, (iii) direct-success predictor, (iv) order-invariant control, and (v) matched same-endpoint AB/BA contrasts whenever possible. Identify required additional labels without generating them on this training server.

Do not launch full end-to-end 3D repair execution/IK as a hidden dependency of sampler or X/Y training. A learnable model's output is not a verified repair.

## 7. Training execution: staged gates instead of a long uncontrolled run

Execution ladder, with each step persisted and with permission to progress *only when the previous gate passes*:

1. **Static checks and CPU-light metadata inspection:** zero teacher calls, no generator writes, host safe.
2. **Small GPU capability smoke:** torch sees selected GPU and trains 1–3 batches of a tiny synthetic or verified-data network, no CPU training fallback; monitor resources. If this fails, stop training only and report blockers.
3. **Sampler data path smoke:** deterministic `S,o,d` batch, positive labels and split isolation, GPU forward/backward, finite gradients and nonzero parameter updates for BOTH cVAE and FM.
4. **Short actual train/val sampler run:** a small, **pre-budgeted** number of steps/epochs, one model at a time, with reproducible checkpoints and ETA, watchdog active, early stopping and hard walltime limit based on free resources. Ensure no accidental train-on-test; keep candidate budget identical.
5. **Optional longer sampler run:** only if the first measured run shows healthy CPU/GPU behavior, usable learning curves and adequate verified positive training coverage. Fix the budget and checkpoint cadence first.
6. **X/Y audit and adapter validation:** read-only inspection can occur independently. Real X/Y training only if its own labels pass the full-sequence semantic gate and host is safe; otherwise run synthetic mathematical tests only.

If training consumes spare CPU needed by the generator or existing workload, preempt the training job immediately and mark `STOPPED_FOR_RESOURCE_SAFETY`. **Collector/generator work has priority**. Never kill or pause someone else's processes. Keep model training, verification and heavy packaging **off the active `gvlab` collector** and off the laptop's active 2D collector.

Use a project-owned status log, checkpoint manifests and a compact 10-minute status snapshot for steps/rates/losses/VRAM/GPU temperature/CPU/host RAM/ETA. Push only small git-tracked reports on the dedicated learning branch at safe intervals when approved; do not make automatic unbounded checkpoint commits. If a scheduled status service is installed, do it only with permission in user space and independently verify it is active, not merely manually tested. Mirror verified checkpoints to a **confirmed** distinct storage destination; if none exists, report this as a backup gap rather than inventing one.

## 8. Acceptance criteria and exact final handoff

Create one concise top-level `reports/00_READ_ME_FIRST.md` plus:

- `01_SERVER_AUDIT.md/json`: GPU availability, CPU-support allowance, resource thresholds, generator/process protection, go/no-go.
- `02_3D_DATASET_AUDIT.md/json`: exact verified snapshot, roots, query/label/split/shape/height coverage, missingness, hashes and a train-safe loader.
- `03_SAMPLER_IMPLEMENTATION.md`: encoder and cVAE/FM architectures, equations/losses, proposal representation, configs, tests and nonlearned baseline.
- `04_SAMPLER_RESULTS.md/json`: genuine train/val/test policy and any completed GPU runs; curves, fairness, failure cases, ablations and GPU/CPU resource trace. Never report a placeholder as a measurement.
- `05_XY_MODEL_AND_LABEL_AUDIT.md`: existing source path and code status, equations and numerical sanity tests, any authentic 3D sequence labels, missing label requirements and a conditional 3D training go/no-go.
- `06_NEXT_STAGE_DECISION.json`: exact states such as `SAMPLER_GPU_TRAINED_ON_PARTIAL_SNAPSHOT`, `SAMPLER_IMPLEMENTED_GPU_BLOCKED`, `XY_READY_FOR_REAL_3D_TRAINING`, or `XY_BLOCKED_MISSING_SEQUENCE_LABELS`, with evidence paths and unresolved dependencies.
- `07_INTEGRITY_AND_PUSH_AUDIT.md`: tests, source hashes, git branch/commit/push verification, immutable dataset and checkpoint backup status.

The final response to me must give: **(a)** what ran on the new server, **(b)** which GPU and CPU affinity were actually used, **(c)** the exact data snapshot and label counts, **(d)** measured cVAE and flow-matching performance, or explicit proof why training was gated off, **(e)** whether the existing X/Y model and valid 3D X/Y labels were actually found, **(f)** what I can now run next, **(g)** links to pushed evidence/figures/checkpoints (only verified paths), and **(h)** any remaining authorization/resource blocker.

Treat this as the first real 3D learning kickoff, not a claim that both model families are trained or that full 3D Approach B has been proven. **Make usable progress today without causing another server incident.**
