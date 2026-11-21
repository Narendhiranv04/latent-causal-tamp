#!/usr/bin/env python3
"""Experiment C3: temporary-target feasibility (engineering diagnostic; never training data, never a benchmark label).
TASK ADAPTER TT_ADAPTER_V1 (separately versioned; the frozen teachers are called unchanged on an ADAPTED raw record): the teachers hard-code
the target id 't0', so a temporary task (target A, goal d_A) is written as a new raw record in which the physical object A carries id 't0'
(kind 'target' in 2D) and the physical original target carries A's old id (kind 'obstacle', role 'temporary_obstacle'); goal := d_A; every
other field the teachers read (scene, legal cells, q0, fixed ids, robot) is unchanged.  root_id gets a '~TT~A~d' tag (own caches / witnesses).
Learner side: retarget.retarget (every task-specific input updated).  Oracle labels never enter model inputs or proposal selection.
Examples (VAL, sha order): a verified X=1/Y=1 sequence of length >= 2; A = its LAST moved object, d_A = its destination, P = the preceding
verified relocations.  Proposals: frozen TaskCVAE top-4 under the temporary-task context, under the ORIGINAL task context, and NoTask, for
the movers of P and the 2 movable objects nearest A.
    python ttarget.py build DOM N      -> examples, adapted records, jobs + QUERY manifest (before any teacher call), parity jobs
    python ttarget.py teach DOM W      unchanged benchmark.teach into $K3V/runs/ttarget_cache
    python ttarget.py analyze DOM      -> $K3V/runs/out/ttarget/TT_DOM.json"""
import copy, hashlib, json, os, subprocess, sys, time

import numpy as np
import torch

import vk
import retarget as RT
import cvae_probe as CP
import search as S  # noqa: E402
import contracts as CT  # noqa: E402

OUT = vk.OUT / "ttarget"
CACHE = vk.K3V / "runs/ttarget_cache"
ADAPTER = "TT_ADAPTER_V1"


