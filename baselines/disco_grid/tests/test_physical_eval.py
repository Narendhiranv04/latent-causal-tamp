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


def test_reference_motion_excludes_unexecuted_failed_plan(tmp_path):
    import numpy as np
    toy=ToyEnv();st=toy.reset('fixture');j=J.QueryJournal(tmp_path)
    a=toy.transition(st,(1,5));a.witness_ids=['abc'];path=tmp_path/'witnesses/witnesses/ab/abc.npz';path.parent.mkdir(parents=True)
    np.savez(path,q=np.array([[0.,0.,0.],[1.,0.,0.],[1.,2.,0.]]))
    j.start(1,'transition',E.RepairEnv.clone_or_serialize(st),dict(parent_state_hash=st.state_hash()));j.finish(a)
    j.start(2,'transition',E.RepairEnv.clone_or_serialize(a.next_state),dict(parent_state_hash=a.next_state.state_hash()))
    j.finish(E.StepResult('PHYSICALLY_FAILED','GRASP_FAILED','GRASP_FAILED',(2,6),None,witness_ids=['unexecuted_full_plan']))
    cost=PE.reference_motion_cost(tmp_path)
    assert cost['reference_joint_path_rad']==3. and cost['coverage']=='PARTIAL_EXECUTION_PREFIX'
    assert len(cost['sources'])==1 and not cost['missing_witnesses']


def test_release_rule_selection_uses_val_only_and_fixed_missing_denominator():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reports/stage2'))
    import release_evaluation as RE
    jobs=[];outcomes=[]
    for dom in ('2d','3d'):
        for eta in RE.ETAS:
            for arm in ('O0_P2Q2','O0_closed_P2Q2','O1_closed_P2Q2'):
                for k in ('0','1','NONE'):
                    jid=f'{dom}_{eta}_{arm}_{k}'
                    jobs.append(dict(id=jid,domain=dom,split='val',arm=arm,K_legacy=k,rule={'abstain_eta':eta}))
                    status='NOOP' if k=='0' else 'ABSTAIN' if k=='NONE' and eta else 'REPAIR'
                    outcomes.append(dict(job_id=jid,status=status,verified=int(k!='NONE')))
    selected=RE.select_eta(jobs,outcomes)
    assert selected['selected_eta']=={'2d':.08,'3d':.08}
    abstained_tasks=[dict(row,status='ABSTAIN',verified=0) if row['job_id'].endswith('_1') else row for row in outcomes]
    with pytest.raises(RuntimeError,match='insufficient decided'):
        RE.select_eta(jobs,abstained_tasks)
    with pytest.raises(ValueError,match='VAL'):RE.select_eta([dict(jobs[0],split='test')],[])
    with pytest.raises(PermissionError):RE.validate({'status':'REQUESTED_NOT_AUTHORIZED'})
    with pytest.raises(PermissionError,match='physical-call ceiling'):
        RE.validate(dict(status='APPROVED',scope='DISCO_RELEASE_EVALUATION',authorization_text='fixture',host='gvlab',workers=1,gpu=False,cpu_threads=1,global_adapter_call_ceiling=5524))


