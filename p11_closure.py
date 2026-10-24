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


# ------------------------------------------------------------------ P11-1: H9 with collision-free (root, palette) keys (evaluation only)
def h9_variants():
    """[(compound key, base root, palette, prepared root)] for every H9 record; asserts 2 distinct palettes per base root."""
    import p10c_train_eval as pc
    rs = pc.prepared("h9")
    out = [(f"{r['key']}#{r['audit']['palette']}", r["key"], r["audit"]["palette"], r) for r in rs]
    keys = [k for k, *_ in out]
    if len(set(keys)) != len(keys):
        raise ValueError("H9 compound keys collide")
    per = collections.Counter(b for _, b, _, _ in out)
    if set(per.values()) != {2}:
        raise ValueError(f"expected exactly two palettes per root, got {collections.Counter(per.values())}")
    return out


def h9_integrity() -> dict:
    """Non-visual inputs bit-identical to the original record; visual features differ between original, P1 and P2."""
    import torch
    orig = {r["audit"]["root"]: r for n in ("trainval", "blind") for r in torch.load(f"runs/p10c/dataset_{n}.pt", weights_only=False)["roots"]}
    h9 = torch.load("runs/p10c/dataset_h9.pt", weights_only=False)["roots"]
    bad_geom, same_vis, qid = 0, 0, 0
    vis = collections.defaultdict(dict)
    for r in h9:
        o = orig[r["audit"]["root"]]
        bad_geom += any(not np.array_equal(np.asarray(r["inputs"][k]), np.asarray(o["inputs"][k])) for k in r["inputs"] if k != "visual")
        qid += [c["privileged"]["query"] for c in r["candidates"]] != [c["privileged"]["query"] for c in o["candidates"]]
        same_vis += np.allclose(r["inputs"]["visual"], o["inputs"]["visual"])
        vis[r["audit"]["root"]][r["audit"]["palette"]] = np.asarray(r["inputs"]["visual"])
    p12 = sum(np.allclose(v["P1"], v["P2"]) for v in vis.values())
    return {"records": len(h9), "roots": len(vis), "nonvisual_input_mismatch": int(bad_geom), "query_id_mismatch": int(qid),
            "visual_identical_to_original": int(same_vis), "P1_identical_to_P2": int(p12),
            "mask_rule": "p10c_train_eval._recolor colours pixels by the SAME instance mask of the recorded observation (instance > 0 -> object RGB, "
                         "== 0 -> support RGB); masks, ids and geometry are not modified; no label or certificate is read"}


def h9_eval() -> None:
    import contextlib
    import p10_eval as pe
    import p10_protocol as pp
    import p10c_train_eval as pc
    import unique_factor_keyed as ufk
    snap = _rd("runs/p10d/predictions.json")
    integ = h9_integrity()
    if integ["nonvisual_input_mismatch"] or integ["query_id_mismatch"] or integ["P1_identical_to_P2"] or integ["visual_identical_to_original"]:
        raise SystemExit(f"H9 integrity FAILED: {integ}")
    V = h9_variants()
    split = {b: ("blind" if b in snap["arms"][next(iter(snap["arms"]))]["roots"]["blind"] else "validation") for _, b, _, _ in V}
    calls, out = pp.instrument(), {}
    for n, a in snap["arms"].items():
        if a["regime"] != "full":
            continue
        m, x = pc.load(n)
        keyed = pc.ARMS[a["arm"]][2]
        rows = {}
        for ck, base, pal, r in V:
            if a["arm"] == "B-V0":
                import copy
                r = pc._v0([copy.deepcopy(r)])[0]
            with ufk.installed() if keyed else contextlib.nullcontext():
                pm = pe.marginals(m, r, a["arm"] not in ("A", "SF"))
            sel = pp.top1(m, r, a["tau"], a["threshold"], frozenset(), keyed)["choice"]
            o = a["roots"][split[base]][base]
            vetoed_o = o["top1"]
            dp = [abs(pm[q] - p) for q, p in o["marginals"].items() if q in pm]
            cross = [(pm[q] >= 0.5) != (p >= 0.5) for q, p in o["marginals"].items() if q in pm]
            rows[ck] = {"base": base, "palette": pal, "split": split[base], "mean_abs_dp": float(np.mean(dp)), "max_abs_dp": float(np.max(dp)),
                        "crossing_frac": float(np.mean(cross)), "top1": sel, "top1_original": vetoed_o, "top1_changed": sel != vetoed_o, "marginals": pm}
        out[n] = {"arm": a["arm"], "seed": a["seed"], "rows": rows}
    if sum(calls.values()):
        raise RuntimeError(f"physical calls in H9 evaluation: {dict(calls)}")
    (OUT / "h9").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "h9" / "h9_predictions.json", {"integrity": integ, "runs": out, "snapshot": snap["hash"], "physical_calls": dict(calls)})


