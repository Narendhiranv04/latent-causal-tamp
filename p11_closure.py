"""P11: 2D scientific closure. Ledger (runs/p11/guards, contract caps), read-only source-to-result audit (P11-0), collision-free H9
two-palette evaluation (P11-1), F1 / J / ablation component identification (P11-2), short-trained physical execution (P11-3), D versus
A/B/C comparison (P11-5). Every P10 artifact is read-only; P11 outputs are new files under runs/p11/. No teacher / IK / planner call
in any learned path (instrumented); physical episodes only for one committed choice."""
from __future__ import annotations

import collections
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

import config as cf

OUT = Path("runs/p11")
CAPS = {"audit_eval": 4000.0, "f1_training": 6000.0, "short_episodes": 5000.0, "newcon_dev": 1200.0, "newholdout_teacher": 8000.0,
        "newholdout_exec": 5000.0, "regression": 1700.0}
JOB = {"cpu_s": 3000.0, "wall_s": 9000.0}


def _rd(p):
    return json.loads(Path(p).read_text())


def spent(cat=None) -> tuple:
    gs = [_rd(p) for p in (OUT / "guards").glob("*.json")]
    gs = [g for g in gs if cat is None or g["category"] == cat]
    return sum(g["cpu_s"] for g in gs), sum(g["wall_s"] for g in gs)


def job(name, call, cpu, module="p11_closure", category="audit_eval", wall=None) -> dict:
    """Process-tree guarded job, ONE process per job, charged to one P11 category; refuses to start past the category cap."""
    import teacher
    (OUT / "guards").mkdir(parents=True, exist_ok=True)
    left = CAPS[category] - spent(category)[0]
    cpu = min(cpu, JOB["cpu_s"], left)
    if cpu < 5:
        raise SystemExit(f"{category} budget exhausted")
    g = teacher.guard([sys.executable, "-c", f"import torch; torch.set_num_threads(1); import {module}; {module}.{call}"], cpu,
                      wall or JOB["wall_s"], OUT / f"heartbeat_{name}.txt", 15.0, 0.25, Path("."))
    n = 1
    while (OUT / "guards" / f"{name}{'' if n == 1 else f'_attempt{n}'}.json").exists():
        n += 1
    rec = {k: g[k] for k in ("stop", "returncode", "cpu_s", "wall_s", "overshoot_s", "stderr_tail")} | \
          {"cpu_cap_s": cpu, "call": f"{module}.{call}", "category": category, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    cf.write_json(OUT / "guards" / f"{name}{'' if n == 1 else f'_attempt{n}'}.json", rec)
    (OUT / f"heartbeat_{name}.txt").unlink(missing_ok=True)
    print(json.dumps({k: rec[k] for k in ("stop", "returncode", "cpu_s", "wall_s")} | {category: round(spent(category)[0], 1)}))
    return rec


def sha(p) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()


def boot(d, n=2000, seed=0):
    if len(d) < 2:
        return [None, None]
    rng, a = np.random.default_rng(seed), np.asarray(d, float)
    ms = [a[rng.integers(0, len(a), len(a))].mean() for _ in range(n)]
    return [float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))]


def sign_p(d):
    from scipy.stats import binomtest
    n, k = sum(x != 0 for x in d), sum(x > 0 for x in d)
    return float(binomtest(k, n).pvalue) if n else 1.0


def paired(per, a, b):
    ks = sorted(set(per.get(a, {})) & set(per.get(b, {})))
    d = [per[a][k] - per[b][k] for k in ks]
    return {"roots": len(d), "mean": float(np.mean(d)) if d else None, "ci95": boot(d), "sign_p": sign_p(d),
            "a_better": sum(x > 0 for x in d), "b_better": sum(x < 0 for x in d)}


def holm(ps: dict) -> dict:
    out, run = {}, 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out[k] = {"p": ps[k], "holm_p": run, "reject_0.05": run < 0.05}
    return out


