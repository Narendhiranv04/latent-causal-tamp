"""R3 shared paths, ceilings and root lineage / exposure (evaluator side).  Reuses r2.common (paths, metrics) and r24 (labels, DP)."""
from __future__ import annotations

import glob, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent), str(HERE.parent / "r2"), str(HERE.parent / "r24")]
import common as C  # noqa: E402
import labels as LB  # noqa: E402

O = C.FIG3 / "r3"
K45 = C.NW / "k45/cohort/roots"
# cumulative R3 ceilings (instruction section 8); counts include failed / censored attempts; no borrowing between reserves
CEIL = {"3d": {"R3.0": (40, 2.0), "R3.1": (1000, 20.0), "R3.1_pilot": (600, None), "REGR": (60, 3.0), "R3.4": (80, 4.0), "R3.5": (120, 6.0)},
        "2d": {"R3.0": (40, 2.0), "R3.1_diag": (60, 2.0), "R3.1_targeted": (600, 8.0), "R3.1_gen": (4000, 24.0), "REGR": (80, 3.0),
               "R3.4": (180, 5.0), "R3.5": (300, 6.0)}}
GPU_H = {"train": 6.0, "eval": 2.0}
MAX_WORKERS = 16


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def k45_roots():
    return {Path(g).stem: json.loads(Path(g).read_text()) for g in sorted(glob.glob(str(K45 / "*.json")))}


def job_roots(dom):
    """Root ids that received physical queries in R1 / R2.1-2.3 / K45 / R2.4 (every archived non-TEST source + the R2.4 jobs)."""
    out = {}
    src = list(LB.sources(dom)) + [(C.FIG3 / "r24" / f"jobs_24_{dom}.json", None, "R2.4")]
    for jf, _, tag in src:
        if not Path(jf).exists():
            continue
        J = json.loads(Path(jf).read_text())
        J = J if isinstance(J, list) else [x for v in J.values() for x in v]
        for j in J:
            try:
                rid = LB.rid_of(dom, j)
            except Exception:  # noqa: BLE001
                continue
            out.setdefault(rid, set()).add(tag)
    return out


def exposure(dom, rows):
    """-> dict: exposed root ids (with tags), DEV lineage roots/families (K45 cohort + ancestors), and the family sets to exclude.
    dev_fams: never train / validate / replay.  diag_fams: exposed to physical diagnostics only -> excluded from new TRAIN_SCALE / VAL_SCALE."""
    jr = job_roots(dom)
    fam = lambda rid: rows[rid]["parent_family_id"] if rid in rows else None  # noqa: E731
    dev_roots, dev_fams = set(), set()
    roster = [json.loads(l)["root_id"] for l in open(C.R2 / "r23" / f"roster_{dom}.jsonl")]
    if dom == "3d":
        K = k45_roots()
        for rid, r in K.items():
            dev_roots.add(rid); dev_fams.add(r["ids"].get("parent_family_id"))
            p = (r.get("k45") or {}).get("parent_root_id")
            while p:
                dev_roots.add(p)
                if p in K:
                    dev_fams.add(K[p]["ids"].get("parent_family_id")); p = (K[p].get("k45") or {}).get("parent_root_id")
                else:
                    p = None
    dev_roots |= set(roster)
    dev_fams |= {fam(r) for r in dev_roots if fam(r)}
    diag_fams = {fam(r) for r in jr if fam(r)} | dev_fams
    return {"job_roots": {k: sorted(v) for k, v in jr.items()}, "dev_roots": sorted(dev_roots), "dev_fams": sorted(f for f in dev_fams if f),
            "diag_fams": sorted(f for f in diag_fams if f), "roster": roster}
