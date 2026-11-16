#!/usr/bin/env python3
"""DISCO-Grid Tree-to-Policy and Tree-to-Value Distillation (`DISCO_plan.md` Sections 6.3, 7, 9, and D4).

Implements the exact distillation principles of Saha et al. (CoRL 2026) adapted to DISCO-Grid:
1. Subtree leaf statistics (`leaf_stats`, matching `disco/data.py:1876-1903`):
   - Recursively counts `(n_success_leaves, n_visited_leaves)` over visited non-failed descendant leaves.
   - Handles `UNRESOLVED` leaves cleanly by returning `(0, 0)` (excluded from decided denominators, never
     falsely treated as physical failures).
2. Policy distillation dataset (`D_pi`):
   - Default (`edges_mode='all_feasible'`): includes EVERY physically executed feasible relocation edge
     in the MCTS trees (plus verified-successful `STOP` edges), not only complete successful plans.
   - Ablation (`edges_mode='successful_only'`): restricts policy supervision to edges with `n_success_leaves > 0`.
3. Value distillation dataset (`D_Q`):
   - Includes every visited feasible relocation child node `v_i` with `n_visited_leaves(v_i) > 0`,
     target `y_i = n_success_leaves(v_i) / n_visited_leaves(v_i)`, weight `w_i = log(1 + n_visited_leaves(v_i))`.
   - Also includes all **decided** `STOP` evaluations (`Z_stop in {0, 1}`, including failed `STOP` attempts
     with `Z_stop = 0`) so the value network learns when `STOP` will fail vs. succeed!
"""
from __future__ import annotations

import collections
import dataclasses
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import data as D
import env as E
import mcts as M
import policy as P


def compute_leaf_stats(nodes: list[M.MCTSNode]) -> dict[int, tuple[int, int]]:
    """Compute `(n_success_leaves, n_decided_visited_leaves)` for every node in `nodes`.
    Matches `disco/data.py:leaf_stats`, while excluding `UNRESOLVED` leaves (`terminal_z is None`)
    from decided denominators (`DISCO_plan.md` Section 7.2).
    """
    node_map = {n.node_id: n for n in nodes}
    stats: dict[int, tuple[int, int]] = {}

    def visit(nid: int) -> tuple[int, int]:
        node = node_map[nid]
        visited_kids = [
            cid
            for cid in node.children_ids
            if node_map[cid].visit_count > 0 and not node_map[cid].is_failed
        ]
        if not visited_kids:
            # This node is a leaf of the visited search tree
            z = E.censor_administrative_stop(node.stop_result).z_outcome if node.stop_result is not None else node.terminal_z
            if z in (0, 1):
                stats[nid] = (int(z == 1), 1)
            else:
                # Unresolved or un-evaluated leaf -> (0, 0) censored, not a false negative
                stats[nid] = (0, 0)
            return stats[nid]

        child_totals = [visit(cid) for cid in visited_kids]
        n_succ = sum(a for a, _ in child_totals)
        n_leaf = sum(b for _, b in child_totals)
        stats[nid] = (n_succ, n_leaf)
        return stats[nid]

    if nodes:
        visit(0)
    return stats


