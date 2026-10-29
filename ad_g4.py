"""Approach D G4 (approachD_G4_local_witness_catalog_and_causal_repair_instructions_v1_0): local witness-grounded motion coverage.

Local 2D only (P13-P17 archives, frozen Dp17, frozen catalog C3). Three things are kept apart throughout:
  teacher feasibility   the historical P16 teacher (p16_motion.DetPhysics + p16_common.verify_sequence) VERIFIED a specific sequence from
                        a specific occupancy and start q; re-running it offline (deterministic node budgets) reproduces that witness;
  library realizability the solver-free provider (ad_provider.Precompiled) executes a chain from stored records only, re-certified in the
                        current scene and replayed independently; a missing record is UNAVAILABLE, never infeasible;
  policy effectiveness  a search policy finds a realizable repair under a common budget without the teacher sequence as a hint.
Catalogs (both = C3 + witness pieces, written under runs/approach_d/g4/catalogs):
  W-ROOT      pieces of the exact DEV witnesses (each record cut at existing waypoints into a free-arm connector and an object core;
              consecutive free legs concatenated bitwise). Engineering ceiling only: compiled with the root's own teacher witness.
  W-TRANSFER  pieces of TRAIN-root witnesses (roots disjoint from DEV, chosen in fixed root-id order; no DEV label, sequence or trace is
              read), plus offline empty-workspace home connectors for their cores (the G2a EXACT_CELL_WITNESS representation).
Offline compilation happens only here, under one ledger (400 fresh planner / IK invocations or 1200 CPU-s). Runtime stays solver-free."""
from __future__ import annotations

import collections
import glob
import hashlib
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

import ad_runtime as ar
import config as cf

VERSION = "AD_G4_V1"
OUT, FIG = Path("runs/approach_d/g4"), Path("visualizations/approach_d/g4")
GKEYS = {"seed", "compile_attempts", "compile_cpu_s", "cohort_b", "transfer_roots", "max_hops", "sweep_demote"}
ROLE = {"W_ROOT": "W_ROOT_WITNESS", "COHORT_B": "W_ROOT_WITNESS", "W_TRANSFER": "W_TRANSFER_WITNESS"}


def gcfg(path="approach_d.toml") -> dict:
    import tomllib
    with open(path, "rb") as f:
        c = tomllib.load(f)["g4"]
    if set(c) != GKEYS:
        raise ValueError(f"invalid [g4]: {sorted(set(c) ^ GKEYS)}")
    return c


def rd(p):
    return json.loads(Path(p).read_text())


def _plan(split):
    return rd(f"runs/p16/data/{split}/plan.json")["roots"]


def _merged(split, kind):
    out = {}
    for f in sorted(glob.glob(f"runs/p16/data/{split}/{kind}*.json")):
        out.update(rd(f))
    return out


def dev_roots():
    return sorted(rd("runs/p16/data/dev/pilot_keys.json"))


def _sha(*x):
    return hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()


# ------------------------------------------------------------------ G4.0 baseline freeze
def baseline() -> dict:
    """Fingerprints of everything G4 must not change, plus the historical G3 facts it starts from (saved results, not re-derived)."""
    import ad_causal as C
    import ad_local as L
    vb, va = rd(C.OUT / "VIEW_B_C3.json"), rd(C.OUT / "VIEW_A_calib.json")
    g = rd(L.OUT / "catalog" / "GRAPH_C3.json")
    files = ["config.toml", "approach_d.toml", "runs/p16/data/dev/plan.json", "runs/p16/data/dev/pilot_keys.json",
             str(L.OUT / "catalog" / "GRAPH_C3.json"), str(L.OUT / "catalog" / "GRAPH_C3_ARRAYS.npz"), str(C.OUT / "VIEW_B_C3.json")]
    files += sorted(glob.glob("runs/p16/data/dev/labels_v2w*.json")) + sorted(glob.glob("runs/p17/d/ckpt/P17-Dp-*.pt"))
    out = {"version": VERSION, "dev_roots": dev_roots(), "graph_C3_hash": g["hash"], "graph_C3_arrays_sha256": g["arrays_sha256"],
           "files_sha256": {f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files if Path(f).exists()},
           "g3_view_b": {p: {k: v[k] for k in ("success", "n", "reasons")} for p, v in vb["summary"].items()},
           "g3_view_a_calib_auroc": va["edit_auroc"], "g3_forbidden_calls": vb["forbidden_calls"],
           "historical_facts": {"total": "1/12", "blocked_repaired": "0/11", "calib_edit_auroc_D": 0.949}}
    (OUT / "baseline").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "baseline" / "BASELINE.json", out)
    return out


# ------------------------------------------------------------------ G4.1 witness inventory (read-only)
def witnesses(split, k, labels, tags) -> list:
    """Every historically VERIFIED repair of root k: label sequences (singles, ordered pairs) and the tag search plan (<= 4 moves); the
    empty sequence when the original target was VERIFIED. Deterministic order (length, text)."""
    seqs = []
    lab, tag = labels.get(k, {}), tags.get(k, {})
    if lab.get("original", {}).get("status") == "VERIFIED":
        seqs.append([])
    for s, v in lab.get("sequences", {}).items():
        if v["status"] == "VERIFIED":
            seqs.append([[o, int(d)] for o, d in (x.split(">") for x in s.split("."))])
    if tag.get("found"):
        seqs.append([[o, int(d)] for o, d, *_ in tag["steps"]])
    uniq = {json.dumps(s): s for s in seqs}
    return sorted(uniq.values(), key=lambda s: (len(s), json.dumps(s)))


