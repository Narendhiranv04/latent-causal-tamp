"""Configuration registry (Guide v1.6 §2): TOML schema, physical consistency checks,
canonical hashes and the fixture reference-construction policy.

Split from scene.py (size, announced in reports 0003/0004): scene.py keeps the
scene records; this module owns everything about validated settings. Unknown,
missing or mistyped keys fail immediately.
"""
from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

VEC2, VEC3, LIMITS3, PAIRS = "vec2", "vec3", "limits3", "pairs"
SCHEMA = {
    "suite": {"name": str, "rows": int, "cols": int, "pitch_m": float,
              "obstacle_radius_m": float, "margin_m": float, "num_obstacles": int,
              "num_targets": int, "coordinate_frame": str, "domain_policy": str,
              "margin_policy": str},
    "arm2d": {"base_xy_m": VEC2, "link_lengths_m": VEC3, "link_full_widths_m": VEC3,
              "joint_limits_rad": LIMITS3, "q_home_rad": VEC3, "base_radius_m": float,
              "joint_housing_radius_m": float, "self_collision_exclusions": PAIRS},
    "gripper2d": {"model": str, "palm_length_m": float, "palm_full_width_m": float,
                  "finger_length_m": float, "finger_thickness_m": float,
                  "open_gap_m": float, "closed_gap_m": float, "tcp_at_palm_tip": bool,
                  "attachment_pose_policy": str, "contact_pos_tolerance_m": float,
                  "release_xy_tolerance_m": float, "rail_depth_m": float,
                  "grasp_center_x_m": float},
    "geometry": {"numeric_margin_band_m": float, "interval_max_step_rad": float,
                 "interval_certifier": str, "certify_max_evals": int},
    "planner2d": {"algorithm": str, "seed": int, "max_nodes": int, "max_wall_seconds": float,
                  "extend_step_rad": float, "shortcut_rounds": int, "pose_step_m": float,
                  "pose_phi_weight_m": float, "edge_max_evals": int},
    "skill2d": {"approach_dirs": int, "approach_dist_m": float, "retreat_dist_m": float,
                "line_step_m": float, "max_ik_jump_rad": float, "max_plan_failures": int,
                "max_direct_pairs": int},
    "render": {"image_px": int, "overview_xlim_m": VEC2, "overview_ylim_m": VEC2},
}


class ConfigError(ValueError):
    """Raised for unknown, missing, mistyped or physically inconsistent settings."""


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _vec(v, n):
    return isinstance(v, list) and len(v) == n and all(_num(x) for x in v)


def _normalize(value, spec):
    """Return the value with floats normalised, or None if it has the wrong type."""
    if spec is float:
        return float(value) if _num(value) else None
    if spec is int:
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    if spec in (str, bool):
        return value if isinstance(value, spec) else None
    if spec in (VEC2, VEC3):
        return [float(x) for x in value] if _vec(value, 2 if spec == VEC2 else 3) else None
    if spec == LIMITS3:
        ok = isinstance(value, list) and len(value) == 3 and all(_vec(p, 2) for p in value)
        return [[float(x) for x in p] for p in value] if ok else None
    ok = isinstance(value, list) and all(
        isinstance(p, list) and len(p) == 2 and all(type(i) is int for i in p) for p in value)
    return value if ok else None


def validate_config(raw: dict) -> dict:
    """Check keys and types against SCHEMA, then physical consistency."""
    if set(raw) != set(SCHEMA):
        raise ConfigError(f"unknown sections {sorted(set(raw) - set(SCHEMA))}, "
                          f"missing sections {sorted(set(SCHEMA) - set(raw))}")
    cfg = {}
    for sec, spec in SCHEMA.items():
        got = raw[sec]
        if set(got) != set(spec):
            raise ConfigError(f"[{sec}] unknown keys {sorted(set(got) - set(spec))}, "
                              f"missing keys {sorted(set(spec) - set(got))}")
        cfg[sec] = {}
        for key, kind in spec.items():
            value = _normalize(got[key], kind)
            if value is None:
                raise ConfigError(f"[{sec}] {key} has invalid type/shape: {got[key]!r}")
            cfg[sec][key] = value
    _check_physics(cfg)
    return cfg


