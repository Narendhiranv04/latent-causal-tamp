"""Exact extension approval and immutable prior-view tests; no teacher calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import pytest

HERE=Path(__file__).resolve().parents[1]/'reports/stage2';sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('queue_fixture',HERE/'queue_completion_extension.py')
Q=importlib.util.module_from_spec(spec);spec.loader.exec_module(Q)
M=Q.M


def fixture(tmp_path):
    prior=tmp_path/'prior';prior.mkdir()
    pending=[dict(id=f'pending{i}',domain='2d',query_wall_s=60,trial_wall_s=300,adapter_call_cap=4 if i<31 else 3) for i in range(113)]
    limits=dict(additional_cpu_s=43200,additional_active_wall_s=18000,maximum_additional_adapter_calls=370,
        remaining_trials=113,workers=3,host='girish-laptop',gpu=False,ram_gib=4,new_disk_gib=2,
        reserved_physical_cores=2,query_wall_s=60,trial_wall_s=300)
    request=tmp_path/'request.json';M.write(request,dict(limits,global_adapter_ceiling_unchanged=5523,
        jobs=[dict(id=j['id'],job_sha256=hashlib.sha256(json.dumps(j,sort_keys=True).encode()).hexdigest()) for j in pending]))
    approval=tmp_path/'approval.json';M.write(approval,dict(limits,status='APPROVED',scope='DISCO_ONLY_FROZEN_2D_TEST_CPU_EXTENSION',
        authorization_text='Synthetic fixture approval only',request_sha256=M.digest(request),global_adapter_call_ceiling=5523))
    M.write(prior/'APPROVED_ENVELOPE.json',dict(global_adapter_call_ceiling=5523,ceilings={'2d':{'val':3600,'test':10800},'3d':{'val':7200,'test':21600}}))
    M.write(prior/'COMPLETE.json',dict(global_adapter_calls=2000));M.write(prior/'SELECTION_FREEZE.json',dict(selected_eta={'2d':0,'3d':0}))
    for phase in ('val','test'):
        for domain in ('2d','3d'):
            p=prior/f'{phase}_{domain}';p.mkdir()
            jobs=[dict(id='previous_unknown')]+pending if (phase,domain)==('test','2d') else []
            M.write(prior/f'{phase}_{domain}_jobs.json',dict(jobs=jobs))
            (p/'outcomes.jsonl').write_text(json.dumps(dict(job_id='previous_unknown',verified=None))+'\n' if jobs else '')
            M.write(p/'ACCOUNTING.json',dict(cpu_s=10720,active_wall_s=2847,adapter_calls=923))
    return prior,request,approval,tmp_path/'extension/approved_prior_view'


def test_exact_extension_preserves_prior_unknowns_and_separate_limits(tmp_path):
    args=fixture(tmp_path);args[-1].parent.mkdir()
    old=(args[0]/'APPROVED_ENVELOPE.json').read_bytes()
    ext=Q.prepare(*args);view=args[-1];e=M.read(view/'APPROVED_ENVELOPE.json')
    assert (args[0]/'APPROVED_ENVELOPE.json').read_bytes()==old
    assert e['ceilings']['2d']['test']==10720+43200
    assert e['wall_ceilings']['2d']['test']==2847+18000
    assert e['ceilings']['3d']['test']==21600
    assert len(ext['job_ids'])==113 and 'previous_unknown' not in ext['job_ids']
    assert (view/'test_2d/outcomes.jsonl').read_bytes()==(args[0]/'test_2d/outcomes.jsonl').read_bytes()
    assert (view/'SELECTION_FREEZE.json').read_bytes()==(args[0]/'SELECTION_FREEZE.json').read_bytes()


def test_unapproved_or_modified_request_cannot_raise_limits(tmp_path):
    args=fixture(tmp_path);a=M.read(args[2]);a['status']='REQUESTED';M.write(args[2],a)
    with pytest.raises(PermissionError,match='Exact approved'):Q.prepare(*args)
    a['status']='APPROVED';M.write(args[2],a)
    request=M.read(args[1]);request['additional_cpu_s']=999999;M.write(args[1],request)
    with pytest.raises(PermissionError,match='Exact approved'):Q.prepare(*args)


def test_changed_pending_job_is_rejected(tmp_path):
    args=fixture(tmp_path);p=args[0]/'test_2d_jobs.json';a=M.read(p);a['jobs'][1]['trial_wall_s']=301;M.write(p,a)
    with pytest.raises(ValueError,match='Frozen job bytes'):Q.prepare(*args)


def test_queue_waits_for_startup_manifest_and_detects_early_exit(tmp_path,monkeypatch):
    monkeypatch.setattr(M,'alive',lambda record:False)
    with pytest.raises(RuntimeError,match='before frozen startup'):Q.wait_for_startup(tmp_path,{})
    M.write(tmp_path/'SELECTION_FREEZE.json',dict(selected_eta=0))
    Q.wait_for_startup(tmp_path,{})
