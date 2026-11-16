#!/usr/bin/env python3
"""DISCO-Grid Training-Only Progressive-Widening MCTS (`DISCO_plan.md` Section 8).

Implements progressive-widening MCTS from Saha et al. (CoRL 2026), adapted to discrete object-destination
rearrangement with stateful physical transitions (`RepairEnv`):
- Progressive widening condition (`disco/search/mcts.py:797`):
      |children(v)| < k * (N(v) ** alpha)   with k=2.0, alpha=0.3
- UCB child selection (`disco/search/mcts.py:482`):
      UCB(v') = Q(v') + C * sqrt(log(N(v) + 1) / (N(v') + 1))   with C=1.5
- Candidate expansion:
  Samples up to `B` unique legal `(object, destination)` actions from the current policy `pi_theta`,
  deduplicating actions already attempted at `v`. Executes each new candidate through `env.transition`.
  Only physically `EXECUTED` transitions become feasible child nodes; failed/unresolved attempts are
  logged for sample-efficiency and failure-taxonomy accounting.
- Child Q initialization:
  In Round 0 (no `Q_phi`), new feasible children initialize `Q = edge_reward`.
  In Round >= 1 (with `Q_phi`), new feasible children initialize `Q = Q_phi(obs_parent, action)`.
- Terminal `STOP` branch semantics (Sections 3.4 & 8.4):
  At any node `v` (depths 0..3), `STOP` is evaluated via `env.terminal_query(v.state)` (connector to `q_ref`
  + canonical endpoint `Y`).
  - If `STOP` succeeds (`Z = 1`), a verified terminal child `v_stop` (`kappa = 1.0`) is attached and selected.
  - If `STOP` fails (`Z = 0`) at depth `< 3`, the decided negative `STOP` outcome is recorded for value
    distillation (`Z_stop = 0`), while `v` remains open to explore longer corrective relocation sequences.
  - At depth `3`, no further relocations are legal; the descent terminates at `v` with its `STOP` outcome.
- Disk persistence & crash recovery:
  Saves tree nodes (`tree.json` + compressed state blobs `states.pkl`) for deterministic resume and
  post-search dataset extraction (`distill.py`).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import pickle
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import data as D
import env as E
import policy as P
import journal as J


def point_to_segment_dist(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    den = abx * abx + aby * aby
    if den <= 1e-12:
        return math.hypot(apx, apy)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / den))
    return math.hypot(apx - t * abx, apy - t * aby)


def compute_progress_kappa(
    obs: E.LearnerObservation,
    is_verified_terminal_success: bool = False,
    mode: str = "geometric",
) -> float:
    """Compute label-blind progress score `kappa(s)` (`DISCO_plan.md` Section 8.3).
    - Exactly `1.0` for a physically verified successful terminal (`Z = 1`).
    - Strictly bounded in `[0.0, 0.85]` (`< 1.0`) for all nonterminal states under `mode='geometric'`
      so heuristic partial clearance never outranks a verified terminal solution.
    - Exactly `0.0` for all non-successful states under `mode='sparse'`.
    - Uses ONLY learner-visible coordinates (`obs.cells`, `obs.xy`, `obs.tid`, `obs.goal_cell`, `obs.goal_xy`).
    """
    if is_verified_terminal_success:
        return 1.0
    if mode == "sparse":
        return 0.0

    dom_l = obs.domain.lower()
    R, C = D.GRID_SHAPE[dom_l]
    pitch = 0.08 if dom_l == "2d" else 0.075

    tid = int(obs.tid)
    t_cell = int(obs.cells[tid])
    g_cell = int(obs.goal_cell)
    tr, tc = divmod(t_cell, C)
    gr, gc = divmod(g_cell, C)
    tx, ty = float(obs.xy[tid][0]), float(obs.xy[tid][1])
    gx, gy = float(obs.goal_xy[0]), float(obs.goal_xy[1])

    h_goal = 0.0
    h_swept = 0.0
    for i, c_val in enumerate(obs.cells):
        if i == tid:
            continue
        r, c = divmod(int(c_val), C)
        ox, oy = float(obs.xy[i][0]), float(obs.xy[i][1])

        cheb_g = max(abs(r - gr), abs(c - gc))
        if int(c_val) == g_cell:
            h_goal += 1.5
        elif cheb_g == 1:
            h_goal += 0.6

        cheb_t = max(abs(r - tr), abs(c - tc))
        if cheb_t == 1:
            h_swept += 0.5
        seg_d = point_to_segment_dist(ox, oy, tx, ty, gx, gy)
        if seg_d <= 1.35 * pitch:
            h_swept += max(0.0, 1.0 - seg_d / (1.5 * pitch))

    H = 4.0
    raw = 1.0 - min(1.0, max(0.0, (h_goal + h_swept) / H))
    # Bound nonterminal heuristic strictly in [0.0, 0.85] (< 1.0)
    return round(0.85 * raw, 6)


@dataclass
class MCTSNode:
    node_id: int
    parent_id: int | None
    prefix: list[tuple[int, int]]
    depth: int
    state_blob: bytes
    state_hash: str
    obs: E.LearnerObservation
    incoming_action: tuple[int, int] | str | None  # (o, d) or "STOP" or None (root)
    is_stop_node: bool = False
    is_failed: bool = False
    failure_type: str | None = None
    progress_kappa: float = 0.0
    edge_reward: float = 0.0
    visit_count: int = 0
    Q: float = 0.0
    q_prior: float | None = None
    Q_history: list[float] = field(default_factory=list)
    children_ids: list[int] = field(default_factory=list)
    attempted_actions: list[tuple[int, int]] = field(default_factory=list)
    failed_attempts: list[dict[str, Any]] = field(default_factory=list)
    stop_evaluated: bool = False
    stop_result: E.StopResult | None = None
    stop_child_id: int | None = None
    terminal_z: int | None = None  # 1, 0, or None (if unresolved or nonterminal)
    created_at_iter: int = 0
    first_visit_iter: int = -1
    step_time_s: float = 0.0
    witness_ids: list[str] = field(default_factory=list)

    def ucb_score(self, parent_visits: int, C: float) -> float:
        if self.is_failed:
            return float("-inf")
        return float(self.Q + C * math.sqrt(math.log(parent_visits + 1) / (self.visit_count + 1)))


class DISCOMCTS:
    """Progressive-Widening MCTS over stateful physical transitions for DISCO-Grid."""

    def __init__(
        self,
        env: E.RepairEnv,
        proposal: P.PolicyProposalWrapper,
        C: float = 1.5,
        k: float = 2.0,
        alpha: float = 0.3,
        max_depth: int = 3,
        expansion_budget_B: int = 8,
        use_progressive_widening: bool = True,
        selection_mode: str = "ucb",  # "ucb" or "random"
        reward_mode: str = "geometric",  # "geometric" or "sparse"
        seed: int = 0,
    ):
        self.env = env
        self.proposal = proposal
        self.C = float(C)
        self.k = float(k)
        self.alpha = float(alpha)
        self.max_depth = int(max_depth)
        self.expansion_budget_B = int(expansion_budget_B)
        self.use_progressive_widening = bool(use_progressive_widening)
        self.selection_mode = selection_mode
        self.reward_mode = reward_mode
        self.seed = int(seed)
        self.rng = np.random.default_rng(seed)

        self.nodes: list[MCTSNode] = []
        self.edge_logs: list[dict[str, Any]] = []
        self.sim_transition_calls = 0
        self.sim_terminal_calls = 0
        self.current_iter = 0
        self.cancel_requested = False
        self.completed_iterations = 0
        self.resolved_run_config: dict[str, Any] = {}
        self.iteration_traces: list[dict[str, Any]] = []
        self.cumulative_wall_s = 0.0
        self.cumulative_cpu_s = 0.0
        self.save_dir: Path | None = None

    def _journal_query(self, event: str, kind: str, node: MCTSNode, result=None, action=None):
        if self.save_dir is None: return
        if not hasattr(self, "query_journal"):
            self.query_journal = J.QueryJournal(self.save_dir)
        if event == "started":
            self.query_journal.start(self.sim_transition_calls+self.sim_terminal_calls,kind,node.state_blob,
                {"parent_id":node.node_id,"root_id":node.obs.root_id,"action":action,
                 "parent_state_hash":node.state_hash,"depth":node.depth,
                 "resolved_config_sha256":hashlib.sha256(json.dumps(self.resolved_run_config,sort_keys=True).encode()).hexdigest()})
        else:
            self.query_journal.finish(result)

    def _increment_visit(self, node: MCTSNode):
        if node.visit_count == 0 and node.first_visit_iter < 0:
            node.first_visit_iter = self.current_iter
        node.visit_count += 1

    def widening_condition(self, node: MCTSNode) -> bool:
        """DISCO progressive widening condition: |children(v)| < k * N(v)^alpha.
        If `use_progressive_widening=False` (fixed-width ablation), expands only once when `len(children) == 0`.
        """
        if node.is_stop_node or node.depth >= self.max_depth:
            return False
        reloc_kids = [cid for cid in node.children_ids if not self.nodes[cid].is_stop_node]
        n_total_legal = len(node.obs.eligible_objects) * len(node.obs.legal_destinations)
        if len(node.attempted_actions) >= n_total_legal:
            return False
        if not self.use_progressive_widening:
            return len(node.attempted_actions) == 0
        return len(reloc_kids) < self.k * (max(node.visit_count, 1) ** self.alpha)

    def _evaluate_node_stop(self, node: MCTSNode) -> E.StopResult:
        """Evaluate `STOP` at `node` via `env.terminal_query`. Cached on `node`.
        If `STOP` succeeds (`Z = 1`), creates a terminal child `v_stop` (`is_stop_node=True`, `terminal_z=1`).
        """
        if node.stop_evaluated and node.stop_result is not None:
            return node.stop_result
        state = self.env.restore(node.state_blob)
        self.sim_terminal_calls += 1
        self._journal_query("started","terminal",node)
        stop_res = self.env.terminal_query(state)
        self._journal_query("finished","terminal",node,result=stop_res)
        node.stop_evaluated = True
        node.stop_result = stop_res
        node.terminal_z = stop_res.z_outcome

        if stop_res.status == "DECIDED" and stop_res.success:
            # Create a verified successful terminal STOP child node
            r_edge = 1.0 - node.progress_kappa
            q_init = r_edge
            if self.proposal.value_model is not None:
                q_init = float(self.proposal.score_actions_q(node.obs, ["STOP"])[0])
            stop_node = MCTSNode(
                node_id=len(self.nodes),
                parent_id=node.node_id,
                prefix=list(node.prefix),
                depth=node.depth + 1,
                state_blob=node.state_blob,
                state_hash=node.state_hash + "|STOP",
                obs=node.obs,
                incoming_action="STOP",
                is_stop_node=True,
                is_failed=False,
                progress_kappa=1.0,
                edge_reward=r_edge,
                visit_count=0,
                Q=q_init,
                q_prior=q_init if self.proposal.value_model is not None else None,
                stop_evaluated=True,
                stop_result=stop_res,
                terminal_z=1,
                created_at_iter=self.current_iter,
                step_time_s=stop_res.time_s,
                witness_ids=[w for w in (stop_res.witness_connector, stop_res.witness_y) if w],
            )
            self.nodes.append(stop_node)
            node.children_ids.append(stop_node.node_id)
            node.stop_child_id = stop_node.node_id
        return stop_res

    def _expand(self, node: MCTSNode, max_sim_calls_remaining: int | None = None):
        """Sample candidate actions from `pi_theta`, filter already-attempted actions at `node`,
        and execute up to `expansion_budget_B` physical transitions via `env.transition`.
        """
        if node.depth >= self.max_depth:
            return
        # Sample over all available legal actions and take up to B unattempted ones
        n_avail = len(node.obs.eligible_objects) * len(node.obs.legal_destinations)
        if n_avail == 0:
            return
        samp = self.proposal.sample_candidates(node.obs, B=n_avail, rng=self.rng)
        already = set(map(tuple, node.attempted_actions))
        unattempted = [tuple(a) for a in samp["candidates"] if tuple(a) not in already]
        batch = unattempted[: self.expansion_budget_B]
        if max_sim_calls_remaining is not None:
            batch = batch[: max(0, max_sim_calls_remaining)]
        if not batch:
            return

        parent_state = self.env.restore(node.state_blob)
        executed_actions = []
        executed_states = []
        executed_results = []

        for act in batch:
            if self.cancel_requested: break
            node.attempted_actions.append(act)
            self.sim_transition_calls += 1
            self._journal_query("started","transition",node,action=act)
            sr = self.env.transition(parent_state, act)
            self._journal_query("finished","transition",node,result=sr,action=act)
            self.edge_logs.append({
                "root_id": node.obs.root_id,
                "parent_id": node.node_id,
                "depth": node.depth + 1,
                "action": [int(act[0]), int(act[1])],
                "parent_state_hash": node.state_hash,
                "child_state_hash": sr.next_state.state_hash() if sr.next_state is not None else None,
                "status": sr.status,
                "failure_kind": sr.failure_kind,
                "teacher_status": sr.teacher_status,
                "time_s": sr.time_s,
                "planner_calls": sr.planner_calls,
                "seed": self.seed,
            })
            if sr.status == "EXECUTED" and sr.next_state is not None:
                executed_actions.append(act)
                executed_states.append(sr.next_state)
                executed_results.append(sr)
            else:
                node.failed_attempts.append({
                    "action": [int(act[0]), int(act[1])],
                    "status": sr.status,
                    "failure_kind": sr.failure_kind,
                    "teacher_status": sr.teacher_status,
                    "time_s": sr.time_s,
                })

        if not executed_actions:
            return

        q_priors = None
        if self.proposal.value_model is not None:
            q_priors = self.proposal.score_actions_q(node.obs, executed_actions)

        for idx, (act, next_st, sr) in enumerate(zip(executed_actions, executed_states, executed_results)):
            child_obs = self.env.observe(next_st, include_qt=self.proposal.observation_schema == P.O1)
            child_blob = self.env.clone_or_serialize(next_st)
            kappa_child = compute_progress_kappa(child_obs, is_verified_terminal_success=False, mode=self.reward_mode)
            r_edge = kappa_child - node.progress_kappa
            q_init = float(q_priors[idx]) if q_priors is not None else r_edge
            child = MCTSNode(
                node_id=len(self.nodes),
                parent_id=node.node_id,
                prefix=list(next_st.prefix),
                depth=next_st.depth,
                state_blob=child_blob,
                state_hash=next_st.state_hash(),
                obs=child_obs,
                incoming_action=act,
                is_stop_node=False,
                is_failed=False,
                progress_kappa=kappa_child,
                edge_reward=r_edge,
                visit_count=0,
                Q=q_init,
                q_prior=float(q_priors[idx]) if q_priors is not None else None,
                created_at_iter=self.current_iter,
                step_time_s=sr.time_s,
                witness_ids=list(sr.witness_ids),
            )
            self.nodes.append(child)
            node.children_ids.append(child.node_id)

    def _select_child(self, node: MCTSNode) -> MCTSNode | None:
        kids = [self.nodes[cid] for cid in node.children_ids if not self.nodes[cid].is_failed]
        if not kids:
            return None
        if self.selection_mode == "random":
            return kids[int(self.rng.integers(len(kids)))]
        # Shuffle for uniform random tie-breaking, matching disco/search/mcts.py:958
        order = self.rng.permutation(len(kids))
        best_k = kids[int(order[0])]
        best_ucb = best_k.ucb_score(node.visit_count, self.C)
        for idx in order[1:]:
            k_cand = kids[int(idx)]
            u = k_cand.ucb_score(node.visit_count, self.C)
            if u > best_ucb:
                best_ucb = u
                best_k = k_cand
        return best_k

    def path_return(self, leaf: MCTSNode) -> float:
        R = 0.0
        cur: MCTSNode | None = leaf
        while cur is not None and cur.parent_id is not None:
            R += cur.edge_reward
            cur = self.nodes[cur.parent_id]
        return float(R)

    def backpropagate(self, leaf: MCTSNode):
        R = self.path_return(leaf)
        cur: MCTSNode | None = leaf
        while cur is not None:
            if cur.parent_id is not None:
                cur.Q = float(cur.Q + (R - cur.Q) / max(cur.visit_count, 1))
                cur.Q_history.append(cur.Q)
            cur = self.nodes[cur.parent_id] if cur.parent_id is not None else None

    def run_search(
        self,
        root_id: str,
        iterations: int = 12,
        max_sim_calls: int | None = None,
        save_dir: Path | None = None,
    ) -> dict[str, Any]:
        """Run MCTS from `root_id` for `iterations` rollouts (or until `max_sim_calls` is reached)."""
        E.assert_physics_allowed("MCTS_calls")
        t0 = time.time()
        cpu0 = time.process_time()
        accounted_wall, accounted_cpu = t0, cpu0
        self.save_dir = Path(save_dir) if save_dir is not None else None
        def model_hash(model):
            if model is None: return None
            h = hashlib.sha256()
            for name, tensor in sorted(model.state_dict().items()):
                h.update(name.encode())
                h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
            return h.hexdigest()
        config = {"iterations": iterations, "max_sim_calls": max_sim_calls,
                  "proposal_mode":self.proposal.mode,
                  "policy_state_sha256":model_hash(self.proposal.model),
                  "value_state_sha256":model_hash(self.proposal.value_model),
                  "scalers_sha256":hashlib.sha256(json.dumps(self.proposal.scalers,sort_keys=True).encode()).hexdigest(),
                  "adapter_source_sha256":D.sha256_file(HERE / "env.py"),
                  "search_sources_sha256":{n:D.sha256_file(HERE/n) for n in ("mcts.py","policy.py","data.py","journal.py")},
                  "C": self.C, "k": self.k, "alpha": self.alpha,
                  "expansion_budget_B": self.expansion_budget_B, "max_depth": self.max_depth,
                  "selection_mode": self.selection_mode, "reward_mode": self.reward_mode,
                  "use_progressive_widening": self.use_progressive_widening,
                  "observation_schema": self.proposal.observation_schema, "seed": self.seed}
        if self.resolved_run_config and config != self.resolved_run_config:
            raise ValueError("Resume requires identical resolved configuration and total budgets")
        self.resolved_run_config = config
        if self.nodes and self.nodes[0].obs.root_id != root_id:
            raise ValueError("Cannot resume a different root")
        if max_sim_calls is not None and max_sim_calls < 0:
            raise ValueError("Negative physical-call budget")
        def has_budget():
            return not self.cancel_requested and (max_sim_calls is None or self.sim_transition_calls + self.sim_terminal_calls < max_sim_calls)
        if not self.nodes:
            s0 = self.env.reset(root_id, seed=self.seed)
            obs0 = self.env.observe(s0, include_qt=self.proposal.observation_schema == P.O1)
            blob0 = self.env.clone_or_serialize(s0)
            kappa0 = compute_progress_kappa(obs0, is_verified_terminal_success=False, mode=self.reward_mode)
            root = MCTSNode(
                node_id=0,
                parent_id=None,
                prefix=[],
                depth=0,
                state_blob=blob0,
                state_hash=s0.state_hash(),
                obs=obs0,
                incoming_action=None,
                progress_kappa=kappa0,
                edge_reward=0.0,
            )
            self.nodes.append(root)

        root = self.nodes[0]
        start_iter = self.completed_iterations

        for it in range(start_iter, iterations):
            if self.cancel_requested or not has_budget():
                break
            if save_dir is not None:
                Path(save_dir).mkdir(parents=True, exist_ok=True)
                J.atomic_bytes(Path(save_dir)/"IN_FLIGHT",str(it).encode())
            self.current_iter = it
            cur = root
            self._increment_visit(cur)

            while not cur.is_stop_node and cur.depth < self.max_depth:
                # 1. Evaluate STOP at `cur` if not yet evaluated
                if not cur.stop_evaluated and has_budget():
                    stop_res = self._evaluate_node_stop(cur)
                    # If K0 root (depth 0) or intermediate prefix already solves the task (Z=1),
                    # and stop_child was created, select it immediately on first discovery!
                    if stop_res.success and cur.stop_child_id is not None:
                        cur = self.nodes[cur.stop_child_id]
                        self._increment_visit(cur)
                        break

                # 2. Check progressive widening for relocation actions
                if self.widening_condition(cur):
                    rem = None if max_sim_calls is None else (max_sim_calls - (self.sim_transition_calls + self.sim_terminal_calls))
                    if rem is None or rem > 0:
                        self._expand(cur, max_sim_calls_remaining=rem)

                # 3. Select best child by UCB
                child = self._select_child(cur)
                if child is None:
                    break
                cur = child
                self._increment_visit(cur)

            # If descent ended at depth == max_depth (or a non-stop leaf without children), ensure terminal STOP is evaluated
            if not cur.is_stop_node and not cur.stop_evaluated and has_budget():
                stop_res = self._evaluate_node_stop(cur)
                if stop_res.success and cur.stop_child_id is not None:
                    cur = self.nodes[cur.stop_child_id]
                    self._increment_visit(cur)

            self.backpropagate(cur)
            self.completed_iterations = it + 1
            self.iteration_traces.append({"iteration": it, "leaf_id": cur.node_id,
                "path_return": self.path_return(cur), "transition_calls": self.sim_transition_calls,
                "terminal_calls": self.sim_terminal_calls,
                "visits": [n.visit_count for n in self.nodes], "Q": [n.Q for n in self.nodes]})
            now, cpu = time.time(), time.process_time()
            self.cumulative_wall_s += now-accounted_wall
            self.cumulative_cpu_s += cpu-accounted_cpu
            accounted_wall, accounted_cpu = now, cpu
            if save_dir is not None:
                self.save_tree(save_dir)
                (Path(save_dir) / "IN_FLIGHT").unlink(missing_ok=True)

        self.cumulative_wall_s += time.time() - accounted_wall
        self.cumulative_cpu_s += time.process_time() - accounted_cpu
        wall_s = round(time.time() - t0, 3)
        summary = self.tree_summary(wall_s=wall_s)
        if save_dir is not None:
            self.save_tree(save_dir, summary)
        return summary

    def tree_summary(self, wall_s: float = 0.0) -> dict[str, Any]:
        succ_nodes = [n for n in self.nodes if n.is_stop_node and n.terminal_z == 1]
        reloc_nodes = [n for n in self.nodes if n.node_id > 0 and not n.is_stop_node]
        failed_attempts = sum(len(n.failed_attempts) for n in self.nodes)
        best_ret = max((self.path_return(n) for n in self.nodes), default=0.0)
        return {
            "root_id": self.nodes[0].obs.root_id if self.nodes else None,
            "domain": self.env.domain,
            "seed": self.seed,
            "reward_mode": self.reward_mode,
            "use_progressive_widening": self.use_progressive_widening,
            "root_visits": self.nodes[0].visit_count if self.nodes else 0,
            "total_nodes": len(self.nodes),
            "feasible_relocation_edges": len(reloc_nodes),
            "failed_transition_attempts": failed_attempts,
            "successful_terminal_nodes": len(succ_nodes),
            "found_verified_solution": len(succ_nodes) > 0,
            "verified_solutions": [n.prefix for n in succ_nodes],
            "best_path_return": round(float(best_ret), 4),
            "sim_transition_calls": self.sim_transition_calls,
            "sim_terminal_calls": self.sim_terminal_calls,
            "total_sim_calls": self.sim_transition_calls + self.sim_terminal_calls,
            "wall_s": wall_s,
            "cumulative_wall_s": self.cumulative_wall_s,
            "cumulative_cpu_s": self.cumulative_cpu_s,
            "completed_iterations": self.completed_iterations,
            "resolved_config": self.resolved_run_config,
            "budget_unit": "adapter_transition_plus_terminal_calls; terminal may include connector and Y",
        }

    def save_tree(self, save_dir: Path | str, summary: dict[str, Any] | None = None):
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        # Save JSON metadata (without binary state_blob) + pickle full nodes for exact resume/distillation
        json_nodes = []
        for n in self.nodes:
            json_nodes.append({
                "node_id": n.node_id,
                "parent_id": n.parent_id,
                "prefix": n.prefix,
                "depth": n.depth,
                "state_hash": n.state_hash,
                "incoming_action": n.incoming_action if n.incoming_action == "STOP" or n.incoming_action is None else list(n.incoming_action),
                "is_stop_node": n.is_stop_node,
                "progress_kappa": n.progress_kappa,
                "edge_reward": n.edge_reward,
                "visit_count": n.visit_count,
                "Q": round(n.Q, 6),
                "q_prior": round(n.q_prior, 6) if n.q_prior is not None else None,
                "children_ids": n.children_ids,
                "n_attempted_actions": len(n.attempted_actions),
                "n_failed_attempts": len(n.failed_attempts),
                "stop_evaluated": n.stop_evaluated,
                "terminal_z": n.terminal_z,
                "witness_ids": n.witness_ids,
            })
        payload = {
            "summary": summary or self.tree_summary(),
            "nodes": json_nodes,
            "edge_logs": self.edge_logs,
        }
        payload["resolved_config"] = self.resolved_run_config
        payload["iteration_traces"] = self.iteration_traces
        # One atomic checkpoint is authoritative. Legacy extraction mirrors are
        # disposable; resume never assembles a tree from mixed file generations.
        checkpoint = {"version": 2, "config": self.resolved_run_config, "summary":payload["summary"],
            "nodes": self.nodes, "edge_logs": self.edge_logs,
            "rng_state": self.rng.bit_generator.state,
            "sim_transition_calls": self.sim_transition_calls,
            "sim_terminal_calls": self.sim_terminal_calls,
            "completed_iterations": self.completed_iterations,
            "iteration_traces": self.iteration_traces,
            "cumulative_wall_s": self.cumulative_wall_s,
            "cumulative_cpu_s": self.cumulative_cpu_s,
            "backend_caches": self.env.snapshot_caches() if hasattr(self.env,"snapshot_caches") else None}
        checkpoint_bytes=pickle.dumps(checkpoint,protocol=pickle.HIGHEST_PROTOCOL)
        J.atomic_bytes(save_dir/"checkpoint.pkl",checkpoint_bytes)
        J.atomic_bytes(save_dir/"checkpoint.sha256",hashlib.sha256(checkpoint_bytes).hexdigest().encode())
        J.atomic_bytes(save_dir/"nodes.pkl",pickle.dumps(self.nodes,protocol=pickle.HIGHEST_PROTOCOL))
        J.atomic_json(save_dir/"tree.json",payload)

    def resume(self, save_dir: Path | str) -> None:
        """Resume a clean iteration boundary; refuse uncertain in-flight crashes.

        A terminated physical call cannot be charged exactly after a process crash.
        Such runs require explicit reconciliation, never automatic re-execution.
        Pickles must be trusted local artifacts.
        """
        save_dir = Path(save_dir)
        if (save_dir / "IN_FLIGHT").exists() or (save_dir/"ACTIVE_QUERY.json").exists():
            raise ValueError("Unreconciled in-flight physical queries; automatic resume refused")
        if not (save_dir/"checkpoint.sha256").exists() or D.sha256_file(save_dir/"checkpoint.pkl")!=(save_dir/"checkpoint.sha256").read_text():
            raise ValueError("Uncertified or corrupt checkpoint checksum")
        with open(save_dir / "checkpoint.pkl", "rb") as f:
            ck = pickle.load(f)
        if ck["version"] != 2:
            raise ValueError("Unsupported search checkpoint version")
        if (save_dir/"queries.jsonl").exists():
            J.certify_journal(save_dir,ck["sim_transition_calls"]+ck["sim_terminal_calls"])
        else:
            raise ValueError("Missing durable journal; legacy tree is analysis-only")
        if ck.get("backend_caches") is not None:
            self.env.restore_caches(ck["backend_caches"])
        self.resolved_run_config = ck["config"]
        self.nodes = ck["nodes"]
        self.edge_logs = ck["edge_logs"]
        self.rng.bit_generator.state = ck["rng_state"]
        self.sim_transition_calls = ck["sim_transition_calls"]
        self.sim_terminal_calls = ck["sim_terminal_calls"]
        self.completed_iterations = ck["completed_iterations"]
        self.iteration_traces = ck["iteration_traces"]
        self.cumulative_wall_s = ck["cumulative_wall_s"]
        self.cumulative_cpu_s = ck["cumulative_cpu_s"]


def load_saved_tree_nodes(tree_dir: Path | str) -> tuple[list[MCTSNode], dict[str, Any]]:
    tree_dir = Path(tree_dir)
    if (tree_dir/"IN_FLIGHT").exists() or (tree_dir/"ACTIVE_QUERY.json").exists():
        raise ValueError("Unreconciled physical tree cannot supervise training")
    if (tree_dir/"checkpoint.pkl").exists():
        with (tree_dir/"checkpoint.pkl").open("rb") as f: ck=pickle.load(f)
        return ck["nodes"], {"summary":ck["summary"] if "summary" in ck else json.loads((tree_dir/"tree.json").read_text())["summary"],"config":ck["config"]}
    meta = json.loads((tree_dir / "tree.json").read_text())
    with open(tree_dir / "nodes.pkl", "rb") as f:
        nodes = pickle.load(f)
    return nodes, meta


def select_mcts_train_cohort(dom: str, counts_by_k: dict[str, int] | None = None, seed: int = 0) -> list[dict[str, Any]]:
    """Deterministically select a stratified cohort of TRAIN roots (`K0, K1, K2, K3, NONE`) for MCTS."""
    import hashlib
    dom_l = dom.lower()
    if counts_by_k is None:
        counts_by_k = (
            {"0": 4, "1": 6, "2": 6, "3": 5, "NONE": 3}
            if dom_l == "2d"
            else {"0": 2, "1": 4, "2": 3, "3": 2, "NONE": 1}
        )
    rows = D.load_snapshot_rows(dom_l, "train", D.BASE_SNAP)
    out = []
    for k_cls, cnt in counts_by_k.items():
        sub = [r for r in rows if r["K_legacy"] == k_cls]
        # Prefer certified solvable roots for K1..K3 so MCTS progress is measurable on known solvable tasks
        if k_cls in ("1", "2", "3"):
            sub.sort(
                key=lambda r: (
                    not bool(r["masks"]["eval_repair"]),
                    hashlib.sha256(f"mcts_cohort|{seed}|{r['root_id']}".encode()).hexdigest(),
                )
            )
        else:
            sub.sort(key=lambda r: hashlib.sha256(f"mcts_cohort|{seed}|{r['root_id']}".encode()).hexdigest())
        out.extend(sub[:cnt])
    return out


def _mcts_worker_job(job: dict[str, Any]) -> dict[str, Any]:
    os.environ["OMP_NUM_THREADS"] = "1"
    dom = job["domain"]
    root_id = job["root_id"]
    k_legacy = job["K_legacy"]
    save_dir = Path(job["save_dir"])
    if (save_dir / "tree.json").exists() and (save_dir / "nodes.pkl").exists():
        meta = json.loads((save_dir / "tree.json").read_text())
        s = meta["summary"]
        s["K_legacy"] = k_legacy
        return s

    env = E.RepairEnv(dom)
    scalers = job["scalers"]
    pol_ckpt = job.get("policy_ckpt")
    val_ckpt = job.get("value_ckpt")
    prop_mode = job.get("proposal_mode", "p0")

    pol_model = None
    if pol_ckpt is not None and prop_mode != "uniform":
        pol_model, _ = P.load_policy_checkpoint(pol_ckpt, device="cpu")
    val_model = None
    if val_ckpt is not None:
        ck_v = torch.load(val_ckpt, map_location="cpu", weights_only=False)
        val_model = P.DiscoValueNet(dom, h=ck_v.get("hidden", 128), observation_schema=ck_v.get("observation_schema", P.O0)).to("cpu")
        val_model.load_state_dict(ck_v["state_dict"])
        val_model.eval()

    proposal = P.PolicyProposalWrapper(
        dom,
        pol_model,
        scalers,
        device="cpu",
        mode=prop_mode,
        value_model=val_model,
    )
    mcts = DISCOMCTS(
        env=env,
        proposal=proposal,
        C=job.get("C", 1.5),
        k=job.get("k", 2.0),
        alpha=job.get("alpha", 0.3),
        max_depth=3,
        expansion_budget_B=job.get("expansion_budget_B", 4),
        use_progressive_widening=job.get("use_progressive_widening", True),
        selection_mode=job.get("selection_mode", "ucb"),
        reward_mode=job.get("reward_mode", "geometric"),
        seed=job.get("seed", 0),
    )
    summary = mcts.run_search(
        root_id=root_id,
        iterations=job.get("iterations", 10),
        max_sim_calls=job.get("max_sim_calls", 16),
        save_dir=save_dir,
    )
    summary["K_legacy"] = k_legacy
    return summary


import torch  # noqa: E402


def run_mcts_cohort_parallel(
    dom: str,
    cohort: list[dict[str, Any]],
    out_trees_dir: Path,
    scalers: dict[str, Any],
    policy_ckpt: Path | str | None,
    value_ckpt: Path | str | None = None,
    proposal_mode: str = "p0",
    iterations: int = 10,
    expansion_budget_B: int = 4,
    max_sim_calls: int = 16,
    use_progressive_widening: bool = True,
    reward_mode: str = "geometric",
    seed: int = 0,
    workers: int = 12,
) -> dict[str, Any]:
    """Run MCTS across a cohort of TRAIN roots in parallel worker processes."""
    import hashlib
    import multiprocessing as mp
    dom_l = dom.lower()
    out_trees_dir = Path(out_trees_dir)
    out_trees_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    for r in cohort:
        rid = r["root_id"]
        r_seed = int(hashlib.sha256(f"tree|{dom_l}|{rid}|{seed}".encode()).hexdigest()[:8], 16) % (2**31 - 1)
        jobs.append({
            "domain": dom_l,
            "root_id": rid,
            "K_legacy": r["K_legacy"],
            "save_dir": str(out_trees_dir / rid),
            "scalers": scalers,
            "policy_ckpt": str(policy_ckpt) if policy_ckpt is not None else None,
            "value_ckpt": str(value_ckpt) if value_ckpt is not None else None,
            "proposal_mode": proposal_mode,
            "iterations": iterations,
            "expansion_budget_B": expansion_budget_B,
            "max_sim_calls": max_sim_calls,
            "use_progressive_widening": use_progressive_widening,
            "reward_mode": reward_mode,
            "seed": r_seed,
        })

    t0 = time.time()
    n_w = min(workers, max(1, len(jobs)))
    if n_w > 1:
        with mp.get_context("spawn").Pool(n_w) as pool:
            summaries = list(pool.map(_mcts_worker_job, jobs))
    else:
        summaries = [_mcts_worker_job(j) for j in jobs]

    wall_s = round(time.time() - t0, 2)
    task_summaries = [s for s in summaries if s.get("K_legacy") in ("1", "2", "3")]
    k0_summaries = [s for s in summaries if s.get("K_legacy") == "0"]
    none_summaries = [s for s in summaries if s.get("K_legacy") == "NONE"]

    tot_sim = sum(s["total_sim_calls"] for s in summaries)
    tot_trans = sum(s["sim_transition_calls"] for s in summaries)
    tot_term = sum(s["sim_terminal_calls"] for s in summaries)
    tot_feas = sum(s["feasible_relocation_edges"] for s in summaries)
    tot_fail = sum(s["failed_transition_attempts"] for s in summaries)
    n_task_solved = sum(1 for s in task_summaries if s["found_verified_solution"])
    n_k0_solved = sum(1 for s in k0_summaries if s["found_verified_solution"])
    n_none_solved = sum(1 for s in none_summaries if s["found_verified_solution"])

    by_k = {}
    for k_cls in ("0", "1", "2", "3", "NONE"):
        sub = [s for s in summaries if s.get("K_legacy") == k_cls]
        if sub:
            by_k[f"K{k_cls}"] = {
                "n_roots": len(sub),
                "n_solved": sum(1 for s in sub if s["found_verified_solution"]),
                "solve_rate": round(sum(1 for s in sub if s["found_verified_solution"]) / len(sub), 4),
                "mean_sim_calls": round(float(np.mean([s["total_sim_calls"] for s in sub])), 2),
                "mean_feasible_edges": round(float(np.mean([s["feasible_relocation_edges"] for s in sub])), 2),
            }

    agg = {
        "domain": dom_l,
        "proposal_mode": proposal_mode,
        "use_progressive_widening": use_progressive_widening,
        "reward_mode": reward_mode,
        "seed": seed,
        "n_trees": len(summaries),
        "n_task_roots": len(task_summaries),
        "n_task_solved": n_task_solved,
        "task_solve_rate_in_search": round(n_task_solved / max(1, len(task_summaries)), 4),
        "k0_solve_rate_in_search": round(n_k0_solved / max(1, len(k0_summaries)), 4) if k0_summaries else None,
        "none_novel_solved_in_search": n_none_solved,
        "by_K": by_k,
        "total_sim_calls": tot_sim,
        "total_transition_calls": tot_trans,
        "total_terminal_calls": tot_term,
        "total_feasible_edges": tot_feas,
        "total_failed_attempts": tot_fail,
        "feasible_edge_yield": round(tot_feas / max(1, tot_trans), 4),
        "verified_plans_per_1000_transitions": round(1000.0 * n_task_solved / max(1, tot_trans), 2),
        "wall_s": wall_s,
        "tree_dirs": [str(out_trees_dir / r["root_id"]) for r in cohort],
        "summaries": summaries,
    }
    (out_trees_dir / "cohort_summary.json").write_text(json.dumps(agg, indent=2))
    return agg
