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
    jobs.write_text(json.dumps({'jobs':[dict(id='bad',split='val',protocol='open_loop',schema=P.O1,adapter_call_cap=4,query_wall_s=1,trial_wall_s=2)]}))
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
