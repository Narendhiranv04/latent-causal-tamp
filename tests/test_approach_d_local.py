"""Local research track: archived P17 comparison recomputed from saved records, the bounded G2c-lite catalogs, and the matched ordering
pilot on the solver-free backend (D queried for the original target only; zero runtime IK / planner calls)."""
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

import ad_local as L
import ad_runtime as ar


def test_archived_p17_values_reproduce_from_saved_records():
    a = L.archived()
    assert (a["roster"]["feasible"], a["roster"]["infeasible"]) == (27, 63)
    assert {k: a["arms"][k]["resolved"][0] for k in "ABC"} == {"A": 26, "B": 29, "C": 22}
    g = a["guides"]
    assert (g["Dp17"]["resolved_infeasible"][0], g["geometry"]["resolved_infeasible"][0]) == (43, 40)
    assert g["Dp17-norec"]["solved"] == g["geometry-norec"]["solved"] == [71, 90]
    assert round(a["D_classifier"]["offline_auroc_140_decided_P17_test"], 3) == 0.952
    assert all(g[x]["moved_on_feasible"][0] == 0 for x in L.GUIDES)          # verify-first search never moves on feasible roots


def test_matched_guides_query_d_for_the_original_target_only_and_never_a_solver():
    import ad_g2b as g2
    import ad_provider as pv
    import p17_d as pd
    root = "p13_2026216000"
    st, cells0, mv, sl = L.domain(root)
    g = pv.Graph(L.OUT / "catalog", "GRAPH_C3")
    ri, member = g2._ri()
    with ar.forbid() as calls:
        gd = pd.Guide("Dp17-norec", st.task, st, mv)
        prov = pv.Precompiled(st.cfg, st.robot, st.s0, st.goal_cell, g, g2.Ranker(ri, member, g2._excl(root), **g2.POLICIES["EXACT+REL_6x1+CATALOG"]),
                              6, 2, "OFF", "test")
        r = L.search(prov, gd, cells0, st.s0.robot.q_rad, mv, sl, max_depth=1, node_cap=4)
    assert not calls and r["edges"] <= 4
    assert gd.d_calls >= 1 and {k[2] for k in gd.cache} == {"t0"} and {k[3] for k in gd.cache} == {st.goal_cell}   # no D(A) / D(B)
    assert all(not pd.Guide(k, st.task, st, mv).recursion for k in L.GUIDES_L3)              # recursion (temporary targets) never runs


def test_catalogs_are_nested_validated_and_provenanced():
    c = json.loads((L.OUT / "CATALOGS.json").read_text())
    assert all(c[k]["rejected"] == 0 for k in c) and c["C4"]["dev_informed"]
    G = {k: json.loads((L.OUT / "catalog" / f"GRAPH_{k}.json").read_text()) for k in ("C1", "C2", "C3", "C4")}
    for a, b in (("C1", "C2"), ("C2", "C3"), ("C3", "C4")):
        assert set(G[a]["actions"]) <= set(G[b]["actions"]) and set(G[a]["connectors"]) <= set(G[b]["connectors"])
    rules = {x.get("origin_rule") for x in G["C4"]["connectors"].values() if x["origin"] == "COMPILED_DIRECT"}
    assert rules == {"LOCAL_BYPASS_HOME_V1", "LOCAL_STATE_CONNECTOR_DEV_INFORMED"}
    led = json.loads((L.OUT / "COMPILE_LEDGER.json").read_text())
    assert sum(e["attempts"] for e in led["entries"]) <= L.LOCAL_BUDGET["compile_attempts"]
    assert sum(e["cpu_s"] for e in led["entries"]) <= L.LOCAL_BUDGET["cpu_s"]


def test_access_diverse_rule_one_pair_per_branch_and_sector():
    import math
    import ad_compile as ac
    import skill as sk
    C = lambda phi, b: sk.Candidate(phi, b, "OK", line=[np.zeros(3)], q_end=np.zeros(3))  # noqa: E731
    good = [C(0.1, 1), C(0.2, 1), C(1.2, 1), C(0.1, -1)]
    goodp = [C(0.0, 1)]
    pairs = ac.direct_pairs(good, goodp, np.zeros(3), 6, "access")
    keys = {(a.branch, b.branch, int(a.phi // (math.pi / 3))) for a, b in pairs}
    assert len(pairs) == len(keys) == 3


def test_pilot_results_are_binary_zero_solver_and_identical_domain_across_guides():
    for f in ("PILOT_L3.json", "PILOT_L3_C4.json"):
        R = json.loads((L.OUT / f).read_text())
        assert R["forbidden_calls"] == 0
        for r in R["rows"].values():
            assert all(isinstance(v["found"], bool) for v in r["guides"].values())
            assert len({v["edges"] for v in r["guides"].values() if not v["found"]}) <= 1      # exhausted the same finite domain


def test_local_config_and_historical_artifacts_untouched(tmp_path):
    assert L.lcfg()["max_depth"] == L.MAX_DEPTH == 2
    src = Path("approach_d.toml").read_text()
    (tmp_path / "bad.toml").write_text(src.replace("node_cap = 60", "node_cap = 60\nonline_fallback = true"))
    with pytest.raises(ValueError):
        L.lcfg(tmp_path / "bad.toml")
    for p in ("config.toml", "runs/p17/eval/P17_PROSPECTIVE.json", "runs/p16/data/dev/labels_v2w2.json", "PoC-takeaway/build.py"):
        assert subprocess.run(["git", "diff", "--quiet", "HEAD", "--", p]).returncode == 0, p
