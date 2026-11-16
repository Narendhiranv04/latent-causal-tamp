#!/usr/bin/env python3
"""V3.2 Phase C: TRAIN-only expanded-candidate mining for physically labelled X / Y evidence (no validation / test root is ever touched).

Frozen task cVAE q2init_all seed 0 -> top-6 destinations per movable object (exhaustive.proposals; M4 / M5 are nested prefixes) -> EVERY legal
ordered K1-K3 sequence (exhaustive.stream) scored in fixed chunks by the frozen V3 D seed 0 -> a compact, label-blind, seeded per-root sample
(the full pool is never stored):
  sel_M4 / sel_M5 / sel_M6   the frozen-rule top-1 repair at each M (exhaustive.Selectors, exact xy.choose semantics)
  high_2 / high_3 ...        next highest-p11 candidates (winner's-curse / high-confidence false-positive probes), up to N_HIGH
  band_0.3_0.9 / 0.1_0.3 / lt_0.1, random   one seeded reservoir draw per p11 band + one uniform draw over the whole M6 pool
  order_of_sel_M6 / order_of_known          every other order of the M6 top-1 assignment and of the known successful assignments in the pool
Items carry the proposal rank r (M membership = r < M) and the frozen scores.  Teacher labelling is onpolicy.v3_label (unchanged teachers:
Y once per canonical endpoint, X per order where Y = 1 or seeded-flagged, X | Y = 0 kept for a seeded third), output under $V34_DIR.

    python v32c.py roots DOM N1 N2 N3 N0 NNONE          -> stratified TRAIN roots (sha256 "v32c|" order), printed summary
    python v32c.py mine  DOM N1 N2 N3 N0 NNONE [PART]   -> $V34_DIR/<dom>/mine.jsonl (resumable; PART 'i/n' shards roots)
    python v32c.py items DOM                            -> $V34_DIR/<dom>/items_v32c.json (onpolicy.v3_label format)"""
from __future__ import annotations

import hashlib, itertools, json, os, random, sys, time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exhaustive as EX  # noqa: E402

ABF = EX.ABF
OUT = Path(os.environ.get("V34_DIR", str(EX.V3OUT / "v3_2c")))
RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}         # frozen V3 rule (v3_5/rule_*.json)
N_HIGH, BANDS = 4, ((0.3, 0.9), (0.1, 0.3), (0.0, 0.1))


def roots(dom, n):
    rows = [r for r in EX.rows_of(dom, "train")]
    out = []
    for K, k in zip(("1", "2", "3", "0", "NONE"), n):
        out += sorted((r for r in rows if r["K_legacy"] == K), key=lambda r: hashlib.sha256(("v32c|" + r["root_id"]).encode()).hexdigest())[:k]
    return out


def sig(s):
    return json.dumps([list(map(int, x)) for x in s])


def mine_root(root, D6, scorer, known, chunk=8192):
    rng = random.Random("v32c|" + root.id)
    sel = EX.Selectors([RULE])
    noop = scorer.score(root, [[]])[0]
    high, res, seen = [], {b: None for b in BANDS + ("all",)}, {b: 0 for b in BANDS + ("all",)}
    found, n_all, buf, rbuf = {}, 0, [], []

    def flush():
        nonlocal high, n_all
        if not buf:
            return
        sc = scorer.score(root, [list(map(list, s)) for s in buf])
        p = np.array([c["p11"] for c in sc], float); py = np.array([c["py"] for c in sc], float); px = np.array([c["px"] for c in sc], float)
        J = np.array([c["J"] for c in sc], float); m = np.array([len(s) for s in buf]); r = np.array(rbuf)
        D = np.array([root.displacement(list(s)) for s in buf], float)
        sel.update(buf, p, m, D, J, r, {"py": py, "px": px})
        top = np.argsort(-p, kind="stable")[:N_HIGH + 3]
        high = sorted(high + [(-float(p[i]), sig(buf[i]), int(r[i]), float(py[i]), float(px[i])) for i in top])[:N_HIGH + 3]
        for i, s in enumerate(buf):                                    # seeded reservoir (size 1) per band and over the whole pool
            n_all += 1
            for b in BANDS + ("all",):
                if b == "all" or b[0] <= p[i] < b[1]:
                    seen[b] += 1
                    if rng.random() < 1.0 / seen[b]:
                        res[b] = (sig(s), float(p[i]), int(r[i]), float(py[i]), float(px[i]))
            if s in known:
                found[sig(s)] = (float(p[i]), int(r[i]), float(py[i]), float(px[i]))
        buf.clear(); rbuf.clear()

    for s, r in EX.stream(D6, 6):
        buf.append(s); rbuf.append(r)
        if len(buf) >= chunk:
            flush()
    flush()
    dec = sel.finish(noop["p11"])
    return {"root_id": root.id, "K": root.row["K_legacy"], "p_noop": noop["p11"], "n_scored_M6": n_all, "D6": {str(o): v for o, v in D6.items()},
            "decisions": {str(M): dec[M][0] for M in EX.MS},
            "high": [{"seq": json.loads(h[1]), "p11": -h[0], "r": h[2], "py": h[3], "px": h[4]} for h in high],
            "reservoir": {("%s_%s" % b if b != "all" else "all"): (None if v is None else {"seq": json.loads(v[0]), "p11": v[1], "r": v[2], "py": v[3], "px": v[4]})
                          for b, v in res.items()},
            "band_sizes": {("%s_%s" % b if b != "all" else "all"): seen[b] for b in BANDS + ("all",)},
            "known_in_pool": [{"seq": json.loads(k), "p11": v[0], "r": v[1], "py": v[2], "px": v[3]} for k, v in sorted(found.items())]}


