#!/usr/bin/env python3
"""V3.4 dependence enrichment on NEW raw parent roots -- thin wrappers around the FROZEN scripts (never edited, never copied):
  2D  order  : order_classification_2d/perm2d.job_run                         (missing permutations of the minimal assignment)
      repark : final_dataset_generation/dep2d.job        (K2_REPARK / K3_REPARK; K3 cap DEP2D_K3_MAXOK, default 5 as the full run)
      hard   : k3_hard/hard2d.job  (start built as k3_hard/build_jobs.py 2d)  + k3_hard/consistency2d.job gate (fail-closed)
  3D  order  : final3d_v4/code/fin3d.job legacy+fixed (V4 fresh-env strength) and/or perm3d.job_run (V3 classification)
      repark : final_dataset_generation/dep3d.job (pins = sha256 of the NEW parents) + k3_hard/consistency3d.job gate
      hard   : k3_hard/hard3d.job (v3, start as build_jobs.py 3d) | final3d_v4/code/hard3d.job (v4, start as build_hard.py)
Overrides (hard-coded paths, child-id namespace, caps) are applied at MODULE TOP LEVEL by setup(), driven by V34E_* env vars, so every spawn
worker (which re-imports this file as __mp_main__) gets them.  Inputs are read through OUT/ds_view (raw -> STORE, code -> generator code);
nothing is ever written to STORE.  Each stage keeps an append-only, resumable ledger (OUT/<stage>.jsonl) with cpu_s per job, and rewrites
OUT/accepted.jsonl (repark/hard) or OUT/order_summary.jsonl.  STOP file in OUT stops after the current job (in-flight jobs re-run on resume).

  v34_enrich.py order  2d|3d --store S --jobs J.json --out O [--workers N] [--code C] [--impl fin3d|perm3d|both]
  v34_enrich.py repark 2d|3d --store S --jobs J.json --out O --host V34xx [--workers N] [--code C]
  v34_enrich.py hard   2d|3d --store S --jobs J.json --out O --order-out O1 [--known D ...] [--variant v3|v4] [--host V34xx]
  J.json = [[parent_root_id, kind, slot_id], ...]  (kind: order -> ignored; repark -> K2_REPARK|K3_REPARK; hard -> K3_HARD)"""
import argparse, hashlib, importlib.util, itertools, json, os, sys, time
from pathlib import Path

FDG = Path(os.environ.get("V34E_FDG", "/home/naren/Desktop/boltzmann_lfd/final_dataset_generation"))
OC2, K3H, V4C = FDG.parent / "order_classification_2d", FDG / "k3_hard", FDG / "final3d_v4/code"
CODE = {"2d": os.environ.get("CODE2D", "/home/naren/abf_v34/src2d/code"), "3d": os.environ.get("CODE3D", "/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/"
        "dataset_bd_classquota_without_home_position_no_overpass/code")}
