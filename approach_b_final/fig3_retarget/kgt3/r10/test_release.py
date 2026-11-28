#!/usr/bin/env python3
"""R10.0 automated release tests (gvlab2):  $PYG -m pytest -q test_release.py   (env R10_REL = release dir, R10_INV = inventory dir).
Loader allowlists, family / template disjointness, canonical ids, lineage of learning views, label conflicts, action lengths, seal hashes."""
import collections, hashlib, json, os
from pathlib import Path

import numpy as np
import pytest

REL = Path(os.environ.get("R10_REL", "/home/projects/long-horizon/naren_workspace/r10/release/LEGOLAS_FINAL_v1"))
INV = Path(os.environ.get("R10_INV", "/home/projects/long-horizon/naren_workspace/r10/data/inv"))
CLEAN_EVAL = ("TEST_SHORT_2D", "TEST_SHORT_3D")
EXPOSED = ("BENCH_SHORT_2D", "BENCH_SHORT_3D", "BENCH_COMP_3D", "DEV_EXPOSED")


def jl(p):
    return [json.loads(l) for l in open(p)]


@pytest.fixture(scope="module")
def reg():
    return jl(REL / "registry.jsonl")


@pytest.fixture(scope="module")
def nodes():
    return jl(INV / "nodes.jsonl")


def test_canonical_ids_unique(reg):
    c = collections.Counter((r["domain"], r["partition"], r["scene_id"]) for r in reg)
    assert max(c.values()) == 1
    al = collections.Counter((r["domain"], t, rid) for r in reg for t, rid in r["aliases"])
    assert max(al.values()) == 1, "a source row appears in two canonical records"


def test_each_scene_assigned_once(reg):
    by = collections.defaultdict(set)
    for r in reg:
        by[(r["domain"], r["geom_fp"])].add(r["partition"])
    multi = {k: v for k, v in by.items() if len(v - {"POOL_TEST_UNUSED", "QUARANTINE", "EXCLUDE"}) > 1}   # exclusion ledgers may hold a twin
    assert not multi, list(multi.items())[:3]


def test_family_disjoint_learning_vs_eval(reg):
    fam = collections.defaultdict(set)
    for r in reg:
        fam[(r["domain"], r["family_id"])].add(r["partition"])
    for k, ps in fam.items():
        learn = ps & {"TRAIN", "VAL"}
        assert not (learn and ps & set(CLEAN_EVAL + EXPOSED)), (k, ps)
        assert not ({"TRAIN"} <= ps and {"VAL"} <= ps), (k, ps)


def test_template_disjoint_learning_vs_test(reg):
    tt = {(r["domain"], r["template_id"]) for r in reg if r["partition"] in CLEAN_EVAL and r["template_id"]}
    bad = [r["scene_id"] for r in reg if r["partition"] in ("TRAIN", "VAL") and (r["domain"], r["template_id"]) in tt]
    assert not bad, bad[:5]


def test_snapshot_allowlist(reg):
    snap = next((REL / "snapshot").glob("abf_r10_*"))
    allowed = {(r["domain"], rid) for r in reg if r["partition"] in ("TRAIN", "VAL") for t, rid in r["aliases"] if t.startswith("ORIG_")}
    forbidden = {(r["domain"], rid) for r in reg if r["partition"] not in ("TRAIN", "VAL") for t, rid in r["aliases"]}
    for dom in ("2d", "3d"):
        for l in open(snap / f"data{dom}.jsonl"):
            row = json.loads(l)
            assert row["split"] in ("train", "val")
            assert (dom, row["root_id"]) in allowed and (dom, row["root_id"]) not in forbidden, row["root_id"]
            for a in row["meta"].get("r10_aliases", []):
                assert (dom, a) not in forbidden


def test_q2_lineage(reg):
    ok = {(r["domain"], rid): r["partition"] for r in reg if r["partition"] in ("TRAIN", "VAL") for t, rid in r["aliases"]}
    for dom in ("2d", "3d"):
        d = REL / "q2" / f"q2_{dom}"
        sp = np.load(d / "features.npz")["split"]
        roots = json.loads((d / "rows.json").read_text())["roots"]
        assert len(roots) == len(sp) and set(np.unique(sp)) <= {0, 1}
        for r, s in zip(roots, sp):
            assert ok.get((dom, r)) == ("TRAIN" if s == 0 else "VAL"), (dom, r, s)


def test_local_split_lineage(nodes):
    M = json.loads((REL / "views" / "local_split.json").read_text())
    comp = collections.defaultdict(set)
    for n in nodes:
        comp[n["pfam"]].add(n["track"])
    for n in nodes:
        if n["track"] != "LOCAL":
            continue
        p = M[f"{n['dom']}|{n['root_id']}"]
        tr = comp[n["pfam"]]
        if tr & {"ORIG_TEST", "Q2POOL_TEST", "V34", "R8B", "DEV_K45", "DEV_R53", "DEV_R5DEMO"}:
            assert p == "EXCLUDE", n["root_id"]
        if p == "TRAIN":
            assert not tr & {"ORIG_VAL", "Q2POOL_VAL"}, n["root_id"]


def test_label_conflicts_dropped_not_voted():
    C = json.loads((REL / "provenance" / "label_conflicts.json").read_text())
    snap = next((REL / "snapshot").glob("abf_r10_*"))
    keys = {(c["dom"], c["roots"][0], c["key"]) for c in C}
    for dom in ("2d", "3d"):
        for l in open(snap / f"data{dom}.jsonl"):
            row = json.loads(l)
            for kind in ("X", "Y"):
                for lab in row["labels"][kind]:
                    k = json.dumps({kk: v for kk, v in lab.items() if kk in ("edit", "seq", "order")}, sort_keys=True)
                    assert (dom, row["root_id"], k) not in keys


def test_action_lengths(reg):
    snap = next((REL / "snapshot").glob("abf_r10_*"))
    for dom in ("2d", "3d"):
        for l in open(snap / f"data{dom}.jsonl"):
            row = json.loads(l)
            assert all(len(x["seq"]) <= 3 for x in row["labels"]["X"]) and all(len(y["edit"]) <= 3 for y in row["labels"]["Y"])


def test_seal_hashes():
    S = json.loads((REL / "R10_DATASET_SEAL.json").read_text())
    for rel, h in S["files"].items():
        assert hashlib.sha256((REL / rel).read_bytes()).hexdigest() == h, rel
