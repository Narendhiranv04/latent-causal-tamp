"""Primary query records, the learner allowlist and identity hashes (Methodology v1.5
§1, §10; Guide v1.7 §3).

A query has four namespaces. `learner` holds only allowlisted initial-scene, robot
and action/goal fields; `labels` decided evidence; `oracle_only` reference paths,
construction ancestry, root IDs and seeds; `execution` the committed repair and its
outcomes. Learner tensors and proposal inputs are built from `learner` by explicit
keys, never by flattening a record, so nothing privileged can reach them.
"""
from __future__ import annotations

import numpy as np

from config import robot_profile_hash, stable_hash
from scene import Scene, scene_from_dict, scene_to_dict
import viz

PROTOCOL = "INITIAL_SCENE_ONE_SHOT_V1"
SCENE_KEYS = ("lattice", "objects", "robot", "legal_cells", "domain_policy")   # learner-visible scene fields
OBJECT_KEYS = ("id", "kind", "radius_m", "xy_m", "cell", "support")


def action_context(cfg: dict, scene: Scene, target_id: str, goal_cell: int, end_policy: str | None = None) -> dict:
    """Everything that defines the intended action, identical across candidate repairs:
    active target, unique goal pose with its tolerance, grasp family, contact mode, end
    policy and robot profile. A trajectory hash is never part of it. end_policy None is
    the G3.5 HOME-constrained scope (hash-identical to report 0007); "SAFE_RETREAT" is the
    G4A contract of addendum A1 (success through a checked retreat; HOME optional)."""
    sk = cfg["skill2d"]
    ctx = {"action": "TRANSPORT_TARGET_TO_GOAL", "target_id": target_id, "goal_cell": goal_cell,
            "goal_xy_m": list(scene.lattice.center(goal_cell)),
            "goal_tolerance_m": cfg["gripper2d"]["release_xy_tolerance_m"],
            "goal_orientation": "ANY (rotationally symmetric disc)",
            "grasp_family": {"approach_dirs": sk["approach_dirs"], "ik_branches": 2,
                             "approach_dist_m": sk["approach_dist_m"], "retreat_dist_m": sk["retreat_dist_m"]},
            "contact_mode": "PLANAR_SUPPORT_CONTACT_SIDE_GRASP", "no_lift": True, "pushing_allowed": False,
            "final_connector": cfg["target_evaluation"]["final_connector"],
            "robot_profile_hash": robot_profile_hash(cfg)}
    if end_policy is None:
        return ctx
    if end_policy != "SAFE_RETREAT":
        raise ValueError(f"unknown end policy {end_policy!r}")
    del ctx["final_connector"]
    return {**ctx, "end_policy": "SAFE_RETREAT", "home_return": "OPTIONAL_DIAGNOSTIC", "goal_alternatives_xy": [],
            "state_pose_uncertainty_m": cfg["evidence"]["state_pose_uncertainty_m"],
            "contract_addendum": "docs/addenda/A1_target_end_policy_v1.md"}


def learner_scene(scene: Scene) -> dict:
    d = scene_to_dict(scene)
    out = {k: d[k] for k in SCENE_KEYS}
    out["objects"] = [{k: o[k] for k in OBJECT_KEYS} for o in d["objects"]]
    return out


def make_query(cfg: dict, name: str, scene: Scene, target_id: str, goal_cell: int, oracle_only: dict,
               end_policy: str | None = None) -> dict:
    learner = {"scene": learner_scene(scene), "action": action_context(cfg, scene, target_id, goal_cell, end_policy)}
    return {"protocol": PROTOCOL, "query_id": name, "learner": learner, "labels": {}, "oracle_only": oracle_only,
            "hashes": hashes(learner)}


def hashes(learner: dict) -> dict:
    return {"observation": stable_hash(learner["scene"]), "action_context": stable_hash(learner["action"])}


def initial_scene(query: dict) -> Scene:
    """The immutable initial scene S0 rebuilt from learner fields only (labels neutral)."""
    d = query["learner"]["scene"]
    return scene_from_dict({**d, "root_id": "query", "variant_id": "initial", "action_hash": None,
                            "robot_profile_hash": query["learner"]["action"]["robot_profile_hash"]})


def learner_tensors(query: dict, image_px: int) -> dict:
    """float32 tensors (uint8 image) from allowlisted learner keys. Object slots follow
    storage order; IDs are not encoded. Clean image: no paths, arrows or status."""
    L = query["learner"]
    sc, act = L["scene"], L["action"]
    objs = sc["objects"]
    lat = sc["lattice"]
    centres = [((c % lat["cols"] + 0.5) * lat["pitch_m"], (c // lat["cols"] + 0.5) * lat["pitch_m"])
               for c in sc["legal_cells"]]
    target = [o["id"] == act["target_id"] for o in objs]
    rgb = viz.render_observation(initial_scene(query), image_px)[0]
    return {"object_xy": np.array([o["xy_m"] for o in objs], np.float32),
            "object_radius": np.array([o["radius_m"] for o in objs], np.float32),
            "is_active_target": np.array(target, np.float32),
            "is_obstacle": np.array([o["kind"] == "obstacle" for o in objs], np.float32),
            "robot_q": np.array(sc["robot"]["q_rad"], np.float32),
            "robot_gripper_gap": np.array([sc["robot"]["gripper_gap_m"]], np.float32),
            "robot_attached": np.array([sc["robot"]["attachment"] != "free"], np.float32),
            "goal_xy": np.array(act["goal_xy_m"], np.float32),
            "goal_tolerance": np.array([act["goal_tolerance_m"]], np.float32),
            "candidate_xy": np.array(centres, np.float32),
            "support_extent": np.array([lat["cols"] * lat["pitch_m"], lat["rows"] * lat["pitch_m"]], np.float32),
            "rgb": rgb}


# ------------------------------------------------------------------ labels (G4A; no model)
POSITIVE, NEGATIVE, UNKNOWN, CONTRADICTION = "VERIFIED_FEASIBLE", "CERTIFIED_INFEASIBLE", "UNRESOLVED", "CONTRADICTION"


def aggregate(evidence: list) -> dict:
    """Assignment-level label from all attempts: a complete witness is a positive, a
    validated assignment-wide certificate a negative, both together a contradiction that
    halts labelling; anything else (failed orders, budgets, unchecked proofs) is unknown."""
    pos = [e for e in evidence if e["kind"] == "complete_witness"]
    neg = [e for e in evidence if e["kind"] == "certificate" and e.get("validated")]
    label = CONTRADICTION if pos and neg else POSITIVE if pos else NEGATIVE if neg else UNKNOWN
    return {"label": label, "positive_sources": [e["source"] for e in pos],
            "negative_sources": sorted({e["certificate"] for e in neg}), "attempts": len(evidence)}


def label_masks(labels: list) -> dict:
    """Binary targets and masks: decided labels only; unknowns masked out of the binary
    loss and of the joint-pool denominator (which needs both a positive and a negative)."""
    if CONTRADICTION in labels:
        raise ValueError("contradictory evidence: labelling halted")
    y = np.array([1.0 if l == POSITIVE else 0.0 for l in labels], np.float32)
    mask = np.array([l in (POSITIVE, NEGATIVE) for l in labels])
    pool = mask if (y[mask] == 1).any() and (y[mask] == 0).any() else np.zeros_like(mask)
    return {"y": y, "binary_mask": mask, "joint_pool_mask": pool}
