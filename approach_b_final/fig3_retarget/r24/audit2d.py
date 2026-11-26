#!/usr/bin/env python3
"""R2.4C audit: physically verified 2D K4-K6 repair witnesses in NON-TEST material (never opens TEST indices / files or release_v2).
Scans (1) the R2.0 exact label pool (TRAIN/VAL verifier caches), (2) every TRAIN/VAL raw root record listed in the private TRAIN/VAL indices
(verified_K, B-label sequences with y = 1 and their lengths, K-certificate fields), (3) every Fig.3 R1-R2.3 teacher result on 2D roots.
    python audit2d.py OUT.json"""
from __future__ import annotations

import collections, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent), str(HERE.parent / "r2")]
import common as C  # noqa: E402


def main(out):
    res = {"pool": {}, "raw": {}, "fig3_results": {}}
    P = C.pool("2d")
    Y = {}
    for e in P:
        if e["t"] == "Y":
            Y[(e["root"], json.dumps(sorted(map(list, e["edit"]))))] = e["y"]
    lens = collections.Counter(); ver = collections.Counter()
    for e in P:
        if e["t"] == "X":
            m = len(e["seq"]); lens[m] += 1
            if e["x"] == 1 and Y.get((e["root"], json.dumps(sorted(map(list, e["seq"]))))) == 1:
                ver[m] += 1
    res["pool"] = {"x_labels_by_m": dict(sorted(lens.items())), "verified_xy_by_m": dict(sorted(ver.items()))}
    vk, blen, n, fields = collections.Counter(), collections.Counter(), 0, collections.Counter()
    long_roots = []
    for sp in ("train", "val"):
        for l in open(C.PRIV / f"private_{sp}_2d.jsonl"):
            e = json.loads(l)
            try:
                rec = json.loads(Path(e["path"]).read_text())
            except (OSError, KeyError):
                fields["unreadable"] += 1; continue
            n += 1
            vk[str(rec.get("verified_K"))] += 1
            for k in ("K", "certified_K", "k_min", "label_K"):
                if k in rec:
                    fields[k] += 1
            ok = [b for b in (rec.get("labels") or {}).get("B", []) or [] if b.get("y") == 1]
            for b in ok:
                blen[(len(b.get("sequence") or []), b.get("role"))] += 1
            if ok and min(len(b["sequence"]) for b in ok) >= 4 and rec.get("verified_K") not in (0, 1, 2, 3):
                long_roots.append({"split": sp, "root": rec["ids"]["root_id"], "N": len(rec["scene"]["objects"]), "shortest_verified": min(len(b["sequence"]) for b in ok),
                                   "verified_K": rec.get("verified_K"), "roles": sorted({b.get("role") for b in ok})})
    res["raw"] = {"records": n, "verified_K": dict(vk), "B_y1_by_len_role": {f"{k[0]}|{k[1]}": v for k, v in sorted(blen.items(), key=str)}, "fields": dict(fields), "candidate_K4plus_roots": long_roots,
                  "n_candidate_K4plus": len(long_roots), "definition": "shortest y=1 B sequence >= 4 and verified_K not in 0..3 (witnessed length, minimum unknown)"}
    F = C.R2
    fl = collections.Counter()
    for f in ("phys_2d.jsonl", "phys_S_2d.jsonl"):
        for l in open(F / f):
            e = json.loads(l)
            X = e.get("X") or {}
            if X.get("x") == 1 and (e.get("Y") or {}).get("y") == 1:
                fl[len(X.get("ordered_actions") or [])] += 1
    res["fig3_results"] = {"verified_xy_by_len": dict(sorted(fl.items())), "note": "R2.3 plans are on K3 VAL roots; a verified plan longer than 3 is not a K>3 witness (shorter repairs exist)"}
    res["not_opened"] = ["TEST indices and records", "release_v2 (protected K4-K12 scaling set)"]
    res["other_known"] = {"kgt3_P7A-R": "24 roots, static-only feasibility (no physical execution witnesses) -- [[kgt3-recursive]] / R2.3",
                          "scaling2d_release_v2": "protected; not usable for development"}
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "raw"}, indent=1)); print(json.dumps({k: v for k, v in res["raw"].items() if k != "long_witness_roots"}))


if __name__ == "__main__":
    main(sys.argv[1])
