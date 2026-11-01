"""BXY-P19: certified-closure monotonicity, K_cert semantics, strict order key parsing."""
import itertools

import pytest

import bxy_p16 as G
import bxy_p19_audit as A

pytestmark = pytest.mark.skipif(not G._maps_file().exists(), reason="P16 access maps missing")


def test_certified_closure_is_monotone_in_the_disc_set():
    """If the target pick screen is certified closed with a disc set, it stays certified closed when discs are added (never re-opens)."""
    src = 29
    ring = [21, 28, 37]
    s3 = G._scene([src] + ring)
    n3, c3 = A.screen_cert("pick", s3)
    assert n3 == 0
    for extra in (20, 36, 27):
        n4, c4 = A.screen_cert("pick", G._scene([src] + ring + [extra]))
        assert n4 == 0 and (c4 or not c3)
    for k in range(3):
        for sub in itertools.combinations(ring, k):
            n, _ = A.screen_cert("pick", G._scene([src, *sub]))
            assert n >= 0


def test_k_cert_zero_when_s0_open_and_bounded_by_movables():
    R = G.roots_of("wA")
    if not R:
        pytest.skip("wave wA missing")
    rec = R["2d-bxyg21dev-wA-s000"]                                   # an `open` K0 root
    assert A.k_cert(rec, 2)[0] == 0
    rec2 = R["2d-bxyg21dev-wA-s026"]
    k, _ = A.k_cert(rec2, 3)
    assert 0 <= k <= 3


def test_strict_order_key_parsing():
    assert A._seq("X2:root:abc:o01>12.o02>13") == [("o01", 12), ("o02", 13)]
    assert sorted(A._seq("X2:r:c:o02>13.o01>12")) == sorted(A._seq("X2:r:c:o01>12.o02>13"))
