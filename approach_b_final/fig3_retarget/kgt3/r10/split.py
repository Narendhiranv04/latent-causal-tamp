#!/usr/bin/env python3
"""R10.0 canonical partition + release construction for LEGOLAS_FINAL_v1 (gvlab2).  Input: inventory nodes (inventory.py).

Partition rules (declared in R10_DATASET_RELEASE_REPORT.md before training; no model outcome is read anywhere):
  P0  Tracks: ORIG_{TRAIN,VAL,TEST} snapshot rows, Q2POOL_* (unselected dataset-pool roots used only by Q2 pretraining), LOCAL (strict local
      supervision roots), V34 -> BENCH_SHORT_{2D,3D}, R8B -> BENCH_COMP_3D, DEV_* -> DEV_EXPOSED.
  P1  Physical family = connected component of L1/L2/L4 (inventory).  A component containing a BENCH/DEV scene sends every learning node of
      that component (ORIG_TRAIN/VAL, Q2POOL, LOCAL) to QUARANTINE (LINK_EXPOSED).
  P2  A component containing an original TEST scene (ORIG_TEST or Q2POOL_TEST) together with any TRAIN/VAL/LOCAL node: all those learning nodes
      -> QUARANTINE (TEST_LINK), and its TEST rows -> QUARANTINE (TEST_HIST_TWIN: a physical twin was in historical training/selection, so
      the scene cannot be called held-out).  Otherwise TEST rows -> TEST_SHORT_{2D,3D}.
  P3  A component containing VAL and TRAIN nodes (no TEST): TRAIN-side nodes -> QUARANTINE (VAL_LINK); VAL nodes stay VAL.
  P4  LOCAL families (the local label family, e.g. 'R5.1|F004'): EXCLUDE if any member root's component is quarantined/TEST/exposed;
      else VAL if any member root links (physically, else by template) to VAL; else TRAIN if it links to TRAIN; a template that belongs to
      original TEST -> EXCLUDE; no ancestry -> the R7 local split (R5.1 family hash / KGT3 2D GATE = VAL / R4.x = TRAIN).
  P5  Exact duplicate scenes (same geometric fp = same scene and task) inside one partition -> one canonical record (lowest root id), labels
      merged by edit (asserted non-contradictory), all source aliases kept; evaluation tracks evaluate each canonical scene once.
  P6  Template disjointness: no learning node may share a template with TEST_SHORT (asserted).

    $PYG split.py INV_DIR RELEASE_DIR
"""
from __future__ import annotations

import collections, gzip, hashlib, json, os, shutil, sys
from pathlib import Path

import numpy as np

