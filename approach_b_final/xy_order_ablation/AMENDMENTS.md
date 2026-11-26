# Amendments (append-only)

1. **2026-11-26, P0:** the 2D strict mapping also treats `Q_REF_NOT_CLEAR_IN_EDITED_SCENE` and `TERMINAL_STATE_NOT_CLEAR` as decided negatives, because `bxy_teacher.py` labels both `negative_kind: CERTIFIED`. This differs from the CR study's list, which never encountered these statuses on its cohort. Decided before any new query.