def test_release_analysis_retains_missing_roots_and_distinguishes_novel_repairs(tmp_path):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reports/stage2'))
    import analyze_evaluation as AE
    release=tmp_path/'release';release.mkdir();prep=tmp_path/'prep';prep.mkdir()
    (prep/'checkpoint_manifest.json').write_text('[]')
    (release/'APPROVED_ENVELOPE.json').write_text(json.dumps(dict(preparation=str(prep))))
    jobs=[];outcomes=[]
    for index,(k,status) in enumerate([('1','REPAIR'),('NONE','NOOP'),('NONE','REPAIR'),('2',None)]):
        root=f'fixture{index}';jid=f'job{index}'
        jobs.append(dict(id=jid,root_id=root,family_id=root,K_legacy=k,seed=0,domain='2d',split='test',protocol='open_loop',arm='O0_P2Q2',
            rule={'abstain_eta':0.},schema=P.O0,policy_sha256='fixture',root_sha256='fixture',input_sha256='fixture',
            prediction=dict(status=status,seq=[] if status=='NOOP' else [[1,5]])))
        if status:outcomes.append(dict(job_id=jid,root_id=root,seed=0,domain='2d',status=status,verified=1,x=1,y=1,seq=[] if status=='NOOP' else [[1,5]]))
    (release/'test_2d_jobs.json').write_text(json.dumps(dict(jobs=jobs)))
    phase=release/'test_2d';phase.mkdir();(phase/'outcomes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in outcomes))
    out=tmp_path/'analysis';AE.analyze(release,out)
    metrics=json.loads((out/'FINAL_METRICS.json').read_text())['metrics']['test|2d|open_loop|O0_P2Q2|0.0']
    assert metrics['overall']['n_expected_predictions']==4 and metrics['overall']['n_not_run']==1
    assert metrics['overall']['success_rate']==.75
    assert metrics['deployment_diagnostics']['n_novel_verified_repairs_NONE']==1
    assert metrics['deployment_diagnostics']['n_verified_original_target_NONE']==1
    assert 'NOT_RUN' in (out/'CENSORING_LEDGER.csv').read_text()


def test_coverage_counts_physical_stop_once_not_absorbing_child(tmp_path):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reports/stage2'))
    import summarize_campaign as SC
    campaign=tmp_path/'campaign';campaign.mkdir()
    root=dict(root_id='fixture',family_id='f',K_legacy='0')
    (campaign/'manifest.json').write_text(json.dumps(dict(source_commit='fixture',cohorts=dict(domains={'2d':{'train_roots':[root]},'3d':{'train_roots':[]}}))))
    td=campaign/'trees/2d/R0/fixture/fixture';td.mkdir(parents=True)
    nodes=[dict(node_id=0,is_stop_node=False,depth=0,prefix=[],stop_evaluated=True,terminal_z=1),
           dict(node_id=1,is_stop_node=True,depth=1,prefix=[],stop_evaluated=True,terminal_z=1)]
    (td/'tree.json').write_text(json.dumps(dict(nodes=nodes,summary=dict(root_id='fixture'))))
    out=tmp_path/'summary';SC.summarize(campaign,out)
    rows=json.loads((out/'training_coverage.json').read_text())['records']
    assert rows[0]['checkpoint_terminal_counts']=={'depth0|Z1':1}


def test_root_stop_diagnostics_require_independent_probe_not_legacy_K():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reports/stage2'))
    import analyze_evaluation as AE
    model=dict(id='model',split='test',domain='2d',root_id='r',family_id='f',seed=0,arm='O0_P2Q2',use_value=True,
        rule={'abstain_eta':0.},prediction={'selection_trace':[{'decision':dict(n_candidates=2,best_reloc_score=.3,stop_score=.2,selected='STOP')}]})
    probe=dict(model,id='probe',arm='root_stop_diagnostic',diagnostic_only=True)
    assert AE.root_stop_diagnostics([model,probe],[])['examples']==[]
    result=AE.root_stop_diagnostics([model,probe],[dict(job_id='probe',verified=1)])
    stats=result['summaries']['test|2d|O0_P2Q2']
    assert stats['n']==1 and stats['n_positive']==1 and stats['brier']==pytest.approx(.64)
    assert stats['stop_precision']==1. and stats['stop_recall']==1.


def test_artifact_inventory_rejects_changed_completed_checkpoint(tmp_path):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reports/stage2'))
    import artifact_index as AI
    root=tmp_path/'campaign';fit=root/'training/fixture';fit.mkdir(parents=True)
    checkpoint=fit/'policy.pt';checkpoint.write_bytes(b'opaque fixture; never deserialized')
    (fit/'COMPLETE.json').write_text(json.dumps({'checkpoint_sha256':{str(checkpoint):AI.digest(checkpoint)}}))
    ledger=root/'COMPLETE.json';ledger.write_text('{}')
    report=tmp_path/'index.json';result=AI.index(root,ledger,report)
    assert result['completed_checkpoint_checks']==1
    checkpoint.write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash mismatch'):AI.index(root,ledger,tmp_path/'tampered_index.json')


def test_3d_coverage_control_cannot_use_recovered_cycle_as_clean(tmp_path):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reports/stage2'))
    import prepare_evaluation as PRE
    for name in ('3d_P1Q1','3d_P2Q2'):
        directory=tmp_path/'training'/name;directory.mkdir(parents=True);(directory/'COMPLETE.json').write_text('{}')
    with pytest.raises(ValueError,match='genuine clean-only'):PRE.model_configs(tmp_path,'3d')
    control=tmp_path/'training/3d_P2Q2_strictclean';control.mkdir();(control/'COMPLETE.json').write_text('{}')
    assert PRE.model_configs(tmp_path,'3d')['O0_P2_clean_onlyQ2'][0]==control


def test_empty_physical_phase_retains_zero_attempt_accounting(tmp_path,monkeypatch):
    jobs=tmp_path/'jobs.json';jobs.write_text(json.dumps({'jobs':[]}))
    envelope=tmp_path/'envelope.json';envelope.write_text(json.dumps(dict(status='APPROVED',scope='DISCO_PHYSICAL_EVALUATION',
        authorization_text='analytical fixture only',host='gvlab',workers=1,gpu=False,split='val',jobs_sha256=D.sha256_file(jobs),
        cpu_s=1,active_wall_s=1,adapter_calls=0,disk_gib=1)))
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES','');monkeypatch.setenv('DISCO_SOURCE_COMMIT','analytical-fixture');monkeypatch.setattr(D,'DISCO_ROOT',tmp_path)
    monkeypatch.setattr(PE.C,'require_headroom',lambda:{})
    out=tmp_path/'stage2/empty';PE.run(jobs,envelope,out)
    cost=json.loads((out/'ACCOUNTING.json').read_text())
    assert cost['n_attempted']==cost['adapter_calls']==0 and cost['cpu_s']>=0
