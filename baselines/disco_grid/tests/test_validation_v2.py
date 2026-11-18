"""Analytical fixtures: no real teacher calls, data mounts, or CUDA required."""
import copy
import dataclasses
import math
import pickle
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import data as D
import distill as DS
import env as E
import evaluate as EV
import mcts as M
import policy as P


def observation(dom="2d"):
    R, C = D.GRID_SHAPE[dom]
    xy = {str(c): list(P.cell_xy_tuple(dom, c)) for c in range(R * C)}
    return E.LearnerObservation("fixture", dom, ["t0", "a", "b", "c"], [0, 1, 2, 3],
        [xy[str(i)] for i in range(4)], [[.02, .02, .04, 0.]] * 4,
        0, 4, xy["4"], [-.14, .32], [0.] * (9 if dom == "2d" else 19),
        list(range(R*C)), xy, [False]*4, 3, [1, 2, 3], [5, 6, 7, 8],
        q_t_optional=[0.] * (3 if dom == "2d" else 7))


SCALERS = {"mean": [0.]*14, "std": [1.]*14}


@pytest.mark.parametrize("dom,nq", [("2d", 3), ("3d", 7)])
def test_q_tensor_visibility_and_scores(dom, nq):
    torch.manual_seed(0)
    a = observation(dom)
    b = dataclasses.replace(a, q_t_optional=[.5] * nq)
    for extractor, args in ((P.extract_query_features, (1, SCALERS)),
                            (P.extract_scene_object_tokens, (SCALERS,))):
        olda = extractor(dom, a, *args)
        oldb = extractor(dom, b, *args)
        for x, y in zip(olda, oldb):
            np.testing.assert_array_equal(x, y)
        newa = extractor(dom, a, *args, observation_schema=P.O1)
        newb = extractor(dom, b, *args, observation_schema=P.O1)
        assert not np.array_equal(newa[2], newb[2])
        assert newa[2].shape[-1] == olda[2].shape[-1] + 3*nq
        assert np.max(np.abs(newb[2][-3*nq:])) <= 1
        np.testing.assert_array_equal(newb[2][-nq:], np.ones(nq))
    missing = dataclasses.replace(a, q_t_optional=None)
    np.testing.assert_array_equal(P.proprio_features(dom, missing, P.O1), np.zeros(3*nq))
    pol = P.DiscoPolicyNet(dom, h=16, observation_schema=P.O1)
    pol.obj_trained = True
    val = P.DiscoValueNet(dom, h=16, observation_schema=P.O1)
    w = P.PolicyProposalWrapper(dom, pol, SCALERS, device="cpu", mode="distilled", value_model=val)
    assert not np.array_equal(w.score_actions_q(a, [(1,5), "STOP"]), w.score_actions_q(b, [(1,5), "STOP"]))
    assert w.action_distribution(a)["stop_prob"] != w.action_distribution(b)["stop_prob"]
    # Destination task branch starts zero; make a controlled nonzero learned branch.
    with torch.no_grad():
        pol.dst_enc.task_mlp[-1].weight.fill_(.1)
    fa = P.extract_query_features(dom, a, 1, SCALERS, observation_schema=P.O1)
    fb = P.extract_query_features(dom, b, 1, SCALERS, observation_schema=P.O1)
    def dst(fs):
        return pol.forward_dst(*(torch.as_tensor(x[None]) for x in fs)).detach().numpy()
    assert not np.array_equal(dst(fa), dst(fb))
    assert a.obs_hash() != b.obs_hash()
    for q in ([0.]*(nq-1), [float("nan")]*nq):
        with pytest.raises(ValueError):
            P.proprio_features(dom, dataclasses.replace(a, q_t_optional=q), P.O1)


