#!/usr/bin/env python3
"""Stateful physical simulation adapter (`RepairEnv`) for 2D and 3D DISCO-Grid.

Implements the exact contract of `DISCO_plan.md` Sections 3.2-3.4 and 4.1-4.4:
- `reset(root_id, seed)` -> `FullState`
- `observe(state, include_qt=False)` -> `LearnerObservation` (strictly learner-visible inputs)
- `legal_actions(state)` -> list of `(obj_idx, dest_cell)` static grammar actions (+ `"STOP"`)
- `transition(state, action)` -> `StepResult` (executes one physical relocation with carried robot/physics state,
  never resetting `q` to `q_ref` and never running the terminal `q_ref` connector between steps)
- `terminal_query(state)` -> `StopResult` (runs the terminal `q_ref` connector from the carried state, plus
  the independent `Y` target query from `q_ref` in the canonical endpoint-edited scene)
- `clone_or_serialize(state)` / `restore(blob)` -> exact, zero-cross-contamination state snapshots for MCTS
- `predict_observation_edit(obs, action)` -> labelled, no-physics static scene edit for open-loop inference only
"""
from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
import pickle
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

import data as D

ABF_ROOT = D.ABF_ROOT
DISCO_ROOT = D.DISCO_ROOT


@dataclass
class FullState:
    root_id: str
    domain: str
    seed: int
    depth: int
    prefix: list[tuple[int, int]]
    cells: list[int]
    moved_mask: list[bool]
    used_dests: list[int]
    q_t: list[float]
    gripper_state: dict[str, Any]
    physics_payload: dict[str, Any]
    sim_teacher_version: str

    def state_hash(self) -> str:
        h = hashlib.sha256()
        h.update(f"{self.domain}|{self.root_id}|{self.depth}|{self.prefix}|{self.cells}".encode())
        h.update(np.round(np.asarray(self.q_t, dtype=np.float64), 7).tobytes())
        if self.domain == "2d":
            used = self.physics_payload.get("used", {})
            h.update(json.dumps(used, sort_keys=True).encode())
        else:
            qpos = np.asarray(self.physics_payload.get("qpos", []), dtype=np.float64)
            qvel = np.asarray(self.physics_payload.get("qvel", []), dtype=np.float64)
            h.update(np.round(qpos, 6).tobytes())
            h.update(np.round(qvel, 6).tobytes())
        return h.hexdigest()[:24]


@dataclass
class LearnerObservation:
    root_id: str
    domain: str
    ids: list[str]
    cells: list[int]
    xy: list[list[float]]
    attrs: list[list[float]]
    tid: int
    goal_cell: int
    goal_xy: list[float]
    base_xy: list[float]
    ctx: list[float]
    legal_cells: list[int]
    cell_xy: dict[str, list[float]]
    moved_mask: list[bool]
    remaining_steps: int
    eligible_objects: list[int]
    legal_destinations: list[int]
    can_stop: bool = True
    is_predicted_edit: bool = False
    q_t_optional: list[float] | None = None

    def obs_hash(self) -> str:
        payload = {
            "root_id": self.root_id,
            "domain": self.domain,
            "cells": self.cells,
            "moved_mask": self.moved_mask,
            "remaining_steps": self.remaining_steps,
            "is_predicted_edit": self.is_predicted_edit,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]


@dataclass
class StepResult:
    status: str  # "EXECUTED", "PHYSICALLY_FAILED", "UNRESOLVED"
    failure_kind: str | None
    teacher_status: str
    action: tuple[int, int]
    next_state: FullState | None
    witness_ids: list[str] = field(default_factory=list)
    planner_calls: int = 1
    time_s: float = 0.0
    detail: str | None = None


@dataclass
class StopResult:
    status: str  # "DECIDED", "UNRESOLVED"
    success: bool
    x_terminal: int | None
    y_target: int | None
    z_outcome: int | None
    failed_phase: str | None
    failure_kind: str | None
    connector_status: str
    y_status: str
    witness_connector: str | None = None
    witness_y: str | None = None
    canonical_endpoint_cells: dict[str, Any] = field(default_factory=dict)
    executed_object_poses: dict[str, list[float]] = field(default_factory=dict)
    endpoint_pose_drift_m: dict[str, float] = field(default_factory=dict)
    planner_calls: int = 0
    time_s: float = 0.0


