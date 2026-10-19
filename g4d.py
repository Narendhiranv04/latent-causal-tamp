"""G4D migration checkpoint (Guide v1.8 §3, §8-9): the V1 -> V2 migration manifest, the
scope audit of archived G4A labels, and the frozen sparse G4D evidence plan.

No planner or target evaluator runs here. Legacy positives are re-validated only by
re-certifying their archived trajectories (a compatibility replay); certificates are
transferred by scope rule, never re-mined; unknowns stay unknown. The plan freezes
roots, sequences, interventions, seeds, policies and acceptance before any outcome;
its numerical compute budget is left unset until authorized (no budget is invented).
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np

import cases
import certificates as cert
import config as cf
import data
import effects as ef
import geometry as ge
import interventions as iv
import motion as mo
import ordered as od
import sequences as sq
import teacher
import verify as vf
from scene import scene_from_dict, scene_hash, scene_to_dict

DOCS = {"methodology_v1_6": "latent_causal_tamp_specification_v1_6.pdf",
        "guide_v1_8": "latent_causal_tamp_implementation_guide_v1_8.pdf"}
LEGACY_POLICY = "LEGACY_V1_AUDIT_ORDER_SEARCH_FIRST_RELOCATION_WITNESS"
FIELD_MAP = [  # V1 field/API -> V2 field/API, and what changes in meaning
    ("query.protocol INITIAL_SCENE_ONE_SHOT_V1", "INITIAL_SCENE_ORDERED_ONE_SHOT_V2 + schema_version 1",
     "same learner allowlist and SAFE_RETREAT action context (hash-identical); V2 forbids end_policy None"),
    ("candidate {label, cells}", "proposal {label, sequence=[[id, cell], ...]}; assignment derived (sequences.assignment)",
     "order is part of the proposal; no stay/padding/duplicate entries; empty list = unique no-repair"),
    ("proposals.rank_proposals", "sequences.rank_sequences", "ordered physical-signature dedup; lexicographic V2 rank"),
    ("verify.plan_repair (searches up to max_orders orders)", "verify.plan_fixed_order",
     "exactly the proposed order; V1 search kept for V1 and named baselines"),
    ("evaluate.primary_episode(planner=None)", "ordered.primary_v2 (planner=fixed order) + ordered.episode_audit",
     "witness order must equal the proposed sequence or the episode aborts before COMMIT"),
    ("evaluate.audit_candidate (assignment label)", "ordered.teach_sequence (ordered label)",
     "first relocation witness and its cost stored before the target is examined"),
    ("data.aggregate", "data.ordered_aggregate", "evidence carries scope ORDER / ASSIGNMENT / TRAJECTORY"),
    ("single status field", "static / ordered_feasibility / relocation_attempt / target_attempt / simulation / hardware",
     "separate evidence masks"),
    ("certificate kinds", "certificates.CERTIFICATE_SCOPE (+ ORDER_FIRST_ACTION)", "assignment-wide vs order-specific"),
    ("data.learner_tensors", "data.learner_tensors_v2 (+ robot profile, FK, joint limits, instance masks, anchor)",
     "V1 tensors unchanged"),
    ("(none)", "effects.* scene/robot-start substitutions, omissions, deletion diagnostic, effect records", "new"),
    ("(none)", "ordered.cost_record: first-witness normalized joint travel", "new; legacy traces are not V2 cost labels"),
    ("REOBSERVE event {matches, reasons}", "+ object, commanded/achieved pose, q, gap, attachment, moved history",
     "additive trace fields; V1 decisions unchanged"),
]


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _rd(path: Path):
    return json.loads(path.read_text())


# ------------------------------------------------------------------ legacy label scope audit
def _certified(robot, scene, oid, a, d, e, n) -> bool:
    try:
        return all(v.status == ge.CLEAR for v in mo.certify_trajectory(robot, scene, oid, a, d, e, n))
    except ValueError:                                  # malformed record (e.g. attachment inconsistent): not a witness
        return False


def legacy_positive(cfg, robot, q: dict, tag: str, cells: dict, tasks: dict, scenes: dict, npz) -> dict:
    """Re-validate one archived first-pass witness for its exact recorded order: identity and
    end policy, every relocation certified in its own pre-move scene from the previous
    achieved state (hash-bound), placement at the destination, move-once, and the target
    record starting at the last achieved state and ending in a certified safe retreat."""
    s, act = scene_from_dict(q["scene"]), q["action"]
    v2q = data.make_query(cfg, q["query_id"], s, act["target_id"], q["goal_cell"], {}, "SAFE_RETREAT", data.PROTOCOL_V2)
    rhash, d, e, n = cf.robot_profile_hash(cfg), cfg["suite"]["margin_m"], cfg["geometry"]["numeric_margin_band_m"], \
        cfg["geometry"]["certify_max_evals"]
    arr = lambda t: {k.split("__")[1]: npz[k] for k in npz.files if k.startswith(t + "__")}  # noqa: E731
    ms = sorted((k for k in tasks if k.startswith(tag + ".m")), key=lambda k: int(k.rsplit(".m", 1)[1]))
    if tag + ".target" not in tasks:
        return {"v2_status": data.UNKNOWN, "migration": "WITNESS_NOT_ARCHIVED"}
    chk = {"identity_and_end_policy": v2q["hashes"] == q["hashes"] and v2q["learner"]["action"] == act}
    scene, qs, gap, order, recs = s, np.asarray(s.robot.q_rad), s.robot.gripper_gap_m, [], []
    for m in ms:
        a, oid = arr(m), tasks[m]["target"]
        order.append([oid, cells.get(oid)])
        pre = scene_from_dict(scenes[m])
        c = {"pre_scene": scene_hash(pre) == scene_hash(scene), "certified": _certified(robot, pre, oid, a, d, e, n),
             "hash": mo.trajectory_hash(a, oid, scene_hash(pre), rhash) == tasks[m]["action_hash"],
             "starts_at_achieved": bool(np.array_equal(a["q"][0], qs) and a["gap"][0] == gap),
             "placed": oid in cells and math.dist(a["place_xy"], s.lattice.center(cells[oid])) <= 1e-9,
             "ends_in_retreat": str(a["phase"][-1]) == "retreat" and a["gap"][-1] == robot.open_gap}
        chk[m.rsplit(".", 1)[1]] = {k: bool(v) for k, v in c.items()}
        recs.append(a)
        if oid in cells:
            scene = replace(scene, objects=tuple(replace(o, xy_m=tuple(a["place_xy"]), cell=cells[oid]) if o.id == oid else o
                                                 for o in scene.objects))
        qs, gap = a["q"][-1], float(a["gap"][-1])
    t, pre = arr(tag + ".target"), scene_from_dict(scenes[tag + ".target"])
    w = teacher.check_witness(robot, cfg, pre, vf.RepairState(pre, tuple(qs), gap), act, t)
    chk["target"] = {k: bool(v) for k, v in {**w, "pre_scene": scene_hash(pre) == scene_hash(scene), "hash": mo.trajectory_hash(
        t, act["target_id"], scene_hash(pre), rhash) == tasks[tag + ".target"]["action_hash"]}.items()}
    chk["move_once_and_assignment"] = bool(len({o for o, _ in order}) == len(order) and sq.assignment(order) == cells)
    chk["identity_and_end_policy"] = bool(chk["identity_and_end_policy"])
    ok = all(all(v.values()) if isinstance(v, dict) else v for v in chk.values())
    jt = od.joint_travel(robot, recs)
    return {"recorded_sequence": order, "v2_status": data.POSITIVE if ok else data.UNKNOWN,
            "migration": "VALIDATED_EXACT_RECORDED_ORDER" if ok else "VALIDATION_FAILED", "validation": chk,
            "legacy_cost": {"policy": LEGACY_POLICY, "J": 0.0 if not recs else jt["J"], "per_record": jt["per_record"],
                            "usable_as_v2_cost_label": False,
                            "why": "V1 seed keys and order search differ from the frozen V2 first-witness backend"}}


def legacy_audit(cfg, robot, g4a: Path) -> dict:
    plan, rows = _rd(g4a / "g4a_plan.json"), _rd(g4a / "candidate_labels.json")
    tasks, scenes, npz = _rd(g4a / "result.json")["tasks"], _rd(g4a / "scenes.json"), np.load(g4a / "arrays.npz")
    qs, idx, out = {q["query_id"]: q for q in plan["queries"]}, {}, []
    for r in rows:
        i = idx.get(r["query_id"], 0)
        idx[r["query_id"]] = i + 1
        cells = {o: dd for o, dd in r["signature"]}
        kinds = sorted({c["kind"] for c in r["certificates"] if c["checker_accepted"]})
        row = {"query_id": r["query_id"], "audit_index": i, "assignment": cells, "moved": r["moved"],
               "v1_first_pass": r["first_pass"], "v1_diagnostic_enriched": r["diagnostic_enriched"]}
        if r["first_pass"] == data.POSITIVE:
            row.update(legacy_positive(cfg, robot, qs[r["query_id"]], f"{r['query_id']}.audit{i}", cells, tasks, scenes, npz))
            row["other_orders"] = "UNRESOLVED (a witness labels only its own order)"
        elif r["first_pass"] == data.NEGATIVE:
            wide = [k for k in kinds if cert.CERTIFICATE_SCOPE.get(k) == "ASSIGNMENT"]
            row.update(v2_status=data.NEGATIVE if wide else data.UNKNOWN, certificate_kinds=kinds,
                       migration="ASSIGNMENT_WIDE_TRANSFER_TO_ALL_ORDERS" if wide else "NO_TRANSFERABLE_SCOPE",
                       orders_covered=math.factorial(r["moved"]), premises="archived checker verdict; same observation, "
                       "action context (SAFE_RETREAT = GOAL_AND_SAFE_RETREAT), grasp family and move-once rule")
        else:
            row.update(v2_status=data.UNKNOWN, migration="UNKNOWN_STAYS_UNKNOWN", unknown_reason=r["unknown_reason"])
        out.append(row)
    pos = [r for r in out if r["v1_first_pass"] == data.POSITIVE]
    return {"rows": out, "summary": {
        "assignments": len(out), "v1_first_pass": {k: sum(r["v1_first_pass"] == k for r in out) for k in
                                                   (data.POSITIVE, data.NEGATIVE, data.UNKNOWN)},
        "v2_ordered_positive_exact_order": sum(r["v2_status"] == data.POSITIVE for r in pos),
        "v2_positive_validation_failed": sum(r["v2_status"] != data.POSITIVE for r in pos),
        "v2_zero_move_positive_roots": sorted({r["query_id"] for r in pos if r["v2_status"] == data.POSITIVE and not r["moved"]}),
        "v2_multi_move_positive_sequences": sum(r["v2_status"] == data.POSITIVE and r["moved"] >= 2 for r in pos),
        "v2_negative_assignments_all_orders": sum(r["v2_status"] == data.NEGATIVE for r in out),
        "v2_negative_ordered_sequences_covered": sum(r.get("orders_covered", 0) for r in out if r["v2_status"] == data.NEGATIVE),
        "unknown_assignments": sum(r["v1_first_pass"] == data.UNKNOWN for r in out),
        "v2_cost_labels_from_legacy": 0, "decided_same_endpoint_order_contrasts": 0, "matched_scene_effect_pairs": 0,
        "matched_omission_pairs": 0, "diagnostic_enriched_only_positives_not_migrated": sum(
            r["v1_diagnostic_enriched"] == data.POSITIVE and r["v1_first_pass"] != data.POSITIVE for r in out),
        "g3_5_labels": "NOT_TRANSFERRED: HOME_REQUIRED end policy (report 0007) is a separate historical scope"}}


# ------------------------------------------------------------------ frozen sparse G4D plan
ROOTS = {"R0": "G35_R0_D1REF", "R1": "G35_R1_D1BLOCK", "R2": "G35_R2_GOAL", "R4": "G35_R4_ACCESS", "R5": "G35_R5_D2BLOCK"}
GOALS = {"R0": 45, "R1": 45, "R2": 45, "R4": 28, "R5": 53}
SEQS = {"R0": [[]], "R1": [[]], "R2": [[], [["o03", 60]], [["o03", 38]], [["o01", 21], ["o03", 13]], [["o03", 13], ["o01", 21]],
                                     [["o03", 13]]],
        "R4": [[], [["o01", 18], ["o00", 29]], [["o00", 29], ["o01", 18]], [["o00", 29]], [["o01", 18]]], "R5": [[]]}
ALT_STARTS = [[math.pi / 2, -math.pi / 2, -math.pi / 2], [math.pi / 4, math.pi / 2, math.pi / 2],
              [3 * math.pi / 4, -math.pi / 2, -math.pi / 2]]                # first eligible is used (frozen rule)
CASES = [
    ("D-V2-0", "checked empty-repair target success with exact zero relocation cost",
     {"legacy": ["g4a_r05", "g4a_r10", "g4a_r19"], "units": [("R0", [])]}),
    ("D-V2-1", "mandatory goal occupant plus a checked sufficient repair; original/edited target-only pair at fixed robot",
     {"units": [("R2", []), ("R2", [["o03", 60]]), ("R2", [["o03", 38]])], "scene": [("R2", {"o03": 60}), ("R2", {"o03": 38})]}),
    ("D-V2-2", "identical endpoints, two orders: one complete success and one order-wide certified negative",
     {"units": [("R4", [["o01", 18], ["o00", 29]]), ("R4", [["o00", 29], ["o01", 18]]),
                ("R2", [["o01", 21], ["o03", 13]]), ("R2", [["o03", 13], ["o01", 21]])],
      "contrast": [("R4", [["o01", 18], ["o00", 29]], [["o00", 29], ["o01", 18]]),
                   ("R2", [["o01", 21], ["o03", 13]], [["o03", 13], ["o01", 21]])]}),
    ("D-V2-3", "destination choice changes whether another object must move (occupancy retained)",
     {"units": [("R2", [["o03", 60]]), ("R2", [["o01", 21], ["o03", 13]]), ("R2", [["o03", 13]])]}),
    ("D-V2-4", "joint omission/intervention exposing an interaction singletons do not summarize",
     {"units": [("R4", [["o01", 18], ["o00", 29]]), ("R4", [["o00", 29]]), ("R4", [["o01", 18]]), ("R4", [])],
      "omissions": [("R4", [["o01", 18], ["o00", 29]])], "scene": "R5_BLOCKER_RESTORATIONS"}),
    ("D-V2-5", "complete relocation traces with measured joint travel for >= 2 alternatives vs endpoint distance",
     {"units": [("R2", [["o03", 60]]), ("R2", [["o03", 38]]), ("R4", [["o01", 18], ["o00", 29]])]}),
    ("D-V2-6", "robot-start counterfactual, identical object geometry, independently decided outcome per valid start",
     {"units": [("R1", [])], "starts": ["R1"]}),
]


def _sig(seq) -> str:
    return ".".join(f"{o}>{c}" for o, c in seq) or "empty"


def _r5_restorations(cfg):
    """Frozen rule for D-V2-4's scene interaction: the objects whose pose differs between the
    archived G2_D2 reference and block_ab scenes, restored singly and jointly."""
    _, snaps = iv.load_archived("runs/g2_interventions", "G2_D2")
    ref, blk = snaps["ref"], snaps["block_ab"]
    moved = sorted(o.id for o in blk.objects if o.cell != ref.get(o.id).cell)
    return [{o: ref.get(o).cell} for o in moved] + [{o: ref.get(o).cell for o in moved}]


def _unit(units: dict, k: str, seq: list, cid: str) -> None:
    uid = f"seq:{k}:{_sig(seq)}"
    u = units.setdefault(uid, {"unit": uid, "kind": "ORDERED_TEACHER", "root": k, "sequence": seq, "cases": [],
                               "relocation_key": f"g4d/{k}/{_sig(seq)}/reloc", "target_key": f"g4d/{k}/{_sig(seq)}/target",
                               "relocation_skills_max": len(seq), "target_evaluations_max": 1})
    u["cases"] += [] if cid in u["cases"] else [cid]


def make_plan(cfg, v2, robot, root: Path) -> dict:
    roots, units = {}, {}
    for k, name in ROOTS.items():
        s, prov = cases.build_scene(cfg, _rd(root / "fixtures.json")["fixtures"][name])
        q = data.make_query(cfg, f"g4d_{k}", s, "t0", GOALS[k], {}, "SAFE_RETREAT", data.PROTOCOL_V2)
        pool = sq.rank_sequences(s, q["learner"]["action"], [{"label": _sig(x), "sequence": x} for x in SEQS[k] if x], cfg, v2)
        roots[k] = {"fixture": name, "construction": prov.get("construction"), "scene": scene_to_dict(s),
                    "scene_hash": scene_hash(s), "hashes": q["hashes"], "goal_cell": GOALS[k],
                    "sequences": [{"sequence": x, "validation": sq.validate_sequence(s, q["learner"]["action"], x, 3),
                                   "endpoint_distance": round(sq.endpoint_distance(s, x), 9)} for x in SEQS[k]],
                    "primary_pool_preview": [r["sequence"] for r in pool["ranked"]], "_scene": s, "_q": q}
    for cid, _, spec in CASES:
        for k, seq in spec.get("units", []):
            _unit(units, k, seq, cid)
        scene_edits = spec.get("scene", [])
        if scene_edits == "R5_BLOCKER_RESTORATIONS":
            scene_edits = [("R5", e) for e in _r5_restorations(cfg)]
            _unit(units, "R5", [], cid)
        for k, edit in scene_edits:
            r = roots[k]
            sub = ef.pose_substitution(robot, cfg, r["_scene"], r["_q"]["learner"]["action"], edit)
            uid = f"scene:{k}:{_sig(sorted(edit.items()))}"
            units.setdefault(uid, {"unit": uid, "kind": "SCENE_TARGET_ONLY", "root": k, "edit": edit,
                                   "eligible": sub["eligible"], "eligibility_reasons": sub["reasons"],
                                   "intervened_scene_hash": sub["intervened_scene_hash"],
                                   "reference_unit": f"seq:{k}:empty", "target_key": f"g4d/{k}/scene/{_sig(sorted(edit.items()))}/target",
                                   "relocation_skills_max": 0, "target_evaluations_max": int(sub["eligible"]), "cases": []}
                             )["cases"].append(cid)
        for k in spec.get("starts", []):
            r = roots[k]
            for j, qa in enumerate(ALT_STARTS):
                rs = ef.robot_start_substitution(robot, cfg, r["_scene"], r["_q"]["learner"]["action"], qa)
                if rs["eligible"]:
                    uid = f"start:{k}:{j}"
                    units[uid] = {"unit": uid, "kind": "ROBOT_START_TARGET_ONLY", "root": k, "q_start": rs["q_to"],
                                  "rule": "first eligible of ALT_STARTS", "candidates_skipped": j,
                                  "intervened_scene_hash": rs["intervened_scene_hash"], "reference_unit": f"seq:{k}:empty",
                                  "target_key": f"g4d/{k}/start{j}/target", "relocation_skills_max": 0,
                                  "target_evaluations_max": 1, "cases": [cid]}
                    break
            _unit(units, k, [], cid)
    omissions = {f"{k}:{_sig(s)}": ef.omission_plan(tuple(tuple(a) for a in s), v2)
                 for cid, _, spec in CASES for k, s in spec.get("omissions", [])}
    for v in roots.values():
        del v["_scene"], v["_q"]
    plan = {"stage": "G4D", "protocol": data.PROTOCOL_V2, "schema_version": data.SCHEMA_V2,
            "status": "FROZEN_PENDING_BUDGET_AUTHORIZATION", "documents": {k: _sha(root / f) for k, f in DOCS.items()},
            "config_hash": cf.config_hash(cfg), "config_v2_hash": cf.stable_hash(v2), "robot_profile_hash": cf.robot_profile_hash(cfg),
            "source_hashes": {f: _sha(root / f) for f in ("sequences.py", "ordered.py", "effects.py", "verify.py", "evaluate.py",
                                                         "data.py", "certificates.py", "skill.py", "planner.py", "motion.py",
                                                         "geometry.py", "config_v2.toml", "config.toml", "fixtures.json")},
            "roots": roots, "cases": [{"id": c, "requirement": t, **{k: v for k, v in s.items() if k != "units"},
                                       "units": [f"seq:{k}:{_sig(x)}" for k, x in s.get("units", [])]} for c, t, s in CASES],
            "units": sorted(units.values(), key=lambda u: u["unit"]), "omission_plans": omissions,
            "seeds": {"planner_base": cfg["planner2d"]["seed"], "per_call": "planner.call_seed(base, key/connector label)",
                      "keys": "unit relocation_key / target_key (frozen above)"},
            "policies": {"relocation_backend": vf.FIXED_ORDER_POLICY, "cost": v2["cost"]["policy"],
                         "target_end_policy": "GOAL_AND_SAFE_RETREAT (evaluate.evaluate_safe_retreat); HOME diagnostic only",
                         "target_when_certified": "NOT_RUN (an accepted covering certificate already decides the order)",
                         "skill_budgets": {"relocation": cfg["repair2d"]["skill_plan_failures"],
                                           "target": cfg["skill2d"]["max_plan_failures"],
                                           "planner_max_nodes": cfg["planner2d"]["max_nodes"]},
                         "unknowns": "timeouts, censoring, failed connectors and exhausted search stay UNRESOLVED",
                         "no_root_replacement": True, "no_relaxation": "no collision, tolerance or budget loosening"},
            "execution": {"order": "units in the listed order; one evaluation per unit", "workers": None,
                          "guard": "teacher.guard process-tree CPU guard per unit; censored -> UNRESOLVED",
                          "aggregate_rule": "a unit starts only if spent + per-unit cap <= aggregate cap; else NOT_RUN_BUDGET"},
            "budget": {"per_unit_cpu_s": None, "aggregate_cpu_s": None, "wall_guard_s": None, "cancellation_margin_s": None,
                       "authorization": "REQUIRED: no numerical G4D collection budget has been authorized",
                       "work_upper_bound": {"units": len(units),
                                            "relocation_skills": sum(u["relocation_skills_max"] for u in units.values()),
                                            "target_evaluations": sum(u["target_evaluations_max"] for u in units.values())}},
            "acceptance": {"blocking": ["at least one checked nonempty two-move sequence (complete witness + target)",
                                        "at least one decided same-endpoint order contrast (POSITIVE vs order-scope NEGATIVE)",
                                        "at least one decided, eligible scene-effect pair (both sides decided)",
                                        "at least one decided omission pair (both sides decided)",
                                        "joint continuity and target-start equality on every complete witness"],
                           "per_case": "ATTEMPTED / DECIDED / UNKNOWN / UNAVAILABLE with witnesses or certificates",
                           "failure": "a blocking item not met => G4D BLOCKED; recorded, never retried with a looser plan",
                           "timeouts": "a timeout in the bad order never satisfies the decided-order contrast"}}
    return plan


def reference_costs(root: Path) -> dict:
    """Measured CPU from archived runs, for whoever sets the budget (not a budget)."""
    prim = _rd(root / "runs/g4a_evidence_audit/primary_episodes.json")
    t = _rd(root / "runs/g4a_teacher_budget_diagnostic/teacher_budget_results.json")
    cpu = sorted(p["cpu_s"] for p in prim.values())
    return {"g4a_query_cpu_s": {"n": len(cpu), "median": cpu[len(cpu) // 2], "max": cpu[-1],
                                "scope": "whole G4A query: primary episode + 12-assignment first-pass audit"},
            "followup_target_evaluations": [{k: e.get(k) for k in ("query_id", "tier", "stop", "status", "cpu_s")}
                                            for e in t["evaluations"]],
            "note": "measurements for whoever sets the G4D budget; not a budget"}


# ------------------------------------------------------------------ commands
def cmd_g4d_plan(args) -> int:
    cfg, v2, root = cf.load_config(args.config), cf.load_config_v2(args.config_v2), Path(".")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    plan = make_plan(cfg, v2, ge.make_robot(cfg), root)
    plan["budget"]["reference_measurements"] = reference_costs(root)
    plan["plan_hash"] = cf.stable_hash({k: v for k, v in plan.items() if k != "plan_hash"})
    cf.write_json(out / "g4d_plan.json", plan)
    print(json.dumps({"plan_hash": plan["plan_hash"], "units": len(plan["units"]), "status": plan["status"]}))
    return 0


def cmd_g4d_migrate(args) -> int:
    import g4d_figures
    import time
    cfg, v2, root, out = cf.load_config(args.config), cf.load_config_v2(args.config_v2), Path("."), Path(args.out)
    plan = _rd(out / "g4d_plan.json")
    if cf.stable_hash({k: v for k, v in plan.items() if k != "plan_hash"}) != plan["plan_hash"]:
        raise SystemExit("g4d_plan.json was modified after freezing")
    robot, t0, c0 = ge.make_robot(cfg), time.perf_counter(), time.process_time()
    g4a = root / "runs/g4a_evidence_audit"
    legacy = legacy_audit(cfg, robot, g4a)
    archive = {str(p): _sha(p) for p in sorted((root / "docs/archive").glob("*.pdf"))}
    manifest = {"protocol_from": data.PROTOCOL, "protocol_to": data.PROTOCOL_V2, "schema_version": data.SCHEMA_V2,
                "field_map": [{"v1": a, "v2": b, "meaning": c} for a, b, c in FIELD_MAP],
                "documents": {**{k: {"path": f, "sha256": _sha(root / f)} for k, f in DOCS.items()}, "archived": archive},
                "legacy_sources": {f: _sha(g4a / f) for f in ("g4a_plan.json", "candidate_labels.json", "result.json",
                                                              "scenes.json", "arrays.npz")},
                "label_scope_rules": {
                    "V1 first-pass POSITIVE": "V2 POSITIVE for the exact recorded order only, after validation; other orders UNRESOLVED",
                    "V1 NEGATIVE, ASSIGNMENT-scope certificate": "V2 NEGATIVE for every canonical order of the assignment",
                    "V1 NEGATIVE without such a certificate": "V2 UNRESOLVED",
                    "V1 UNRESOLVED": "V2 UNRESOLVED (no failed-search negatives)",
                    "V1 diagnostic-enriched positives": "not migrated here (separate source; would need the same validation)",
                    "G3.5 HOME_REQUIRED labels": "separate historical scope, not transferred",
                    "legacy relocation traces": "joint travel reported under LEGACY policy; not V2 first-witness cost labels",
                    "scene-effect / omission / order-contrast labels": "none exist in V1 records; require G4D collection"},
                "needs_scope_validation": ["ordered positives (exact state, policy, schema, complete witness replay)",
                                           "assignment-wide negatives (observation, action context, grasp family, move-once)",
                                           "any reuse of G4A roots as V2 benchmark roots (they are V1 development roots)"],
                "config": {"deployment_config_hash": cf.config_hash(cfg), "config_v2_hash": cf.stable_hash(v2)},
                "plan_hash": plan["plan_hash"]}
    cpu, wall = round(time.process_time() - c0, 1), round(time.perf_counter() - t0, 1)
    cf.write_json(out / "migration_manifest.json", manifest)
    cf.write_json(out / "legacy_label_audit.json", {**legacy, "cpu_s": cpu, "wall_s": wall})
    cf.write_json(out / "config_v2.json", {"config_v2_hash": cf.stable_hash(v2), "config_v2": v2})
    g4d_figures.draw_all(out, robot, cfg, v2, plan, legacy)
    cf.write_json(out / "result.json", {"stage": "G4D", "protocol": data.PROTOCOL_V2, "plan_hash": plan["plan_hash"],
                                        "legacy_summary": legacy["summary"], "new_collection": "NONE (budget not authorized)",
                                        "migration_cpu_s": cpu, "migration_wall_s": wall,
                                        "simulation_status": "NOT_RUN", "hardware_status": "NOT_AUTHORIZED",
                                        "learned_components": "NONE"})
    cf.write_manifest(out, {"planner_base": cfg["planner2d"]["seed"]}, cf.config_hash(cfg),
                      {"config_v2_hash": cf.stable_hash(v2), "plan_hash": plan["plan_hash"]})
    print(json.dumps({"out": str(out), **legacy["summary"], "cpu_s": cpu}))
    return 0
