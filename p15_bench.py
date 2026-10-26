"""P15 ledger (runs/p15/guards, contract caps, one guarded OS process per job), P15-0 source / evidence audit, benchmark runners, summaries,
B closure and figures. P10-P14 artifacts are read-only; every P15 output is a new versioned file under runs/p15."""
from __future__ import annotations

import collections
import json
import sys
import time
from pathlib import Path

import numpy as np

import config as cf

OUT = Path("runs/p15")
P14 = Path("runs/p14")
CAPS = {"audit": 3000.0, "retarget_probe": 8000.0, "retarget_train": 10000.0, "retarget_teacher": 15000.0, "index": 6000.0,
        "search_dev": 8000.0, "retro24": 27000.0, "prospective": 38000.0, "ablation": 12000.0, "b_diag": 3000.0, "regression": 3000.0}
JOB = {"cpu_s": 6500.0, "wall_s": 60000.0}


def rd(p):
    return json.loads(Path(p).read_text())


def sha(p) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()


def spent(cat=None) -> float:
    return sum(g["cpu_s"] for g in (rd(p) for p in (OUT / "guards").glob("*.json")) if cat is None or g["category"] == cat)


def job(name, call, cpu, module="p15_bench", category="audit", wall=None) -> dict:
    """One guarded child per OS process (never threads in one parent), charged to one P15 category; refuses past the cap."""
    import teacher
    (OUT / "guards").mkdir(parents=True, exist_ok=True)
    cpu = min(cpu, JOB["cpu_s"], CAPS[category] - spent(category))
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
    print(json.dumps({k: rec[k] for k in ("stop", "returncode", "cpu_s", "wall_s")} | {category: round(spent(category), 1)}))
    return rec


def gate(stage, **kw) -> None:
    cf.write_json(OUT / f"P15_{stage}_GATE.json", {"stage": f"P15-{stage}", **kw, "spend": {c: round(spent(c), 1) for c in CAPS}})


# ------------------------------------------------------------------ P15-0 audit
def audit() -> dict:
    """Recompute P14 D3 (identical-cohort) and matched-admission tables from stored JSON; verify P14 manifest hashes; claim matrix."""
    import p14_audit as pa
    m = rd(P14 / "P14_FINAL_MANIFEST.json")
    mism = [p for sec in ("P14_A", "P14_D", "sources", "figures") for p, h in m[sec].items() if sha(p) != h]
    runs = {k: rd(P14 / "search" / f"EVAL_{k}.json") for k in ("D", "D-pairless", "geometry", "uninformed", "oracle")}
    common = sorted(set.intersection(*[set(v) for v in runs.values()]))
    ok = lambda v: bool(v.get("found") and (v.get("replay") or {}).get("success"))  # noqa: E731
    d3 = {k: {"success": sum(ok(v[r]) for r in common), "n": len(common), "cpu_mean": float(np.mean([v[r]["cpu_s"] for r in common])),
              "roots_completed": len(v)} for k, v in runs.items()}
    rep = rd(P14 / "eval" / "D3_SUMMARY.json")["methods"]
    d3_agree = all(abs(d3[k]["success"] / d3[k]["n"] - rep[k]["success"]) < 1e-12 for k in d3)
    ma = rd(P14 / "calibration" / "MATCHED_ADMISSION.json")["summary"]
    adm = {k: {"val_coverage_mean": float(np.mean(v["val_coverage"])), "test_admission": v["test_admission"], "executed_success": v["executed_success_lower_bound"]}
           for k, v in ma.items() if k.split("|")[1] == "coverage_matched"}
    claims = {
        "first_certified_witness_only": "p14_d_search._move returns at the first CLEAR candidate: alternative modes / terminal q are dropped; minimum travel over modes NOT established",
        "target_unknown_as_none": "p14_d_search._target returns None for any non-VERIFIED planner outcome: UNKNOWN collapsed with failure; depth_exhaustive is not a physical proof",
        "restricted_graph": "movers from ORDERED_TEACHER tokens, move-once, K slots, depth <= 3: a restricted finite graph",
        "root_variant_goal": "p14 root_variant kept R.goal and the original visual tokens; the physical probe used another destination: unmatched comparison",
        "unnecessary_moves": "counted moves outside the ORIGINAL blocker union; not redundant moves",
        "no_similarity_threshold": "lookup ranks only; no validated minimum-similarity cut",
        "validation_vs_test_admission": "coverage matched on VALIDATION; test admissions differ (see table)"}
    out = {"p14_manifest_mismatches": mism, "replay_fidelity_sample": rd(P14 / "lookup" / "PROVENANCE_AUDIT.json")["trace_fidelity_sample"],
           "d3_common_roots": common, "d3_recomputed": d3, "d3_matches_report": d3_agree, "coverage_matched_admission": adm,
           "index": {"entries": len(rd(P14 / "lookup" / "INDEX.json")["entries"]), "excluded_roots": len(rd(P14 / "eval_roster.json")["excluded_roots"])},
           "p14_roster_primary": rd(P14 / "P14_PREREG.json")["D_track"]["roster_primary"], "claims": claims,
           "historical_hashes": {p: sha(p) for p in ("runs/p14/P14_FINAL_MANIFEST.json", "runs/p14/P14_PREREG.json", "runs/p14/lookup/INDEX.json",
                                                     "runs/p14/eval/D3_SUMMARY.json", "runs/p14/calibration/MATCHED_ADMISSION.json")},
           "p14_spend": {c: round(pa.spent(c), 1) for c in pa.CAPS}}
    (OUT / "audit").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "audit" / "P15_0_AUDIT.json", out)
    return out


