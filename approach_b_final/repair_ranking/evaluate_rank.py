#!/usr/bin/env python3
"""Evaluator side for P5 (DEV end-to-end with cached exact-contract labels) and P6 (sealed CONFIRM predictions, teacher jobs, physical outcomes).
    python evaluate_rank.py dev MODEL=PRED.jsonl,...                    -> reports/P5_MATRIX.json
    python evaluate_rank.py seal PRED.jsonl ARM@B,... OUTDIR             -> benchmark-format predictions per arm + SEAL (before any teacher call)
    python evaluate_rank.py jobs OUTDIR                                  -> unique REPAIR queries not in any cache (private jobs file)
    python evaluate_rank.py physical OUTDIR CACHEDIR                     -> reports/P6_PHYSICAL.json"""
from __future__ import annotations

import collections, glob, json, sys
from pathlib import Path

import numpy as np

import rr
import diagnostics as D

PRIMARY_ARMS = ["EXACT4@None", "EXACT6@None", "BEAM_SEEDED4@1024", "BEAM_FULL@1024", "PW_MCTS_SEEDED4@1024", "BEAM_SEEDED4@256", "PW_MCTS_SEEDED4@256"]


def key(x):
    return f"{x['arm']}@{x['budget']}"


def outcome_strict(rid, x, lab):
    if x["decision"] != "REPAIR":
        return x["decision"]
    e = lab.get((rid, json.dumps(x["seq"])))
    return rr.z_hist(e["x"], e["y"]) if e else "UNKNOWN"


def dev(spec):
    files = dict(s.split("=", 1) for s in spec.split(","))
    vm, lab = rr.val_meta(), rr.strict_labels()
    samp, _, _ = rr.bundle()
    cv = rr.cvae_table(rr.public_val(), samp, "val")
    P = {m: {r["root_id"]: r for r in rr.jl(f)} for m, f in files.items()}
    base = P["A0"]
    out = {}
    for m, preds in P.items():
        for arm in sorted({key(x) for r in preds.values() for x in r["results"]}):
            for part in ("DEV_CAL", "DEV_AUDIT"):
                rows = []
                for rid, r in preds.items():
                    if vm[rid]["part"] != part:
                        continue
                    x = next(y for y in r["results"] if key(y) == arm)
                    b = next(y for y in base[rid]["results"] if key(y) == "EXACT4@None")
                    rk = rr.Ranks(cv[rid])
                    rows.append({"rid": rid, "K": vm[rid]["K"], "fam": vm[rid]["family"], "o": outcome_strict(rid, x, lab), "ob": outcome_strict(rid, b, lab),
                                 "off": x["decision"] == "REPAIR" and rk.seq_info(x["seq"])["n_off4"] > 0, "same": x["seq"] == b["seq"] and x["decision"] == b["decision"]})
                t = [r for r in rows if r["K"] in ("1", "2")]
                c = collections.Counter(r["o"] for r in t); dec = sum(v for k, v in c.items() if k != "UNKNOWN")
                both = [r for r in t if r["o"] != "UNKNOWN" and r["ob"] != "UNKNOWN"]
                d = [float(r["o"] == "SUCCESS") - float(r["ob"] == "SUCCESS") for r in both]
                out[f"{m}|{arm}|{part}"] = {
                    "K1K2": len(t), "counts": dict(c), "decided": dec, "decided_success": c["SUCCESS"], "rate": round(c["SUCCESS"] / dec, 4) if dec else None,
                    "unknown": c["UNKNOWN"], "ITT": [round(c["SUCCESS"] / len(t), 4), round((c["SUCCESS"] + c["UNKNOWN"]) / len(t), 4)] if t else None,
                    "paired_vs_A0_EXACT4_cached": {"pairs": len(both), "delta": D.cboot(d, [r["fam"] for r in both]),
                                                   "wins": sum(1 for x in d if x > 0), "losses": sum(1 for x in d if x < 0)},
                    "changed_vs_A0_EXACT4": sum(1 for r in t if not r["same"]), "off_D4_picks": sum(r["off"] for r in t),
                    "off_D4_verified_success": sum(1 for r in t if r["off"] and r["o"] == "SUCCESS"),
                    "off_D4_verified_fail": sum(1 for r in t if r["off"] and r["o"] in ("FAIL_X", "FAIL_Y")),
                    "K0_correct_NOOP": f"{sum(1 for r in rows if r['K'] == '0' and r['o'] == 'NOOP')}/{sum(1 for r in rows if r['K'] == '0')}",
                    "NONE_correct_ABSTAIN": f"{sum(1 for r in rows if r['K'] == 'NONE' and r['o'] == 'ABSTAIN')}/{sum(1 for r in rows if r['K'] == 'NONE')}"}
    rr.wjson(rr.REP / "P5_MATRIX.json", out)
    for k, v in out.items():
        print(k, v["decided_success"], "/", v["decided"], "unk", v["unknown"], "pair", v["paired_vs_A0_EXACT4_cached"]["delta"], v["paired_vs_A0_EXACT4_cached"]["wins"], v["paired_vs_A0_EXACT4_cached"]["losses"])