def _check_physics(cfg: dict) -> None:
    s, a, g, r = cfg["suite"], cfg["arm2d"], cfg["gripper2d"], cfg["render"]
    rad, delta, n_cells = s["obstacle_radius_m"], s["margin_m"], s["rows"] * s["cols"]
    rules = [
        (s["coordinate_frame"] == "world_xy_y_back", "coordinate_frame must be world_xy_y_back"),
        (s["margin_policy"] == "UNINFLATED_ORACLE_DELTA_ONCE", "margin_policy must apply delta once"),
        (s["domain_policy"] == "ALL_SUPPORTED",
         "RESTRICTED needs an explicit published spot list (introduced in G3)"),
        (s["rows"] > 0 and s["cols"] > 0 and s["pitch_m"] > 0, "lattice must be non-empty"),
        (rad > 0 and delta >= 0, "radius must be > 0 and margin >= 0"),
        (s["pitch_m"] > 2 * rad + delta, "distinct cells must be pair-compatible: pitch > 2r + delta"),
        (1 <= s["num_targets"] <= 3, "num_targets must be 1..3"),
        (0 <= s["num_obstacles"] and s["num_obstacles"] + s["num_targets"] <= n_cells,
         "objects must fit in distinct cells"),
        (all(x > 0 for x in a["link_lengths_m"] + a["link_full_widths_m"]), "links must be > 0"),
        (a["base_radius_m"] > 0 and a["joint_housing_radius_m"] > 0, "base/housing radii must be > 0"),
        (all(lo < hi for lo, hi in a["joint_limits_rad"]), "joint limits need lo < hi"),
        (all(lo <= q <= hi for q, (lo, hi) in zip(a["q_home_rad"], a["joint_limits_rad"])),
         "q_home outside joint limits"),
        (all(0 <= i <= 2 for p in a["self_collision_exclusions"] for i in p), "link index not in 0..2"),
        (g["open_gap_m"] > 2 * rad, "open_gap must exceed the object diameter 2r"),
        (0 < g["closed_gap_m"] < g["open_gap_m"], "need 0 < closed_gap < open_gap"),
        (min(g["palm_length_m"], g["palm_full_width_m"], g["finger_length_m"],
             g["finger_thickness_m"]) > 0, "gripper dimensions must be > 0"),
        (g["rail_depth_m"] > 0, "rail_depth must be > 0"),
        (g["grasp_center_x_m"] - rad >= delta, "held object must clear the rail/palm by delta"),
        (0 <= g["grasp_center_x_m"] <= g["finger_length_m"], "grasp contact must lie on the fingers"),
        (cfg["skill2d"]["approach_dist_m"] >= g["finger_length_m"] - g["grasp_center_x_m"] + rad + delta,
         "pregrasp finger tips must clear the object by delta"),
        (cfg["geometry"]["interval_certifier"] == "analytic_or_conservative_subdivision",
         "unknown interval_certifier"),
        (min(cfg["geometry"]["certify_max_evals"], cfg["planner2d"]["max_nodes"],
             cfg["skill2d"]["approach_dirs"], cfg["skill2d"]["max_plan_failures"]) > 0
         and cfg["skill2d"]["line_step_m"] > 0, "budgets and steps must be > 0"),
        (r["image_px"] > 0, "image_px must be > 0"),
        (r["overview_xlim_m"][0] < r["overview_xlim_m"][1]
         and r["overview_ylim_m"][0] < r["overview_ylim_m"][1], "overview limits need lo < hi"),
    ]
    errors = [msg for ok, msg in rules if not ok]
    if errors:
        raise ConfigError("; ".join(errors))


def load_config(path: str | Path) -> dict:
    with open(path, "rb") as f:
        return validate_config(tomllib.load(f))


def stable_hash(obj) -> str:
    """sha256 of canonical JSON (sorted keys, exact float repr)."""
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def config_hash(cfg: dict) -> str:
    return stable_hash(cfg)


def robot_profile_hash(cfg: dict) -> str:
    """Hash of the robot body/gripper profile (provisional until G1 freezes it)."""
    return stable_hash({"arm2d": cfg["arm2d"], "gripper2d": cfg["gripper2d"]})


# Reference-construction policy for fixtures from G2 on (reports 0004, 0005). Every
# policy plans and certifies the nominal action in the fixture's final scene except
# the sparse-seeded bootstrap. Dense primary roots hold 30-40 obstacles (Methodology
# §1); development scenes (D1, D2, ...) are explicitly sparse and never primary.
REFERENCE_POLICIES = {"FINAL_DENSE_PLANNED": "PRIMARY",
                      "FINAL_DEV_SCENE_PLANNED": "DEVELOPMENT_ONLY",
                      "SPARSE_SEEDED_REFERENCE": "BOOTSTRAP_ONLY"}
DENSE_OBSTACLES = (30, 40)


def validate_fixtures(fixtures: dict) -> dict:
    """Reject G2+ fixtures without an allowed policy/role pair, explicit dense roots
    outside 30-40 obstacles, and development scenes that are not explicitly sparse."""
    for name, fx in fixtures.items():
        if int(fx["stage"].lstrip("G")) < 2:
            continue
        policy, role = fx.get("reference_policy"), fx.get("benchmark_role")
        if policy not in REFERENCE_POLICIES or REFERENCE_POLICIES[policy] != role:
            raise ConfigError(f"{name}: needs reference_policy in {sorted(REFERENCE_POLICIES)} "
                              f"with the matching benchmark_role, got {policy!r}/{role!r}")
        n = len(fx["obstacle_cells"]) if "obstacle_cells" in fx else None
        if policy == "FINAL_DENSE_PLANNED" and n is not None and not DENSE_OBSTACLES[0] <= n <= DENSE_OBSTACLES[1]:
            raise ConfigError(f"{name}: a dense primary root needs {DENSE_OBSTACLES} obstacles, has {n}")
        if policy == "FINAL_DEV_SCENE_PLANNED" and (n is None or n >= DENSE_OBSTACLES[0]):
            raise ConfigError(f"{name}: a development scene must list fewer than {DENSE_OBSTACLES[0]} obstacles")
    return fixtures
