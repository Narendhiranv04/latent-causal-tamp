#!/usr/bin/env python3
"""Read-only, evidence-only order-dependency audit of the FROZEN final 2D (5,000) and 3D (2,500) datasets.

Inputs (never written): the frozen training snapshot (labels actually used for training), the final readiness-gate X/Y manifests (per-order
status / provenance / replay), the 3D replay results, the selection manifests and the raw root records (generator provenance).
Outputs (this directory): DATASET_SUMMARY.json, ORDER_DEPENDENCY_CLASSIFICATION.jsonl, FAILURE_MECHANISM_SUMMARY.json,
MISSING_COUNTERFACTUALS.jsonl, GATES.json.  Deterministic: no clocks, no randomness, sorted iteration.

Evidence model (finalized X protocol = carried robot state from q_ref, ordered relocations, then terminal connector to q_ref):
  an executed order observes, for every step t it reached, the outcome of action a_t in the IDEAL object state S_{set(prefix)} started from the
  ACHIEVED configuration q(prefix).  Step 0 is the only step that starts from q_ref (S_0, q_ref)  -> P1 evidence.
  Two orders reaching the same action with the same predecessor SET but a different predecessor ORDER share the ideal object state and differ
  only in the carried configuration  -> the only controlled (fixed-geometry) contrast available in existing records (K3, step 3).
  No existing record evaluates a step from q_ref in an intermediate state S_P (P non-empty): P2 / P4 need new controlled queries.
    python audit.py            (writes the artifacts; re-running must reproduce byte-identical files)"""
import collections, hashlib, itertools, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = Path(os.environ.get("ABF_SNAPSHOT", "/home/naren/abf_v3_laptop/root/snapshot/abf_9de85710c2a7103f"))
GEN = Path(os.environ.get("FINAL_GEN", "/home/naren/Desktop/boltzmann_lfd/final_dataset_generation"))
MAN = GEN / "FINAL_READINESS_GATE/manifests"
RAW2D = [Path("/home/naren/abf_v3_laptop/root/mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/raw/roots"),
         GEN / "d2/store/roots", GEN / "k3_hard/d2/store", GEN / "k3_hard/d2_gvlab/store"]
RAW3D = [Path("/home/naren/abf_v3_laptop/root/mirror/rss3d_final_src"), GEN, Path("/home/naren/abf_v3_laptop/gen/final3d_v4")]
OC3D = Path("/home/naren/Desktop/boltzmann_lfd/order_classification_3d/3D_ORDER_CLASSIFICATION_PER_SCENE.jsonl")
OC2D = Path("/home/naren/Desktop/boltzmann_lfd/order_classification_2d/per_scene_six_permutation_outcomes.jsonl")
V34_PRIVATE = Path("/home/naren/abf_v34/final/PRIVATE_INDEX.jsonl")           # read ONLY its root ids, to prove exclusion (gate 2)
EXPECT = {"2D": {"n": 5000, "split": {"train": 3500, "val": 751, "test": 749}, "K": {"0": 1250, "1": 800, "2": 800, "3": 1150, "NONE": 1000}},
          "3D": {"n": 2500, "split": {"train": 1766, "val": 364, "test": 370}, "K": {"0": 511, "1": 357, "2": 612, "3": 612, "NONE": 408}}}
FAMILY = {"ORIGINAL_SELECTED": "original", "PUBLISHED_ORIGINAL": "original", "PUBLISHED_RUN_DEPENDENT_K3": "original_run_dependent",
          "GENERATED_V4_K3": "other_v4", "NEW_DEPENDENCE_SEEKING": "dependence_reparking", "NEW_DEPENDENCE_SEEKING_V1": "dependence_reparking",
          "NEW_HARD_ORDER": "hard_order_reparking", "NEW_HARD_ORDER_V3": "hard_order_reparking", "NEW_HARD_ORDER_V4": "hard_order_reparking"}
CERT = "CERTIFIED"                      # failure kinds that carry a teacher certificate (see AUDIT_REPORT.md for what it certifies)


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cert(kind):
    return bool(kind) and kind.startswith(CERT)


def phase_step(ph, K):
    """x_phase -> index of the first failing step (K = connector), None = all succeeded."""
    if ph is None:
        return None
    return K if ph == "connector" else int(ph.split(":")[1])


# ------------------------------------------------------------------ per-order failure kinds (status) from the gate manifests / replays
def status_2d():
    st = {}
    for r in json.load(open(MAN / "2D_FINAL_XY_LABEL_MANIFEST.json"))["rows"]:
        if r["row_kind"] in ("SELECTED_ASSIGNMENT_ORDER", "OMISSION_YNEG"):
            st[(r["root_id"], tuple(tuple(x) for x in r["relocations"]))] = {"x_status": r.get("x_status"), "y_status": r.get("y_status"),
                                                                           "x_replay": r.get("x_replay"), "x_provenance": r["x_provenance"]}
    return st