def extract_distillation_data_from_tree(
    nodes: list[M.MCTSNode],
    dom: str,
    scalers: dict[str, Any],
    tree_round: int = 1,
    observation_schema: str = P.O0,
    edges_mode: str = "all_feasible",  # "all_feasible" or "successful_only"
) -> dict[str, Any]:
    """Extract policy rows (`D_pi`) and value rows (`D_Q`) from one MCTS tree (`nodes`)."""
    if edges_mode not in ("all_feasible", "successful_only"):
        raise ValueError("Unknown policy-edge extraction mode")
    dom_l = dom.lower()
    max_o = P.MAXOBJ[dom_l]
    N = P.GRID[dom_l][0] * P.GRID[dom_l][1]
    node_map = {n.node_id: n for n in nodes}
    stats = compute_leaf_stats(nodes)

    policy_dst_rows = []
    policy_obj_rows = []
    value_rows = []

    for parent in nodes:
        if parent.is_stop_node:
            continue
        obs = parent.obs
        if observation_schema == P.O1:
            state = E.RepairEnv.restore(parent.state_blob)
            if state.state_hash() != parent.state_hash or state.prefix != parent.prefix:
                raise ValueError("Physical state/observation lineage mismatch")
            if (state.root_id!=obs.root_id or state.domain!=dom_l or state.cells!=obs.cells
                or state.moved_mask!=obs.moved_mask or state.depth!=parent.depth
                or obs.remaining_steps!=3-state.depth or obs.is_predicted_edit):
                raise ValueError("Executed observation/state identity mismatch")
            obs = dataclasses.replace(obs, q_t_optional=list(state.q_t))
        s_tok, s_mask, s_ctx, s_elig = P.extract_scene_object_tokens(dom_l, obs, scalers, observation_schema)

        stop_result = E.censor_administrative_stop(parent.stop_result) if parent.stop_result is not None else None
        # 1. Decided STOP evaluation at `parent` -> always enters Value dataset (positive OR negative!)
        if parent.stop_evaluated and stop_result is not None and stop_result.status == "DECIDED" and stop_result.z_outcome in (0, 1):
            z_stop = int(stop_result.z_outcome == 1)
            # Repeated selections of a cached STOP are one physical observation.
            n_stop_leaves = 1
            value_rows.append({
                "root_id": parent.obs.root_id,
                "parent_id": parent.node_id,
                "child_id": parent.stop_child_id if parent.stop_child_id is not None else -1,
                "is_stop": True,
                "scene_obj_tok": s_tok,
                "scene_obj_mask": s_mask,
                "scene_ctx": s_ctx,
                "action_obj_idx": max_o,
                "action_dest_idx": N,
                "n_success_leaves": z_stop * n_stop_leaves,
                "n_visited_leaves": n_stop_leaves,
                "value_target": float(z_stop),
                "evidence_weight": float(math.log1p(n_stop_leaves)),
                "tree_round": tree_round,
            })
            # Only verified-positive STOP enters Policy demonstration dataset
            if z_stop == 1:
                policy_obj_rows.append({
                    "root_id": parent.obs.root_id,
                    "parent_id": parent.node_id,
                    "scene_obj_tok": s_tok,
                    "scene_obj_mask": s_mask,
                    "scene_ctx": s_ctx,
                    "elig_mask": s_elig,
                    "target_obj_or_stop": max_o,
                    "is_stop": True,
                    "tree_round": tree_round,
                })

        # 2. Feasible relocation child edges from `parent`
        for cid in parent.children_ids:
            child = node_map[cid]
            if child.is_failed or child.is_stop_node or child.incoming_action is None:
                continue
            act_o, act_d = int(child.incoming_action[0]), int(child.incoming_action[1])
            n_succ, n_leaf = stats.get(cid, (0, 0))

            # Value row: requires visited feasible child with >= 1 decided descendant leaf
            if child.visit_count > 0 and n_leaf > 0:
                y_val = float(n_succ) / float(n_leaf)
                w_val = float(math.log1p(n_leaf))
                value_rows.append({
                    "root_id": parent.obs.root_id,
                    "parent_id": parent.node_id,
                    "child_id": cid,
                    "is_stop": False,
                    "scene_obj_tok": s_tok,
                    "scene_obj_mask": s_mask,
                    "scene_ctx": s_ctx,
                    "action_obj_idx": act_o,
                    "action_dest_idx": act_d,
                    "n_success_leaves": int(n_succ),
                    "n_visited_leaves": int(n_leaf),
                    "value_target": y_val,
                    "evidence_weight": w_val,
                    "tree_round": tree_round,
                })

            # Policy row: all feasible edges (default) vs successful-only edges (ablation)
            include_pol = True if edges_mode == "all_feasible" else (n_succ > 0)
            if include_pol:
                q_f, q_m, q_ot, q_ld = P.extract_query_features(dom_l, obs, act_o, scalers, task_on=True, observation_schema=observation_schema)
                if q_ld[act_d]:
                    policy_dst_rows.append({
                        "root_id": parent.obs.root_id,
                        "parent_id": parent.node_id,
                        "child_id": cid,
                        "obj": q_f,
                        "mask": q_m,
                        "occ_task": q_ot,
                        "legal_dest": q_ld,
                        "target_dest": act_d,
                        "tree_round": tree_round,
                    })
                if s_elig[act_o]:
                    policy_obj_rows.append({
                        "root_id": parent.obs.root_id,
                        "parent_id": parent.node_id,
                        "scene_obj_tok": s_tok,
                        "scene_obj_mask": s_mask,
                        "scene_ctx": s_ctx,
                        "elig_mask": s_elig,
                        "target_obj_or_stop": act_o,
                        "is_stop": False,
                        "tree_round": tree_round,
                    })

    for rows in (policy_dst_rows,policy_obj_rows,value_rows):
        for row in rows:
            row["depth"]=node_map[row["parent_id"]].depth
    return {
        "policy_dst_rows": policy_dst_rows,
        "policy_obj_rows": policy_obj_rows,
        "value_rows": value_rows,
        "leaf_stats": stats,
        "domain":dom_l,
        "observation_schema": observation_schema,
    }


