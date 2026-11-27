#!/usr/bin/env python3
"""R5.3 Addendum A: bounded 2D cVAE recovery (existing TaskCVAE architecture / losses / hyper-parameters; original staged recipe from fresh
initialisation; isolated ABF_ROOT / V3OUT so production and historical checkpoints are untouched; Y frozen and unused here).
  stage 1  placement.fit('2d', q2_2d, 'cvae', 0)                     Q2 placement pretraining, fresh init
  stage 2  placement.fit_task('2d', 'q2init_all', 0) twice:          R-ORIG  = original V2 snapshot repair targets (retraining control)
                                                                     R-LOCAL = original + local verified single-action repairs (TRAIN only)
Local example = (scene, temporary task B -> pB, mover E, destination pE) where B -> pB is CERTIFIED_INFEASIBLE with E present and VERIFIED
(replayed) after the VERIFIED (replayed) relocation E -> pE; analogously (scene, task E -> pE, mover F, destination pF).  Length-1 local repairs
for their own task; never long-repair or witness destinations; R4.3 + R5.1 TRAIN families only.
    ABF_ROOT=<isolated> V3OUT=<isolated> $PYG cvae_rec.py run          -> curves + checkpoints + local-data audit"""
from __future__ import annotations

import collections, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
NW = Path(os.environ.get("R2_NW", "/home/projects/long-horizon/naren_workspace"))
O = NW / "fig3" / "kgt3"


def local_examples(PL, dev):
    """-> tensors in placement.repair_data format + audit."""
    import numpy as np
    import torch
    import contracts as CT
    import search as S
    import views as V
    import xlearn as XLN
    sc = json.loads((PL.ROOT / "data" / "q2_2d" / "scalers.json").read_text())
    mu, sd = np.array(sc["mean"], np.float32), np.array(sc["std"], np.float32)
    F, Mk, Oc, L, Dd, W, rid, audit = [], [], [], [], [], [], [], collections.Counter()
    for src, d, split in (("R4.3", O / "r4" / "b2d", lambda f: "TRAIN"), ("R5.1", O / "r5" / "b2d", XLN.new_split)):
        fam = collections.defaultdict(lambda: collections.defaultdict(list))
        for q in map(json.loads, open(d / "queries.jsonl")):
            if q["kind"] == "PROBE":
                fam[q["fid"]][q["stage"]].append(q)
        for fid, st in fam.items():
            if split(fid) != "TRAIN":
                audit[f"{src}|excluded_VAL"] += 1; continue
            for blk, frees, after, mover, tgt in (("PROBE:B_blocked_by_E", "PROBE:E_free", "PROBE:B_free_after_E", "oE", "oB"),
                                                   ("PROBE:E_blocked_by_F", "PROBE:F_free", "PROBE:E_free_after_F", "oF", "oE")):
                b = [x for x in st.get(blk, []) if x["outcome"] == "CERTIFIED_INFEASIBLE"]
                f = [x for x in st.get(frees, []) if x["outcome"] == "SUCCESS"]
                a = [x for x in st.get(after, []) if x["outcome"] == "SUCCESS"]
                if not (b and f and a):
                    continue
                b, f, a = b[-1], f[-1], a[-1]
                (to, td), = b["seq"]; (mo, md), = f["seq"]
                if to != tgt or mo != mover or a["cells"].get(mover) != md or b["cells"] != f["cells"]:
                    audit[f"{src}|inconsistent"] += 1; continue
                rec = json.loads(Path(f["rec"]).read_text())
                inp = CT.view2d(rec); ix = {n: i for i, n in enumerate(inp["ids"])}
                row = {"root_id": f"{fid}|{mover}", "domain": "2d", "inputs": inp}
                T = V.rebase(row, [], task=(ix[tgt], int(td)))
                root = S.Root(T, "2d")
                cd = {root.ids[i]: c for i, c in enumerate(root.cells0)}
                lg = np.zeros(64, bool); lg[root.legal_dests(root.cells0)] = True
                if not lg[int(md)]:
                    audit[f"{src}|dest_not_legal"] += 1; continue
                o = ix[mover]
                ff, m, occ, _ = PL.scene_features("2d", root.pattr, cd, root.ids[o], root.legal)
                F.append((ff - mu) / sd * m[:, None]); Mk.append(m); L.append(lg); Dd.append(int(md)); W.append(1.0); rid.append(f"{fid}|{mover}")
                Oc.append(np.concatenate([occ, PL.task_features("2d", T["inputs"], root.cells0, o, True)]))
                audit[f"{src}|{mover}_example"] += 1
    Tn = lambda a, dt: torch.as_tensor(np.stack(a), dtype=dt, device=dev)  # noqa: E731
    return {"obj": Tn(F, torch.float32), "mask": Tn(Mk, torch.bool), "occx": Tn(Oc, torch.float32), "legal": Tn(L, torch.bool),
            "dest": torch.as_tensor(Dd, dtype=torch.long, device=dev), "w": torch.as_tensor(np.array(W, np.float32), device=dev), "roots": rid}, dict(audit)


def run():
    import torch
    import placement as PL
    out = Path(os.environ["V3OUT"]); out.mkdir(parents=True, exist_ok=True)
    assert "naren_workspace/fig3/kgt3/r5" in str(PL.ROOT) and "naren_workspace/fig3/kgt3/r5" in str(out), "isolated roots only"
    PL.fit("2d", PL.ROOT / "data" / "q2_2d", "cvae", 0)                    # stage 1 (fresh)
    orig = PL.repair_data
    loc, audit = local_examples(PL, "cuda")
    (out / "local_audit.json").write_text(json.dumps({"audit": audit, "n": int(len(loc["dest"])), "families": len({r.split("|")[0] for r in loc["roots"]})}, indent=1))
    print("LOCAL", json.dumps(audit), len(loc["dest"]), flush=True)
    for stage, add in (("r5rec_orig", False), ("r5rec_local", True)):
        def rd(dom, snap, split, assign, task_on, device="cuda", _add=add):
            d = orig(dom, snap, split, assign, task_on, device)
            if not (_add and split == "train"):
                return d
            w = torch.cat([d["w"], loc["w"]]); w = w / w.mean()
            return {**{k: torch.cat([d[k], loc[k]]) for k in ("obj", "mask", "occx", "legal", "dest")}, "w": w, "roots": d["roots"] + loc["roots"]}
        PL.repair_data = rd
        os.environ["V3_TASK_STAGE"] = stage
        PL.fit_task("2d", "q2init_all", 0)
    PL.repair_data = orig


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