# ------------------------------------------------------------------------------------------------------------- P6
def seal(pred, arms, outdir):
    import benchmark as BM
    import run_eval as RE
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    pub = {r["root_id"]: r for r in rr.jl(rr.PRIV / "confirm/public_confirm_2d.jsonl")}
    recs = rr.jl(pred)
    for a in arms.split(","):
        arm, _, b = a.partition("@"); B = None if b in ("", "None") else int(b)
        f = out / f"pred_{arm}@{b or 'None'}.jsonl"
        f.write_text("".join(json.dumps(RE.bench_format(r, arm, B, pub[r["root_id"]])) + "\n" for r in recs))
        BM.seal(str(f), str(rr.PRIV / "confirm/public_confirm_2d.jsonl"))
        BM.validate(str(rr.PRIV / "confirm/public_confirm_2d.jsonl"), str(f))


def jobs(outdir, gv_root="/home/projects/long-horizon/naren_workspace/xy_repair_ranking/confirm"):
    idx = {e["root_id"]: e for e in rr.jl(rr.PRIV / "confirm/PRIVATE_INDEX.jsonl")}
    want = collections.defaultdict(set)
    for f in sorted(Path(outdir).glob("pred_*.jsonl")):
        seal_ = json.loads(Path(str(f) + ".SEAL.json").read_text())
        assert seal_["sha256"] == rr.sha(f), f"{f} not sealed"
        for r in rr.jl(f):
            if r["decision"] == "REPAIR":
                want[r["root_id"]].add(json.dumps([[m["object_id"], int(m["destination_cell"])] for m in r["moves"]]))
    rows = [{"root_id": rid, "dom": "2D", "path": f"{gv_root}/{idx[rid]['path']}", "geom": idx[rid]["geom"], "ids": idx[rid]["ids"],
             "seqs": [json.loads(s) for s in sorted(ss)]} for rid, ss in sorted(want.items())]
    f = rr.PRIV / "p6_jobs_2d.jsonl"
    f.write_text("".join(json.dumps(j) + "\n" for j in rows))
    n = sum(len(j["seqs"]) for j in rows)
    res = {"roots": len(rows), "queries": n, "jobs_sha256": rr.sha(f), "by_K": dict(collections.Counter(idx[j["root_id"]]["K"] for j in rows))}
    rr.wjson(Path(outdir) / "JOBS_SUMMARY.json", res)
    print(json.dumps(res))


def physical(outdir, cache):
    import benchmark as BM
    idx = {e["root_id"]: e for e in rr.jl(rr.PRIV / "confirm/PRIVATE_INDEX.jsonl")}
    lab = rr.strict_labels([Path(cache) / "verify_2d.jsonl"])
    L, op_outcome = BM.cache_labels(cache, "2d")
    preds = {}
    for f in sorted(Path(outdir).glob("pred_*.jsonl")):
        assert json.loads(Path(str(f) + ".SEAL.json").read_text())["sha256"] == rr.sha(f)
        preds[f.stem[5:]] = {r["root_id"]: r for r in rr.jl(f)}
    per = []
    for rid, e in sorted(idx.items()):
        row = {"root_id": rid, "K": e["K"], "family": e["parent_family_id"]}
        for arm, P in preds.items():
            r = P[rid]
            seq = [[m["object_index"], int(m["destination_cell"])] for m in r["moves"]]
            x = {"decision": r["decision"], "seq": seq}
            sel = None if r["decision"] == "ABSTAIN" else [] if r["decision"] == "NOOP" else seq
            le = lab.get((rid, json.dumps(seq))) if r["decision"] == "REPAIR" else None
            row[arm] = {"decision": r["decision"], "seq": seq if r["decision"] == "REPAIR" else None, "strict": outcome_strict(rid, x, lab),
                        "logical": (r["decision"] if r["decision"] != "REPAIR" else {1: "SUCCESS", 0: "FAIL", None: "UNKNOWN"}[rr.z_logic(le["x"], le["y"]) if le else None]),
                        "operational": op_outcome(sel, L, rid), "p11": r["score_p11"],
                        "x_status": le and le["xs"], "y_status": le and le["ys"]}
        per.append(row)
    (rr.REP / "P6_PHYSICAL_PER_ROOT.jsonl").write_text("".join(json.dumps(p) + "\n" for p in per))
    return per


def cboot_pairs(per, a, b, mode, Ks=("1", "2"), n=4000):
    rows = [p for p in per if p["K"] in Ks]
    ok = lambda o: o != "UNKNOWN"  # noqa: E731
    both = [p for p in rows if ok(p[a][mode]) and ok(p[b][mode])]
    d = [float(p[a][mode] == "SUCCESS") - float(p[b][mode] == "SUCCESS") for p in both]
    return {"pairs": len(both), "delta_ci": D.cboot(d, [p["family"] for p in both], n=n), "wins": sum(1 for x in d if x > 0), "losses": sum(1 for x in d if x < 0)}


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "dev":
        dev(sys.argv[2])
    elif c == "seal":
        seal(*sys.argv[2:5])
    elif c == "jobs":
        jobs(sys.argv[2])
