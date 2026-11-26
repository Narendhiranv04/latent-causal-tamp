# Amendments (append-only)

1. **2026-11-26, P0:** the 2D strict mapping also treats `Q_REF_NOT_CLEAR_IN_EDITED_SCENE` and `TERMINAL_STATE_NOT_CLEAR` as decided negatives, because `bxy_teacher.py` labels both `negative_kind: CERTIFIED`. This differs from the CR study's list, which never encountered these statuses on its cohort. Decided before any new query.
2. **2026-11-26, P4:** an analysis bug briefly added the secondary Y − X contrast to the Holm family. It was fixed to the four preregistered contrasts (2D / 3D × J − X, J − Y) before any report; no verdict changed.
3. **2026-11-26:** `stats.py` was added to the plan's file list. The optional archived order-invariant G arm was not run: the matched checkpoint is on gvlab2, and the laptop copies are older, unmatched fits.