def h9_report() -> None:
    """Per-root appearance robustness (seed mean per root; palettes separately and averaged); before / after the overwrite fix."""
    import p10d_execute as px
    import p10e_report as rr
    d, snap, P = _rd(OUT / "h9" / "h9_predictions.json"), _rd("runs/p10d/predictions.json"), px.plans()
    tok = {k: {c["token"]: c["query"] for c in P[k]["items"]} for k in P}
    res = {"integrity": d["integrity"], "static_veto": "no H9 base root has a vetoed candidate, so TOP1 recomputation without the veto set equals "
                                                         "the deployed rule", "by_arm": {}}
    for arm in ("K-B", "K-C", "A", "SF", "B-V0", "B-F2", "B-F3", "B-F4", "B-F5s", "B-F5q", "B-U"):
        runs = [r for r in d["runs"].values() if r["arm"] == arm]
        if not runs:
            continue
        acc = collections.defaultdict(lambda: collections.defaultdict(list))
        for r in runs:
            orig = next(a for a in snap["arms"].values() if a["arm"] == arm and a["seed"] == r["seed"] and a["regime"] == "full")
            for ck, x in r["rows"].items():
                b, pal = x["base"], x["palette"]
                for m in ("mean_abs_dp", "crossing_frac", "top1_changed"):
                    acc[(m, pal)][b].append(float(x[m]))
                    acc[(m, "both")][b].append(float(x[m]))
                fam = P[b]["family"]
                om = orig["roots"][x["split"]][b]["marginals"]
                if fam == "H1":
                    t = tok[b]
                    k_ = lambda mm: mm[t["edit:A+B"]] - mm[t["edit:A"]] - mm[t["edit:B"]] + mm[t[""]]  # noqa: E731
                    acc[("kappa_abs_change", "both")][b].append(abs(k_(x["marginals"]) - k_(om)))
                for a_, b_ in rr.ORDER_PAIRS.get(fam, []):
                    qa, qb = tok[b].get(a_), tok[b].get(b_)
                    if qa in om and qb in om:
                        acc[("order_flip", "both")][b].append(float((x["marginals"][qa] > x["marginals"][qb]) != (om[qa] > om[qb])))
        out = {}
        for (m, pal), per in acc.items():
            v = {b: float(np.mean(s)) for b, s in per.items()}
            bl = [x for b, x in v.items() if P[b]["split"] == "blind"]
            out[f"{m}|{pal}"] = {"roots": len(v), "mean": float(np.mean(list(v.values()))), "ci95": boot(list(v.values())),
                                 "blind_mean": float(np.mean(bl)) if bl else None, "blind_roots": len(bl)}
        res["by_arm"][arm] = out
    old = _rd("runs/p10d/BLIND_EVAL.json")["H9_mean_abs_change"]
    res["before_after"] = {a: {"P10e_reported (blind, P2 only, query-pooled)": old.get(a), "corrected blind both palettes (per-root)": res["by_arm"][a]["mean_abs_dp|both"]["blind_mean"],
                               "corrected blind P1": res["by_arm"][a]["mean_abs_dp|P1"]["blind_mean"], "corrected blind P2": res["by_arm"][a]["mean_abs_dp|P2"]["blind_mean"]}
                           for a in res["by_arm"] if a in old}
    cf.write_json(OUT / "h9" / "H9_RESULTS.json", res)


def h9_figure() -> None:
    import p10_eval as pe  # noqa: F401
    import p6_viz as pv
    import geometry as ge
    from scene import scene_from_dict
    import data
    import learn_data as ld
    import p10c_train_eval as pc
    import p10d_execute as px
    from viz import plt
    dst = Path("visualizations/p11")
    dst.mkdir(parents=True, exist_ok=True)
    res, d, P = _rd(OUT / "h9" / "H9_RESULTS.json"), _rd(OUT / "h9" / "h9_predictions.json"), px.plans()
    cfg = cf.load_config("config.toml")
    b = next(k for k in P if P[k]["split"] == "blind" and P[k]["family"] == "H1")
    s = scene_from_dict(P[b]["scene"])
    q = data.make_query(cfg, b, s, "t0", P[b]["goal_cell"], {}, "SAFE_RETREAT", data.PROTOCOL_V2)
    a = data.appearance_anchor(q, ld.IMAGE_PX)
    run = next(r for r in d["runs"].values() if r["arm"] == "K-B" and r["seed"] == 0)
    f, ax = plt.subplots(1, 4, figsize=(20, 5))
    ax[0].imshow(a["rgb"])
    ax[0].set_title(f"{b}\noriginal observation (same geometry in all panels)", fontsize=9)
    for i, (name, pal) in enumerate(pc.PALETTES.items(), 1):
        rgb = a["rgb"].copy()
        rgb[a["instance"] > 0], rgb[a["instance"] == 0] = pal
        x = run["rows"][f"{b}#{name}"]
        ax[i].imshow(rgb)
        ax[i].set_title(f"palette {name}\nK-B s0: mean |dp| {x['mean_abs_dp']:.3f}; TOP1 changed: {x['top1_changed']}", fontsize=9)
    for x in ax[:3]:
        x.axis("off")
    arms = [k for k in ("K-B", "K-C", "A", "SF", "B-V0") if k in res["by_arm"]]
    for j, pal in enumerate(("P1", "P2")):
        v = [res["by_arm"][k][f"mean_abs_dp|{pal}"] for k in arms]
        ax[3].errorbar([i + (j - 0.5) * 0.25 for i in range(len(arms))], [x["mean"] for x in v],
                       yerr=[[x["mean"] - (x["ci95"][0] or x["mean"]) for x in v], [(x["ci95"][1] or x["mean"]) - x["mean"] for x in v]],
                       fmt="o", capsize=3, label=f"palette {pal}", color=["#2a6fdb", "#e07b00"][j])
    ax[3].set(xticks=range(len(arms)), xticklabels=arms, ylabel="per-root mean |p_variant - p_original|", title="H9 (100 roots, both palettes; root CI)")
    ax[3].legend(fontsize=8)
    pv.png(f, dst / "P11_H9_two_palettes.png", "P11-1: same geometry, two palettes (instance masks unchanged); per-root prediction shift per arm and palette")
