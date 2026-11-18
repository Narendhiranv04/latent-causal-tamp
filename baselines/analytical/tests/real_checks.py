"""Real-root physics checks (run as a subprocess by test_real.py, with the domain's physics python):
    python -m baselines.analytical.tests.real_checks DOM ROOT_ID PUBLIC.jsonl OUTDIR   -> one JSON line on stdout
TRAIN roots only.  Checks: restore / no cross-contamination after a rejected branch, carried state between moves, connector counted at
depth > 0, Y order independence (endpoint cache), private-field independence + deterministic replay of a full E-M4M run."""
from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np

from baselines.analytical import envs
from baselines.analytical.contract import eligible, legal_dests
from baselines.analytical.em4m import EM4M
from baselines.analytical.phys import RealPhys


def main(dom, rid, pub, out):
    row = next(r for r in map(json.loads, open(pub)) if r["root_id"] == rid)
    E = envs.make_env(dom, str(Path(out) / f"witnesses_{dom}"))
    E.backend.boot()
    inp, res = row["inputs"], {}

    def fresh():
        envs.load_root(E, row)
        return RealPhys(E, row, call_cap_s=120)

    ph = fresh()
    s0 = ph.reset()
    blob = pickle.dumps(s0)
    el = eligible(inp, dom, [])
    g = ph.geo
    good = []                                                              # first successful move per object (nearest dests first)
    for o in el:
        for d in sorted(legal_dests(inp, inp["cells0"]), key=lambda d: (g.dist(inp["cells0"][o], d), d))[:int(os.environ.get("REAL_TRIES", 6))]:
            s = ph.step(s0, o, d)
            if s is not None:
                good.append((o, d, s))
                break
        if len(good) >= 4:
            break
    o1, d1, s1 = good[0]
    res["parent_untouched"] = pickle.dumps(s0) == blob
    ph2 = fresh()                                                          # cold caches; reject-first branch then the same action
    t0 = ph2.reset()
    ph2.step(t0, good[1][0], good[1][1])
    t1 = ph2.step(t0, o1, d1)
    res["restore_equal_after_branch"] = ph2.key(t1) == ph.key(s1) and t1.state_hash() == s1.state_hash()
    res["carried_q_differs_from_qref"] = not np.allclose(s1.q_t, s0.q_t)
    res["two_orders_executed"] = False
    for (o1, d1, s1), (o2, d2, s2) in [(a, b) for a in good for b in good if a[0] < b[0] and a[1] != b[1]][:4]:
        s12, s21 = ph.step(s1, o2, d2), ph.step(s2, o1, d1)
        if s12 is None or s21 is None:
            continue
        res["two_orders_executed"], res["pair"] = True, [[o1, d1], [o2, d2]]
        if dom == "2d":
            recs = s12.physics_payload["records"][len(s1.physics_payload["records"]):]
            res["second_move_starts_at_carried_q"] = bool(np.allclose(np.asarray(recs[0]["q"])[0], s1.q_t, atol=1e-9))
        else:                                                              # 3D: the step restores s1's MuJoCo state, never a reset
            res["second_move_starts_at_carried_q"] = bool(not np.allclose(s12.q_t, s0.q_t))
        res["same_endpoint"] = s12.cells == s21.cells
        res["keys_differ"] = ph.key(s12) != ph.key(s21)
        res["keys_differ_or_transposition"] = res["keys_differ"] or s12.q_t == s21.q_t
        n0 = dict(ph.n)
        res["terminal"] = [ph.terminal(s12), ph.terminal(s21)]
        res["connector_calls_for_two_terminals"] = ph.n["connector_calls"] - n0.get("connector_calls", 0)
        y1 = E.endpoint_y_query(rid, [(o1, d1), (o2, d2)])
        y2 = E.endpoint_y_query(rid, [(o2, d2), (o1, d1)])
        res["y_order_independent"] = y1["y"] == y2["y"] and y2["accounting"]["y_cache_hits"] == 1 and y2["accounting"]["y_calls"] == 0
        break
    # private-field independence + deterministic replay: identical E-M4M runs with real vs corrupted private fields
    runs = []
    rec = json.loads(Path(envs.raw_path(dom, rid)).read_text())
    bad = {**rec, **{k: "CORRUPTED" for k in envs.PRIVATE_RAW_KEYS if k in rec and k != "roles"},
           "roles": {k: "CORRUPTED" for k in rec["roles"]}}
    bad_path = Path(out) / f"corrupted_{rid}.json"
    bad_path.write_text(json.dumps(bad))
    for p in (None, None, str(bad_path)):
        envs.load_root(E, row, p)
        ph = RealPhys(E, row, max_calls=int(os.environ.get("REAL_MAX_CALLS", 16)))   # call-count cap: deterministic stop
        d = EM4M(ph, 0).run()
        runs.append([d.kind, d.prefix, d.termination, d.stats["search"], {k: v for k, v in ph.n.items()}])
    res["deterministic_replay"] = runs[0] == runs[1]
    res["private_fields_irrelevant"] = runs[0] == runs[2]
    res["em4m"] = runs[0][:3]
    print(json.dumps(res, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:5])
