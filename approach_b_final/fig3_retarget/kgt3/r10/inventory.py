#!/usr/bin/env python3
"""R10.0 inventory + lineage graph (gvlab2; metadata/geometry only - no labels of evaluation tracks are read beyond their label *status*).

Predeclared identity rules (fixed before any output was inspected; see R10_DATASET_RELEASE_REPORT.md):
  L1 exact scene      : geometric fp (v34_geomfp.geom_fp: sorted per-object (cell, attrs@1e-6) + target cell + goal cell) equal.
  L2 3D instance      : 3D, N >= 3, sorted per-object attrs multiset (rounded 1e-6, cells ignored) equal -> same physical objects (continuous
                        random dimensions), i.e. a re-arrangement / intermediate / derived scene of the same instance.
  L3 2D re-arrangement: 2D, same N, goal cell, target attrs and attrs multiset, and the (cell, attrs) multisets differ in <= 3 objects.
      REVIEW (2026-11-28, after first run, before any split decision): with discrete 2D attributes L3 links independently generated similar
      scenes (N = 4 scenes differ "in <= 3 objects" by chance) and chains them into giant components; the plan forbids conflating merely
      similar independent scenes.  L3 is therefore NOT a merge rule: it is reported as a near-duplicate sensitivity (direct neighbours per
      track pair, by N), and 2D derivation lineage comes from L1/L4 only.  First-run numbers are kept in inventory_summary_L3merge.json.
  L4 declared physical: layout_root_id, parent_root, construction parent fields.
  T  template         : parent_family_id / template_id (abstract factor template; the original split is template-level).
Physical families = connected components of L1-L4.  Template families = T.  Both are reported; partition rules use both (see split.py).

    $PYG inventory.py OUTDIR
"""
from __future__ import annotations

import collections, hashlib, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KG = HERE.parent
sys.path[:0] = [str(KG), str(KG.parent), str(KG.parent / "r3"), str(KG.parent / "r24"), str(KG.parent / "r2"), str(KG.parent.parent),
                str(KG.parent.parent / "scripts")]
NW = Path("/home/projects/long-horizon/naren_workspace")
BASE = NW / "k3abl/abf/snapshot/abf_9de85710c2a7103f"
EXP = NW / "k3abl/abf/snapshot/abf_v32_fb0eef4f5ff433ee"
V34 = NW / "fig3/final/r8a_verify"
R8B = NW / "r10/data/r8b"
Q2 = NW / "fig3/final/r7/abf/data"


