"""DISCO-Grid final scaled TRAIN campaign (user-authorized FINAL-SCALE amendment; never touches VAL/TEST outcomes).

Reuses the stage-2 engine unchanged where it matters: per-root physical search = collect.execute (journalled queries, independent
watchdog, quarantine of IN_FLIGHT trees, no automatic resume); fits = campaign.fit_worker (O0 all-feasible, O1 all-feasible,
O0 successful-only x seeds 0/1/2, 45 fixed epochs, exact trainer/optimizer/RNG resume).  New: an independent, family-disjoint TRAIN
cohort with NESTED K-stratified ladder subsets, parallel worker slots (one physical child each), per-host reserves.

  freeze : scale.py freeze --domain D --out OUT --counts JSON --ladder JSON --calls C --iterations I --tree-wall-s W --query-wall-s Q
  run    : scale.py run --out OUT --domain D --round r --workers N [--shard i/n]       (r=0 uses P0 s0; r=1 uses the round-0 fit of the
           largest subset, O0 all-feasible s0, exactly like E16)
  fit    : scale.py fit --out OUT --domain D --round r --subset NAME [--calls-cap C]     (streams = clean trees of rounds 0..r restricted
           to the subset; --calls-cap truncates every tree to its first C charged calls = search-budget ladder)
  status : scale.py status --out OUT --domain D
Environment: DISCO_EXECUTION_AUTHORIZATION=<FINAL_SCALE_AUTHORIZATION.json>, DISCO_SOURCE_COMMIT, CUDA_VISIBLE_DEVICES=''."""
from __future__ import annotations
import argparse, hashlib, json, multiprocessing as mp, os, pickle, shutil, socket, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import collect as C  # noqa: E402
import data as D  # noqa: E402
import journal as J  # noqa: E402
import policy as P  # noqa: E402

TAG = "disco-final-scale-v1"


def jr(p):
    return json.loads(Path(p).read_text())


def freeze(a):
    out = Path(a.out); dom = a.domain
    rows = D.load_snapshot_rows(dom)
    hyg = D.check_split_hygiene(rows)
    if any(v for k, v in hyg.items() if k.endswith("conflicts")):
        raise ValueError("split overlap " + json.dumps(hyg))
    groups = D.independence_groups(rows)
    used = {p.name for p in (D.DISCO_ROOT / "trees" / dom).glob("*/*") if p.is_dir()}          # historical D3 trees
    for m in (D.DISCO_ROOT / "stage2").rglob("manifest.json"):                                   # stage-2 pilots, E16, evaluations
        try:
            used.update(r["root_id"] for r in jr(m).get("roots", []) if isinstance(r, dict) and "root_id" in r)
        except Exception:  # noqa: BLE001
            pass
    for m in (D.DISCO_ROOT / "validation_v2").rglob("manifest.json"):
        try:
            used.update(r["root_id"] for r in jr(m).get("roots", []) if isinstance(r, dict) and "root_id" in r)
        except Exception:  # noqa: BLE001
            pass
    coh = HERE / "reports/stage2/cohorts.json"
    if coh.exists():
        used.update(r["root_id"] for r in jr(coh)["domains"][dom]["train_roots"])
    excl = {groups[r["root_id"]] for r in rows if r["root_id"] in used}
    seen, sel = set(excl), []
    for k, n in json.loads(a.counts).items():
        cand = sorted((r for r in rows if r["split"] == "train" and str(r["K_legacy"]) == k),
                      key=lambda r: hashlib.sha256(f"{TAG}|{dom}|{r['root_id']}".encode()).hexdigest())
        got = []
        for r in cand:
            g = groups[r["root_id"]]
            if g in seen:
                continue
            seen.add(g)
            got.append({"root_id": r["root_id"], "family_id": g, "root_sha256": r["root_sha256"], "input_sha256": C.input_hash(r),
                        "K_legacy": k, "split": "train", "rank_in_K": len(got)})
            if len(got) == n:
                break
        if len(got) != n:
            raise ValueError(f"{dom} K={k}: only {len(got)}/{n} independent TRAIN groups")
        sel += got
    ladder = {name: {k: int(v) for k, v in q.items()} for name, q in json.loads(a.ladder).items()}   # nested: first q[K] ranks per K
    for name, q in ladder.items():
        for k, v in q.items():
            if v > json.loads(a.counts)[k]:
                raise ValueError("ladder subset exceeds cohort")
    m = {"version": 1, "tag": TAG, "domain": dom, "roots": sel, "ladder": ladder, "split_hygiene": hyg,
         "excluded_used_roots": len(used), "excluded_groups": len(excl), "search_seed_schedule": [20261118, 20261218],
         "per_tree": {"iterations": a.iterations, "max_sim_calls": a.calls, "expansion_budget_B": 2, "C": 1.5, "k": 2.0, "alpha": 0.3,
                      "max_depth": 3, "reward_mode": "geometric"},
         "tree_wall_s": a.tree_wall_s, "query_wall_s": a.query_wall_s,
         "snapshot_lock_sha256": D.sha256_file(D.BASE_SNAP / "data_snapshot.lock.json"),
         "teacher_source_sha256": C.teacher_sources(dom), "frozen_utc": time.strftime("%FT%TZ", time.gmtime())}
    out.mkdir(parents=True, exist_ok=True)
    with (out / f"cohort_{dom}.json").open("x") as f:
        json.dump(m, f, indent=1)
    print(json.dumps({"domain": dom, "roots": len(sel), "excluded_groups": len(excl),
                      "ladder": {n: sum(q.values()) for n, q in ladder.items()}}))