def status_3d():
    st, rp = {}, {}
    for q in json.load(open(MAN / "3D_REPLAY_RESULTS.json"))["queries"]:
        if q["q"] == "X":
            r = q.get("replay") or {}
            fail = [s.get("failure") for s in r.get("steps", []) if not s.get("ok")]
            con = r.get("connector") or {}
            rp[(q["root_id"], tuple((o, tuple(c)) for o, c in q["order"]))] = {"how": r.get("how"), "step_failure": fail[0] if fail else None,
                                                                               "connector_failure": None if con.get("ok", True) else con.get("failure")}
    leg = legacy_kinds_3d()
    for r in json.load(open(MAN / "3D_FINAL_XY_LABEL_MANIFEST_WITH_REPLAY.json"))["rows"]:
        if r["row_kind"] in ("SELECTED_ASSIGNMENT_ORDER", "OMISSION_YNEG"):
            k = (r["root_id"], tuple((o, tuple(c)) for o, c in r["relocations"]))
            x = rp.get(k, {})
            how = x.get("how")
            # finalized 3D X drops the CERTIFIED / NO_PLAN_FOUND kind (fin3d.py:111); a relocation failure at the SAME step of the same order in the
            # legacy carried-state execution (identical relocation protocol up to that step) supplies it, otherwise the replay class is used.
            fs = None if r["x"] == 1 or r["x_phase"] in (None, "connector") else int(r["x_phase"].split(":")[1])
            lk = leg.get(k)
            if r["x"] == 1:
                kind = None
            elif r["x_phase"] == "connector":
                kind = "CONNECTOR_NO_PLAN"
            elif lk and lk[0] == fs and lk[1]:
                kind = {"CERTIFIED": "CERTIFIED_OBSTRUCTION_LEGACY_SAME_STEP", "NO_PLAN_FOUND": "NO_PLAN_FOUND_LEGACY_SAME_STEP",
                        "OTHER_FAILURE": "EXECUTION_FAILURE_LEGACY_SAME_STEP"}.get(lk[1], "LEGACY_" + str(lk[1]))
            else:
                kind = ("PLANNER_NO_PLAN_RECONFIRMED" if how == "PLANNING_FAILURE_RECONFIRMED" else "EXECUTION_FAILURE" if how == "REPLAYED_EXECUTION_FAILURE"
                        else "UNRESOLVED_KIND_" + r["x_provenance"])
            st[k] = {"x_status": kind, "x_replay": r.get("x_replay"), "x_provenance": r["x_provenance"], "replay": x or None, "legacy": lk}
    return st


def legacy_fallback_2d():
    """Original 2D K2/K3 legacy outcomes for all permutations (order_classification_2d); the snapshot carries legacy_y for only some orders."""
    out = {}
    for rec in jl(OC2D):
        for o in rec.get("permutations", []):
            if o.get("y") in (0, 1):
                out[(rec["root_id"], tuple(tuple(a) for a in o["order"]))] = o["y"]
    return out


def legacy_detail(dom, rid, rec):
    """(order key) -> (legacy y, failed_step, negative_kind) from the root's own permutation records (+ OC2D / fresh-env legacy files)."""
    out = {}
    perms = list(rec.get("permutations") or []) + LEGACY_EXTRA.get((dom, rid), [])
    for o in perms:
        if isinstance(o, dict) and o.get("order"):
            k = tuple((a, tuple(c) if isinstance(c, list) else c) for a, c in o["order"])
            out.setdefault(k, (o.get("y"), o.get("failed_step"), o.get("negative_kind")))
    return out


LEGACY_EXTRA = {}


def load_legacy_extra():
    for rec in jl(OC2D):
        LEGACY_EXTRA.setdefault(("2D", rec["root_id"]), []).extend(rec.get("permutations", []))
    for rec in jl(OC3D):
        LEGACY_EXTRA.setdefault(("3D", rec["root_id"]), []).extend(rec.get("permutations", []))
    for f in ("final3d_v4/work/stage1_legacy.jsonl", "final3d_v4/work/gen_legacy.jsonl"):
        if (GEN / f).exists():
            for rec in jl(GEN / f):
                LEGACY_EXTRA.setdefault(("3D", rec["root_id"]), []).extend(rec["orders"])


def legacy_kinds_3d():
    """(root, order) -> (legacy failed_step, negative_kind) from the fresh-env legacy executions and the raw children's permutations."""
    out = {}
    for f in ("final3d_v4/work/stage1_legacy.jsonl", "final3d_v4/work/gen_legacy.jsonl"):
        p = GEN / f
        if p.exists():
            for rec in jl(p):
                for o in rec["orders"]:
                    out[(rec["root_id"], tuple((a, tuple(c)) for a, c in o["order"]))] = (o.get("failed_step"), o.get("negative_kind"))
    sel = json.load(open(GEN / "FINAL_3D_DATASET_V4/FINAL_3D_SELECTION_MANIFEST.json"))["rows"]
    for s in sel:
        p = next((b / s["path"] for b in RAW3D if (b / s["path"]).exists()), None)
        if p is None or s["K"] not in ("2", "3"):
            continue
        for o in json.loads(p.read_text()).get("permutations") or []:
            if isinstance(o, dict) and o.get("order"):
                out.setdefault((s["root_id"], tuple((a, tuple(c)) for a, c in o["order"])), (o.get("failed_step"), o.get("negative_kind")))
    return out


