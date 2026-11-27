# FIG3_KGT3 — final decision

**Branch:** `naren/rss27-fig3-retarget-home`, from `7c948deef0`; not merged.

| Commit | Content |
|---|---|
| `f11230eb2d` | Pre-registration + P0 |
| `15e0076b5d` | P2 builders + 2D manifest |
| `303eb69649` | P1 |
| `2a6b6ff49a`, `f00758b094`, `5479d8df1c` | P2 manifests and expansions |
| `1f4577ba94` | P2 results |
| this commit | P4 accounting and final reports |

**Production.** The released K ≤ 3 bundle, sampler, Y pathway, X/Y factorization and teacher contracts are unchanged. Every scaling checkpoint is separate. No TEST or release_v2 access occurred. All evidence is development evidence.

## Outcome by stage

| Stage | 2D | 3D |
|---|---|---|
| P0 audit | PASS: no privileged input; planners read only public scene/task fields; no physical module callable; metadata- and relabel-invariant | same |
| P1 composition audit | F0 chunk AUROC on the archived certified panel 0.46 (h0 0.37); witness-order rank quantile 0.82 | F0 0.33, G1s 0.21, M1s 0.17 |
| P2 fresh multi-action gate | **DATA_LIMITED**: 6 discordant GATE families. The teacher returned UNKNOWN on 644/1,032 runs; screen-live orders verified 32 times vs 324 UNKNOWN. | **DATA_LIMITED**: 9 mixed h ≥ 1 g2–3 families. The selected trained model also fails AUROC (0.63 [0.45, 0.79]) and paired gain (+0.045 n.s.). Concordance passes (0.73). |
| P3 order recovery given the assignment | NOT RUN (gate) | NOT RUN (gate) |
| P4 planners | implemented, tested, model-only accounting | same |
| P5 discovery and fresh confirmation | NOT RUN | NOT RUN |

## Answers (required questions)

1. **No-oracle audit.** Passed in both domains: runtime field tracking, physical import guard, metadata and relabel invariance, full-grid legal masks, `_NoGeo` zeros.
   - Caveats: canonical index tie-breaks are disclosed, and witness order is weakly anti-correlated with ID order (τ −0.16 / −0.13).
   - The displacement tie-break remains only in the production floor (`rank.b0`, unchanged).
2. **Actual conditioning.**
   - The released sampler is a TaskCVAE with **task_on = True**: goal, target, query-relative offsets and q_ref context, rule S1, M = 4.
   - The scorer is XYNet arm D (vis_dim 0, GEO features zeroed). The 3D scaling heads add query-relative geometry only.
3. **Multi-action intermediate learning.** **Not established in either domain.**
   - 3D: the query-relative heads prefer enabler-first orders (G1s concordance 0.77) but do not rank multi-action chunks at reached states (AUROC ≤ 0.69 for every arm). Targeted training (O1 / O2) improved likelihood and calibration only. O2 showed no established benefit, and no GNN-vs-MLP claim is possible.
   - 2D: not testable (data-limited); F0 is anti-concordant on TRAIN (0.15).
4. **Physical order recovery with the assignment given.** Not run (gate). No new evidence beyond the archived 2D 3/30 and 3D 2/20 learned orders.
5. **Deployable Fig. 3A / Fig. 3B outcomes without assignments.** None physically evaluated. Model-only, both planners produce long multi-chunk plans within budget; no plan is verified.
6. **Full exact enumeration.**
   - 3D GA was EXACT on 14/20 DEV roots (≤ 110 s) and BOUNDED on 6.
   - 2D GA was BOUNDED on 30/30, because the dense scenes exceed the declared envelope.
   - Exactness refers to the learned energy over the declared proposal pool only.
7. **Effect of multi-action ordering and boundary assumptions.**
   - The parameter-free objective with has_multi changes plans relative to the historical λ: 8–9 of 20 3D roots for F0 and G1s, 3/30 in 2D.
   - Without has_multi, F0's 3D optimum is all-singleton on 7/20 roots.
   - The physical effect is untested.
8. **Unresolved:**
   - **2D teacher decidability** in dense chain scenes: most feasible-looking orders are UNKNOWN_PLANNER, which blocks both supervision and evaluation.
   - **3D intermediate-state support:** only 1-step reached prefixes, no g = 3 at h ≥ 1, and GATE short by one family.
   - **Initial proposal coverage:** the witness assignment is in the initial D4 pool on 0/30 2D and 2/20 3D DEV roots. This binds Fig. 3B before retention or X; Y-only retention is no longer the first bottleneck.
   - **Multi-action X ranking** at reached states, even where supported.
9. **Manuscript-ready:**
   - the leakage and provenance audit;
   - the exact grouped-DP formulation and its tested equivalence and complexity;
   - the negative data result that the 2D teacher cannot decide most orders in dense certified scenes;
   - 3D probe-constructed enabler chains reproduce physically (47/48 discordant at h0);
   - query-relative 3D X heads prefer enabler-first orders descriptively but fail the multi-action AUROC gate.

   **Not manuscript-ready:** any claim of K > 3 discovery, order recovery, architectural superiority (3A vs 3B, GNN vs MLP, O2 vs O1) or generalization.
10. **Resources, exposures and deviations.** See `FIG3_KGT3_LEDGER.json`.

| Item | Used | Cap |
|---|---|---|
| 2D | 1,032 queries / 7.8 CPU-h | 1,200 / 20 |
| 3D | 1,040 queries (515 probes + 525 runs) / 3.5 CPU-h | 1,200 / 20 |
| GPU | about 0.4 GPU-h in total | – |
| Workers | ≤ 16 | 16 |

   **New exposures:**
   - 3D VAL_GATE_NEW was opened once and is no longer fresh;
   - 2D VAL_GATE_NEW was never read by a model;
   - the quarantined A2 outcomes were opened DIAGNOSTIC_ONLY.

   **Deviations (disclosed):**
   - The 3D construction dispatcher bug (families skipped on in-flight reservations) was fixed and resumed after 14 families. Completed constructions were kept and the deterministic order was preserved.
   - The stage-A selection rule was ambiguous (lowest NLL vs must-qualify). It was resolved by choosing among qualifying runs; only O2 s0 qualified.
   - Stage B and the 2D MLP challenger were not triggered.
   - First-relocation FPR is not estimable on the P2 GATE panel.

## Stop

Stopped at the P2 gate in both domains, as pre-registered. No R4, protected evaluation, production change, further training or architecture work was done.

**The next step needs separate approval.** The binding problems are teacher decidability (2D), reached intermediate-state coverage (3D) and initial proposal coverage (both). The cheapest information gain is likely:
1. a 2D teacher-budget audit on the screen-live UNKNOWN orders;
2. teacher-verified 3D chains with h ≥ 2 and g = 3 prefixes on new families, with a new sealed gate.
