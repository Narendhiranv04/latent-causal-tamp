"""V3.3 fresh-cohort exclusion manifests (label-free): every family template, construction seed, root id, root_sha256 and layout fingerprint
already used by any local generator ledger or any Approach B snapshot.  family = fam-sha256([domain_tag, {8 factors}])[:10] (bd_core.ids).
usage: v33_fresh_exclusions.py OUTDIR SNAPSHOT_DIR... -- LEDGER_SEARCH_ROOT...   -> OUTDIR/EXCL2D.json, EXCL3D.json, EXCL_SUMMARY.json"""
import glob, hashlib, json, os, sys
from pathlib import Path

FACTORS = ["K", "distractors", "source", "displacement", "mechanism", "parking", "distractor_role", "start_pose"]
TAG = {"2d": "2d", "3ds66": "3d"}


def sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def fam(tag, spec):
    return "fam-" + sha([tag, {k: spec[k] for k in FACTORS}])[:10]


def layout_fp(inp):
    return sha([sorted(map(int, inp["cells0"])), int(inp["cells0"][inp["tid"]]), int(inp["goal_cell"])])


def main():
    a = sys.argv[1:]
    out, snaps, roots = Path(a[0]), a[1:a.index("--")], a[a.index("--") + 1:]
    E = {d: {"families": set(), "seeds": set(), "root_ids": set(), "root_sha256": set(), "layout_fp": set(), "namespaces": set()} for d in ("2d", "3d")}
    used_ledgers, fam_check = [], {"2d": [0, 0], "3d": [0, 0]}
    led = {}
    for r in roots:
        for p in glob.glob(f"{r}/**/ledger*.jsonl", recursive=True):
            if "/.claude/" in p:
                continue
            n = 0
            for l in open(p):
                try:
                    v = json.loads(l)
                except json.JSONDecodeError:
                    continue
                rid, spec = v.get("root_id"), v.get("spec")
                if not rid or not isinstance(spec, dict) or rid.split("-")[0] not in TAG or not all(k in spec for k in FACTORS):
                    continue
                tag = rid.split("-")[0]; d = TAG[tag]
                f = fam(tag, spec); led[rid] = f
                E[d]["families"].add(f); E[d]["root_ids"].add(rid); E[d]["namespaces"].add(rid.split("-")[1])
                if v.get("construction_seed") is not None:
                    E[d]["seeds"].add(int(v["construction_seed"]))
                n += 1
            if n:
                used_ledgers.append({"path": p, "rows": n})
    for s in snaps:
        for d in ("2d", "3d"):
            f = Path(s) / f"data{d}.jsonl"
            if not f.exists():
                continue
            for l in open(f):
                r = json.loads(l)
                E[d]["families"].add(r["parent_family_id"]); E[d]["root_ids"].add(r["root_id"]); E[d]["root_sha256"].add(r["root_sha256"])
                E[d]["layout_fp"].add(layout_fp(r["inputs"]))
                if r["root_id"] in led:                                   # the formula reproduces snapshot family ids of original roots
                    fam_check[d][0] += 1; fam_check[d][1] += led[r["root_id"]] == r["parent_family_id"]
    out.mkdir(parents=True, exist_ok=True)
    summ = {"ledgers": used_ledgers, "snapshots": [str(s) for s in snaps], "family_formula_check": {d: {"compared": c[0], "equal": c[1]} for d, c in fam_check.items()}}
    for d in ("2d", "3d"):
        j = {k: sorted(v) for k, v in E[d].items()}
        (out / f"EXCL{d.upper()}.json").write_text(json.dumps(j))
        summ[d] = {k: len(v) for k, v in j.items()} | {"sha256": hashlib.sha256((out / f"EXCL{d.upper()}.json").read_bytes()).hexdigest()}
    (out / "EXCL_SUMMARY.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps({d: summ[d] for d in ("2d", "3d")} | {"family_formula_check": summ["family_formula_check"], "ledgers": len(used_ledgers)}, indent=1))


if __name__ == "__main__":
    main()
