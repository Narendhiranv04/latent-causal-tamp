#!/usr/bin/env python3
"""V3.4 Option B fresh cohort: slot plan (VAL-template-matched, independent instances).

    v34_cohort.py plan BASE_SNAP_DIR OUT_JSON      (ABF_ROOT = laptop mirror root; reads VAL rows + their root files, never outcomes of any model)

Each cohort slot replicates ONE reference VAL root's (factor template, observed class, construction kind): K quotas from the registered protocol,
VAL slots of a class taken in sha256('V34_SLOT|' + root_id) order and cycled when the quota exceeds the VAL count.  A slot needs a NEW raw
instance of its template (new name / wave / slot -> new construction seed and root id) whose teacher-observed class equals `raw_class`
(the slot's own class for raw kinds, the parent's class for child kinds), followed for child kinds by the same enrichment construction."""
import collections, hashlib, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
FACT = ("K", "displacement", "distractor_role", "distractors", "mechanism", "parking", "source", "start_pose")
QUOTA = {"2d": {"0": 180, "1": 116, "2": 116, "3": 167, "NONE": 145}, "3d": {"0": 93, "1": 58, "2": 106, "3": 76, "NONE": 63}}
KIND = {"ORIGINAL_SELECTED": "RAW", "PUBLISHED_ORIGINAL": "RAW", "GENERATED_V4_K3": "RAW", "PUBLISHED_RUN_DEPENDENT_K3": "RAW",
        "NEW_DEPENDENCE_SEEKING": "REPARK", "NEW_DEPENDENCE_SEEKING_V1": "REPARK", "NEW_HARD_ORDER": "HARD", "NEW_HARD_ORDER_V3": "HARD",
        "NEW_HARD_ORDER_V4": "HARD"}


def fam(tag, spec):
    import hashlib as h
    blob = json.dumps([tag, {k: spec[k] for k in FACT}], sort_keys=True, separators=(",", ":"))
    return blob


def plan(snap, out):
    import evaluate as EV
    slots, notes = [], collections.Counter()
    for dom in ("2d", "3d"):
        rows = [json.loads(l) for l in open(Path(snap) / f"data{dom}.jsonl")]
        val = [r for r in rows if r["split"] == "val"]
        by = collections.defaultdict(list)
        for r in val:
            by[r["K_legacy"]].append(r)
        for K, q in QUOTA[dom].items():
            ref = sorted(by[K], key=lambda r: hashlib.sha256(("V34_SLOT|" + r["root_id"]).encode()).hexdigest())
            for i in range(q):
                r = ref[i % len(ref)]
                j = json.load(open(EV.path_of(dom.upper(), r)))
                kind = KIND[r["source"]]
                rid = r["root_id"]
                ns = rid.split("-")[1] if rid.startswith(("2d-", "3ds66-")) else rid.split("_")[0]
                if dom == "3d" and K == "NONE" and ns.startswith(("lapN", "srvN")):
                    kind = "NONE_DENSE_TRIM" if ns.endswith("t") else "NONE_DENSE"
                spec = {k: j["spec"][k] for k in FACT}
                if "intent" in j["spec"] and kind == "RAW":
                    spec["intent"] = j["spec"]["intent"]
                raw_class, parent = K, None
                if kind in ("REPARK", "HARD"):
                    parent = j["construction"]["parent_root_id"]
                    pr = next((x for x in rows if x["root_id"] == parent), None)
                    try:
                        pj = json.load(open(EV.path_of(dom.upper(), pr))) if pr else None
                    except Exception:  # noqa: BLE001
                        pj = None
                    if pj is None:                                    # parent not a selected row: read it from the child's recorded store
                        notes[f"{dom}:parent_not_selected"] += 1
                        raw_class = "2" if j.get("construction", {}).get("kind", "").startswith("K2") else "3"
                    else:
                        raw_class = str(pj.get("observed"))
                        assert {k: pj["spec"][k] for k in FACT} == spec, ("parent spec differs", rid)
                exact = dom == "2d" and (K == "NONE" or (spec["K"] >= 2 and spec["mechanism"] in ("grasp", "place", "mixed")) or spec["K"] == 4)
                slots.append({"slot_id": f"{dom}-{K}-{i:03d}", "domain": dom, "K": K, "ref_root_id": rid, "ref_source": r["source"], "ref_namespace": ns,
                              "kind": kind, "spec": spec, "raw_class": raw_class, "ref_parent_root_id": parent,
                              "ref_parent_family_id": j["ids"]["parent_family_id"], "repeat": i // len(ref),
                              "needs_2d_cover_table": exact, "ref_order_strength": r["meta"].get("legacy_strength")})
    c = collections.Counter((s["domain"], s["K"], s["kind"]) for s in slots)
    man = {"version": "V34_SLOT_PLAN_V1", "quota": QUOTA, "n": len(slots), "by_dom_K_kind": {"|".join(k): v for k, v in sorted(c.items())},
           "needs_2d_cover_table": sum(s["needs_2d_cover_table"] for s in slots), "notes": dict(notes), "slots": slots}
    Path(out).write_text(json.dumps(man, indent=1))
    print(json.dumps({k: v for k, v in man.items() if k != "slots"}, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "plan":
        plan(sys.argv[2], sys.argv[3])
