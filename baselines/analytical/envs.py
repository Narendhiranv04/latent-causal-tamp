"""Boot the reusable, already-validated physical layers READ-ONLY (never edited, never copied into git):

* DISCO-Grid stage-2 stateful adapter  RepairEnv   .claude/worktrees/disco-grid-stage2/baselines/disco_grid/env.py
* NOR-Grid reference target paths      homotopy    .claude/worktrees/baseline-sorc-grid/baselines/neural_object_retrieval/homotopy.py

Data paths come from the environment (ABF_ROOT, FIN3D_CODE, FIN3D_SRC; see run.py ENV).  Private-field hygiene: the env is handed the
PUBLIC row (it never opens the snapshot, which carries K / labels) and a SCRUBBED raw record: every label / role / construction /
teacher-ledger key is deleted before the physics sees it, so no planner can read one."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WT = Path(os.environ.get("ANALYTICAL_WORKTREES", Path(__file__).resolve().parents[3]))   # .claude/worktrees (sibling worktrees)
DISCO = Path(os.environ.get("DISCO_CODE", WT / "disco-grid-stage2/baselines/disco_grid"))
NOR = Path(os.environ.get("NOR_CODE", WT / "baseline-sorc-grid/baselines/neural_object_retrieval"))

PRIVATE_RAW_KEYS = ("labels", "roles", "intended_blockers", "verified_K", "spec", "parking", "alt_parking", "observed", "ledger_observed",
                    "label_consistency", "greedy_blockers", "mechanism_pools", "construction", "teacher_calls", "teacher_cpu_s",
                    "teacher_wall_s", "reteach", "start_stratum", "empty_scene_T_swept", "empty_scene_T_witness", "empty_table_T_solve",
                    "independent_moves", "n_movable", "generator_version_plus")


_M: dict = {}


def scrub(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k not in PRIVATE_RAW_KEYS}


def _paths():
    for p in (str(NOR), str(DISCO)):
        if p not in sys.path:
            sys.path.insert(0, p)


def make_env(dom: str, witness_dir: str):
    """RepairEnv for one domain; witnesses (content-addressed trajectories) go under our own output tree."""
    _paths()
    Path(witness_dir).mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DISCO_ROOT", str(Path(witness_dir).parent / "disco_root"))
    os.environ["FIN3D_STORE"] = str(witness_dir)
    import env as EN                                                   # disco_grid/env.py (imports disco_grid/data.py as `data`)
    _M["D"] = EN.D                                                     # keep it: the 2D boot later rebinds sys.modules["data"]
    E = EN.RepairEnv(dom, witness_dir=Path(witness_dir))
    E._rows_by_id = {"__public_only__": None}                         # non-empty: the snapshot (with labels) is never loaded
    return E


def raw_path(dom: str, root_id: str) -> Path:
    """disco_grid/data.py: selection manifest -> raw root path (nothing else is read)."""
    return _M["D"].raw_root_path(dom, root_id)


def load_root(E, row: dict, path: str | None = None) -> None:
    """Register one root: the public row + the scrubbed raw record; drop every cache of earlier runs (each run starts cold)."""
    rid = row["root_id"]
    rec = json.loads(Path(path or raw_path(row["domain"], rid)).read_text())
    clean = scrub(rec)
    if "roles" in rec:                                                 # 2D teacher eligibility reads only the KEYS (movable set):
        from .contract import movable                                 # rebuild them from public attrs, values neutralised
        ids = row["inputs"]["ids"]
        clean["roles"] = {ids[i]: "movable" for i in movable(row["inputs"], row["domain"])}
        assert set(clean["roles"]) == set(rec["roles"]), "public movable set differs from the record's"
    E._rows_by_id = {rid: row}
    E._raw_by_id = {rid: clean}
    be = E.backend
    be.y_endpoint_cache = {}
    if hasattr(be, "root_caches"):
        be.root_caches = {}