# ------------------------------------------------------------------ raw records (generator provenance, legacy permutations, annotations)
def raw_index(dom, snap):
    if dom == "2D":
        idx = {}
        for d in RAW2D:
            for p in sorted(d.rglob("*.json")):
                idx.setdefault(p.stem, []).append(p)
        return {rid: next((p for p in idx.get(rid, []) if sha(p) == r["root_sha256"]), None) for rid, r in snap.items()}
    sel = {r["root_id"]: r for r in json.load(open(GEN / "FINAL_3D_DATASET_V4/FINAL_3D_SELECTION_MANIFEST.json"))["rows"]}
    out = {}
    for rid, r in snap.items():
        p = next((b / sel[rid]["path"] for b in RAW3D if (b / sel[rid]["path"]).exists()), None)
        out[rid] = p if p is not None and sha(p) == sel[rid]["root_sha256"] else None
    return out


def provenance(dom, rec):
    c = rec.get("construction") or {}
    return {"method": c.get("method"), "mechanism_intent": c.get("mechanism") or c.get("kind") or (rec.get("spec") or {}).get("mechanism"),
            "path_mechanisms": sorted({p.get("mechanism") for p in c.get("path", []) if isinstance(p, dict) and p.get("mechanism")}),
            "changed_destinations": c.get("changed_destinations") or ([c["changed_destination"]] if c.get("changed_destination") else []),
            "parent_root_id": c.get("parent_root_id") or (rec.get("ids") or {}).get("parent_root_id"),
            "independent_moves": rec.get("independent_moves"), "generator_version": rec.get("generator_version_plus") or (rec.get("ids") or {}).get("generator_version")}


# ------------------------------------------------------------------ per-root evidence and classification
def obs_table(orders, K):
    """{(action, prefix_tuple): (outcome, kind)} for every executed step; plus connector outcomes per full order."""
    t, con = {}, {}
    for o in orders:
        seq, f = tuple(tuple(a) for a in o["seq"]), phase_step(o["x_phase"], len(o["seq"])) if o["x"] == 0 else None
        for i, a in enumerate(seq):
            if f is not None and i > f:
                break
            ok = 0 if (f == i) else 1
            t.setdefault((a, seq[:i]), []).append((ok, o["status"] if ok == 0 else None))
        if len(seq) == K and (f is None or f == len(seq)):
            con[seq] = (1 if o["x"] == 1 else 0, o["status"] if o["x"] == 0 else None)
    return t, con


