"""Stage 2 accounting, failure isolation, and exact trainer recovery contracts."""
import copy, dataclasses, hashlib, json, os, pickle, signal, sys, time
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import data as D, distill as DS, env as E, evaluate as EV, journal as J, policy as P
from test_validation_v2 import observation, tree, SCALERS


def test_archive_protection():
    root=Path(__file__).resolve().parents[3]
    manifest=json.loads((Path(__file__).resolve().parents[1]/'reports/stage2/archive_protection.json').read_text())
    assert all(D.sha256_file(root/p)==sha for p,sha in manifest['files'].items())


def test_intent_crash_refuses_dispatch_and_resume(tmp_path):
    t=tree();original=t.env.transition
    def crash(*args):raise RuntimeError('simulated process crash')
    t.env.transition=crash
    with pytest.raises(RuntimeError,match='simulated'):
        t.run_search('fixture',iterations=4,max_sim_calls=12,save_dir=tmp_path)
    starts=[r for r in J.read_events(tmp_path) if r['event']=='started']
    ends=[r for r in J.read_events(tmp_path) if r['event']=='finished']
    assert len(starts)==2 and len(ends)==1
    assert (tmp_path/'ACTIVE_QUERY.json').exists() and (tmp_path/'IN_FLIGHT').exists()
    with pytest.raises(ValueError,match='in-flight'):tree().resume(tmp_path)
    with pytest.raises(ValueError,match='Unreconciled'):
        J.QueryJournal(tmp_path).start(3,'transition',b'parent',{})
    assert hashlib.sha256((tmp_path/starts[-1]['parent_blob']).read_bytes()).hexdigest()==starts[-1]['parent_blob_sha256']


def test_clean_checkpoint_time_and_result_integrity(tmp_path):
    t=tree();save=t.save_tree;captured=[]
    def capture(*args,**kwargs):
        save(*args,**kwargs)
        with (tmp_path/'checkpoint.pkl').open('rb') as f:captured.append(pickle.load(f))
    t.save_tree=capture
    t.run_search('fixture',iterations=3,max_sim_calls=20,save_dir=tmp_path)
    assert captured[0]['cumulative_wall_s']>0 and captured[0]['cumulative_cpu_s']>0
    assert all(b['cumulative_wall_s']>=a['cumulative_wall_s'] for a,b in zip(captured,captured[1:]))
    J.certify_journal(tmp_path,t.sim_transition_calls+t.sim_terminal_calls)
    result=next(tmp_path.glob('query_*.pkl'))
    # Choose a completed result rather than a parent blob.
    result=tmp_path/next(r['result_blob'] for r in J.read_events(tmp_path) if r['event']=='finished')
    result.write_bytes(b'corruption')
    with pytest.raises(ValueError,match='checksum'):tree().resume(tmp_path)


def test_external_per_query_watchdog_ignores_alarm_and_term(tmp_path):
    import multiprocessing as mp
    ctx=mp.get_context('fork');ready=ctx.Event()
    def worker():
        os.setsid();signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGALRM,lambda *_:None)
        signal.alarm(3600)
        J.QueryJournal(tmp_path).start(1,'terminal',b'state',{'root_id':'fixture'})
        ready.set();time.sleep(10)
    proc=ctx.Process(target=worker);proc.start();assert ready.wait(2)
    assert J.wait_for_child(proc,3,grace_s=.05,directory=tmp_path,query_wall_s=.1)
    log=json.loads((tmp_path/'WATCHDOG_ACCOUNTING.json').read_text())
    assert log['reason']=='SINGLE_QUERY_WALL_LIMIT' and log['wall_s']<2
    assert log['reaped_child_cpu_s']>=0 and not proc.is_alive()
    assert len(J.read_events(tmp_path))==1


