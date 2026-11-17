"""V3.4 CONV1 slots (2D refs that were conversions of ROUTE2D_V1 roots): one attempt = a NEW V1 raw root of the slot's template (frozen
run_2d_plus.v1 / bd_2d_plus.v1 in their own source dir, subprocess) -> the frozen all-movable conversion bd_2d_convert.work (current code +
bd_2d_cover_table.json, this process).  Env V34_V1_DIR = the V1 code dir (bd_2d_plus.py / run_2d_plus.py = the .v1 snapshots), V34_V1_PY.
Returns the conversion's ledger entry (+ v1 fields); a V1 reject / no immovable structure is a failed attempt."""
import json, os, subprocess, sys
from pathlib import Path


def work(job):
    name, wave, slot, spec, out = job
    v1dir, py = os.environ["V34_V1_DIR"], os.environ.get("V34_V1_PY", sys.executable)
    v1out = str(Path(out) / "v1")
    code = ("import json,sys,run_2d_plus as R;e=R.work((sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),json.loads(sys.argv[4]),sys.argv[5]));"
            "R.bc.Store(sys.argv[5]).append(e);print('V34E'+json.dumps(e))")
    env = {**os.environ, "PYTHONPATH": f"{v1dir}/dataset-bd:{v1dir}:{v1dir}/latent-causal-tamp"}
    p = subprocess.run([py, "-c", code, name, str(wave), str(slot), json.dumps(spec), v1out], cwd=f"{v1dir}/latent-causal-tamp", env=env,
                       capture_output=True, text=True)
    line = next((l for l in p.stdout.splitlines() if l.startswith("V34E")), None)
    v1 = json.loads(line[4:]) if line else {"accepted": False, "reason": "ERROR:v1_subprocess:" + p.stderr[-300:]}
    base = {"spec": spec, "v34_v1_root_id": v1.get("root_id"), "v34_v1_observed": v1.get("observed"), "v34_v1_wall_s": v1.get("wall_s")}
    if not v1.get("accepted"):
        return {**base, "accepted": False, "reason": "V1:" + str(v1.get("reason"))[:200], "root_id": v1.get("root_id"), "wall_s": v1.get("wall_s", 0)}
    import bd_2d_convert as C
    if str(v1.get("observed")) not in C.QUOTA_CLASSES:                 # production converts counted-class roots only (bd_2d_convert.todo)
        return {**base, "accepted": False, "reason": f"V1_NOT_COUNTED:{v1.get('observed')}", "root_id": v1["root_id"], "wall_s": v1.get("wall_s", 0)}
    rec = json.load(open(f"{v1out}/roots/{v1['root_id']}.json"))
    if not rec.get("fixed_ids"):
        return {**base, "accepted": False, "reason": "V1_NO_IMMOVABLE_STRUCTURE (no conversion)", "root_id": v1["root_id"], "wall_s": v1.get("wall_s", 0)}
    e = C.work((v1["root_id"], v1out, out, spec))
    return {**e, **base, "wall_s": e.get("wall_s", 0) + v1.get("wall_s", 0)}