# ------------------------------------------------------------------ P15-4 / 5: guidance policies and the benchmark runner
GUIDES = ("D", "D-pairless", "geometry", "uniform", "oracle")


class Guide:
    """Reorder-only guidance. D / D-pairless: original-target blocker score from the rebuilt current state (p15_retarget.build_record);
    recursion: an object whose RECALIBRATED temporary-target feasibility (to its first candidate slot) is < 0.5 is deferred behind the
    other candidates. geometry: analytic heuristic on updated positions; geometry recursion defers an object with heuristic blockers among
    the other movers. uniform: catalogue order. oracle: original teacher blocker union (non-deployable), no recursion."""

    def __init__(self, kind, root, rr, recursion=True):
        import p14_d_search as ds
        self.kind, self.root, self.rr, self.recursion = kind, root, rr, recursion and kind != "oracle" and kind != "uniform"
        self.models = ds.d_models(kind == "D-pairless") if kind in ("D", "D-pairless") else []
        self.recal = rd(OUT / "retarget" / "RECALIBRATION.json")["fit_all_dev"]
        self.cache, self.d_calls, self.d_cpu = {}, 0, 0.0
        self.oracle = None

    def _d(self, phys, cells, q, target, goal, pool):
        import p15_retarget as pr
        k = (tuple(sorted(cells.items())), tuple(np.round(q, 12)), target, goal, tuple(pool))
        if k not in self.cache:
            t0 = time.process_time()
            s = pr.retarget_scene(phys.s0, cells, target, q)
            self.cache[k] = pr.d_predict(self.models, pr.build_record(phys.cfg, s, target, goal), target, list(pool) + ["t0"])
            self.d_calls += 1
            self.d_cpu += time.process_time() - t0
        return self.cache[k]

    def _geo(self, phys, cells, q, target, pool):
        import torch
        import d_blockers as db
        import p14_d_search as ds
        ids = self.rr["ids"]
        xy = torch.as_tensor(np.array([phys.s0.lattice.center(cells[o]) for o in ids]), dtype=torch.float64)
        R2 = ds.root_variant(self.rr["R"], phys.robot, xy, ids.index(target), q)
        return dict(zip(pool, db.heuristic(R2, [ids.index(o) for o in pool])))

    def order(self, phys, movers):
        def f(cells, q, moved, cands):
            if self.kind == "uniform" or not cands:
                return cands
            pool = [o for o in movers if o not in moved]
            if self.kind == "oracle":
                sc = {o: float(self.oracle.get(o, 0)) for o in pool}
            elif self.kind == "geometry":
                sc = {o: float(v) for o, v in self._geo(phys, cells, q, "t0", pool).items()}
            else:
                pr = self._d(phys, cells, q, "t0", phys.goal_cell, pool)
                sc = {o: (1 - pr["p_feasible"]) * m for o, m in zip(pr["pool"], pr["marg"])}
            defer = set()
            if self.recursion:
                first = {}
                for o, d in cands:
                    first.setdefault(o, d)
                for o, d in first.items():
                    others = [x for x in pool if x != o]
                    if self.kind == "geometry":
                        if any(self._geo(phys, cells, q, o, others).values()):
                            defer.add(o)
                    else:
                        p = self._d(phys, cells, q, o, d, others)["p_feasible"]
                        lg = np.log(max(p, 1e-9) / max(1 - p, 1e-9))
                        if 1 / (1 + np.exp(-(lg - self.recal["bias"]) / self.recal["temperature"])) < 0.5:
                            defer.add(o)
            return sorted(cands, key=lambda c: (c[0] in defer, -sc.get(c[0], 0.0), cands.index(c)))
        return f


