"""Approach D G2a: inference-side contract for OFFLINE-compiled motion templates (approachD_G2_offline_only_instructions_v1_1 §1-§2.3).

Allowed here: occupancy tests, forward kinematics and the exact continuous certifier applied to a STORED, FROZEN joint trajectory. Nothing
in this module generates, adapts, retargets or plans a motion (no IK, no planner, no online connector, no grasp synthesis). `forbid`
replaces every inference-forbidden entry point found by the G2a audit with a raiser (or a counter, for auditing historical code); the
tests run every runtime path under it. A missing or rejected template is a finite-library FAILURE with a reason code: never a third truth
label, never a geometric impossibility claim, and never rescued by an online planner."""
from __future__ import annotations

import collections
import contextlib
import importlib
import sys

import numpy as np

import geometry as ge
import motion as mo

VERSION = "AD_RUNTIME_V1"
SUCCESS, FAILURE = "SUCCESS", "FAILURE"
REASONS = ("NO_TEMPLATE", "DEST_OCCUPIED", "FOOTPRINT_MISMATCH", "NO_COMPATIBLE_START", "COLLISION_ALL_CHECKED", "NOT_CLEAR_ALL_CHECKED",
           "CHECK_BUDGET_EXHAUSTED")
# Inference-forbidden entry points (module -> attribute, 'Class.method' for methods). Leaves: every IK solver, IK-tracked line, RRT and
# connector planner, grasp screen and online skill planner; the remaining rows are the historical composites that reach those leaves
# (named so a trace attributes the call). Audit: static grep + dynamic trace (ad_compile.audit_runtime_paths, RUNTIME_PATH_AUDIT.json).
FORBIDDEN = {"geometry": ("ik",), "sector_check": ("_ik",), "motion": ("ik_track", "ik_line", "carry_line"),
             "planner": ("plan", "_rrt_connect"),
             "skill": ("plan_skill", "screen_pick", "screen_place", "pick_certificate", "_ik"),
             "ordered": ("certificates_for", "first_screen"), "p15_retarget": ("certified", "probe"), "sector_cert": ("produce",),
             "p6_scenes": ("Screens.pick", "Screens.place"), "p14_d_search": ("_transit",),
             "p15_search": ("Physics._goal", "Physics._edges"), "p16_motion": ("DetPhysics._goal", "DetPhysics._edges", "DetPhysics._transit")}
LEAVES = ("geometry.ik", "sector_check._ik", "motion.ik_track", "motion.ik_line", "motion.carry_line", "planner.plan", "planner._rrt_connect",
          "skill.plan_skill", "skill.screen_pick", "skill.screen_place")
IK_ENTRIES = {"geometry.ik", "sector_check._ik", "motion.ik_track", "motion.ik_line", "motion.carry_line", "skill._ik", "skill.screen_pick",
              "skill.screen_place", "skill.pick_certificate", "ordered.first_screen", "p6_scenes.Screens.pick", "p6_scenes.Screens.place"}


class ForbiddenCall(RuntimeError):
    pass


@contextlib.contextmanager
def forbid(mode="raise"):
    """Patch every FORBIDDEN entry point; mode 'raise' (runtime guard) or 'count' (audit of historical code: calls + first caller)."""
    calls, saved = collections.Counter(), []

    def wrap(name, fn):
        def g(*a, **k):
            f = sys._getframe(1)
            calls[name] += 1
            calls[f"{name} <- {f.f_globals.get('__name__')}.{f.f_code.co_name}"] += 1
            if mode == "raise":
                raise ForbiddenCall(f"{name} reached at inference")
            return fn(*a, **k)
        return g

    try:
        for mod, names in FORBIDDEN.items():
            m = importlib.import_module(mod)
            for n in names:
                owner, attr = (getattr(m, n.split(".")[0]), n.split(".")[1]) if "." in n else (m, n)
                saved.append((owner, attr, owner.__dict__.get(attr)))          # None: inherited method, patched on this class only
                setattr(owner, attr, wrap(f"{mod}.{n}", getattr(owner, attr)))
        yield calls
    finally:
        for owner, attr, fn in reversed(saved):
            setattr(owner, attr, fn) if fn is not None else delattr(owner, attr)


def _params(cfg):
    return cfg["suite"]["margin_m"], cfg["geometry"]["numeric_margin_band_m"], cfg["geometry"]["certify_max_evals"]


def check_entry(robot, cfg, scene, q, tpl) -> dict:
    """Precompiled ENTRY template (root start q -> home, nothing held): exact start match, then every stored segment certified in scene."""
    if np.max(np.abs(np.asarray(q, float) - tpl["q_start"])) > tpl.get("start_tol", 1e-9):
        return {"status": FAILURE, "reason": "NO_COMPATIBLE_START", "checks": 0}
    delta, eps, evals = _params(cfg)
    ck, a = ge.Checker(robot, ge.make_world(scene), delta, eps), tpl["arrays"]
    for i in range(len(a["q"]) - 1):
        v = ge.certify(ck, a["q"][i], a["q"][i + 1], a["gap"][i], a["gap"][i + 1], evals)
        if v.status != ge.CLEAR:
            return {"status": FAILURE, "reason": "COLLISION_ALL_CHECKED" if v.status == ge.COLLISION else "NOT_CLEAR_ALL_CHECKED",
                    "checks": 1, "first": {"segment": i, "verdict": v.status, "pair": v.pair}}
    return {"status": SUCCESS, "reason": None, "checks": 1, "template_id": tpl["id"], "q_end": tpl["q_end"]}