def subset_roots(m, name):
    if name == "ALL":
        return [r["root_id"] for r in m["roots"]]
    q = m["ladder"][name]
    return [r["root_id"] for r in m["roots"] if r["rank_in_K"] < q.get(r["K_legacy"], 0)]


def proposal_for(out, dom, rnd):
    if rnd == 0:
        return D.DISCO_ROOT / f"runs/p0/{dom}/s0/model.pt", None
    fit = Path(out) / f"training/{dom}_R{rnd - 1}_ALL/{P.O0}_all_feasible_s0"
    return fit / "policy.pt", fit / "value.pt"


def tree_manifest(m, root, rnd, policy, value):
    dom = m["domain"]; scal = D.ABF_ROOT / f"data/q2_{dom}/scalers.json"
    cs = m["search_seed_schedule"][rnd]
    ss = int(hashlib.sha256(f"{TAG}|{dom}|{rnd}|{root['root_id']}|{cs}".encode()).hexdigest()[:8], 16) % (2 ** 31 - 1)
    return dict(version=3, domain=dom, roots=[{k: root[k] for k in ("root_id", "family_id", "root_sha256", "input_sha256", "K_legacy", "split")}],
                source_commit=os.environ.get("DISCO_SOURCE_COMMIT"), runtime_versions={n: __import__("importlib.metadata", fromlist=["version"]).version(n)
                for n in ("torch", "numpy", "mujoco")}, permission_envelope="FINAL-SCALE-v1 APPROVED", cohort_seed=cs, search_seed=ss,
                network_initialization_seed=0, proposal_mode="distilled" if value else "p0", observation_schema=P.O0,
                policy_checkpoint=str(policy), policy_sha256=D.sha256_file(policy), value_checkpoint=str(value) if value else None,
                value_sha256=D.sha256_file(value) if value else None, scalers=str(scal), scalers_sha256=D.sha256_file(scal),
                snapshot_lock_sha256=D.sha256_file(D.BASE_SNAP / "data_snapshot.lock.json"),
                source_sha256={p.name: D.sha256_file(p) for p in HERE.glob("*.py")}, teacher_source_sha256=C.teacher_sources(dom),
                host_allowlist=[socket.gethostname()], workers=1, threads=1, gpu=False, wall_envelope_s=m["tree_wall_s"],
                cpu_envelope_s=m["tree_wall_s"], rss_limit_kib=3 * 2 ** 20, query_wall_s=m["query_wall_s"],
                aggregate_adapter_call_ceiling=m["per_tree"]["max_sim_calls"], per_tree=m["per_tree"])