NW = Path("/home/projects/long-horizon/naren_workspace")
EXP = NW / "k3abl/abf/snapshot/abf_v32_fb0eef4f5ff433ee"
BASE = NW / "k3abl/abf/snapshot/abf_9de85710c2a7103f"
Q2 = NW / "fig3/final/r7/abf/data"
LEARN = ("ORIG_TRAIN", "ORIG_VAL", "LOCAL", "Q2POOL_TRAIN", "Q2POOL_VAL", "Q2POOL_TEST")
EXPOSED = ("V34", "R8B", "DEV_K45", "DEV_R53", "DEV_R5DEMO")
RELEASE = "LEGOLAS_FINAL_v1"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def H(o):
    return hashlib.sha256(json.dumps(o, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def side(t):
    return "TEST" if t in ("ORIG_TEST", "Q2POOL_TEST") else "VAL" if t in ("ORIG_VAL", "Q2POOL_VAL") else "TRAIN" if t in ("ORIG_TRAIN", "Q2POOL_TRAIN") \
        else "EXPOSED" if t in EXPOSED else t


def main(inv, rel):
    inv, rel = Path(inv), Path(rel)
    N = [json.loads(l) for l in open(inv / "nodes.jsonl")]
    comp = collections.defaultdict(list)
    for n in N:
        comp[n["pfam"]].append(n)
    led = collections.Counter()
    # ------------------------------------------------ P1-P3 component rules for non-LOCAL nodes
    for pf, ns in comp.items():
        sides = {side(n["track"]) for n in ns if n["track"] != "LOCAL"}
        has_local = any(n["track"] == "LOCAL" for n in ns)
        for n in ns:
            t, s = n["track"], side(n["track"])
            if t == "LOCAL":
                continue
            if s == "EXPOSED":
                n["part"] = {"V34": f"BENCH_SHORT_{n['dom'].upper()}", "R8B": "BENCH_COMP_3D"}.get(t, "DEV_EXPOSED"); n["why"] = "track"
            elif "EXPOSED" in sides:
                n["part"], n["why"] = "QUARANTINE", "LINK_EXPOSED"
            elif "TEST" in sides and (sides - {"TEST"} or has_local):
                n["part"], n["why"] = "QUARANTINE", ("TEST_HIST_TWIN" if s == "TEST" else "TEST_LINK")
            elif s == "TEST":
                n["part"], n["why"] = ("TEST_SHORT_" + n["dom"].upper(), "orig_test") if t == "ORIG_TEST" else ("POOL_TEST_UNUSED", "q2_test_split")
            elif "VAL" in sides and "TRAIN" in sides and s == "TRAIN":
                n["part"], n["why"] = "QUARANTINE", "VAL_LINK"
            else:
                n["part"], n["why"] = s, "orig_split"
            led[f"{n['dom']}|{t}->{n['part']}|{n['why']}"] += 1
    # ------------------------------------------------ P4 local families
    tsplit = collections.defaultdict(set)
    for n in N:
        if n["track"] in ("ORIG_TRAIN", "ORIG_VAL", "ORIG_TEST") and n["tmpl"]:
            tsplit[(n["dom"], n["tmpl"])].add(side(n["track"]))
    lf = collections.defaultdict(list)
    for n in N:
        if n["track"] == "LOCAL":
            for f in n["local_fams"]:
                lf[(n["dom"], f)].append(n)
    fam_part = {}
    for (dom, f), ns in lf.items():
        tags = set()
        for n in ns:
            cp = [m for m in comp[n["pfam"]] if m["track"] != "LOCAL"]
            parts = {m["part"] for m in cp}
            if parts & {"QUARANTINE"} or any(side(m["track"]) in ("TEST", "EXPOSED") for m in cp):
                tags.add("EXCLUDE")
            tags |= {p for p in parts if p in ("TRAIN", "VAL")}
            if not cp and n["tmpl"]:
                tags |= {"EXCLUDE" if x == "TEST" else x for x in tsplit.get((dom, n["tmpl"]), ())}
        r7 = {s for n in ns for s in n["local_splits"]}
        part = "EXCLUDE" if "EXCLUDE" in tags else "VAL" if "VAL" in tags else "TRAIN" if "TRAIN" in tags else ("VAL" if r7 == {"VAL"} else "TRAIN" if r7 == {"TRAIN"} else "CONFLICT")
        why = "ancestry" if tags else "r7_split"
        assert part != "CONFLICT", (dom, f, r7)
        fam_part[(dom, f)] = (part, why)
        led[f"{dom}|LOCALFAM->{part}|{why}|r7={'/'.join(sorted(r7))}"] += 1
    for n in N:
        if n["track"] == "LOCAL":
            ps = {fam_part[(n["dom"], f)][0] for f in n["local_fams"]}
            n["part"] = "EXCLUDE" if "EXCLUDE" in ps else "VAL" if "VAL" in ps else "TRAIN"
            n["why"] = "local_family"
    # ------------------------------------------------ P6 template disjointness vs TEST_SHORT
    test_t = {(n["dom"], n["tmpl"]) for n in N if n.get("part", "").startswith("TEST_SHORT") and n["tmpl"]}
    bad = [n["node"] for n in N if n.get("part") in ("TRAIN", "VAL") and (n["dom"], n["tmpl"]) in test_t]
    assert not bad, bad[:5]
    # ------------------------------------------------ P5 canonical scene records
    canon = collections.defaultdict(list)
    for n in N:
        canon[(n["dom"], n["part"], n["geom_fp"])].append(n)
    reg = []
    for (dom, part, g), ns in sorted(canon.items()):
        ns = sorted(ns, key=lambda n: (n["track"] != "ORIG_" + part, n["root_id"]))
        c = ns[0]
        reg.append({"scene_id": f"S{dom}-{g[:16]}", "domain": dom, "partition": part, "reason": c["why"], "canonical_root_id": c["root_id"],
                    "canonical_track": c["track"], "aliases": [[n["track"], n["root_id"]] for n in ns], "family_id": c["pfam"],
                    "template_id": c["tmpl"], "geom_fp": g, "inst_fp": c["inst_fp"], "n_obj": c["n_obj"], "K_legacy": c.get("K"),
                    "L_ref": c.get("L_ref"), "exposure": exposure(c, part)})
    # ------------------------------------------------ write release
    (rel / "splits").mkdir(parents=True, exist_ok=True); (rel / "provenance").mkdir(exist_ok=True); (rel / "checks").mkdir(exist_ok=True)
    with open(rel / "registry.jsonl", "w") as f:
        for r in reg:
            f.write(json.dumps(r) + "\n")
    byp = collections.defaultdict(list)
    for r in reg:
        byp[r["partition"]].append(r)
    for p, rs in byp.items():
        with open(rel / "splits" / f"{p.lower()}.jsonl", "w") as f:
            for r in rs:
                f.write(json.dumps({k: r[k] for k in ("scene_id", "domain", "canonical_root_id", "aliases", "family_id", "template_id", "K_legacy", "L_ref",
                                                      "reason")}) + "\n")
    (rel / "provenance" / "partition_ledger.json").write_text(json.dumps(dict(sorted(led.items())), indent=1))
    (rel / "provenance" / "local_family_partition.json").write_text(json.dumps({f"{d}|{f}": v for (d, f), v in sorted(fam_part.items())}, indent=1))
    snap_dir = build_snapshot(N, rel)
    q2_dir = build_q2(N, rel)
    loc = {f"{n['dom']}|{n['root_id']}": n["part"] for n in N if n["track"] == "LOCAL"}
    (rel / "views").mkdir(exist_ok=True)
    (rel / "views" / "local_split.json").write_text(json.dumps(loc, indent=0, sort_keys=True))
    counts = collections.Counter(f"{r['domain']}|{r['partition']}" for r in reg)
    print(json.dumps({"canonical_scenes": dict(sorted(counts.items())), "snapshot": str(snap_dir), "q2": str(q2_dir),
                      "local": dict(collections.Counter(f"{k.split('|')[0]}|{v}" for k, v in loc.items()))}, indent=1))


def exposure(n, part):
    if part.startswith("TEST_SHORT"):
        return "HELD_OUT_FROM_ALL_TRAINING_AND_SELECTION; aggregate outcomes of earlier model generations viewed (V3-6 2026-11-16, V3.2 TEST)"
    return {"BENCH_SHORT_2D": "V3.4 cohort evaluated in V3.4/R8A (outcomes viewed)", "BENCH_SHORT_3D": "V3.4 cohort evaluated in V3.4/R8A (outcomes viewed)",
            "BENCH_COMP_3D": "R8B roster evaluated in R8C/R9 (outcomes viewed)", "DEV_EXPOSED": "development (outcomes viewed)"}.get(part, "learning" if part in ("TRAIN", "VAL") else "none")


def build_snapshot(N, rel):
    """Canonical learning snapshot: canonical TRAIN + VAL rows of the expanded snapshot (VAL/TEST rows identical to base, asserted upstream);
    TEST and quarantined rows are physically absent; exact duplicates merged (labels unioned by edit, contradiction -> abort)."""
    keep = {(n["dom"], n["root_id"]): n for n in N if n["track"] in ("ORIG_TRAIN", "ORIG_VAL") and n["part"] in ("TRAIN", "VAL")}
    tmp = rel / "snapshot" / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    stats = {}
    for dom in ("2d", "3d"):
        rows = [json.loads(l) for l in open(EXP / f"data{dom}.jsonl")]
        by = collections.defaultdict(list)
        for r in rows:
            n = keep.get((dom, r["root_id"]))
            if n:
                assert r["split"].upper() == n["part"]
                by[n["geom_fp"]].append(r)
        out = []
        for g, rs in by.items():
            rs = sorted(rs, key=lambda r: r["root_id"])
            r0 = json.loads(json.dumps(rs[0]))
            dropped = set()                                   # conflicting keys of this duplicate group stay dropped for every later alias
            for r in rs[1:]:
                assert r["split"] == r0["split"] and r["K_legacy"] == r0["K_legacy"], (r0["root_id"], r["root_id"])
                ren = canon_map(r["inputs"], r0["inputs"])
                for kind in ("X", "Y"):
                    have = {lab_key(l): l for l in r0["labels"][kind]}
                    for l in r["labels"][kind]:
                        l2 = rename(l, ren)
                        k = lab_key(l2)
                        if (kind, k) in dropped:
                            continue
                        if k in have:
                            if val(have[k]) != val(l2):          # contradictory physical outcomes: unresolved -> both dropped (never voted)
                                CONFLICTS.append({"dom": dom, "kind": kind, "key": k, "roots": [r0["root_id"], r["root_id"]], "vals": [val(have[k]), val(l2)]})
                                r0["labels"][kind] = [x for x in r0["labels"][kind] if lab_key(x) != k]; have.pop(k); dropped.add((kind, k))
                        else:
                            r0["labels"][kind].append(l2); have[k] = l2
            r0.setdefault("meta", {})["r10_aliases"] = [r["root_id"] for r in rs]
            out.append(r0)
        out.sort(key=lambda r: r["root_id"])
        with open(tmp / f"data{dom}.jsonl", "w") as f:
            for r in out:
                f.write(json.dumps(r) + "\n")
        stats[dom] = dict(collections.Counter(r["split"] for r in out))
    h = H({d: sha(tmp / f"data{d}.jsonl") for d in ("2d", "3d")})[:16]
    d = rel / "snapshot" / f"abf_r10_{h}"
    if d.exists():
        shutil.rmtree(tmp)
    else:
        tmp.rename(d)
    (rel / "provenance" / "label_conflicts.json").write_text(json.dumps(CONFLICTS, indent=1))
    (d / "data_snapshot.lock.json").write_text(json.dumps({"snapshot_id": d.name, "release": RELEASE, "derived_from": [EXP.name, BASE.name],
        "rule": "canonical TRAIN+VAL only (split.py P1-P5); TEST / quarantine rows physically absent", "split_counts": stats, "label_conflicts_dropped": len(CONFLICTS),
        "files": {f"data{x}.jsonl": sha(d / f"data{x}.jsonl") for x in ("2d", "3d")}}, indent=1))
    return d


CONFLICTS = []


def val(l):
    return None if l.get("_dropped") else l.get("y", l.get("x"))


def canon_map(src, dst):
    """object map src -> dst for two identical scenes, by (cell, attrs) (an object is identified by its occupied cell): index and id."""
    key = lambda v, i: (int(v["cells0"][i]), tuple(round(float(a), 6) for a in v["attrs"][i]))  # noqa: E731
    d = {key(dst, i): i for i in range(len(dst["ids"]))}
    m = {i: d[key(src, i)] for i in range(len(src["ids"]))}
    m.update({src["ids"][i]: dst["ids"][j] for i, j in list(m.items())})
    return m


def rename(l, ren):
    l = json.loads(json.dumps(l))
    for k in ("edit", "seq"):
        if k in l and l[k]:
            l[k] = [[ren[a[0]], *a[1:]] for a in l[k]]
    return l


def lab_key(l):
    return json.dumps({k: v for k, v in l.items() if k in ("edit", "seq", "order")}, sort_keys=True)


def build_q2(N, rel):
    """Q2 placement data restricted to canonical TRAIN / VAL roots (Q2 TEST-split samples and quarantined roots removed); TRAIN-only scalers."""
    part = {}
    for n in N:
        if n["track"] in ("ORIG_TRAIN", "ORIG_VAL", "Q2POOL_TRAIN", "Q2POOL_VAL") and n["part"] in ("TRAIN", "VAL"):
            part[(n["dom"], n["root_id"])] = n["part"]
    out_root = rel / "q2"
    res = {}
    for dom in ("2d", "3d"):
        src = Q2 / f"q2_{dom}"
        F = dict(np.load(src / "features.npz"))
        R = json.loads((src / "rows.json").read_text())
        sp = F["split"]
        want = {0: "TRAIN", 1: "VAL"}
        keep = np.array([s in want and part.get((dom, r)) == want[s] for r, s in zip(R["roots"], sp)])
        assert not (keep & (sp == 2)).any()
        mism = int(sum(1 for r, s in zip(R["roots"], sp) if part.get((dom, r)) not in (None, ("TRAIN" if s == 0 else "VAL" if s == 1 else "x"))))
        assert mism == 0, (dom, "Q2 split disagrees with canonical partition", mism)
        d = out_root / f"q2_{dom}"
        d.mkdir(parents=True, exist_ok=True)
        G = {k: v[keep] for k, v in F.items()}
        sc = json.loads((src / "scalers.json").read_text())
        NORM = [2, 3, 6, 7, 8]
        mu, sd = np.zeros(14, np.float32), np.ones(14, np.float32)
        tr = G["split"] == 0
        for j in NORM:
            v = G["obj"][tr][:, :, j][G["mask"][tr]]
            mu[j], sd[j] = v.mean(), v.std() + 1e-6
        np.savez_compressed(d / "features.npz", **G)
        (d / "rows.json").write_text(json.dumps({k: [x for x, m in zip(v, keep) if m] for k, v in R.items()}))
        sc.update({"mean": mu.tolist(), "std": std_list(sd), "n": int(keep.sum()), "features_sha256": sha(d / "features.npz"), "fit_on": "canonical TRAIN only",
                   "r10_source": {"features_sha256": sha(src / "features.npz"), "dropped": int((~keep).sum()), "dropped_test_split": int((sp == 2).sum())},
                   "by_split": {s: {"queries": int((G["split"] == i).sum())} for i, s in enumerate(["train", "val", "test"])}})
        (d / "scalers.json").write_text(json.dumps(sc, indent=1))
        res[dom] = {"kept": int(keep.sum()), "dropped": int((~keep).sum())}
    (out_root / "Q2_R10.json").write_text(json.dumps(res, indent=1))
    return out_root


def std_list(sd):
    return [float(x) for x in sd]


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
