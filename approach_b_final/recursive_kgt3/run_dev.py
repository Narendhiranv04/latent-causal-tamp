#!/usr/bin/env python3
"""Planner-side DEV run (no labels, no teacher): one arm over dev_public.jsonl; label-free probes (D1/D3 at S0); per-root traces; SEAL.
The leakage guard (A11) is installed after imports/model loading: from then on only the out dir and the code/venv may be opened.
    python run_dev.py ARM DEV_PUBLIC OUT_DIR [--device cuda]"""
import argparse, hashlib, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as DA  # noqa: E402
import models as MD  # noqa: E402
import planner as PLN  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def probes(row, M):
    """Label-free S0 probes (outside the search budget): best K1 p11 per mover (original task) and ŷ(A -> top-1 proposal of A)."""
    h = DA.HypoRoot(row)
    D = M.propose(h)
    k1 = [[(o, d)] for o, v in D.items() for d in v]
    sc = M.score(h, k1)
    best = {}
    for s, r in zip(k1, sc):
        best[s[0][0]] = max(best.get(s[0][0], -1.0), r["p11"])
    yt = {}
    for o, v in D.items():
        if v:
            yt[str(o)] = {"d": v[0], "y": M.ytask(DA.HypoRoot(row, (), (o, v[0])))}
    return {"k1_best": {str(o): b for o, b in best.items()}, "ytask_s0": yt, "proposals_s0": {str(o): v for o, v in D.items()}}


def main(arm, dev_public, out, device):
    out = Path(out); (out / "traces").mkdir(parents=True, exist_ok=True)
    cfg_all = json.loads((HERE / "dev_config.json").read_text())
    assert sha(dev_public) == cfg_all["dev_public_sha256"], "dev_public changed after pre-registration"
    rows = DA.jl(dev_public)
    M = MD.Frozen(device) if cfg_all["models"][arm] == "frozen" else MD.Random(device)
    DA.install_guard([HERE, HERE.parent, out, Path(sys.executable).resolve().parents[1]])
    preds = []
    for row in rows:
        c0 = dict(M.c)
        pr = probes(row, M) if arm != "RAND" else None
        log = {"local": [], "ytask": [], "insert": [], "rounds": []}
        res = PLN.Planner(row, M, arm, cfg_all[arm], log).run()
        res["model_calls"] = {k: M.c.get(k, 0) - c0.get(k, 0) for k in M.c}
        (out / "traces" / f"{row['root_id']}.json").write_text(json.dumps({"res": res, "log": log, "probe": pr}))
        preds.append(res)
        print(json.dumps({k: res[k] for k in ("root_id", "decision", "stop", "n_candidates", "rounds")} | {"len": len(res["seq"]), "budget": res["budget"]}), flush=True)
    with open(out / "predictions.jsonl", "w") as f:
        for p in preds:
            f.write(json.dumps({k: v for k, v in p.items() if k != "cfg"}) + "\n")
    seal = {"arm": arm, "utc": time.strftime("%FT%TZ", time.gmtime()), "predictions_sha256": sha(out / "predictions.jsonl"),
            "traces_sha256": hashlib.sha256(b"".join(sha(p).encode() for p in sorted((out / "traces").glob("*.json")))).hexdigest(),
            "dev_config_sha256": sha(HERE / "dev_config.json"), "code_sha256": {f: sha(HERE / f) for f in ("data.py", "models.py", "planner.py", "run_dev.py")},
            "teacher_calls": 0, "labels_read": False}
    (out / "SEAL.json").write_text(json.dumps(seal, indent=1))
    print(json.dumps({"sealed": seal["predictions_sha256"][:16], "n": len(preds)}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("arm"); ap.add_argument("dev_public"); ap.add_argument("out"); ap.add_argument("--device", default="cuda")
    a = ap.parse_args(); main(a.arm, a.dev_public, a.out, a.device)
