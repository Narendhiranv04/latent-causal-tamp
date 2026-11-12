#!/usr/bin/env python3
"""Work lists for the locally generated K3 layouts (published generator, namespaces lap4 / lap5 / srv5): every ledger line after the
4,071 copied published lines whose verified class is K3 (accepted 'observed' 3, or DEPENDENT with verified_K 3).  legacy: all 6 orders of
the teacher's minimal assignment in a fresh env; fixed: the published no-fixed-object rule.  Writes work/gen_legacy_items.json and
work/gen_fixed_items.json (resumable by key; re-run as generation continues)."""
import itertools, json
from pathlib import Path
V4 = Path(__file__).resolve().parent.parent
leg, fix = [], []
for g in ("gen_k3", "gen_k3b", "gen_k3g"):
    lp = V4 / g / "raw/ledger.jsonl"
    if not lp.exists():
        continue
    for r in [json.loads(l) for l in open(lp)][4071:]:
        if not (r.get("observed") == "3" or (r.get("observed") == "DEPENDENT" and r.get("verified_K") == 3)):
            continue
        p = V4 / g / "raw/roots" / f"{r['root_id']}.json"
        if not p.exists():
            continue
        rec = json.loads(p.read_text())
        mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
        assert len(mini["sequence"]) == 3
        leg.append({"key": f"G_{r['root_id']}", "path": str(p), "origin": "GENERATED_V4_K3", "observed": r["observed"],
                    "orders": [list(map(list, q)) for q in itertools.permutations([[o, list(d)] for o, d in mini["sequence"]])]})
        fix.append({"key": f"GF_{r['root_id']}", "path": str(p)})
(V4 / "work/gen_legacy_items.json").write_text(json.dumps(leg)); (V4 / "work/gen_fixed_items.json").write_text(json.dumps(fix))
print("generated K3 roots", len(leg))
