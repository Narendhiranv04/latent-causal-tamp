"""V3.4 3D NONE slots: one attempt = the frozen dense NONE construction + certificate + teacher (run_shelf66_none.work, store OUT/dense) ->
the production trim cascade on that dense root: trim_none66 (NONE_TRIM66_V1) first, and only if it does not confirm NONE, trim_none66_v3
(the production run applied V1 to every dense root, then V2 (0 confirmed) and V3 to the V1 failures; V2 is skipped: it never confirmed one).
Each trimmed scene is labelled from scratch (NONE gate none_cert66_v4).  Counted only if CONFIRMED NONE.
Run in the 3D code dir (cwd = .../code, shelf66_v3 on sys.path), like run_shelf66_full."""
import importlib, json, os
from pathlib import Path

_MAP = {}


def work(job):
    name, wave, slot, spec, out = job
    import bd_core as bc
    import run_shelf66_none as N
    dense = str(Path(out) / "dense")
    e = N.work((name, wave, slot, spec, dense))
    bc.Store(dense).append(e)
    base = {"spec": spec, "v34_dense_root_id": e.get("root_id"), "v34_dense_observed": e.get("observed"), "v34_dense_wall_s": e.get("wall_s")}
    if not e.get("accepted") or str(e.get("observed")) != "NONE":
        return {**base, "accepted": False, "root_id": e.get("root_id"), "reason": "DENSE:" + str(e.get("reason") or e.get("observed"))[:200],
                "wall_s": e.get("wall_s", 0)}
    w, tried = e.get("wall_s", 0), []
    for ver, mod in (("V1", "trim_none66"), ("V3", "trim_none66_v3")):
        t = importlib.import_module(mod).work((e, dense, out))
        w += t.get("wall_s", 0)
        tried.append({"version": ver, "root_id": t.get("root_id"), "accepted": t.get("accepted"), "observed": t.get("observed"), "reason": str(t.get("reason"))[:120]})
        if t.get("accepted") and str(t.get("observed")) == "NONE":
            break
    return {**t, **base, "v34_trim_version": ver, "v34_trim_tried": tried, "wall_s": w}
