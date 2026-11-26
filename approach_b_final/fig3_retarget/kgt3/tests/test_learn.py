"""KGT3 gate statistics: matched permutation groups, family-weighted concordance (ties 0.5), support counts (gvlab2 env: imports torch)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
pytest.importorskip("torch")
import learn as LN  # noqa: E402


def e(fam, root, prefix, chunk, label, px, h=None):
    return {"fam": fam, "root_id": root, "base": [], "prefix": prefix, "chunk": chunk, "label": label, "px": px, "h": len(prefix) if h is None else h,
            "m": len(chunk), "stratum": "CHAIN"}


def test_groups_concordance_support():
    a, b, c = [1, 10], [2, 20], [3, 30]
    P = [e("f1", "r1", [], [a, b], 1, 0.9), e("f1", "r1", [], [b, a], 0, 0.2),                 # concordant
         e("f2", "r2", [c], [a, b], 1, 0.3), e("f2", "r2", [c], [b, a], 0, 0.3),               # tie -> 0.5
         e("f3", "r3", [], [a, b, c], 1, 0.1), e("f3", "r3", [], [c, b, a], 0, 0.6), e("f3", "r3", [], [b, a, c], 0, 0.05),
         e("f4", "r4", [], [a, b], 1, 0.5), e("f4", "r4", [], [b, a], 1, 0.4)]                  # both executable: not discordant
    G = LN.groups(P)
    assert len(G) == 4
    cc = LN.concordance(P)
    assert cc["families"] == 3 and abs(cc["concordance"] - (1.0 + 0.5 + 0.5) / 3) < 1e-12 and cc["pairs"] == 4
    s = LN.support(P)
    assert s["discordant_perm_families"] == 3 and s["mixed_h1_g23"] == 1 and s["mixed_h0"] == 2


def test_different_scene_not_grouped():
    a, b, c = [1, 10], [2, 20], [3, 30]
    P = [e("f1", "r1", [], [a, b], 1, 0.9), e("f1", "r1", [c], [b, a], 0, 0.2)]
    assert LN.groups(P) == {} and LN.concordance(P)["families"] == 0