def _slot_worker(out, dom, rnd, roots, slot):
    os.environ["DISCO_WORKER_SLOT"] = f"{socket.gethostname()}_{slot}"
    m = jr(Path(out) / f"cohort_{dom}.json")
    pol, val = proposal_for(out, dom, rnd)
    for root in roots:
        td = Path(out) / f"trees/{dom}/R{rnd}/{root['root_id']}"
        if (td / "ATTEMPT_COMPLETE.json").exists():
            continue
        try:
            td.mkdir(parents=True)                                       # atomic claim; an existing dir = claimed/interrupted elsewhere
        except FileExistsError:
            continue
        J.atomic_json(td / "CLAIM.json", {"host": socket.gethostname(), "slot": slot, "pid": os.getpid(), "utc": time.time()})
        while True:                                                       # per-host reserve from the authorization record
            try:
                C.require_headroom(); break
            except RuntimeError:
                time.sleep(60)
        J.atomic_json(td / "manifest.json", tree_manifest(m, root, rnd, pol, val))
        t0 = time.time()
        try:
            C.execute(td)
            err = None
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        sd = td / root["root_id"]
        clean = (sd / "checkpoint.pkl").exists() and not (sd / "IN_FLIGHT").exists() and err is None
        J.atomic_json(td / "ATTEMPT_COMPLETE.json", dict(root_id=root["root_id"], K_legacy=root["K_legacy"], family_id=root["family_id"],
                      clean=clean, tree=str(sd), error=err, status="COMPLETED" if clean else "QUARANTINED_UNRESOLVED",
                      host=socket.gethostname(), wall_s=round(time.time() - t0, 1),
                      cancellation=jr(td / "BLOCKED_WALL_LIMIT.json") if (td / "BLOCKED_WALL_LIMIT.json").exists() else None))
        print(dom, f"R{rnd}", root["root_id"], "clean" if clean else "QUARANTINED", round(time.time() - t0), err or "", flush=True)


def run(a):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("CPU only")
    C.execution_host()
    m = jr(Path(a.out) / f"cohort_{a.domain}.json")
    roots = m["roots"]
    if a.shard:
        i, n = map(int, a.shard.split("/"))
        roots = [r for r in roots if int(hashlib.sha256(r["root_id"].encode()).hexdigest(), 16) % n == i]
    roots = sorted(roots, key=lambda r: (r["rank_in_K"], r["K_legacy"]))     # smallest ladder subsets complete first
    ps = [mp.get_context("spawn").Process(target=_slot_worker, args=(a.out, a.domain, a.round, roots[w:] + roots[:w], w)) for w in range(a.workers)]
    for p in ps:
        p.start(); time.sleep(3)
    for p in ps:
        p.join()


def truncate_tree(src, dst, cap):
    """Copy of a clean tree restricted to the nodes created while the first `cap` charged calls were spent (iteration granularity)."""
    import mcts as M
    nodes, meta = M.load_saved_tree_nodes(src)
    with open(Path(src) / "checkpoint.pkl", "rb") as f:
        ck = pickle.load(f)
    last = -1
    for tr in ck["iteration_traces"]:
        if tr["transition_calls"] + tr["terminal_calls"] <= cap:
            last = tr["iteration"]
    keep = [n for n in nodes if n.created_at_iter <= last or n.node_id == 0]
    ids = {n.node_id for n in keep}
    for n in keep:
        n.children_ids = [c for c in n.children_ids if c in ids]
        if n.stop_child_id is not None and n.stop_child_id not in ids:
            n.stop_child_id = None
    dst = Path(dst); dst.mkdir(parents=True, exist_ok=True)
    with open(dst / "nodes.pkl", "wb") as f:
        pickle.dump(keep, f)
    meta = dict(meta); meta["truncated_to_calls"] = cap; meta["truncated_last_iteration"] = last
    (dst / "tree.json").write_text(json.dumps(meta, default=str))
    return len(keep)


