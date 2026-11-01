"""BXY-P20 / P21: K34 construction semantics (certified necessity, frozen catalogue outcome-blindness, caps), wave determinism, readiness
counting, and the P21 design's reuse of the unchanged P17 model family."""
import copy
import json

import pytest

import bxy_p16 as G
import bxy_p20_k34 as Z

pytestmark = pytest.mark.skipif(not (Z.wdir("k1") / "DESIGN.json").exists(), reason="P20 wave k1 missing")


def _roots(w="k1"):
    return Z.roots_of(w)


def test_local_roots_carry_certified_necessity_and_validated_intent():
    for k, r in _roots().items():
        C = r["construction"]
        if C.get("family", "").startswith("local_"):
            assert C["K_cert"] == C["K_geom"] == r["spec"]["K_intent"]
            assert len(C["intended"]) == C["K_geom"] and len({o for o, _ in C["intended"]}) == C["K_geom"]
            assert r["q_ref"] == r["q0"] == r["scene"]["robot"]["q_rad"]


def test_catalogue_outcome_blind_and_within_caps():
    R = _roots()
    k = next(k for k, r in R.items() if r["construction"].get("K_geom") == 4)
    rec = R[k]
    base = Z.candidates(rec)
    noisy = copy.deepcopy(rec)
    noisy["labels"], noisy["verified_K"] = {"original": {"y": 1}}, 4
    assert Z.candidates(noisy) == base
    assert len(rec["catalogue_v21"]) <= Z.MAX_CANDS and len(rec["design_v21"]["queries"]) <= Z.MAX_QUERIES
    kinds = {c["kind"] for c in rec["catalogue_v21"]}
    assert {"repair", "prefix_1", "prefix_2", "prefix_3", "omission_0"} <= kinds


def test_wave_k1_reproducible_after_revisions():
    R = _roots()
    k = "2d-bxyg34dev-k1-s024" if "2d-bxyg34dev-k1-s024" in R else sorted(R)[0]
    r = R[k]
    n = Z.construct(r["spec"], Z.ids("k1", int(k[-3:]), r["spec"]))
    drop = lambda d: {a: ({x: y for x, y in b.items() if "cpu" not in x} if a == "construction" else b) for a, b in d.items()  # noqa: E731
                      if a not in ("catalogue_v21", "design_v21")}
    assert drop(n) == drop(r)


def test_readiness_counts_only_complete_shorter_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(Z, "OUT", tmp_path)
    (tmp_path / "kx").mkdir()
    row = lambda K, claim, fam: {"results": 5, "verified_K_claim": claim, "family": fam, "K_cert": K, "K_geom": K, "strict_discordant": [1] if K >= 3 else [],  # noqa: E731
                                 "harmful": [1], "neutral_ok": True}
    rows = [row(3, 3, "a") for _ in range(10)] + [row(3, 3, "b") for _ in range(10)] + [row(4, 4, "a") for _ in range(10)] + [row(4, 4, "b") for _ in range(10)]
    (tmp_path / "kx" / "SUMMARY.json").write_text(json.dumps({"rows": rows}))
    assert Z.readiness(["kx"])["decision"] == "K34_DATA_READY"
    rows2 = [dict(r, verified_K_claim=None) if r["K_geom"] == 4 else r for r in rows]
    (tmp_path / "kx" / "SUMMARY.json").write_text(json.dumps({"rows": rows2}))
    assert Z.readiness(["kx"])["decision"] == "K4_PHYSICAL_DATA_NOT_ESTABLISHED"


def test_generate_refuses_unknown_wave():
    with pytest.raises(PermissionError):
        Z.generate("bxyg21confirm")


def test_p21_reuses_the_unchanged_p17_arms():
    import bxy_p17 as M
    import bxy_p21_k34 as H
    assert H.ARMS is M.ARMS and H.arm_hooks is M.arm_hooks and H.roster() == M.roster()