def classify(r, st, dom, legfb):
    K = int(r["K_legacy"])
    X = r["labels"]["X"]
    sel = []
    for x in X:
        if x["kind"] == "SELECTED_ASSIGNMENT_ORDER":
            k = key(dom, r, x["seq"])
            fb = legfb.get((r["root_id"], k))
            src = "SNAPSHOT" if x["legacy_y"] is not None else "ORDER_CLASSIFICATION_2D_FALLBACK" if fb is not None else "MISSING"
            sel.append(dict(x, status=(st.get((r["root_id"], k)) or {}).get("x_status"), legacy_y=x["legacy_y"] if x["legacy_y"] is not None else fb, legacy_src=src))
    om = [dict(x, status=(st.get((r["root_id"], key(dom, r, x["seq"]))) or {}).get("x_status")) for x in X if x["kind"] == "OMISSION_YNEG"]
    assign = {frozenset(tuple(a) for a in x["seq"]) for x in sel}
    n, xs = len(sel), sum(x["x"] for x in sel)
    leg = [x["legacy_y"] for x in sel]
    legacy_strength = sum(1 for v in leg if v == 1) if all(v in (0, 1) for v in leg) else None
    y_end = r["meta"]["y_selected_endpoint"]
    tab, con = obs_table(sel + om, K)
    acts = sorted({a for x in sel for a in map(tuple, x["seq"])})
    flags, ev = set(), []
    # P1 from step-0 observations (S_0, q_ref): the only reference-configuration evidence in existing records
    p1 = {}
    for a in acts:
        o = tab.get((a, ()), [])
        p1[str(list(a))] = None if not o else int(all(v for v, _ in o)) if len({v for v, _ in o}) == 1 else "INCONSISTENT"
    # fixed-ideal-geometry, different-carried-q contrasts (same action, same predecessor SET, different predecessor ORDER)
    byset = collections.defaultdict(dict)
    for (a, pre), o in tab.items():
        byset[(a, frozenset(pre))][pre] = o
    for (a, P), d in sorted(byset.items(), key=lambda kv: json.dumps([kv[0][0], sorted(kv[0][1])])):
        outs = {pre: o[0] for pre, o in d.items()}
        if len(outs) > 1 and len({v for v, _ in outs.values()}) > 1:
            fails = [(pre, k) for pre, (v, k) in outs.items() if v == 0]
            certified = any(cert(k) for _, k in fails)
            flags.add("CARRIED_STATE_EFFECT_AT_FIXED_IDEAL_GEOMETRY" + ("_CERTIFIED" if certified else "_PLANNER_LIMITED"))
            ev.append({"type": "fixed_geometry_carried_contrast", "action": list(a), "pred_set": sorted(map(list, P)),
                       "outcomes": {json.dumps([list(p) for p in pre]): list(o) for pre, o in sorted(outs.items())}})
    # confounded comparisons: geometry AND carried q both change between the compared observations.  A failure carrying a configuration-
    # INDEPENDENT obstruction certificate (2D CERTIFIED_INFEASIBLE: occupied destination or the pose-only ORDER_FIRST_ACTION grasp screen,
    # LCT/p16_motion.py:129, ordered.py:83-95) holds from q_ref as well, which turns the comparison into a matched object-state comparison
    # at a common configuration -> CONFIRMED.  3D CERTIFIED kinds come from the first IK branch tried (q-dependent order) and are copied from
    # the legacy execution of the same step -> certificate-SUPPORTED only.
    qind = lambda k: dom == "2D" and cert(k)                                          # noqa: E731
    for a in acts:
        s0 = tab.get((a, ()), [])
        later = [(pre, o) for (b, pre), oo in tab.items() if b == a and pre for o in oo]
        if s0 and all(v == 0 for v, _ in s0) and any(o[0] == 1 for _, o in later):
            tier = "CONFIRMED" if all(qind(k) for _, k in s0) else "CERT_SUPPORTED" if all(cert(k) for _, k in s0) else "SUSPECTED"
            flags.add({"CONFIRMED": "GEOMETRIC_ENABLING_CONFIRMED", "CERT_SUPPORTED": "GEOMETRIC_ENABLING_CERT_SUPPORTED"}.get(tier, "SUSPECTED_ENABLING_OR_Q_DEPENDENT"))
            ev.append({"type": "fails_from_S0_qref_succeeds_after_prefix", "tier": tier, "action": list(a), "s0_kinds": sorted({str(k) for _, k in s0}),
                       "succeeds_after": sorted({json.dumps([list(x) for x in pre]) for pre, o in later if o[0] == 1})})
        if s0 and all(v == 1 for v, _ in s0):
            bad = collections.defaultdict(list)
            for pre, o in later:
                bad[frozenset(pre)].append(o)
            for P, oo in sorted(bad.items(), key=lambda kv: json.dumps(sorted(kv[0]))):
                if any(v == 0 for v, _ in oo):
                    f0 = [k for v, k in oo if v == 0]
                    tier = "CONFIRMED" if any(qind(k) for k in f0) else "CERT_SUPPORTED" if any(cert(k) for k in f0) else "SUSPECTED"
                    if tier == "SUSPECTED" and not all(v == 0 for v, _ in oo):
                        continue                                                      # mixed outcome at a fixed set: recorded as carried contrast
                    flags.add({"CONFIRMED": "GEOMETRIC_BLOCKING_CONFIRMED", "CERT_SUPPORTED": "GEOMETRIC_BLOCKING_CERT_SUPPORTED"}.get(
                        tier, "SUSPECTED_BLOCKING_OR_HANDOFF" + ("_MULTI_Q" if len(oo) > 1 else "")))
                    ev.append({"type": "succeeds_from_S0_qref_fails_after_prefix_set", "tier": tier, "action": list(a), "pred_set": sorted(map(list, P)),
                               "n_orderings_observed": len(oo), "kinds": sorted({str(k) for k in f0})})
        if s0 and all(v == 0 for v, _ in s0) and not any(o[0] == 1 for _, o in later):
            flags.add("ACTION_NEVER_SUCCEEDS_IN_RECORDS")
    fails = [x for x in sel if x["x"] == 0]
    fsteps = [phase_step(x["x_phase"], K) for x in fails]
    rel = [x for x, s in zip(fails, fsteps) if s < K]
    if any(s == K for s in fsteps):
        flags.add("CONNECTOR_FAILURE_PRESENT")
    if rel:
        flags.add("RELOCATION_FAILURE_PRESENT")
    # per failing order: is its OWN failure explained by a configuration-independent certificate (geometry at that step)?
    expl = [qind(x["status"]) for x in rel]
    if rel and not all(expl):
        flags.add("UNEXPLAINED_RELOCATION_FAILURES_REMAIN")
    if legacy_strength is not None and legacy_strength != xs:
        flags.add("LEGACY_FINALIZED_STRENGTH_DIFFER")
    if y_end == 0:
        flags.add("SELECTED_ENDPOINT_Y0")
    if any(x["legacy_src"] == "ORDER_CLASSIFICATION_2D_FALLBACK" for x in sel):
        flags.add("SNAPSHOT_LEGACY_Y_INCOMPLETE")
    kinds = sorted({str(x["status"]) for x in fails})
    geo_b, geo_e = "GEOMETRIC_BLOCKING_CONFIRMED" in flags, "GEOMETRIC_ENABLING_CONFIRMED" in flags
    hand_ctrl = any(f.startswith("CARRIED_STATE_EFFECT") for f in flags)
    # primary class: confirmed classes only from configuration-independent certificates; HANDOFF_ONLY / MIXED need P2 + P4 controls that no
    # existing record provides (2D carried contrasts are all planner-limited; 3D certificates are q-dependent) -> never assigned here.
    if n == 0 or len(assign) != 1:
        primary = "UNKNOWN_REQUIRES_CONTROL"
    elif xs == n:
        primary = "LEGACY_TARGET_ONLY" if legacy_strength is not None and legacy_strength < n else "NO_ORDER_CONTRAST"
    elif xs == 0:
        primary = "NO_VERIFIED_SUCCESSFUL_ORDER"
    elif not rel:
        primary = "CONNECTOR_ONLY"
    elif geo_b or geo_e:
        primary = "GEOMETRIC_BLOCKING_CONFIRMED" if geo_b and not geo_e else "GEOMETRIC_ENABLING_CONFIRMED" if geo_e and not geo_b else "GEOMETRIC_BLOCKING_AND_ENABLING_CONFIRMED"
    elif all(not cert(x["status"]) for x in rel) and not hand_ctrl:
        primary = "PLANNER_LIMITED_OR_INCONCLUSIVE"
    else:
        primary = "UNKNOWN_REQUIRES_CONTROL"
    fully = bool(rel) and all(expl) and (geo_b or geo_e)
    return {"root_id": r["root_id"], "domain": dom, "split": r["split"], "K": r["K_legacy"], "source": r["source"], "family": FAMILY[r["source"]],
            "layout_root_id": r["layout_root_id"], "parent_family_id": r["parent_family_id"], "K_status": r["meta"]["K_status"], "flag": r["meta"]["flag"],
            "assignment": sorted(map(list, next(iter(assign)))) if len(assign) == 1 else None, "n_assignments_in_orders": len(assign),
            "n_orders": n, "x_strength_finalized": xs, "x_strength_meta": r["meta"]["x_strength_finalized"], "legacy_strength": legacy_strength,
            "legacy_strength_meta": r["meta"]["legacy_strength"], "y_selected_endpoint": y_end,
            "orders": [{"seq": x["seq"], "x": x["x"], "x_phase": x["x_phase"], "x_status": x["status"], "legacy_y": x["legacy_y"], "legacy_y_source": x["legacy_src"],
                        "x_provenance": x["x_provenance"]} for x in sel],
            "omission_orders": [{"seq": x["seq"], "x": x["x"], "x_phase": x["x_phase"], "x_status": x["status"]} for x in om],
            "P1_step0_from_qref": p1, "P2_intermediate_from_qref": "NOT_OBSERVED_IN_EXISTING_RECORDS" + ("; implied 0 only where a 2D q-independent certificate exists" if dom == "2D" else ""),
            "P4_controlled_contrast": "NOT_AVAILABLE (no step >0 starts from q_ref)", "failure_kinds": kinds, "flags": sorted(flags), "evidence": ev,
            "primary_class": primary, "order_contrast_fully_explained_by_q_independent_geometry": fully,
            "confirmed": {"handoff_only": False, "geometric_enabling": geo_e, "geometric_blocking": geo_b, "mixed": False},
            "unknown_control_requirements": [] if primary in ("NO_ORDER_CONTRAST", "LEGACY_TARGET_ONLY", "NO_VERIFIED_SUCCESSFUL_ORDER") or fully else
            ["P2: F(a|S_P,q_ref) for all actions and non-empty predecessor subsets", "P4: same step from q_ref vs q_achieved at identical S_P"]
            + (["connector from q_achieved vs q_ref reachability"] if "CONNECTOR_FAILURE_PRESENT" in flags else [])}


