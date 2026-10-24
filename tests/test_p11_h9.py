"""P11-1: H9 variants use collision-free (root, palette) keys; both palettes persisted; non-visual inputs identical to the original."""
import os

os.environ.setdefault("P10C_OUT", "runs/p10c")

import p11_closure as p  # noqa: E402


def test_compound_keys_unique_two_palettes_per_root():
    v = p.h9_variants()
    keys = [k for k, *_ in v]
    assert len(keys) == len(set(keys)) == 200
    assert {pal for _, _, pal, _ in v} == {"P1", "P2"}


def test_h9_geometry_identical_and_visual_distinct():
    i = p.h9_integrity()
    assert i["nonvisual_input_mismatch"] == 0 and i["query_id_mismatch"] == 0
    assert i["visual_identical_to_original"] == 0 and i["P1_identical_to_P2"] == 0


def test_old_snapshot_key_collision_is_real():
    import json
    snap = json.load(open("runs/p10d/predictions.json"))
    a = next(x for x in snap["arms"].values() if x["regime"] == "full")
    assert len(a["roots"]["h9"]) == 100          # the defect P11-1 corrects (one palette lost per root)