def test_full_trainer_exact_resume(tmp_path):
    t=tree();t.run_search('fixture',iterations=8,max_sim_calls=60)
    extracted=DS.extract_distillation_data_from_tree(t.nodes,'2d',SCALERS,observation_schema=P.O1)
    init=P.DiscoPolicyNet('2d',16)
    ck=tmp_path/'init.pt';P.save_checkpoint(dict(domain='2d',hidden=16,scalers=SCALERS,state_dict=init.state_dict()),ck)
    kw=dict(dom='2d',extracted=extracted,init_policy_ckpt=ck,epochs=4,batch_size=8,device='cpu',checkpoint_rule='fixed_epochs')
    full=DS.distill_policy_and_value(**kw,out_dir=tmp_path/'full')
    DS.distill_policy_and_value(**kw,out_dir=tmp_path/'resumed',stop_after_epochs=2)
    resumed=DS.distill_policy_and_value(**kw,out_dir=tmp_path/'resumed',resume=True)
    assert full['policy_curve']==resumed['policy_curve'] and full['value_curve']==resumed['value_curve']
    for name in ['policy.pt','value.pt']:
        a=torch.load(tmp_path/'full'/name,weights_only=False);b=torch.load(tmp_path/'resumed'/name,weights_only=False)
        for k,v in a['state_dict'].items():torch.testing.assert_close(v,b['state_dict'][k],rtol=0,atol=0)
    with pytest.raises(ValueError,match='configuration'):
        DS.distill_policy_and_value(**{**kw,'lr':.002},out_dir=tmp_path/'resumed',resume=True)


def test_stop_only_policy_and_common_value_initialization(tmp_path):
    t=tree();t.run_search('fixture',iterations=8,max_sim_calls=60)
    init=P.DiscoPolicyNet('2d',16);ck=tmp_path/'init.pt'
    P.save_checkpoint(dict(domain='2d',hidden=16,scalers=SCALERS,state_dict=init.state_dict()),ck)
    extracted=DS.extract_distillation_data_from_tree(t.nodes,'2d',SCALERS)
    extracted['policy_dst_rows']=[]
    extracted['policy_obj_rows']=[r for r in extracted['policy_obj_rows'] if r['is_stop']]
    rep=DS.distill_policy_and_value('2d',extracted,ck,epochs=1,device='cpu',out_dir=tmp_path/'stop',checkpoint_rule='fixed_epochs')
    assert rep['n_policy_dst_rows']==0 and rep['policy_curve'][0]['train_dst_ce'] is None
    pol,_=P.load_policy_checkpoint(rep['policy_ckpt'],'cpu');assert pol.obj_trained
    loss=rep['policy_curve'][0]['val_total_ce'];assert np.isfinite(loss)


def test_guard_catches_physical_call_even_if_model_catches_error():
    @E.selection_only
    def buggy():
        try:E.RepairEnv('2d').reset('fixture')
        except RuntimeError:pass
        return {}
    with pytest.raises(RuntimeError,match='counter violation'):buggy()


def test_mixed_domain_and_bad_value_evidence_refused():
    with pytest.raises(ValueError,match='Mixed-domain'):
        P.PolicyProposalWrapper('2d',P.DiscoPolicyNet('3d',16),SCALERS,'cpu')
    net=P.DiscoValueNet('2d',16);obs=observation()
    tok,mask,ctx,_=P.extract_scene_object_tokens('2d',obs,SCALERS)
    args=[torch.tensor(x[None]) for x in (tok,mask,ctx)]
    with pytest.raises(ValueError,match='decided'):
        net.weighted_bce_loss(*args,torch.tensor([1]),torch.tensor([5]),torch.tensor([0.]),torch.tensor([0.]))
    with pytest.raises(ValueError,match='action'):
        net.forward_logits(*args,torch.tensor([1]),torch.tensor([64]))
    loss,_=net.weighted_bce_loss(*args,torch.tensor([20]),torch.tensor([64]),torch.tensor([1.]),torch.tensor([1.]))
    loss.backward();assert torch.isfinite(net.q_head[-1].weight.grad).all() and net.q_head[-1].weight.grad.abs().sum()>0


def test_watchdog_monitor_error_cancels_only_own_child(tmp_path):
    import multiprocessing as mp
    ctx=mp.get_context('fork');ready=ctx.Event()
    def worker():
        os.setsid();signal.signal(signal.SIGTERM,signal.SIG_IGN);ready.set();time.sleep(10)
    child=ctx.Process(target=worker);child.start();assert ready.wait(2)
    # Malformed active metadata deterministically emulates a parent-monitor failure.
    (tmp_path/'ACTIVE_QUERY.json').write_text('{bad')
    with pytest.raises(RuntimeError,match='cancelled and charged'):
        J.wait_for_child(child,3,grace_s=.05,directory=tmp_path,query_wall_s=.1)
    assert not child.is_alive()
    assert json.loads((tmp_path/'WATCHDOG_ACCOUNTING.json').read_text())['reason']=='MONITOR_ERROR'
