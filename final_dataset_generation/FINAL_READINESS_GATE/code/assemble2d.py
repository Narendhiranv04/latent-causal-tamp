#!/usr/bin/env python3
"""Assemble the 2D finalized X/Y label manifest for 2D_K3_STRENGTH_SELECTION_V3 (5,000 scenes) from:
  work/xy2d_fin.jsonl                     this gate's bxy_teacher queries (SEL / OM / EMPTY / EMPTY_PARITY / PARITY)
  k3_hard/xy2d_all.jsonl                  reused K3 hard-order X/Y (same teacher, same root file, same assignment; parity-checked here)
  root labels.original                    Y at the empty endpoint (bd_2d.t_goal from q_ref = q0, same QB) for K1-K3 / NONE (parity-checked)
  legacy per-order labels                 root permutations (new roots) or order_classification_2d/per_scene_order_classification.jsonl
  assemble2d.py  -> manifests/2D_FINAL_XY_LABEL_MANIFEST.json, work/2d_stats.json"""
import collections as C, hashlib, json
from pathlib import Path

H = Path(__file__).resolve().parent
GATE, G = H.parent, H.parent.parent
DS = Path("/home/naren/Desktop/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota")
SELF = G / "k3_hard/2D_K3_STRENGTH_SELECTION_V3.json"


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if Path(p).exists() else []


def okey(seq):
    return "".join(o[-1] for o, _ in seq)


def rpath(r):
    return DS / "raw/roots" / f"{r['root_id']}.json" if r["source"] == "ORIGINAL_SELECTED" else Path(r["host_store"]) / "roots" / f"{r['root_id']}.json"


