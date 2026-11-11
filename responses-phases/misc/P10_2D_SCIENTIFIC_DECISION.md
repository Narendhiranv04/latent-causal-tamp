# P10 — 2D scientific decision

**Decision (by the preregistered rule).** The winner is the arm with the highest blind TOP1 success that beats SF after Holm correction, provided one exists.

**Keyed B (ABC9K_KEYED_V1, JOINT-CAUSAL-EBM) is selected as the strongest learned 2D approach.**
- Blind strict TOP1 executed success: B 71.8 % vs SF 38.5 % (Holm p = 8e-6), with C tied at 71.8 %. Tie-break on the next endpoint (H1): B has κ error 0.014 vs C 0.057. Then per-root NLL: B 0.234 vs C 0.269.
- **C is not adopted.** The GRU order encoder shows no benefit over B's predecessor factor.
- **A** is clearly behind on 3-move repairs and complementarity. **SF** is the weakest learned arm.

**What is and is not established:**

| Claim | Status |
|---|---|
| B > SF on executed one-shot repair success (blind, 65 roots) | **Confirmed** (P1, Holm) |
| B > A on H1 complementarity κ (9 blind roots) | **Confirmed** (P2, Holm) |
| C > B on order | **Not supported** (ceiling; no difference) |
| B > SF on omission necessity | **Not supported** (+3 points, ns) |
| Learned B ≥ planner-assisted G+M | **Not supported** (G+M 83 % vs 72 %) |
| Order factor (F2), scene pair (F3), generic coupling (F5) and DINOv2 contribute | Supported by retrained ablations |
| Repair–omission pair (F4) contributes | Not supported |
| Learned edit-vs-executable reasoning (H7) | **Fails** (0 / 4 for every learned arm) |
| Appearance invariance | **Fails** (H9 prediction shift about 0.16) |
| D predicts initial feasibility | **Confirmed on blind** (64 / 64) |
| D's pairwise Boltzmann term helps blocker attribution | **Not supported** (pairless equal or better) |

**Nature of the evidence.** These are intervention-conditional physical effects, measured under certificate-scoped teacher labels: an edit or relocation was made, and the outcome was certified or witnessed. They are not a learned structural causal model and they do not show mechanism transfer beyond these 2D constructor families.

**Recommended next work** (not started):
1. Learned proposal of alternative destinations for H7-type failures.
2. Appearance-randomized training or a vision-invariance objective (H9).
3. B as a re-ranker inside a planner-assisted loop, to close the gap to G+M.
4. D destinations and recursive displacement (deferred by contract).
5. 3D (future, not implemented).