# ------------------------------------------------------------------ P11-0: read-only source-to-result audit
def audit() -> None:
    import subprocess
    import torch
    import p10b_dataset as pd
    import p10c_train_eval as pc
    import p10d_execute as px
    sh = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()  # noqa: E731
    A = {"head": sh("rev-parse", "HEAD"), "origin": sh("rev-parse", "origin/main"), "tracked_changes": sh("status", "--short", "--untracked-files=no").splitlines()}
    man = _rd("runs/p10b/SPLIT_MANIFEST.json")
    roots = man["roots"]
    A["split_counts"] = dict(collections.Counter(v["split"] for v in roots.values()))
    A["split_manifest_hash_ok"] = cf.stable_hash({k: v for k, v in man.items() if k != "hash"}) == man["hash"]
    A["sealed_files_unchanged"] = all(sha(f) == h for f, h in man["sealed_file_sha256"].items())
    P = px.plans()
    A["blind_constructor_versions"] = {f"{a}|{b}": n for (a, b), n in collections.Counter((P[k]["family"], P[k]["construction"].split(" + ")[-1][:40]) for k in P if P[k]["split"] == "blind" and P[k]["family"] == "H3").items()}
    A["h3_v1_roots_by_split"] = dict(collections.Counter(P[k]["split"] for k in P if P[k]["family"] == "H3" and "V1.1" not in P[k]["construction"]))
    tv = torch.load("runs/p10c/dataset_trainval.pt", weights_only=False)["roots"]
    A["trainval_sources"] = {f"{a}|{b}": n for (a, b), n in collections.Counter((r["audit"]["split"], r["audit"]["source"].split(":")[0]) for r in tv).items()}
    bl = torch.load("runs/p10c/dataset_blind.pt", weights_only=False)["roots"]
    A["blind_records"] = {"n": len(bl), "labels_present": sum(c["privileged"]["y"] is not None for r in bl for c in r["candidates"]),
                          "disjoint_from_trainval": not ({r["audit"]["root"] for r in bl} & {r["audit"]["root"] for r in tv})}
    ck = {}
    for f in sorted(Path("runs/p10c/runs").glob("*.json")):
        x = _rd(f)
        ck[x["name"]] = sha(f"runs/p10c/ckpt/{x['name']}.pt").removeprefix("sha256:") == x["checkpoint_sha256"].removeprefix("sha256:")
    A["checkpoints"] = {"n": len(ck), "all_hash_ok": all(ck.values())}
    snap = _rd("runs/p10d/predictions.json")
    A["snapshot_hash_ok"] = cf.stable_hash({k: v for k, v in snap.items() if k != "hash"}) == snap["hash"]
    A["snapshot_commit_before_unseal"] = int(sh("log", "-1", "--format=%ct", "162338ea47478bb96acf80c96360e4cd85972f89")) < int(sh("log", "-1", "--format=%ct", "--", "runs/p10b/UNSEALED"))
    # H9 key collision check
    h9 = torch.load("runs/p10c/dataset_h9.pt", weights_only=False)["roots"]
    keys = collections.Counter(r["audit"]["root"] for r in h9)
    a0 = next(a for a in snap["arms"].values() if a["regime"] == "full")
    A["h9"] = {"records": len(h9), "distinct_keys": len(keys), "max_records_per_key": max(keys.values()),
               "snapshot_h9_entries_per_run": len(a0["roots"].get("h9", {})), "overwrite_confirmed": len(a0["roots"].get("h9", {})) < len(h9)}
    # episodes: 975 choices -> 255 deterministic episodes; every choice mapped; committed sequence equals the choice
    jobs = _rd("runs/p10d/episode_jobs.json")
    led = {}
    for f in Path("runs/p10d/episodes").glob("*/ledger.json"):
        led |= {k: (v, f.parent / k) for k, v in _rd(f)["episodes"].items()}
    seqs = {c["query"]: c["sequence"] for r in P.values() for c in r["items"] if c["kind"] == "ORDERED_TEACHER"}
    bad, abst, n_choice = [], 0, 0
    for key, arms in jobs["arms"].items():
        root, ch = key.split("::", 1)
        n_choice += len(arms)
        if ch in ("ABSTAIN", "NOT_RUN"):
            abst += len(arms)
            continue
        j = next(j for j in jobs["jobs"] if j["root"] == root and j["choice"] == ch)
        e, d = led.get(f"{j['arm']}__{root}", (None, None))
        if e is None:
            bad.append((key, "missing episode"))
        elif not (d / "result.json").exists():
            if e.get("outcome") != "UNRESOLVED_CENSORED":
                bad.append((key, f"no result.json but outcome {e.get('outcome')}"))
        elif ch != "GM":
            res = _rd(d / "result.json")
            if [list(map(list, x)) for x in [res["committed_sequence"] or []]][0] not in ([], [list(a) for a in seqs[ch]]) and res["committed_sequence"] is not None:
                bad.append((key, "committed sequence differs"))
    A["episodes"] = {"distinct": len(jobs["jobs"]), "choices": n_choice, "abstain_choices": abst, "mapping_errors": bad[:10], "n_errors": len(bad),
                     "jobs_hash_ok": cf.stable_hash(jobs["jobs"]) == jobs["hash"], "outcomes": dict(collections.Counter(v[0].get("outcome") for v in led.values()))}
    # recompute P1 contrasts + Holm independently from per-root success
    p1 = _rd("runs/p10d/P1_TOP1.json")
    succ = p1["per_root"]
    re = {f"{a}-{b}": paired(succ, a, b) for a, b in (("K-B", "SF"), ("K-B", "A"), ("K-C", "K-B"), ("K-B", "G+M"), ("K-B", "geometry"))}
    A["p1_recomputed"] = {k: {x: v[x] for x in ("mean", "ci95", "sign_p", "roots")} for k, v in re.items()}
    A["p1_matches_report"] = all(abs(re[k]["mean"] - p1["contrasts"][k]["mean"]) < 1e-12 and abs(re[k]["sign_p"] - p1["contrasts"][k]["sign_p"]) < 1e-12 for k in re)
    be = _rd("runs/p10d/BLIND_EVAL.json")
    ps = {"P1": re["K-B-SF"]["sign_p"], "P2": paired(be["per_root"]["H1"], "K-B", "A")["sign_p"],
          "P3": paired(be["per_root"]["order"], "K-C", "K-B")["sign_p"], "P4": paired(be["per_root"]["omission"], "K-B", "SF")["sign_p"]}
    A["holm_recomputed"] = holm(ps)
    A["holm_matches_report"] = all(abs(A["holm_recomputed"][k]["holm_p"] - v["holm_p"]) < 1e-12 for k, v in zip(("P1", "P2", "P3", "P4"), p1["holm"].values()))
    # recompute the blind evaluation into a NEW file and compare with the committed one
    import p10e_report as rr
    (OUT / "audit").mkdir(parents=True, exist_ok=True)
    rr.blind_eval("blind", str(OUT / "audit" / "BLIND_EVAL_recomputed.json"))
    nb = _rd(OUT / "audit" / "BLIND_EVAL_recomputed.json")
    A["blind_eval_recompute_identical"] = cf.stable_hash({k: v for k, v in nb.items() if k != "split"}) == cf.stable_hash({k: v for k, v in be.items() if k != "split"})
    A["status_counts_blind"] = be["status_counts"]
    A["regression_p10e"] = {k: _rd("runs/p10b/regression/regression_result.json")[k] for k in ("tests", "replays", "verdict")}
    A["ledger"] = {c: round(pd.spent(c)[0], 1) for c in pd.CAPS} | {"true_training_cpu_s": round(sum(_rd(f)["train_cpu_s"] for f in Path("runs/p10c/runs").glob("*.json")) +
                                                                                              sum(_rd(f)["train_cpu_s"] for f in Path("runs/p10c_prelim/runs").glob("*.json")), 1)}
    A["inference_cost_unit"] = "process CPU seconds per root (time.process_time), single thread"
    (OUT / "audit").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "audit" / "P11_0_AUDIT.json", A)