CFG_HASH = {"2d": "90d3eb68e8a42108", "3d": "8d521b1f6d23db23"}
HIST_HOSTS = {"LOCAL", "GVLAB", "BLACKWELL", "LAPTOP", "GVLAB4", "LAP4"}
E, M = os.environ, {}
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    m = sys.modules[name] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def setup():
    """Import the frozen modules and redirect their hard-coded paths.  Runs at import (parent AND every spawn worker); no-op without env."""
    dom, st = E.get("V34E_DOM"), E.get("V34E_STAGE")
    if not dom or M:
        return
    out = Path(E["V34E_OUT"])
    view = out / "ds_view"
    if dom == "2d":
        sys.path[:0] = [str(OC2), str(FDG), str(K3H)]
        import perm2d as P
        P.DS, P.CODE, P.OUT = view, Path(E["V34E_CODE"]), out              # record()/parent_sha256 read view/raw/roots; boot() reads CODE
        M["P"] = M["_M"] = P
        if st == "repark":
            E.setdefault("DEP2D_K3_MAXOK", "5")
            import dep2d
            host = E["V34E_HOST"]
            dep2d.OUT, dep2d.K3_MAXOK = out, int(E["DEP2D_K3_MAXOK"])
            dep2d.root_id = lambda parent, kind: f"D2_{host}_{kind}_{sha((parent + kind).encode())[:10]}"   # namespaced child ids
            M["dep2d"] = dep2d
        elif st == "hard":
            E["HK_OUT"] = str(out)
            import hard2d, consistency2d
            hard2d.OUT, consistency2d.SCRATCH = out, out / "consistency2d_scratch"
            M.update(hard2d=hard2d, consistency2d=consistency2d)
    else:
        sys.path.insert(0, str(FDG))
        import perm3d as Q, dep3d as D
        for f in ("perm3d.py", "dep3d.py"):                                    # V4 hard3d / fin3d import their own (identical) copies
            assert sha((FDG / f).read_bytes()) == sha((V4C / f).read_bytes()), f
        Q.DS, Q.CODE, Q.OUT = view, view / "code", out
        M.update(Q=Q, _M=Q, dep3d=D)
        if st == "order":
            E["FIN3D_SRC"], E["FIN3D_STORE"] = str(view), str(out / "store")
            E.setdefault("FIN3D_TEMPS", "96,92")
            M["fin3d"] = _load("fin3d", V4C / "fin3d.py")
        elif st == "repark":
            D.MAX_OK_K3 = int(E.setdefault("DEP3D_K3_MAXOK", "5"))
            M["consistency3d"] = _load("consistency3d", K3H / "consistency3d.py")
        elif st == "hard":
            E.setdefault("HK_TEMPS", "96,92,99")
            v = E.get("V34E_VARIANT", "v4")
            if v == "v4":
                E.setdefault("HK_SOURCE_COMMIT", f"fb1120a30ab1be2ede6e0e4c585a93f0aacdb907+{E.get('V34E_HOST', 'V34')}")
            h = M["hard3d"] = _load("hard3d", (V4C if v == "v4" else K3H) / "hard3d.py")
            h.PAUSE_C, h.RESUME_C, h.STOP_C = (float(x) for x in E["HK_TEMPS"].split(","))   # v3 hard-codes 88,82,93 (laptop idles ~89 C)


setup()


# ---------------------------------------------------------------- worker side
def _init(boot, *args):
    """frozen boot + fail-closed teacher config-hash check (a mismatch becomes a per-job boot error, never a label)"""
    mod, fn = boot.split(".")
    getattr(M[mod], fn)(*args)
    _M = M["_M"]._M
    if "boot_error" not in _M:
        try:
            h = _M["A"].env()["config_hash"]
            if h != CFG_HASH[E["V34E_DOM"]]:
                _M["boot_error"] = f"CONFIG_HASH {h} != {CFG_HASH[E['V34E_DOM']]}"
        except Exception as e:  # noqa: BLE001
            _M["boot_error"] = f"config hash check: {type(e).__name__}: {e}"


def _call(a):
    fn, key, item = a
    t0, w0 = time.process_time(), time.time()
    try:
        r = dict(globals()[fn](item) if fn.startswith("w_") else getattr(M[fn.split(".")[0]], fn.split(".")[1])(item))
    except Exception as e:  # noqa: BLE001  (infrastructure error: recorded, never a label; job re-runs only if it is a boot error)
        import traceback
        r = {"accepted": False, "error": f"WRAPPER:{type(e).__name__}:{str(e)[:300]}", "trace": traceback.format_exc()[-1200:]}
    r["key"] = key
    r.setdefault("cpu_s", round(time.process_time() - t0, 1))
    r["wrap_cpu_s"], r["wrap_wall_s"], r["pid"] = round(time.process_time() - t0, 1), round(time.time() - w0, 1), os.getpid()
    return r


def _sum(perms):
    ys = [p.get("y") for p in perms]
    ns, nf = ys.count(1), ys.count(0)
    cls = ("ORDER_DEPENDENT" if ns and nf else "ORDER_INDEPENDENT" if ns == len(ys) and ys else "UNRESOLVED")
    return {"n_success": ns, "n_fail": nf, "n_orders": len(ys), "n_unresolved": len(ys) - ns - nf, "order_class": cls}


def w_order2d(rid):
    r = M["P"].job_run(rid)
    return {**r, "K": len(r.get("assignment") or []) or None, **_sum(r.get("perms") or []), "error": r.get("error")}