def predict_observation_edit(obs: LearnerObservation, action: tuple[int, int]) -> LearnerObservation:
    """Deterministic, no-physics predicted-scene edit for OPEN-LOOP inference only.
    Never called as a substitute for physical transition in training or verification.
    """
    o_idx, dest_cell = int(action[0]), int(action[1])
    if obs.remaining_steps <= 0:
        raise ValueError("Cannot apply relocation edit at horizon 0")
    if o_idx not in obs.eligible_objects:
        raise ValueError(f"Object index {o_idx} is not eligible in current observation")
    if dest_cell not in obs.legal_destinations:
        raise ValueError(f"Destination {dest_cell} is not legal in current observation")

    new_cells = list(obs.cells)
    new_cells[o_idx] = dest_cell
    new_xy = [list(obs.cell_xy[str(c)]) for c in new_cells]
    new_moved = list(obs.moved_mask)
    new_moved[o_idx] = True
    new_rem = obs.remaining_steps - 1

    inp_proxy = {
        "tid": obs.tid,
        "attrs": obs.attrs,
        "cells0": [obs.cells[i] if not obs.moved_mask[i] else -1 for i in range(len(obs.cells))],
        "legal_cells": obs.legal_cells,
        "goal_cell": obs.goal_cell,
    }
    # Reconstruct original occ0 from obs: any unmoved object is at its original cell; any moved object's
    # original cell is already excluded from obs.legal_destinations.
    elig_objs = [] if new_rem == 0 else [o for o in obs.eligible_objects if o != o_idx]
    leg_dests = [] if new_rem == 0 else [d for d in obs.legal_destinations if d != dest_cell]

    return LearnerObservation(
        root_id=obs.root_id,
        domain=obs.domain,
        ids=list(obs.ids),
        cells=new_cells,
        xy=new_xy,
        attrs=obs.attrs,
        tid=obs.tid,
        goal_cell=obs.goal_cell,
        goal_xy=obs.goal_xy,
        base_xy=obs.base_xy,
        ctx=obs.ctx,
        legal_cells=obs.legal_cells,
        cell_xy=obs.cell_xy,
        moved_mask=new_moved,
        remaining_steps=new_rem,
        eligible_objects=elig_objs,
        legal_destinations=leg_dests,
        can_stop=True,
        is_predicted_edit=True,
        q_t_optional=None,
    )


# ---------------------------------------------------------------------------
# 2D Backend (Planar 3R arm, BXY_X_TEACHER_V1 / BXY_Y_TEACHER_V1)
# ---------------------------------------------------------------------------

