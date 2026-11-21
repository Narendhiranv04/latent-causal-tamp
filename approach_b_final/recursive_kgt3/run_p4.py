#!/usr/bin/env python3
"""P4 planner-side runner (no labels, no teacher): one arm of p4_config.json over a public DEV file; saves per-scene trace INCLUDING the
full scored candidate pool (needed to separate 'never generated' from 'generated but mis-ranked'); resumable; helper sharding; SEAL.
    python run_p4.py ARM DEV_PUBLIC OUT_DIR [--device cuda] [--shard i/n --reverse --no-seal]"""
import argparse, hashlib, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as DA  # noqa: E402
import models as MD  # noqa: E402
import planner as PLN  # noqa: E402
import planner_r as PR  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(arm, dev_public, out, device, shard=None, reverse=False, no_seal=False):
    out = Path(out); (out / "traces").mkdir(parents=True, exist_ok=True)
    C = json.loads((HERE / "p4_config.json").read_text())
    spec = C["arms"][arm]
    rows = DA.jl(dev_public)
    code_sha = {f: sha(HERE / f) for f in ("data.py", "models.py", "planner.py", "planner_r.py", "run_p4.py")}
    M = MD.Frozen(device) if spec["models"] == "frozen" else MD.Random(device)
    DA.install_guard([HERE, HERE.parent, out, Path(sys.executable).resolve().parents[1]])
    order = list(enumerate(rows))
    if shard:
        i_, n_ = map(int, shard.split("/")); order = [(k, r) for k, r in order if k % n_ == i_]
    if reverse:
        order = order[::-1]
    for _, row in order:
        tf = out / "traces" / f"{row['root_id']}.json"
        if tf.exists():
            continue
        c0 = dict(M.c)
        log = {"local": [], "ytask": [], "insert": [], "rounds": [], "seeds": []}
        P = (PLN.Planner if spec["planner"] == "R0" else PR.PlannerR)(row, M, spec["mode"], spec["cfg"], log)
        res = P.run()
        res["model_calls"] = {k: M.c.get(k, 0) - c0.get(k, 0) for k in M.c}
        cands = [{"seq": json.loads(k), **v} for k, v in P.cands.items() if v is not None]
        tf.write_text(json.dumps({"res": res, "log": log, "cands": cands}))
        print(json.dumps({k: res[k] for k in ("root_id", "decision", "stop", "n_candidates", "rounds")} | {"len": len(res["seq"]), "budget": res["budget"]}), flush=True)
    if no_seal or not all((out / "traces" / f"{r['root_id']}.json").exists() for r in rows):
        return
    preds = [json.loads((out / "traces" / f"{r['root_id']}.json").read_text())["res"] for r in rows]
    with open(out / "predictions.jsonl", "w") as f:
        for p in preds:
            f.write(json.dumps({k: v for k, v in p.items() if k != "cfg"}) + "\n")
    seal = {"arm": arm, "utc": time.strftime("%FT%TZ", time.gmtime()), "predictions_sha256": sha(out / "predictions.jsonl"),
            "p4_config_sha256": sha(HERE / "p4_config.json"), "code_sha256": code_sha, "teacher_calls": 0, "labels_read": False}
    (out / "SEAL.json").write_text(json.dumps(seal, indent=1))
    print(json.dumps({"sealed": seal["predictions_sha256"][:16], "n": len(preds)}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("arm"); ap.add_argument("dev_public"); ap.add_argument("out"); ap.add_argument("--device", default="cuda")
    ap.add_argument("--shard"); ap.add_argument("--reverse", action="store_true"); ap.add_argument("--no-seal", action="store_true")
    a = ap.parse_args(); main(a.arm, a.dev_public, a.out, a.device, a.shard, a.reverse, a.no_seal)
