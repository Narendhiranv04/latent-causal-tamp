#!/usr/bin/env python3
"""EVALUATOR ONLY (post-seal) for P4_PROTOCOL_V1.  Reads sealed P4 arms (predictions + traces with candidate pools), private DEV labels,
kill tables and teacher verification rows.  Two modes:
  extra   write EXTRA_JOBS.jsonl: per scene, up to 5 statically complete pool candidates (best energy first) for post-hoc teacher checks
  report  P4 metrics (§5): success, object/destination/order coverage, generation vs ranking failure, length vs K, temporary-subgoal success,
          effort, stop reasons, per-K tables, paired matched-compute sign tests -> P4_SUMMARY.json + p4_per_scene.jsonl
    python p4_eval.py extra|report P4_DIR DEV_PUBLIC DEV_PRIVATE TABLES VERIFY.jsonl OUT_DIR"""
import collections, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dev_eval import Static, jl, sha, mcnemar  # noqa: E402

ARMS = ("R0_REC", "R0_REC2", "R0_FLAT", "R1", "R2", "R3", "F", "N")


def load(p4):
    A = {}
    for a in ARMS:
        d = Path(p4) / a
        if (d / "SEAL.json").exists():
            s = json.loads((d / "SEAL.json").read_text())
            assert sha(d / "predictions.jsonl") == s["predictions_sha256"], f"seal mismatch {a}"
            A[a] = {p["root_id"]: p for p in jl(d / "predictions.jsonl")}
    return A