def adapt(raw, dom, A_id, goal_cell, tag=True):
    """raw record -> temporary-task raw record (A_id becomes 't0'; the original target takes A_id).  A_id == 't0' and the original goal
    returns an identical record (identity)."""
    r = copy.deepcopy(raw)
    goal_cell = int(goal_cell)
    if dom == "2d":
        if A_id != "t0":
            for o in r["scene"]["objects"]:
                if o["id"] == A_id:
                    o["id"], o["kind"] = "t0", "target"
                elif o["id"] == "t0":
                    o["id"], o["kind"] = A_id, "obstacle"
            r["roles"] = {(A_id if k == A_id else k): v for k, v in r["roles"].items() if k != A_id}
            r["roles"][A_id] = "temporary_obstacle"
            assert A_id not in r["fixed_ids"]
        r["goal_cell"] = goal_cell
    else:
        if A_id != "t0":
            for o in r["objects"]:
                if o["id"] == A_id:
                    o["id"] = "t0"
                elif o["id"] == "t0":
                    o["id"] = A_id
            ic = r["initial_cells"]
            ic["t0"], ic[A_id] = ic[A_id], ic["t0"]
            r["roles"] = {k: v for k, v in r.get("roles", {}).items() if k != A_id}
            r["roles"][A_id] = "temporary_obstacle"
        r["goal"] = [goal_cell // 6, goal_cell % 6]
    if tag and (A_id != "t0" or goal_cell != (raw["goal_cell"] if dom == "2d" else raw["goal"][0] * 6 + raw["goal"][1])):
        r["ids"] = {**r["ids"], "root_id": f"{raw['ids']['root_id']}~TT~{A_id}~{goal_cell}"}
        if dom == "2d":
            r["scene"]["root_id"] = r["ids"]["root_id"]
    r["tt_adapter"] = {"version": ADAPTER, "A": A_id, "goal_cell": goal_cell, "source_root": raw["ids"]["root_id"]}
    return r


def new_ids(ids, A, tid):
    return ["t0" if i == A else (ids[A] if i == tid else x) for i, x in enumerate(ids)]


def build(dom, n, mode="last"):
    sfx = "" if mode == "last" else "_b"
    import placement as PL
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "roots").mkdir(exist_ok=True)
    assert not (OUT / f"QUERY_{dom}{sfx}.json").exists(), "query list already registered"
    priv = {e["root_id"]: e for e in vk.jl(vk.K3A / "runs/public" / f"private_val_{dom}.jsonl")}
    R = sorted(vk.rows(dom, "val"), key=lambda r: hashlib.sha256(("tt|" + r["root_id"]).encode()).hexdigest())
    sc = json.loads((vk.BUNDLE / dom / "scalers.json").read_text())
    mu, sd = np.array(sc["mean"], np.float32), np.array(sc["std"], np.float32)
    cv = {"task": CP.load_cvae(vk.BUNDLE / dom / "sampler.pt"), "notask": CP.load_cvae(vk.K3A / "runs/training/notask_cvae" / dom / "scratch_all_notask_s0" / "model.pt")}
    ex, jobs = [], []
    for r in R:
        if len(ex) >= n:
            break
        inp = r["inputs"]
        Y = {CT.ekey(y["edit"]): y["y"] for y in r["labels"]["Y"]}
        succ = sorted((q["seq"] for q in r["labels"]["X"] if q["x"] == 1 and Y.get(CT.ekey(q["seq"])) == 1 and len(q["seq"]) >= 2), key=json.dumps)
        if not succ:
            continue
        seq = [(int(o), int(d)) for o, d in succ[0]]
        A, dA = seq[-1]
        P = seq[:-1]
        if mode == "blocked":       # C3b: an ordering of a Y = 1 endpoint whose FIRST relocation (A -> d_A) failed in S0, with a verified ordering
            blk = sorted((q["seq"] for q in r["labels"]["X"] if q["x"] == 0 and q.get("x_phase") == "relocation:0" and len(q["seq"]) >= 2
                          and Y.get(CT.ekey(q["seq"])) == 1), key=json.dumps)
            good = {CT.ekey(s): s for s in succ}
            blk = [b for b in blk if CT.ekey(b) in good]
            if not blk:
                continue
            A, dA = int(blk[0][0][0]), int(blk[0][0][1])
            seq = [(int(o), int(d)) for o, d in good[CT.ekey(blk[0])]]
            P = seq[:[o for o, _ in seq].index(A)]                          # the verified moves made before A in the successful ordering
            if not P:
                continue
        e = priv[r["root_id"]]
        raw = json.loads(open(e["path"]).read())
        ids = inp["ids"]
        inpT = RT.retarget(inp, dom, A, dA)
        rowT = {**r, "inputs": inpT}
        rootT, root0 = S.Root(rowT, dom), S.Root(r, dom)
        cxy = {int(c): np.array(v) for c, v in inp["cell_xy"].items()}
        others = sorted((o for o in rootT.movable if o not in {x for x, _ in P}), key=lambda o: (np.linalg.norm(cxy[inp["cells0"][o]] - cxy[inp["cells0"][A]]), o))[:2]
        objs = sorted({x for x, _ in P} | set(others))
        objs = [o for o in objs if o in rootT.movable]
        props = {}
        for name, m, ctx_inp in (("tt_task", cv["task"], inpT), ("orig_task", cv["task"], inp), ("notask", cv["notask"], inpT)):
            D = CP.dists(m, mu, sd, rootT, rootT.cells0, objs, ctx_inp, 0)
            legal = set(rootT.legal_dests(rootT.cells0))                      # the temporary task's legal destinations (d_A excluded)
            props[name] = {o: [int(c) for c in np.argsort(-D[o], kind="stable") if D[o][c] > 0 and int(c) in legal][:4] for o in objs}
        single = sorted({(o, d) for v in props.values() for o, ds in v.items() for d in ds})
        nid = new_ids(ids, A, inp["tid"])
        rawT = adapt(raw, dom, ids[A], dA)
        pT = OUT / "roots" / f"{hashlib.sha256(rawT['ids']['root_id'].encode()).hexdigest()[:16]}.json"
        pT.write_text(json.dumps(rawT))
        seqsT = [[]] + ([[[nid[o], d] for o, d in P]] if P else []) + [[[nid[o], d]] for o, d in single]
        jobs.append({"root_id": rawT["ids"]["root_id"], "dom": dom.upper(), "path": str(pT), "geom": e.get("geom", "original"), "seqs": seqsT, "ids": nid})
        o1, d1 = seq[0]                                                        # semantic check: Y_tt(S0; A=o1, goal=d1) vs X_orig([(o1, d1)])
        rawF = adapt(raw, dom, ids[o1], d1)
        pF = OUT / "roots" / f"{hashlib.sha256(rawF['ids']['root_id'].encode()).hexdigest()[:16]}.json"
        pF.write_text(json.dumps(rawF))
        jobs.append({"root_id": rawF["ids"]["root_id"], "dom": dom.upper(), "path": str(pF), "geom": e.get("geom", "original"), "seqs": [[]], "ids": new_ids(ids, o1, inp["tid"])})
        full = [[ids[o], d] for o, d in seq]                                   # identity parity: the verified sequence on the UNCHANGED record
        jobs.append({"root_id": r["root_id"], "dom": dom.upper(), "path": e["path"], "geom": e.get("geom", "original"), "seqs": [[[ids[o1], d1]], full], "ids": ids})
        rawR = copy.deepcopy(raw)                                              # RNG-key noise floor: same task, only the root id tag changes
        rawR["ids"] = {**raw["ids"], "root_id": raw["ids"]["root_id"] + "~RL"}
        if dom == "2d":
            rawR["scene"]["root_id"] = rawR["ids"]["root_id"]
        pR = OUT / "roots" / f"{hashlib.sha256(rawR['ids']['root_id'].encode()).hexdigest()[:16]}.json"
        pR.write_text(json.dumps(rawR))
        jobs.append({"root_id": rawR["ids"]["root_id"], "dom": dom.upper(), "path": str(pR), "geom": e.get("geom", "original"), "seqs": [full], "ids": ids})
        rawI = adapt(raw, dom, "t0", inp["goal_cell"])                         # identity parity (same root id): must reproduce the ablation cache
        assert {k: v for k, v in rawI.items() if k != "tt_adapter"} == raw
        ex.append({"root_id": r["root_id"], "K": r["K_legacy"], "A": A, "A_id": ids[A], "dA": dA, "P": P, "o1": o1, "d1": d1, "objs": objs, "props": props,
                   "single": single, "seq": seq, "tt_root": rawT["ids"]["root_id"], "first_root": rawF["ids"]["root_id"], "nid": nid})
    with open(OUT / f"jobs_{dom}{sfx}.jsonl", "w") as f:
        for j in jobs:
            f.write(json.dumps(j) + "\n")
    vk.wjson(OUT / f"EXAMPLES_{dom}{sfx}.json", ex)
    man = {"adapter": ADAPTER, "dom": dom, "examples": len(ex), "jobs": len(jobs), "queries": sum(len(j["seqs"]) for j in jobs),
           "jobs_sha256": vk.sha(OUT / f"jobs_{dom}{sfx}.jsonl"), "examples_sha256": vk.sha(OUT / f"EXAMPLES_{dom}{sfx}.json"), "utc": time.strftime("%FT%TZ", time.gmtime())}
    vk.wjson(OUT / f"QUERY_{dom}{sfx}.json", man)
    print(json.dumps(man))