@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_no_q_privilege_open_loop_or_cached_edits(dom, monkeypatch):
    obs = observation(dom)
    edit = E.predict_observation_edit(obs, (1, 5))
    assert edit.q_t_optional is None
    forged = dataclasses.replace(edit, q_t_optional=obs.q_t_optional)
    with pytest.raises(ValueError, match="predicted"):
        P.extract_scene_object_tokens(dom, forged, SCALERS, P.O1)
    p = P.DiscoPolicyNet(dom, h=16, observation_schema=P.O1)
    wrap = P.PolicyProposalWrapper(dom, p, SCALERS, "cpu")
    with pytest.raises(ValueError, match="open-loop"):
        EV.predict_open_loop_sequence({}, dom, wrap)
    # Poison physical entry points: O0 must complete using learner inputs alone.
    def forbidden(*args, **kwargs):
        raise AssertionError("Physical call before commitment")
    for method in ("reset", "transition", "terminal_query"):
        monkeypatch.setattr(E.RepairEnv, method, forbidden)
    inp = {"ids":obs.ids, "cells0":obs.cells, "xy0":obs.xy, "attrs":obs.attrs,
           "tid":0, "goal_cell":4, "goal":obs.goal_xy, "base":obs.base_xy,
           "ctx":obs.ctx, "legal_cells":obs.legal_cells, "cell_xy":obs.cell_xy}
    row = {"root_id":"fixture", "inputs":inp, "split":"val", "K_legacy":"3", "masks":{}}
    w0 = P.PolicyProposalWrapper(dom, None, SCALERS, "cpu", "uniform")
    out = EV.predict_open_loop_sequence(row, dom, w0, use_value=False)
    assert out["planner_calls_during_selection"] == 0
    assert D.validate_repair_sequence(inp, dom, out["seq"]) == []


@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_checkpoint_versions_and_explicit_transfer(tmp_path, dom):
    torch.manual_seed(3)
    old = P.DiscoPolicyNet(dom, h=16)
    path = tmp_path / "old.pt"
    torch.save({"domain":dom, "hidden":16, "state_dict":old.state_dict(), "scalers":SCALERS}, path)
    loaded, _ = P.load_policy_checkpoint(path, "cpu")
    for k, v in old.state_dict().items():
        torch.testing.assert_close(v, loaded.state_dict()[k], rtol=0, atol=0)
    new, ck = P.load_policy_checkpoint(path, "cpu", P.O1)
    assert ck["observation_schema"] == P.O1
    a = P.extract_scene_object_tokens(dom, observation(dom), SCALERS)
    b = P.extract_scene_object_tokens(dom, observation(dom), SCALERS, P.O1)
    with torch.no_grad():
        torch.testing.assert_close(old.forward_obj(*(torch.as_tensor(x[None]) for x in a)),
                                   new.forward_obj(*(torch.as_tensor(x[None]) for x in b)), rtol=1e-5, atol=1e-6)
    torch.save({**ck, "obj_trained":True}, tmp_path / "new.pt")
    loaded1, _ = P.load_policy_checkpoint(tmp_path / "new.pt", "cpu")
    assert loaded1.observation_schema == P.O1
    with pytest.raises(ValueError):
        P.load_policy_checkpoint(tmp_path / "new.pt", "cpu", P.O0)
    v0 = P.DiscoValueNet(dom, 16)
    v1 = P.DiscoValueNet(dom, 16, P.O1)
    with pytest.raises(ValueError):
        P.PolicyProposalWrapper(dom, old, SCALERS, "cpu", value_model=v1)
    P.transfer_o0_weights(v1, v0.state_dict())
    torch.save({"domain":dom, "hidden":16, "observation_schema":P.O1, "state_dict":v1.state_dict()}, tmp_path / "v.pt")
    assert DS.load_value_checkpoint(tmp_path / "v.pt", "cpu")[0].observation_schema == P.O1


