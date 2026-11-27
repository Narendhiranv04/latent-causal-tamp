#!/usr/bin/env python3
"""R8B independent 3D long-horizon evaluation cohort (evaluator-only; never imported by any planner).
Design (frozen before collection beyond the pilot; reports/final/R8_K45_DATASET_REPORT.md):
  Stage P  fresh K3 PARENT roots: the unchanged production SHELF66V3 generator through the V3.4 slot driver (v34_gen.py) under a NEW name /
           seed namespace ('r8bp'); slot templates = generator factor tuples of the V3.4 3D K3 slots (templates only; no reference roots).
  Stage D  the existing K45 derivation pipeline (compose3d k45 generate_a4.attempt_x, DERIVE = parent + ONE physically necessary enabler,
           certified from scratch: initial target infeasible, continuous replayed witness X = Y = 1, (K-1)-subset shorter probe).
           Pool assignment per PARENT FAMILY, fixed in advance: sha256('R8B-pool|' + parent_root_id) even -> pool A (K3 -> K4 child = roster
           K4 root); odd -> pool B (K3 -> K4 intermediate (never roster) -> K5 child = roster K5 root).  At most ONE roster root per parent
           family, so the 200 roots come from distinct fresh families.
  Labels   L_ref = verified witness length (4 / 5); WITNESS_LEN_K_MIN_UNKNOWN unless a sound lower bound exists (none is claimed).
    python r8b.py slots N SEED OUT.json [PLAN OFF] slot plan (K3 templates; slot ids from OFF)
    python r8b.py status GEN_DIR                yield / cost of stage P
    python r8b.py items GEN_DIR OUT.json J      DERIVE items for accepted K3 parents (J attempts each), pool recorded"""
from __future__ import annotations

import collections, gzip, hashlib, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V34_PLAN = HERE.parents[2] / "approach_b_final" / "reports" / "final_v34" / "SLOT_PLAN.json.gz"


def pool(parent_id):
    return "A" if int(hashlib.sha256(f"R8B-pool|{parent_id}".encode()).hexdigest(), 16) % 2 == 0 else "B"


def slots(n, seed, out, plan=None, off=0):
    import random
    P = json.load(gzip.open(plan or V34_PLAN))
    T = [s["spec"] for s in P["slots"] if s["domain"] == "3d" and s["raw_class"] == "3" and s["spec"]["K"] == 3]
    rng = random.Random(f"R8B-slots|{seed}")
    S = []
    for i in range(int(n)):
        sp = dict(rng.choice(T))
        S.append({"slot_id": f"r8b-3-{int(off) + i:04d}", "domain": "3d", "K": "3", "ref_root_id": "NONE", "ref_source": "TEMPLATE_ONLY", "kind": "RAW",
                  "spec": sp, "raw_class": "3", "needs_2d_cover_table": False})
    Path(out).write_text(json.dumps({"slots": S, "note": "R8B fresh K3 parents; factor templates only (V3.4 3D K3 slots); name namespace r8bp"}, indent=0))
    print(len(S), collections.Counter(json.dumps(s["spec"], sort_keys=True) for s in S).most_common(1)[0][1])


def status(gen_dir):
    L = [json.loads(l) for l in open(Path(gen_dir) / "ledger.jsonl")]
    acc = [e for e in L if e.get("accepted")]
    cpu = sum(e.get("v34_cpu_wall_s") or e.get("wall_s") or 0 for e in L) / 3600
    obs = collections.Counter(str(e.get("observed")) for e in acc)
    rej = collections.Counter((e.get("reason") or "")[:40] for e in L if not e.get("accepted"))
    k3 = obs.get("3", 0)
    out = {"attempts": len(L), "accepted": len(acc), "observed": dict(obs), "rejected": dict(rej.most_common(8)), "worker_h": round(cpu, 2),
           "worker_h_per_K3": round(cpu / k3, 2) if k3 else None}
    print(json.dumps(out, indent=1))
    return out


def items(gen_dir, out, J):
    L = [json.loads(l) for l in open(Path(gen_dir) / "ledger.jsonl")]
    I = []
    for e in L:
        if e.get("accepted") and str(e.get("observed")) == "3":
            p = Path(gen_dir) / "roots" / f"{e['root_id']}.json"
            if not p.exists():
                continue
            for j in range(int(J)):
                I.append({"root_id": f"{e['root_id']}-d{j}", "kind": "DERIVE", "mode": "v2", "parent_id": e["root_id"], "seed": int(hashlib.sha256(f"R8B|{e['root_id']}|{j}".encode()).hexdigest()[:8], 16),
                          "j": j, "parent_path": str(p), "pool": pool(e["root_id"])})
    Path(out).write_text(json.dumps(I, indent=0))
    print(len(I), collections.Counter(i["pool"] for i in I))


J = 9                                       # DERIVE v2 attempts per (parent, step): blocker j % 3 x destination (j // 3) % 3


def parents(gen_dirs):
    """Accepted K3 parents (observed 3) of every generation shard, in a fixed order (shard, ledger order)."""
    out = []
    for g in gen_dirs:
        lp = Path(g) / "ledger.jsonl"
        if not lp.exists():
            continue
        for l in open(lp):
            try:
                e = json.loads(l)
            except ValueError:                                                 # partially copied last line (relay in progress)
                continue
            p = Path(g) / "roots" / f"{e.get('root_id')}.json"
            if e.get("accepted") and str(e.get("observed")) == "3" and p.exists():
                out.append((e["root_id"], str(p)))
    return out