def main(mode, p4, dev_public, priv, tables, verify_f, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    ST = Static(tables)
    pub = {r["root_id"]: r for r in jl(dev_public)}
    pv = {r["root_id"]: r for r in jl(Path(priv) / "dev_private.jsonl")}
    A = load(p4)
    tr = lambda a, rid: json.loads((Path(p4) / a / "traces" / f"{rid}.json").read_text())  # noqa: E731
    if mode == "extra":
        jobs = []
        for a in A:
            for rid in A[a]:
                inp = pub[rid]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; T0, G0 = int(inp["tid"]), int(inp["goal_cell"])
                comp = [c for c in tr(a, rid)["cands"] if ST.endpoint_y(c0, T0, G0, [tuple(x) for x in c["seq"]]) and ST.order_valid(c0, T0, G0, [tuple(x) for x in c["seq"]])]
                comp.sort(key=lambda c: (c["C"], len(c["seq"])))
                for c in comp[:5]:
                    jobs.append({"root_id": rid, "seq": c["seq"], "arm": a})
        seen, uniq = set(), []
        for j in jobs:
            k = (j["root_id"], json.dumps(j["seq"]))
            if k not in seen:
                seen.add(k); uniq.append(j)
        (out / "EXTRA_JOBS.jsonl").write_text("".join(json.dumps(j) + "\n" for j in uniq))
        print(json.dumps({"extra_jobs": len(uniq)}))
        return
    VER = {(r["root_id"], json.dumps(r["seq"])): r for r in jl(verify_f)} if Path(verify_f).exists() else {}
    ok = lambda rid, s: bool(VER.get((rid, json.dumps(s))) and VER[(rid, json.dumps(s))]["x"] == 1 and VER[(rid, json.dumps(s))]["y"] == 1)  # noqa: E731
    per, S = [], {"arms": {}, "paired": {}, "by_K": {}}
    for rid in sorted(pv):
        inp = pub[rid]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; T0, G0, K = int(inp["tid"]), int(inp["goal_cell"]), pv[rid]["K"]
        W = [(inp["ids"].index(o), int(d)) for o, d in pv[rid]["witness"]]
        Wo, Wd = {o for o, _ in W}, set(W)
        rec = {"root_id": rid, "K": K, "n_objects": len(c0), "arms": {}}
        for a in A:
            p = A[a][rid]; t = tr(a, rid); s = [tuple(x) for x in p["seq"]]
            cands = t.get("cands", [])
            comp = [c for c in cands if ST.endpoint_y(c0, T0, G0, [tuple(x) for x in c["seq"]]) and ST.order_valid(c0, T0, G0, [tuple(x) for x in c["seq"]])]
            pool_success = any(ok(rid, c["seq"]) for c in comp)
            succ = p["decision"] == "REPAIR" and ok(rid, p["seq"])
            obj_ok = bool(s) and ST.endpoint_y(c0, T0, G0, s)
            ord_ok = bool(s) and ST.order_valid(c0, T0, G0, s)
            cells, dest_live = list(c0), 0
            for i, d in s:
                dest_live += int(bool(ST.place(d, [c for k_, c in enumerate(cells) if k_ != i])))
                cells[i] = d
            subgoal = [0, 0]
            for e in t["log"].get("insert", []):
                if "P" in e:
                    cells = list(c0)
                    for i, d in e["P"] + e.get("p", []) + e["enabling"]:
                        cells[i] = d
                    subgoal[0] += int(ST.feasible(cells, e["before"][0], e["before"][1])); subgoal[1] += 1
            if p["decision"] != "REPAIR":
                fail = p["decision"]
            elif succ:
                fail = "SUCCESS"
            elif not comp:
                fail = "GENERATION (no statically complete candidate in pool)"
            elif pool_success:
                fail = "RANKING (pool held a teacher-verified success)"
            else:
                fail = "RANKING/STATIC (pool held statically complete candidates; none verified among top-5)" if not obj_ok or not ord_ok else \
                       ("EXECUTION X=0" if VER.get((rid, json.dumps(p["seq"])), {}).get("x") != 1 else "FINAL_Y Y=0")
            depth_hist = collections.Counter(str(e.get("depth", 0)) for e in t["log"].get("insert", []))
            tt_calls = sum(1 for L in t["log"].get("local", []) if L["task"].startswith("TT"))
            rec["arms"][a] = {"success": succ, "decision": p["decision"], "seq": p["seq"], "len": len(s), "len_minus_K": len(s) - K, "failure": fail,
                              "object_set_correct": obj_ok, "order_valid": ord_ok, "dest_live_frac": dest_live / max(1, len(s)),
                              "witness_object_overlap": len({o for o, _ in s} & Wo) / max(1, len(Wo)), "witness_action_overlap": len(set(s) & Wd) / max(1, len(Wd)),
                              "pool_size": len(cands), "pool_complete": len(comp), "pool_success": pool_success, "pool_max_len": max([len(c["seq"]) for c in cands] or [0]),
                              "subgoal_success": subgoal, "insertions": len(t["log"].get("insert", [])), "insert_depth": dict(depth_hist), "tt_local_calls": tt_calls,
                              "local": p["budget"]["local"], "ytask": p["budget"]["ytask"], "wall_s": p["budget"]["wall_s"], "stop": p["stop"],
                              "local_scored": (p.get("model_calls") or {}).get("local_scored", 0), "hY": (p.get("energy") or {}).get("hY"),
                              "rounds": p["rounds"], "seeds": t["log"].get("seeds", [])}
        per.append(rec)
    with open(out / "p4_per_scene.jsonl", "w") as f:
        for r in per:
            f.write(json.dumps(r) + "\n")
    Ks = sorted({r["K"] for r in per})
    for a in A:
        rows = [r["arms"][a] for r in per]
        fc = collections.Counter(x["failure"].split(" (")[0] for x in rows)
        S["arms"][a] = {"success": sum(x["success"] for x in rows), "n": len(rows),
                        "by_K": {str(k): f"{sum(r['arms'][a]['success'] for r in per if r['K'] == k)}/{sum(1 for r in per if r['K'] == k)}" for k in Ks},
                        "object_set_correct": sum(x["object_set_correct"] for x in rows), "order_valid": sum(x["order_valid"] for x in rows),
                        "mean_dest_live": sum(x["dest_live_frac"] for x in rows) / len(rows), "mean_witness_object_overlap": sum(x["witness_object_overlap"] for x in rows) / len(rows),
                        "scenes_pool_complete": sum(x["pool_complete"] > 0 for x in rows), "scenes_pool_success": sum(x["pool_success"] for x in rows),
                        "len_ge_K": sum(x["len_minus_K"] >= 0 for x in rows), "mean_len": sum(x["len"] for x in rows) / len(rows),
                        "mean_pool_max_len": sum(x["pool_max_len"] for x in rows) / len(rows), "subgoal_success": [sum(x["subgoal_success"][0] for x in rows), sum(x["subgoal_success"][1] for x in rows)],
                        "mean_local": sum(x["local"] for x in rows) / len(rows), "mean_ytask": sum(x["ytask"] for x in rows) / len(rows),
                        "mean_local_scored": sum(x["local_scored"] for x in rows) / len(rows), "mean_wall_s": sum(x["wall_s"] for x in rows) / len(rows),
                        "mean_insertions": sum(x["insertions"] for x in rows) / len(rows), "failures": dict(fc), "stops": dict(collections.Counter(x["stop"] for x in rows))}
    for a, b in (("R2", "F"), ("R2", "N"), ("R3", "F"), ("R3", "N"), ("R1", "F"), ("R2", "R1"), ("R3", "R2"), ("F", "N")):
        if a in A and b in A:
            S["paired"][f"{a}_vs_{b}"] = mcnemar([r["arms"][a]["success"] for r in per], [r["arms"][b]["success"] for r in per])
    (out / "P4_SUMMARY.json").write_text(json.dumps(S, indent=1))
    for a, v in S["arms"].items():
        print(a, {k: v[k] for k in ("success", "by_K", "object_set_correct", "order_valid", "scenes_pool_complete", "scenes_pool_success", "len_ge_K", "mean_len", "mean_local", "failures", "stops")})
    print(json.dumps(S["paired"]))


if __name__ == "__main__":
    main(*sys.argv[1:8])