def _slots(phys, idx):
    import p6_scenes as p6
    T = phys.s0.get("t0").cell

    def f(cells, o):
        s = phys.scene(cells, phys.s0.robot.q_rad)
        ds_ = p6._dests(phys.scr, s, o, [T, phys.goal_cell], [], 4)
        occ = set(cells.values())
        ds_ += sorted(d for (src, d) in idx.by_key if src == cells[o] and d not in ds_ and d in phys.scr.valid and d not in occ
                      and p6._cheb(d, T) >= 2 and p6._cheb(d, phys.goal_cell) >= 2)
        return ds_[:6]
    return f


def run_arm(guide, roster, out_name, split="test", recursion=True, budget=None, cpu_cap=400.0, lookup="combined", modal_only=False, use_index=True):
    """One process per arm; writes after every root. Catalogue-restricted action domain (declared), identical for every guide."""
    import p14_eval as pe
    import p15_lookup as pl
    import p15_search as ps
    rs, P, D = pe._roots(split) if split in ("test", "dev") else _prosp_roots()
    idx, _ = pl.index_v2()
    res = rd(OUT / "search" / f"{out_name}.json") if (OUT / "search" / f"{out_name}.json").exists() else {}
    for k in roster:
        if k in res:
            continue
        root, rr, dl = P[k], rs[k], D[k]
        c0, w0 = time.process_time(), time.time()
        phys = ps.Physics(root, idx if use_index else None, lookup, modal_only, budget, cpu_cap)
        g = Guide(guide, root, rr, recursion)
        g.oracle = {o: m for o, m in zip(dl["pool"], dl["mask"])} if dl.get("mask") else ({o: 0 for o in dl["pool"]} if dl.get("y0") == 1 else {})
        movers = sorted({o for it in root["items"] if it["kind"] == "ORDERED_TEACHER" for o, _ in it["sequence"]})
        out = ps.search(phys, g.order(phys, movers), movers, _slots(phys, idx), {o.id: o.cell for o in phys.s0.objects}, phys.s0.robot.q_rad)
        rep = ps.replay(phys, out["plan"]) if out["found"] else None
        union = {o for o, m in zip(dl["pool"], dl["mask"])} if dl.get("mask") else (set() if dl.get("y0") == 1 else None)
        moved = [s["object"] for s in out["plan"]["steps"]] if out["found"] else []
        res[k] = {"family": root["family"], "y0": dl.get("y0"), "found": out["found"], "replay_success": rep, "claim": out["claim"],
                  "min_moves_proven": out["min_moves_proven"], "min_travel_proven": out["min_travel_proven"], "flags": out["flags"],
                  "plan": None if not out["found"] else {"moves": out["plan"]["moves"], "travel": out["plan"]["travel"], "steps": out["plan"]["steps"]},
                  "moves_outside_original_blocker_union": None if union is None or not out["found"] else sum(o not in union for o in moved),
                  "log": out["log"], "used": phys.used, "stats": phys.stats, "truncated": phys._trunc, "d_calls": g.d_calls, "d_cpu_s": g.d_cpu,
                  "cpu_s": time.process_time() - c0, "wall_s": time.time() - w0, "guide": guide, "recursion": g.recursion}
        (OUT / "search").mkdir(parents=True, exist_ok=True)
        cf.write_json(OUT / "search" / f"{out_name}.json", res)


# ------------------------------------------------------------------ prospective cohort (new seeds; frozen before any outcome)
PROSP = OUT / "prospective"
PROSP_FAMS = ("PC_SG", "PR_SIDES", "PN_SIMP", "PN_GIMP", "ORD_CHAIN", "OMIT_OPT")