class _Backend2D:
    def __init__(self, geom_impl: str = "auto", witness_dir: Path | None = None):
        self.geom_impl = geom_impl
        self.witness_dir = str(witness_dir or (DISCO_ROOT / "caches/witnesses_2d"))
        Path(self.witness_dir).mkdir(parents=True, exist_ok=True)
        self._booted = False
        self.fastgeom = None
        self.T = None
        self.E = None
        self.bd_2d = None
        self.bd_data = None
        self.pm = None
        self.pc = None
        self.ps = None
        self.ge = None
        self.mo = None
        self.root_caches: dict[str, dict[Any, Any]] = {}
        self.y_endpoint_cache: dict[str, dict[str, Any]] = {}

    def boot(self):
        if self._booted:
            return
        code_dir = ABF_ROOT / "mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/code"
        wt_dir = ABF_ROOT / "teacher2d_wt"
        paths = [str(code_dir / "dataset-bd"), str(code_dir), str(code_dir / "latent-causal-tamp"), str(wt_dir)]
        if sys.version_info < (3, 11):
            paths.insert(0, str(code_dir / "py310_shim"))
        for p in reversed(paths):
            if p not in sys.path:
                sys.path.insert(0, p)
        os.chdir(code_dir / "latent-causal-tamp")
        import importlib.util
        import warnings
        warnings.filterwarnings("ignore")
        # Ensure `import data` inside 2D teacher resolves to latent-causal-tamp/data.py
        lct_data_path = code_dir / "latent-causal-tamp/data.py"
        spec = importlib.util.spec_from_file_location("data", str(lct_data_path))
        lct_data = importlib.util.module_from_spec(spec)
        sys.modules["data"] = lct_data
        spec.loader.exec_module(lct_data)
        import fastgeom
        import bd_2d
        import bxy_data as bd_data
        import bxy_teacher as T
        import geometry as ge
        import motion as mo
        import p15_search as ps
        import p16_common as pc
        import p16_motion as pm

        self.fastgeom = fastgeom
        self.bd_2d = bd_2d
        self.bd_data = bd_data
        self.T = T
        self.E = T.env()
        self.pm = pm
        self.pc = pc
        self.ps = ps
        self.ge = ge
        self.mo = mo
        self._booted = True

    def _sync_geom(self, rec: dict[str, Any]):
        use_fg = (rec.get("geometry_impl") == "fastgeom1") if self.geom_impl == "auto" else (self.geom_impl == "fastgeom1")
        if use_fg:
            self.fastgeom.install()
        else:
            self.fastgeom.uninstall()

    def _get_cache(self, root_id: str) -> dict[Any, Any]:
        return self.root_caches.setdefault(root_id, {})

    def _make_phys(self, root_id: str, rec: dict[str, Any], used: dict[str, int] | None = None, stats: dict[str, int] | None = None, vcpu: float = 0.0):
        self._sync_geom(rec)
        cache = self._get_cache(root_id)
        phys = self.pm.DetPhysics(self.T.task_of(root_id, rec), None, budget=dict(self.bd_2d.QB), cache=cache)
        if used is not None:
            phys.used = dict(used)
        if stats is not None:
            phys.stats.update(stats)
        phys.vcpu = float(vcpu)
        return phys

    def reset(self, row: dict[str, Any], rec: dict[str, Any], seed: int = 0) -> FullState:
        self.boot()
        self._sync_geom(rec)
        inp = row["inputs"]
        cells0_dict = self.bd_data.cells0(rec)
        q0 = self.T.qref(rec).tolist()
        gap0 = self.T.ref_gap(rec)
        phys = self._make_phys(row["root_id"], rec)
        payload = {
            "cells_dict": dict(cells0_dict),
            "q": list(q0),
            "gap": float(gap0),
            "records": [],
            "steps": [],
            "used": dict(phys.used),
            "stats": dict(phys.stats),
            "vcpu": 0.0,
            "witnesses": [],
            "geometry_impl": rec.get("geometry_impl") or "original",
        }
        return FullState(
            root_id=row["root_id"],
            domain="2d",
            seed=int(seed),
            depth=0,
            prefix=[],
            cells=[int(c) for c in inp["cells0"]],
            moved_mask=[False] * len(inp["ids"]),
            used_dests=[],
            q_t=list(q0),
            gripper_state={"gap": float(gap0), "held": None},
            physics_payload=payload,
            sim_teacher_version=f"{self.T.X_VERSION}/{self.T.Y_VERSION}",
        )

    def transition(self, row: dict[str, Any], rec: dict[str, Any], state: FullState, action: tuple[int, int]) -> StepResult:
        self.boot()
        t0 = time.process_time()
        o_idx, dest_cell = int(action[0]), int(action[1])
        inp = row["inputs"]
        new_prefix = list(state.prefix) + [(o_idx, dest_cell)]
        violations = D.validate_repair_sequence(inp, "2d", new_prefix)
        if violations:
            return StepResult(
                status="PHYSICALLY_FAILED",
                failure_kind="INELIGIBLE",
                teacher_status="INELIGIBLE:" + ",".join(violations),
                action=(o_idx, dest_cell),
                next_state=None,
                planner_calls=0,
                time_s=round(time.process_time() - t0, 4),
                detail=",".join(violations),
            )
        o_id = inp["ids"][o_idx]
        pay = state.physics_payload
        phys = self._make_phys(state.root_id, rec, pay["used"], pay["stats"], pay["vcpu"])
        cells_dict = dict(pay["cells_dict"])
        q_now = np.asarray(pay["q"], dtype=float)

        outs = phys.edges(cells_dict, q_now, o_id, int(dest_cell))
        e = self.pc.best_edge(outs)
        dt = round(time.process_time() - t0, 4)
        if e is None:
            st = outs[0][0] if outs else self.ps.U_PLAN
            neg_kind = self.bd_2d._neg(st)
            return StepResult(
                status="PHYSICALLY_FAILED",
                failure_kind=neg_kind,
                teacher_status=str(st),
                action=(o_idx, dest_cell),
                next_state=None,
                planner_calls=1,
                time_s=dt,
                detail=str(outs[0][4] if outs else None)[:200],
            )
        _, rs, q2, J, meta = e
        wids = [self.T.wid(a, self.witness_dir) for a in rs]
        new_cells_dict = {**cells_dict, o_id: int(dest_cell)}
        new_q = np.asarray(q2, dtype=float).tolist()
        new_gap = float(rs[-1]["gap"][-1])
        new_cells = list(state.cells)
        new_cells[o_idx] = int(dest_cell)
        new_moved = list(state.moved_mask)
        new_moved[o_idx] = True
        new_used_dests = list(state.used_dests) + [int(dest_cell)]

        new_payload = {
            "cells_dict": new_cells_dict,
            "q": new_q,
            "gap": new_gap,
            "records": copy.deepcopy(pay["records"]) + copy.deepcopy(rs),
            "steps": copy.deepcopy(pay["steps"]) + [
                {"object": o_id, "dest": int(dest_cell), "via": meta.get("via"), "J_record": float(J), "witness": wids}
            ],
            "used": dict(phys.used),
            "stats": dict(phys.stats),
            "vcpu": float(phys.vcpu),
            "witnesses": list(pay["witnesses"]) + wids,
        }
        next_state = FullState(
            root_id=state.root_id,
            domain="2d",
            seed=state.seed,
            depth=state.depth + 1,
            prefix=new_prefix,
            cells=new_cells,
            moved_mask=new_moved,
            used_dests=new_used_dests,
            q_t=new_q,
            gripper_state={"gap": new_gap, "held": None},
            physics_payload=new_payload,
            sim_teacher_version=state.sim_teacher_version,
        )
        return StepResult(
            status="EXECUTED",
            failure_kind=None,
            teacher_status="VERIFIED_STEP",
            action=(o_idx, dest_cell),
            next_state=next_state,
            witness_ids=wids,
            planner_calls=1,
            time_s=dt,
            detail=meta.get("via"),
        )

    def terminal_query(self, row: dict[str, Any], rec: dict[str, Any], state: FullState) -> StopResult:
        self.boot()
        t0 = time.process_time()
        inp = row["inputs"]
        ids = inp["ids"]
        seq_obj = [(ids[o], int(d)) for o, d in state.prefix]
        cache = self._get_cache(state.root_id)

        # 1. Terminal connector + X verification
        p_calls = 0
        w_conn = None
        if not seq_obj:
            x_val = 1
            conn_status = "EMPTY_PREFIX_X_IS_1_BY_DEFINITION"
            failed_phase = None
            fail_kind = None
        else:
            pay = state.physics_payload
            phys = self._make_phys(state.root_id, rec, pay["used"], pay["stats"], pay["vcpu"])
            cells_dict = dict(pay["cells_dict"])
            q_now = np.asarray(pay["q"], dtype=float)
            gap = float(pay["gap"])
            q_ref = self.T.qref(rec)
            s = phys.scene(cells_dict, q_now)
            ck = self.mo.checkers(self.E["robot"], s, "t0", None, None, self.E["p"]["delta"], self.E["p"]["eps"])[("start", False)]
            p_calls += 1
            if ck.status_at(q_now, gap).status != self.ge.CLEAR:
                x_val = 0
                conn_status = "TERMINAL_STATE_NOT_CLEAR"
                failed_phase = "connector:terminal_q"
                fail_kind = "CERTIFIED"
            elif ck.status_at(q_ref, gap).status != self.ge.CLEAR:
                x_val = 0
                conn_status = "Q_REF_NOT_CLEAR_IN_EDITED_SCENE"
                failed_phase = "connector:q_ref"
                fail_kind = "CERTIFIED"
            else:
                conn, _ = phys._transit(
                    s,
                    "t0",
                    q_now,
                    {"q": [q_ref], "gap": [gap]},
                    ("bxy_connector", self.ps.state_key(cells_dict, q_now, ())),
                )
                if conn is None:
                    st = self.ps.U_BUD if phys.used["transit_plans"] >= phys.budget["transit_plans"] else self.ps.U_TR
                    x_val = 0
                    conn_status = str(st)
                    failed_phase = "connector"
                    fail_kind = self.bd_2d._neg(st)
                else:
                    w_conn = self.T.wid(conn, self.witness_dir)
                    rep = self.T.replay_x(self.E, rec, seq_obj, pay["records"], conn)
                    if rep["ok"]:
                        x_val = 1
                        conn_status = "VERIFIED"
                        failed_phase = None
                        fail_kind = None
                    else:
                        x_val = 0
                        conn_status = "REPLAY_FAILED"
                        failed_phase = "replay"
                        fail_kind = "OTHER_FAILURE"

        # 2. Canonical endpoint Y query (cached by canonical endpoint key)
        self._sync_geom(rec)
        y_key = self.T.ykey(state.root_id, rec, seq_obj)
        if y_key in self.y_endpoint_cache:
            yr = self.y_endpoint_cache[y_key]
        else:
            yr = self.T.y_query(self.E, state.root_id, rec, seq_obj, cache, out=self.witness_dir)
            self.y_endpoint_cache[y_key] = yr
            p_calls += 1

        y_val = yr.get("y")
        y_status = str(yr.get("teacher_status"))
        w_y = yr.get("target_witness")
        if x_val == 1 and y_val != 1:
            failed_phase = "target"
            fail_kind = yr.get("negative_kind")

        z_val = int(x_val == 1 and y_val == 1) if (x_val in (0, 1) and y_val in (0, 1)) else None
        canon_cells = {ids[i]: int(c) for i, c in enumerate(state.cells)}
        exec_poses = {ids[i]: list(inp["cell_xy"][str(c)]) for i, c in enumerate(state.cells)}
        drift = {k: 0.0 for k in canon_cells}

        return StopResult(
            status="DECIDED" if z_val is not None else "UNRESOLVED",
            success=bool(z_val == 1),
            x_terminal=x_val,
            y_target=y_val,
            z_outcome=z_val,
            failed_phase=failed_phase,
            failure_kind=fail_kind,
            connector_status=conn_status,
            y_status=y_status,
            witness_connector=w_conn,
            witness_y=w_y,
            canonical_endpoint_cells=canon_cells,
            executed_object_poses=exec_poses,
            endpoint_pose_drift_m=drift,
            planner_calls=p_calls,
            time_s=round(time.process_time() - t0, 4),
        )


