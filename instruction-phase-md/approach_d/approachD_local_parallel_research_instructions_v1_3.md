# Local workstation track — Approach A/B/C/D comparison + Approach D G2c-lite

**Purpose.** While the separate server builds the new balanced 2D and xArm7 3D datasets, use the **existing, already-labelled 2D P13–P17 data** on the local computer to (i) make the A/B/C/D comparison clear and reproducible and (ii) improve Approach D's precompiled-motion system just enough to demonstrate and evaluate its components. **Do not wait for the new dataset. Do not regenerate the legacy dataset.** This is not a request for exhaustive formal proofs or a wholesale rewrite.

**Repository:** local `Narendhiranv04/latent-causal-tamp`, work on `approach-d-v1`. Latest *reported* local HEAD: `43fd985` (G2b). Verify locally. Important references: `responses-phases/0102_AD_G2b_SOLVER_FREE_PROVIDER_AND_SEQUENTIAL_REARRANGEMENT.md`, `responses-phases/0098_P17_D2_Retrospective_48_and_Prospective_D_Evaluation.md`, `responses-phases/0094_P17_B1_Labels_Training_Matched_Retraining_and_Controls.md`, `p17_d.py`, `p17_b.py`, `d_blockers.py`, `ad_compile.py`, `ad_runtime.py`, `ad_provider.py`, and existing `PoC-takeaway` visualizations in the `naren/PoC` branch of `rss-ebm-infeasibility` (reference only, if available).

## 1. Scientific story to establish

1. **Why this is needed.** T may be infeasible in the original arrangement even when its start and goal are valid. Correcting it may require zero to four relevant relocations; other nearby objects may be irrelevant or moving them may hurt.
2. **What is learned.** A/B/C use their existing energy/sequence architectures and labels; D is a conditional Boltzmann model for **original-target** feasibility and intervention-grounded blocker participation. Report each actual historical model variant by its exact name: P17 uses retrained A, lean B (`LB`), historical `P13:K-C`, and `Dp17` for the matched comparison. Do not represent those as four newly trained matched architectures.
3. **What is not learned.** D does not learn destination selection, obstacle ordering, IK, trajectories, or swept volumes. Geometry proposes relocations; an offline-compiled library provides absolute robot motions; inference only retrieves, collision-checks, updates hypothetical states, and queries D for **the same T**.
4. **What the evidence does—and does not—show.** Distinguish D's original-target classification / blocker diagnosis from D's effect on **search success**. The historic P17 report says Dp17-norec and geometry-norec each solve 71/90, so learned search superiority is *not established*. Better catalog coverage is a motion-library contribution, not proof of better causal learning.
5. **Physical scope.** Geometric certification of stored 2D paths is not actual hardware/simulator execution. A finite-library failure does not imply universal physical impossibility.

Make these five claims understandable through short explanations, formulas only where useful, and a few authentic scenes/trajectories. No elaborate new theory needed.

## 2. Keep the two ongoing tracks separate

| Local workstation — do now | Dataset server — separate ongoing work |
|---|---|
| Reuse historical P16/P17 roots, labels, checkpoints and executed comparisons | Create systematically balanced new 2D and xArm7 3D scenes, counterfactuals, B/D supervision |
| Present A/B/C/D against honest common historical baselines | Verify new intended K0–K4 mechanisms and distractor variants |
| Improve a small offline motion catalog; run limited solver-free DEV demonstrations | Expand toward the larger dataset only after its own pilot gates |
| Prepare compatibility with future 7-action protocol | Define and freeze that protocol for new data |

**Do not SSH to the server, modify its files, copy partial datasets, run 3D MuJoCo jobs locally, or let server work block this task.** Avoid local data contamination with new unfinished scene collections.

## 3. Work package L1 — Reproduce and explain the existing A/B/C/D evidence (highest priority)

**First use archived outputs; do not rerun the expensive historical teachers merely to make figures.** Inspect exact scripts, snapshots and reports and independently regenerate summary numbers from saved result records.

