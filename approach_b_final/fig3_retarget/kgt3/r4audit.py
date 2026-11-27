#!/usr/bin/env python3
"""R4.0 evidence-accounting audit (no new physical runs; historical artefacts are read, never rewritten).
    $PYG r4audit.py labels       -> O/kgt3/r4/audit_labels.json : P2 outcome taxonomy, replay status of every retained positive label,
                                    descriptive support under STRICT labels (positives from replayed successes, negatives certified only)
    $PYG r4audit.py length       -> O/kgt3/r4/audit_length.json : does the long-plan energy favour short plans / few chunks? (corrected P4 rerun)"""
from __future__ import annotations

import collections, json, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
import guard as GD  # noqa: E402
O = K.C.FIG3 / "kgt3"
R4 = O / "r4"


def runs(dom):
    R, J = {}, {}
    for tag in ("p2", "p2x"):
        jf, rf = O / f"jobs_{tag}_{dom}.json", O / f"phys_{tag}_{dom}.jsonl"
        if jf.exists():
            J.update({j["key"]: j for j in json.loads(jf.read_text())})
            R.update({json.loads(l)["key"]: json.loads(l) for l in open(rf)})
    return J, R


def labels():
    import learn as LN
    out = {}
    for dom in ("3d", "2d"):
        J, R = runs(dom)
        tax = collections.Counter(GD.outcome(r) for r in R.values())
        tax_split = collections.Counter(f"{J[k]['split']}|{GD.outcome(r)}" for k, r in R.items())
        L = [json.loads(l) for l in open(O / f"labels_p2_{dom}.jsonl")]
        rep = collections.Counter()
        strict = []
        for e in L:
            r = R[e["key"]]; X = r.get("X") or {}
            oc = GD.outcome(r)
            if e["label"] == 1:
                if X.get("x") == 1:
                    ok = (r.get("REPLAY") or {}).get("replay") == 1 if dom == "3d" else bool(X.get("independent_replay"))
                    rep["pos_from_success_replayed" if ok else "pos_from_success_NOT_replayed"] += 1
                    if ok:
                        strict.append(e)
                else:
                    rep["pos_prefix_of_failed_run_no_replay"] += 1                 # executed prefix chunk; the run failed later -> never replayed
            elif e["label"] == 0:
                rep[f"neg_{oc}"] += 1
                if oc == "CERTIFIED_INFEASIBLE":
                    strict.append(e)
        sup = {}
        for name, S in (("historical", [e for e in L if e["label"] in (0, 1)]), ("strict", strict)):
            sup[name] = {sp: LN.support([e for e in S if e["split"] == sp]) for sp in ("TRAIN", "SELECT", "GATE")}
        out[dom] = {"runs": len(R), "taxonomy": dict(tax), "taxonomy_by_split": dict(sorted(tax_split.items())), "labels": len(L),
                    "label_provenance": dict(rep), "support": sup,
                    "note": "STRICT is descriptive only: the P2 gate decisions stand (no reopening, no relabel of historical artefacts)."}
        print(dom, json.dumps(out[dom]["taxonomy"]), json.dumps(out[dom]["label_provenance"]))
        print("  support GATE historical", sup["historical"]["GATE"], "strict", sup["strict"]["GATE"])
    R4.mkdir(parents=True, exist_ok=True)
    (R4 / "audit_labels.json").write_text(json.dumps(out, indent=1))


def length():
    out = {}
    for dom in ("2d", "3d"):
        f = R4 / f"p4c_{dom}.jsonl"
        P = [json.loads(l) for l in open(f)]
        old = {json.loads(l)["root_id"]: json.loads(l) for l in open(O / f"p4_model_only_{dom}.jsonl")} if (O / f"p4_model_only_{dom}.jsonl").exists() else {}
        d = {"roots": len(P)}
        ga = [p["arms"]["GA"] for p in P]
        bys = [{int(k): v for k, v in (a.get("by_size") or {}).items()} for a in ga]
        sizes = sorted({k for b in bys for k in b})
        d["E_by_size_median"] = {k: statistics.median([b[k]["E"] for b in bys if k in b]) for k in sizes}
        d["minusLogY_by_size_median"] = {k: statistics.median([-__import__("math").log(max(1e-8, b[k]["y_global"])) for b in bys if k in b and b[k]["y_global"]]) for k in sizes}
        d["F_by_size_median"] = {k: statistics.median([b[k]["F"] for b in bys if k in b and b[k].get("F") is not None]) for k in sizes if k > 3}
        d["chunks_by_size_median"] = {k: statistics.median([b[k]["n_chunks"] for b in bys if k in b]) for k in sizes}
        d["argmin_size_hist"] = dict(collections.Counter(min(b, key=lambda k: (round(b[k]["E"], 12), k)) for b in bys if b))
        d["witness_K_hist"] = dict(collections.Counter(p["K"] for p in P))
        # how often is E monotone non-decreasing in size? (intrinsic short-plan preference)
        d["E_nondecreasing_in_size"] = sum(all(b[k]["E"] <= b[k + 1]["E"] + 1e-12 for k in sorted(b) if k + 1 in b) for b in bys)
        # within long plans: chosen partition vs maximal chunking (fewest chunks = ceil(m/3))
        lp = [(len(a["seq"]), a["n_chunks"]) for a in ga if a.get("seq") and len(a["seq"]) > 3]
        d["long_selected_chunks_vs_min"] = dict(collections.Counter(f"m{m}:chunks{n}:min{-(-m // 3)}" for m, n in lp))
        modes = collections.Counter(a["mode"] for a in ga)
        d["GA_modes"] = dict(modes); d["GA_exhausted"] = sum(bool(a.get("exhausted")) for a in ga)
        d["scores_median"] = {k: statistics.median([a["scores"][k] for a in ga if a.get("scores")]) for k in ("requested", "x_unique", "cache_hits", "batches", "dp_lookups")}
        d["est_theoretical_dp_lookups_median"] = statistics.median([a["est_theoretical_dp_lookups"] for a in ga])
        d["est_distinct_x_median"] = statistics.median([a["est_distinct_x"] for a in ga])
        d["wall_median_max"] = [statistics.median([a["wall_s"] for a in ga]), max(a["wall_s"] for a in ga)]
        ch = collections.Counter()
        for p in P:
            for arm, a in p["arms"].items():
                o = (old.get(p["root_id"]) or {}).get("arms", {}).get(arm)
                if o:
                    ch[f"{arm}:{'same' if o['seq'] == a['seq'] and o['partition'] == a['partition'] else 'changed'}"] += 1
                ch[f"{arm}:len>3"] += bool(a.get("long"))
                ch[f"{arm}:short_kind_{a.get('kind')}"] += 1
        d["vs_P4"] = dict(sorted(ch.items()))
        out[dom] = d
        print(dom, json.dumps(d, default=str)[:1500])
    (R4 / "audit_length.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    {"labels": labels, "length": length}[sys.argv[1]]()
