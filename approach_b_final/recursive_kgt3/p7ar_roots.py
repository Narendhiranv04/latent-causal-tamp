#!/usr/bin/env python3
"""P7A-R new independent development roots (P7AR_PREREG section 1).  EVALUATOR-SIDE selection, then a public scene build.
  select  pools (ENG_/ENG2_ engineering layouts; release-disjoint per scaling2d_k12/G1/GEN_SPEC.md) -> filters -> one root per (geom, seed)
          lineage -> strata K6, K5, K4 (K_lb, evaluator-only) x 8 by sha256("P7AR|"+root_id).  witness_set is never copied.
  build   (teacher env, scene construction only, NO teacher query) witness.rec_of + contracts.view2d -> PUBLIC roots file (dev_public schema)
    python p7ar_roots.py select DEV_PUBLIC POOLS_DIR OUT_DIR
    ABF_ROOT=... python p7ar_roots.py build SCALING_CODE_DIR OUT_DIR"""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOLS = ("lay_e.jsonl", "lay_g.jsonl", "lay_fg.jsonl")


def key(rid):
    return hashlib.sha256(("P7AR|" + rid).encode()).hexdigest()


def select(dev_public, pools, out, per=8):
    out = Path(out); (out / "private").mkdir(parents=True, exist_ok=True)
    dev = {json.loads(l)["root_id"] for l in open(dev_public)}
    rows = [dict(json.loads(l), _pool=f) for f in POOLS for l in open(Path(pools) / f)]
    sig = lambda r: (tuple(r["cells0"]), r["goal_cell"], r["tid"])  # noqa: E731
    lin = lambda r: (r["geom"], r["seed"])  # noqa: E731
    devr = [r for r in rows if r["root_id"] in dev]; devlin = {lin(r) for r in devr}; devsig = {sig(r) for r in devr}
    ok = {}
    for r in rows:
        if (r["geom"] == "original" and r["n_objects"] <= 20 and r["root_id"].split("_")[0] in ("ENG", "ENG2") and r["root_id"] not in dev
                and lin(r) not in devlin and sig(r) not in devsig):
            ok.setdefault(sig(r), r)
    L = {}
    for r in ok.values():
        L.setdefault(lin(r), []).append(r)
    chosen, used = [], set()
    for K in (6, 5, 4):
        cand = []
        for ln, rs in L.items():
            if ln in used:
                continue
            ks = sorted((r for r in rs if r["K_lb"] == K), key=lambda r: key(r["root_id"]))
            if ks:
                cand.append(ks[0])
        for r in sorted(cand, key=lambda r: key(r["root_id"]))[:per]:
            chosen.append(r); used.add(lin(r))
    priv = [{k: v for k, v in r.items() if k not in ("witness_set", "_pool")} | {"pool": r["_pool"]} for r in chosen]
    (out / "private" / "roots_private.jsonl").write_text("".join(json.dumps(r) + "\n" for r in priv))
    S = {"eligible_unique_layouts": len(ok), "eligible_lineages": len(L), "selected": len(chosen),
         "by_K": {K: sum(r["K_lb"] == K for r in chosen) for K in (4, 5, 6)},
         "pool_sha256": {f: hashlib.sha256((Path(pools) / f).read_bytes()).hexdigest() for f in POOLS},
         "root_ids": [r["root_id"] for r in chosen]}
    (out / "SELECTION.json").write_text(json.dumps(S, indent=1))
    print(json.dumps({k: S[k] for k in ("eligible_unique_layouts", "eligible_lineages", "selected", "by_K")}))


def build(code, out):
    out = Path(out); sys.path.insert(0, str(code)); sys.path.insert(0, str(HERE.parent))
    import mink as MK, witness as W
    pub = []
    for lay in (json.loads(l) for l in open(out / "private" / "roots_private.jsonl")):
        MK.boot(lay.get("geom", "original"))
        import contracts as CT
        rec, ids = W.rec_of(lay, lay.get("geom", "original"))
        pub.append({"root_id": lay["root_id"], "domain": "2d", "inputs": CT.view2d(rec)})
    (out / "public").mkdir(exist_ok=True)
    (out / "public" / "roots_public.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in sorted(pub, key=lambda r: r["root_id"])))
    print(json.dumps({"built": len(pub)}))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"select": lambda: select(*a[1:4]), "build": lambda: build(*a[1:3])}[a[0]]()
