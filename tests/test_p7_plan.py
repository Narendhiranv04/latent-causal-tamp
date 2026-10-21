"""P7b frozen schedule and static construction (no teacher): balance, splits, strata, catalogue caps, V3 layouts."""
import collections
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import geometry as ge  # noqa: E402
import p6_scenes as p6  # noqa: E402
import p7_scenes as p7  # noqa: E402
import zlayout_r4 as z4  # noqa: E402


def test_schedule_predeclared_balanced_and_waved():
    assert len(p7.ROOTS) == 48 and len({r["seed"] for r in p7.ROOTS}) == 48
    for w in (1, 2):
        for f in p7.FAMS:
            sp = collections.Counter(r["split"] for r in p7.ROOTS if r["wave"] == w and r["family"] == f)
            assert sp == {"train": 2, "validation": 1, "test": 1}
    assert all(collections.Counter(r["batch"] for r in p7.ROOTS)[b] == 12 for b in (1, 2, 3, 4))
    assert {r["batch"] for r in p7.ROOTS if r["wave"] == 1} == {1, 2}
    assert len({r["stratum"] for r in p7.ROOTS}) >= 4
    assert all(r["stratum"] in p7.MOT_STRATA for r in p7.ROOTS if r["family"] == "MOT")


@pytest.fixture(scope="module")
def built():
    cfg = cf.load_config(ROOT / "config.toml")
    robot = ge.make_robot(cfg)
    scr, out = p6.Screens(cfg, robot), []
    for f in p7.FAMS:
        spec = next(r for r in p7.ROOTS if r["family"] == f)
        for a in range(p7.MAX_ATTEMPTS):
            rec, _ = p7._try(cfg, robot, scr, spec, a, set())
            if rec:
                out.append(rec)
                break
    return cfg, robot, out


def test_each_family_constructs_with_intent_and_catalogue_caps(built):
    cfg, robot, roots = built
    assert [r["family"] for r in roots] == p7.FAMS
    for r in roots:
        assert all(p["ok"] for p in r["predicates"])
        assert list(r["scene"].robot.q_rad) == p7.STRATA[r["stratum"]]
        cat = p7.catalogue(cfg, robot, r)
        n = 1 + len(cat["pool"]) + sum(q["eligible"] for q in cat["scene_queries"])
        assert n <= p7.QUERY_CAP
        assert all(p["canonical"] for p in cat["pool"]) and len({z4.sig([tuple(a) for a in p["sequence"]]) for p in cat["pool"]}) == len(cat["pool"])
        for p in cat["pool"]:
            z4.verify(p["z_layout"])
            assert not any(s.startswith("zS[nuisance") for s in p["z_layout"]["query"])
        assert max(len(p["sequence"]) for p in cat["pool"]) >= 2
    mot = next(r for r in roots if r["family"] == "MOT")
    assert any(p["check"].startswith("target link-0 sector-blocked") and p["ok"] for p in mot["predicates"])