def w_order3d(rid):
    Q, F, impl = M["Q"], M["fin3d"], E.get("V34E_IMPL", "fin3d")
    if "boot_error" in Q._M:
        return {"root_id": rid, "error": "boot: " + Q._M["boot_error"]}
    path = str(Q.DS / "raw/roots" / f"{rid}.json")
    rec = json.loads(Path(path).read_text())
    mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
    out = {"root_id": rid, "K": rec["verified_K"], "minimal": mini["sequence"]}
    if impl in ("fin3d", "both"):                                    # build_stage1: every permutation, fresh env (no 'new' perm3d reuse)
        orders = [list(map(list, q)) for q in itertools.permutations([[o, list(d)] for o, d in mini["sequence"]])]
        lg = F.job({"mode": "legacy", "key": f"L_{rid}", "path": path, "orders": orders})
        fx = F.job({"mode": "fixed", "key": f"F_{rid}", "path": path})
        out.update(fin3d_legacy=lg, fin3d_fixed=fx, fixed_objects=fx.get("fixed_objects"), fixed_resolution=fx.get("resolution"),
                   **_sum(lg.get("orders") or []))
    if impl in ("perm3d", "both"):
        p = Q.job_run(rid)
        out["perm3d"] = p
        out["perm3d_summary"] = _sum(p.get("perms") or [])
        if impl == "perm3d":
            out.update(out["perm3d_summary"])
    return out


def w_repark2d(it):
    return {**M["dep2d"].job(tuple(it[:2])), "slot_id": it[2]}


def w_repark3d(it):
    return {**M["dep3d"].job(tuple(it[:2])), "slot_id": it[2]}


def w_hard(item):
    mod = M["hard2d"] if E["V34E_DOM"] == "2d" else M["hard3d"]
    return {**mod.job({k: v for k, v in item.items() if k != "slot_id"}), "slot_id": item.get("slot_id")}


# ---------------------------------------------------------------- parent side
def temp_c():
    for h in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (h / "name").read_text().strip() in ("k10temp", "coretemp"):
                return int((h / "temp1_input").read_text()) / 1000
        except OSError:
            pass
    return None


def rows(p):
    return [json.loads(l) for l in open(p) if l.strip()] if Path(p).exists() else []


def drive(out, name, fn, items, key, workers, boot, initargs=()):
    """resumable pool over items; one ledger line per finished job (ADMIN_STOP / boot errors are re-run)"""
    import multiprocessing as mp
    led = out / f"{name}.jsonl"
    if (out / "STOP").exists():
        print(f"STOP file present: {name} not started", flush=True)
        return
    done = {r["key"] for r in rows(led) if not r.get("precheck") and not str(r.get("reason", "")).startswith("ADMIN_STOP") and "boot:" not in str(r.get("error") or r.get("reason") or "")}
    todo = [it for it in items if key(it) not in done]
    stop_c = float(E.get("V34E_TEMP_STOP_C", "99"))
    print(f"{time.strftime('%FT%TZ', time.gmtime())} {name} todo={len(todo)} done={len(done)} workers={workers}", flush=True)
    if not todo:
        return
    with open(led, "a", buffering=1) as f, mp.get_context("spawn").Pool(min(workers, len(todo)), initializer=_init, initargs=(boot, *initargs)) as pool:
        for i, r in enumerate(pool.imap_unordered(_call, [(fn, key(it), it) for it in todo]), 1):
            r["stage"], r["utc_done"] = name, time.strftime("%FT%TZ", time.gmtime())
            f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
            t = temp_c()
            print(f"{r['utc_done']} {name} {i}/{len(todo)} {r['key']} cpu_s={r.get('cpu_s')} acc={r.get('accepted')} ns={r.get('n_success')} "
                  f"reason={r.get('reason')} temp={t}", flush=True)
            if (out / "STOP").exists() or (t is not None and t >= stop_c):
                print(f"STOP (file or temp {t})", flush=True)
                return


def load_jobs(p):
    J = []
    for j in json.loads(Path(p).read_text()):
        j = list(j.values()) if isinstance(j, dict) else list(j)
        J.append([j[0], j[1] if len(j) > 1 else None, j[2] if len(j) > 2 else None])
    return J


def mkview(a):
    v = a.out / "ds_view"
    v.mkdir(parents=True, exist_ok=True)
    for n, tgt in (("raw", a.store), ("code", Path(a.code))):
        if a.dom == "2d" and n == "code":
            continue
        if not (v / n).is_symlink():
            (v / n).symlink_to(tgt)
        assert (v / n).resolve() == tgt.resolve(), f"ds_view/{n} points elsewhere"


def check_parent(a, rid, K=None):
    p = a.store / "roots" / f"{rid}.json"
    if not p.exists():
        return "PARENT_MISSING"
    r = json.loads(p.read_text())
    if r["ids"].get("config_hash") != CFG_HASH[a.dom]:
        return f"PARENT_CONFIG_HASH_{r['ids'].get('config_hash')}"
    if K is not None and r.get("verified_K") not in K:
        return f"PARENT_VERIFIED_K_{r.get('verified_K')}"
    return None


