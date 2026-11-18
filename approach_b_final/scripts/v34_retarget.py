#!/usr/bin/env python3
"""V3.4 registered capped-slot re-target rule (final_protocol.yaml amendment): a CAPPED slot (>= CAP attempts of its template + class
across all hosts' ledgers, none filling it) is re-targeted, in order, to the NEXT reference VAL root of the SAME class and construction kind
in the registered sha256('V34_SLOT|'+root_id) order whose template has not yet been used as a re-target (and is not itself a capped
template); <= 2 re-targets per slot, then MISSING.  No model output is involved; the order is the plan's own reference order.

    v34_retarget.py PLAN.json CAPPED.json OUT_PLAN.json OUT_RECORD.json
CAPPED.json = {slot_id: total_attempts | {"attempts": n, "reason": "ATTEMPT_CAP"|"ENRICH_MAX_ROUNDS"}} (enrichment exhausted = MAX_ROUNDS parents rejected).  OUT_PLAN = PLAN with those slots' template fields replaced (+ "retarget" history)."""
import json, sys, time
from pathlib import Path

CAP = {"2d": 16, "3d": 8}
TEMPLATE = ("ref_root_id", "ref_source", "ref_namespace", "spec", "raw_class", "ref_parent_root_id", "ref_parent_family_id",
            "needs_2d_cover_table", "ref_order_strength")
tkey = lambda s: json.dumps([s["spec"], s["raw_class"]], sort_keys=True)  # noqa: E731


def main(plan_f, capped_f, out_plan, out_rec):
    P = json.loads(Path(plan_f).read_text())
    capped = json.loads(Path(capped_f).read_text())
    S = P["slots"]
    by = {s["slot_id"]: s for s in S}
    order = {}                                           # (dom, K) -> reference slots in registered order (repeat 0 = one per VAL ref)
    for s in S:
        if s["repeat"] == 0:
            order.setdefault((s["domain"], s["K"]), []).append(json.loads(json.dumps(s)))   # frozen copy: re-targets must not alter the order
    capped = {k: (v if isinstance(v, dict) else {"attempts": v, "reason": "ATTEMPT_CAP"}) for k, v in capped.items()}
    bad = {tkey(by[k]) for k in capped} | {json.dumps([r["from_spec"], r["from_raw_class"]], sort_keys=True)
                                           for r in P.get("retarget_log", []) if r.get("from_spec")}   # every capped template so far
    used, rec = {json.dumps([r["to_spec"], r["to_raw_class"]], sort_keys=True) for r in P.get("retarget_log", []) if r.get("to_spec")}, []
    for sid in sorted(capped):
        s = by[sid]
        c = capped[sid]
        assert c["reason"] == "ENRICH_MAX_ROUNDS" or c["attempts"] >= CAP[s["domain"]], (sid, c)
        hist = s.get("retarget", [])
        if len(hist) >= 2:
            rec.append({"slot_id": sid, "status": "MISSING", **c})
            continue
        refs = order[(s["domain"], s["K"])]
        i0 = next(i for i, r in enumerate(refs) if r["ref_root_id"] == s["ref_root_id"])
        tgt = None
        for j in range(1, len(refs) + 1):
            r = refs[(i0 + j) % len(refs)]
            if r["kind"] == s["kind"] and tkey(r) not in used and tkey(r) not in bad:
                tgt = r
                break
        if tgt is None:
            rec.append({"slot_id": sid, "status": "MISSING_NO_TARGET", **c})
            continue
        used.add(tkey(tgt))
        entry = {"round": len(hist) + 1, "from_ref": s["ref_root_id"], "from_spec": s["spec"], "from_raw_class": s["raw_class"],
                 "to_ref": tgt["ref_root_id"], "attempts_before": c["attempts"], "cap_reason": c["reason"], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        for f in TEMPLATE:
            s[f] = tgt[f]
        s["retarget"] = hist + [entry]
        rec.append({"slot_id": sid, "status": "RETARGETED", **entry, "to_spec": tgt["spec"], "to_raw_class": tgt["raw_class"]})
    P["version"] = P["version"] + "+RT"
    P.setdefault("retarget_log", []).extend(rec)
    Path(out_plan).write_text(json.dumps(P, indent=1))
    Path(out_rec).write_text(json.dumps(rec, indent=1))
    for r in rec:
        print(r["slot_id"], r["status"], r.get("to_ref", ""), json.dumps(r.get("to_spec", "")), r.get("to_raw_class", ""))


if __name__ == "__main__":
    main(*sys.argv[1:5])
