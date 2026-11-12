#!/usr/bin/env python3
"""Approach B final: data handoff contract (plan.md section 2).  Runs on gvlab over the read-only mirror of the laptop artifacts.

    python contracts.py handoff      verify packages + root hashes, write the qualified-training exception, evaluation masks, compiled per-domain
                                     learner data and the immutable snapshot lock (snapshot/<id>/, read-only afterwards)
    python contracts.py check        re-verify an existing snapshot (hashes, schema, split hygiene) -> LOADER_SCHEMA_REPORT.json

Compiled data (one JSON line per selected root, 2D 5,000 / 3D 2,500): learner-visible inputs only (object coordinates / attributes, target, goal,
q_ref context, legal cells) + labels kept in a separate block (finalized X per ordered sequence, Y per endpoint, legacy labels as metadata) + the
evaluation masks.  Labels never enter the learner inputs; legacy K is metadata only (QUALIFIED_TRAINING_EXCEPTION_V1)."""
from __future__ import annotations

import collections, hashlib, json, math, os, stat, sys, time
from pathlib import Path

LAPTOP = "/home/naren/Desktop"
ROOT = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
MIR = ROOT / "mirror"
G = MIR / "boltzmann_lfd/final_dataset_generation"
GATE, V4 = G / "FINAL_READINESS_GATE", G / "FINAL_3D_DATASET_V4"
SEL2 = G / "k3_hard/2D_K3_STRENGTH_SELECTION_V3.json"
DS2 = MIR / "rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota"
SRC3 = MIR / "rss3d_final_src"
PACKAGES = [GATE, V4, G / "k3_hard/K3_HARD_ORDER_V1", G / "FINAL_DATASET_SELECTION_MANIFESTS"]
QREF3 = [-1.345029, -0.632166, 0.221281, 2.024222, 0.267756, 2.629261, 2.210774]      # SHELF66V3 q_ready = q_ref (bwlphys.QREF_AUDIT)
X0_3D, PITCH_3D = 0.42, 0.075
BASE2D = (-0.14, 0.32)                                                               # planar 3R base (dataset README)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def mp(p):
    """Laptop absolute path recorded in a manifest -> mirror path."""
    p = str(p)
    return MIR / p[len(LAPTOP) + 1:] if p.startswith(LAPTOP) else Path(p)


def cell3(rc):
    return [X0_3D + (rc[0] - 2.5) * PITCH_3D, (rc[1] - 2.5) * PITCH_3D]


def okey(order):
    return "".join(str(o)[-1] for o in order)


# ------------------------------------------------------------------------------------------------ verification
def verify_packages():
    out = {}
    for d in PACKAGES:
        bad, n = [], 0
        for line in (d / "SHA256SUMS").read_text().splitlines():
            h, name = line.split(None, 1)
            n += 1
            if sha(d / name.strip()) != h:
                bad.append(name)
        out[str(d.relative_to(MIR))] = {"files": n, "mismatch": bad}
    return out