def inventory() -> dict:
    """WITNESS_MANIFEST: cohort A = the fixed 12 DEV roots; cohort B = up to cohort_b TRAIN roots with a verified >= 2-move sequence (fixed
    sha order); transfer pool = TRAIN roots with any verified witness, scanned in root-id order (DEV disjoint by construction)."""
    c = gcfg()
    out = {"version": VERSION, "cohort_A": {}, "cohort_B": {}, "transfer_pool": []}
    L, T = _merged("dev", "labels_v2w"), _merged("dev", "tags_v2w")
    P = _plan("dev")
    for k in dev_roots():
        ws = witnesses("dev", k, L, T)
        out["cohort_A"][k] = {"family": L.get(k, {}).get("family"), "original": L.get(k, {}).get("original", {}).get("status"),
                              "goal_cell": P[k]["goal_cell"], "witnesses": ws, "witness_lengths": [len(s) for s in ws],
                              "teacher_has_verified_repair": any(ws), "source_trajectories_archived": False,
                              "note": "statuses archived; trajectories re-derived offline from the deterministic teacher (G4.2)"}
    Lt, Tt = _merged("train", "labels"), _merged("train", "tags")
    elig = {k: witnesses("train", k, Lt, Tt) for k in sorted(Lt)}
    elig = {k: w for k, w in elig.items() if w}
    assert not set(elig) & set(dev_roots())
    b = sorted((k for k, w in elig.items() if any(len(s) >= 2 for s in w)), key=lambda k: _sha("cohortB", c["seed"], k))[:c["cohort_b"]]
    out["cohort_B"] = {k: {"witnesses": [s for s in elig[k] if len(s) >= 2]} for k in b}
    out["transfer_pool"] = [{"root": k, "witnesses": elig[k]} for k in sorted(elig)[:c["transfer_roots"]]]
    out["disclosure"] = ("Dp17 was trained on splits including DEV (D_TRAIN_SPLITS = train, dev, p17train): DEV results are a catalog / "
                         "library test, not a clean D generalisation test.")
    (OUT / "manifest").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "manifest" / "WITNESS_MANIFEST.json", out)
    return out


# ------------------------------------------------------------------ G4.2 offline reconstruction of teacher witnesses (ledgered)
_IDX = {}


def _free(a) -> bool:
    return not np.asarray(a["held_local"]).size and not any(np.asarray(a["attached"], bool)) and all(str(p) == "pregrasp" for p in a["phase"])


def _cut(a, lo, hi, core=False):
    """Waypoints lo..hi (inclusive) of a stored record, phases / attachment of the segments between them; nothing re-sampled."""
    return {"q": np.asarray(a["q"], float)[lo:hi + 1], "gap": np.asarray(a["gap"], float)[lo:hi + 1], "phase": np.asarray(a["phase"])[lo:hi],
            "attached": np.asarray(a["attached"], bool)[lo:hi], "held_local": np.asarray(a["held_local"]) if core else np.array([]),
            "place_xy": np.asarray(a["place_xy"]) if core else np.array([])}


def _join(parts):
    """Bitwise concatenation of consecutive free-arm legs (each starts exactly where the previous ended; boundary waypoint kept once)."""
    a = parts[0]
    for b in parts[1:]:
        assert np.array_equal(a["q"][-1], b["q"][0])
        a = {"q": np.vstack([a["q"], b["q"][1:]]), "gap": np.concatenate([a["gap"], b["gap"][1:]]), "phase": np.concatenate([a["phase"], b["phase"]]),
             "attached": np.concatenate([a["attached"], b["attached"]]), "held_local": np.array([]), "place_xy": np.array([])}
    return a


def chain_pieces(phys, plan) -> list:
    """A verified teacher plan -> [connector, action, connector, action, ..., connector, T action]; each piece validated in the scene of
    its own stage (certify_free / certify_action, the provider's checkers). Pieces partition the chain exactly at stored waypoints."""
    import ad_compile as ac
    import ordered as od
    cells, recs, i, out, buf = {o.id: o.cell for o in phys.s0.objects}, plan["records"], 0, [], []
    stages = [(st["object"], st["dest"], 2 if st["via"] == "lookup" else 1) for st in plan["steps"]] + [("t0", phys.goal_cell, 1)]
    for o, d, n in stages:
        s = phys.scene(cells, phys.s0.robot.q_rad)
        for a in recs[i:i + n]:
            if _free(a):
                buf.append(_cut(a, 0, len(a["q"]) - 1))
                continue
            ph = [str(x) for x in a["phase"]]
            i0 = next(j for j, x in enumerate(ph) if x != "pregrasp")
            if i0:
                buf.append(_cut(a, 0, i0))
            core = _cut(a, i0, len(a["q"]) - 1, core=True)
            if buf:
                con = _join(buf)
                out.append({"kind": "connector", "arrays": con, "check": ar.certify_free(phys.robot, phys.cfg, s, con), "cells": dict(cells),
                            "swept": sorted(set().union(*map(set, ac.sweep(phys.robot, phys.cfg, con).values())))})
            sw = ac.sweep(phys.robot, phys.cfg, core)
            out.append({"kind": "action", "object": o, "src": cells[o], "dst": d, "radius": phys.s0.get(o).radius_m, "arrays": core,
                        "check": ar.certify_action(phys.robot, phys.cfg, s, o, core), "cells": dict(cells),
                        "swept": sorted(set().union(*(set(sw.get(p, [])) for p in ("approach", "close_attach", "carry", "release", "retreat")))),
                        "travel_J": float(od.joint_travel(phys.robot, [core])["J"] or 0.0)})
            buf = []
        i += n
        cells = {**cells, o: d}
    return out