def extract_dataset_from_tree_dirs(
    tree_dirs: list[Path],
    dom: str,
    scalers: dict[str, Any],
    tree_round: int = 1,
    edges_mode: str = "all_feasible",
    observation_schema: str = P.O0,
) -> dict[str, Any]:
    all_dst, all_obj, all_val = [], [], []
    tree_sources=[]
    summaries = []
    # The locked source snapshot supplies authoritative family lineage.
    if len({Path(p).resolve() for p in tree_dirs})!=len(tree_dirs):raise ValueError("Duplicate physical tree evidence")
    snapshot_rows = {r["root_id"]: r for r in D.load_snapshot_rows(dom)}
    groups=D.independence_groups(list(snapshot_rows.values()))
    for td in tree_dirs:
        if not (Path(td) / "nodes.pkl").exists():
            raise FileNotFoundError(f"Missing declared tree: {td}")
        nodes, meta = M.load_saved_tree_nodes(td)
        tree_hash=D.sha256_file(Path(td)/("checkpoint.pkl" if (Path(td)/"checkpoint.pkl").exists() else "nodes.pkl"))
        if tree_hash in tree_sources:raise ValueError("Duplicate physical tree evidence")
        tree_sources.append(tree_hash)
        for node in nodes:
            row = snapshot_rows[node.obs.root_id]
            if row["split"] != "train":
                raise ValueError("Refusing distillation from non-TRAIN physical trees")
        ext = extract_distillation_data_from_tree(nodes, dom, scalers, tree_round=tree_round, edges_mode=edges_mode, observation_schema=observation_schema)
        for key in ("policy_dst_rows","policy_obj_rows","value_rows"):
            for row in ext[key]:
                row["K_legacy"]=snapshot_rows[row["root_id"]]["K_legacy"]
                row["tree_source_sha256"]=D.sha256_file(Path(td)/("checkpoint.pkl" if (Path(td)/"checkpoint.pkl").exists() else "nodes.pkl"))
        all_dst.extend(ext["policy_dst_rows"])
        all_obj.extend(ext["policy_obj_rows"])
        all_val.extend(ext["value_rows"])
        summaries.append(meta["summary"])
    return {
        "domain": dom.lower(),
        "tree_round": tree_round,
        "edges_mode": edges_mode,
        "observation_schema": observation_schema,
        "n_trees": len(summaries),
        "n_trees_with_solution": sum(1 for s in summaries if s.get("found_verified_solution")),
        "total_sim_calls": sum(s.get("total_sim_calls", 0) for s in summaries),
        "policy_dst_rows": all_dst,
        "policy_obj_rows": all_obj,
        "value_rows": all_val,
        "tree_summaries": summaries,
        "tree_sources":tree_sources,
        "root_families": {s["root_id"]:groups[s["root_id"]] for s in summaries},
    }