def reject(out, name, lines):
    led, have = out / f"{name}.jsonl", {r.get("key") for r in rows(out / f"{name}.jsonl")}
    with open(led, "a") as f:
        for ln in lines:
            if ln["key"] not in have:
                f.write(json.dumps({**ln, "accepted": False, "precheck": True, "cpu_s": 0.0, "stage": name, "utc_done": time.strftime("%FT%TZ", time.gmtime())}) + "\n")


def st_order(a, J):
    roots, bad = [], []
    for rid, _, slot in J:
        why = check_parent(a, rid, (2, 3))
        if why:
            bad.append({"key": rid, "root_id": rid, "slot_id": slot, "reason": why})
        elif rid not in roots:
            roots.append(rid)
    reject(a.out, "order", bad)
    if a.dom == "2d":                                                     # perm2d.drive: one pool per geometry implementation
        by = {}
        for rid in roots:
            by.setdefault(json.loads((a.store / "roots" / f"{rid}.json").read_text()).get("geometry_impl") or "original", []).append(rid)
        for g, its in sorted(by.items()):
            drive(a.out, "order", "w_order2d", its, str, a.workers, "P.boot", (g,))
    else:
        drive(a.out, "order", "w_order3d", roots, str, a.workers, "fin3d.boot" if a.impl != "perm3d" else "Q.boot")
    with open(a.out / "order_summary.jsonl", "w") as f:
        for r in rows(a.out / "order.jsonl"):
            f.write(json.dumps({k: r.get(k) for k in ("root_id", "key", "K", "n_success", "n_orders", "n_unresolved", "order_class", "fixed_objects",
                                                       "perm3d_summary", "reason", "error", "cpu_s")}) + "\n")


def gate(a, name, roots, boot, initargs, fn):
    drive(a.out, name, fn, [str(p) for p in roots], lambda x: Path(x).stem, a.workers, boot, initargs)
    return {r["key"]: r.get("consistent") for r in rows(a.out / f"{name}.jsonl")}


def write_accepted(a, kids):
    with open(a.out / "accepted.jsonl", "w") as f:
        for k in kids:
            f.write(json.dumps(k) + "\n")
    print(f"accepted children: {len(kids)}  strengths: {sorted(k['strength'] for k in kids)}", flush=True)


def child(a, rid, parent, kind, slot, gate_ok=True):
    r = json.loads((a.out / "store/roots" / f"{rid}.json").read_text())
    return {"root_id": rid, "parent_root_id": parent, "kind": kind, "slot_id": slot, "n_success": r["n_success"], "n_orders": r["n_orders"],
            "strength": f"{r['n_success']}/{r['n_orders']}", "verified_K": r["verified_K"], "gate_consistent": gate_ok,
            "path": str(a.out / "store/roots" / f"{rid}.json")}


def st_repark(a, J):
    K = {"K2_REPARK": 2, "K3_REPARK": 3}
    good, bad = [], []
    for rid, kind, slot in J:
        why = "KIND_NOT_REPARK" if kind not in K else check_parent(a, rid, (K[kind],))
        (bad.append({"key": f"{rid}|{kind}", "parent_root_id": rid, "kind": kind, "slot_id": slot, "reason": why}) if why else good.append([rid, kind, slot]))
    reject(a.out, "repark", bad)
    key = lambda x: f"{x[0]}|{x[1]}"  # noqa: E731
    if a.dom == "2d":
        drive(a.out, "repark", "w_repark2d", good, key, a.workers, "dep2d.boot")
        kids = [child(a, r["root_id"], r["parent_root_id"], r["kind"], r.get("slot_id")) for r in rows(a.out / "repark.jsonl") if r.get("accepted")]
    else:
        pf = a.out / "pins.json"                                           # pin parent bytes now; a later change fails closed
        pins = json.loads(pf.read_text()) if pf.exists() else {}
        for rid, _, _ in good:
            pins.setdefault(rid, sha((a.store / "roots" / f"{rid}.json").read_bytes()))
        pf.write_text(json.dumps(pins, indent=0))
        drive(a.out, "repark", "w_repark3d", good, key, a.workers, "dep3d.boot", (a.host, str(a.out / "ds_view"), str(a.out), pins))
        acc = [r for r in rows(a.out / "repark.jsonl") if r.get("accepted")]
        g = gate(a, "gate3d", [a.out / "store/roots" / f"{r['root_id']}.json" for r in acc], "consistency3d.boot",
                 (str(a.out / "ds_view"), str(a.out / "consistency3d_scratch")), "consistency3d.job")
        kids = [child(a, r["root_id"], r["parent_root_id"], r["kind"], r.get("slot_id"), g.get(r["root_id"])) for r in acc if g.get(r["root_id"]) is True]
    write_accepted(a, kids)