Use the same historical P17 90-root D-roster for the existing matched operational comparison. The archived report gives **27 operationally feasible, 63 operationally infeasible** roots; reported *resolved among 63*: A 26, B 29, C 22, D 43, geometry search 40. It also reports D's original-target AUROC around 0.952, and **Dp17-norec = geometry-norec = 71/90** for their matched search comparison. Treat these as *values to verify from files*, not hardcoded results to manufacture.

Provide:
- One compact, transparent A/B/C/D panel showing each method's actual model/decision interface, what is predicted, and how its candidate is verified. Distinguish learned classifier threshold from non-empty sequence selection; methods have different detection definitions.
- One matched *archived* outcome comparison: blockage detection, false alarms, verified repaired tasks, unnecessary moves, and number of relocations where available. Always give denominators and the old operational-label convention. Do not silently turn historical `UNKNOWN` into the new binary teacher protocol.
- One D-vs-geometry panel isolating **learned guidance** under the same historic search and physics budgets, including the null result. Include a fair no-learning baseline.
- A small and honestly chosen set of authentic scenes: directly feasible clutter; one-blocker repair; multiple-blocker candidate; irrelevant/needless move; an alternative-relocation or ordering failure; and a motion-catalog failure. Omit a category if it has no valid saved example; do not fabricate.
- Explain in plain language what each visualization proves and one limitation per approach. Reuse existing scene and GIF rendering utilities wherever possible.

**Crucial:** Existing P17 A/B/C/D comparison used historical solver-based execution. The newer `AD_PRECOMPILED` runtime is a *different* backend. Never mix those results into one bar chart as if physically identical. Use clearly labelled panels: `Historical P17 — archived shared evaluation` and `New precompiled backend — limited DEV pilot`.

## 4. Work package L2 — G2c-lite: close the most obvious motion-library gaps, offline only

Start with the measured G2b problems, not an indiscriminate expansion:

- G2b demonstrated one A→B→T sequence from **stored actions only**, but 1/12 was a development-informed demonstration, and exact+relative tiers alone solved 0/12 chains. The successful F12 root (`p13_2026216000`) is **not a proven K2**: archived P16 verifies `o00→59` followed by T, a one-relocation solution.
- Target-T motion diversity is the dominant gap (in five of seven analyzed fixtures, no stored target motion clears). Compile a *small*, diverse selection of **original-target** side-grasp/approach/branch templates **offline** for development roots. Favor modes that change access through clutter, rather than adding many nearly identical paths.
- Add a *small* number of actual precompiled post-retreat→next-approach connectors **offline** where the current home-route is the blockage. Do not generate all pairwise connections across the graph.
- Keep exact source/destination witnesses, relative-family compiled candidates, and generic offline templates distinguishable in provenance. Relative 3×3/4×4 similarity is a hypothesis, **not yet proven better than geometry-only or random ranking**; compare at equal stored-candidate budgets.
- A stored action is valid only if the current-scene full trajectory and robot start/end continuity pass the existing collision and consistency check. Never translate a swept volume or call runtime IK/RRT/grasp planning.
- Use a *small, fixed development set*, preferably existing G2b fixtures plus a few additional predeclared DEV roots. Avoid redesigned success cases in the prospective success-rate denominator. Report dev-informed demonstrations separately.

**Resource scope:** A small, bounded local pilot only; benchmark actual cost before setting a reasonable cap, record attempted compiles and time, and stop well before any full-board build. No 442-query held-out benchmark, no extensive retraining, and no large new dataset construction. You may stop with an honest limited result if target coverage remains low.

## 5. Work package L3 — Connect D's diagnosis to the solver-free backend, only if L2 supports it

