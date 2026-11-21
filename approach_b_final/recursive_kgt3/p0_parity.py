#!/usr/bin/env python3
"""P0: frozen-bundle hash check + full 751-root 2D VAL replay of the frozen K<=3 benchmark WITH the DynPad wrapper active, compared to the
recorded frozen predictions (proposals, decision, moves, p11, p_noop); + 25/27/28-object synthetic input support.
    python p0_parity.py OUT_DIR [--device cuda]"""
import argparse, hashlib, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as DA  # noqa: E402

BUNDLE = Path.home() / "abf_v34/approach_b_bundle"
VAL_IN, VAL_PRED = Path.home() / "abf_v34/parity/public_val_2d.jsonl", Path.home() / "abf_v34/parity/pred_val_2d_gpu.jsonl"


def main(out, device, shard=None, skip_from=None):
    import torch
    import benchmark as BM
    import exhaustive as EX
    import construct as CO
    import search as S
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    man = json.loads((BUNDLE / "MANIFEST.json").read_text())
    hashes = {n: hashlib.sha256((BUNDLE / n).read_bytes()).hexdigest() == h for n, h in man["files"].items()}
    DA.enable_dynpad()
    samp, scor, man = BM.load_bundle(BUNDLE, "2d", device, 0)
    cfg = man["config"]
    ref = {r["root_id"]: r for r in DA.jl(VAL_PRED)}
    mism, dp, dn, t0 = [], 0.0, 0.0, time.time()
    pf = out / "p0_val_pred.jsonl"
    prev = {x["root_id"]: x for x in DA.jl(pf) if "ok" in x} if pf.exists() else {}      # RESUME: rows carrying their parity flags
    pf.write_text("".join(json.dumps(x) + "\n" for x in prev.values()))
    for x in prev.values():
        dp = max(dp, x["dp11"]); dn = max(dn, x["dpnoop"])
        if not all(x["ok"]):
            mism.append({"root": x["root_id"], "decision": x["ok"][0], "moves": x["ok"][1], "proposals": x["ok"][2]})
    with open(pf, "a") as f:
        done_ext = {x["root_id"] for x in DA.jl(skip_from) if "ok" in x} if skip_from and Path(skip_from).exists() else set()
        for k, r in enumerate(DA.jl(VAL_IN)):
            if r["root_id"] in prev or r["root_id"] in done_ext:
                continue
            if shard and k % int(shard.split("/")[1]) != int(shard.split("/")[0]):
                continue
            root = S.Root(r, "2d")
            D6 = EX.proposals(root, samp, cfg["proposal_seed"])
            rec = EX.score_root(root, D6, scor, [cfg["rule"]], cfg["M"], set(), cfg["chunk"])
            d = rec["per_M"][str(cfg["M"])]["decisions"][0]
            kind = "ABSTAIN" if d is None else "NOOP" if d["seq"] == [] else "REPAIR"
            moves = [[root.ids[o], c] for o, c in (d["seq"] if kind == "REPAIR" else [])]
            g = ref[r["root_id"]]
            ok = (kind == g["decision"], moves == [[m["object_id"], m["destination_cell"]] for m in g["moves"]],
                  all({str(o): v[:4] for o, v in D6.items()}.get(k) == v for k, v in g["proposals"].items()))
            p11 = d["p11"] if d else None
            e1, e2 = abs((p11 or 0) - (g["score_p11"] or 0)), abs(rec["p_noop"] - g["p_noop"])
            dp = max(dp, e1); dn = max(dn, e2)
            if not all(ok):
                mism.append({"root": r["root_id"], "decision": ok[0], "moves": ok[1], "proposals": ok[2]})
            f.write(json.dumps({"root_id": r["root_id"], "decision": kind, "moves": moves, "p11": p11, "p_noop": rec["p_noop"], "ok": list(ok),
                                "dp11": e1, "dpnoop": e2}) + "\n"); f.flush()
    if shard:                                          # shard worker: rows only (merged by p0_merge)
        return
    syn = {}
    base = DA.jl(VAL_IN)[0]
    import random, copy
    for nt in (25, 26, 27, 28):
        rr = copy.deepcopy(base); i = rr["inputs"]
        free = [c for c in i["legal_cells"] if c not in set(i["cells0"]) and c != i["goal_cell"]]
        random.Random(f"SYN|{nt}").shuffle(free)
        j = 0
        while len(i["ids"]) < nt:
            c = free[j]; j += 1
            i["ids"].append(f"x{j:02d}"); i["attrs"].append([0.024, 0.0, 1.0, 0.0]); i["cells0"].append(c); i["xy0"].append(list(i["cell_xy"][str(c)]))
        rr["root_id"] += f"~SYN{nt}"
        root = S.Root(rr, "2d")
        D6 = EX.proposals(root, samp, 0)
        legal = set(root.legal_dests(root.cells0))
        sc = scor.score(root, [[]] + [[(o, v[0])] for o, v in list(D6.items())[:8]])
        syn[nt] = {"movers": len(root.movable), "top4_all": all(len(v[:4]) == 4 for v in D6.values()), "legal_all": all(set(v) <= legal for v in D6.values()),
                   "scores_finite": all(abs(x["p11"]) < 2 for x in sc), "K3_count": CO.counts({o: v[:4] for o, v in D6.items()})}
    rep = {"hashes_ok": f"{sum(hashes.values())}/{len(hashes)}", "n": len(ref), "mismatches": len(mism), "mismatch_rows": mism[:20],
           "max_abs_dp11": dp, "max_abs_dpnoop": dn, "device": device, "torch": torch.__version__, "wall_s": round(time.time() - t0, 1),
           "dynpad": "active (identical code path for n<=20)", "synthetic_25_28": syn}
    (out / "P0_PARITY.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "mismatch_rows"}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--device", default="cuda")
    ap.add_argument("--shard"); ap.add_argument("--skip-from")
    a = ap.parse_args(); main(a.out, a.device, a.shard, a.skip_from)