def build_prospective(seed0=2026200000) -> None:
    """32 new roots: 4 per executable mechanism family (mechanism-conditioned) + 8 NAT (unconditioned, feasible controls). Labels later: only
    the original task and the parking-lattice edits are teacher-labelled (oracle arm / blocker-union metric)."""
    import p13_pipeline as pp
    pd = pp._register()
    specs = [{"family": f, "seed": seed0 + 10 * i + j, "index": 4 * i + j, "wave": 0, "batch": 1, "split": "blind"} for i, f in enumerate(PROSP_FAMS) for j in range(4)]
    specs += [{"family": "NAT", "seed": seed0 + 100 + j, "index": 24 + j, "wave": 0, "batch": 1, "split": "blind"} for j in range(8)]
    if not (PROSP / "plan.json").exists():
        pd.build_plan(PROSP, specs, max_attempts=600, root_cpu=300.0)
    plan = rd(PROSP / "plan.json")
    keep = lambda q: q["token"] == "" or str(q["token"]).startswith("edit:")  # noqa: E731
    plan["queries"] = [q for q in plan["queries"] if keep(q)]
    qs = {q["query"] for q in plan["queries"]}
    plan["units"] = [u for u in plan["units"] if u["query"] in qs]
    plan["label_scope"] = "original task + parking-lattice edits only (oracle / blocker union); search outcomes are the primary physical endpoint"
    plan["plan_hash"] = cf.stable_hash({x: v for x, v in plan.items() if x != "plan_hash"})
    cf.write_json(PROSP / "plan.json", plan)


def prospective_records() -> None:
    """Unlabelled learner records (same pipeline as P13) written under runs/p15/prospective; leakage check against the index."""
    import os
    import torch
    os.environ["P10C_OUT"] = "runs/p13/models"
    import learn_data as ld
    import p10c_train_eval as pc
    import p15_lookup as pl
    cfg, dino, recs = cf.load_config("config.toml"), ld.dino(), []
    plan = rd(PROSP / "plan.json")
    for k, r in plan["roots"].items():
        ed = [it for it in r["items"] if it["kind"] == "SCENE_TARGET_ONLY" and it.get("d_subset")]
        sq = [it for it in r["items"] if it["kind"] == "ORDERED_TEACHER"]
        rec, _ = pc._record(cfg, dino, k, r, {}, "blind", "P15_PROSPECTIVE", ed, sq)
        rec["audit"] |= {"family": r["family"], "variant": r["variant"]}
        ids = rec["audit"]["ids"]
        rec["d"] = {"pool": [ids.index(o) for o in r["parking"]], "roles": [{v: kk for kk, v in r["ids"].items()}[o] for o in r["parking"]]}
        recs.append(rec)
    torch.save({"version": "P15_PROSPECTIVE_RECORDS_V1", "roots": recs}, PROSP / "records.pt")
    idx, _ = pl.index_v2()
    import p14_sweep_index as sx
    P = sx._plans()
    fps = {pl.json_fp(P[e["root"]]) for es in idx.by_key.values() for e in es}
    leak = [k for k, r in plan["roots"].items() if pl.json_fp(r) in fps or k in {e["root"] for es in idx.by_key.values() for e in es}]
    cf.write_json(PROSP / "LEAKAGE_CHECK.json", {"roots": len(plan["roots"]), "index_overlap_by_root_or_fingerprint": leak})


def _prosp_sealed():
    """Prospective teacher outcomes; refused before runs/p15/prospective/UNSEALED (written only after the label hash commit)."""
    import p6_run as p6r
    import operational_teacher as ot
    if not (PROSP / "UNSEALED").exists():
        raise SystemExit("P15 prospective labels are sealed")
    plan, static, pol = rd(PROSP / "plan.json"), rd(PROSP / "static_admission.json")["certificates"], ot.load_policy("teacher_opneg.toml")
    res = {}
    for k in plan["roots"]:
        f = PROSP / "sealed" / f"{k}.json"
        if f.exists():
            done = rd(f)["done"]
            for q in plan["queries"]:
                if q["root"] == k and q["query"] in done:
                    res[q["query"]] = {**p6r.judge(static, pol, q, done[q["query"]]), "query": q, "root": k}
    return res


def _prosp_roots():
    import os
    import torch
    os.environ["P10C_OUT"] = "runs/p13/models"
    import abc7_train as t7
    import p10b_dataset as pd
    ds = torch.load(PROSP / "records.pt", weights_only=False)
    rs = {}
    for r, rec in zip(t7.prepare(ds), ds["roots"]):
        r["ids"], r["audit"], r["d"] = rec["audit"]["ids"], rec["audit"], rec.get("d")
        rs[r["key"]] = r
    plan = rd(PROSP / "plan.json")
    D = pd.d_labels(plan, _prosp_sealed()) if (PROSP / "UNSEALED").exists() else {k: {} for k in plan["roots"]}
    return rs, plan["roots"], D
