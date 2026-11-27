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
    python r8b.py slots N SEED OUT.json         slot plan (K3 templates)
    python r8b.py status GEN_DIR                yield / cost of stage P
    python r8b.py items GEN_DIR OUT.json J      DERIVE items for accepted K3 parents (J attempts each), pool recorded"""
from __future__ import annotations

import collections, gzip, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V34_PLAN = HERE.parents[2] / "approach_b_final" / "reports" / "final_v34" / "SLOT_PLAN.json.gz"


def pool(parent_id):
    return "A" if int(hashlib.sha256(f"R8B-pool|{parent_id}".encode()).hexdigest(), 16) % 2 == 0 else "B"


def slots(n, seed, out, plan=None):
    import random
    P = json.load(gzip.open(plan or V34_PLAN))
    T = [s["spec"] for s in P["slots"] if s["domain"] == "3d" and s["raw_class"] == "3" and s["spec"]["K"] == 3]
    rng = random.Random(f"R8B-slots|{seed}")
    S = []
    for i in range(int(n)):
        sp = dict(rng.choice(T))
        S.append({"slot_id": f"r8b-3-{i:04d}", "domain": "3d", "K": "3", "ref_root_id": "NONE", "ref_source": "TEMPLATE_ONLY", "kind": "RAW",
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


if __name__ == "__main__":
    a = sys.argv[1]
    {"slots": lambda: slots(*sys.argv[2:5]), "status": lambda: status(sys.argv[2]), "items": lambda: items(*sys.argv[2:5])}[a]()
