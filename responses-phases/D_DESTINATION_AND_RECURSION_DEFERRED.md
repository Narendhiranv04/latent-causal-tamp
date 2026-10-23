# D — destinations and recursive displacement: deferred (open question only; nothing implemented)

**Status.** Not implemented, by contract (0038 §3.3). D_BLOCKERS_V1 predicts only:
- whether the original target retrieval (with SAFE_RETREAT) is feasible from `q0`;
- which movable objects belong to an inclusion-minimal sufficient clearing set under a frozen hypothetical parking map.

**Open research question.** Given D's blocker distribution `P_D(b | y0 = 0, S)`, can one learn *where* each blocker should go and *in which order*, recursively handling blockers of blockers, so that the physically executed sequence succeeds? This must be done without a planner at inference and without confusing hypothetical parking (a label device) with executable placement. The H7 evidence (edit feasible, physical relocation infeasible) shows these differ.

**Interface contract for a future stage (not code):**
- **Input:** `S0`, robot `q0`, target, goal, D's blocker marginals and joint MAP set, and a candidate destination set per object.
- **Output:** an ordered relocation proposal `[(object, destination)]` with a calibrated success probability.
- **Evaluation:** compared against A / B / C / SF under the same TOP1_COMMIT protocol and teacher.
- **Must declare:**
  - destination generation, with no privileged collision labels;
  - the recursion depth cap;
  - how hypothetical parking labels are kept separate from executable placement labels.
- **Must not:** reuse D's parking map as an executable destination set without new teacher evidence.

3D work is likewise future work and not implemented.
