#!/usr/bin/env python3
"""V3.4: VOID re-targets whose triggering evidence was an infrastructure failure (ENRICH_MAX_ROUNDS counted rejections from enrichment stages
that never ran: CODE2D/CODE3D unset on remote hosts).  A re-target is void when, after removing those infrastructure rejections, fewer than
MAX_ROUNDS (4) genuine enrichment rejections exist on its from-template.  The slot reverts to the template it had before the voided re-target(s)
(trailing entries of its history); voided entries move to "retarget_voided" (audit), and their targets become available again.

    v34_retarget_void.py PLAN.json ORIGINAL_PLAN.json VOID.json OUT_PLAN.json OUT_RECORD.json      VOID.json = [[file, slot_id, round, n_genuine]]"""
import json, sys, time
from pathlib import Path

TEMPLATE = ("ref_root_id", "ref_source", "ref_namespace", "spec", "raw_class", "ref_parent_root_id", "ref_parent_family_id",
            "needs_2d_cover_table", "ref_order_strength")


def main(plan_f, orig_f, void_f, out_plan, out_rec):
    P = json.loads(Path(plan_f).read_text())
    O = {s["slot_id"]: s for s in json.loads(Path(orig_f).read_text())["slots"]}
    by_ref = {}
    for s in O.values():
        by_ref.setdefault(s["ref_root_id"], s)
    void = {}
    for _, sid, rnd, n in json.loads(Path(void_f).read_text()):
        if n < 4:
            void.setdefault(sid, set()).add(rnd)
    rec = []
    for s in P["slots"]:
        if s["slot_id"] not in void:
            continue
        hist = s.get("retarget", [])
        while hist and hist[-1]["round"] in void[s["slot_id"]]:
            v = hist.pop()
            s.setdefault("retarget_voided", []).append({**v, "voided_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                                        "reason": "INFRASTRUCTURE_REJECTIONS"})
        src = by_ref[hist[-1]["to_ref"]] if hist else O[s["slot_id"]]
        for f in TEMPLATE:
            s[f] = src[f]
        s["retarget"] = hist
        if not hist:
            s.pop("retarget")
        rec.append({"slot_id": s["slot_id"], "now_ref": s["ref_root_id"], "rounds_left": len(hist), "voided": [v["round"] for v in s["retarget_voided"]]})
    P["retarget_log"] = [r for r in P.get("retarget_log", []) if not (r.get("slot_id") in void and r.get("round") in void[r["slot_id"]] and r.get("to_ref")
                         and r["to_ref"] in {v["to_ref"] for s2 in P["slots"] if s2["slot_id"] == r["slot_id"] for v in s2.get("retarget_voided", [])})]
    P["version"] += "+VOID"
    Path(out_plan).write_text(json.dumps(P, indent=1))
    Path(out_rec).write_text(json.dumps(rec, indent=1))
    for r in rec:
        print(r)


if __name__ == "__main__":
    main(*sys.argv[1:6])
