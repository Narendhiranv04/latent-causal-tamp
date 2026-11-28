"""R10.1: the composition planner can only see public rows (r6.public_roots); private references are not loaded and cannot change inputs."""
import json, os, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _rows(tmp, extra=None):
    pub = tmp / "pub.jsonl"; prv = tmp / "prv.jsonl"
    r = {"root_id": "r1", "domain": "3d", "inputs": {"ids": ["t0", "o00"], "cells0": [0, 1], "tid": 0, "goal_cell": 5, "attrs": [[1, 0, .1, .1, 1], [1, 0, .1, .1, 0]]}}
    if extra:
        r.update(extra)
    pub.write_text(json.dumps(r) + "\n")
    prv.write_text(json.dumps({"root_id": "r1", "L_ref": 4, "N": 2, "K_cert": None, "witness": [[1, 7]], "path": "x", "goal": [0, 5]}) + "\n")
    return pub, prv


def test_public_only_and_private_invariance(tmp_path, monkeypatch):
    import r6
    pub, prv = _rows(tmp_path)
    monkeypatch.setenv("R10_PUBLIC", str(pub)); monkeypatch.setenv("R10_PRIVATE", str(prv))
    a = r6.public_roots("r10comp")
    prv.write_text(json.dumps({"root_id": "r1", "L_ref": 5, "N": 9, "K_cert": 3, "witness": [[1, 9], [0, 2]], "path": "y", "goal": [1, 1]}) + "\n")
    b = r6.public_roots("r10comp")
    prv.unlink()                                             # planner input must not even need the private file
    c = r6.public_roots("r10comp")
    assert a == b == c and set(a[0][1]) == {"root_id", "domain", "inputs"}


@pytest.mark.parametrize("extra", [{"witness": [[1, 7]]}, {"L_ref": 4}, {"labels": {}}])
def test_schema_rejects_private_fields(tmp_path, monkeypatch, extra):
    import r6
    pub, _ = _rows(tmp_path, extra)
    monkeypatch.setenv("R10_PUBLIC", str(pub))
    with pytest.raises(AssertionError):
        r6.public_roots("r10comp")


def test_inputs_schema_rejects_extra(tmp_path, monkeypatch):
    import r6
    pub, _ = _rows(tmp_path)
    r = json.loads(pub.read_text()); r["inputs"]["witness"] = [[1, 7]]; pub.write_text(json.dumps(r) + "\n")
    monkeypatch.setenv("R10_PUBLIC", str(pub))
    with pytest.raises(AssertionError):
        r6.public_roots("r10comp")
