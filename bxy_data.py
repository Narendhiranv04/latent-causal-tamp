"""Approach B X/Y (Approach_B_Final_Methodology_2026-10-31): data interface over the existing BD_GEN_V1 2D roots (read-only).

Canonical query identities (methodology §2, §3.2, §4.4):
  X:{root}:{o>c.o>c}   one ordered physical prefix r_1:t (relocations from S0, q0, achieved state carried, terminal connector to q_ref)
  Y:{root}:{o>c...}    one hypothetical edited scene S^q = final object poses of a prefix (sorted moved objects); target from q_ref = q0
Two orders with identical final poses share one Y key; every distinct ordered prefix has its own X key.

Observations taken from the immutable records only where their semantics match:
  Y  labels.original (empty edit) and labels.D (SCENE_TARGET_ONLY: target from q0 in the edited scene, same teacher and budget)
  X  0 for the shortest prefix r_1:j+1 of a B sequence whose relocation step j failed (bd_2d teacher = p16_common.verify_sequence,
     deterministic, fixed per-query budget: the prefix query performs exactly the same failing attempt; the connector is never reached).
     No X = 1 exists in BD_GEN_V1 (no prefix was ever tested with the terminal connector to q_ref); X of the empty repair is 1 by
     definition (methodology §2.2) and is a constant, not a variable.
  B  whole-sequence outcomes (target from the ACHIEVED state) stay the legacy LB targets and the external full-execution check.
Unattempted queries are absent, never zeros. The sidecar is versioned and written next to the run, never into the dataset."""
from __future__ import annotations

import collections
import hashlib
import json
import os
from pathlib import Path

import bd_core as bc

DATA = Path(os.environ.get("BXY_DATA", "/home/naren/Desktop/rss_ebm_dataset_snapshot/20261031_mock2d_5000_full"))
OUT = Path("runs/approach_b/bxy")
SIDECAR = "BXY_SIDECAR_V1"
X_TEACHER = "BD2D_TEACHER_V1:p16_common.verify_sequence(greedy cheapest mode)+terminal connector to q_ref=q0"


def sig(pairs) -> str:
    return ".".join(f"{o}>{int(c)}" for o, c in pairs) or "empty"


def roots(data=DATA) -> dict:
    """{root_id: record} for every accepted root file (sorted, read-only)."""
    return {p.stem: json.loads(p.read_text()) for p in sorted((Path(data) / "roots").glob("*.json"))}


