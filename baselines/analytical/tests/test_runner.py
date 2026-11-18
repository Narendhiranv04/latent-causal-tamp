"""Runner plumbing: exactly one committed prediction per root across shards (merge), budget cuts turn late decisions into ABSTAIN."""
import json
from argparse import Namespace

import pytest

from baselines.analytical import run as RUN


def write(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))


def pred(rid, dec="ABSTAIN", cpu=10.0):
    return {"root_id": rid, "domain": "2d", "decision": dec, "moves": [] if dec != "REPAIR" else [{"object_index": 1, "destination_cell": 4}],
            "decided_cpu_s": cpu}


def test_merge_one_answer_per_root(tmp_path):
    pub = tmp_path / "pub.jsonl"
    write(pub, [{"root_id": r, "domain": "2d", "inputs": {}} for r in "abc"])
    write(tmp_path / "s0/em4m_paper_s0_b300/predictions_2d.jsonl", [pred("a"), pred("b")])
    write(tmp_path / "s1/em4m_paper_s0_b300/predictions_2d.jsonl", [pred("c", "REPAIR")])
    RUN.merge(Namespace(domain="2d", public=str(pub), out=str(tmp_path / "m"), parts=[str(tmp_path / "s0"), str(tmp_path / "s1")],
                        allow_missing=False))
    got = RUN.jl(tmp_path / "m/em4m_paper_s0_b300/predictions_2d.jsonl")
    assert sorted(x["root_id"] for x in got) == ["a", "b", "c"]
    write(tmp_path / "s2/em4m_paper_s0_b300/predictions_2d.jsonl", [pred("a")])
    with pytest.raises(AssertionError):
        RUN.merge(Namespace(domain="2d", public=str(pub), out=str(tmp_path / "m2"), parts=[str(tmp_path / "s0"), str(tmp_path / "s2")],
                            allow_missing=True))
    with pytest.raises(SystemExit):
        RUN.merge(Namespace(domain="2d", public=str(pub), out=str(tmp_path / "m3"), parts=[str(tmp_path / "s0")], allow_missing=False))


def test_cut(tmp_path):
    write(tmp_path / "msmcts_paper_s0_b300/predictions_2d.jsonl", [pred("a", "REPAIR", 50.0), pred("b", "REPAIR", 200.0), pred("c", "NOOP", 70)])
    RUN.cut(Namespace(out=str(tmp_path), budget=60))
    got = {x["root_id"]: x for x in RUN.jl(tmp_path / "msmcts_paper_s0_b60_cut300/predictions_2d.jsonl")}
    assert got["a"]["decision"] == "REPAIR" and got["b"]["decision"] == "ABSTAIN" and got["b"]["moves"] == []
    assert got["c"]["decision"] == "ABSTAIN"
