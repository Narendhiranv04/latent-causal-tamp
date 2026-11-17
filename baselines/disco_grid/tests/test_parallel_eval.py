"""Pool budgeting and isolated multi-process fixtures; no physical teacher."""
import json
import os
from pathlib import Path
import sys
import time
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import collect as C, data as D, journal as J, parallel_eval as POOL


def fake_trial(job,out,parent):
    J.die_with_parent(parent);os.setsid()
    journal=J.QueryJournal(out)
    journal.start(1,'fixture_only',b'not a physical state',dict(root_id=job['root_id']))
    time.sleep(.5)
    journal.finish(dict(status='FIXTURE_RETURNED'))
    result=dict(job.get('prediction') or {},**{k:job[k] for k in ('root_id','domain','seed','arm','protocol','K_legacy','family_id')})
    result.update(job_id=job['id'],status='REPAIR',verified=1,x=1,y=1,failed_phase=None,failure_kind=None)
    J.atomic_json(out/'result.json',result)


def fixture(tmp_path,monkeypatch,jobs):
    root=tmp_path/'disco';root.mkdir()
    monkeypatch.setattr(D,'DISCO_ROOT',root)
    monkeypatch.setenv('DISCO_ROOT',str(root))
    auth=tmp_path/'auth.json'
    J.atomic_json(auth,dict(status='APPROVED',scope='DISCO_RELEASE_PARALLEL_HOST_AMENDMENT',
        authorization_text='Three synthetic fixture workers, no teacher',workers=3,cpu_threads=1,gpu=False,
        host='girish-laptop',hostname='gvcstar'))
    monkeypatch.setenv('DISCO_EXECUTION_AUTHORIZATION',str(auth))
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES','');monkeypatch.setenv('DISCO_SOURCE_COMMIT','synthetic_fixture')
    path=tmp_path/'jobs.json';J.atomic_json(path,dict(jobs=jobs))
    env=tmp_path/'envelope.json';J.atomic_json(env,dict(status='APPROVED',scope='DISCO_PHYSICAL_EVALUATION',
        authorization_text='Synthetic fixture only',host='girish-laptop',workers=3,gpu=False,split='val',
        jobs_sha256=D.sha256_file(path),cpu_s=300,active_wall_s=120,adapter_calls=3,disk_gib=.1))
    return path,env,root/'stage2/pool'


def job(i,protocol):
    return dict(id=str(i),root_id='r'+str(i) if protocol=='closed_loop' else 'shared',
        domain='2d',seed=i,arm='fixture',protocol=protocol,K_legacy='1',family_id='f',
        split='val',physics_seed=0,schema='o0_v1',root_sha256='raw',input_sha256='input',
        teacher_sources={'fixture':'sha'},adapter_call_cap=1,query_wall_s=10,trial_wall_s=30,
        prediction=dict(seq=[[1,2]],status='REPAIR',root_id='shared',domain='2d',seed=i,
            K_legacy='1',protocol='open_loop'))


def test_reservations_include_inflight_and_shutdown_overhead():
    limit=2000.;used=100.;reserved=0.
    for _ in range(3):reserved+=POOL.reserve_cpu(limit,used,reserved,600)
    assert used+reserved<=limit-10
    reserved+=POOL.reserve_cpu(limit,used,reserved,600)
    assert POOL.reserve_cpu(limit,used,reserved,600)==0
    assert POOL.reserve_cpu(100,100,0,600)==0


def test_parallel_host_amendment_keeps_exactly_three_workers(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch,[])
    assert C.execution_workers()==3
    with pytest.raises(RuntimeError,match='requested host'):C.execution_host('gvlab')
    p=Path(os.environ['DISCO_EXECUTION_AUTHORIZATION']);d=json.loads(p.read_text());d['workers']=4;J.atomic_json(p,d)
    with pytest.raises(RuntimeError,match='invalid execution'):C.execution_workers()


def test_drain_does_not_mistake_cached_trials_for_unpublished_worker(tmp_path):
    import importlib.util
    p=Path(__file__).resolve().parents[1]/'reports/stage2/drain_serial_evaluation.py'
    spec=importlib.util.spec_from_file_location('drain_fixture',p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    fragment=tmp_path/'val_3d_girish_fragment';fragment.mkdir()
    for i in ('cached','active'):
        d=fragment/i;d.mkdir();J.atomic_json(d/'job.json',dict(id=i));J.atomic_json(d/'result.json',dict(verified=1))
    (fragment/'outcomes.jsonl').write_text(json.dumps(dict(job_id='cached'))+'\n')
    assert module.unpublished_trials(tmp_path)==[fragment/'active']


@pytest.mark.skipif(os.environ.get('DISCO_POOL_INTEGRATION')!='1',reason='Opt-in synthetic process fixture on a headroom-qualified host')
def test_three_supervisors_have_separate_child_accounts(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch,[job(i,'closed_loop') for i in range(3)])
    rows=POOL.run(*args,worker_target=fake_trial)
    account=json.loads((args[2]/'ACCOUNTING.json').read_text())
    assert len(rows)==3 and all(r['verified']==1 for r in rows)
    assert account['max_concurrent_trials']==3 and account['adapter_calls']==3
    supervisors=[json.loads(p.read_text()) for p in args[2].glob('*/SUPERVISOR_COMPLETE.json')]
    assert len(supervisors)==3
    assert account['worker_cpu_s']==pytest.approx(sum(a['physical_child_cpu_s'] for a in supervisors))
    assert account['cpu_s']>=sum(a['cpu_s'] for a in supervisors)


@pytest.mark.skipif(os.environ.get('DISCO_POOL_INTEGRATION')!='1',reason='Opt-in synthetic process fixture on a headroom-qualified host')
def test_identical_inflight_sequences_execute_once(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch,[job(i,'open_loop') for i in range(3)])
    rows=POOL.run(*args,worker_target=fake_trial)
    account=json.loads((args[2]/'ACCOUNTING.json').read_text())
    assert len(rows)==3 and account['adapter_calls']==1
    assert sum(bool(r.get('physical_verification_reuse_from')) for r in rows)==2
    assert len(list(args[2].glob('*/SUPERVISOR_COMPLETE.json')))==1
