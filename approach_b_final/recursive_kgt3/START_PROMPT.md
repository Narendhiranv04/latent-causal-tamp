# Starting prompt — Claude Opus 5.5 High

You are the lead research engineer and a skeptical scientific reviewer for my RSS 2027 Latent Causal TAMP project. We are extending an **already frozen, experimentally validated K≤3 Approach B** into the **recursive K>3 method shown in our Fig. 3(a): iterative loop → temporary-target retarget → compose → rank**, then independent physical verification. I want a rigorous **audit-first** implementation, not a quick prototype that happens to work on a few known scenes.

## Workspace and source of truth

Repository: `https://github.com/Narendhiranv04/latent-causal-tamp`  
Dataset branch: `naren/scaling2d-k12-test`, frozen commit `e07354b3c8344954c05e3b5ddf499436d855a550`.  
Completed dataset: `scaling2d_k12/G7/release_v2/` — 23 minimum-K-certified public scenes: K4=5, K5=5, K6=5, K9=5, K12=3. The 2D scenes range up to 28 objects; K9/K12 contain scenes outside the ≤20-object TRAIN support. All 23 certified full witnesses and their prefixes have already passed independent tests. Dataset generation is over; **do not restart it**.

You have a detailed **`plan.md` accompanying this prompt**. Locate and fully read it first; if it is only attached, copy it into a new isolated `approach_b_final/recursive_kgt3/` folder *after checking repository state*. Use it as a proposed research contract to critically evaluate, **not** as an unquestionable specification. If it conflicts with actual code or physical semantics, give evidence and correct the plan before implementation.

The canonical frozen bundle manifest is under `approach_b_final/reports/final_v34/BUNDLE_MANIFEST.json` on `naren/approach-b-v3-4-final-benchmark`. Inspect `approach_b_final/placement.py`, `search.py`, `xy.py`, `construct.py`, `contracts.py`, `exhaustive.py`, and `scaling2d_k12/teacher_long.py` at the pinned commit. Historical retargeting/temporary-target diagnostics are under `approach_b_final/validation_k3/` on `naren/k3-postablation-validation`; the completed ablation study is on `naren/k3-ablation-gvlab2-20261120`. Reuse actual interfaces rather than recreating model code.

## FIRST TASK: critical methodology and code audit — no full implementation yet

1. Establish repo HEAD/branch, local changes, exact available checkpoints, SHA-256 and dataset manifest. **Never overwrite pre-existing changes or training jobs**. Create a new additive development branch only after auditing state. If the frozen checkpoints are unavailable, report a blocker and the exact missing assets; do not retrain substitute models.
2. Trace the entire algorithm in code: public scene → dynamic cVAE features → top-four destination proposals → local K≤3 X/Y hypotheses → local task reassignment → recursive enabling hypotheses → globally legal ordered composition → terminal original-target Y and stagewise X ranking → sealed one-shot decision → long-teacher X/Y physical verification.
3. Explain **how recursion proposes which pending action to repair without a learned blocker identity, a step-level failure model, or teacher feedback**. Give a concrete hand-worked K6 chain and K12 chain using synthetic objects, then demonstrate exactly how the search could discover them. Do not consult the 23 certified witnesses to construct these examples.
4. Audit the deepest mathematical pitfalls:
   - Which code output is the **marginal `px`**, which is conditional X|Y, and which is `p11`? Which belongs in stagewise ranking?
   - How to call the frozen D **Y endpoint head** on an endpoint containing >3 edits **without** passing >3 actions through the frozen X/order head. Preserve the original S0/edit-history representation; do not assume a rebased-root no-op is equivalent.
   - The frozen X label **includes a terminal return to q_ref**, while real full sequences carry the robot state continuously and return to reference only at the end. A product of local X values is a **heuristic energy**, not a physically valid independent success probability.
   - How to avoid multiplying temporary-target Y values into final original-target Y, and how to handle an originally blocked target whose original Y remains false across all proper prefixes.
   - The current placement feature builder has `MAXOBJ['2d']=20`; prove a narrow dynamic-padding fix works on 25–28 objects with weights untouched and historical predictions unchanged.
   - Prevent duplicated objects, self/cyclic dependencies, illegal parking, swapping/goal occupation, and loss of order sensitivity in deduplication.
   - Frozen temporary-target Y calibration is weak and large edited endpoints are out-of-distribution. Explain what can and cannot be claimed scientifically.
5. Derive the actual combinatorial cost, bounded search strategy and realistic worst-case resource budget. Plan model-only batch evaluation and instrumentation. A claim that a full K3 action pool is exhaustively enumerated is unacceptable unless the implemented pool and complexity actually permit it; use an explicit budget and report incomplete search.
6. Review the final evaluation's scientific fairness: comparison to frozen K≤3, a budget-matched nonrecursive longer search, recursive Y-only/X-only/full, and an optional no-retarget control. Do **not** let increasing computation alone masquerade as a recursion contribution.
7. Treat `release_v2/public/` as inference input; **private labels, certified K, witnesses, prior successful sequences, private coverage and GIFs must never influence predictions, ranking, hyperparameter choice or early stopping**. Private data is accessed only by a separate post-seal evaluator. The physical teacher is never called while planning.

## Deliverables from this first pass

Write a **substantive `AUDIT.md`** inside the new `recursive_kgt3` folder with:

- A source-grounded component/interface map (actual functions, paths and likely required adapters).
- Mathematical definitions for local `p11`, stage X, original final Y, composition and decision rule; a clear separation of a neural heuristic from a physically verified result.
- A worked nested K6 and K12 hypothetical example and a search-state/recursion algorithm or pseudocode detailed enough to implement.
- A prioritized risk register containing every conceptual, implementation, data, evaluation and resource flaw; rank blockers as **CRITICAL / MAJOR / MINOR**, with tests and precise fixes.
- A small, minimal file-change plan: which new `.py` files, which existing functions can be reused as-is, and which narrowly scoped compatibility fixes (if any) require parity testing. Do not create an enormous new framework.
- Explicit PASS / CONDITIONAL / BLOCKED gates for P0–P6 in `plan.md`, a no-leakage protocol, and a **predeclared** test/ablation schedule with visualizations after each phase.
- An **adversarial second review**: actively try to falsify the design with counterexamples (e.g., high local X but globally invalid order; same endpoint with different physical order; a correct enabling action never sampled; X qref mismatch; K12 OOD). Record what fails, what can be fixed and what is fundamentally unsupported.
- A concise final **GO / REVISE / BLOCKED** verdict and an exact actionable implementation order, including commands for any small **read-only or mock-only** checks you actually performed.

You may revise `plan.md` if the audit warrants it, but retain a section titled **`Amendments and why`** so the original design decisions are traceable. Do not call something “validated” without test logs/results. Report failures, partial findings and unknowns explicitly.

## Stop conditions and execution discipline

**Stop after this audit and return its findings, amended `plan.md`, and the GO/NO-GO decision to me.** Do not launch full dataset physics, run TEST evaluations, alter existing models, start servers or GPU campaigns, or push to a remote repository. No new dataset generation or model training is authorized. Light code inspection, dependency checks, isolated unit tests and synthetic mock demonstrations are allowed, but must not read TEST private witnesses or labels. Do not touch parallel CF/NULL experiments or other active worktrees.

When the audit passes and I authorize the implementation phase, work through P0–P6 one phase at a time with clear tests, a visual artifact after each stage, and a gate report before advancing. **The scientific goal is not simply to get a K12 success; it is to determine rigorously what the frozen K≤3 models can and cannot do when recursively composed.**