class ToyEnv:
    domain = "2d"
    calls = 0
    def reset(self, root_id, seed=0):
        return E.FullState(root_id, "2d", seed, 0, [], [0,1,2,3], [False]*4,
                           [], [0.]*3, {"held":None}, {}, "toy-v1")
    def observe(self, state, include_qt=False):
        o = observation()
        o.cells = list(state.cells)
        o.remaining_steps = 3-state.depth
        o.moved_mask = state.moved_mask
        o.eligible_objects = [i for i in (1,2,3) if not state.moved_mask[i]] if state.depth < 3 else []
        o.legal_destinations = [i for i in (5,6,7,8) if i not in state.used_dests]
        o.q_t_optional = state.q_t if include_qt else None
        return o
    clone_or_serialize = staticmethod(pickle.dumps)
    restore = staticmethod(pickle.loads)
    def transition(self, state, act):
        self.calls += 1
        nxt = copy.deepcopy(state)
        nxt.depth += 1
        nxt.prefix.append(act)
        nxt.cells[act[0]] = act[1]
        nxt.used_dests.append(act[1])
        nxt.moved_mask[act[0]] = True
        nxt.q_t = [nxt.depth*.1]*3
        return E.StepResult("EXECUTED", None, "VERIFIED", act, nxt)
    def terminal_query(self, state, evaluate_y_on_x_fail=True):
        self.calls += 1
        z = int(state.depth >= 2)
        return E.StopResult("DECIDED", bool(z), 1, z, z, None, None, "VERIFIED", "VERIFIED")


def tree():
    e = ToyEnv()
    w = P.PolicyProposalWrapper("2d", None, SCALERS, "cpu", "uniform")
    return M.DISCOMCTS(e, w, seed=5, expansion_budget_B=2)


@pytest.mark.parametrize("budget", list(range(9)))
def test_hard_search_call_caps(budget):
    t = tree()
    out = t.run_search("fixture", iterations=10, max_sim_calls=budget)
    assert t.env.calls == out["total_sim_calls"] <= budget
    assert out["root_visits"] == out["completed_iterations"]
    for n in t.nodes:
        assert len(n.attempted_actions) == len(set(n.attempted_actions))


def test_resume_exact_rng_visits_labels_and_trace(tmp_path):
    full = tree()
    full.run_search("fixture", iterations=8, max_sim_calls=60)
    part = tree()
    orig = part.backpropagate
    def cancel_after_iteration(leaf):
        orig(leaf)
        part.cancel_requested = True
    part.backpropagate = cancel_after_iteration
    part.run_search("fixture", iterations=8, max_sim_calls=60, save_dir=tmp_path)
    resumed = tree()
    resumed.resume(tmp_path)
    resumed.run_search("fixture", iterations=8, max_sim_calls=60)
    assert resumed.iteration_traces == full.iteration_traces
    assert resumed.edge_logs == full.edge_logs
    assert resumed.sim_transition_calls == full.sim_transition_calls
    assert resumed.sim_terminal_calls == full.sim_terminal_calls
    assert DS.compute_leaf_stats(resumed.nodes) == DS.compute_leaf_stats(full.nodes)
    with pytest.raises(ValueError, match="configuration"):
        resumed.run_search("fixture", iterations=9, max_sim_calls=60)
    (tmp_path / "IN_FLIGHT").write_text("1")
    with pytest.raises(ValueError, match="in-flight"):
        tree().resume(tmp_path)


def test_stop_evidence_unique_and_q_parent_state():
    t = tree()
    t.run_search("fixture", iterations=8, max_sim_calls=60)
    stats = DS.compute_leaf_stats(t.nodes)
    for n in t.nodes:
        if n.visit_count == 0:
            assert n.node_id not in stats
    out = DS.extract_distillation_data_from_tree(t.nodes, "2d", SCALERS, observation_schema=P.O1)
    stop = [r for r in out["value_rows"] if r["is_stop"]]
    assert {r["value_target"] for r in stop} == {0.,1.}
    assert all(r["n_visited_leaves"] == 1 and r["evidence_weight"] == math.log(2) for r in stop)
    assert all(r["scene_ctx"].shape[-1] == 64 + P.task_dim("2d", P.O1) for r in out["value_rows"])
    # Success leaf return telescopes to 1-kappa(root), ancestor Q is mean traced return.
    for n in t.nodes[1:]:
        if n.is_stop_node:
            assert t.path_return(n) == pytest.approx(1.-t.nodes[0].progress_kappa)
    for node in t.nodes[1:]:
        returns = []
        for trace in t.iteration_traces:
            cur = t.nodes[trace["leaf_id"]]
            path = []
            while cur.parent_id is not None:
                path.append(cur.node_id)
                cur = t.nodes[cur.parent_id]
            if node.node_id in path:
                returns.append(trace["path_return"])
        if returns:
            assert node.Q == pytest.approx(np.mean(returns))


