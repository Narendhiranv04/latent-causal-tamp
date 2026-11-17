"""Evaluation authorization and journaling checks, with no real physical calls."""
import dataclasses, json, os, sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import data as D, env as E, journal as J, physical_eval as PE, policy as P
from test_validation_v2 import ToyEnv


def test_train_approval_cannot_execute_evaluation(tmp_path):
    jobs=tmp_path/'jobs.json';jobs.write_text(json.dumps({'jobs':[]}))
    with pytest.raises(PermissionError,match='Separate explicit evaluation'):
        PE.validate_execution(jobs,{'id':'E16-v1','status':'APPROVED','scope':'TRAIN'})
    e=dict(status='APPROVED',scope='DISCO_PHYSICAL_EVALUATION',authorization_text='test fixture only',jobs_sha256=D.sha256_file(jobs),host='gvlab',workers=1,gpu=False,split='val')
    assert PE.validate_execution(jobs,e)==[]
    jobs.write_text(json.dumps({'jobs':[dict(id='bad',split='val',protocol='open_loop',schema=P.O1,physics_seed=0,adapter_call_cap=4,query_wall_s=1,trial_wall_s=2)]}))
    e['jobs_sha256']=D.sha256_file(jobs)
    with pytest.raises(ValueError,match='O1 open-loop'):PE.validate_execution(jobs,e)


def test_evidence_wrapper_records_exact_carried_state_and_caps(tmp_path,monkeypatch):
    toy=ToyEnv()
    monkeypatch.setattr(E.RepairEnv,'__init__',lambda self,*a,**kw:setattr(self,'domain','2d'))
    monkeypatch.setattr(E.RepairEnv,'reset',lambda self,*a,**kw:toy.reset(*a,**kw))
    monkeypatch.setattr(E.RepairEnv,'transition',lambda self,*a,**kw:toy.transition(*a,**kw))
    env=PE.EvidenceEnv('2d',tmp_path,2);a=env.reset('fixture');b=env.transition(a,(1,5)).next_state
    assert b.prefix==[(1,5)]
    env.transition(b,(2,6))
    starts=[x for x in J.read_events(tmp_path) if x['event']=='started']
    assert starts[1]['parent_state_hash']==b.state_hash()
    assert E.RepairEnv.restore((tmp_path/starts[1]['parent_blob']).read_bytes()).q_t==b.q_t
    J.certify_journal(tmp_path,2)
    with pytest.raises(RuntimeError,match='ADAPTER_CALL_CAP'):env.transition(b,(3,7))
    assert len(J.read_events(tmp_path))==4


def test_continuation_charges_prior_controller_work_without_new_ceiling():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reports/stage2'))
    import continue_e16 as CE
    costs=CE.charged_totals(dict(cpu_s=3051.,wall_s=3293.,jobs=32),dict(cpu_s=55.,wall_s=8.))
    assert costs['cpu_s']==3106. and costs['wall_s']==3301. and costs['jobs']==32
    assert CE.live_child_cpu()>=0


def test_open_verification_identity_separates_physics_from_model_seed():
    j=dict(protocol='open_loop',prediction={'seq':[[1,5]]},domain='2d',root_id='r',root_sha256='raw',input_sha256='input',teacher_sources={'teacher':'abc'},physics_seed=0,query_wall_s=60,trial_wall_s=300,adapter_call_cap=5,seed=0)
    key=PE.verification_key(j,{'env.py':'sha'})
    assert key==PE.verification_key(dict(j,seed=2),{'env.py':'sha'})
    assert key!=PE.verification_key(dict(j,physics_seed=1),{'env.py':'sha'})
    assert key!=PE.verification_key(dict(j,prediction={'seq':[[1,6]]}),{'env.py':'sha'})
    assert key!=PE.verification_key(j,{'env.py':'changed'})
    assert PE.verification_key(dict(j,protocol='closed_loop'),{'env.py':'sha'}) is None