def teach(dom, W, sfx=""):
    man = json.loads((OUT / f"QUERY_{dom}{sfx}.json").read_text())
    assert vk.sha(OUT / f"jobs_{dom}{sfx}.jsonl") == man["jobs_sha256"]
    CACHE.mkdir(parents=True, exist_ok=True)
    py = os.environ["PY2D" if dom == "2d" else "PY3D"]
    C0 = int(os.environ.get("TEACH_CPU0", 4))
    assert 4 <= C0 and C0 + W - 1 <= 42, "CPUs 0-3 and 43-47 stay free"
    subprocess.run(["taskset", "-c", f"{C0}-{C0 + W - 1}", py, str(vk.HERE.parent / "benchmark.py"), "teach", dom, str(OUT / f"jobs_{dom}{sfx}.jsonl"), str(CACHE), str(W), str(C0)],
                   check=True, env={**os.environ, "V3OUT": str(vk.K3V / "runs/teach_out_tt")})



def analyze(dom, sfx=""):
    """Teacher labels of the temporary tasks + frozen D (FULL s0) Y / p11 predictions on the retargeted learner views."""
    import benchmark as BM
    import xy as XY  # noqa: F401
    ex = json.loads((OUT / f"EXAMPLES_{dom}{sfx}.json").read_text())
    lab = BM.cache_labels(CACHE, dom)[0]
    snap = {r["root_id"]: r for r in vk.rows(dom, "val")}
    sc = S.Scorer(vk.ckpt("FULL_s0", dom), None, device="cuda")
    L = lambda root, seq: lab.get((root, json.dumps([list(map(int, x)) for x in seq])), (None, None))  # noqa: E731
    rows, par, sem, noise = [], [], [], []
    for e in ex:
        r = snap[e["root_id"]]
        inpT = RT.retarget(r["inputs"], dom, e["A"], e["dA"])
        rootT = S.Root({**r, "inputs": inpT}, dom)
        seq = [tuple(x) for x in e["seq"]]
        xy_full = L(e["root_id"], seq)
        par.append({"root": e["root_id"], "label": [1, 1], "reteach": list(xy_full)})            # snapshot labels are X = 1, Y = 1 by selection
        noise.append({"root": e["root_id"], "reteach_root_id_tag": list(L(e["root_id"] + "~RL", seq))})
        sem.append({"root": e["root_id"], "x_orig_first": L(e["root_id"], [(e["o1"], e["d1"])])[0], "y_tt_first": L(e["first_root"], [])[1]})
        y0 = L(e["tt_root"], [])[1]
        yP = L(e["tt_root"], [tuple(x) for x in e["P"]]) if e["P"] else (None, None)
        cand = [[]] + ([[tuple(x) for x in e["P"]]] if e["P"] else []) + [[tuple(x)] for x in e["single"]]
        pr = sc.score(rootT, [list(map(list, c)) for c in cand])
        base = {"root": e["root_id"], "K": e["K"], "y_tt_S0": y0, "py_tt_S0": pr[0]["p11"], "xy_tt_P": list(yP),
                "py_tt_P": pr[1]["py"] if e["P"] else None, "p11_tt_P": pr[1]["p11"] if e["P"] else None}
        k0 = 1 + (1 if e["P"] else 0)
        sing = {}
        for (o, d), p in zip(e["single"], pr[k0:]):
            x, y = L(e["tt_root"], [(o, d)])
            sing[f"{o}>{d}"] = {"x": x, "y": y, "py": p["py"], "p11": p["p11"], "px": p["px"]}
        base["single"] = sing
        base["props"] = e["props"]
        rows.append(base)
    out = {"dom": dom, "adapter": ADAPTER, "n_examples": len(rows)}
    ok = [p for p in par if None not in p["reteach"]]
    out["parity_identity"] = {"n": len(par), "decided": len(ok), "agree_x1y1": sum(p["reteach"] == [1, 1] for p in ok)}
    nz = [n for n in noise if None not in n["reteach_root_id_tag"]]
    out["rng_key_noise_floor"] = {"n": len(noise), "decided": len(nz), "x1y1": sum(n["reteach_root_id_tag"] == [1, 1] for n in nz)}
    sm = [s for s in sem if None not in (s["x_orig_first"], s["y_tt_first"])]
    out["semantic_first_move"] = {"n": len(sem), "decided": len(sm), "agree": sum(s["x_orig_first"] == s["y_tt_first"] for s in sm),
                                  "x1_y0": sum(s["x_orig_first"] == 1 and s["y_tt_first"] == 0 for s in sm), "x0_y1": sum(s["x_orig_first"] == 0 and s["y_tt_first"] == 1 for s in sm)}
    # temporary-target Y: frozen D on retargeted views vs teacher
    yv = [(r_["y_tt_S0"], r_["py_tt_S0"]) for r_ in rows if r_["y_tt_S0"] is not None]
    for r_ in rows:
        yv += [(v["y"], v["py"]) for v in r_["single"].values() if v["y"] is not None]
        if r_["xy_tt_P"][1] is not None:
            yv.append((r_["xy_tt_P"][1], r_["py_tt_P"]))
    y, p = np.array([a for a, _ in yv]), np.array([b for _, b in yv])
    out["Y_tt_model"] = {"n": len(y), "pos_rate": float(y.mean()), "mean_py": float(p.mean()), "auroc": vk.auroc(y, p), "nll": float(vk.bce(y, p).mean()),
                         "brier": float(((p - y) ** 2).mean()), "ece": vk.ece(y, p)}
    out["S0_blocked"] = {"n": sum(r_["y_tt_S0"] is not None for r_ in rows), "y0": sum(r_["y_tt_S0"] == 0 for r_ in rows),
                         "P_repairs_when_blocked": sum(r_["y_tt_S0"] == 0 and r_["xy_tt_P"] == [1, 1] for r_ in rows)}
    # proposal usefulness for the temporary task: one-step corrective success (X = 1, Y = 1) among each context's top-4, on blocked examples
    use = {}
    for ctx in ("tt_task", "orig_task", "notask"):
        hit, frac = [], []
        for r_ in rows:
            if r_["y_tt_S0"] != 0:
                continue
            res = [r_["single"].get(f"{o}>{d}") for o, ds in r_["props"][ctx].items() for d in ds]
            res = [v for v in res if v and None not in (v["x"], v["y"])]
            if res:
                hit.append(float(any(v["x"] == 1 and v["y"] == 1 for v in res))); frac.append(float(np.mean([v["x"] == 1 and v["y"] == 1 for v in res])))
        use[ctx] = {"blocked_examples": len(hit), "any_one_step_fix_in_top4": float(np.mean(hit)) if hit else None, "fix_rate_per_proposal": float(np.mean(frac)) if frac else None}
    out["proposal_usefulness_blocked"] = use
    # the frozen D as a selector among the one-step candidates of the temporary task (blocked examples): argmax p11 success
    sel = []
    for r_ in rows:
        if r_["y_tt_S0"] != 0:
            continue
        c = [(v["p11"], k, v) for k, v in r_["single"].items() if None not in (v["x"], v["y"])]
        if c:
            best = max(c, key=lambda t: (t[0], t[1]))[2]
            sel.append((float(best["x"] == 1 and best["y"] == 1), float(np.mean([v["x"] == 1 and v["y"] == 1 for _, _, v in c]))))
    out["D_select_one_step_fix"] = {"n": len(sel), "argmax_p11_success": float(np.mean([a for a, _ in sel])) if sel else None,
                                    "random_candidate_success": float(np.mean([b for _, b in sel])) if sel else None}
    vk.wjson(OUT / f"TT_{dom}{sfx}.json", {**out, "rows": rows})
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"build": lambda: build(a[1], int(a[2]), a[3] if len(a) > 3 else "last"), "teach": lambda: teach(a[1], int(a[2]), a[3] if len(a) > 3 else ""),
     "analyze": lambda: analyze(a[1], a[2] if len(a) > 2 else "")}[a[0]]()
