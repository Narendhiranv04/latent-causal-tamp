#!/usr/bin/env python3
"""Matched round-1 controls on identical immutable TRAIN trees and initializations.

CPU, one thread on gvlab. Fixed historical hyperparameters, no TEST queries or
checkpoint selection on TEST. O1 is trained from actually executed saved states;
this driver does not establish closed-loop task performance.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import data as D
import distill as DS
import policy as P
from collect import require_headroom


def run(dom, out, epochs=45, seeds=(0,1,2)):
    require_headroom()
    os.nice(10)
    import torch
    torch.set_num_threads(1)
    out.mkdir(parents=True,exist_ok=False)
    trees=sorted((D.DISCO_ROOT/"trees"/dom/"r0_p0_pw_geom").glob("*/tree.json"))
    if not trees: raise ValueError("Missing frozen source trees")
    manifest={"domain":dom,"trees":[{"path":str(t.parent),"tree_sha256":D.sha256_file(t),
                  "nodes_sha256":D.sha256_file(t.parent/"nodes.pkl")} for t in trees],
              "seeds":list(seeds),"epochs":epochs,"batch_size":64,"lr":.001,
              "round":1,"new_physical_calls":0,"max_workers":1,"threads":1,"device":"cpu",
              "arms":["o0_all_feasible","o0_successful_only","o1_all_feasible"],
              "source_sha256":{p.name:D.sha256_file(p) for p in HERE.glob("*.py")},
              "claim_scope":"pilot-tree representation/distillation controls; task evaluation pending"}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2))
    reports=[];start=time.time()
    for schema,mode in [(P.O0,"all_feasible"),(P.O0,"successful_only"),(P.O1,"all_feasible")]:
        scalers=json.loads((D.ABF_ROOT/f"data/q2_{dom}/scalers.json").read_text())
        extracted=DS.extract_dataset_from_tree_dirs([t.parent for t in trees],dom,scalers,
                                                    tree_round=1,edges_mode=mode,observation_schema=schema)
        for seed in seeds:
            require_headroom()
            rep=DS.distill_policy_and_value(dom,extracted,D.DISCO_ROOT/f"runs/p0/{dom}/s{seed}/model.pt",
                    round_name="validation_r1",seed=seed,epochs=epochs,batch_size=64,lr=.001,
                    device="cpu",out_dir=out/f"{schema}_{mode}_s{seed}",checkpoint_rule="fixed_epochs")
            rep.update(policy_sha256=D.sha256_file(rep["policy_ckpt"]),value_sha256=D.sha256_file(rep["value_ckpt"]))
            reports.append(rep)
            (out/"results.json").write_text(json.dumps({"runs":reports,"wall_s":time.time()-start},indent=2))
            print(dom,schema,mode,seed,rep["wall_s"],flush=True)
    return reports


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--domain",required=True,choices=["2d","3d"])
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--epochs",type=int,default=45)
    a=p.parse_args()
    if not a.out.resolve().is_relative_to((D.DISCO_ROOT/"validation_v2").resolve()):
        p.error("Output must be inside DISCO_ROOT/validation_v2")
    run(a.domain,a.out,a.epochs)