def derive(gen_dirs, outdir, workers, cpu_lo, cap_h, a4_code):
    """Pipelined DERIVE (K3 parent -> K4 child [pool A: roster]; pool B: K4 intermediate -> K5 child [roster]).  Per parent family: attempts
    j = 0..J-1 per step, at most 2 in flight, the family stops at its first accepted roster child (lowest completed j); pool B retries the
    K4 step with the next j only if every K5 attempt of an intermediate failed.  Outcome-blind w.r.t. any planner; CPU-h cap; STOP drains."""
    import multiprocessing as mp
    import time
    sys.path.insert(0, a4_code)
    import generate_a4 as A4
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    led = out / "ledger_r8b.jsonl"
    done = [json.loads(l) for l in open(led)] if led.exists() else []
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + int(workers))))
    pool = mp.get_context("spawn").Pool(int(workers), initializer=A4.boot, initargs=(str(out / "store"),), maxtasksperchild=3)
    S = {}                                                                     # family -> state

    def st(pid, path):
        return S.setdefault(pid, {"pool": pool_of(pid), "path": path, "k4_j": 0, "k5": None, "k5_j": 0, "done": False, "inflight": 0, "k4_ok": []})

    def apply(r):
        s = S[r["family"]]
        s["inflight"] -= 1
        if not r.get("accepted") or s["done"]:
            return
        if r["step"] == "K4" and s["pool"] == "A" or r["step"] == "K5":
            s["done"], s["roster"] = True, r["root_id"]
        elif r["step"] == "K4" and s["k5"] is None:
            s["k5"], s["k5_j"] = r["child_path"], 0
    for d in done:
        s = st(d["family"], d["parent_path"]); s["inflight"] += 1
        s["k4_j" if d["step"] == "K4" else "k5_j"] = max(s["k4_j" if d["step"] == "K4" else "k5_j"], d["j"] + 1)
        if d["step"] == "K4" and d.get("accepted") and s["pool"] == "B" and s["k5"] is None:
            s["k5"] = d["child_path"]
        apply(d)
    running, f = {}, open(led, "a")
    while True:
        for rid, (ar, t, meta) in list(running.items()):
            if ar.ready():
                r = {**ar.get(), **meta}; running.pop(rid)
                f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno()); done.append(r)
                apply(r)
                if r["step"] == "K5" and not S[r["family"]]["done"] and S[r["family"]]["k5_j"] >= J and S[r["family"]]["inflight"] == 0:
                    S[r["family"]]["k5"] = None                                  # every K5 attempt of this intermediate failed -> next K4 j
                print(f"{time.strftime('%H:%M:%S')} {rid} {r.get('reason')} K={r.get('K_child')} cpu={r.get('cpu_s')}", flush=True)
        for pid, path in parents(gen_dirs):
            st(pid, path)
        cpu_h = (sum(d.get("cpu_s", 0) for d in done) + sum(time.time() - t for t, _ in [(v[1], 0) for v in running.values()])) / 3600
        roster = {k: v["roster"] for k, v in S.items() if v.get("roster")}
        (out / "STATUS.json").write_text(json.dumps({"utc": time.strftime("%FT%TZ", time.gmtime()), "parents": len(S), "attempts": len(done), "running": len(running),
                                                     "cpu_h": round(cpu_h, 2), "roster_A_K4": sum(1 for k in roster if S[k]["pool"] == "A"),
                                                     "roster_B_K5": sum(1 for k in roster if S[k]["pool"] == "B"), "stop": (out / "STOP").exists()}))
        if cpu_h >= float(cap_h) - 0.05:
            pool.terminate(); print("R8B_DERIVE_CAP_HARD_STOP", flush=True); break
        nxt = None
        if len(running) < int(workers) and not (out / "STOP").exists() and cpu_h + (len(running) + 1) * 0.1 < float(cap_h):
            for pid, s in sorted(S.items(), key=lambda kv: (kv[1]["inflight"], kv[0])):     # least-served family first
                if s["done"] or s["inflight"] >= 2:
                    continue
                if s["k5"] is not None and s["k5_j"] < J:
                    nxt = (pid, "K5", s["k5_j"], s["k5"]); s["k5_j"] += 1; break
                if s["k5"] is None and s["k4_j"] < J:
                    nxt = (pid, "K4", s["k4_j"], s["path"]); s["k4_j"] += 1; break
        if nxt:
            pid, step, j, pp = nxt
            rid = f"{pid}-r8b{step.lower()}j{j}" if step == "K4" else f"{Path(pp).stem}-k5j{j}"
            it = {"root_id": rid, "kind": "DERIVE", "mode": "v2", "parent_id": Path(pp).stem, "j": j, "parent_path": pp, "out": str(out),
                  "seed": int(hashlib.sha256(f"R8B|{rid}".encode()).hexdigest()[:8], 16)}
            S[pid]["inflight"] += 1
            running[rid] = (pool.apply_async(A4.attempt_x, (it,)), time.time(), {"family": pid, "step": step, "j": j, "parent_path": S[pid]["path"], "pool": S[pid]["pool"]})
            continue
        if (out / "STOP").exists() and not running:
            print("R8B_DERIVE_STOPPED", flush=True); break
        time.sleep(10)
    f.close()


pool_of = pool

if __name__ == "__main__":
    a = sys.argv[1]
    {"slots": lambda: slots(*sys.argv[2:7]), "status": lambda: status(sys.argv[2]), "items": lambda: items(*sys.argv[2:5]),
     "derive": lambda: derive(sys.argv[2].split(","), *sys.argv[3:8])}[a]()