def test_unknown_noop_is_censored_and_denominators_explicit():
    row = {"root_id":"r", "seed":0, "K_legacy":"1", "masks":{"eval_task":True,
        "eval_repair":False, "eval_noop":False, "eval_abstain":False}, "status":"NOOP", "verified":None}
    met = EV.compute_benchmark_metrics([row])
    assert met["n_task_unresolved"] == 1
    assert met["task_success"] == 0 and met["task_success_upper"] == 1
    assert met["n_distinct_task_roots"] == 1


def test_paired_ci_rejects_unmatched_roots_and_seeds():
    def row(root,seed,success):
        return {"root_id":root,"domain":"2d","seed":seed,"masks":{"eval_task":True},
                "status":"REPAIR","verified":success}
    a=[row("a",0,1),row("a",1,0),row("b",0,0),row("b",1,1)]
    b=[row("a",0,0),row("a",1,0),row("b",0,0),row("b",1,0)]
    ci=EV.paired_root_bootstrap_ci(a,b,require_same_seeds=True)
    assert ci["delta"] == .5 and ci["ci95"] == [.5,.5] and ci["n_roots"]==2
    with pytest.raises(ValueError,match="cohorts"):
        EV.paired_root_bootstrap_ci(a,b[:2])
    with pytest.raises(ValueError,match="seed coverage"):
        EV.paired_root_bootstrap_ci(a,b[::2],require_same_seeds=True)
    with pytest.raises(ValueError,match="Duplicate"):
        EV.paired_root_bootstrap_ci(a,a+[a[0]])


def test_closed_loop_observes_only_executed_q(monkeypatch):
    env=ToyEnv()
    net=P.DiscoPolicyNet("2d",16,P.O1)
    w=P.PolicyProposalWrapper("2d",net,SCALERS,"cpu","distilled")
    seen=[]
    def decide(obs,*args,**kwargs):
        seen.append(obs.q_t_optional)
        depth=3-obs.remaining_steps
        sel=[(1,5),(2,6),"STOP"][depth]
        return {"selected":sel,"ranked_candidates":[sel]}
    monkeypatch.setattr(EV,"select_action_model_only",decide)
    o=observation()
    row={"root_id":"fixture","split":"val","K_legacy":"2","masks":{},
         "inputs":{"cells0":o.cells,"cell_xy":o.cell_xy}}
    result=EV.run_closed_loop_episode(env,row,w)
    assert seen == [[0.]*3,[.1]*3,[.2]*3]
    assert result["verified"]==1 and result["seq"]==[[1,5],[2,6]]


def test_q_aware_distillation_atomic_checkpoints_and_no_overwrite(tmp_path):
    t=tree();t.run_search("fixture",iterations=8,max_sim_calls=60)
    extracted=DS.extract_distillation_data_from_tree(t.nodes,"2d",SCALERS,observation_schema=P.O1)
    extracted["domain"]="2d"
    init=P.DiscoPolicyNet("2d",16)
    ck=tmp_path/"init.pt"
    torch.save({"domain":"2d","hidden":16,"scalers":SCALERS,"state_dict":init.state_dict()},ck)
    out=tmp_path/"train"
    result=DS.distill_policy_and_value("2d",extracted,ck,epochs=2,batch_size=64,device="cpu",
                                      out_dir=out,checkpoint_rule="fixed_epochs")
    assert all(np.isfinite(r["train_dst_ce"]) for r in result["policy_curve"])
    p,_=P.load_policy_checkpoint(out/"policy.pt","cpu")
    v,_=DS.load_value_checkpoint(out/"value.pt","cpu")
    assert p.observation_schema==v.observation_schema==P.O1
    assert not list(out.glob("*.tmp"))
    assert not torch.equal(p.scene_ctx_mlp[0].weight[:,-9:],torch.zeros_like(p.scene_ctx_mlp[0].weight[:,-9:]))
    with pytest.raises(FileExistsError):
        DS.distill_policy_and_value("2d",extracted,ck,device="cpu",out_dir=out)


