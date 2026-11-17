"""V3.3 sampler data audit: positive (X=1 AND Y=1, V3-grammar-legal) corrective assignments in the pre-expansion V3 snapshot (S-control) vs the
expanded V3.2 snapshot (S-expanded), holdout byte-identity vs the base snapshot, family/layout leakage, and the exact training examples that
placement.repair_data produces for 'scratch_all' (CPU).  usage: v33_data_audit.py BASE_SNAP CONTROL_SNAP EXPANDED_SNAP OUT_JSON"""
import collections, hashlib, json, os, sys
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contracts as CT  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lines(snap, dom):
    return {json.loads(l)["root_id"]: l for l in open(Path(snap) / f"data{dom}.jsonl")}


def positives(row):
    """-> {assignment key: {"assignment", "orders" (X=1), ...}} grammar-legal Z=1 assignments (= repair_data's targets), and the excluded ones."""
    pa = CT.positive_assignments(row)
    ok = {k: a for k, a in pa.items() if not CT.v3_grammar(row["inputs"], a["assignment"])}
    return ok, {k: CT.v3_grammar(row["inputs"], a["assignment"]) for k, a in pa.items() if k not in ok}


def main():
    base, ctl, exp, out = sys.argv[1:5]
    rep = {"snapshots": {}, "domains": {}}
    for s in (base, ctl, exp):
        lock = json.loads((Path(s) / "data_snapshot.lock.json").read_text())
        rep["snapshots"][Path(s).name] = {n: {"sha256": sha(Path(s) / n), "lock_ok": sha(Path(s) / n) == h} for n, h in lock["files"].items()
                                          if (Path(s) / n).exists()}
    import placement as PL
    for dom in ("2d", "3d"):
        L = {k: lines(s, dom) for k, s in (("base", base), ("control", ctl), ("expanded", exp))}
        R = {k: {r: json.loads(l) for r, l in v.items()} for k, v in L.items()}
        d = {"same_root_sets": len({frozenset(v) for v in L.values()}) == 1,
             "split_counts": dict(collections.Counter(r["split"] for r in R["expanded"].values())),
             "split_changed_vs_base": {k: sum(R[k][r]["split"] != R["base"][r]["split"] for r in R["base"]) for k in ("control", "expanded")},
             "holdout_lines_changed_vs_base": {k: {sp: sum(L[k][r] != L["base"][r] for r in L["base"] if R["base"][r]["split"] == sp) for sp in ("val", "test")}
                                               for k in ("control", "expanded")},
             "train_lines_changed": {"control_vs_base": sum(L["control"][r] != L["base"][r] for r in L["base"] if R["base"][r]["split"] == "train"),
                                     "expanded_vs_control": sum(L["expanded"][r] != L["control"][r] for r in L["base"] if R["base"][r]["split"] == "train")}}
        fam = collections.defaultdict(set); lay = collections.defaultdict(set)
        for r in R["expanded"].values():
            fam[r["parent_family_id"]].add(r["split"]); lay[r["layout_root_id"]].add(r["split"])
        d["families_in_two_splits"] = sum(len(v) > 1 for v in fam.values())
        d["layouts_in_two_splits"] = sum(len(v) > 1 for v in lay.values())
        arms = {}
        P = {}
        for arm in ("control", "expanded"):
            per, excl, orders, acts = {}, collections.Counter(), 0, set()
            for rid, r in R[arm].items():
                if r["split"] != "train":
                    continue
                ok, bad = positives(r)
                for v in bad.values():
                    excl.update(v)
                if ok:
                    per[rid] = ok
                    for k, a in ok.items():
                        orders += len(a["orders"])
                        for o, c in a["assignment"]:
                            acts.add((rid, int(o), int(c)))
                        # every target must have Y = 1 at its endpoint and >= 1 X = 1 order
                        Y = {CT.ekey(y["edit"]): y["y"] for y in r["labels"]["Y"]}
                        assert Y[k] == 1 and any(q["x"] == 1 and CT.ekey(q["seq"]) == k for q in r["labels"]["X"]), (rid, k)
            P[arm] = per
            nA = sum(len(v) for v in per.values())
            arms[arm] = {"train_roots_with_positive": len(per), "unique_assignments": nA, "successful_orders": orders,
                         "orders_per_assignment": round(orders / max(nA, 1), 3), "distinct_root_object_destination_actions": len(acts),
                         "grammar_excluded_rules": dict(excl),
                         "assignments_by_len": dict(collections.Counter(len(a["assignment"]) for v in per.values() for a in v.values())),
                         "roots_by_K_legacy": dict(collections.Counter(R[arm][r]["K_legacy"] for r in per))}
        newA = {(r, k) for r, v in P["expanded"].items() for k in v} - {(r, k) for r, v in P["control"].items() for k in v}
        lost = {(r, k) for r, v in P["control"].items() for k in v} - {(r, k) for r, v in P["expanded"].items() for k in v}
        acts = lambda arm: {(r, int(o), int(c)) for r, v in P[arm].items() for a in v.values() for o, c in a["assignment"]}  # noqa: E731
        newR = set(P["expanded"]) - set(P["control"])
        d["arms"] = arms
        d["new_in_expanded"] = {"unique_assignments": len(newA), "control_assignments_missing_in_expanded": len(lost),
                                "roots_with_new_assignments": len({r for r, _ in newA}), "roots_newly_positive": len(newR),
                                "new_distinct_actions": len(acts("expanded") - acts("control")),
                                "new_assignments_by_len": dict(collections.Counter(len(json.loads(k)) for _, k in newA)),
                                "new_assignments_on_nontrain_roots": sum(R["expanded"][r]["split"] != "train" for r, _ in newA),
                                "newly_positive_roots_by_K_legacy": dict(collections.Counter(R["expanded"][r]["K_legacy"] for r in newR))}
        ex = {}
        for arm, s in (("control", ctl), ("expanded", exp)):
            t = PL.repair_data(dom, s, "train", "all", True, "cpu")
            ex[arm] = {"examples": len(t["dest"]), "roots": len(set(t["roots"])),
                       "targets_sha256": hashlib.sha256(json.dumps(sorted(zip(t["roots"], t["dest"].tolist()))).encode()).hexdigest()}
        v = PL.repair_data(dom, base, "val", "all", True, "cpu")
        ex["val_base"] = {"examples": len(v["dest"]), "roots": len(set(v["roots"]))}
        d["repair_data_scratch_all"] = ex
        rep["domains"][dom] = d
        print(dom, json.dumps({k: d[k] for k in ("holdout_lines_changed_vs_base", "families_in_two_splits", "new_in_expanded", "repair_data_scratch_all")}), flush=True)
    Path(out).write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
