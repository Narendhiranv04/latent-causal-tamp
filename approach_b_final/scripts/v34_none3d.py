"""V3.4 3D NONE slots: one attempt = the frozen dense NONE construction + certificate + teacher (run_shelf66_none.work, store OUT/dense) ->
the frozen trim of that dense root (trim_none66 = NONE_TRIM66_V1 or trim_none66_v3 = V3, the version the slot's reference root used;
env V34_TRIM_MAP = JSON {global slot ordinal: "V1"|"V3"}) labelled from scratch (NONE gate none_cert66_v4).  Counted only if CONFIRMED NONE.
Run in the 3D code dir (cwd = .../code, shelf66_v3 on sys.path), like run_shelf66_full."""
import importlib, json, os
from pathlib import Path

_MAP = {}


def work(job):
    name, wave, slot, spec, out = job
    import bd_core as bc
    import run_shelf66_none as N
    if not _MAP:
        _MAP.update(json.loads(Path(os.environ["V34_TRIM_MAP"]).read_text()))
    dense = str(Path(out) / "dense")
    e = N.work((name, wave, slot, spec, dense))
    bc.Store(dense).append(e)
    base = {"spec": spec, "v34_dense_root_id": e.get("root_id"), "v34_dense_observed": e.get("observed"), "v34_dense_wall_s": e.get("wall_s")}
    if not e.get("accepted") or str(e.get("observed")) != "NONE":
        return {**base, "accepted": False, "root_id": e.get("root_id"), "reason": "DENSE:" + str(e.get("reason") or e.get("observed"))[:200],
                "wall_s": e.get("wall_s", 0)}
    ver = _MAP[str(wave)]
    T = importlib.import_module("trim_none66" if ver == "V1" else "trim_none66_v3")
    t = T.work((e, dense, out))
    return {**t, **base, "v34_trim_version": ver, "wall_s": t.get("wall_s", 0) + e.get("wall_s", 0)}