def key(dom, r, seq):
    ids = r["inputs"]["ids"]
    if dom == "2D":
        return tuple((ids[i], c) for i, c in seq)
    g = r["inputs"]["grid"]
    return tuple((ids[i], (c // g[1], c % g[1])) for i, c in seq)


def missing(rec, snap_r, dom):
    """Controlled queries absent from existing records: F(a | S_P, q_ref) for every action and every NON-EMPTY predecessor subset (P = {} is
    already observed at step 0), plus F(a | S_P, q(prefix)) for every carried prefix never executed (orders stopped before it).  Keyed for
    deduplication by (layout, ideal object state, action)."""
    out, acts = [], [tuple(a) for a in rec["assignment"]]
    tab, _ = obs_table([dict(o, status=o["x_status"]) for o in rec["orders"]] + [dict(o, status=o["x_status"]) for o in rec["omission_orders"]], int(rec["K"]))
    implied = {(a, frozenset(pre)) for (a, pre), oo in tab.items() if dom == "2D" and any(v == 0 and cert(k) for v, k in oo)}   # q-independent 0
    for a in acts:
        others = [b for b in acts if b != a]
        for k in range(1, len(others) + 1):
            for P in itertools.combinations(others, k):
                if (a, frozenset(P)) in implied:
                    continue
                st = sorted(map(list, P))
                out.append({"query": "REF", "root_id": rec["root_id"], "domain": dom, "split": rec["split"], "action": list(a), "pred_set": st,
                            "start": "q_ref", "dedup_key": hashlib.sha256(json.dumps([rec["layout_root_id"], snap_r["root_sha256"], st, list(a)]).encode()).hexdigest()[:24]})
        for k in range(1, len(others) + 1):
            for pre in itertools.permutations(others, k):
                if (a, pre) not in tab:
                    out.append({"query": "CARRIED", "root_id": rec["root_id"], "domain": dom, "split": rec["split"], "action": list(a),
                                "prefix": [list(p) for p in pre], "start": "q_achieved(prefix)",
                                "dedup_key": hashlib.sha256(json.dumps([rec["layout_root_id"], snap_r["root_sha256"], [list(p) for p in pre], list(a)]).encode()).hexdigest()[:24]})
    return out


def main():
    gates, summary, fms, rows, miss = {}, {}, {}, [], []
    v34 = {json.loads(l)["root_id"] for l in open(V34_PRIVATE)} if V34_PRIVATE.exists() else set()
    load_legacy_extra()
    lock = json.load(open(SNAP / "data_snapshot.lock.json"))
    for dom in ("2D", "3D"):
        snap = {r["root_id"]: r for r in jl(SNAP / f"data{dom.lower()}.jsonl")}
        st = status_2d() if dom == "2D" else status_3d()
        raw = raw_index(dom, snap)
        legfb = legacy_fallback_2d() if dom == "2D" else {}
        E = EXPECT[dom]
        cnt = lambda f: dict(sorted(collections.Counter(str(f(r)) for r in snap.values() if f(r) is not None).items()))  # noqa: E731
        g = {"1_counts": len(snap) == E["n"] and cnt(lambda r: r["split"]) == dict(sorted(E["split"].items())) and cnt(lambda r: r["K_legacy"]) == dict(sorted(E["K"].items())),
             "2_no_v34_root": not (set(snap) & v34) and bool(v34), "raw_records_resolved_sha_ok": sum(p is not None for p in raw.values()) == len(snap)}
        fam_split = collections.defaultdict(set)
        for r in snap.values():
            fam_split[r["parent_family_id"]].add(r["split"])
        g["family_split_leakage_none"] = all(len(s) == 1 for s in fam_split.values())
        dr = []
        for rid in sorted(snap):
            r = snap[rid]
            if r["K_legacy"] not in ("2", "3"):
                continue
            c = classify(r, st, dom, legfb)
            rec = json.loads(Path(raw[rid]).read_text()) if raw[rid] else {}
            c["provenance"] = provenance(dom, rec)
            ld = legacy_detail(dom, rid, rec)
            for o in c["orders"]:
                d = ld.get(key(dom, r, o["seq"]))
                o["legacy_failed_step"], o["legacy_negative_kind"] = (d[1], d[2]) if d else ("NOT_FOUND", None)
            c["raw_record"] = str(raw[rid]) if raw[rid] else None
            c["inherited_independent_moves_after_destination_change"] = bool(c["provenance"]["independent_moves"]) and bool(c["provenance"]["changed_destinations"])
            dr.append(c)
            if c["unknown_control_requirements"]:
                miss += missing(c, r, dom)
        rows += dr
        nK = {"2": 2, "3": 6}
        g["3_orders_share_one_assignment"] = all(c["n_assignments_in_orders"] == 1 for c in dr)
        g["3b_orders_complete_permutations"] = all(c["n_orders"] == nK[c["K"]] for c in dr)
        g["4_finalized_x_strength_matches_meta"] = all(c["x_strength_finalized"] == c["x_strength_meta"] for c in dr)
        g["4b_legacy_strength_matches_meta_after_fallback"] = all(c["legacy_strength"] == c["legacy_strength_meta"] for c in dr if c["legacy_strength_meta"] is not None)
        g["4c_snapshot_per_order_legacy_y_complete(EXCEPTION_IF_FALSE)"] = not any("SNAPSHOT_LEGACY_Y_INCOMPLETE" in c["flags"] for c in dr)
        g["4d_failure_kind_resolved_for_every_relocation_failure"] = all(o["x_status"] is not None for c in dr for o in c["orders"] if o["x"] == 0)
        yshare = True
        for r in snap.values():
            ys = collections.defaultdict(set)
            for y in r["labels"]["Y"]:
                ys[json.dumps(sorted(map(list, y["edit"])))].add(y["y"])
            yshare &= all(len(v) == 1 for v in ys.values())
        g["5_y_shared_per_endpoint"] = yshare
        g["6_x_provenance_present"] = all(o["x_provenance"] for c in dr for o in c["orders"])
        g["7_no_binary_failure_promoted_to_certified"] = all(any(e["tier"] == "CONFIRMED" for e in c["evidence"] if "tier" in e) or
                                                             not (c["confirmed"]["geometric_blocking"] or c["confirmed"]["geometric_enabling"]) for c in dr) and \
            (dom == "2D" or not any(c["confirmed"]["geometric_blocking"] or c["confirmed"]["geometric_enabling"] for c in dr))
        g["8_no_handoff_from_later_failure_alone"] = all(not c["confirmed"]["handoff_only"] for c in dr)
        g["9_no_geometric_without_matched_comparison"] = all(not (c["confirmed"]["geometric_blocking"] or c["confirmed"]["geometric_enabling"]) or
                                                             any(e.get("tier") == "CONFIRMED" for e in c["evidence"]) for c in dr)
        g["13_snapshot_files_unchanged_vs_lock"] = sha(SNAP / f"data{dom.lower()}.jsonl") == lock["files"][f"data{dom.lower()}.jsonl"]
        g["13b_selection_manifest_unchanged_vs_lock"] = sha(GEN / ("k3_hard/2D_K3_STRENGTH_SELECTION_V3.json" if dom == "2D" else "FINAL_3D_DATASET_V4/FINAL_3D_SELECTION_MANIFEST.json")) == lock[f"selection_{dom.lower()}"]["sha256"]
        g["14_evidence_references_resolve"] = all(c["raw_record"] and Path(c["raw_record"]).exists() for c in dr) and \
            all(o["legacy_failed_step"] != "NOT_FOUND" for c in dr for o in c["orders"] if o["legacy_y"] in (0, 1))
        gates[dom] = g
        # ---------------- summaries
        S = {"n_roots": len(snap), "by_split_K": {s: cnt(lambda r: r["K_legacy"] if r["split"] == s else None) for s in ("train", "val", "test")},
             "by_source_K": dict(sorted(collections.Counter(f"{r['source']}|{r['K_legacy']}" for r in snap.values()).items())),
             "K_status": dict(sorted(collections.Counter(f"{r['K_legacy']}|{r['meta']['K_status']}" for r in snap.values()).items())),
             "flags": dict(sorted(collections.Counter(str(r["meta"]["flag"]) for r in snap.values()).items())),
             "n_X_labels": sum(len(r["labels"]["X"]) for r in snap.values()), "n_Y_labels": sum(len(r["labels"]["Y"]) for r in snap.values()),
             "x_kinds": dict(sorted(collections.Counter(x["kind"] for r in snap.values() for x in r["labels"]["X"]).items())),
             "family_split_leakage_none": g["family_split_leakage_none"], "snapshot_files_sha256": {f: sha(SNAP / f) for f in (f"data{dom.lower()}.jsonl",)}}
        strength = {}
        for K in ("2", "3"):
            for sp in ("train", "val", "test", "all"):
                cs = [c for c in dr if c["K"] == K and (sp == "all" or c["split"] == sp)]
                strength[f"K{K}|{sp}"] = {"finalized_x": dict(sorted(collections.Counter(f"{c['x_strength_finalized']}/{c['n_orders']}" for c in cs).items())),
                                          "legacy": dict(sorted(collections.Counter(f"{c['legacy_strength']}/{c['n_orders']}" for c in cs).items())),
                                          "selected_endpoint_y0": sum(c["y_selected_endpoint"] == 0 for c in cs), "n": len(cs)}
        S["order_strength"] = strength
        cls = {}
        for K in ("2", "3", "all"):
            for sp in ("train", "val", "test", "all"):
                cs = [c for c in dr if (K == "all" or c["K"] == K) and (sp == "all" or c["split"] == sp)]
                cls[f"K{K}|{sp}"] = {"n": len(cs), "primary": dict(sorted(collections.Counter(c["primary_class"] for c in cs).items())),
                                     "flags": dict(sorted(collections.Counter(f for c in cs for f in c["flags"]).items()))}
        S["classification"] = cls
        S["by_family"] = {f: {"n": len(cs), "primary": dict(sorted(collections.Counter(c["primary_class"] for c in cs).items())),
                              "flags": dict(sorted(collections.Counter(x for c in cs for x in c["flags"]).items())),
                              "x_strength": dict(sorted(collections.Counter(f"K{c['K']}:{c['x_strength_finalized']}/{c['n_orders']}" for c in cs).items())),
                              "mechanism_intent": dict(sorted(collections.Counter(str(c["provenance"]["mechanism_intent"]) for c in cs).items())),
                              "path_mechanisms": dict(sorted(collections.Counter(m.split(":")[0] for c in cs for m in c["provenance"]["path_mechanisms"]).items())),
                              "independent_moves_annotation": dict(sorted(collections.Counter(str(c["provenance"]["independent_moves"]) for c in cs).items())),
                              "inherited_independent_moves_after_destination_change": sum(c["inherited_independent_moves_after_destination_change"] for c in cs)}
                       for f in sorted({c["family"] for c in dr}) for cs in [[c for c in dr if c["family"] == f]]}
        summary[dom] = S
        # ---------------- failure mechanisms (observed location vs kind; nothing here is a proven cause)
        F = collections.Counter()
        for c in dr:
            K = int(c["K"])
            for o in c["orders"]:
                s = phase_step(o["x_phase"], K) if o["x"] == 0 else None
                loc = "x_success" if s is None else "first_relocation" if s == 0 else "terminal_connector" if s == K else "later_relocation"
                F[f"finalized_x|{loc}|{o['x_status']}"] += 1
                lf = o["legacy_failed_step"]
                lloc = "legacy_success" if o["legacy_y"] == 1 else "legacy_missing" if o["legacy_y"] is None else "legacy_original_target_step" if lf == "target" \
                    else "legacy_first_relocation" if lf == 0 else "legacy_later_relocation" if isinstance(lf, int) else f"legacy_other:{lf}"
                F[f"legacy|{lloc}|{o['legacy_negative_kind']}"] += 1
                if lloc == "legacy_original_target_step":
                    F[f"legacy_target_failure_vs_finalized|x={o['x']}|y_end={c['y_selected_endpoint']}"] += 1
        fms[dom] = {"order_level_counts": dict(sorted(F.items())), "note": "location = first failing phase of the finalized-X execution; kinds are teacher "
                    "statuses, not causes. 2D CERTIFIED_INFEASIBLE / UNKNOWN_PLANNER / UNKNOWN_TRANSIT from the gate manifest; 3D from the replay audit "
                    "(PLANNING_FAILURE_RECONFIRMED / EXECUTION / CONNECTOR) or UNREPLAYED_<provenance>."}
    # ---------------- write
    w = lambda name, obj: (HERE / name).write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")  # noqa: E731
    with open(HERE / "ORDER_DEPENDENCY_CLASSIFICATION.jsonl", "w") as f:
        for c in rows:
            f.write(json.dumps(c, sort_keys=True) + "\n")
    seen, uniq = set(), []
    for m in miss:
        if m["dedup_key"] not in seen:
            seen.add(m["dedup_key"])
            uniq.append(m)
    with open(HERE / "MISSING_COUNTERFACTUALS.jsonl", "w") as f:
        for m in uniq:
            f.write(json.dumps(m, sort_keys=True) + "\n")
    summary["missing_counterfactuals"] = {d: dict(sorted(collections.Counter(f"{m['query']}|K{len(m.get('pred_set', m.get('prefix', [])))}" for m in uniq if m["domain"] == d).items()))
                                          for d in ("2D", "3D")}
    # gate 10: per-scene classification consistent with aggregated counts
    for dom in ("2D", "3D"):
        gates[dom]["10_counts_consistent"] = sum(summary[dom]["classification"]["Kall|all"]["primary"].values()) == sum(1 for c in rows if c["domain"] == dom)
    # smallest representative pilot: TRAIN only, per domain 8 K3 + 4 K2 roots per family among roots that need controls, chosen by sha256(root_id)
    need = {c["root_id"] for c in rows if c["unknown_control_requirements"]}
    pick = []
    for dom in ("2D", "3D"):
        for fam in sorted({c["family"] for c in rows if c["domain"] == dom}):
            for K, n in (("3", 8), ("2", 4)):
                cs = sorted((c for c in rows if c["domain"] == dom and c["family"] == fam and c["K"] == K and c["split"] == "train" and c["root_id"] in need),
                            key=lambda c: hashlib.sha256(c["root_id"].encode()).hexdigest())
                pick += [c["root_id"] for c in cs[:n]]
    pq = [m for m in uniq if m["root_id"] in set(pick)]
    with open(HERE / "PILOT_QUERIES.jsonl", "w") as f:
        for m in pq:
            f.write(json.dumps(m, sort_keys=True) + "\n")
    summary["pilot"] = {"roots": sorted(pick), "n_roots": len(pick), "n_queries": dict(sorted(collections.Counter(f"{m['domain']}|{m['query']}" for m in pq).items()))}
    summary["roots_needing_controls"] = dict(sorted(collections.Counter(c["domain"] + "|" + c["split"] for c in rows if c["root_id"] in need).items()))
    w("DATASET_SUMMARY.json", summary)
    w("FAILURE_MECHANISM_SUMMARY.json", fms)
    w("GATES.json", gates)
    print(json.dumps(gates, indent=1))


if __name__ == "__main__":
    main()