# ---------------------------------------------------------------------------
# 3D Backend (xArm7 + MuJoCo 6x6 Confined Shelf, fin3d / bwlphys)
# ---------------------------------------------------------------------------

class _Backend3D:
    def __init__(self, witness_dir: Path | None = None):
        self.witness_dir = Path(witness_dir or (DISCO_ROOT / "caches/witnesses_3d"))
        self.witness_dir.mkdir(parents=True, exist_ok=True)
        self._booted = False
        self.F = None
        self.A = None
        self.BP = None
        self.S = None
        self.store = None
        self.mujoco = None
        self._env_cache: dict[str, Any] = {}
        self.y_endpoint_cache: dict[str, dict[str, Any]] = {}

    def boot(self):
        if self._booted:
            return
        os.environ.setdefault("MUJOCO_GL", "disable")
        os.environ.setdefault("FIN3D_STORE", str(self.witness_dir))
        os.environ.setdefault(
            "FIN3D_SRC",
            "/home/nav/approachb_final_gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass",
        )
        fin3d_code = os.environ.get("FIN3D_CODE", "/home/nav/approachb_final_gen/final3d_v4/code")
        if fin3d_code not in sys.path:
            sys.path.insert(0, fin3d_code)
        import fin3d as F
        import mujoco

        F.boot()
        self.F = F
        self.A = F.Q._M["A"]
        self.BP = F.M["BP"]
        self.store = F.Q._M["store"]
        self.S = self.A.env()["TS"]
        self.mujoco = mujoco
        self._booted = True

    def _get_env(self, root_id: str, rec: dict[str, Any]):
        if root_id not in self._env_cache:
            if len(self._env_cache) >= 8:
                oldest = next(iter(self._env_cache))
                del self._env_cache[oldest]
            self._env_cache[root_id] = self.A.build(rec["objects"], rec["initial_cells"])
        return self._env_cache[root_id]

    @staticmethod
    def _snap_env(e, witnesses: list[str]) -> dict[str, Any]:
        return {
            "time": float(e.data.time),
            "qpos": e.data.qpos.copy().tolist(),
            "qvel": e.data.qvel.copy().tolist(),
            "act": e.data.act.copy().tolist() if e.model.na else [],
            "qacc_warmstart": e.data.qacc_warmstart.copy().tolist(),
            "qacc": e.data.qacc.copy().tolist(),
            "ctrl": e.data.ctrl.copy().tolist(),
            "q_cmd": e.q_cmd.copy().tolist(),
            "held": e.held,
            "focus_i": e._focus_i,
            "table_z": float(e.table_z),
            "ikc": {k: [q.copy().tolist() for q in v] for k, v in e._ikc.items()},
            "obj_pos": [o["pos"].copy().tolist() for o in e.objects],
            "witnesses": list(witnesses),
        }

    def _restore_env(self, e, pay: dict[str, Any]):
        self.mujoco.mj_resetData(e.model, e.data)
        e.data.time = float(pay["time"])
        e.data.qpos[:] = np.asarray(pay["qpos"], dtype=np.float64)
        e.data.qvel[:] = np.asarray(pay["qvel"], dtype=np.float64)
        if e.model.na and pay.get("act"):
            e.data.act[:] = np.asarray(pay["act"], dtype=np.float64)
        e.data.qacc_warmstart[:] = np.asarray(pay["qacc_warmstart"], dtype=np.float64)
        e.data.qacc[:] = np.asarray(pay["qacc"], dtype=np.float64)
        e.data.ctrl[:] = np.asarray(pay["ctrl"], dtype=np.float64)
        e.q_cmd = np.asarray(pay["q_cmd"], dtype=np.float64).copy()
        e.held = pay["held"]
        e._focus_i = pay.get("focus_i")
        e.table_z = float(pay.get("table_z", e.levels[0]["z"]))
        e._check_width = None
        e._excuse = set()
        e.current = None
        e._ikc = {k: [np.asarray(q, dtype=np.float64).copy() for q in v] for k, v in pay.get("ikc", {}).items()}
        for o, p in zip(e.objects, pay["obj_pos"]):
            o["pos"] = np.asarray(p, dtype=np.float64).copy()
        for j, c in enumerate(e._col_ids):
            e.model.geom_pos[c, :2] = e.obj_pos(j)[:2]
        self.mujoco.mj_forward(e.model, e.data)

    def reset(self, row: dict[str, Any], rec: dict[str, Any], seed: int = 0) -> FullState:
        self.boot()
        inp = row["inputs"]
        e = self._get_env(row["root_id"], rec)
        e._ikc.clear()
        e._focus_i = None
        e._check_width = None
        e._excuse = set()
        e.current = None
        e.held = None
        e.table_z = float(e.levels[0]["z"])
        self.A.settle(e, rec["initial_cells"])
        payload = self._snap_env(e, [])
        q_now = e.q_now().tolist()
        return FullState(
            root_id=row["root_id"],
            domain="3d",
            seed=int(seed),
            depth=0,
            prefix=[],
            cells=[int(c) for c in inp["cells0"]],
            moved_mask=[False] * len(inp["ids"]),
            used_dests=[],
            q_t=q_now,
            gripper_state={"ctrl": float(e.data.ctrl[e.act_grip]), "held": e.held},
            physics_payload=payload,
            sim_teacher_version=self.A.TEACHER_VERSION,
        )

    def transition(self, row: dict[str, Any], rec: dict[str, Any], state: FullState, action: tuple[int, int]) -> StepResult:
        self.boot()
        t0 = time.process_time()
        o_idx, dest_cell = int(action[0]), int(action[1])
        inp = row["inputs"]
        new_prefix = list(state.prefix) + [(o_idx, dest_cell)]
        violations = D.validate_repair_sequence(inp, "3d", new_prefix)
        if violations:
            return StepResult(
                status="PHYSICALLY_FAILED",
                failure_kind="INELIGIBLE",
                teacher_status="INELIGIBLE:" + ",".join(violations),
                action=(o_idx, dest_cell),
                next_state=None,
                planner_calls=0,
                time_s=round(time.process_time() - t0, 4),
                detail=",".join(violations),
            )
        o_id = inp["ids"][o_idx]
        dest_rc = (dest_cell // 6, dest_cell % 6)
        e = self._get_env(state.root_id, rec)
        self._restore_env(e, state.physics_payload)

        before = {n: e.cell_of(n) for n in e.obj_index if n != o_id}
        p, qi = self.A.query(e, o_id, dest_rc)
        if p is None:
            dt = round(time.process_time() - t0, 4)
            lbl = self.A.label(None, qi)
            return StepResult(
                status="PHYSICALLY_FAILED",
                failure_kind=lbl.get("negative_kind") or "NO_PLAN_FOUND",
                teacher_status=str(lbl.get("reason") or "no feasible side grasp"),
                action=(o_idx, dest_cell),
                next_state=None,
                planner_calls=1,
                time_s=dt,
                detail=f"tried={qi.get('tried')}",
            )
        wid = self.A.witness(self.store, p)
        try:
            e.run_plan(p)
        except self.S.GraspFailed as err:
            dt = round(time.process_time() - t0, 4)
            return StepResult(
                status="PHYSICALLY_FAILED",
                failure_kind="GRASP_FAILED",
                teacher_status=f"GRASP_FAILED:{str(err)[:60]}",
                action=(o_idx, dest_cell),
                next_state=None,
                witness_ids=[wid],
                planner_calls=1,
                time_s=dt,
                detail=str(err)[:120],
            )
        h = next(x["height"] for x in rec["objects"] if x["id"] == o_id)
        z = float(e.obj_pos(o_id)[2] - e.table_z - h / 2)
        if e.cell_of(o_id) != dest_rc or abs(z) > 0.01 or any(e.cell_of(n) != before[n] for n in before):
            dt = round(time.process_time() - t0, 4)
            return StepResult(
                status="PHYSICALLY_FAILED",
                failure_kind="EXECUTION_NOT_VERIFIED",
                teacher_status="EXECUTION_NOT_VERIFIED",
                action=(o_idx, dest_cell),
                next_state=None,
                witness_ids=[wid],
                planner_calls=1,
                time_s=dt,
                detail=f"end_cell={e.cell_of(o_id)} z_err={z:.4f}",
            )

        new_wids = list(state.physics_payload["witnesses"]) + [wid]
        new_payload = self._snap_env(e, new_wids)
        new_cells = list(state.cells)
        new_cells[o_idx] = dest_cell
        new_moved = list(state.moved_mask)
        new_moved[o_idx] = True
        new_used_dests = list(state.used_dests) + [dest_cell]
        q_now = e.q_now().tolist()

        next_state = FullState(
            root_id=state.root_id,
            domain="3d",
            seed=state.seed,
            depth=state.depth + 1,
            prefix=new_prefix,
            cells=new_cells,
            moved_mask=new_moved,
            used_dests=new_used_dests,
            q_t=q_now,
            gripper_state={"ctrl": float(e.data.ctrl[e.act_grip]), "held": e.held},
            physics_payload=new_payload,
            sim_teacher_version=state.sim_teacher_version,
        )
        return StepResult(
            status="EXECUTED",
            failure_kind=None,
            teacher_status="VERIFIED_STEP",
            action=(o_idx, dest_cell),
            next_state=next_state,
            witness_ids=[wid],
            planner_calls=1,
            time_s=round(time.process_time() - t0, 4),
            detail=f"grasp_id={qi.get('grasp_id')}",
        )

    def terminal_query(self, row: dict[str, Any], rec: dict[str, Any], state: FullState) -> StopResult:
        self.boot()
        t0 = time.process_time()
        inp = row["inputs"]
        ids = inp["ids"]
        e = self._get_env(state.root_id, rec)
        self._restore_env(e, state.physics_payload)

        exec_poses = {o["id"]: e.obj_pos(o["id"]).tolist() for o in rec["objects"]}
        canon_rc = {
            **{k: [int(v[0]), int(v[1])] for k, v in rec["initial_cells"].items()},
            **{ids[o]: [int(d) // 6, int(d) % 6] for o, d in state.prefix},
        }
        drift = {}
        for o in rec["objects"]:
            oid = o["id"]
            nom_xy = e.cell_xy(canon_rc[oid])
            act_xy = np.asarray(exec_poses[oid][:2], dtype=float)
            drift[oid] = round(float(np.linalg.norm(act_xy - nom_xy)), 6)

        p_calls = 0
        w_conn = None
        if state.depth == 0:
            x_val = 1
            conn_status = "EMPTY_PREFIX_X_IS_1_BY_DEFINITION"
            failed_phase = None
            fail_kind = None
        else:
            expected = {k: tuple(v) for k, v in canon_rc.items()}
            c, path = self.BP.connector(e, self.S, expected)
            p_calls += 1
            if path is not None:
                w_conn = self.store.witness({"connector_q": path})
            x_val = int(bool(c["ok"]))
            conn_status = str(c.get("failure") or "VERIFIED")
            failed_phase = None if c["ok"] else "connector"
            fail_kind = None if c["ok"] else conn_status

        # Canonical endpoint Y query (independent of relocation order, settled at q_ready)
        ekey = f"{state.root_id}|{json.dumps( sorted(canon_rc.items()) )}"
        if ekey in self.y_endpoint_cache:
            yr = self.y_endpoint_cache[ekey]
        else:
            yr = self.F.capped(self.F.run_y, rec, canon_rc)
            self.y_endpoint_cache[ekey] = yr
            p_calls += 1

        if yr.get("resolution") != "EVALUATED":
            return StopResult(
                status="UNRESOLVED",
                success=False,
                x_terminal=x_val,
                y_target=None,
                z_outcome=None,
                failed_phase="target_unresolved",
                failure_kind=yr.get("resolution"),
                connector_status=conn_status,
                y_status=str(yr.get("resolution")),
                witness_connector=w_conn,
                witness_y=None,
                canonical_endpoint_cells=canon_rc,
                executed_object_poses=exec_poses,
                endpoint_pose_drift_m=drift,
                planner_calls=p_calls,
                time_s=round(time.process_time() - t0, 4),
            )

        y_val = int(yr["y"])
        y_status = str(yr.get("status") or ("VERIFIED" if y_val == 1 else "FAILED"))
        w_y = (yr.get("witnesses") or [None])[0]
        if x_val == 1 and y_val != 1:
            failed_phase = "target"
            fail_kind = y_status

        z_val = int(x_val == 1 and y_val == 1)
        return StopResult(
            status="DECIDED",
            success=bool(z_val == 1),
            x_terminal=x_val,
            y_target=y_val,
            z_outcome=z_val,
            failed_phase=failed_phase,
            failure_kind=fail_kind,
            connector_status=conn_status,
            y_status=y_status,
            witness_connector=w_conn,
            witness_y=w_y,
            canonical_endpoint_cells=canon_rc,
            executed_object_poses=exec_poses,
            endpoint_pose_drift_m=drift,
            planner_calls=p_calls,
            time_s=round(time.process_time() - t0, 4),
        )


# ---------------------------------------------------------------------------
# Unified RepairEnv Facade
# ---------------------------------------------------------------------------

class RepairEnv:
    """Domain-dispatched stateful physical rearrangement environment for DISCO-Grid."""

    def __init__(
        self,
        domain: str,
        snap_dir: Path = D.BASE_SNAP,
        geom_impl_2d: str = "auto",
        witness_dir: Path | None = None,
    ):
        self.domain = domain.lower()
        assert self.domain in ("2d", "3d"), f"Unsupported domain: {domain}"
        self.snap_dir = Path(snap_dir)
        self._rows_by_id: dict[str, dict[str, Any]] = {}
        self._raw_by_id: dict[str, dict[str, Any]] = {}
        if self.domain == "2d":
            self.backend = _Backend2D(geom_impl=geom_impl_2d, witness_dir=witness_dir)
        else:
            self.backend = _Backend3D(witness_dir=witness_dir)

    def _get_row_and_raw(self, root_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self._rows_by_id:
            for r in D.load_snapshot_rows(self.domain, None, self.snap_dir):
                self._rows_by_id[r["root_id"]] = r
        row = self._rows_by_id[root_id]
        if root_id not in self._raw_by_id:
            p = D.raw_root_path(self.domain, root_id)
            self._raw_by_id[root_id] = json.loads(p.read_text())
        return row, self._raw_by_id[root_id]

    def reset(self, root_id: str, seed: int = 0) -> FullState:
        row, rec = self._get_row_and_raw(root_id)
        return self.backend.reset(row, rec, seed=seed)

    def observe(self, state: FullState, include_qt: bool = False) -> LearnerObservation:
        row, _ = self._get_row_and_raw(state.root_id)
        inp = row["inputs"]
        leg_info = D.legal_actions_at_prefix(inp, self.domain, state.prefix, include_stop=True)
        xy = [list(inp["cell_xy"][str(c)]) for c in state.cells]
        return LearnerObservation(
            root_id=state.root_id,
            domain=self.domain,
            ids=list(inp["ids"]),
            cells=list(state.cells),
            xy=xy,
            attrs=[list(a) for a in inp["attrs"]],
            tid=int(inp["tid"]),
            goal_cell=int(inp["goal_cell"]),
            goal_xy=list(inp["goal"]),
            base_xy=list(inp["base"]),
            ctx=list(inp["ctx"]),
            legal_cells=[int(c) for c in inp["legal_cells"]],
            cell_xy=dict(inp["cell_xy"]),
            moved_mask=list(state.moved_mask),
            remaining_steps=3 - state.depth,
            eligible_objects=leg_info["eligible_objects"],
            legal_destinations=leg_info["legal_destinations"],
            can_stop=True,
            is_predicted_edit=False,
            q_t_optional=list(state.q_t) if include_qt else None,
        )

    def legal_actions(self, state: FullState, include_stop: bool = True) -> dict[str, Any]:
        row, _ = self._get_row_and_raw(state.root_id)
        return D.legal_actions_at_prefix(row["inputs"], self.domain, state.prefix, include_stop=include_stop)

    def transition(self, state: FullState, action: tuple[int, int]) -> StepResult:
        row, rec = self._get_row_and_raw(state.root_id)
        return self.backend.transition(row, rec, state, action)

    def terminal_query(self, state: FullState) -> StopResult:
        row, rec = self._get_row_and_raw(state.root_id)
        return self.backend.terminal_query(row, rec, state)

    def endpoint_y_query(self, root_id: str, seq: list[tuple[int, int]]) -> dict[str, Any]:
        """Evaluate canonical endpoint Y independently of whether X succeeded (for parity & open-loop verification)."""
        row, rec = self._get_row_and_raw(root_id)
        ids = row["inputs"]["ids"]
        if self.domain == "2d":
            self.backend.boot()
            self.backend._sync_geom(rec)
            seq_obj = [(ids[int(o)], int(d)) for o, d in seq]
            y_key = self.backend.T.ykey(root_id, rec, seq_obj)
            if y_key not in self.backend.y_endpoint_cache:
                cache = self.backend._get_cache(root_id)
                self.backend.y_endpoint_cache[y_key] = self.backend.T.y_query(
                    self.backend.E, root_id, rec, seq_obj, cache, out=self.backend.witness_dir
                )
            yr = self.backend.y_endpoint_cache[y_key]
            return {"y": yr.get("y"), "status": yr.get("teacher_status"), "witness": yr.get("target_witness")}
        else:
            self.backend.boot()
            canon_rc = {
                **{k: [int(v[0]), int(v[1])] for k, v in rec["initial_cells"].items()},
                **{ids[int(o)]: [int(d) // 6, int(d) % 6] for o, d in seq},
            }
            ekey = f"{root_id}|{json.dumps(sorted(canon_rc.items()))}"
            if ekey not in self.backend.y_endpoint_cache:
                self.backend.y_endpoint_cache[ekey] = self.backend.F.capped(self.backend.F.run_y, rec, canon_rc)
            yr = self.backend.y_endpoint_cache[ekey]
            if yr.get("resolution") != "EVALUATED":
                return {"y": None, "status": yr.get("resolution"), "witness": None}
            return {
                "y": int(yr["y"]),
                "status": yr.get("status") or ("VERIFIED" if yr["y"] == 1 else "FAILED"),
                "witness": (yr.get("witnesses") or [None])[0],
            }

    def execute_complete_sequence(self, root_id: str, seq: list[tuple[int, int]], seed: int = 0) -> dict[str, Any]:
        """Run `reset -> transition -> ... -> terminal_query` for `seq` (`0 <= len(seq) <= 3`).
        If an intermediate `transition` fails at step `j`, `x=0` (`failed_phase=f'relocation:{j}'`),
        and `y` is still evaluated on the canonical endpoint `End(S0, seq)`.
        """
        st = self.reset(root_id, seed=seed)
        step_results = []
        for j, act in enumerate(seq):
            sr = self.transition(st, (int(act[0]), int(act[1])))
            step_results.append(sr)
            if sr.status != "EXECUTED":
                yq = self.endpoint_y_query(root_id, seq)
                y_val = yq["y"]
                x_val = 0 if sr.status == "PHYSICALLY_FAILED" else None
                z_val = int(x_val == 1 and y_val == 1) if (x_val in (0, 1) and y_val in (0, 1)) else None
                return {
                    "root_id": root_id,
                    "seq": [[int(o), int(d)] for o, d in seq],
                    "status": "DECIDED" if z_val is not None else "UNRESOLVED",
                    "x": x_val,
                    "y": y_val,
                    "z": z_val,
                    "failed_phase": f"relocation:{j}",
                    "failure_kind": sr.failure_kind,
                    "teacher_status": sr.teacher_status,
                    "y_status": yq["status"],
                    "step_results": step_results,
                    "stop_result": None,
                }
            st = sr.next_state
        stop_res = self.terminal_query(st)
        return {
            "root_id": root_id,
            "seq": [[int(o), int(d)] for o, d in seq],
            "status": stop_res.status,
            "x": stop_res.x_terminal,
            "y": stop_res.y_target,
            "z": stop_res.z_outcome,
            "failed_phase": stop_res.failed_phase,
            "failure_kind": stop_res.failure_kind,
            "teacher_status": stop_res.connector_status,
            "y_status": stop_res.y_status,
            "step_results": step_results,
            "stop_result": stop_res,
        }

    @staticmethod
    def clone_or_serialize(state: FullState) -> bytes:
        return pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def restore(blob: bytes) -> FullState:
        return pickle.loads(blob)