def data_hash(data=DATA) -> str:
    h = hashlib.sha256()
    for p in sorted((Path(data) / "roots").glob("*.json")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return "sha256:" + h.hexdigest()


def split_of(rec) -> str:
    """The generator's own IID family-grouped rule (bd_core.manifest), recomputed over the full root set."""
    u = int(bc.sha(["split", rec["ids"]["parent_family_id"]])[:8], 16) / 2 ** 32
    return "test" if u < 0.15 else "val" if u < 0.25 else "train"


def cells0(rec) -> dict:
    return {o["id"]: int(o["cell"]) for o in rec["scene"]["objects"]}


def endpoint(rec, seq) -> dict:
    """Final object poses after applying the ordered edits ideally (no arm); returns only the objects that moved."""
    c0, c = cells0(rec), cells0(rec)
    for o, d in seq:
        c[o] = int(d)
    return {o: v for o, v in sorted(c.items()) if v != c0[o]}


def xkey(k, seq) -> str:
    return f"X:{k}:{sig(seq)}"


def ykey(k, rec, seq=None, edit=None) -> str:
    e = endpoint(rec, seq) if edit is None else {o: int(v) for o, v in sorted(edit.items())}
    return f"Y:{k}:{sig(sorted(e.items()))}"


def catalogue(rec) -> list:
    """Frozen candidate catalogue of a root: the empty repair, then the recorded B sequences in recorded order (all kept, up to 6)."""
    out = [{"seq": [], "role": "empty", "y_full": rec["labels"]["original"]["y"], "travel": None, "failed_step": None}]
    for b in rec["labels"]["B"]:
        out.append({"seq": [(o, int(d)) for o, d in b["sequence"]], "role": b["role"], "y_full": b["y"], "travel": b["travel"],
                    "failed_step": b["failed_step"]})
    return out


def sidecar(k, rec) -> dict:
    """Versioned X/Y sidecar of one root: variables of every catalogue prefix and the observations that match the methodology."""
    cat, Y, X, conflicts = catalogue(rec), {}, {}, []

    def put(d, key, y, src):
        if key in d and d[key]["y"] != y:
            conflicts.append([key, d[key], y, src])
        d.setdefault(key, {"y": int(y), "source": src})
    put(Y, ykey(k, rec, []), rec["labels"]["original"]["y"], "labels.original")
    for e in rec["labels"]["D"]:
        put(Y, ykey(k, rec, edit=e["edit"]), e["y"], "labels.D")
    for c in cat:
        if isinstance(c["failed_step"], int):
            put(X, xkey(k, c["seq"][:c["failed_step"] + 1]), 0, "DERIVED_B_RELOCATION_FAILURE")
    xs, ys, link = set(), {ykey(k, rec, [])}, {}
    for c in cat:
        for t in range(1, len(c["seq"]) + 1):
            q = xkey(k, c["seq"][:t])
            xs.add(q)
            link[q] = ykey(k, rec, c["seq"][:t])
            ys.add(link[q])
        for t in range(len(c["seq"]) if len(c["seq"]) >= 2 else 0):     # F4 omission queries: same scorers, recomputed prefix
            om = [a for i, a in enumerate(c["seq"]) if i != t]
            q = xkey(k, om)
            xs.add(q)
            link[q] = ykey(k, rec, om)
            ys.add(link[q])
    return {"version": SIDECAR, "root": k, "x_teacher": X_TEACHER, "x_vars": sorted(xs), "y_vars": sorted(ys | set(Y)), "x_to_y": link,
            "x_obs": X, "y_obs": Y, "conflicts": conflicts, "catalogue": [{**c, "seq": [list(a) for a in c["seq"]],
                                                                          "x": xkey(k, c["seq"]) if c["seq"] else None, "y": ykey(k, rec, c["seq"])} for c in cat]}


def coverage(R=None) -> dict:
    """Schema and supervision coverage per split (counts of variables and observations; no label-distribution analysis)."""
    R = R or roots()
    out = {s: collections.Counter() for s in ("train", "val", "test")}
    fam = collections.defaultdict(set)
    for k, rec in R.items():
        s, sc = split_of(rec), sidecar(k, rec)
        fam[rec["ids"]["parent_family_id"]].add(s)
        c = out[s]
        c["roots"] += 1
        c["candidates_nonempty"] += len(sc["catalogue"]) - 1
        for x in sc["catalogue"][1:]:
            c[f"len_{len(x['seq'])}"] += 1
            c["full_check_observed"] += x["y_full"] is not None
            c["legacy_travel_witnessed"] += x["travel"] is not None
            c["cand_endpoint_y_observed"] += x["y"] in sc["y_obs"]
            c["cand_full_x_observed"] += x["x"] in sc["x_obs"]
        c["x_vars"] += len(sc["x_vars"])
        c["y_vars"] += len(sc["y_vars"])
        c["x_obs"] += len(sc["x_obs"])
        c["x_obs_positive"] += sum(v["y"] == 1 for v in sc["x_obs"].values())
        c["y_obs"] += len(sc["y_obs"])
        c["paired_xy_obs"] += sum(1 for q in sc["x_obs"] if sc["x_to_y"].get(q) in sc["y_obs"])
        c["conflicts"] += len(sc["conflicts"])
        c[f"verified_K_{rec['verified_K']}"] += 1
        c[f"start_{rec['start_stratum']}"] += 1
    return {"splits": {s: dict(sorted(v.items())) for s, v in out.items()}, "families_straddling_splits": sum(len(v) > 1 for v in fam.values())}


def build(out=OUT) -> dict:
    """Phase 0 provenance + sidecar file (BXY_SIDECAR_V1) for every root."""
    R = roots()
    old = json.loads((DATA / "SPLITS.json").read_text())["splits"]["iid"]
    man = {"data": str(DATA), "data_hash": data_hash(), "roots": len(R), "generator_version": sorted({r["ids"]["generator_version"] for r in R.values()}),
           "label_protocol": sorted({r["ids"]["label_protocol"] for r in R.values()}), "teacher_version": sorted({r["ids"]["teacher_version"] for r in R.values()}),
           "split": {k: split_of(r) for k, r in R.items()},
           "stale_SPLITS_json": {"roots_listed": len(old), "agree_with_recomputed": all(split_of(R[k]) == v for k, v in old.items() if k in R)},
           "coverage": coverage(R), "sidecar_version": SIDECAR, "x_teacher": X_TEACHER}
    out.mkdir(parents=True, exist_ok=True)
    (out / "SIDECAR.json").write_text(json.dumps({k: sidecar(k, r) for k, r in R.items()}, indent=1, sort_keys=True))
    (out / "P0_MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    return man


if __name__ == "__main__":
    m = build()
    print(json.dumps({k: v for k, v in m.items() if k != "split"}, indent=1))