def H(o):
    return hashlib.sha256(json.dumps(o, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def geom_fp(v):
    objs = sorted([int(c)] + [round(float(a), 6) for a in at] for c, at in zip(v["cells0"], v["attrs"]))
    return H([objs, int(v["cells0"][v["tid"]]), int(v["goal_cell"])])


def inst_fp(v):
    return H(sorted([round(float(a), 6) for a in at] for at in v["attrs"]))


def objs(v):
    return sorted((int(c), tuple(round(float(a), 6) for a in at)) for c, at in zip(v["cells0"], v["attrs"]))


class UF:
    def __init__(s):
        s.p = {}

    def f(s, x):
        s.p.setdefault(x, x)
        while s.p[x] != x:
            s.p[x] = s.p[s.p[x]]; x = s.p[x]
        return x

    def u(s, a, b):
        a, b = s.f(a), s.f(b)
        if a != b:
            s.p[max(a, b)] = min(a, b)


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    N = []                                    # scene nodes: dict(node, track, dom, root_id, inputs, tmpl, links)
    stats = collections.Counter()

    def add(track, dom, rid, inp, tmpl=None, links=(), extra=None):
        node = f"{track}::{rid}"
        N.append({"node": node, "track": track, "dom": dom, "root_id": rid, "inp": inp, "tmpl": tmpl, "links": [l for l in links if l],
                  **(extra or {})})
        stats[f"{dom}|{track}"] += 1

    # (1) original snapshots (base = TRAIN/VAL/TEST; expanded adds TRAIN labels only - verified below)
    base_sha = {}
    for dom in ("2d", "3d"):
        for l in open(BASE / f"data{dom}.jsonl"):
            r = json.loads(l)
            base_sha[r["root_id"]] = r["root_sha256"]
            add("ORIG_" + r["split"].upper(), dom, r["root_id"], r["inputs"], r["parent_family_id"], [r.get("layout_root_id")],
                {"K": r["K_legacy"], "source": r["source"], "masks": r.get("masks"), "K_status": r["meta"].get("K_status")})
        diff = collections.Counter()
        for l in open(EXP / f"data{dom}.jsonl"):
            r = json.loads(l)
            diff[(r["split"], base_sha.get(r["root_id"]) == r["root_sha256"])] += 1
        stats[f"{dom}|expanded_vs_base"] = str(dict(diff))
    # (2) V3.4 cohort (public inputs + evaluator metadata: template, reference VAL root)
    for dom in ("2d", "3d"):
        P = {r["root_id"]: r for r in jl(V34 / f"private_{dom}_gt.jsonl")}
        for r in jl(V34 / f"public_{dom}.jsonl"):
            p = P.get(r["root_id"], {})
            add("V34", dom, r["root_id"], r["inputs"], p.get("template_id"), [], {"K": p.get("K"), "ref_root_id": p.get("ref_root_id"),
                "kind": p.get("kind"), "ns": p.get("source_namespace")})
    # (3) R8B sealed composition roster
    Pv = {r["root_id"]: r for r in jl(R8B / "PRIVATE_r8b.jsonl")}
    for r in jl(R8B / "PUBLIC_r8b.jsonl"):
        p = Pv.get(r["root_id"], {})
        add("R8B", "3d", r["root_id"], r["inputs"], p.get("template_id") or p.get("parent_family_id"), [p.get("parent_root_id")],
            {"L_ref": p.get("L_ref"), "pkeys": sorted(p)})
    # (4) exposed development populations (3D k45 panel; 2D R5 demo families + R5.3 2D panel)
    import r53
    import r6
    for dom in ("3d", "2d"):
        try:
            for rid, row, A, W, meta in r53.panel(dom):
                add("DEV_" + ("K45" if dom == "3d" else "R53"), dom, rid, row["inputs"], None, [], {"L_ref": len(W)})
        except Exception as e:  # noqa: BLE001
            stats[f"{dom}|dev_panel_error"] = repr(e)[:200]
    for rid, row, meta in r6.roots("demo"):
        add("DEV_R5DEMO", "2d", rid, row["inputs"], None, [], {"L_ref": meta["L_ref"]})
    # (5) strict additional local supervision (exact R7 builder)
    import xlearn as XLN
    loc = {}
    for dom in ("2d", "3d"):
        E, rows, aud = XLN.build(dom)
        stats[f"{dom}|local_entries"] = len(E)
        per = collections.defaultdict(lambda: {"splits": collections.Counter(), "srcs": collections.Counter(), "fams": set(), "n": 0})
        for e in E:
            k = e["root"] if "root" in e else e.get("root_id")
            d = per[k]; d["n"] += 1; d["splits"][e["split"]] += 1; d["srcs"][e["src"]] += 1; d["fams"].add(str(e["fam"]))
        for k, d in per.items():
            fam = sorted(d["fams"])
            tm = [f.split("|", 1)[1] for f in fam if "|fam-" in f]
            add("LOCAL", dom, k, rows[k]["inputs"], tm[0] if tm else None, [], {"local_splits": dict(d["splits"]), "local_srcs": dict(d["srcs"]),
                "local_fams": fam, "n_labels": d["n"]})
        loc[dom] = {"n_entries": len(E), "entry_keys": sorted(E[0].keys()) if E else []}
    # (6) Q2 geometry-placement pretraining rows
    q2 = {}
    for dom in ("2d", "3d"):
        R = json.loads((Q2 / f"q2_{dom}" / "rows.json").read_text())
        q2[dom] = collections.Counter(R["roots"]) if "roots" in R else None
        stats[f"{dom}|q2_keys"] = str(sorted(R.keys()))[:300]
    # (6b) Q2 pool roots that are not snapshot rows (unselected dataset-pool roots): geometry from their root files, template from ids
    import contracts as CT
    MIR = Path("/home/projects/long-horizon/abf_v2/root/mirror")
    RD = {"2d": MIR / "rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/raw/roots",
          "3d": MIR / "rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass/raw/roots"}
    known = {(n["dom"], n["root_id"]) for n in N}
    for dom in ("2d", "3d"):
        R = json.loads((Q2 / f"q2_{dom}" / "rows.json").read_text())["roots"]
        import numpy as np
        sp = np.load(Q2 / f"q2_{dom}" / "features.npz")["split"]
        rs = {}
        for r, s_ in zip(R, sp):
            rs.setdefault(r, set()).add(int(s_))
        for r, ss in sorted(rs.items()):
            if (dom, r) in known:
                continue
            rec = json.loads((RD[dom] / f"{r}.json").read_text())
            v = CT.view2d(rec) if dom == "2d" else CT.view3d(rec)
            ids = rec.get("ids", {})
            add("Q2POOL_" + "/".join(["train", "val", "test"][i] for i in sorted(ss)).upper(), dom, r, v, ids.get("parent_family_id"),
                [ids.get("layout_root_id"), (rec.get("construction") or {}).get("parent_root_id")], {"q2_samples": int(sum(1 for x in R if x == r))})
    # ---------------------------------------------------------------- identity graph
    uf = UF()
    by = collections.defaultdict(list)
    for n in N:
        v = n["inp"]
        n["geom_fp"] = geom_fp(v); n["inst_fp"] = inst_fp(v); n["n_obj"] = len(v["ids"])
        uf.f(n["node"])
        by[("L1", n["dom"], n["geom_fp"])].append(n["node"])
        if n["dom"] == "3d" and n["n_obj"] >= 3:
            by[("L2", n["dom"], n["inst_fp"])].append(n["node"])
        for l in n["links"]:
            by[("L4", n["dom"], l)].append(n["node"])
        by[("L4", n["dom"], n["root_id"])].append(n["node"])      # same root id in two tracks = same scene by declaration
    linkc = collections.Counter()
    for (rule, dom, key), nodes in by.items():
        if len(nodes) > 1:
            linkc[rule] += len(nodes) - 1
            for x in nodes[1:]:
                uf.u(nodes[0], x)
    # L3: 2D re-arrangements (bucket by N, goal, target attrs, attrs multiset)
    nd = {n["node"]: n for n in N}
    b3 = collections.defaultdict(list)
    for n in N:
        if n["dom"] == "2d":
            v = n["inp"]
            b3[(n["n_obj"], int(v["goal_cell"]), tuple(round(float(a), 6) for a in v["attrs"][v["tid"]]), n["inst_fp"])].append(n["node"])
    l3 = 0
    for key, nodes in b3.items():
        O = [(x, collections.Counter(objs(nd[x]["inp"]))) for x in nodes]
        for i in range(len(O)):
            for j in range(i + 1, len(O)):
                if uf.f(O[i][0]) == uf.f(O[j][0]):
                    continue
                if key[0] - sum((O[i][1] & O[j][1]).values()) <= 3:
                    a, b = nd[O[i][0]], nd[O[j][0]]
                    for x, y in ((a, b), (b, a)):
                        x.setdefault("l3_tracks", set()).add(y["track"])
                    l3 += 1
    linkc["L3_sensitivity_pairs"] = l3
    # ---------------------------------------------------------------- summaries
    comp = collections.defaultdict(set)
    for n in N:
        n["pfam"] = "P" + hashlib.sha256(uf.f(n["node"]).encode()).hexdigest()[:12]
        comp[n["pfam"]].add(n["track"])
    tm = collections.defaultdict(set)
    for n in N:
        if n["tmpl"]:
            tm[(n["dom"], n["tmpl"])].add(n["track"])
    tracks = sorted({n["track"] for n in N})
    M = {d: {a: {b: 0 for b in tracks} for a in tracks} for d in ("2d", "3d")}
    T = {d: {a: {b: 0 for b in tracks} for a in tracks} for d in ("2d", "3d")}
    for n in N:
        for b in comp[n["pfam"]]:
            M[n["dom"]][n["track"]][b] += 1
        if n["tmpl"]:
            for b in tm[(n["dom"], n["tmpl"])]:
                T[n["dom"]][n["track"]][b] += 1
    # Q2 membership by original split
    rid_track = collections.defaultdict(set)
    for n in N:
        rid_track[(n["dom"], n["root_id"])].add(n["track"])
    q2m = {}
    for dom in q2:
        c = collections.Counter()
        for rid, k in (q2[dom] or {}).items():
            tr = sorted(rid_track.get((dom, rid), {"UNMATCHED"}))
            c["|".join(tr)] += k
        q2m[dom] = {"samples_by_track": dict(c), "roots": len(q2[dom] or {})}
    l3s = collections.Counter()
    for n in N:
        for t in n.get("l3_tracks", ()):
            l3s[f"{n['dom']}|{n['track']}->{t}|N{'<=5' if n['n_obj'] <= 5 else '6-9' if n['n_obj'] <= 9 else '>=10'}"] += 1
    S = {"l3_near_dup_rows": dict(sorted(l3s.items())), "stats": dict(stats), "link_counts": dict(linkc), "physical_overlap_rows": M, "template_overlap_rows": T, "q2": q2m, "local": loc,
         "n_physical_families": len(comp), "tracks": tracks}
    (out / "inventory_summary.json").write_text(json.dumps(S, indent=1, default=str))
    with open(out / "nodes.jsonl", "w") as f:
        for n in N:
            f.write(json.dumps({k: (sorted(v) if isinstance(v, set) else v) for k, v in n.items() if k != "inp"}, default=str) + "\n")
    print(json.dumps({k: S[k] for k in ("stats", "link_counts", "q2", "n_physical_families")}, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1])