def certify_free(robot, cfg, scene, a) -> dict:
    """G2b: a stored free-arm leg or connector (open gripper, nothing held): record consistency (limits, gap, no attachment), then every
    stored segment certified against every object at rest in `scene`. -> {'ok', 'verdict', 'pair', 'segment'}."""
    q, gap = np.asarray(a["q"], float), np.asarray(a["gap"], float)
    if any(np.asarray(a["attached"], bool)) or not all(ge.within_limits(robot, w) for w in q) or np.any(gap < 0) or \
            np.any(gap > robot.open_gap + 1e-9):
        return {"ok": False, "verdict": "RECORD_INVALID", "pair": None, "segment": None}
    delta, eps, evals = _params(cfg)
    ck = ge.Checker(robot, ge.make_world(scene), delta, eps)
    for i in range(len(q) - 1):
        v = ge.certify(ck, q[i], q[i + 1], gap[i], gap[i + 1], evals)
        if v.status != ge.CLEAR:
            return {"ok": False, "verdict": v.status, "pair": v.pair, "segment": i}
    return {"ok": True, "verdict": ge.CLEAR, "pair": None, "segment": None}


def certify_action(robot, cfg, scene, oid, a) -> dict:
    """G2b: a stored object action (approach .. retreat, or any full template) in `scene` with `oid` resting at the action's pick pose:
    motion.check_record (phases, attachment, held offset, pick and place consistency) then every stored segment in its phase context."""
    delta, eps, evals = _params(cfg)
    try:
        vs = mo.certify_trajectory(robot, scene, oid, a, delta, eps, evals)
    except ValueError as e:
        return {"ok": False, "verdict": "RECORD_INVALID", "pair": str(e), "segment": None, "phase": None}
    bad = next(((i, v) for i, v in enumerate(vs) if v.status != ge.CLEAR), None)
    if bad is None:
        return {"ok": True, "verdict": ge.CLEAR, "pair": None, "segment": None, "phase": None}
    return {"ok": False, "verdict": bad[1].status, "pair": bad[1].pair, "segment": bad[0], "phase": str(a["phase"][bad[0]])}


def check(robot, cfg, scene, oid, dst, q, templates, budget, prefilter=True) -> dict:
    """First-valid selection over an ordered list of compiled templates for 'oid -> dst' from the robot's actual q. Order: occupancy and
    footprint, exact start-q continuity, conservative swept-cell prefilter (may reject valid templates, never accepts one), then the exact
    continuous certifier on the frozen record in the current scene (decisive). `budget` caps exact certifications. Returns SUCCESS with the
    template, or FAILURE with one reason code and every rejection."""
    o = scene.get(oid)
    occ = {x.cell for x in scene.objects if x.id != oid}
    out = {"status": FAILURE, "reason": None, "checks": 0, "prefiltered": 0, "rejected": [], "template_id": None, "q_end": None}
    if dst in occ:
        return {**out, "reason": "DEST_OCCUPIED"}
    ts = [t for t in templates if (t["src"], t["dst"]) == (o.cell, dst)]      # absolute cells only: a same-delta template elsewhere is not one
    if not ts:
        return {**out, "reason": "NO_TEMPLATE"}
    ts = [t for t in ts if abs(t["radius"] - o.radius_m) <= 1e-9]
    if not ts:
        return {**out, "reason": "FOOTPRINT_MISMATCH"}
    ts = [t for t in ts if np.max(np.abs(np.asarray(q, float) - t["q_start"])) <= t.get("start_tol", 1e-9)]
    if not ts:
        return {**out, "reason": "NO_COMPATIBLE_START"}
    delta, eps, evals = _params(cfg)
    definite = True
    for t in ts:
        hit = sorted(set(t["swept"]) & occ) if prefilter else []
        if hit:
            out["prefiltered"] += 1
            out["rejected"].append({"template_id": t["id"], "by": "SWEPT_PREFILTER", "cells": hit})
            continue
        if out["checks"] >= budget:
            return {**out, "reason": "CHECK_BUDGET_EXHAUSTED"}
        out["checks"] += 1
        vs = mo.certify_trajectory(robot, scene, oid, t["arrays"], delta, eps, evals)
        bad = next(((i, v) for i, v in enumerate(vs) if v.status != ge.CLEAR), None)
        if bad is None:
            return {**out, "status": SUCCESS, "template_id": t["id"], "q_end": t["q_end"]}
        definite &= bad[1].status == ge.COLLISION
        out["rejected"].append({"template_id": t["id"], "by": "CERTIFIER", "verdict": bad[1].status, "pair": bad[1].pair,
                                "segment": bad[0], "phase": str(t["arrays"]["phase"][bad[0]])})
    return {**out, "reason": "COLLISION_ALL_CHECKED" if definite else "NOT_CLEAR_ALL_CHECKED"}