def _teach_job(item) -> dict:
    """Re-run the historical P16 teacher (same physics, index and label budget) on the listed VERIFIED sequences of one root."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_eval as pe
    import p16_motion as pm
    if "idx" not in _IDX:
        _IDX["idx"] = pl.index_v2()[0]
    c0 = time.process_time()
    P = _plan(item["split"])
    phys = pm.DetPhysics(pc.task_from_root(P[item["root"]], item["root"]), _IDX["idx"], budget=pe.LABEL_BUDGET)
    rows = []
    for seq in item["seqs"]:
        r = pc.verify_sequence(phys, [tuple(x) for x in seq])
        row = {"sequence": seq, "status": r["status"], "failed_step": r["failed_step"]}
        if r["status"] == pm.V:
            row.update(replay=pm.replay(phys, r["plan"]), steps=[{k: s.get(k) for k in ("object", "dest", "via", "transit", "entry")}
                                                                  for s in r["plan"]["steps"]], pieces=chain_pieces(phys, r["plan"]))
        rows.append(row)
    used = dict(phys.used)
    return {**item, "rows": rows, "used": used, "attempts": used["online_moves"] + used["goal_plans"] + used["transit_plans"],
            "cpu_s": time.process_time() - c0, "q0": np.asarray(phys.s0.robot.q_rad, float).tolist(), "goal_cell": phys.goal_cell}


def _ledger():
    f = OUT / "COMPILE_LEDGER.json"
    c = gcfg()
    return rd(f) if f.exists() else {"budget": {"attempts": c["compile_attempts"], "cpu_s": c["compile_cpu_s"]}, "entries": []}


def _spent(led):
    return sum(e["attempts"] for e in led["entries"]), sum(e["cpu_s"] for e in led["entries"])


def _charge(kind, attempts, cpu, note):
    led = _ledger()
    led["entries"].append({"kind": kind, "attempts": attempts, "cpu_s": cpu, "note": note})
    cf.write_json(OUT / "COMPILE_LEDGER.json", led)
    return _spent(led)


def reconstruct(role, items, workers=8, reserve_cpu=0.0) -> dict:
    """Offline G4.2: teacher re-runs in fixed order, charged to the ledger chunk by chunk; stops (BUDGET_REACHED) before a chunk that would
    start beyond the cap. Results -> runs/approach_d/g4/catalogs/<role>_PIECES.npz + .json."""
    done, stop = [], None
    with mp.get_context("spawn").Pool(workers) as pool:
        for j in range(0, len(items), workers):
            a, c = _spent(_ledger())
            b = _ledger()["budget"]
            if a >= b["attempts"] or c >= b["cpu_s"] - reserve_cpu:
                stop = {"at_item": j, "of": len(items), "spent": [a, c], "reserve_cpu": reserve_cpu}
                break
            res = pool.map(_teach_job, items[j:j + workers], chunksize=1)
            _charge(f"teacher_rerun:{role}", sum(r["attempts"] for r in res), sum(r["cpu_s"] for r in res), f"{len(res)} roots")
            done += res
    arrs, meta = {}, []
    for r in done:
        for si, row in enumerate(r["rows"]):
            m = {k: row[k] for k in row if k != "pieces"}
            m["pieces"] = []
            for pi, p in enumerate(row.get("pieces", [])):
                key = f"{r['root']}__s{si}__p{pi}"
                arrs.update({f"{key}__{f}": np.asarray(v) for f, v in p["arrays"].items()})
                m["pieces"].append({**{k: v for k, v in p.items() if k != "arrays"}, "key": key})
            meta.append({"role": role, "split": r["split"], "root": r["root"], "q0": r["q0"], "goal_cell": r["goal_cell"], "attempts": r["attempts"],
                         "cpu_s": r["cpu_s"], "used": r["used"], **m})
    (OUT / "catalogs").mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "catalogs" / f"{role}_PIECES.npz", **arrs)
    cf.write_json(OUT / "catalogs" / f"{role}_PIECES.json", {"role": role, "rows": meta, "stopped": stop, "ledger": _spent(_ledger())})
    return {"role": role, "roots": len(done), "sequences": len(meta), "verified": sum(m["status"] == "VERIFIED" for m in meta),
            "replay_ok": sum(bool((m.get("replay") or {}).get("ok")) for m in meta), "stopped": stop, "ledger": _spent(_ledger())}


def load_pieces(role):
    meta = rd(OUT / "catalogs" / f"{role}_PIECES.json")["rows"]
    z = np.load(OUT / "catalogs" / f"{role}_PIECES.npz")
    arr = collections.defaultdict(dict)
    for k in z.files:
        root, s, p, f = k.split("__")
        arr[f"{root}__{s}__{p}"][f] = z[k]
    return meta, dict(arr)


# ------------------------------------------------------------------ W-TRANSFER: offline home connectors for transfer cores (ledgered)
def _home_job(job):
    import ad_compile as ac
    cfg, robot, p = ac.setup()
    c0 = time.process_time()
    a, term, neg = ac.compile_connector(cfg, robot, p, job["qa"], job["qb"], job["key"])
    return {**job, "arrays": a, "term": term, "neg": neg, "cpu_s": time.process_time() - c0}


def transfer_home_connectors(workers=8) -> dict:
    """Each W-TRANSFER core gets an empty-workspace entry (home -> approach start) and exit (retreat end -> home) connector, compiled
    offline in fixed (root, sequence, piece) order while the ledger allows. These make transfer cores reachable from the stored home hub."""
    import ad_compile as ac
    _, robot, _ = ac.setup()
    home = np.asarray(robot.q_home, float)
    meta, arr = load_pieces("W_TRANSFER")
    jobs, seen = [], set()
    for m in meta:
        for p in m["pieces"]:
            if p["kind"] == "action" and p["check"]["ok"]:
                a = arr[p["key"]]
                for qa, qb, tag in ((home, a["q"][0], "entry"), (a["q"][-1], home, "exit")):
                    k = (ac.qid(qa), ac.qid(qb))
                    if k not in seen:
                        seen.add(k)
                        jobs.append({"qa": np.asarray(qa, float), "qb": np.asarray(qb, float), "key": f"g4/home/{k[0]}>{k[1]}", "tag": tag, "piece": p["key"]})
    outs, stop = [], None
    with mp.get_context("spawn").Pool(workers) as pool:
        for j in range(0, len(jobs), workers):
            a, c = _spent(_ledger())
            b = _ledger()["budget"]
            if a + len(jobs[j:j + workers]) > b["attempts"] or c >= b["cpu_s"]:
                stop = {"at_job": j, "of": len(jobs), "spent": [a, c]}
                break
            res = pool.map(_home_job, jobs[j:j + workers], chunksize=1)
            _charge("transfer_home_connectors", len(res), sum(r["cpu_s"] for r in res), f"{len(res)} connectors")
            outs += res
    ok = [o for o in outs if o["arrays"] is not None]
    np.savez_compressed(OUT / "catalogs" / "W_TRANSFER_HOME.npz", **{f"h{i}__{f}": np.asarray(v) for i, o in enumerate(ok)
                                                                      for f, v in {**o["arrays"], "qa": o["qa"], "qb": o["qb"]}.items()})
    cf.write_json(OUT / "catalogs" / "W_TRANSFER_HOME.json", {"jobs": len(jobs), "run": len(outs), "compiled": len(ok), "stopped": stop,
                                                               "rows": [{"piece": o["piece"], "tag": o["tag"], "compiled": o["arrays"] is not None,
                                                                         "termination": o["term"], "negative_kind": o["neg"]} for o in outs]})
    return {"jobs": len(jobs), "run": len(outs), "compiled": len(ok), "stopped": stop, "ledger": _spent(_ledger())}


# ------------------------------------------------------------------ witness graphs (C3 + pieces), loadable by ad_provider.Graph
def build_wgraph(name, roles, base="C3", home=False) -> dict:
    """GRAPH_<name> = frozen base graph + validated witness pieces of `roles` (+ W-TRANSFER home connectors). Witness actions carry
    origins W_ROOT_WITNESS / W_TRANSFER_WITNESS and their provenance; a piece whose stage-scene check failed is listed as rejected."""
    import ad_compile as ac
    import ad_local as L
    g = rd(L.OUT / "catalog" / f"GRAPH_{base}.json")
    z = np.load(L.OUT / "catalog" / f"GRAPH_{base}_ARRAYS.npz")
    flat = {k: z[k] for k in z.files}
    nodes, actions, conns, rejected = g["nodes"], g["actions"], g["connectors"], list(g["rejected"])

    def node(q, role):
        n = ac.qid(q)
        nodes.setdefault(n, {"q": np.asarray(q, float).tolist(), "roles": [], "gripper": "open", "attached": False})["roles"].append(role)
        return n

    def put(i, a):
        flat.update({f"{i}__{f}": np.asarray(v) for f, v in a.items()})

    added = collections.Counter()
    for role in roles:
        meta, arr = load_pieces(role)
        for m in meta:
            node(m["q0"], f"root_start:{m['root']}")
            prev = None
            for p in m["pieces"]:
                a = arr[p["key"]]
                if not p["check"]["ok"]:
                    rejected.append({"piece": p["key"], "role": role, "check": p["check"]["verdict"]})
                    prev = None
                    continue
                h = hashlib.sha256(np.asarray(a["q"], float).tobytes() + np.asarray(a["gap"], float).tobytes()).hexdigest()[:12]
                prov = {"role": role, "root": m["root"], "split": m["split"], "sequence": m["sequence"], "piece": p["key"]}
                if p["kind"] == "connector":
                    i = f"WC:{h}"
                    if i not in conns:
                        conns[i] = {"from": node(a["q"][0], "witness_leg_start"), "to": node(a["q"][-1], "witness_leg_end"), "origin": ROLE[role],
                                    "rank": 0, "swept": p["swept"], **prov}
                        put(i, a)
                        added[f"{role}:connector"] += 1
                    prev = p
                else:
                    i = f"W:{h}"
                    if i not in actions:
                        actions[i] = {"template": None, "src": p["src"], "dst": p["dst"], "radius": p["radius"], "from": node(a["q"][0], f"approach_start:{i}"),
                                      "to": node(a["q"][-1], f"retreat_end:{i}"), "origins": [ROLE[role]], "modes": [], "family_roots": [],
                                      "swept": p["swept"], "entry_swept": prev["swept"] if prev else [], "travel_J": p["travel_J"],
                                      "provenance": "CORE_OF_TEACHER_WITNESS", "object": p["object"], **prov}
                        put(i, a)
                        added[f"{role}:{'target' if p['object'] == 't0' else 'relocation'}"] += 1
                    prev = None
    if home and (OUT / "catalogs" / "W_TRANSFER_HOME.npz").exists():
        zh = np.load(OUT / "catalogs" / "W_TRANSFER_HOME.npz")
        n = 1 + max((int(k.split("__")[0][1:]) for k in zh.files), default=-1)
        for j in range(n):
            a = {k.split("__")[1]: zh[k] for k in zh.files if k.startswith(f"h{j}__")}
            qa, qb = a.pop("qa"), a.pop("qb")
            i = "WH:" + hashlib.sha256(np.asarray(a["q"], float).tobytes()).hexdigest()[:12]
            conns[i] = {"from": node(qa, "connector_end"), "to": node(qb, "connector_end"), "origin": "W_TRANSFER_HOME_CONNECTOR", "rank": 0}
            put(i, a)
            added["home_connector"] += 1
    meta = {"version": "AD_GRAPH_V1", "g4": VERSION, "base": base, "base_hash": g["hash"], "roles": list(roles), "nodes": nodes, "actions": actions,
            "connectors": conns, "rejected": rejected, "added": dict(added), "arrays_sha256": ac.arrays_hash(flat),
            "hubs": sorted(n for n, v in nodes.items() if any(r == "home" or r.startswith("stratum:") for r in v["roles"]))}
    meta["hash"] = cf.stable_hash({"actions": sorted(actions), "connectors": sorted(conns), "arrays": meta["arrays_sha256"]})
    np.savez_compressed(OUT / "catalogs" / f"GRAPH_{name}_ARRAYS.npz", **flat)
    cf.write_json(OUT / "catalogs" / f"GRAPH_{name}.json", meta)
    return {"name": name, "hash": meta["hash"], "added": dict(added), "actions": len(actions), "connectors": len(conns), "rejected_new": len(rejected) - len(g["rejected"])}


class WitnessFirst:
    """Provider candidate order for G4 catalogs: stored witness cores first (cheapest travel), then the frozen G3 ranker's order. Identical
    for every policy; it orders, it never adds or removes stored actions."""

    def __init__(self, base):
        self.base = base

    def __call__(self, prov, cells, oid, dst, cand):
        A = prov.g.actions
        w = sorted((i for i in cand if any(o.startswith("W_") for o in A[i]["origins"])), key=lambda i: (A[i]["travel_J"], i))
        return list(dict.fromkeys(w + self.base(prov, cells, oid, dst, [i for i in cand if i not in w])))


# ------------------------------------------------------------------ G4.3 motion-availability diagnostic (teacher sequence supplied for DIAGNOSIS only)
CATS = {"C3": None, "W_ROOT": "W_ROOT", "W_TRANSFER": "W_TRANSFER"}


def _graph(cat):
    import ad_local as L
    import ad_provider as pv
    return pv.Graph(L.OUT / "catalog", "GRAPH_C3") if cat == "C3" else pv.Graph(OUT / "catalogs", f"GRAPH_{cat}")


def _prov(st, g, root, policy):
    import ad_g2b as g2
    import ad_provider as pv
    if "ri" not in _IDX:
        _IDX["ri"] = g2._ri()
    ri, member = _IDX["ri"]
    base = g2.Ranker(ri, member, g2._excl(root), **g2.POLICIES["EXACT+REL_6x1+CATALOG"])
    return pv.Precompiled(st.cfg, st.robot, st.s0, st.goal_cell, g, WitnessFirst(base), 6, gcfg()["max_hops"], "OFF", policy)


def _why(r):
    """First-failure class of one provider step (finite library outcome)."""
    rc = r.get("reason_counts") or {}
    if r["status"] == "SUCCESS":
        return None
    if r["reason"] in ("NO_TEMPLATE", "TARGET_TEMPLATE_UNAVAILABLE"):
        return "NO_TEMPLATE"
    if r["reason"] == "NO_COMPATIBLE_Q":
        return "Q_INCOMPATIBLE"
    if r["reason"] == "NO_COMPATIBLE_CONNECTOR":
        return "NO_CONNECTOR_PATH"
    if r["reason"] == "CONNECTOR_COLLISION":
        return "BLOCKED_ENTRY_CONNECTOR"
    if r["reason"] in ("TARGET_ACTION_COLLISION", "COLLISION_CURRENT_SCENE"):
        held = any("held" in str(a.get("pair")) or "t0" == str(a.get("pair", [""])[0]) for a in r["attempts"] if a.get("pair"))
        return ("TARGET_CORE_COLLISION" if r["kind"] == "TARGET" else "RELOCATION_CORE_COLLISION") + (":held/gripper" if held else "")
    if r["reason"] == "CHECK_BUDGET_EXHAUSTED":
        return "BUDGET_EXHAUSTED"
    return r["reason"] or (max(rc, key=rc.get) if rc else "OTHER")


def _diag_job(item):
    import ad_causal as C
    import ad_local as L
    import ad_provider as pv
    import p17_domain as dm
    root, cats, seqs = item
    st = L.Stub(root)
    cells0, q0 = {o.id: o.cell for o in st.s0.objects}, np.asarray(st.s0.robot.q_rad, float)
    cfg = C.ccfg()
    f = dm.slot_fn(st, None, width=cfg["universe_slots"], origin=cells0)
    out = {}
    with ar.forbid("raise") as calls:
        for cat in cats:
            g = _graph(cat)
            prov = _prov(st, g, root, f"G4/diag/{cat}")
            rows = []
            for seq in seqs:
                r = pv.run_sequence(prov, cells0, q0, [tuple(x) for x in seq])
                cells, steps = dict(cells0), []
                for j, s in enumerate(r["log"]):
                    o, d = (seq[j] if j < len(seq) else ("t0", st.goal_cell))
                    in_universe = o == "t0" or d in f(cells, o)[:cfg["universe_slots"]]
                    steps.append({"object": o, "dest": d, "status": s["status"], "why": _why(s), "in_search_universe": in_universe,
                                  "stored_actions": len(g.by_pair.get((cells[o], d), []))})
                    cells = {**cells, o: d}
                tcells = dict(cells0)
                for o, d in seq:
                    tcells[o] = d
                T = g.by_pair.get((tcells["t0"], st.goal_cell), [])
                core_clear = [i for i in T if prov._cert(i, tcells, "t0")["ok"]]
                last_ok = r["status"] == "SUCCESS" or (r["failed_step"] == len(seq))
                rows.append({"sequence": seq, "full_chain": r["status"] == "SUCCESS", "failed_step": r["failed_step"], "reason": r["reason"],
                             "steps": steps, "relocations_available": all(s["status"] == "SUCCESS" for s in steps[:len(seq)]) and len(steps) > len(seq),
                             "target_core_clear": bool(core_clear), "target_actions_stored": len(T), "target_reached_after_relocations": last_ok,
                             "replay": (r.get("replay") or {}).get("status")})
            out[cat] = rows
    return root, out, sum(calls.values())


def diagnose(workers=6) -> dict:
    """Per DEV root x catalog: every archived teacher witness sequence pushed through the provider step by step. catalog_ceiling counts
    roots where SOME declared witness executes end to end (conditional on these witnesses; never a claim about untested repairs)."""
    m = rd(OUT / "manifest" / "WITNESS_MANIFEST.json")["cohort_A"]
    cats = [c for c in CATS if c == "C3" or (OUT / "catalogs" / f"GRAPH_{c}.json").exists()]
    items = [(k, cats, v["witnesses"]) for k, v in m.items() if v["witnesses"]]
    with mp.get_context("spawn").Pool(workers) as pool:
        res = pool.map(_diag_job, items, chunksize=1)
    rows = {k: o for k, o, _ in res}
    blocked = [k for k, v in m.items() if v["original"] != "VERIFIED"]
    summ = {}
    for c in cats:
        first = collections.Counter(next((s["why"] for s in r["steps"] if s["why"]), "REPLAY" if not r["full_chain"] else None)
                                    for k in rows for r in rows[k][c] if not r["full_chain"])
        summ[c] = {"roots_with_witness": len(rows), "catalog_ceiling": sum(any(r["full_chain"] for r in rows[k][c]) for k in rows),
                   "blocked_ceiling": sum(any(r["full_chain"] for r in rows[k][c]) for k in rows if k in blocked),
                   "blocked_with_witness": sum(k in blocked for k in rows),
                   "sequences": sum(len(rows[k][c]) for k in rows), "sequences_full": sum(r["full_chain"] for k in rows for r in rows[k][c]),
                   "first_failure": dict(first.most_common()),
                   "waterfall": {"teacher_witness": sum(len(rows[k][c]) for k in rows),
                                 "relocations_stored_and_certified": sum(r["relocations_available"] or not r["sequence"] for k in rows for r in rows[k][c]),
                                 "target_core_clear": sum(r["target_core_clear"] for k in rows for r in rows[k][c]),
                                 "full_replay": sum(r["full_chain"] for k in rows for r in rows[k][c])},
                   "witness_dest_in_search_universe": sum(all(s["in_search_universe"] for s in r["steps"]) for k in rows for r in rows[k][c])}
    out = {"version": VERSION, "forbidden_calls": sum(x[2] for x in res), "summary": summ, "rows": rows, "blocked_roots": blocked}
    (OUT / "diagnostics").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "diagnostics" / "AVAILABILITY.json", out)
    return {k: v for k, v in out.items() if k != "rows"}


# ------------------------------------------------------------------ G4.5 matched policy evaluation (same roots, catalog, budgets)
def _eval_job(item):
    import ad_causal as C
    import ad_local as L
    import p17_domain as dm
    root, cat, policies = item
    cfg = C.ccfg()
    st = L.Stub(root)
    cells0 = {o.id: o.cell for o in st.s0.objects}
    mv, _ = dm.movers(st.task, cells0)
    f = dm.slot_fn(st, None, width=cfg["universe_slots"], origin=cells0)
    slot_f = lambda cells, o: f(cells, o)[:cfg["universe_slots"]]  # noqa: E731
    g = _graph(cat)
    geo = C.Geo(g, L._catalog_all(), st)
    out = {}
    with ar.forbid("raise") as calls:
        for pol in policies:
            prov = _prov(st, g, root, f"G4/{cat}/{pol}")
            dor = C.DOracle(st, mv, cfg["max_d_calls"]) if pol not in ("GEOM_CAUSAL", "UNIFORM") else None
            c0 = time.process_time()
            r = C.search(pol, prov, st, cells0, st.s0.robot.q_rad, mv, slot_f, geo, dor, cfg, seed=gcfg()["seed"])
            out[pol] = {**r, "cpu_s": time.process_time() - c0}
    return root, out, sum(calls.values())


def evaluate(cat, workers=6) -> dict:
    import ad_causal as C
    pols = C.G4_POLICIES
    with mp.get_context("spawn").Pool(workers) as pool:
        res = pool.map(_eval_job, [(k, cat, pols) for k in dev_roots()], chunksize=1)
    rows = {k: o for k, o, _ in res}
    m = rd(OUT / "manifest" / "WITNESS_MANIFEST.json")["cohort_A"]
    blocked = [k for k in rows if m[k]["original"] != "VERIFIED"]
    av = rd(OUT / "diagnostics" / "AVAILABILITY.json")["rows"] if (OUT / "diagnostics" / "AVAILABILITY.json").exists() else {}
    ceil = [k for k in blocked if any(r["full_chain"] for r in av.get(k, {}).get(cat, []))]

    def cnt(p, ks):
        return sum(rows[k][p]["status"] == "SUCCESS" for k in ks)
    summ = {p: {"success_all": f"{cnt(p, rows)}/{len(rows)}", "success_blocked": f"{cnt(p, blocked)}/{len(blocked)}",
                "success_blocked_within_ceiling": f"{cnt(p, ceil)}/{len(ceil)}",
                "reasons": dict(collections.Counter(rows[k][p]["reason"] for k in rows if rows[k][p]["status"] != "SUCCESS")),
                "reloc_certifications": sum(rows[k][p]["budget"]["reloc"] for k in rows), "expansions": sum(rows[k][p]["budget"]["expand"] for k in rows),
                "d_calls": sum(rows[k][p]["d_calls"] for k in rows), "cpu_s": round(sum(rows[k][p]["cpu_s"] for k in rows), 1),
                "moves_on_success": {k: len(rows[k][p].get("moves") or []) for k in rows if rows[k][p]["status"] == "SUCCESS"}} for p in pols}
    out = {"version": VERSION, "catalog": cat, "config": C.ccfg(), "g4": gcfg(), "policies": list(pols), "forbidden_calls": sum(x[2] for x in res),
           "blocked_roots": blocked, "ceiling_roots": ceil, "summary": summ, "rows": rows}
    (OUT / "eval").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "eval" / f"EVAL_{cat}.json", out)
    return {k: v for k, v in out.items() if k != "rows"}


# ------------------------------------------------------------------ G4.6 figures (real saved records only)
F12, ORD = "p13_2026216000", "p13_2026213000"
CATC = {"C3": "#9a9890", "W_ROOT": "#2a78d6", "W_TRANSFER": "#b0417a"}


def fig_waterfall(plt):
    av = rd(OUT / "diagnostics" / "AVAILABILITY.json")["summary"]
    stages = [("teacher_witness", "archived teacher\nwitness sequences"), ("relocations_stored_and_certified", "every relocation\nstored + certified"),
              ("target_core_clear", "a stored T core\nclear after repair"), ("full_replay", "full chain\nreplayed")]
    fig, (a, b) = plt.subplots(1, 2, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1.6, 1]}, constrained_layout=True)
    w = 0.26
    for j, (c, v) in enumerate(av.items()):
        xs = np.arange(len(stages)) + (j - 1) * w
        ys = [v["waterfall"][k] for k, _ in stages]
        a.bar(xs, ys, w * 0.92, color=CATC[c], label=f"{c}: blocked-root ceiling {v['blocked_ceiling']}/{v['blocked_with_witness']}")
        for x, y in zip(xs, ys):
            a.text(x, y + 0.4, str(y), ha="center", fontsize=8)
    a.set_xticks(range(len(stages)), [t for _, t in stages], fontsize=9)
    a.set_ylabel("DEV witness sequences (n = 30, 11 roots)")
    a.legend(fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)
    a.set_title("(a) Motion coverage of the archived teacher witnesses (sequence supplied for diagnosis only)", loc="left", fontsize=10)
    reasons = sorted({r for v in av.values() for r in v["first_failure"]})
    left = np.zeros(len(av))
    pal = ["#d03b3b", "#e8a33d", "#8a5a00", "#7a52b3", "#1f5fa8", "#4aa3a3", "#555555"]
    for i, r in enumerate(reasons):
        ys = np.array([v["first_failure"].get(r, 0) for v in av.values()])
        b.barh(list(av), ys, left=left, color=pal[i % len(pal)], label=r)
        left += ys
    b.set_xlabel("witness sequences that do NOT execute: first failing stage")
    b.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.45, -0.13), ncol=2, frameon=False)
    b.set_title("(b) Where C3 / W-TRANSFER stop (W-ROOT: none)", loc="left", fontsize=10)
    fig.suptitle("G4 coverage waterfall. W-ROOT is an ENGINEERING CEILING (compiled from each root's own teacher witness); "
                 "W-TRANSFER uses train roots only.", x=0.01, ha="left", fontsize=11)
    return fig


def _setup(root, cat):
    import ad_local as L
    st = L.Stub(root)
    g = _graph(cat)
    return st, g, _prov(st, g, root, "fig")


def fig_replay(plt):
    import ad_provider as pv
    import ad_viz as av
    import viz
    st, g, prov = _setup(ORD, "W_ROOT")
    cells0 = {o.id: o.cell for o in st.s0.objects}
    seq = [("o01", 53), ("o00", 52)]
    with ar.forbid("raise"):
        r = pv.run_sequence(prov, cells0, st.s0.robot.q_rad, seq)
    fig, axs = plt.subplots(1, 5, figsize=(25, 6.2), constrained_layout=True)
    av._base(axs[0], st.robot, st.s0, f"(a) {ORD} (ORD_CHAIN) original clutter; goal cell {st.goal_cell}", (), cells0["t0"], st.goal_cell)
    viz.draw_robot(axs[0], st.robot, st.s0.robot.q_rad, st.robot.open_gap, alpha=0.6, zorder=5)
    cells = av._chain_panels(axs[1:4], st.robot, prov, {"log": r["log"]}, "W-ROOT")
    av._base(axs[4], st.robot, prov.scene(cells), f"(e) final arrangement after independent replay: {r['replay']['status']}", (), None, st.goal_cell)
    viz.draw_robot(axs[4], st.robot, g.q[r['replay']['q_end']] if r['replay'].get('q_end') else st.s0.robot.q_rad, st.robot.open_gap, alpha=0.6, zorder=5)
    fig.suptitle("W-ROOT witness replay from STORED records only (no planner reachable; forbid('raise')). Historical teacher: o01>53 then o00>52 "
                 "VERIFIED, the reverse order certified infeasible. Engineering demonstration — not transfer, not a learned result.",
                 x=0.01, ha="left", fontsize=11)
    return fig


def fig_sweeps(plt):
    import ad_viz as av
    import viz
    fig, axs = plt.subplots(1, 3, figsize=(19, 6.6), constrained_layout=True)
    for ax, cat, d, tag in ((axs[0], "C3", 60, "(a) C3 after G3's choice o00 56->60"), (axs[1], "C3", 59, "(b) C3 after the teacher's o00 56->59"),
                            (axs[2], "W_ROOT", 59, "(c) W-ROOT after o00 56->59")):
        st, g, prov = _setup(F12, cat)
        cells = {**{o.id: o.cell for o in st.s0.objects}, "o00": d}
        T = g.by_pair.get((cells["t0"], st.goal_cell), [])
        cnt = collections.Counter(c for i in T for c in set(g.actions[i]["swept"]) | set(g.actions[i].get("entry_swept", [])))
        s = prov.scene(cells)
        av._base(ax, st.robot, s, "", (), cells["t0"], st.goal_cell)
        for c, n in cnt.items():
            ax.add_patch(plt.Rectangle(((c % 8) * 0.08, (c // 8) * 0.08), 0.08, 0.08, fc="#9ec5f0", ec="none", alpha=0.15 + 0.7 * n / max(1, len(T)), zorder=1))
        with ar.forbid("raise"):
            res = [(i, prov._cert(i, cells, "t0")) for i in T]
            e = prov.edges({o.id: o.cell for o in st.s0.objects}, st.s0.robot.q_rad, "o00", d)
            gl = prov.goal(e["cells"], g.q[e["q_end"]]) if e["status"] == "SUCCESS" else None
        ok = [i for i, v in res if v["ok"]]
        bad = collections.Counter(f"{v['pair']} in {v['phase']}" for i, v in res if not v["ok"])
        if gl and gl["status"] == "SUCCESS":
            av._motion(ax, st.robot, g.arrays[gl["action"]], color="#0ca30c")
        elif ok:
            av._motion(ax, st.robot, g.arrays[ok[0]], color="#e8a33d")
        ax.set_title(f"{tag}: {len(T)} stored T motions, {len(ok)} core-clear in this occupancy\n(shade = how many stored T sweeps cover the cell)",
                     loc="left", fontsize=9.5)
        txt = (f"relocation {e['action'][:10]} {e['status']}; then T from ITS q_end: {gl['status']} {gl['reason'] or ''}\n"
               f"T attempts: {gl.get('reason_counts')}" if gl else f"relocation {e['status']}: {e['reason']}")
        av._tag(ax, txt + ("\ncore collisions: " + "; ".join(f"{k} x{n}" for k, n in bad.most_common(2)) if bad else ""),
                "valid" if gl and gl["status"] == "SUCCESS" else "invalid")
    fig.suptitle(f"F12 ({F12}): per-alternative stored T sweeps (not one canonical sweep). \nOn C3, core-clear T motions exist after either "
                 "placement, but from the relocation's own q_end the T entry connectors collide and the 6-check budget runs out\n(orange = a "
                 "core-clear T core that is never reached). W-ROOT adds the witness's own connector + T core, which certify (green).",
                 x=0.01, ha="left", fontsize=10.5)
    return fig


def fig_counterfactual(plt):
    ev = rd(OUT / "eval" / "EVAL_W_ROOT.json")["rows"][F12]
    fig, axs = plt.subplots(1, 2, figsize=(17, 5.6), constrained_layout=True)
    for ax, pol in zip(axs, ("D_CAUSAL_G3", "D_CAUSAL_G4_SWEEP")):
        r = ev[pol]
        fr = next(t for t in r["trace"] if t["event"] == "frontier")
        cert = {(t["object"], t["dest"], t["action"]): t["status"] for t in r["trace"] if t["event"] == "certify" and not t["moved"]}
        cs = fr["candidates"]
        lab = [f"{c['object']}->{c['dest']} [{c['action'][:8]}]" for c in cs]
        col = ["#d03b3b" if c.get("demoted") else "#1baf7a" for c in cs]
        ax.barh(range(len(cs)), [c.get("p_after", 0) for c in cs], color=col)
        ax.axvline(fr["p_before"], color="#555", ls="--", lw=1)
        ax.text(fr["p_before"], len(cs) - 0.4, f" p_T before = {fr['p_before']:.3f}", fontsize=8)
        for y, c in enumerate(cs):
            st = cert.get((c["object"], c["dest"], c["action"]))
            ax.text(c.get("p_after", 0) + 0.01, y, f"{'rank ' + str(y + 1)}  {'certified: ' + st if st else 'not certified'}"
                    + (f"  t_options {c['t_options'][1]}/{c['t_options'][0]} (DEMOTED)" if c.get("demoted") else ""), va="center", fontsize=7.5)
        ax.set_yticks(range(len(cs)), lab, fontsize=7.5)
        ax.invert_yaxis()
        ax.set_xlim(0, 1.35)
        ax.set_xlabel("D's counterfactual p_T for the ORIGINAL target at the edited occupancy and that motion's q_end")
        ax.set_title(f"{pol}: frontier {fr['frontier']}; outcome {r['status']} "
                     f"(depth {r['depth']}, moves {r.get('moves')})\nreloc certifications {r['budget']['reloc']}, D calls {r['d_calls']}",
                     loc="left", fontsize=9.5)
    fig.suptitle(f"F12 on W-ROOT: D ranks placements by counterfactual feasibility of T at each stored motion's q_end; G4's non-learned rule "
                 "only DEMOTES placements inside every compatible stored T sweep (red; none at this root's first frontier).\nDevelopment "
                 "demonstration: W-ROOT contains this root's own witness.", x=0.01, ha="left", fontsize=10.5)
    return fig


SHORT = {"D_CAUSAL_G3": "D-G3", "D_CAUSAL_G4_SWEEP": "D-G4\nsweep", "D_BLOCKER_ONLY": "D\nblocker", "GEOM_CAUSAL": "geom", "UNIFORM": "uniform"}


def fig_policies(plt):
    import ad_causal as C
    fig, axs = plt.subplots(1, 2, figsize=(18, 6.4), constrained_layout=True, gridspec_kw={"width_ratios": [1.5, 1]})
    E = {c: rd(OUT / "eval" / f"EVAL_{c}.json") for c in ("C3", "W_ROOT") if (OUT / "eval" / f"EVAL_{c}.json").exists()}
    roots = dev_roots()
    pols = list(C.G4_POLICIES)
    ax = axs[0]
    for j, (c, e) in enumerate(E.items()):
        for i, p in enumerate(pols):
            for k, r in enumerate(roots):
                ok = e["rows"][r][p]["status"] == "SUCCESS"
                x = j * (len(pols) + 1) + i
                ax.add_patch(plt.Rectangle((x, k), 0.92, 0.92, fc="#0ca30c" if ok else "#f1d4d4", ec="white"))
                if ok:
                    ax.text(x + 0.46, k + 0.46, str(len(e["rows"][r][p].get("moves") or [])), ha="center", va="center", fontsize=7, color="white")
        ax.text(j * (len(pols) + 1) + len(pols) / 2, -0.8, f"{c}", ha="center", fontsize=10, weight="bold")
    ax.set_xlim(-0.2, len(E) * (len(pols) + 1))
    ax.set_ylim(len(roots), -1.4)
    ax.set_yticks(np.arange(len(roots)) + 0.46, [r + ("  (teacher: direct)" if r in ("p13_2026210004", "p13_2026211000") else
                                                      "  (no known witness)" if r == "p13_2026210001" else "") for r in roots], fontsize=8)
    ax.set_xticks([j * (len(pols) + 1) + i + 0.46 for j in range(len(E)) for i in range(len(pols))],
                  [SHORT[p] for _ in E for p in pols], fontsize=7.5)
    ax.set_title("(a) Root-matched outcomes (green = verified stored repair; number = relocations)", loc="left", fontsize=10)
    ax = axs[1]
    for j, (c, e) in enumerate(E.items()):
        xs = np.arange(len(pols)) + j * 0.4
        ax.bar(xs, [e["summary"][p]["reloc_certifications"] for p in pols], 0.38, color=CATC[c], label=f"{c} relocation certifications")
    ax.set_xticks(np.arange(len(pols)) + 0.2, [SHORT[p] for p in pols], fontsize=8)
    ax.legend(fontsize=8, frameon=False)
    ax.set_title("(b) Physical search effort (identical caps per root)", loc="left", fontsize=10)
    fig.suptitle("Matched policies on identical roots, catalogs and budgets. W-ROOT results are DEVELOPMENT DEMONSTRATIONS (catalog built from "
                 "these roots' witnesses); W-TRANSFER is coverage-censored (0 executable blocked witnesses).", x=0.01, ha="left", fontsize=10.5)
    return fig


def figures() -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    out = []
    for name, fn in (("01_coverage_waterfall", fig_waterfall), ("02_witness_replay", fig_replay), ("03_target_sweeps", fig_sweeps),
                     ("04_D_counterfactual_vs_sweep", fig_counterfactual), ("05_policy_comparison", fig_policies)):
        f = fn(plt)
        f.savefig(FIG / f"{name}.png", dpi=120)
        plt.close(f)
        out.append(str(FIG / f"{name}.png"))
    return out


TRANSFER_SEQS, TRANSFER_RESERVE_CPU = 2, 250.0      # per pool root: first 2 witnesses (fixed order); CPU kept for home connectors


def _items(role):
    m = rd(OUT / "manifest" / "WITNESS_MANIFEST.json")
    if role == "W_ROOT":
        return [{"split": "dev", "root": k, "seqs": v["witnesses"], "role": role} for k, v in m["cohort_A"].items() if v["witnesses"]]
    return [{"split": "train", "root": x["root"], "seqs": x["witnesses"][:TRANSFER_SEQS], "role": role} for x in m["transfer_pool"]]


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1]
    if cmd in ("W_ROOT", "W_TRANSFER"):
        print(json.dumps(reconstruct(cmd, _items(cmd), workers=int(sys.argv[2]) if len(sys.argv) > 2 else 6,
                                     reserve_cpu=TRANSFER_RESERVE_CPU if cmd == "W_TRANSFER" else 0.0), default=str))
    elif cmd == "home":
        print(json.dumps(transfer_home_connectors(), default=str))
    elif cmd == "graphs":
        print(json.dumps([build_wgraph("W_ROOT", ["W_ROOT"]), build_wgraph("W_TRANSFER", ["W_TRANSFER"], home=True)], default=str))
    elif cmd == "diagnose":
        print(json.dumps(diagnose(), default=str))
    elif cmd == "figures":
        print(figures())
    elif cmd == "evaluate":
        print(json.dumps(evaluate(sys.argv[2]), default=str))


def teacher_check(items) -> dict:
    """Offline diagnostic (ledgered): are the placements D preferred on W-ROOT failures teacher-feasible? Same P16 teacher and budget as
    the labels. A VERIFIED answer means D was right and the library lacked the motion; otherwise D's preference was not confirmed."""
    a, c = _spent(_ledger())
    if a >= _ledger()["budget"]["attempts"] or c >= _ledger()["budget"]["cpu_s"]:
        return {"stopped": "BUDGET_REACHED"}
    with mp.get_context("spawn").Pool(min(6, len(items))) as pool:
        res = pool.map(_teach_job, items, chunksize=1)
    _charge("teacher_check:D_preferences", sum(r["attempts"] for r in res), sum(r["cpu_s"] for r in res), f"{len(res)} roots")
    out = {r["root"]: [{"sequence": x["sequence"], "status": x["status"], "failed_step": x["failed_step"]} for x in r["rows"]] for r in res}
    (OUT / "diagnostics").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "diagnostics" / "TEACHER_CHECK_D_PREFERENCES.json", {"rows": out, "ledger": _spent(_ledger())})
    return {"rows": out, "ledger": _spent(_ledger())}