# ------------------------------------------------------------------------------------------------ per-domain learner views
def view2d(rec):
    sc = rec["scene"]
    lat = sc["lattice"]
    ids = [o["id"] for o in sc["objects"]]
    tid = next(i for i, o in enumerate(sc["objects"]) if o["kind"] == "target" or o["id"] == "t0")
    cols, pitch = lat["cols"], lat["pitch_m"]
    cxy = lambda c: [pitch * (c % cols + 0.5), pitch * (c // cols + 0.5)]  # noqa: E731
    attrs = [[o["radius_m"], float(i == tid), float(o["kind"] == "obstacle"), float(o["id"] in rec["fixed_ids"])] for i, o in enumerate(sc["objects"])]
    q = rec["q0"]
    return {"ids": ids, "xy0": [list(o["xy_m"]) for o in sc["objects"]], "cells0": [o["cell"] for o in sc["objects"]], "attrs": attrs, "tid": tid,
            "goal": cxy(rec["goal_cell"]), "goal_cell": rec["goal_cell"], "base": list(BASE2D),
            "ctx": [math.sin(a) for a in q] + [math.cos(a) for a in q] + cxy(rec["goal_cell"]) + [sc["robot"]["gripper_gap_m"]],
            "grid": [lat["rows"], lat["cols"]], "legal_cells": sc["legal_cells"], "q_ref": q,
            "cell_xy": {str(c): cxy(c) for c in sc["legal_cells"]}}


def view3d(rec):
    ids = [o["id"] for o in rec["objects"]]
    tid = ids.index("t0")
    attrs = [[float(o["shape"] == "box"), float(o["shape"] == "cylinder"), o["size"], o["height"], float(i == tid)] for i, o in enumerate(rec["objects"])]
    tg = rec["objects"][tid]
    return {"ids": ids, "xy0": [cell3(rec["initial_cells"][o]) for o in ids], "cells0": [rec["initial_cells"][o][0] * 6 + rec["initial_cells"][o][1] for o in ids],
            "attrs": attrs, "tid": tid, "goal": cell3(rec["goal"]), "goal_cell": rec["goal"][0] * 6 + rec["goal"][1], "base": [0.0, 0.0],
            "ctx": [math.sin(a) for a in QREF3] + [math.cos(a) for a in QREF3] + cell3(rec["goal"]) + [tg["size"], tg["height"], float(tg["shape"] == "box")],
            "grid": [6, 6], "legal_cells": list(range(36)), "q_ref": QREF3, "cell_xy": {str(c): cell3((c // 6, c % 6)) for c in range(36)}}


def dest2(c):
    return int(c)


def dest3(d):
    return int(d[0]) * 6 + int(d[1])


# ------------------------------------------------------------------------------------------------ compile
def compile_domain(dom, sel_rows, labels, path_of, flags):
    """-> list of per-root dicts: inputs / queries / labels / masks.  labels: rows of the domain's finalized label manifest."""
    by = collections.defaultdict(list)
    for l in labels:
        by[l["root_id"]].append(l)
    lay_of = {r.get("layout_root_id") or r["root_id"]: r["root_id"] for r in sel_rows}
    out, issues = [], collections.Counter()
    for r in sel_rows:
        rid, K = r["root_id"], r["K"]
        p = path_of(r)
        raw = p.read_bytes()
        h = hashlib.sha256(raw).hexdigest()
        want = r.get("root_sha256") or r.get("source_sha256")
        if want and want != h:
            issues["root_sha_mismatch"] += 1
        rec = json.loads(raw)
        v = view2d(rec) if dom == "2D" else view3d(rec)
        idx = {o: i for i, o in enumerate(v["ids"])}
        dcell = dest2 if dom == "2D" else dest3
        rows = by.get(rid, [])
        if dom == "3D" and (r.get("layout_root_id") or rid) != rid:
            rows = rows + [l for l in by.get(r["layout_root_id"], []) if l["row_kind"].startswith("EMPTY")]
        Xq, Yq = {}, {}
        for l in rows:
            seq = [[idx[o], dcell(d)] for o, d in l["relocations"]]
            ek = json.dumps(sorted(map(tuple, seq)))
            if l["y"] in (0, 1):
                if Yq.setdefault(ek, {"edit": sorted(map(list, seq)), "y": l["y"], "kinds": []})["y"] != l["y"]:
                    issues["y_conflict"] += 1
                Yq[ek]["kinds"].append(l["row_kind"])
            if seq:
                xk = json.dumps(seq)
                if l["x"] in (0, 1):
                    q = Xq.setdefault(xk, {"seq": seq, "x": l["x"], "kind": l["row_kind"], "x_phase": l.get("x_phase"), "legacy_y": l.get("legacy_y"),
                                           "x_witnesses": l.get("x_witnesses"), "y_witness": l.get("y_witness"), "x_provenance": l.get("x_provenance")})
                    if q["x"] != l["x"]:
                        issues["x_conflict"] += 1
                else:
                    issues["x_missing"] += 1
        sel_orders = [q for q in Xq.values() if q["kind"] == "SELECTED_ASSIGNMENT_ORDER"]
        x_strength = sum(q["x"] for q in sel_orders)
        y_sel = next((Yq[json.dumps(sorted(map(tuple, q["seq"])))]["y"] for q in sel_orders), None)
        has_x1y1 = any(q["x"] == 1 and Yq[json.dumps(sorted(map(tuple, q["seq"])))]["y"] == 1 for q in sel_orders)
        om_x1y1 = any(q["kind"] == "OMISSION_YNEG" and q["x"] == 1 and Yq[json.dumps(sorted(map(tuple, q["seq"])))]["y"] == 1 for q in Xq.values())
        flag = flags.get(rid)
        kstat = ("NOT_APPLICABLE_K0" if K == "0" else "NOT_APPLICABLE_NONE" if K == "NONE" else
                 "UNCERTIFIED_NO_FINALIZED_LABELS" if not sel_orders else
                 "FLAGGED_SHORTER_REPAIR_PROVEN" if om_x1y1 else "FLAGGED_NO_FINALIZED_X1Y1_ORDER" if not has_x1y1 else
                 "LEGACY_MINIMAL_AND_FINALIZED_REPAIR_VERIFIED")
        if flag and not kstat.startswith("FLAGGED"):
            issues["flag_mismatch"] += 1
        masks = {"train_prediction": True,                                               # finalized X/Y rows are sound for every root
                 "eval_repair": kstat == "LEGACY_MINIMAL_AND_FINALIZED_REPAIR_VERIFIED",
                 "eval_task": K in ("1", "2", "3"), "eval_noop": K == "0" and Yq.get("[]", {}).get("y") == 1, "eval_abstain": K == "NONE"}
        out.append({"root_id": rid, "domain": dom, "split": r["split"], "K_legacy": K, "layout_root_id": r.get("layout_root_id") or rid,
                    "parent_family_id": rec["ids"].get("parent_family_id"), "source": r.get("source"), "root_sha256": h,
                    "inputs": v, "labels": {"X": list(Xq.values()), "Y": list(Yq.values())},
                    "meta": {"K_status": kstat, "x_strength_finalized": x_strength if K in ("2", "3", "1") else None,
                             "n_orders": len(sel_orders), "y_selected_endpoint": y_sel,
                             "legacy_strength": r.get("n_success") if dom == "2D" else r.get("legacy_n_success"), "flag": flag},
                    "masks": masks})
    return out, issues


LABELFILL = ROOT / "labelfill3d"


def labelfill_rows(sel3):
    """3D K1 / K0 label completion (labelfill3d.py): fin3d xy results admitted only where the independent rpl3d replay AGREES."""
    if not (LABELFILL / "replay.jsonl").exists():
        return [], {}
    agree = {}
    for l in open(LABELFILL / "replay.jsonl"):
        r = json.loads(l)
        for q in r["results"]:
            agree[(r["root_id"], q["q"])] = q["verdict"] in ("AGREE", "AGREE_VALUE_PHASE_DIFFERS")
    split = {r["root_id"]: r["split"] for r in sel3}
    rows, st = [], collections.Counter()
    for l in open(LABELFILL / "fin3d_xy.jsonl"):
        r = json.loads(l)
        rid = r["root_id"]
        y = r.get("y") or {}
        yok = y.get("resolution") == "EVALUATED" and agree.get((rid, "Y"), False)
        for x in r.get("x", []):
            xok = x.get("resolution") == "EVALUATED" and agree.get((rid, "X"), False)
            st["K1_x_admitted" if xok else "K1_x_not_admitted"] += 1
            rows.append({"row_kind": "SELECTED_ASSIGNMENT_ORDER", "root_id": rid, "K": "1", "split": split[rid], "relocations": x["order"],
                         "x": x["x"] if xok else None, "x_phase": x.get("phase"), "x_witnesses": x.get("witnesses"), "y": y.get("y") if yok else None,
                         "x_provenance": "FIN3D_X_LABELFILL_REPLAYED", "y_provenance": "FIN3D_Y_LABELFILL_REPLAYED", "legacy_y": 1})
        if not r.get("x"):
            st["K0_y_admitted" if yok else "K0_y_not_admitted"] += 1
            rows.append({"row_kind": "EMPTY_SEQUENCE_K0", "root_id": rid, "K": "0", "split": split[rid], "relocations": [], "x": 1,
                         "y": y.get("y") if yok else None, "x_provenance": "EMPTY_SEQUENCE", "y_provenance": "FIN3D_Y_LABELFILL_REPLAYED"})
    st["sha256"] = hashlib.sha256((LABELFILL / "fin3d_xy.jsonl").read_bytes() + (LABELFILL / "replay.jsonl").read_bytes()).hexdigest()
    return rows, dict(st)


def handoff():
    t0 = time.time()
    snapdir = ROOT / "snapshot"
    pk = verify_packages()
    assert all(not v["mismatch"] for v in pk.values()), pk
    ready = json.loads((GATE / "FINAL_TRAINING_READINESS.json").read_text())
    corr3 = json.loads((GATE / "manifests/PROPOSED_CORRECTION_MANIFEST.json").read_text())
    corr2 = json.loads((GATE / "manifests/2D_PROPOSED_CORRECTIONS.json").read_text())
    flags = {c["original_root_id"]: "3D:" + c["reason"].split(" ")[0] for c in corr3["corrections"]}
    flags.update({c["root_id"]: "2D:K_REPAIR_UNVERIFIED_UNDER_FINALIZED_PROTOCOL" for c in corr2["K_REPAIR_UNVERIFIED_UNDER_FINALIZED_PROTOCOL"]})
    flags.update({c[0]: "2D:K_CONTRADICTION_SHORTER_REPAIR" for c in corr2["K_CONTRADICTION_SHORTER_REPAIR"]})
    sel2 = json.loads(SEL2.read_text())["rows"]
    sel3 = json.loads((V4 / "FINAL_3D_SELECTION_MANIFEST.json").read_text())["rows"]
    lab2 = json.loads((GATE / "manifests/2D_FINAL_XY_LABEL_MANIFEST.json").read_text())["rows"]
    lab3 = json.loads((GATE / "manifests/3D_FINAL_XY_LABEL_MANIFEST_WITH_REPLAY.json").read_text())["rows"]
    fill, fill_stats = labelfill_rows(sel3)
    lab3 = lab3 + fill
    p2 = lambda r: DS2 / "raw/roots" / f"{r['root_id']}.json" if r["source"] == "ORIGINAL_SELECTED" else mp(r["host_store"]) / "roots" / f"{r['root_id']}.json"  # noqa: E731
    p3 = lambda r: mp(r["path"]) if r["path"].startswith("/") else SRC3 / r["path"]  # noqa: E731
    d2, i2 = compile_domain("2D", sel2, lab2, p2, flags)
    d3, i3 = compile_domain("3D", sel3, lab3, p3, flags)
    sid = hashlib.sha256(json.dumps({"packages": pk, "roots2": [r["root_sha256"] for r in d2], "roots3": [r["root_sha256"] for r in d3],
                                     "readiness": sha(GATE / "FINAL_TRAINING_READINESS.json"), "labelfill3d": fill_stats.get("sha256")},
                                    sort_keys=True).encode()).hexdigest()[:16]
    out = snapdir / f"abf_{sid}"
    if out.exists():
        raise SystemExit(f"REFUSED: {out} exists (immutable)")
    out.mkdir(parents=True)
    for name, rows in (("data2d.jsonl", d2), ("data3d.jsonl", d3)):
        with open(out / name, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    flagged = sorted(flags)
    qual = {"version": "QUALIFIED_TRAINING_EXCEPTION_V1", "date": "2026-11-12", "authorized_by": "user (message of 2026-11-12, Option 1)",
            "original_readiness": {"file": "FINAL_READINESS_GATE/FINAL_TRAINING_READINESS.json", "sha256": sha(GATE / "FINAL_TRAINING_READINESS.json"),
                                   "status": ready["status"], "status_is_unchanged": True, "k_inconsistency_rates": ready["k_inconsistency_rates"]},
            "exception": ["the original BLOCKED verdict (G13 K consistency, 2D rate 2.18 % > 1 %) is retained, not rewritten",
                          "legacy K is historical class metadata only, never a certified minimum",
                          "models train exclusively on finalized X/Y outcomes; all 70 flagged scenes and their physical observations are kept",
                          "flagged scenes are excluded from the minimal-repair (Repair) denominator; they stay eligible for prediction training and Task evaluation"],
            "flagged_scenes": {r: flags[r] for r in flagged}, "n_flagged": len(flagged),
            "repair_certificate_definition": "LEGACY_MINIMAL_AND_FINALIZED_REPAIR_VERIFIED: the legacy teacher's verified minimal K (restricted-grammar, legacy "
                                             "protocol), a finalized X=1/Y=1 order at that K, and no finalized shorter repair found by the omission check. "
                                             "Relative certificate: not a proof of global minimality under the finalized protocol."}
    (out / "QUALIFIED_TRAINING_EXCEPTION.json").write_text(json.dumps(qual, indent=1))
    masks = {r["root_id"]: {**r["masks"], "domain": r["domain"], "split": r["split"], "K_legacy": r["K_legacy"], "K_status": r["meta"]["K_status"]} for r in d2 + d3}
    (out / "EVALUATION_MASKS.json").write_text(json.dumps(masks))
    files = {n: sha(out / n) for n in ("data2d.jsonl", "data3d.jsonl", "QUALIFIED_TRAINING_EXCEPTION.json", "EVALUATION_MASKS.json")}
    lock = {"snapshot_id": f"abf_{sid}", "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "packages_verified": pk,
            "selection_2d": {"file": str(SEL2.relative_to(MIR)), "sha256": sha(SEL2)}, "selection_3d": {"file": "FINAL_3D_DATASET_V4/FINAL_3D_SELECTION_MANIFEST.json", "sha256": sha(V4 / "FINAL_3D_SELECTION_MANIFEST.json")},
            "labels_2d_sha256": sha(GATE / "manifests/2D_FINAL_XY_LABEL_MANIFEST.json"), "labels_3d_sha256": sha(GATE / "manifests/3D_FINAL_XY_LABEL_MANIFEST_WITH_REPLAY.json"),
            "teachers": {"2D": "BXY_X_TEACHER_V1 / BXY_Y_TEACHER_V1 (bxy_teacher.py @ 68183081d)", "3D": "fin3d X (relocations + CONNECTOR_TO_QREADY_V1) / BD3DS66_Y_PLAN_V1"},
            "files": files, "issues": {"2D": dict(i2), "3D": dict(i3)}, "laptop_prefix_mapped": [LAPTOP, str(MIR)], "labelfill3d": fill_stats}
    (out / "data_snapshot.lock.json").write_text(json.dumps(lock, indent=1))
    for p in sorted(out.rglob("*"), reverse=True) + [out]:
        p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    print(json.dumps({"snapshot": str(out), "issues": lock["issues"], "n": [len(d2), len(d3)], "s": round(time.time() - t0, 1)}))
    return out


def check(snap):
    snap = Path(snap)
    lock = json.loads((snap / "data_snapshot.lock.json").read_text())
    rep = {"snapshot_id": lock["snapshot_id"], "files_ok": {n: sha(snap / n) == h for n, h in lock["files"].items()}, "domains": {}}
    for dom, name in (("2D", "data2d.jsonl"), ("3D", "data3d.jsonl")):
        rows = [json.loads(l) for l in open(snap / name)]
        c = collections.Counter
        fam, lay = collections.defaultdict(set), collections.defaultdict(set)
        xy = c()
        for r in rows:
            fam[r["parent_family_id"]].add(r["split"]); lay[r["layout_root_id"]].add(r["split"])
            ylab = {json.dumps(sorted(map(tuple, y["edit"]))): y["y"] for y in r["labels"]["Y"]}
            for q in r["labels"]["X"]:
                yv = ylab.get(json.dumps(sorted(map(tuple, q["seq"]))))
                xy[(q["kind"], r["split"], f"X={q['x']},Y={yv}")] += 1
            if r["K_legacy"] in ("1", "2", "3") and not any(not y["edit"] for y in r["labels"]["Y"]):
                xy[("missing_empty_endpoint_Y", r["split"], r["K_legacy"])] += 1
        n_obj = [len(r["inputs"]["ids"]) for r in rows]
        rep["domains"][dom] = {"roots": len(rows), "by_K_split": {f"{k}|{s}": v for (k, s), v in sorted(c((r["K_legacy"], r["split"]) for r in rows).items())},
                               "family_split_conflicts": sum(len(v) > 1 for v in fam.values()), "layout_split_conflicts": sum(len(v) > 1 for v in lay.values()),
                               "x_rows": sum(len(r["labels"]["X"]) for r in rows), "y_endpoints": sum(len(r["labels"]["Y"]) for r in rows),
                               "xy_cells": {"|".join(k): v for k, v in sorted(xy.items())},
                               "K_status": dict(c(r["meta"]["K_status"] for r in rows)), "masks": {m: sum(r["masks"][m] for r in rows) for m in rows[0]["masks"]},
                               "objects_per_root": [min(n_obj), max(n_obj)], "attr_dim": len(rows[0]["inputs"]["attrs"][0]), "ctx_dim": len(rows[0]["inputs"]["ctx"]),
                               "max_seq_len": max(len(q["seq"]) for r in rows for q in r["labels"]["X"]) if any(r["labels"]["X"] for r in rows) else 0}
    rep["pass"] = all(rep["files_ok"].values()) and all(d["family_split_conflicts"] == 0 and d["layout_split_conflicts"] == 0 for d in rep["domains"].values())
    (ROOT / "runs").mkdir(exist_ok=True)
    (ROOT / "runs" / f"LOADER_SCHEMA_REPORT_{lock['snapshot_id']}.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "domains"}), json.dumps({d: {k: v[k] for k in ("roots", "family_split_conflicts", "layout_split_conflicts", "x_rows", "y_endpoints", "K_status", "masks")} for d, v in rep["domains"].items()}))
    return rep


if __name__ == "__main__":
    if sys.argv[1:2] == ["handoff"]:
        check(handoff())
    elif sys.argv[1:2] == ["check"]:
        check(sys.argv[2])
    else:
        raise SystemExit(__doc__)