def test_stop_calibration_is_val_family_disjoint():
    examples=[{"root_id":str(i),"family_id":str(i//2),"split":"val",
               "q_stop":.1 if i%2 else .3,"z_stop":int(i%2==0)} for i in range(40)]
    out=EV.fit_root_stop_calibration(examples)
    assert not set(out["fit_family_ids"]) & set(out["audit_family_ids"])
    assert out["rule"]["root_stop_temperature"]>0
    assert out["audit_calibrated"]["nll"] < out["audit_raw"]["nll"]
    with pytest.raises(ValueError,match="VALIDATION"):
        EV.fit_root_stop_calibration([{**r,"split":"test"} for r in examples])


def test_administrative_limits_are_censored_without_teacher_relabel():
    raw=E.StepResult("PHYSICALLY_FAILED","TIMEOUT","UNKNOWN_BUDGET",(1,5),None)
    assert E.censor_administrative_step(raw).status=="UNRESOLVED"
    assert raw.status=="PHYSICALLY_FAILED"  # archive object remains untouched
    rawstop=E.StopResult("DECIDED",False,0,1,0,"connector","TIMEOUT","UNKNOWN_BUDGET","VERIFIED")
    censored=E.censor_administrative_stop(rawstop)
    assert censored.x_terminal is None and censored.z_outcome is None and censored.status=="UNRESOLVED"
    assert rawstop.x_terminal==0 and rawstop.z_outcome==0
    # A separate decided target failure still decides Z=0 with X unknown.
    both=dataclasses.replace(rawstop,y_target=0,y_status="NO_PLAN_FOUND")
    assert E.censor_administrative_stop(both).z_outcome==0
    n=M.MCTSNode(0,None,[],0,b"","h",observation(),None,visit_count=1,
                 stop_evaluated=True,stop_result=rawstop,terminal_z=0)
    assert DS.compute_leaf_stats([n])[0]==(0,0)
    assert not DS.extract_distillation_data_from_tree([n],"2d",SCALERS)["value_rows"]


def test_external_watchdog_survives_teacher_alarm_replacement():
    import multiprocessing as mp
    import signal
    import time
    from collect import wait_for_child
    ctx=mp.get_context("fork")
    ready=ctx.Event()
    def teacher():
        signal.signal(signal.SIGALRM,lambda *_:None)
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        signal.alarm(3600)
        ready.set()
        time.sleep(10)
    child=ctx.Process(target=teacher)
    child.start()
    assert ready.wait(timeout=2)
    start=time.monotonic()
    assert wait_for_child(child,.05,.05)
    assert not child.is_alive() and time.monotonic()-start<2


def test_physical_query_journal_counts_and_saves_exact_states(tmp_path):
    import json
    t=tree();summary=t.run_search("fixture",iterations=3,max_sim_calls=12,save_dir=tmp_path)
    rows=[json.loads(x) for x in (tmp_path/"queries.jsonl").read_text().splitlines()]
    started=[r for r in rows if r["event"]=="started"]
    finished=[r for r in rows if r["event"]=="finished"]
    assert len(started)==len(finished)==summary["total_sim_calls"]
    assert [r["query_id"] for r in started]==list(range(1,len(started)+1))
    for row in finished:
        with (tmp_path/row["result_blob"]).open("rb") as f:result=pickle.load(f)
        assert result.status==row["status"]
        if row["kind"]=="transition":
            assert result.next_state.prefix[-1]==tuple(row["action"])


class _Crash(BaseException):
    pass


@pytest.mark.parametrize("crash_at", [3, 7, 11])
def test_reconcile_inflight_replays_finished_reissues_uncertain_once(tmp_path, crash_at):
    import json
    full = tree(); full.run_search("fixture", iterations=8, max_sim_calls=60)
    part = tree()
    for meth in ("transition", "terminal_query"):
        f = getattr(part.env, meth)
        def wrapped(*a, _f=f, **k):
            if part.env.calls + 1 == crash_at:
                raise _Crash()                                # hard kill DURING the physical call (journal 'started' written)
            return _f(*a, **k)
        setattr(part.env, meth, wrapped)
    with pytest.raises(_Crash):
        part.run_search("fixture", iterations=8, max_sim_calls=60, save_dir=tmp_path)
    assert (tmp_path / "IN_FLIGHT").exists()
    with pytest.raises(ValueError, match="in-flight"):
        tree().resume(tmp_path)
    rec = M.reconcile(tmp_path)
    if not (tmp_path / "checkpoint.pkl").exists() and rec["status"] == "CLOSED_NO_CHECKPOINT":
        with pytest.raises(ValueError, match="closed"):
            tree().resume(tmp_path)
        return
    assert rec["status"] == "RECONCILED_TO_CHECKPOINT" and len(rec["uncertain"]) == 1 and rec["labels_inferred"] == 0
    resumed = tree(); resumed.resume(tmp_path)
    resumed.run_search("fixture", iterations=8, max_sim_calls=60, save_dir=tmp_path)
    assert resumed.edge_logs == full.edge_logs and DS.compute_leaf_stats(resumed.nodes) == DS.compute_leaf_stats(full.nodes)
    total = full.sim_transition_calls + full.sim_terminal_calls
    assert resumed.sim_transition_calls + resumed.sim_terminal_calls == total + 1          # uncertain call charged twice
    phys_after = resumed.env.calls
    assert phys_after == total - rec["charged_calls_at_checkpoint"] - len(rec["finished_orphans"])   # orphans reused, not re-executed
    rows = [json.loads(x) for x in (tmp_path / "queries.jsonl").read_text().splitlines()]
    assert sum(1 for r in rows if r.get("reissue_after_reconcile")) == 1
    assert len([e for e in resumed.reconcile_log if e["event"] == "replayed_finished_orphan"]) == len(rec["finished_orphans"])


def test_reconcile_without_checkpoint_is_closed(tmp_path):
    (tmp_path / "IN_FLIGHT").write_text("0")
    (tmp_path / "w.npz").write_bytes(b"witness")
    rec = M.reconcile(tmp_path)
    assert rec["status"] == "CLOSED_NO_CHECKPOINT" and not rec["resumable"] and rec["evidence_inventory"]
    with pytest.raises(ValueError, match="closed"):
        tree().resume(tmp_path)


@pytest.mark.parametrize("cut", [1, 3])
def test_distillation_resume_restores_optimizer_rng_exactly(tmp_path, cut):
    t = tree(); t.run_search("fixture", iterations=8, max_sim_calls=60)
    ex = DS.extract_distillation_data_from_tree(t.nodes, "2d", SCALERS, observation_schema=P.O0); ex["domain"] = "2d"
    torch.manual_seed(0)
    ck = tmp_path / "init.pt"
    torch.save({"domain": "2d", "hidden": 16, "scalers": SCALERS, "state_dict": P.DiscoPolicyNet("2d", 16).state_dict()}, ck)
    kw = dict(epochs=4, batch_size=8, device="cpu", checkpoint_rule="fixed_epochs")
    DS.distill_policy_and_value("2d", ex, ck, out_dir=tmp_path / "full", **kw)
    DS.distill_policy_and_value("2d", ex, ck, out_dir=tmp_path / "cut", stop_after_epochs=cut, **kw)
    with pytest.raises(FileExistsError):
        DS.distill_policy_and_value("2d", ex, ck, out_dir=tmp_path / "cut", **kw)
    DS.distill_policy_and_value("2d", ex, ck, out_dir=tmp_path / "cut", resume=True, **kw)
    for f in ("policy.pt", "value.pt"):
        a = torch.load(tmp_path / "full" / f, weights_only=False)["state_dict"]
        b = torch.load(tmp_path / "cut" / f, weights_only=False)["state_dict"]
        assert all(torch.equal(a[k], b[k]) for k in a), f
