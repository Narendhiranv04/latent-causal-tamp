#!/usr/bin/env python3
"""DISCO-Grid scaled TRAIN-only MCTS collection (search -> distill -> search rounds).  Reuses RepairEnv / DISCOMCTS / collect.py safety.

  freeze : campaign.py freeze --domain D --out DIR --counts '{"1":8,"2":16,"3":16}' --seed S --calls C --iterations I --B 2
                                --tree-wall-s W --round r0 --policy P.pt [--value V.pt] [--exclude-trees GLOB ...]
           TRAIN only, one root per source family, families of every excluded tree set (e.g. historical trees / earlier rounds when
           independence is required) skipped, hash order per K stratum.  Immutable manifest with source/teacher/checkpoint hashes.
  run    : campaign.py run --out DIR --workers N [--shard i/n] [--reserve R]
           N parallel workers claim roots atomically (mkdir CLAIM); each tree runs in its own spawned process under an independent
           parent watchdog (tree wall cap; teacher SIGALRM cannot extend it).  A killed tree is explicitly reconciled (mcts.reconcile):
           it is kept at its last clean checkpoint and never auto-resumed or re-run (no uncertain call is repeated).  Before each tree
           the host must have load1 <= cpus - reserve - 1.
  status : campaign.py status --out DIR"""
from __future__ import annotations
import argparse, glob, hashlib, json, os, socket, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import collect as C  # noqa: E402
import data as D  # noqa: E402


def freeze(a):
    out = Path(a.out)
    rows = D.load_snapshot_rows(a.domain)
    hyg = D.check_split_hygiene(rows)
    if any(v for k, v in hyg.items() if k.endswith("conflicts")):
        raise ValueError("split overlap " + json.dumps(hyg))
    excl_ids = set()
    for g in a.exclude_trees or []:
        excl_ids |= {Path(p).name for p in glob.glob(g) if Path(p).is_dir()}
    excl_fam = {D.root_family_key(r) for r in rows if r["root_id"] in excl_ids}
    seen, sel = set(excl_fam), []
    for k, n in json.loads(a.counts).items():
        cand = sorted((r for r in rows if r["split"] == "train" and str(r["K_legacy"]) == k),
                      key=lambda r: hashlib.sha256(f"disco_final|{a.seed}|{r['root_id']}".encode()).hexdigest())
        got = 0
        for r in cand:
            f = D.root_family_key(r)
            if f in seen:
                continue
            sel.append({"root_id": r["root_id"], "family_id": f, "root_sha256": r["root_sha256"], "input_sha256": C.input_hash(r),
                        "K_legacy": k, "split": "train"})
            seen.add(f); got += 1
            if got == n:
                break
        if got != n:
            raise ValueError(f"only {got}/{n} independent TRAIN families for K={k}")
    m = {"version": 1, "kind": "disco_final_campaign", "domain": a.domain, "round": a.round, "roots": sel, "split_hygiene": hyg,
         "excluded_tree_globs": a.exclude_trees or [], "excluded_families": sorted(excl_fam), "search_seed": a.seed,
         "proposal": {"mode": "p0" if a.value is None and a.round == "r0" else "distilled", "policy": a.policy,
                      "policy_sha256": D.sha256_file(a.policy), "value": a.value, "value_sha256": a.value and D.sha256_file(a.value)},
         "scalers": str(D.ABF_ROOT / f"data/q2_{a.domain}/scalers.json"),
         "snapshot_lock_sha256": D.sha256_file(D.BASE_SNAP / "data_snapshot.lock.json"),
         "source_sha256": {p.name: D.sha256_file(p) for p in HERE.glob("*.py")}, "teacher_source_sha256": C.teacher_sources(a.domain),
         "per_tree": {"iterations": a.iterations, "max_sim_calls": a.calls, "expansion_budget_B": a.B, "C": 1.5, "k": 2.0, "alpha": 0.3,
                      "max_depth": 3, "reward_mode": "geometric", "tree_wall_s": a.tree_wall_s},
         "threads_per_worker": 1, "gpu": False, "frozen_utc": time.strftime("%FT%TZ", time.gmtime())}
    out.mkdir(parents=True, exist_ok=True)
    with (out / "manifest.json").open("x") as f:
        json.dump(m, f, indent=2)
    print(json.dumps({"roots": len(sel), "by_K": {k: sum(r["K_legacy"] == k for r in sel) for k in json.loads(a.counts)},
                      "excluded_families": len(excl_fam)}))


def _tree_worker(out, root):
    m = json.loads((Path(out) / "manifest.json").read_text())
    os.nice(10)
    import torch
    torch.set_num_threads(1)
    import env as E, mcts as M, policy as P, distill as DS  # noqa: E401
    pol, ck = P.load_policy_checkpoint(m["proposal"]["policy"], "cpu")
    val = DS.load_value_checkpoint(m["proposal"]["value"], "cpu")[0] if m["proposal"]["value"] else None
    prop = P.PolicyProposalWrapper(m["domain"], pol, ck["scalers"], "cpu", m["proposal"]["mode"], value_model=val)
    td = Path(out) / root["root_id"]
    env = E.RepairEnv(m["domain"], witness_dir=Path(out) / "witnesses")
    cfg = m["per_tree"]
    t = M.DISCOMCTS(env, prop, seed=int(hashlib.sha256(f"tree|{m['domain']}|{root['root_id']}|{m['search_seed']}".encode()).hexdigest()[:8], 16),
                    **{k: v for k, v in cfg.items() if k not in ("iterations", "max_sim_calls", "tree_wall_s")})
    res = t.run_search(root["root_id"], iterations=cfg["iterations"], max_sim_calls=cfg["max_sim_calls"], save_dir=td)
    (td / "DONE.json").write_text(json.dumps({**res, "K_legacy": root["K_legacy"], "host": socket.gethostname()}, default=str))


