"""V3.4 benchmark harness tests (synthetic, CPU, no teacher): legality grammar, seal-before-evaluate, outcome mapping, dummy adapters,
denominators (UNKNOWN never a failure), and -- when V34_BUNDLE + V34_PUBLIC are set -- the frozen bundle loads scratch models deterministically."""
import json, os, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import benchmark as BM  # noqa: E402
import baseline_adapters as BA  # noqa: E402


def root2d(rid="r1"):
    # 3 objects: target t0 at cell 0, movable m1 at 1, fixed f2 at 2; legal cells 0..9, goal 9
    return {"root_id": rid, "domain": "2d", "inputs": {"ids": ["t0", "m1", "f2"], "tid": 0, "cells0": [0, 1, 2], "goal_cell": 9,
            "legal_cells": list(range(10)), "attrs": [[0.03, 1, 0, 0], [0.03, 0, 1, 0], [0.03, 0, 1, 1]]}}


def test_legality_grammar():
    r = root2d()
    ok = [{"object_id": "m1", "object_index": 1, "destination_cell": 5}]
    assert BM.legality(r, ok) is None
    assert BM.legality(r, []) == "LENGTH"
    assert BM.legality(r, [{"object_index": 0, "destination_cell": 5}]) == "IMMOVABLE_OBJECT"           # target
    assert BM.legality(r, [{"object_index": 2, "destination_cell": 5}]) == "IMMOVABLE_OBJECT"           # fixed
    assert BM.legality(r, [{"object_index": 1, "destination_cell": 2}]) == "ILLEGAL_DESTINATION"        # occupied
    assert BM.legality(r, [{"object_index": 1, "destination_cell": 9}]) == "ILLEGAL_DESTINATION"        # goal
    assert BM.legality(r, [{"object_index": 1, "destination_cell": 0}]) == "ILLEGAL_DESTINATION"        # initially occupied (no swaps)
    assert BM.legality(r, ok + [{"object_index": 1, "destination_cell": 6}]) == "OBJECT_MOVED_TWICE"
    assert BM.legality(r, [{"object_id": "zz", "destination_cell": 5}]) == "UNKNOWN_OBJECT"


def _setup(tmp, adapter):
    pub = tmp / "public.jsonl"
    rows = [root2d("a"), root2d("b"), root2d("c"), root2d("d")]
    pub.write_text("".join(json.dumps(r) + "\n" for r in rows))
    priv = tmp / "private.jsonl"
    K = {"a": "1", "b": "2", "c": "NONE", "d": "0"}
    priv.write_text("".join(json.dumps({"root_id": r, "domain": "2d", "K": k, "path": f"{r}.json", "ids": ["t0", "m1", "f2"],
                                        "evaluation_group_id": "g" + r, "masks": {"eval_task": k in "123", "eval_noop": k == "0", "eval_abstain": k == "NONE"}}) + "\n"
                            for r, k in K.items()))
    pred = tmp / "pred.jsonl"
    BA.run(adapter, pub, pred)
    return pub, priv, pred


def test_seal_required_and_dummy_abstain(tmp_path):
    pub, priv, pred = _setup(tmp_path, "always_abstain")
    with pytest.raises(AssertionError):
        BM.evaluate(pub, pred, priv, tmp_path, tmp_path / "res.jsonl")
    BM.seal(pred, pub)
    BM.evaluate(pub, pred, priv, tmp_path, tmp_path / "res.jsonl")
    R = {x["root_id"]: x for x in BM.jl(tmp_path / "res.jsonl")}
    assert {k: v["outcome"] for k, v in R.items()} == {"a": "ABSTAIN", "b": "ABSTAIN", "c": "ABSTAIN", "d": "ABSTAIN"}
    BM.summarize(priv, tmp_path / "s.json", [tmp_path / "res.jsonl"])
    S = json.loads((tmp_path / "s.json").read_text())["res:2d"]
    assert S["task"]["n"] == 2 and S["task"]["rate_ci"][0] == 0 and S["abstain"]["rate_ci"][0] == 100 and S["noop"]["n"] == 1


def test_dummy_repair_outcomes_and_unknown(tmp_path):
    pub, priv, pred = _setup(tmp_path, "legal_fixed_repair")
    BM.seal(pred, pub)
    seq = json.dumps([[1, 3]])          # m1 -> cell 3 (lowest free legal cell)
    cache = [{"root": "a", "results": [{"seq": [[1, 3]], "x": {"x": 1}, "y": {"y": 1}}]},
             {"root": "b", "results": [{"seq": [[1, 3]], "x": {"x": 0}, "y": {"y": 1}}]}]          # c, d: never queried -> UNKNOWN
    (tmp_path / "verify_2d.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cache))
    assert json.loads(seq) == [[m["object_index"], m["destination_cell"]] for m in BM.jl(pred)[0]["moves"]]
    BM.evaluate(pub, pred, priv, tmp_path, tmp_path / "res.jsonl")
    R = {x["root_id"]: x["outcome"] for x in BM.jl(tmp_path / "res.jsonl")}
    assert R == {"a": "SUCCESS", "b": "FAIL_X", "c": "UNKNOWN", "d": "UNKNOWN"}
    BM.summarize(priv, tmp_path / "s.json", [tmp_path / "res.jsonl"])
    S = json.loads((tmp_path / "s.json").read_text())["res:2d"]
    assert S["task"]["n"] == 2 and S["task"]["rate_ci"][0] == 50.0 and S["noop"]["rate_ci"][0] == 0.0
    assert S["none_false_repair"]["repair_attempts"] == 1


def test_invalid_prediction_counted_not_favourable(tmp_path):
    pub, priv, pred = _setup(tmp_path, "always_abstain")
    rows = BM.jl(pred)
    rows[0] = {**rows[0], "decision": "REPAIR", "moves": [{"object_index": 0, "destination_cell": 5}]}   # moves the target
    pred.write_text("".join(json.dumps(r) + "\n" for r in rows))
    BM.seal(pred, pub)
    BM.evaluate(pub, pred, priv, tmp_path, tmp_path / "res.jsonl")
    assert BM.jl(tmp_path / "res.jsonl")[0]["outcome"] == "INVALID_IMMOVABLE_OBJECT"


@pytest.mark.skipif(not os.environ.get("V34_BUNDLE"), reason="needs V34_BUNDLE (+ V34_PUBLIC)")
def test_bundle_scratch_and_deterministic(tmp_path):
    man = json.loads((Path(os.environ["V34_BUNDLE"]) / "MANIFEST.json").read_text())
    for name, p in man["provenance"].items():
        if "sampler" in name:
            assert p["prov"]["init"] == "scratch" and "v32_fb0eef4f5ff433ee" in p["prov"]["train_snapshot"]
    rows = BM.jl(os.environ["V34_PUBLIC"])[:5]
    pub = tmp_path / "p.jsonl"
    pub.write_text("".join(json.dumps(r) + "\n" for r in rows))
    dev = os.environ.get("V34_DEVICE", "cpu")
    BM.predict(os.environ["V34_BUNDLE"], pub, tmp_path / "a.jsonl", dev)
    BM.predict(os.environ["V34_BUNDLE"], pub, tmp_path / "b.jsonl", dev)
    strip = lambda r: {k: r[k] for k in ("root_id", "decision", "moves", "score_p11", "proposals")}  # noqa: E731
    assert [strip(r) for r in BM.jl(tmp_path / "a.jsonl")] == [strip(r) for r in BM.jl(tmp_path / "b.jsonl")]