def known_children(dirs, layouts):
    """build_jobs.py: accepted same-layout verified-K3 children (DEPSEEK repark / earlier HARDK3) of each layout"""
    k = {}
    for d in dirs:
        for f in sorted(Path(d, "store/roots").glob("*.json")):
            r = json.loads(f.read_text())
            c = r.get("construction", {})
            L = c.get("layout_root_id") or c.get("parent_root_id")
            if r.get("verified_K") == 3 and L in layouts and c.get("same_layout_as_parent") and r.get("permutations"):
                mini = next(b for b in r["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
                k.setdefault(L, []).append((r["ids"]["root_id"], mini["sequence"], r["permutations"]))
    return k


def build_hard(a, J):
    """one job per NEW K3 layout, start exactly as build_jobs.py (2d, 3d v3) / build_hard.py (3d v4); no global quota / selection"""
    order = {r["root_id"]: r for r in rows(a.order_out / "order.jsonl") if r.get("root_id")}
    lays = {rid: slot for rid, _, slot in J}
    kc = known_children(a.known, set(lays)) if a.variant != "v4" else {}
    jobs, bad = [], []
    for L, slot in lays.items():
        why = check_parent(a, L, (3,))
        o = order.get(L)
        if why is None and o is None:
            why = "NO_ORDER_STAGE_RESULT"
        if why:
            bad.append({"key": L, "layout": L, "slot_id": slot, "reason": why})
            continue
        if a.variant == "v4":                                              # build_hard.py: fresh-env legacy orders + fixed rule
            ords = (o.get("fin3d_legacy") or {}).get("orders") or []
            if o.get("fixed_objects") != [] or o.get("fixed_resolution") != "EVALUATED":
                why = f"FIXED_OBJECTS_{o.get('fixed_objects')}_{o.get('fixed_resolution')}"
            elif len(ords) != 6 or any(x.get("resolution") != "EVALUATED" for x in ords):
                why = "ORDERS_UNRESOLVED"
            elif sum(x["y"] for x in ords) <= 1:
                why = "START_ALREADY_1_OF_6"
            if why:
                bad.append({"key": L, "layout": L, "slot_id": slot, "reason": why})
                continue
            assign = sorted([od[0], list(od[1])] for od in ords[0]["order"])
            jobs.append({"job_id": f"HJ3d_v4_{L}", "layout": L, "origin": "GENERATED_K3", "start_id": L, "start_ns": sum(x["y"] for x in ords),
                         "start_assign": assign, "start_succ": [[od[0] for od in x["order"]] for x in ords if x["y"] == 1],
                         "known_keys": [json.dumps(sorted([a_, list(d)] for a_, d in assign))], "variant": "v4", "slot_id": slot})
            continue
        if a.dom == "2d":
            perms, assign = o.get("perms") or [], o.get("assignment")
        elif o.get("perm3d"):
            perms, assign = o["perm3d"]["perms"], o["perm3d"]["minimal"]
        else:                                                              # 3d v3 without perm3d: the fresh-env orders of the same assignment
            perms, assign = (o.get("fin3d_legacy") or {}).get("orders") or [], o["minimal"]
        known, keys, best = [(L, assign, perms)] + kc.get(L, []), [], None
        for rid, asg, ps in known:
            if any(p.get("y") not in (0, 1) for p in ps) or len(ps) != 6:
                continue
            keys.append(json.dumps(sorted([o_, int(d)] if a.dom == "2d" else [o_, list(d)] for o_, d in asg)))
            ns = sum(p["y"] for p in ps)
            if ns >= 1 and (best is None or ns < best[0]):
                best = (ns, rid, asg, [[o_ for o_, _ in p["order"]] for p in ps if p["y"] == 1])
        if best is None or best[0] <= 1:
            bad.append({"key": L, "layout": L, "slot_id": slot, "reason": "NO_RESOLVED_START" if best is None else "START_ALREADY_1_OF_6"})
            continue
        jobs.append({"job_id": f"HJ{a.dom}_{a.variant}_{L}", "layout": L, "split": None, "start_id": best[1], "start_ns": best[0],
                     "start_assign": best[2], "start_succ": best[3], "known_keys": sorted(set(keys)), "variant": a.variant, "slot_id": slot})
    return jobs, bad


def st_hard(a, J):
    jobs, bad = build_hard(a, J)
    (a.out / "hard_jobs.json").write_text(json.dumps(jobs))
    reject(a.out, "hard", bad)
    key = lambda x: x["job_id"]  # noqa: E731
    if a.dom == "2d":
        drive(a.out, "hard", "w_hard", jobs, key, a.workers, "hard2d.boot")
        led = [r for r in rows(a.out / "hard.jsonl") if r.get("accepted")]
        saved = [(s["root_id"], r) for r in led for s in r.get("saved", [])]
        g = gate(a, "gate2d", [a.out / "store/roots" / f"{rid}.json" for rid, _ in saved], "consistency2d.boot", (), "consistency2d.job")
        kids = [child(a, rid, r["layout"], "K3_HARD", r.get("slot_id"), g.get(rid)) for rid, r in saved if g.get(rid) is True]
    else:
        pf = a.out / "pins.json"
        pins = json.loads(pf.read_text()) if pf.exists() else {}
        for j in jobs:
            pins.setdefault(j["layout"], sha((a.store / "roots" / f"{j['layout']}.json").read_bytes()))
        pf.write_text(json.dumps(pins, indent=0))
        drive(a.out, "hard", "w_hard", jobs, key, a.workers, "hard3d.boot", (a.host, str(a.out / "ds_view"), str(a.out), pins))
        kids = [child(a, r["root_id"], r["layout"], "K3_HARD", r.get("slot_id"), True) for r in rows(a.out / "hard.jsonl") if r.get("accepted")]
    write_accepted(a, kids)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["order", "repark", "hard"])
    ap.add_argument("dom", choices=["2d", "3d"])
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--code")
    ap.add_argument("--host", default="V34LP")
    ap.add_argument("--allow-historical-host", action="store_true")
    ap.add_argument("--impl", default="fin3d", choices=["fin3d", "perm3d", "both"])
    ap.add_argument("--order-out", type=Path)
    ap.add_argument("--known", nargs="*", default=[])
    ap.add_argument("--variant", default=None, choices=[None, "v3", "v4"])
    a = ap.parse_args()
    assert E.get("PYTHONDONTWRITEBYTECODE") == "1", "set PYTHONDONTWRITEBYTECODE=1"
    a.store, a.out = a.store.resolve(), a.out.resolve()
    a.code = a.code or CODE[a.dom]
    a.variant = a.variant or ("v34" if a.dom == "2d" else "v4")
    a.known = [Path(k).resolve() for k in a.known]
    a.order_out = a.order_out.resolve() if a.order_out else None
    assert (a.store / "roots").is_dir(), "STORE must hold roots/"
    assert a.out != a.store and not str(a.out).startswith(str(FDG)), "OUT must be a new directory"
    if a.stage != "order" and (a.host in HIST_HOSTS or not a.host.isalnum()) and not a.allow_historical_host:
        sys.exit(f"host label {a.host!r} collides with a historical namespace (use e.g. V34LP / V34GV / V34G2)")
    if a.stage == "hard" and a.order_out is None:
        sys.exit("hard needs --order-out (the order stage output of the same parents)")
    a.out.mkdir(parents=True, exist_ok=True)
    mkview(a)
    E.update(V34E_DOM=a.dom, V34E_STAGE=a.stage, V34E_OUT=str(a.out), V34E_CODE=a.code, V34E_HOST=a.host, V34E_IMPL=a.impl,
             V34E_VARIANT=a.variant)
    setup()
    (a.out / f"{a.stage}_run_args.json").write_text(json.dumps({**{k: str(v) for k, v in vars(a).items()}, "env": {k: v for k, v in E.items() if
                                                     k.startswith(("V34E_", "HK_", "DEP2D_", "DEP3D_", "FIN3D_", "OMP_", "MUJOCO", "PYTHON"))},
                                                     "utc": time.strftime("%FT%TZ", time.gmtime())}, indent=1))
    {"order": st_order, "repark": st_repark, "hard": st_hard}[a.stage](a, load_jobs(a.jobs))