def fit(a):
    import campaign as CA
    out = Path(a.out); dom = a.domain
    m = jr(out / f"cohort_{dom}.json")
    keep = set(subset_roots(m, a.subset))
    streams = []
    for rnd in range(a.round + 1):
        trees = []
        for f in sorted((out / f"trees/{dom}/R{rnd}").glob("*/ATTEMPT_COMPLETE.json")):
            s = jr(f)
            if s["clean"] and s["root_id"] in keep:
                t = Path(s["tree"])
                if a.calls_cap:
                    t2 = out / f"truncated/{dom}/R{rnd}_c{a.calls_cap}/{s['root_id']}"
                    if not (t2 / "nodes.pkl").exists():
                        truncate_tree(t, t2, a.calls_cap)
                    t = t2
                trees.append(str(t))
        streams.append(trees)
    name = f"{dom}_R{a.round}_{a.subset}" + (f"_c{a.calls_cap}" if a.calls_cap else "")
    dest = out / "training" / name
    dest.mkdir(parents=True, exist_ok=True)
    prev = (out / f"training/{dom}_R{a.round - 1}_{a.subset}{f'_c{a.calls_cap}' if a.calls_cap else ''}") if a.round else None
    J.atomic_json(dest / "STREAMS.json", {"streams": streams, "previous": str(prev) if prev else None, "subset": a.subset,
                                          "calls_cap": a.calls_cap, "n_trees": [len(s) for s in streams]})
    CA.fit_worker(dom, dict(streams=streams, previous=str(prev) if prev else None, controller_pid=os.getpid()), dest, a.round)
    print(json.dumps({"fit": str(dest), "trees_per_round": [len(s) for s in streams]}))


def status(a):
    out = Path(a.out); dom = a.domain
    for rnd in (0, 1):
        rows = [jr(f) for f in (out / f"trees/{dom}/R{rnd}").glob("*/ATTEMPT_COMPLETE.json")]
        if not rows:
            continue
        claimed = len(list((out / f"trees/{dom}/R{rnd}").glob("*/CLAIM.json")))
        print(json.dumps({"round": rnd, "complete": len(rows), "clean": sum(r["clean"] for r in rows), "claimed": claimed,
                          "wall_s_sum": round(sum(r.get("wall_s", 0) for r in rows))}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("freeze")
    for k, t, d in (("--domain", str, None), ("--out", str, None), ("--counts", str, None), ("--ladder", str, None), ("--calls", int, None),
                    ("--iterations", int, 24), ("--tree-wall-s", int, 1800), ("--query-wall-s", int, 120)):
        f.add_argument(k, type=t, default=d, required=d is None)
    r = sp.add_parser("run"); r.add_argument("--out", required=True); r.add_argument("--domain", required=True)
    r.add_argument("--round", type=int, required=True); r.add_argument("--workers", type=int, default=1); r.add_argument("--shard")
    g = sp.add_parser("fit"); g.add_argument("--out", required=True); g.add_argument("--domain", required=True)
    g.add_argument("--round", type=int, required=True); g.add_argument("--subset", default="ALL"); g.add_argument("--calls-cap", type=int, default=0)
    s = sp.add_parser("status"); s.add_argument("--out", required=True); s.add_argument("--domain", required=True)
    a = ap.parse_args()
    {"freeze": freeze, "run": run, "fit": fit, "status": status}[a.cmd](a)