def main():
    sel = json.loads(SELF.read_text())["rows"]
    fin = {}
    for r in jl(GATE / "work/xy2d_fin.jsonl"):
        fin[r["root_id"]] = r                                         # one line per root (resumable by key)
    for r in jl(GATE / "work/xy2d_retry.jsonl"):                     # retries of administrative wall-cap hits (appended: they override the MISSING entry)
        fin[r["root_id"]]["results"] = fin[r["root_id"]]["results"] + [q for q in r["results"] if q.get("resolution") == "EVALUATED"]
    for r in jl(GATE / "work/xy2d_empty.jsonl"):                     # finalized Y at the empty endpoint (K1-K3 / NONE roots without a parity query)
        fin.setdefault(r["root_id"], {"results": []})["results"] = fin.get(r["root_id"], {"results": []})["results"] + r["results"]
    reuse = {r["root_id"]: r for r in jl(G / "k3_hard/xy2d_all.jsonl")}
    legacy_pc = {r["root_id"]: r for r in jl(G.parent / "order_classification_2d/per_scene_order_classification.jsonl")}
    rows, st = [], C.Counter()
    parity = C.Counter()
    parity_mm, empty_mm = [], []
    strength = []
    families = C.defaultdict(set)
    ykeys = C.defaultdict(set)
    for r in sel:
        rid, K, split = r["root_id"], r["K"], r["split"]
        p = rpath(r)
        raw = p.read_bytes()
        rec = json.loads(raw)
        sha = hashlib.sha256(raw).hexdigest()
        if r.get("source_sha256") and sha != r["source_sha256"]:
            st["source_sha_mismatch"] += 1
        fam = rec["ids"].get("parent_family_id") or rid
        families[fam].add(split)
        base = {"root_id": rid, "K": K, "split": split, "source": r["source"], "layout_root_id": r.get("layout_root_id") or rid,
                "parent_family_id": fam, "root_sha256": sha}
        f = fin.get(rid, {"results": []})
        res = f["results"]
        orig = rec["labels"]["original"]
        # ---- empty endpoint (X of the empty sequence = 1 by definition)
        if K == "0":
            q = next((x for x in res if x["role"] == "EMPTY"), None)
            ok = q and q.get("resolution") == "EVALUATED"
            rows.append({**base, "row_kind": "EMPTY_SEQUENCE_K0", "order": [], "relocations": [], "x": 1, "x_provenance": "EMPTY_SEQUENCE_X_IS_1_BY_DEFINITION",
                         "y": q.get("y") if ok else None, "y_status": q.get("teacher_status") if q else None,
                         "y_replay": q.get("independent_replay") if q else None, "y_witness": q.get("target_witness") if q else None,
                         "y_provenance": "BXY_Y_TEACHER_V1(this gate)" if ok else "MISSING", "legacy_y": orig["y"]})
        else:
            q = next((x for x in res if x["role"] in ("EMPTY_PARITY", "EMPTY_ALL")), None)
            ok = q and q.get("resolution") == "EVALUATED"
            rows.append({**base, "row_kind": "EMPTY_SEQUENCE_YNEG", "order": [], "relocations": [], "x": 1, "x_provenance": "EMPTY_SEQUENCE_X_IS_1_BY_DEFINITION",
                         "y": q.get("y") if ok else None, "y_status": q.get("teacher_status") if q else None, "y_replay": q.get("independent_replay") if q else None,
                         "y_witness": q.get("target_witness") if q else None,
                         "y_provenance": "BXY_Y_TEACHER_V1(this gate)" if ok else "MISSING", "legacy_y": orig["y"],
                         "legacy_y_note": "labels.original (bd_2d.t_goal from q0 in the unedited scene), kept separately"})
            if ok:
                parity["empty_checked"] += 1
                if q.get("y") == orig["y"]:
                    parity["empty_agree"] += 1
                else:
                    empty_mm.append({"root_id": rid, "K": K, "labels_original": orig["y"], "y_query": q.get("y"), "status": q.get("teacher_status")})
        if K not in ("1", "2", "3"):
            continue
        mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
        assign = [[o, int(d)] for o, d in mini["sequence"]]
        if "permutations" in rec:
            leg = {okey(x["order"]): x.get("y") for x in rec["permutations"]}
        elif rid in legacy_pc and legacy_pc[rid].get("permutations"):
            leg = {okey(x["order"]): x.get("y") for x in legacy_pc[rid]["permutations"]}
        else:
            leg = {okey(assign): 1} if K == "1" else {}
        sx = {okey(x["seq"]): x for x in res if x["role"] == "SEL" and x["q"] == "X"}
        sy = next((x for x in res if x["role"] == "SEL" and x["q"] == "Y"), None)
        px = {okey(x["seq"]): x for x in res if x["role"] == "PARITY" and x["q"] == "X"}
        py = next((x for x in res if x["role"] == "PARITY" and x["q"] == "Y"), None)
        ru = reuse.get(rid)
        import itertools
        xs = []
        if ru and not sx:
            y = {"y": ru["y"]["y"], "status": ru["y"]["status"], "replay": ru["y"]["replay"], "prov": "REUSED_XY2D_K3HARD_V1(k3_hard/xy2d_all.jsonl)", "w": None}
            if py:
                parity["sel_y_checked"] += 1
                parity["sel_y_agree"] += int(py.get("y") == y["y"])
                if py.get("y") != y["y"]:
                    parity_mm.append({"root_id": rid, "q": "Y", "reused": y["y"], "rerun": py.get("y")})
        else:
            ok = sy and sy.get("resolution") == "EVALUATED"
            y = {"y": sy.get("y") if ok else None, "status": sy.get("teacher_status") if sy else None, "replay": sy.get("independent_replay") if sy else None,
                 "prov": "BXY_Y_TEACHER_V1(this gate)" if ok else "MISSING", "w": sy.get("target_witness") if sy else None}
            if sy and sy.get("y_key"):
                ykeys[sy["y_key"]].add(y["y"])
        for q in itertools.permutations(assign):
            k = okey(q)
            if ru and not sx:
                v = ru["x"][k]
                x = {"x": v["x"], "x_status": v["status"], "x_phase": v["phase"], "x_replay": v["replay"], "x_provenance": "REUSED_XY2D_K3HARD_V1(k3_hard/xy2d_all.jsonl)",
                     "x_witnesses": None}
                if k in px:
                    parity["sel_x_checked"] += 1
                    parity["sel_x_agree"] += int(px[k].get("y") == v["x"])
                    if px[k].get("y") != v["x"]:
                        parity_mm.append({"root_id": rid, "q": "X", "order": k, "reused": v["x"], "rerun": px[k].get("y")})
            else:
                v = sx.get(k)
                ok = v and v.get("resolution") == "EVALUATED"
                x = {"x": v.get("y") if ok else None, "x_status": v.get("teacher_status") if v else None, "x_phase": v.get("failed_phase") if v else None,
                     "x_replay": v.get("independent_replay") if v else None, "x_provenance": "BXY_X_TEACHER_V1(this gate)" if ok else ("MISSING_" + str(v.get("resolution")) if v else "MISSING"),
                     "x_witnesses": ((v.get("witness_relocations") or []) + ([v["witness_connector"]] if v.get("witness_connector") else [])) if v else None}
            xs.append(x["x"])
            rows.append({**base, "row_kind": "SELECTED_ASSIGNMENT_ORDER", "order": [o for o, _ in q], "relocations": [list(a) for a in q], **x,
                         "y": y["y"], "y_status": y["status"], "y_replay": y["replay"], "y_provenance": y["prov"], "y_witness": y["w"], "legacy_y": leg.get(k)})
        full = all(v in (0, 1) for v in xs) and y["y"] in (0, 1)
        st[f"K{K}_{'complete' if full else 'incomplete'}"] += 1
        if full:
            strength.append({"root_id": rid, "K": K, "split": split, "x_strength": sum(xs), "legacy_strength": sum(1 for v in leg.values() if v == 1) if leg else None,
                             "n_orders": len(xs), "y": y["y"]})
        # ---- omission
        oy = next((x for x in res if x["role"] == "OM" and x["q"] == "Y"), None)
        for v in (x for x in res if x["role"] == "OM" and x["q"] == "X"):
            okx = v.get("resolution") == "EVALUATED"
            oky = oy and oy.get("resolution") == "EVALUATED"
            rows.append({**base, "row_kind": "OMISSION_YNEG", "omitted": v["omitted"], "order": [o for o, _ in v["seq"]], "relocations": v["seq"],
                         "x": v.get("y") if okx else None, "x_status": v.get("teacher_status"), "x_phase": v.get("failed_phase"), "x_replay": v.get("independent_replay"),
                         "x_provenance": "BXY_X_TEACHER_V1(this gate)" if okx else "MISSING_" + str(v.get("resolution")),
                         "x_witnesses": (v.get("witness_relocations") or []) + ([v["witness_connector"]] if v.get("witness_connector") else []),
                         "y": oy.get("y") if oky else None, "y_status": oy.get("teacher_status") if oy else None, "y_replay": oy.get("independent_replay") if oy else None,
                         "y_provenance": "BXY_Y_TEACHER_V1(this gate)" if oky else "MISSING", "y_witness": oy.get("target_witness") if oy else None})
            if oy and oy.get("y_key"):
                ykeys[oy["y_key"]].add(oy.get("y"))
    split_conflict = {f: sorted(s) for f, s in families.items() if len(s) > 1}
    ycontra = {k: sorted(v, key=str) for k, v in ykeys.items() if len(v) > 1}
    out = {"version": "FINAL_2D_XY_LABELS_GATE_V1", "selection": str(SELF.relative_to(G)), "rows": rows}
    (GATE / "manifests/2D_FINAL_XY_LABEL_MANIFEST.json").write_text(json.dumps(out))
    stats = {"coverage": dict(st), "parity": dict(parity), "parity_mismatches": parity_mm, "empty_parity_mismatches": empty_mm,
             "family_split_conflicts": split_conflict, "y_key_contradictions": ycontra, "strength": strength, "n_rows": len(rows)}
    (GATE / "work/2d_stats.json").write_text(json.dumps(stats))
    print(json.dumps({k: v for k, v in stats.items() if k not in ("strength",)}, default=str)[:3000])


if __name__ == "__main__":
    main()