def test_abstention_is_not_a_physical_decision():
    import evaluate as EV
    roots=[dict(root_id='a',family_id='a',K_legacy='NONE')]
    out=EV.root_level_metrics([dict(root_id='a',seed=0,domain='2d',status='ABSTAIN',verified=0)],roots,seeds=(0,),bootstrap=10)['overall']
    assert out['n_abstentions']==1 and out['n_physically_decided']==0 and out['decided_only'] is None
    assert out['success_rate']==0 and out['n_unresolved_or_unexecuted']==0


def test_paired_missing_trials_keep_frozen_seed_denominator():
    import evaluate as EV
    roots=[dict(root_id='a',family_id='f',K_legacy='1')]
    a=[dict(root_id='a',seed=0,domain='2d',verified=1,status='REPAIR')]
    b=[dict(root_id='a',seed=0,domain='2d',verified=0,status='ABSTAIN'),dict(root_id='a',seed=1,domain='2d',verified=0,status='REPAIR')]
    out=EV.paired_frozen_root_metrics(a,b,roots,seeds=(0,1),bootstrap=10)
    assert out['delta']==.5 and out['unresolved_sensitivity']==[.5,1.] and out['unknown_pair_trials']==1
    assert out['ci95']==[.5,.5]


def test_certified_prefix_does_not_relabel_or_mutate_interruption(tmp_path):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reports/stage2'))
    import recover_prefixes as RP
    from test_validation_v2 import tree
    t=tree();src=tmp_path/'original';t.run_search('fixture',iterations=3,max_sim_calls=20,save_dir=src)
    completed=t.sim_transition_calls+t.sim_terminal_calls
    J.QueryJournal(src).start(completed+1,'terminal',t.nodes[0].state_blob,{'root_id':'fixture'})
    J.atomic_bytes(src/'IN_FLIGHT',b'next iteration interrupted')
    before={str(p.relative_to(src)):D.sha256_file(p) for p in src.iterdir() if p.is_file()}
    record=RP.recover(src,tmp_path/'recovered',J,D)
    assert record['retained_calls']==completed and record['unfinished_queries_not_labelled']==1
    assert record['original_remains_quarantined'] and (src/'IN_FLIGHT').exists()
    assert before=={str(p.relative_to(src)):D.sha256_file(p) for p in src.iterdir() if p.is_file()}
    J.certify_journal(tmp_path/'recovered',completed)
    assert not (tmp_path/'recovered/ACTIVE_QUERY.json').exists()


def test_interrupted_evaluation_needs_returned_proof_not_timeout_label(tmp_path):
    toy=ToyEnv();st=toy.reset('fixture');job=dict(root_id='fixture',domain='2d',protocol='closed_loop',seed=0,K_legacy='1',arm='test',family_id='f',id='job')
    journal=J.QueryJournal(tmp_path);journal.start(1,'transition',E.RepairEnv.clone_or_serialize(st),dict(root_id='fixture',parent_state_hash=st.state_hash()))
    assert PE.reconcile_returned_proof(job,tmp_path) is None
    journal.finish(E.StepResult('UNRESOLVED','TIMEOUT','TIMEOUT',(1,5),None))
    assert PE.reconcile_returned_proof(job,tmp_path) is None
    journal.start(2,'transition',E.RepairEnv.clone_or_serialize(st),dict(root_id='fixture',parent_state_hash=st.state_hash()))
    journal.finish(E.StepResult('PHYSICALLY_FAILED','COLLISION','COLLISION',(1,5),None))
    out=PE.reconcile_returned_proof(job,tmp_path)
    assert out['verified']==0 and out['x']==0 and out['y'] is None and out['recovered_from_durable_query']==2


def test_deployment_cannot_silently_transfer_o0_checkpoint(tmp_path):
    import torch
    from test_validation_v2 import SCALERS
    net=P.DiscoPolicyNet('2d',16)
    path=tmp_path/'o0.pt';torch.save(dict(domain='2d',hidden=16,state_dict=net.state_dict(),scalers=SCALERS),path)
    job=dict(policy=str(path),policy_sha256=D.sha256_file(path),schema=P.O1,domain='2d',mode='distilled',use_value=False)
    with pytest.raises(ValueError,match='Deployment schema mismatch'):PE.load_proposal(job)
