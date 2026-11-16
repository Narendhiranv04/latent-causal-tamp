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

    return {
        "policy_dst_rows": policy_dst_rows,
        "policy_obj_rows": policy_obj_rows,
        "value_rows": value_rows,
        "leaf_stats": stats,
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
    summaries = []
    # The locked source snapshot supplies authoritative family lineage.
    snapshot_rows = {r["root_id"]: r for r in D.load_snapshot_rows(dom)}
    for td in tree_dirs:
        if not (Path(td) / "nodes.pkl").exists():
            continue
        nodes, meta = M.load_saved_tree_nodes(td)
        for node in nodes:
            row = snapshot_rows[node.obs.root_id]
            if row["split"] != "train":
                raise ValueError("Refusing distillation from non-TRAIN physical trees")
        ext = extract_distillation_data_from_tree(nodes, dom, scalers, tree_round=tree_round, edges_mode=edges_mode, observation_schema=observation_schema)
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
        "root_families": {s["root_id"]:D.root_family_key(snapshot_rows[s["root_id"]]) for s in summaries},
    }


def distill_policy_and_value(
    dom: str,
    extracted: dict[str, Any],
    init_policy_ckpt: Path | str,
    init_value_ckpt: Path | str | None = None,
    round_name: str = "r1",
    seed: int = 0,
    epochs: int = 45,
    batch_size: int = 64,
    lr: float = 1e-3,
    device: str = "cuda",
    out_dir: Path | None = None,
    checkpoint_rule: str = "train_family_monitor",
) -> dict[str, Any]:
    """Train distilled Policy (`P_r`) and Value (`Q_r`) networks from extracted MCTS tree datasets."""
    if checkpoint_rule not in ("train_family_monitor", "fixed_epochs"):
        raise ValueError("Unknown checkpoint rule")
    dom_l = dom.lower()
    torch.manual_seed(seed)
    np.random.seed(seed)

    save_dir = Path(out_dir or (D.DISCO_ROOT / "runs/distill" / dom_l / f"{round_name}_s{seed}"))
    save_dir.mkdir(parents=True, exist_ok=True)
    if any(save_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite distillation run: {save_dir}")

    schema = extracted.get("observation_schema", P.O0)
    pol_model, p_ck = P.load_policy_checkpoint(init_policy_ckpt, device=device, observation_schema=schema)
    scalers = p_ck["scalers"]
    pol_model.train()
    (save_dir / "resolved_config.json").write_text(json.dumps({
        "domain":dom_l, "observation_schema":schema, "seed":seed, "round":round_name,
        "policy_initialization":str(init_policy_ckpt), "policy_sha256":D.sha256_file(init_policy_ckpt),
        "value_initialization":str(init_value_ckpt) if init_value_ckpt else None,
        "value_sha256":D.sha256_file(init_value_ckpt) if init_value_ckpt else None,
        "epochs":epochs, "batch_size":batch_size, "lr":lr, "weight_decay":1e-4,
        "edges_mode":extracted.get("edges_mode"), "tree_summaries":extracted.get("tree_summaries", []),
        "checkpoint_rule":checkpoint_rule,
        "selection_scope":"fixed epochs or TRAIN-pool monitor, not independent validation",
        "source_sha256":{p.name:D.sha256_file(p) for p in HERE.glob("*.py")},
    },indent=2))

    val_model = P.DiscoValueNet(dom_l, h=p_ck.get("hidden", 128), observation_schema=schema).to(device)
    if init_value_ckpt is not None and Path(init_value_ckpt).exists():
        v_ck = torch.load(init_value_ckpt, map_location=device, weights_only=False)
        if v_ck.get("observation_schema", P.O0) == schema:
            val_model.load_state_dict(v_ck["state_dict"])
        elif v_ck.get("observation_schema", P.O0) == P.O0 and schema == P.O1:
            P.transfer_o0_weights(val_model, v_ck["state_dict"])
        else:
            raise ValueError("Incompatible value initialization schema")
    val_model.train()

    dst_rows = extracted["policy_dst_rows"]
    obj_rows = extracted["policy_obj_rows"]
    val_rows = extracted["value_rows"]

    # This is a TRAIN-pool monitor, not independent benchmark VALIDATION.
    # Families stay together, including alternate roots from the same source.
    # Frozen P0 may already have seen Q2 placements from these TRAIN families.
    # Therefore this loss is never reported as held-out task generalization.
    root_families = extracted.get("root_families", {})
    all_roots = sorted({root_families.get(r["root_id"], r["root_id"]) for r in (dst_rows + obj_rows + val_rows)})
    rng = np.random.default_rng(seed)
    rng.shuffle(all_roots)
    n_val_r = max(1, len(all_roots) // 6) if len(all_roots) >= 4 and checkpoint_rule == "train_family_monitor" else 0
    val_root_set = set(all_roots[:n_val_r])

    def split_rows(rows):
        if not val_root_set:
            return rows, rows
        tr = [r for r in rows if root_families.get(r["root_id"], r["root_id"]) not in val_root_set]
        va = [r for r in rows if root_families.get(r["root_id"], r["root_id"]) in val_root_set]
        if not tr or not va:
            raise ValueError("Empty family-held-out stream; use a larger TRAIN cohort instead of leaking rows")
        return tr, va

    dst_tr, dst_va = split_rows(dst_rows)
    obj_tr, obj_va = split_rows(obj_rows)
    val_tr, val_va = split_rows(val_rows)

    t0 = time.time()
    pol_curve = []
    val_curve = []

    # 1. Train Policy Network (both destination head and object/STOP head)
    if dst_tr and obj_tr:
        opt_p = torch.optim.AdamW(pol_model.parameters(), lr=lr, weight_decay=1e-4)
        best_p_loss = math.inf

        def tensorize_dst(rows):
            return (
                torch.as_tensor(np.stack([r["obj"] for r in rows]), dtype=torch.float32, device=device),
                torch.as_tensor(np.stack([r["mask"] for r in rows]), dtype=torch.bool, device=device),
                torch.as_tensor(np.stack([r["occ_task"] for r in rows]), dtype=torch.float32, device=device),
                torch.as_tensor(np.stack([r["legal_dest"] for r in rows]), dtype=torch.bool, device=device),
                torch.as_tensor([r["target_dest"] for r in rows], dtype=torch.long, device=device),
            )

        def tensorize_obj(rows):
            return (
                torch.as_tensor(np.stack([r["scene_obj_tok"] for r in rows]), dtype=torch.float32, device=device),
                torch.as_tensor(np.stack([r["scene_obj_mask"] for r in rows]), dtype=torch.bool, device=device),
                torch.as_tensor(np.stack([r["scene_ctx"] for r in rows]), dtype=torch.float32, device=device),
                torch.as_tensor(np.stack([r["elig_mask"] for r in rows]), dtype=torch.bool, device=device),
                torch.as_tensor([r["target_obj_or_stop"] for r in rows], dtype=torch.long, device=device),
            )

        td_tr, td_va = tensorize_dst(dst_tr), tensorize_dst(dst_va)
        to_tr, to_va = tensorize_obj(obj_tr), tensorize_obj(obj_va)
        gen = torch.Generator(device=device).manual_seed(seed)

        for ep in range(epochs):
            pol_model.train()
            p_dst = torch.randperm(len(dst_tr), device=device, generator=gen)
            p_obj = torch.randperm(len(obj_tr), device=device, generator=gen)
            ep_dst_l, ep_obj_l = [], []
            n_steps = max(1, max(len(dst_tr), len(obj_tr)) // batch_size + 1)
            for s_i in range(n_steps):
                # Cycle the smaller stream without empty/wrapped slices.
                ix_d = p_dst[torch.arange(s_i * batch_size, (s_i + 1) * batch_size, device=device) % len(dst_tr)]
                ix_o = p_obj[torch.arange(s_i * batch_size, (s_i + 1) * batch_size, device=device) % len(obj_tr)]
                ld = pol_model.dst_loss(*(x[ix_d] for x in td_tr))
                lo = pol_model.obj_loss(*(x[ix_o] for x in to_tr))
                loss = ld + lo
                opt_p.zero_grad()
                loss.backward()
                opt_p.step()
                ep_dst_l.append(float(ld.item()))
                ep_obj_l.append(float(lo.item()))

            pol_model.eval()
            with torch.no_grad():
                vd = float(pol_model.dst_loss(*td_va).item())
                vo = float(pol_model.obj_loss(*to_va).item())
                vtot = vd + vo
            pol_curve.append({
                "epoch": ep,
                "train_dst_ce": float(np.mean(ep_dst_l)),
                "train_obj_ce": float(np.mean(ep_obj_l)),
                "val_dst_ce": vd,
                "val_obj_ce": vo,
                "val_total_ce": vtot,
            })
            if checkpoint_rule == "fixed_epochs" or vtot <= best_p_loss:
                best_p_loss = vtot
                pol_model.obj_trained = True
                P.save_checkpoint(
                    {
                        "domain": dom_l,
                        "round": round_name,
                        "seed": seed,
                        "epoch": ep,
                        "best_val_ce": vtot,
                        "hidden": pol_model.h,
                        "observation_schema": schema,
                        "obj_trained": True,
                        "scalers": scalers,
                        "state_dict": pol_model.state_dict(),
                    },
                    save_dir / "policy.pt",
                )
    else:
        # Preserve previous policy checkpoint if no feasible edges were extracted
        P.save_checkpoint(p_ck, save_dir / "policy.pt")

    # 2. Train Value Network (weighted BCE over visited leaf fractions + decided STOP outcomes)
    if val_tr:
        opt_v = torch.optim.AdamW(val_model.parameters(), lr=lr, weight_decay=1e-4)
        best_v_loss = math.inf

        def tensorize_val(rows):
            return (
                torch.as_tensor(np.stack([r["scene_obj_tok"] for r in rows]), dtype=torch.float32, device=device),
                torch.as_tensor(np.stack([r["scene_obj_mask"] for r in rows]), dtype=torch.bool, device=device),
                torch.as_tensor(np.stack([r["scene_ctx"] for r in rows]), dtype=torch.float32, device=device),
                torch.as_tensor([r["action_obj_idx"] for r in rows], dtype=torch.long, device=device),
                torch.as_tensor([r["action_dest_idx"] for r in rows], dtype=torch.long, device=device),
                torch.as_tensor([r["value_target"] for r in rows], dtype=torch.float32, device=device),
                torch.as_tensor([r["n_visited_leaves"] for r in rows], dtype=torch.float32, device=device),
            )

        tv_tr, tv_va = tensorize_val(val_tr), tensorize_val(val_va)
        gen_v = torch.Generator(device=device).manual_seed(seed + 77)

        for ep in range(epochs):
            val_model.train()
            perm = torch.randperm(len(val_tr), device=device, generator=gen_v)
            tr_bce = []
            for i in range(0, len(perm), batch_size):
                ix = perm[i : i + batch_size]
                l_v, _ = val_model.weighted_bce_loss(*(x[ix] for x in tv_tr))
                opt_v.zero_grad()
                l_v.backward()
                opt_v.step()
                tr_bce.append(float(l_v.item()))

            val_model.eval()
            with torch.no_grad():
                v_loss, v_stats = val_model.weighted_bce_loss(*tv_va)
            val_curve.append({
                "epoch": ep,
                "train_weighted_bce": float(np.mean(tr_bce)),
                "val_weighted_bce": float(v_stats["weighted_bce"]),
                "val_mse": float(v_stats["mse"]),
                "val_mae": float(v_stats["mae"]),
            })
            if checkpoint_rule == "fixed_epochs" or float(v_stats["weighted_bce"]) <= best_v_loss:
                best_v_loss = float(v_stats["weighted_bce"])
                P.save_checkpoint(
                    {
                        "domain": dom_l,
                        "round": round_name,
                        "seed": seed,
                        "epoch": ep,
                        "best_val_weighted_bce": best_v_loss,
                        "hidden": val_model.h,
                        "observation_schema": schema,
                        "scalers": scalers,
                        "state_dict": val_model.state_dict(),
                    },
                    save_dir / "value.pt",
                )

    stop_pos = sum(1 for r in val_rows if r["is_stop"] and r["value_target"] >= 0.5)
    stop_neg = sum(1 for r in val_rows if r["is_stop"] and r["value_target"] < 0.5)
    reloc_pos = sum(1 for r in val_rows if not r["is_stop"] and r["value_target"] > 0.0)
    reloc_zero = sum(1 for r in val_rows if not r["is_stop"] and r["value_target"] == 0.0)

    report = {
        "domain": dom_l,
        "round": round_name,
        "observation_schema": schema,
        "seed": seed,
        "edges_mode": extracted.get("edges_mode", "all_feasible"),
        "checkpoint_rule":checkpoint_rule,
        "selection_scope": "Fixed epoch schedule; training loss diagnostic" if checkpoint_rule == "fixed_epochs" else "TRAIN-pool family monitor; not benchmark VALIDATION",
        "monitor_families": sorted(val_root_set),
        "hyperparameters": {"epochs":epochs, "batch_size":batch_size, "lr":lr, "weight_decay":1e-4},
        "n_trees": extracted.get("n_trees", 0),
        "n_trees_with_solution": extracted.get("n_trees_with_solution", 0),
        "total_sim_calls": extracted.get("total_sim_calls", 0),
        "n_policy_dst_rows": len(dst_rows),
        "n_policy_obj_rows": len(obj_rows),
        "n_value_rows": len(val_rows),
        "value_row_breakdown": {
            "stop_positive": stop_pos,
            "stop_negative": stop_neg,
            "reloc_positive_target": reloc_pos,
            "reloc_zero_target": reloc_zero,
        },
        "policy_ckpt": str(save_dir / "policy.pt"),
        "value_ckpt": str(save_dir / "value.pt") if val_tr else None,
        "wall_s": round(time.time() - t0, 2),
        "policy_curve": pol_curve,
        "value_curve": val_curve,
    }
    (save_dir / "distill_report.json").write_text(json.dumps(report, indent=2))
    return report


def load_value_checkpoint(ckpt_path: Path | str, device: str = "cuda") -> tuple[P.DiscoValueNet, dict[str, Any]]:
    ck = torch.load(ckpt_path, map_location=device, weights_only=False)
    model = P.DiscoValueNet(ck["domain"], h=ck.get("hidden", 128), observation_schema=ck.get("observation_schema", P.O0)).to(device)
    model.load_state_dict(ck["state_dict"])
    model.eval()
    return model, ck


def merge_extracted_datasets(d_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine extracted policy/value rows across rounds (`r0 + r1`) for cumulative distillation."""
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
