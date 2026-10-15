"""Robot paths: recorded trajectories, IK-tracked lines, certified chains, replay.

Methodology v1.4 §2.1 (skill phases, connectors), §3 (complete validated trajectory,
frozen hash, UNRESOLVED when not certified); Guide v1.6 G1.

A trajectory is a list of waypoints (q [rad], clear finger gap [m]); each segment
between consecutive waypoints is joint-linear and carries a phase label. The phase
fixes the collision context of the target object (CONTEXT below), so a stored
trajectory can be re-certified from its arrays alone (replay).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

import geometry as ge
from scene import stable_hash

# phase -> (where the target is, may the fingers touch it)
CONTEXT = {"pregrasp": ("start", False), "approach": ("start", False),
           "close_attach": ("start", True), "carry": ("held", False),
           "release": ("placed", True), "retreat": ("placed", False),
           "return_home": ("placed", False)}
PHASES = tuple(CONTEXT)


@dataclass
class Trajectory:
    target: str
    q: list = field(default_factory=list)
    gap: list = field(default_factory=list)
    phase: list = field(default_factory=list)        # one label per segment
    held_local: tuple | None = None                  # target centre in tool frame at closure
    place_xy: tuple | None = None

    def add(self, q, gap: float, phase: str | None) -> None:
        """Append a waypoint; `phase` labels the segment that ends here."""
        if self.q:
            self.phase.append(phase)
        self.q.append(np.asarray(q, float))
        self.gap.append(float(gap))

    def arrays(self) -> dict[str, np.ndarray]:
        return {"q": np.array(self.q), "gap": np.array(self.gap),
                "phase": np.array(self.phase, dtype="U16"),
                "attached": np.array([CONTEXT[p][0] == "held" for p in self.phase]),  # m per segment
                "held_local": np.array(self.held_local, float),
                "place_xy": np.array(self.place_xy, float)}


def trajectory_hash(arrays: dict, target: str, scene_hash: str, robot_hash: str) -> str:
    """Frozen action hash over exact waypoints, gaps, phases and attachment."""
    return stable_hash({"target": target, "scene": scene_hash, "robot": robot_hash,
                        **{k: np.asarray(v).tolist() for k, v in arrays.items()}})


def checkers(robot, scene, target_id: str, place_xy, held_local, delta: float, eps: float) -> dict:
    """One Checker per target context: resting at start, held, or placed."""
    t = scene.get(target_id)
    free = ge.make_world(scene, exclude=(target_id,))
    out = {"start": ge.make_world(scene)}
    if held_local is not None:
        out["held"] = free
    if place_xy is not None:
        out["placed"] = ge.make_world(scene, (target_id,), [(target_id, tuple(place_xy), t.radius_m)])
    held = (target_id, t.radius_m, held_local)
    return {(ctx, touch): ge.Checker(robot, w, delta, eps, held if ctx == "held" else None,
                                     target_id if touch else None)
            for ctx, w in out.items() for touch in (False, True)}


def certify_trajectory(robot, scene, target_id: str, arrays: dict, delta, eps, max_evals) -> list:
    """Independent replay: re-certify every stored segment in its phase context."""
    if any(bool(m) != (CONTEXT[str(p)][0] == "held") for m, p in zip(arrays["attached"], arrays["phase"])):
        raise ValueError("stored attachment mode m disagrees with the phase schedule")
    held_local = tuple(arrays["held_local"]) if arrays["held_local"].size else None
    place = tuple(arrays["place_xy"]) if arrays["place_xy"].size else None
    ck = checkers(robot, scene, target_id, place, held_local, delta, eps)
    q, gap = arrays["q"], arrays["gap"]
    return [ge.certify(ck[CONTEXT[str(p)]], q[i], q[i + 1], gap[i], gap[i + 1], max_evals)
            for i, p in enumerate(arrays["phase"])]


# ------------------------------------------------------------------ lines
def ik_track(robot, points, phis, local, branch: int, max_jump: float):
    """IK waypoints placing tool-frame point `local` at each world point with tool
    axis phis[k], on one elbow branch. None if IK is missing or jumps by more than
    max_jump between neighbours (a branch switch or a joint-limit wrap)."""
    out = []
    for x, phi in zip(points, phis):
        u = np.array([math.cos(phi), math.sin(phi)])
        tcp = np.asarray(x) - local[0] * u - local[1] * np.array([-u[1], u[0]])
        sol = [q for b, q in ge.ik(robot, tcp, phi) if b == branch]
        if not sol or (out and np.max(np.abs(sol[0] - out[-1])) > max_jump):
            return None
        out.append(sol[0])
    return out


def ik_line(robot, anchor, local, phi: float, branch: int, d_from: float, d_to: float,
            step: float, max_jump: float):
    """Straight approach/retreat: tool axis fixed at phi while `local` sits at offset
    d (d_from -> d_to) behind `anchor` along phi."""
    u = np.array([math.cos(phi), math.sin(phi)])
    n = max(1, math.ceil(abs(d_to - d_from) / step))
    pts = [np.asarray(anchor) - d * u for d in np.linspace(d_from, d_to, n + 1)]
    return ik_track(robot, pts, [phi] * (n + 1), local, branch, max_jump)


def carry_line(robot, src, dst, local, phi_a: float, phi_b: float, branch: int, step: float,
               max_jump: float):
    """Held object centre on the straight segment src -> dst while the tool axis
    turns by the shortest wrapped angle from phi_a to phi_b (one elbow branch)."""
    n = max(1, math.ceil(math.dist(src, dst) / step))
    s = np.linspace(0.0, 1.0, n + 1)
    pts = np.asarray(src) + s[:, None] * (np.asarray(dst) - np.asarray(src))
    return ik_track(robot, pts, phi_a + s * float(ge.wrap(phi_b - phi_a)), local, branch, max_jump)


def certify_chain(checker, qs, gap: float, max_evals: int) -> ge.Verdict:
    """First non-CLEAR verdict along consecutive joint-linear segments at fixed gap.
    Waypoints are evaluated once (a definite violation there ends the check early);
    the intervals between them are then certified from those endpoint values."""
    ds = []
    for q in qs:
        ds.append(checker.distances(q, gap))
        v = checker._classify(ds[-1], None, len(ds))
        if v.status == ge.COLLISION:
            return v
    for i in range(len(qs) - 1):
        v = ge.certify(checker, qs[i], qs[i + 1], gap, gap, max_evals, (ds[i], ds[i + 1]))
        if v.status != ge.CLEAR:
            return v
    return ge.Verdict(ge.CLEAR)


# ------------------------------------------------------------------ evaluation
GAP_WEIGHT = 40.0  # path-length weight: 1 mm of finger travel counts like 0.04 rad of joint travel

def samples(arrays: dict, n: int) -> list[tuple[np.ndarray, float, str]]:
    """n configurations equally spaced along the stored joint-linear segments (the
    executed path itself; gap-only closure/release segments get proportional samples)."""
    q, gap, phase = arrays["q"], arrays["gap"], arrays["phase"]
    seg = np.maximum(np.linalg.norm(np.diff(q, axis=0), axis=1), np.abs(np.diff(gap)) * GAP_WEIGHT)
    cum = np.concatenate([[0.0], np.cumsum(np.maximum(seg, 1e-9))])
    out = []
    for s in np.linspace(0.0, cum[-1], n):
        i = min(int(np.searchsorted(cum, s, side="right")) - 1, len(seg) - 1)
        f = (s - cum[i]) / (cum[i + 1] - cum[i])
        out.append((q[i] + f * (q[i + 1] - q[i]), gap[i] + f * (gap[i + 1] - gap[i]), str(phase[i])))
    return out


def target_xy(robot, arrays: dict, phase: str, q, start_xy) -> np.ndarray:
    ctx = CONTEXT[phase][0]
    if ctx == "held":
        return ge.tool_point(robot, q, arrays["held_local"])
    return np.asarray(arrays["place_xy"] if ctx == "placed" else start_xy, float)