def mine(dom, n, part=None):
    import torch
    import search as S
    (OUT / dom).mkdir(parents=True, exist_ok=True)
    fo = OUT / dom / "mine.jsonl"
    done = {json.loads(l)["root_id"] for l in open(fo)} if fo.exists() else set()
    rows = roots(dom, n)
    if part:
        i, k = map(int, part.split("/"))
        rows = [r for r in rows if int(hashlib.sha256(r["root_id"].encode()).hexdigest(), 16) % k == i]
    samp, scor = EX.setup(dom)
    t0 = time.time()
    with open(fo, "a") as f:
        for r in rows:
            if r["root_id"] in done:
                continue
            root = S.Root(r, dom)
            t1 = time.time()
            rec = mine_root(root, EX.proposals(root, samp), scor, EX.known_success(r))
            rec["wall_s"] = round(time.time() - t1, 3)
            rec["gpu_peak_mib"] = round(torch.cuda.max_memory_allocated() / 2 ** 20, 1) if torch.cuda.is_available() else None
            f.write(json.dumps(rec) + "\n"); f.flush()
    print(json.dumps({"out": str(fo), "roots": sum(1 for _ in open(fo)), "s": round(time.time() - t0, 1)}), flush=True)


def items(dom):
    """Label-blind item selection from mine.jsonl (seeded per root); exact duplicates of an existing snapshot X label are dropped."""
    import contracts as CT
    rows = {r["root_id"]: r for r in EX.rows_of(dom, "train")}
    lab_rows = rows
    if os.environ.get("V32_DEDUP_SNAPSHOT"):                                  # dedupe against the training snapshot (V2 + V3-4 TRAIN labels)
        lab_rows = {r["root_id"]: r for r in map(json.loads, open(Path(os.environ["V32_DEDUP_SNAPSHOT"]) / f"data{dom}.jsonl")) if r["split"] == "train"}
    out, n_drop = [], 0
    for c in map(json.loads, open(OUT / dom / "mine.jsonl")):
        row = rows[c["root_id"]]
        rng = random.Random("v32items|" + c["root_id"])
        have_x = {json.dumps(q["seq"]) for q in lab_rows[c["root_id"]]["labels"]["X"]}
        pick, why, meta = [], [], []

        def add(x, w):
            nonlocal n_drop
            if x is None or not x["seq"] or x["seq"] in pick:
                return
            if json.dumps(x["seq"]) in have_x:
                n_drop += 1; return
            pick.append(x["seq"]); why.append(w); meta.append({k: x.get(k) for k in ("p11", "r", "py", "px")})

        for M in ("4", "5", "6"):
            add(c["decisions"][M], f"sel_M{M}")
        for h in c["high"]:
            if sum(w.startswith("high") for w in why) < 2:
                add(h, f"high_{len([w for w in why if w.startswith('high')]) + 2}")
        for b in ("0.3_0.9", "0.1_0.3", "0.0_0.1"):
            add(c["reservoir"][b], f"band_{b}")
        add(c["reservoir"]["all"], "random")
        pool = {json.dumps(h["seq"]): h for h in c["high"]}
        for base, w in ([(c["decisions"]["6"], "order_of_sel_M6")] + [(k, "order_of_known") for k in c["known_in_pool"][:2]]):
            if base and base["seq"] and len(base["seq"]) > 1:
                for p in itertools.permutations(base["seq"]):
                    add({"seq": [list(x) for x in p], **{k: pool.get(json.dumps([list(x) for x in p]), {}).get(k) for k in ("p11", "r")}}, w)
        if not pick:
            continue
        ids = row["inputs"]["ids"]
        out.append({"root": c["root_id"], "K": c["K"], "cands": pick, "why": why, "meta": meta, "x_on_y0": [rng.random() < 1 / 3 for _ in pick],
                    "seqs": [[(ids[i], d) for i, d in q] for q in pick], "mode": "v32c",
                    "endpoints": len({CT.ekey(q) for q in pick})})
    p = OUT / dom / "items_v32c.json"
    p.write_text(json.dumps(out))
    print(json.dumps({"dom": dom, "roots": len(out), "candidates": sum(len(i["cands"]) for i in out),
                      "endpoints": sum(i["endpoints"] for i in out), "dropped_already_labelled": n_drop}))


if __name__ == "__main__":
    c, dom = sys.argv[1], sys.argv[2]
    if c == "roots":
        rs = roots(dom, [int(x) for x in sys.argv[3:8]])
        print(json.dumps({"dom": dom, "roots": len(rs), "by_K": {K: sum(r["K_legacy"] == K for r in rs) for K in ("1", "2", "3", "0", "NONE")}}))
    elif c == "mine":
        mine(dom, [int(x) for x in sys.argv[3:8]], sys.argv[8] if len(sys.argv) > 8 else None)
    elif c == "items":
        items(dom)
    else:
        raise SystemExit(__doc__)