def _verify_frozen(m):
    for name, h in m["source_sha256"].items():
        if D.sha256_file(HERE / name) != h:
            raise ValueError("code changed since freeze: " + name)
    for p, h in m["teacher_source_sha256"].items():
        if D.sha256_file(p) != h:
            raise ValueError("teacher source changed: " + p)
    for p, h in ((m["proposal"]["policy"], m["proposal"]["policy_sha256"]), (m["proposal"]["value"], m["proposal"]["value_sha256"])):
        if p and D.sha256_file(p) != h:
            raise ValueError("checkpoint changed: " + p)


def _worker_loop(out, roots, reserve):
    import multiprocessing as mp
    import mcts as M
    m = json.loads((Path(out) / "manifest.json").read_text())
    for root in roots:
        td = Path(out) / root["root_id"]
        try:
            os.makedirs(td / "CLAIM")
        except FileExistsError:
            continue
        (td / "CLAIM" / "host").write_text(f"{socket.gethostname()} {os.getpid()}")
        while os.getloadavg()[0] > (os.cpu_count() or 1) - reserve - 1:
            time.sleep(30)
        p = mp.get_context("spawn").Process(target=_tree_worker, args=(out, root))
        t0 = time.time(); p.start()
        killed = C.wait_for_child(p, m["per_tree"]["tree_wall_s"])
        rec = {"root_id": root["root_id"], "wall_s": round(time.time() - t0, 1), "killed": killed, "exitcode": p.exitcode}
        if (td / "IN_FLIGHT").exists():
            r = M.reconcile(td, [str(Path(out) / "witnesses")])
            rec["reconcile"] = {k: r[k] for k in ("status", "resumable", "inflight_started", "checkpoint_completed_iterations")}
            (td / "KEPT_AT_CHECKPOINT").write_text(json.dumps(rec))     # tree used as-is at its last clean boundary; never resumed here
        with (Path(out) / "log.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")


def run(a):
    import multiprocessing as mp
    out = Path(a.out)
    m = json.loads((out / "manifest.json").read_text())
    _verify_frozen(m)
    roots = m["roots"]
    if a.shard:
        i, n = map(int, a.shard.split("/"))
        roots = [r for r in roots if int(hashlib.sha256(r["root_id"].encode()).hexdigest(), 16) % n == i]
    procs = [mp.get_context("spawn").Process(target=_worker_loop, args=(str(out), roots[w:] + roots[:w], a.reserve)) for w in range(a.workers)]
    for p in procs:
        p.start(); time.sleep(2)
    for p in procs:
        p.join()
    status(a)


def status(a):
    out = Path(a.out)
    m = json.loads((out / "manifest.json").read_text())
    agg = {"roots": len(m["roots"]), "done": 0, "kept_at_checkpoint": 0, "claimed": 0, "calls": 0, "feasible_edges": 0, "solutions_roots": 0,
           "wall_s": 0.0, "cpu_s": 0.0, "edges_by_depth": {}}
    for r in m["roots"]:
        td = out / r["root_id"]
        agg["claimed"] += (td / "CLAIM").exists()
        if (td / "DONE.json").exists():
            s = json.loads((td / "DONE.json").read_text()); agg["done"] += 1
        elif (td / "KEPT_AT_CHECKPOINT").exists() and (td / "tree.json").exists():
            s = json.loads((td / "tree.json").read_text()).get("summary") or {}; agg["kept_at_checkpoint"] += 1
        else:
            continue
        agg["calls"] += s.get("total_sim_calls", 0); agg["feasible_edges"] += s.get("feasible_relocation_edges", 0)
        agg["solutions_roots"] += bool(s.get("found_verified_solution"))
        agg["wall_s"] += s.get("cumulative_wall_s", s.get("wall_s", 0)) or 0; agg["cpu_s"] += s.get("cumulative_cpu_s", 0) or 0
        try:
            import mcts as M
            nodes, _ = M.load_saved_tree_nodes(td)
            for n in nodes:
                if n.node_id > 0 and not n.is_stop_node and not n.is_failed:
                    agg["edges_by_depth"][str(n.depth)] = agg["edges_by_depth"].get(str(n.depth), 0) + 1
                if n.is_stop_node and n.terminal_z == 1:
                    agg.setdefault("success_stop_by_depth", {}); k = str(n.depth - 1)
                    agg["success_stop_by_depth"][k] = agg["success_stop_by_depth"].get(k, 0) + 1
        except Exception:  # noqa: BLE001
            pass
    print(json.dumps(agg))
    (out / "STATUS.json").write_text(json.dumps(agg, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("freeze")
    for k, t, d in (("--domain", str, None), ("--out", str, None), ("--counts", str, None), ("--seed", int, 20261118), ("--calls", int, 32),
                    ("--iterations", int, 32), ("--B", int, 2), ("--tree-wall-s", int, 1800), ("--round", str, "r0"),
                    ("--policy", str, None), ("--value", str, None)):
        f.add_argument(k, type=t, default=d, required=d is None and k not in ("--value",))
    f.add_argument("--exclude-trees", nargs="*")
    r = sp.add_parser("run"); r.add_argument("--out", required=True); r.add_argument("--workers", type=int, default=1)
    r.add_argument("--shard"); r.add_argument("--reserve", type=int, default=5)
    s = sp.add_parser("status"); s.add_argument("--out", required=True)
    a = ap.parse_args()
    {"freeze": freeze, "run": run, "status": status}[a.cmd](a)