def distill_policy_and_value(
    dom, extracted, init_policy_ckpt, init_value_ckpt=None, round_name="r1", seed=0,
    epochs=45, batch_size=64, lr=1e-3, device="cuda", out_dir=None,
    checkpoint_rule="train_family_monitor", resume=False, stop_after_epochs=None,
):
    """Distill executed TRAIN evidence; atomic epoch checkpoints resume both optimizers.

    Fixed epochs use all TRAIN and last epoch. The optional family monitor is
    inside TRAIN, never benchmark VAL. Separate VAL execution selects protocols.
    Policy NLL averages over object/STOP rows; relocation destination CE has
    weight n_relocations/n_policy_rows, preserving the joint categorical NLL.
    """
    import copy, hashlib, pickle, random, resource
    if checkpoint_rule not in ("train_family_monitor","fixed_epochs"):
        raise ValueError("Unknown checkpoint rule")
    dom=dom.lower(); schema=extracted.get("observation_schema",P.O0)
    if extracted.get("domain",dom)!=dom: raise ValueError("Mixed-domain data")
    if epochs<=0 or batch_size<=0 or lr<=0: raise ValueError("Invalid training schedule")
    save_dir=Path(out_dir or D.DISCO_ROOT/"runs/distill"/dom/f"{round_name}_s{seed}")
    save_dir.mkdir(parents=True,exist_ok=True)
    if any(save_dir.iterdir()) and not resume: raise FileExistsError(f"Refusing to overwrite {save_dir}")
    if resume and not (save_dir/"trainer.pt").exists(): raise ValueError("Missing authoritative trainer checkpoint")
    config={"domain":dom,"observation_schema":schema,"seed":seed,"round":round_name,
        "policy_sha256":D.sha256_file(init_policy_ckpt),
        "value_sha256":D.sha256_file(init_value_ckpt) if init_value_ckpt else None,
        "dataset_sha256":hashlib.sha256(pickle.dumps(extracted,protocol=4)).hexdigest(),
        "epochs":epochs,"batch_size":batch_size,"lr":lr,"weight_decay":1e-4,
        "scheduler":"none (constant learning rate)","checkpoint_rule":checkpoint_rule,
        "loss_version":"joint_categorical_nll_v2_unique_stop",
        "source_sha256":{p.name:D.sha256_file(p) for p in HERE.glob('*.py')}}
    if resume:
        state=torch.load(save_dir/"trainer.pt",map_location=device,weights_only=False)
        if config!=state["config"]: raise ValueError("Trainer resume configuration/data/source mismatch")
    else:
        (save_dir/"resolved_config.json").write_text(json.dumps(config,indent=2))
        state=None
    torch.manual_seed(seed);np.random.seed(seed);random.seed(seed)
    pol,pck=P.load_policy_checkpoint(init_policy_ckpt,device,observation_schema=schema)
    if pck['domain']!=dom: raise ValueError("Mixed-domain policy checkpoint")
    # Initialize Q in O0 then zero-pad to O1: common initial function for matched q ablation.
    q_rng=torch.get_rng_state()
    torch.manual_seed(seed+777)
    val0=P.DiscoValueNet(dom,h=pck.get('hidden',128),observation_schema=P.O0).to(device)
    if schema==P.O1:
        val=P.DiscoValueNet(dom,h=val0.h,observation_schema=P.O1).to(device)
        P.transfer_o0_weights(val,val0.state_dict())
    else: val=val0
    torch.set_rng_state(q_rng)
    if init_value_ckpt:
        vck=torch.load(init_value_ckpt,map_location=device,weights_only=False)
        if vck['domain']!=dom: raise ValueError("Mixed-domain value checkpoint")
        if vck.get('observation_schema',P.O0)==schema:val.load_state_dict(vck['state_dict'])
        elif vck.get('observation_schema',P.O0)==P.O0 and schema==P.O1:P.transfer_o0_weights(val,vck['state_dict'])
        else:raise ValueError("Incompatible value schema")
    optp=torch.optim.AdamW(pol.parameters(),lr=lr,weight_decay=1e-4)
    optv=torch.optim.AdamW(val.parameters(),lr=lr,weight_decay=1e-4)
    gp=torch.Generator(device=device).manual_seed(seed)
    gv=torch.Generator(device=device).manual_seed(seed+77)
    dst=extracted['policy_dst_rows'];obj=extracted['policy_obj_rows'];vr=extracted['value_rows']
    if not obj and not vr:raise ValueError("Empty physical supervision")
    families=extracted.get('root_families',{})
    roots=sorted({families.get(r['root_id'],r['root_id']) for r in dst+obj+vr})
    rng=np.random.default_rng(seed);rng.shuffle(roots)
    nmon=max(1,len(roots)//6) if len(roots)>=4 and checkpoint_rule=='train_family_monitor' else 0
    monitor=set(roots[:nmon])
    def split(rows):
        if not monitor:return rows,rows
        tr=[r for r in rows if families.get(r['root_id'],r['root_id']) not in monitor]
        va=[r for r in rows if families.get(r['root_id'],r['root_id']) in monitor]
        if rows and (not tr or not va):raise ValueError('Empty family-held-out stream')
        return tr,va
    dt,dv=split(dst);ot,ov=split(obj);vt,vv=split(vr)
    def tensors(rows,kind):
        if not rows:return None
        cols={'dst':('obj','mask','occ_task','legal_dest','target_dest'),
              'obj':('scene_obj_tok','scene_obj_mask','scene_ctx','elig_mask','target_obj_or_stop'),
              'val':('scene_obj_tok','scene_obj_mask','scene_ctx','action_obj_idx','action_dest_idx','value_target','n_visited_leaves')}[kind]
        bools={'mask','legal_dest','scene_obj_mask','elig_mask'}
        ints={'target_dest','target_obj_or_stop','action_obj_idx','action_dest_idx'}
        if kind=='dst' and any(not r['legal_dest'][r['target_dest']] for r in rows):raise ValueError('Masked destination label')
        if kind=='obj' and any(not r['elig_mask'][r['target_obj_or_stop']] for r in rows):raise ValueError('Masked object/STOP label')
        if kind=='val' and any(r['n_visited_leaves']<=0 or not 0<=r['value_target']<=1 for r in rows):raise ValueError('Invalid decided evidence')
        return tuple(torch.as_tensor(np.stack([r[c] for r in rows]),dtype=torch.bool if c in bools else torch.long if c in ints else torch.float32,device=device) for c in cols)
    td,vd=tensors(dt,'dst'),tensors(dv,'dst');to,vo=tensors(ot,'obj'),tensors(ov,'obj');tv,vv_t=tensors(vt,'val'),tensors(vv,'val')
    pc=[];vc=[];bp=bv=math.inf; selected_p=selected_v=None;start_ep=0;cpu_prior=wall_prior=0.
    if state:
        pol.load_state_dict(state['policy']);val.load_state_dict(state['value'])
        pol.obj_trained=state['obj_trained'];optp.load_state_dict(state['optimizer_policy']);optv.load_state_dict(state['optimizer_value'])
        gp.set_state(state['generator_policy'].cpu());gv.set_state(state['generator_value'].cpu())
        torch.set_rng_state(state['torch_rng'].cpu());np.random.set_state(state['numpy_rng']);random.setstate(state['python_rng'])
        if device.startswith('cuda'):torch.cuda.set_rng_state_all(state['cuda_rng'])
        pc=state['policy_curve'];vc=state['value_curve'];bp=state['best_policy_loss'];bv=state['best_value_loss'];start_ep=state['completed_epochs']
        selected_p=state['selected_policy'];selected_v=state['selected_value'];cpu_prior=state['cpu_s'];wall_prior=state['wall_s']
    t0=time.monotonic();c0=time.process_time()
    def payload(model,epoch,metric):
        return copy.deepcopy({'domain':dom,'round':round_name,'seed':seed,'epoch':epoch,'hidden':model.h,'observation_schema':schema,
            'obj_trained':getattr(model,'obj_trained',False),'scalers':pck['scalers'],'state_dict':model.state_dict(),
            'selection_metric':metric,'checkpoint_rule':checkpoint_rule,'dataset_sha256':config['dataset_sha256']})
    def update(loss,opt,model):
        if not torch.isfinite(loss):raise FloatingPointError('Nonfinite distillation loss')
        opt.zero_grad();loss.backward()
        norm=torch.nn.utils.clip_grad_norm_(model.parameters(),float('inf'),error_if_nonfinite=True)
        opt.step();return float(norm)
    # On resume, restore exported selected models from the authoritative epoch.
    if selected_p:P.save_checkpoint(selected_p,save_dir/'policy.pt')
    if selected_v:P.save_checkpoint(selected_v,save_dir/'value.pt')
    for ep in range(start_ep,epochs):
        pol.train();val.train(); dl=[];ol=[];bl=[];pn=vn=None
        if to is not None:
            po=torch.randperm(len(ot),generator=gp,device=device)
            pd=torch.randperm(len(dt),generator=gp,device=device) if td is not None else None
            steps=max(1,math.ceil(max(len(dt),len(ot))/batch_size))
            dst_weight=len(dt)/len(ot)
            for step in range(steps):
                io=po[torch.arange(step*batch_size,(step+1)*batch_size,device=device)%len(ot)]
                lo=pol.obj_loss(*(x[io] for x in to));loss=lo
                if td is not None:
                    ix=pd[torch.arange(step*batch_size,(step+1)*batch_size,device=device)%len(dt)]
                    ld=pol.dst_loss(*(x[ix] for x in td));loss=loss+dst_weight*ld;dl.append(float(ld))
                pn=update(loss,optp,pol);ol.append(float(lo))
            pol.obj_trained=True;pol.eval()
            with torch.no_grad():
                dloss=float(pol.dst_loss(*vd)) if vd is not None else None
                oloss=float(pol.obj_loss(*vo));total=oloss+(len(dv)/len(ov))*dloss if dloss is not None else oloss
                oa=float((pol.forward_obj(*vo[:-1]).argmax(-1)==vo[-1]).float().mean())
                da=float((pol.forward_dst(*vd[:-1]).argmax(-1)==vd[-1]).float().mean()) if vd is not None else None
            pc.append(dict(epoch=ep,train_dst_ce=float(np.mean(dl)) if dl else None,train_obj_ce=float(np.mean(ol)),
                val_dst_ce=dloss,val_obj_ce=oloss,val_total_ce=total,monitor_obj_accuracy=oa,monitor_dst_accuracy=da,gradient_norm=pn))
            if checkpoint_rule=='fixed_epochs' or total<=bp:bp=total;selected_p=payload(pol,ep,total)
        elif selected_p is None:selected_p=payload(pol,ep,None)
        if tv is not None:
            perm=torch.randperm(len(vt),device=device,generator=gv)
            for i in range(0,len(vt),batch_size):
                ix=perm[i:i+batch_size];loss,_=val.weighted_bce_loss(*(x[ix] for x in tv))
                vn=update(loss,optv,val);bl.append(float(loss))
            val.eval()
            with torch.no_grad():_,stats=val.weighted_bce_loss(*vv_t)
            vc.append(dict(epoch=ep,train_weighted_bce=float(np.mean(bl)),val_weighted_bce=stats['weighted_bce'],val_mse=stats['mse'],val_mae=stats['mae'],gradient_norm=vn))
            if checkpoint_rule=='fixed_epochs' or stats['weighted_bce']<=bv:bv=stats['weighted_bce'];selected_v=payload(val,ep,bv)
        checkpoint={'version':1,'config':config,'completed_epochs':ep+1,'policy':pol.state_dict(),'value':val.state_dict(),
            'obj_trained':pol.obj_trained,'optimizer_policy':optp.state_dict(),'optimizer_value':optv.state_dict(),'scheduler':None,
            'generator_policy':gp.get_state(),'generator_value':gv.get_state(),'torch_rng':torch.get_rng_state(),
            'cuda_rng':torch.cuda.get_rng_state_all() if device.startswith('cuda') else None,
            'numpy_rng':np.random.get_state(),'python_rng':random.getstate(),'policy_curve':pc,'value_curve':vc,
            'best_policy_loss':bp,'best_value_loss':bv,'selected_policy':selected_p,'selected_value':selected_v,
            'cpu_s':cpu_prior+time.process_time()-c0,'wall_s':wall_prior+time.monotonic()-t0}
        P.save_checkpoint(checkpoint,save_dir/'trainer.pt')
        if selected_p:P.save_checkpoint(selected_p,save_dir/'policy.pt')
        if selected_v:P.save_checkpoint(selected_v,save_dir/'value.pt')
        P.save_checkpoint(payload(pol,ep,None),save_dir/'last_policy.pt')
        if tv is not None:P.save_checkpoint(payload(val,ep,None),save_dir/'last_value.pt')
        if stop_after_epochs and ep+1>=stop_after_epochs:break
    report={'domain':dom,'round':round_name,'observation_schema':schema,'seed':seed,'edges_mode':extracted.get('edges_mode','all_feasible'),
        'checkpoint_rule':checkpoint_rule,'selection_scope':'fixed TRAIN epochs' if checkpoint_rule=='fixed_epochs' else 'TRAIN family monitor; not benchmark VAL',
        'monitor_families':sorted(monitor),'hyperparameters':config,'n_trees':extracted.get('n_trees',0),'n_trees_with_solution':extracted.get('n_trees_with_solution',0),
        'total_sim_calls':extracted.get('total_sim_calls',0),'n_policy_dst_rows':len(dst),'n_policy_obj_rows':len(obj),'n_value_rows':len(vr),
        'completed_epochs':ep+1 if start_ep<epochs else start_ep,'policy_ckpt':str(save_dir/'policy.pt'),'value_ckpt':str(save_dir/'value.pt') if selected_v else None,
        'wall_s':wall_prior+time.monotonic()-t0,'cpu_s':cpu_prior+time.process_time()-c0,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'policy_curve':pc,'value_curve':vc,'new_physical_calls':0,'value_initialization':'common O0 weights, zero padded for O1',
        'value_row_breakdown':dict(collections.Counter('stop_positive' if r['is_stop'] and r['value_target']==1 else 'stop_negative' if r['is_stop'] else 'reloc_positive_target' if r['value_target']>0 else 'reloc_zero_target' for r in vr))}
    (save_dir/'distill_report.json').write_text(json.dumps(report,indent=2))
    return report


def load_value_checkpoint(ckpt_path: Path | str, device: str = "cuda") -> tuple[P.DiscoValueNet, dict[str, Any]]:
    ck = torch.load(ckpt_path, map_location=device, weights_only=False)
    model = P.DiscoValueNet(ck["domain"], h=ck.get("hidden", 128), observation_schema=ck.get("observation_schema", P.O0)).to(device)
    model.load_state_dict(ck["state_dict"])
    model.eval()
    return model, ck


def merge_extracted_datasets(d_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine extracted policy/value rows across rounds (`r0 + r1`) for cumulative distillation."""
    if not d_list or len({d["domain"] for d in d_list})!=1:raise ValueError("Mixed-domain or empty dataset merge")
    sources=[s for d in d_list for s in d.get("tree_sources",[])]
    if len(sources)!=len(set(sources)):raise ValueError("Repeated physical tree evidence across streams")
    schemas = {d.get("observation_schema", P.O0) for d in d_list}
    if len(schemas) != 1:
        raise ValueError("Cannot merge mixed observation schemas")
    dst_all, obj_all, val_all, sum_all = [], [], [], []
    for d in d_list:
        dst_all.extend(d["policy_dst_rows"])
        obj_all.extend(d["policy_obj_rows"])
        val_all.extend(d["value_rows"])
        sum_all.extend(d.get("tree_summaries", []))
    return {
        "domain": d_list[0]["domain"],
        "observation_schema": next(iter(schemas)),
        "tree_round": d_list[-1]["tree_round"],
        "edges_mode": d_list[-1]["edges_mode"],
        "n_trees": len(sum_all),
        "n_trees_with_solution": sum(1 for s in sum_all if s.get("found_verified_solution")),
        "total_sim_calls": sum(s.get("total_sim_calls", 0) for s in sum_all),
        "policy_dst_rows": dst_all,
        "policy_obj_rows": obj_all,
        "value_rows": val_all,
        "tree_summaries": sum_all,
        "tree_sources":sources,
        "root_families": {k:v for d in d_list for k,v in d.get("root_families", {}).items()},
    }


def run_d3_d4_d5_pipeline(seeds: tuple[int, ...] = (0, 1, 2), device: str = "cuda") -> dict[str, Any]:
    """Execute Milestones D3 (MCTS search + PW/Uniform/Reward ablations),
    D4 (Round 1 distillation: all_feasible vs successful_only), and
    D5 (Round 2 fresh-tree MCTS with P1+Q1 and Round 2 distillation P2/Q2_value).
    """
    out_summary: dict[str, Any] = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "domains": {},
    }

    for dom in ("2d", "3d"):
        q2 = D.load_q2_dataset(dom)
        scalers = q2["scalers"]
        p0_ckpt_s0 = D.DISCO_ROOT / "runs/p0" / dom / "s0/model.pt"

        if dom == "2d":
            main_counts = {"0": 4, "1": 7, "2": 6, "3": 4, "NONE": 3}  # 24 roots
            abl_counts = {"0": 2, "1": 4, "2": 3, "3": 2, "NONE": 1}   # 12 subset roots
            iters, B_exp, max_sim, workers = 8, 4, 14, 16
        else:
            main_counts = {"0": 2, "1": 4, "2": 3, "3": 2, "NONE": 1}  # 12 roots
            abl_counts = {"0": 1, "1": 2, "2": 2, "3": 1, "NONE": 0}   # 6 subset roots
            iters, B_exp, max_sim, workers = 5, 3, 8, 12

        main_cohort = M.select_mcts_train_cohort(dom, counts_by_k=main_counts, seed=0)
        abl_cohort = M.select_mcts_train_cohort(dom, counts_by_k=abl_counts, seed=0)
        abl_root_ids = {r["root_id"] for r in abl_cohort}

        trees_root = D.DISCO_ROOT / "trees" / dom

        # 1. D3 Primary Round 0 MCTS Search (P0 + PW + Geometric Progress)
        r0_main = M.run_mcts_cohort_parallel(
            dom=dom,
            cohort=main_cohort,
            out_trees_dir=trees_root / "r0_p0_pw_geom",
            scalers=scalers,
            policy_ckpt=p0_ckpt_s0,
            value_ckpt=None,
            proposal_mode="p0",
            iterations=iters,
            expansion_budget_B=B_exp,
            max_sim_calls=max_sim,
            use_progressive_widening=True,
            reward_mode="geometric",
            seed=0,
            workers=workers,
        )

        # 2. D3 Controlled MCTS Ablations on matched `abl_cohort`
        r0_uniform = M.run_mcts_cohort_parallel(
            dom=dom,
            cohort=abl_cohort,
            out_trees_dir=trees_root / "r0_uniform_pw_geom",
            scalers=scalers,
            policy_ckpt=None,
            value_ckpt=None,
            proposal_mode="uniform",
            iterations=iters,
            expansion_budget_B=B_exp,
            max_sim_calls=max_sim,
            use_progressive_widening=True,
            reward_mode="geometric",
            seed=0,
            workers=workers,
        )
        r0_nopw = M.run_mcts_cohort_parallel(
            dom=dom,
            cohort=abl_cohort,
            out_trees_dir=trees_root / "r0_p0_nopw_geom",
            scalers=scalers,
            policy_ckpt=p0_ckpt_s0,
            value_ckpt=None,
            proposal_mode="p0",
            iterations=iters,
            expansion_budget_B=B_exp,
            max_sim_calls=max_sim,
            use_progressive_widening=False,
            reward_mode="geometric",
            seed=0,
            workers=workers,
        )
        r0_sparse = M.run_mcts_cohort_parallel(
            dom=dom,
            cohort=abl_cohort,
            out_trees_dir=trees_root / "r0_p0_pw_sparse",
            scalers=scalers,
            policy_ckpt=p0_ckpt_s0,
            value_ckpt=None,
            proposal_mode="p0",
            iterations=iters,
            expansion_budget_B=B_exp,
            max_sim_calls=max_sim,
            use_progressive_widening=True,
            reward_mode="sparse",
            seed=0,
            workers=workers,
        )

        # Compute matched-cohort metrics for r0_main on abl_root_ids for direct paired comparison
        r0_main_abl_sub = [s for s in r0_main["summaries"] if s["root_id"] in abl_root_ids and s.get("K_legacy") in ("1", "2", "3")]
        r0_main_matched_rate = round(
            sum(1 for s in r0_main_abl_sub if s["found_verified_solution"]) / max(1, len(r0_main_abl_sub)), 4
        )

        # 3. D4 Distillation Round 1 (P0 -> P1, Q1) + Successful-Only Edges Ablation
        r0_tree_dirs = [Path(p) for p in r0_main["tree_dirs"]]
        ext_r0_all = extract_dataset_from_tree_dirs(r0_tree_dirs, dom, scalers, tree_round=1, edges_mode="all_feasible")
        ext_r0_succ = extract_dataset_from_tree_dirs(r0_tree_dirs, dom, scalers, tree_round=1, edges_mode="successful_only")

        r1_distill_runs = []
        for s in seeds:
            p0_ck_s = D.DISCO_ROOT / "runs/p0" / dom / f"s{s}/model.pt"
            d_rep = distill_policy_and_value(
                dom=dom,
                extracted=ext_r0_all,
                init_policy_ckpt=p0_ck_s,
                init_value_ckpt=None,
                round_name="r1",
                seed=s,
                epochs=45,
                batch_size=64,
                lr=1e-3,
                device=device,
            )
            r1_distill_runs.append(d_rep)

        # Successful-only policy edges ablation (seed 0)
        r1_succ_only_s0 = distill_policy_and_value(
            dom=dom,
            extracted=ext_r0_succ,
            init_policy_ckpt=p0_ckpt_s0,
            init_value_ckpt=None,
            round_name="r1_succ_only",
            seed=0,
            epochs=45,
            batch_size=64,
            lr=1e-3,
            device=device,
        )

        # 4. D5 Iterative Round 1 MCTS Search on FRESH trees using frozen P1 + Q1
        p1_ckpt_s0 = r1_distill_runs[0]["policy_ckpt"]
        q1_ckpt_s0 = r1_distill_runs[0]["value_ckpt"]
        r1_main = M.run_mcts_cohort_parallel(
            dom=dom,
            cohort=main_cohort,
            out_trees_dir=trees_root / "r1_p1q1_pw_geom",
            scalers=scalers,
            policy_ckpt=p1_ckpt_s0,
            value_ckpt=q1_ckpt_s0,
            proposal_mode="distilled",
            iterations=iters,
            expansion_budget_B=B_exp,
            max_sim_calls=max_sim,
            use_progressive_widening=True,
            reward_mode="geometric",
            seed=100,
            workers=workers,
        )

        # 5. D5 Round 2 Distillation (P1/Q1 -> P2, Q2_value) over cumulative trees (r0 + r1)
        r1_tree_dirs = [Path(p) for p in r1_main["tree_dirs"]]
        ext_r1_all = extract_dataset_from_tree_dirs(r1_tree_dirs, dom, scalers, tree_round=2, edges_mode="all_feasible")
        ext_cum_r2 = merge_extracted_datasets([ext_r0_all, ext_r1_all])

        r2_distill_runs = []
        for i_s, s in enumerate(seeds):
            p1_ck_s = r1_distill_runs[i_s]["policy_ckpt"]
            q1_ck_s = r1_distill_runs[i_s]["value_ckpt"]
            d2_rep = distill_policy_and_value(
                dom=dom,
                extracted=ext_cum_r2,
                init_policy_ckpt=p1_ck_s,
                init_value_ckpt=q1_ck_s,
                round_name="r2",
                seed=s,
                epochs=45,
                batch_size=64,
                lr=1e-3,
                device=device,
            )
            r2_distill_runs.append(d2_rep)

        # Find a representative solved tree in r1_main for visualization
        solved_r1 = next((s for s in r1_main["summaries"] if s["found_verified_solution"] and s.get("K_legacy") in ("2", "3", "1")), r1_main["summaries"][0])
        sample_tree_meta = json.loads((trees_root / "r1_p1q1_pw_geom" / solved_r1["root_id"] / "tree.json").read_text())

        out_summary["domains"][dom] = {
            "mcts_round0_p0": {k: v for k, v in r0_main.items() if k != "tree_dirs"},
            "mcts_round1_p1q1": {k: v for k, v in r1_main.items() if k != "tree_dirs"},
            "mcts_ablations_matched_subset": {
                "n_subset_roots": len(abl_cohort),
                "p0_pw_geom_solve_rate": r0_main_matched_rate,
                "uniform_pw_geom": {k: v for k, v in r0_uniform.items() if k not in ("tree_dirs", "summaries")},
                "p0_nopw_geom": {k: v for k, v in r0_nopw.items() if k not in ("tree_dirs", "summaries")},
                "p0_pw_sparse": {k: v for k, v in r0_sparse.items() if k not in ("tree_dirs", "summaries")},
            },
            "distill_round1": r1_distill_runs,
            "distill_round1_succ_only_s0": r1_succ_only_s0,
            "distill_round2": r2_distill_runs,
            "value_target_hist_r2": [round(float(r["value_target"]), 4) for r in ext_cum_r2["value_rows"]],
            "value_weight_hist_r2": [round(float(r["evidence_weight"]), 4) for r in ext_cum_r2["value_rows"]],
            "sample_tree": sample_tree_meta,
        }

    out_path = HERE / "reports/d3_d4_d5_mcts_distill_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_summary, indent=2))
    return out_summary


if __name__ == "__main__":
    if sys.argv[1:2] == ["run_d3_d4_d5"]:
        res = run_d3_d4_d5_pipeline()
        print(json.dumps({"d3_d4_d5_done": list(res["domains"].keys())}))
