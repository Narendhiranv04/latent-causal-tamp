#!/usr/bin/env python3
"""Seal LEGOLAS_FINAL_v1 learning/test memberships:  $PYG seal.py RELEASE_DIR [ANNEX_NAME]  -> R10_DATASET_SEAL.json (or annex seal)."""
import hashlib, json, sys, time
from pathlib import Path
rel = Path(sys.argv[1])
files = sorted(p for p in rel.rglob("*") if p.is_file() and not p.name.startswith("R10_DATASET_SEAL") and "annex" not in p.parts)
S = {"release": "LEGOLAS_FINAL_v1", "sealed_utc": time.strftime("%FT%TZ", time.gmtime()), "host": "gvlab2",
     "files": {str(p.relative_to(rel)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
     "note": "learning (TRAIN/VAL views, Q2, local split) and evaluation memberships (TEST_SHORT, BENCH_*, DEV_EXPOSED, QUARANTINE) frozen; "
             "TEST_FEAS_3D is a prospectively specified annex (r10/FEAS_PROTOCOL.json) sealed separately on collection completion"}
S["release_sha256"] = hashlib.sha256(json.dumps(S["files"], sort_keys=True).encode()).hexdigest()
(rel / "R10_DATASET_SEAL.json").write_text(json.dumps(S, indent=1))
print(S["release_sha256"], len(S["files"]))
