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


def layout_fp(v):
    return hashlib.sha256(json.dumps([sorted(map(int, v["cells0"])), int(v["cells0"][v["tid"]]), int(v["goal_cell"])],
                                     separators=(",", ":")).encode()).hexdigest()


def assemble(plan_f, collect, out, excl_dirs):
    """collect/<host>/{gen/<run>/{STATUS.json,ledger.jsonl,roots/}, enrich/<e>/SLOT_CHILDREN.json + child roots} -> out/{roots/, PRIVATE_INDEX.jsonl,
    COHORT_MANIFEST.json}.  One root per slot: raw kinds = the first filling run (original run before replacement runs, EXTERNAL placeholders
    ignored); REPARK / HARD = the orchestrator's child.  A re-targeted slot (plan "retarget" history, v34_retarget.py) is filled only by a root whose
    own spec equals the slot's CURRENT template, so late old-template fills from earlier drivers are never used.  Asserts: no root id / seed / root_sha256 / layout fp shared with history or within."""
    import contracts as CT, shutil
    P = json.loads(Path(plan_f).read_text())
    SL = {s["slot_id"]: s for s in P["slots"]}
    collect, out = Path(collect), Path(out)
    (out / "roots").mkdir(parents=True, exist_ok=True)
    path_of, led, cand = {}, {}, collections.defaultdict(list)
    rt_ok = lambda sid, where: True  # noqa: E731  (re-targeted slots are checked on the root's own template below)
    tkey = lambda sp: json.dumps({k: sp[k] for k in FACT}, sort_keys=True)  # noqa: E731  = v34_gen.key
    work = lambda s: (s["domain"], s["kind"], s["ref_namespace"].startswith("conv"))  # noqa: E731  same construction route (RAW / CONV / NONE_*)
    spares = []
    for st in sorted(collect.glob("*/gen/*/STATUS.json"), key=lambda p: (p.parent.name.count("_r"), str(p))):
        run = st.parent
        for l in (open(run / "ledger.jsonl") if (run / "ledger.jsonl").exists() else []):
            e = json.loads(l)
            if e.get("root_id"):
                led[e["root_id"]] = {**e, "_run": str(run)}
                if e.get("accepted") and e.get("v34_slot") in SL and (run / "roots" / f"{e['root_id']}.json").exists():
                    spares.append((e, run))
        for sid, rid in json.loads(st.read_text()).get("filled_map", {}).items():   # 1st choice: the driver's own fill
            if rid != "EXTERNAL" and SL[sid]["kind"] not in ("REPARK", "HARD") and rt_ok(sid, run):
                cand[sid].append(rid); path_of[rid] = run / "roots" / f"{rid}.json"
    for e, run in spares:                                              # then any other accepted, unused root of the same template + class + route
        o = SL[e["v34_slot"]]
        for sid, s in SL.items():
            if s["kind"] not in ("REPARK", "HARD") and work(s) == work(o) and tkey(s["spec"]) == tkey(e["spec"]) and \
                    s["raw_class"] == str(e.get("observed")) and rt_ok(sid, run) and e["root_id"] not in cand[sid]:
                cand[sid].append(e["root_id"]); path_of[e["root_id"]] = run / "roots" / f"{e['root_id']}.json"
    for sc in sorted(collect.glob("*/enrich/*/SLOT_CHILDREN.json")):
        for sid, e in json.loads(sc.read_text()).items():
            if e.get("child") and rt_ok(sid, sc.parent):
                cand[sid].append(e["child"])
                cp = e.get("child_path")                          # host-absolute path -> same path under collect/<host>/enrich/
                path_of[e["child"]] = (sc.parent.parent / cp.split("/enrich/", 1)[1]) if cp and "/enrich/" in cp else sc.parent / "roots" / f"{e['child']}.json"
                led[e["child"]] = {"parent_root_id": e.get("parent"), "strength": e.get("strength"), "_child": True}
    X = {d: json.loads((Path(excl_dirs) / f"EXCL{d.upper()}.json").read_text()) for d in ("2d", "3d")}
    X = {d: {k: set(map(str, v)) for k, v in X[d].items()} for d in X}
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import v34_geomfp as GF                                           # amendment 2026-11-18: geometric layout fp is the disjointness key
    for d in X:
        X[d]["cell_fp"], X[d]["layout_fp"] = X[d]["layout_fp"], set(json.loads((Path(excl_dirs) / f"EXCL{d.upper()}_GEOM.json").read_text())["geom_fp"])
    rows, seen, bad, skipped, regen = [], {"root_id": set(), "seed": set(), "sha": set(), "fp": set()}, collections.Counter(), collections.Counter(), []
    for sid in [k for k in SL if cand.get(k)]:                       # plan order; first candidate passing every disjointness check wins
        s = SL[sid]
        dom = s["domain"]
        for rid in cand[sid]:
            raw = Path(path_of[rid]).read_bytes()
            rec = json.loads(raw)
            h = hashlib.sha256(raw).hexdigest()
            if s.get("retarget") and tkey(rec["spec"]) != tkey(s["spec"]):   # re-targeted slot: only roots of its CURRENT template
                skipped[f"{dom}:old_template"] += 1
                continue
            v = CT.view2d(rec) if dom == "2d" else CT.view3d(rec)
            fp, cfp, seed = GF.geom_fp(v), layout_fp(v), str(rec["ids"]["construction_seed"])
            hit = [f"{k}:{w}" for k, val, xk in (("root_id", rid, "root_ids"), ("seed", seed, "seeds"), ("sha", h, "root_sha256"), ("fp", fp, "layout_fp"))
                   for w, S_ in (("historical", X[dom][xk]), ("within_cohort", seen[k])) if val in S_]
            if not hit:
                break
            skipped.update(f"{dom}:{x}" for x in hit)
        else:
            regen.append(sid)
            continue
        for k, val in (("root_id", rid), ("seed", seed), ("sha", h), ("fp", fp)):
            seen[k].add(val)
        obs = str(rec.get("observed"))
        if obs != s["K"]:
            bad[f"{dom}:class_mismatch"] += 1
        shutil.copyfile(path_of[rid], out / "roots" / f"{rid}.json")
        L = led.get(rid, {})
        parent = L.get("parent_root_id") or rec.get("construction", {}).get("parent_root_id")
        lineage = parent or L.get("v34_v1_root_id") or L.get("v34_dense_root_id") or rid
        rows.append({"root_id": rid, "domain": dom, "K": s["K"], "slot_id": sid, "kind": s["kind"], "ref_root_id": s["ref_root_id"],
                     "path": f"roots/{rid}.json", "root_sha256": h, "layout_fp": fp, "cell_fp": cfp,
                     "cell_fp_historical": cfp in X[dom]["cell_fp"], "construction_seed": int(seed),
                     "template_id": rec["ids"]["parent_family_id"], "parent_family_id": rec["ids"]["parent_family_id"],
                     "instance_lineage_id": lineage, "evaluation_group_id": "grp-" + hashlib.sha256(lineage.encode()).hexdigest()[:12],
                     "source_namespace": rid.split("-")[1] if rid.startswith(("2d-", "3ds66-")) else rid.split("_")[0] + "_" + rid.split("_")[1],
                     "generator": rec.get("generator_version_plus") or L.get("gen"), "config_hash": rec["ids"]["config_hash"],
                     "teacher_version": rec["ids"].get("teacher_version"), "strength": L.get("strength"),
                     "geom": rec.get("geometry_impl", "original") if dom == "2d" else "original", "ids": v["ids"],
                     "masks": {"eval_task": s["K"] in ("1", "2", "3"), "eval_noop": None, "eval_abstain": s["K"] == "NONE"}})
    cc = collections.Counter((r["domain"], r["cell_fp"]) for r in rows)
    for r in rows:                                                     # sensitivity flag: cell-level collision (registered V1 key)
        r["cell_fp_within_cohort"] = cc[(r["domain"], r["cell_fp"])] > 1
        r["cell_fp_collision"] = r["cell_fp_historical"] or r["cell_fp_within_cohort"]
    with open(out / "PRIVATE_INDEX.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    filled = {r["slot_id"] for r in rows}
    missing = sorted(set(SL) - filled)
    man = {"version": "V34_COHORT_V1", "n": len(rows), "by_dom_K": dict(collections.Counter(f"{r['domain']}|{r['K']}" for r in rows)),
           "missing_slots": missing, "n_missing": len(missing), "assertion_failures": dict(bad),
           "skipped_candidates": dict(skipped), "fingerprint": "GEOM_V1 (amendment 2026-11-18); cell-level flag per row",
           "cell_fp_collision_by_dom_K": dict(collections.Counter(f"{r['domain']}|{r['K']}" for r in rows if r["cell_fp_collision"])), "regen_slots": regen, "never_filled": sorted(set(missing) - set(regen)),
           "status": "COMPLETE" if not missing and not bad else "PARTIAL_COHORT" if not bad else "ASSERTION_FAILED",
           "private_index_sha256": hashlib.sha256((out / "PRIVATE_INDEX.jsonl").read_bytes()).hexdigest()}
    (out / "COHORT_MANIFEST.json").write_text(json.dumps(man, indent=1))
    print(json.dumps({k: v for k, v in man.items() if k != "missing_slots"}, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "plan":
        plan(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "assemble":
        assemble(*sys.argv[2:6])
