"""P12: generator reproducibility + prescreen replay, non-overlap with P10 roots, lock / unseal enforcement, statistics, photometric
non-visual invariance, frozen-prediction physical-call record."""
import json
import os
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("P10C_OUT", "runs/p10c")

import p12_closure as p  # noqa: E402


def _ctx():
    import config as cf
    import geometry as ge
    import p10_scenes as ps
    cfg = cf.load_config("config.toml")
    return ps.Ctx(cfg, ge.make_robot(cfg))


def test_holdout_root_replays_exactly_through_prescreen():
    import p10b_scenes as pb
    import p12_families  # noqa: F401
    from scene import scene_hash
    plan = json.loads(Path("runs/p12/holdout/batch1/plan.json").read_text())
    k, r = next(iter(plan["roots"].items()))
    spec = next(s for s in p.roster() if s["seed"] == r["seed"])
    rec, why = pb.try_root(_ctx(), spec, r["attempt"], set())
    assert rec is not None and scene_hash(rec["scene"]) == r["scene_hash"]


def test_no_overlap_with_p10_fingerprints():
    old = {json.dumps(r["fingerprint"]) for f in Path("runs/p10b").glob("batch*/plan.json") for r in json.loads(f.read_text())["roots"].values()}
    new = [json.dumps(r["fingerprint"]) for r in p.plans().values()]
    assert len(new) == 80 and not (set(new) & old) and len(set(new)) == 80


def test_sealed_records_refuse_without_unseal(tmp_path, monkeypatch):
    monkeypatch.setattr(p, "HOLD", tmp_path)
    with pytest.raises(SystemExit):
        p.sealed_records("batch1")


def test_sign_test_and_holm():
    pv, pos, neg, ties = p._sign([0.1] * 9 + [0.0])
    assert (pos, neg, ties) == (9, 0, 1) and abs(pv - 0.00390625) < 1e-12
    h = p._holm({"a": 0.01, "b": 0.04})
    assert abs(h["a"] - 0.02) < 1e-12 and abs(h["b"] - 0.04) < 1e-12


def test_photometric_recipe_changes_pixels_only():
    rng = np.random.default_rng(0)
    rgb = rng.integers(0, 256, (16, 16, 3), dtype=np.uint8)
    out = p.photometric(rgb, p.PHOTO["G2_whitebalance_desat"])
    assert out.shape == rgb.shape and out.dtype == np.uint8 and not np.array_equal(out, rgb)


def test_frozen_predictions_record_zero_physical_calls_and_full_coverage():
    f = json.loads(Path("runs/p12/holdout/PREDICTIONS_FROZEN.json").read_text())
    assert not sum(f["physical_calls"].values())
    assert not any("coverage_failure" in v for a in f["arms"].values() for v in a["roots"].values())