- Implement the *smallest* adapter necessary to call the existing frozen D model at each hypothetical scene state for **original target `t0` and original goal only**. Existing `Dp17-norec` already does target-only re-querying; avoid rebranding it as new.
- For every candidate repair: D ranks likely blockers; **non-learned** geometry proposes destination options; precompiled trajectories and connectors are physically checked; D is re-queried after the hypothetical move; a final **stored target T action** must pass independent replay.
- Compare D-guided vs geometry-only vs uniform ordering on **exactly the same DEV roots, finite catalog, candidate slots, checking budgets, and search limits**. If D guidance has no advantage, report it plainly; the scientific result is still useful.
- Do **not** retrain A/B/C/D in this local work; do not add `L_updated`, destination/order losses, or temporary-target D(A)/D(B) queries. For eventual D training, continue feasibility BCE + scoped blocker Boltzmann NLL only. The new server dataset will provide any future expanded training evidence.
- If historical A/B/C predictions can be mapped to the same finite-catalog candidate sequences without changing their meaning, include a clearly marked **exploratory common-backend comparison**. If not, retain the honest historical P17 A/B/C/D comparison and explain why a common-backend comparison awaits new data. **Do not force it.**

## 6. Fair evaluation and data integrity

- Existing P17: preserve historical decision rules, 0–4 relocation search, old label/status protocol, seeds, configs and archived reports. Use saved results wherever possible.
- New *future* dataset: at most **7 pick/place actions**, conventionally up to 6 obstacle movements plus T, with constructed scenes designed for 0–4 necessary relocations and up to two redundant moves. **Do not retrospectively convert the P17 4-relocation experiments into 7-action experiments.**
- New label protocol: binary per completed offline teacher query (`1` verified; `0` otherwise including exhausted teacher budget), retaining failure reason as metadata. Historical labels remain untouched. No unsupported claim that budget-negative means impossible.
- Separate three sources of failure: (i) D or sequence choice, (ii) unavailable/blocked stored motion or connector, (iii) teacher-defined task infeasibility. Catalog-specific "necessary" is not globally necessary.
- Treat sequences with needless relocations as task-successful **if T is eventually moved validly**; measure repair length and excess relocations separately. For B, ordered-sequence labels are the relevant evidence. For D, blocker masks require defensible counterfactual supervision; do not label every nearby object a blocker.
- Use existing frozen/test outputs only for retrospective **reporting**, not to tune G2c. Keep the G1 442-query held-out set sealed; only development roots guide code/config choices.
- A useful component demonstration beats exhaustive significance tests for this session. Give honest sample sizes and avoid claims of superiority from 1–2 rescues.

## 7. Minimal engineering, visuals, and deliverables

Avoid new frameworks, sprawling subdirectories or duplicated simulation modules. Prefer reusing `p17_*`, `ad_*`, `PoC-takeaway` renderers, and existing saved artifacts. Keep changes opt-in in `approach_d.toml`; never edit `config.toml` or historical labels/checkpoints/replays.

**Deliverables in the local repo:**

1. `responses-phases/0103_AD_LOCAL_COMPARISON_AND_G2C_LITE.md` — a readable research report (~3–6 pages in Markdown): problem, roles of A/B/C/D, evidence from archived P17, G2b bottleneck, any G2c-lite improvement, matched baselines, conclusion, limitations, next step after server dataset. Clearly separate archived facts from new tests.
2. `visualizations/approach_d/local_comparison/` — preferably 4–6 useful PNGs/GIFs: method overview, verified A/B/C/D outcomes, D-vs-geometry, real illustrative scene(s), precompiled A→B→T chain, and target/connector coverage before/after if changed.
3. Small optional additions to `ad_*` modules, tests, and an opt-in config for the limited local pilot. If no engineering changes are scientifically worthwhile, visuals + analysis may be enough.
4. One concise `LOCAL_WORK_TRACK_STATUS.md` with reproducing commands, actual paths, run status, verified test/replay counts and how this track joins the server dataset later.

**Completion criteria:** (a) archived comparisons reproducible and visually understandable; (b) G2b limitations presented accurately; (c) any new solver-free improvements tested on non-cherry-picked development examples; (d) real D-guidance-vs-geometry comparison attempted only when both have the same usable finite catalog; (e) no inference-time IK/planning; (f) historical experiments unchanged. Explain each component with **what it does, why it's included, and what specific evidence supports it**. A sound *negative* result is acceptable.

Work on the current local branch, commit coherent tested work locally, do not push/merge without permission. No contact with the server is necessary. Stop after this local track and provide a next-step recommendation, not a huge speculative implementation roadmap.
