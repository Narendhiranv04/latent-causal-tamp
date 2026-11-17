"""V3.3 scratch-sampler contract tests (CPU).  Synthetic tests always run; snapshot tests run when V33_SNAPS="BASE:CONTROL:EXPANDED" and ABF_ROOT
(with data/q2_<dom>/scalers.json) are set, e.g. V33_SNAPS=... ABF_ROOT=... CUDA_VISIBLE_DEVICES= python -m pytest tests/test_v33.py"""
import json, os, sys
from pathlib import Path

import pytest

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contracts as CT  # noqa: E402

SNAPS = os.environ.get("V33_SNAPS", "").split(":") if os.environ.get("V33_SNAPS") else None
need = pytest.mark.skipif(SNAPS is None, reason="V33_SNAPS not set")


def _row(X, Y):
    return {"labels": {"X": [{"seq": s, "x": x, "kind": "T"} for s, x in X], "Y": [{"edit": e, "y": y} for e, y in Y]}}


def test_positive_assignments_dedup_orders_and_require_x_and_y():
    a, b, c = [1, 10], [2, 20], [3, 30]
    r = _row([([a, b], 1), ([b, a], 1), ([a, c], 0), ([c, a], 1), ([b], 1), ([c], 1)],
             [(sorted([a, b]), 1), (sorted([a, c]), 1), ([b], 0)])
    pa = CT.positive_assignments(r)
    assert set(pa) == {CT.ekey([a, b]), CT.ekey([a, c])}                       # two successful orders of {a, b} -> ONE target
    assert len(pa[CT.ekey([a, b])]["orders"]) == 2
    assert pa[CT.ekey([a, c])]["orders"] == [[c, a]] and pa[CT.ekey([a, c])]["failed_orders"] == [[a, c]]
    assert CT.ekey([b]) not in pa                                               # X = 1 but Y = 0 -> never a positive
    assert CT.ekey([c]) not in pa                                               # Y unknown (no label) -> never a positive


def test_scratch_init_identical_per_seed_and_device_independent():
    import torch
    import placement as PL
    shas = []
    for _ in range(2):
        torch.manual_seed(3)
        shas.append(PL.state_sha(PL.TaskCVAE(8, 8, PL.task_dim("2d"))))
    torch.manual_seed(4)
    assert shas[0] == shas[1] != PL.state_sha(PL.TaskCVAE(8, 8, PL.task_dim("2d")))


@need
@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_explicit_snapshots_loaded_and_targets_are_positive(dom):
    import placement as PL
    base, ctl, exp = SNAPS
    t = {k: PL.repair_data(dom, s, "train", "all", True, "cpu") for k, s in (("control", ctl), ("expanded", exp))}
    assert len(t["expanded"]["dest"]) > len(t["control"]["dest"])              # the expanded arm really receives more targets
    rows = {r["root_id"]: r for r in map(json.loads, open(Path(exp) / f"data{dom}.jsonl"))}
    for rid, d in zip(t["expanded"]["roots"], t["expanded"]["dest"].tolist()):
        pa = CT.positive_assignments(rows[rid])
        assert rows[rid]["split"] == "train"
        assert any(int(c) == d for a in pa.values() if not CT.v3_grammar(rows[rid]["inputs"], a["assignment"]) for _, c in a["assignment"])


@need
@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_holdout_rows_byte_identical_and_no_family_leak(dom):
    L = [{json.loads(l)["root_id"]: l for l in open(Path(s) / f"data{dom}.jsonl")} for s in SNAPS]
    assert set(L[0]) == set(L[1]) == set(L[2])
    fam = {}
    for k, l in L[2].items():
        r = json.loads(l)
        if r["split"] != "train":
            assert L[0][k] == L[1][k] == L[2][k]
        fam.setdefault(r["parent_family_id"], set()).add(r["split"])
    assert all(len(v) == 1 for v in fam.values())


@need
def test_fixed_step_scratch_arms_match_and_never_load_q2(tmp_path, monkeypatch):
    import torch
    import placement as PL
    base, ctl, exp = SNAPS
    monkeypatch.setattr(PL, "init_from_q2", lambda *a: (_ for _ in ()).throw(AssertionError("Q2 init called")))
    monkeypatch.setattr(PL, "load", lambda *a, **k: (_ for _ in ()).throw(AssertionError("pretrained load called")))
    monkeypatch.setenv("V3OUT", str(tmp_path))
    ck = {}
    for arm, s in (("control", ctl), ("expanded", exp)):
        monkeypatch.setenv("V3_TASK_STAGE", f"v33/{arm}")
        PL.fit_task("3d", "scratch_all", 0, {"steps": 3, "eval_every": 2}, train_snap=s, val_snap=base, device="cpu")
        ck[arm] = torch.load(tmp_path / f"v33/{arm}/3d/scratch_all_s0/model.pt", map_location="cpu", weights_only=False)
        cur = json.loads((tmp_path / f"v33/{arm}/3d/scratch_all_s0/curve.json").read_text())
        assert [c["step"] for c in cur["curve"]] == [2, 3] and all(map(lambda c: c["val"] == c["val"], cur["curve"]))   # finite VAL ELBO
    a, b = ck["control"], ck["expanded"]
    assert a["prov"]["init_state_sha256"] == b["prov"]["init_state_sha256"]            # identical initial weights under the same seed
    assert a["prov"]["init"] == b["prov"]["init"] == "scratch"
    assert a["prov"]["train_data_sha256"] != b["prov"]["train_data_sha256"] and a["prov"]["val_data_sha256"] == b["prov"]["val_data_sha256"]
    assert a["cfg"] == b["cfg"] and {k: v.shape for k, v in a["state"].items()} == {k: v.shape for k, v in b["state"].items()}
    # CPU inference through the unchanged sampler API
    monkeypatch.setenv("ABF_DEVICE", "cpu"); monkeypatch.setenv("V3_TASK_STAGE", "v33/expanded")
    import construct as CO, search as S
    samp = CO.make_sampler("3d", "task:scratch_all", 0, CO.RULES["S1"])
    r = next(r for r in map(json.loads, open(Path(base) / "data3d.jsonl")) if r["split"] == "val" and r["masks"]["eval_task"])
    root = S.Root(r, "3d")
    D = samp.propose_many(root, root.cells0, list(root.movable), 4, torch.Generator().manual_seed(0))
    legal = set(root.legal_dests(root.cells0))
    assert D and all(len(v) == len(set(v)) <= 4 and set(v) <= legal for v in D.values())
