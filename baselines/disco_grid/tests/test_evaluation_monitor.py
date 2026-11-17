"""Monitor identity, no-retry and terminal-evidence tests without a teacher."""
import importlib.util
import json
import os
from pathlib import Path
import pytest

P=Path(__file__).resolve().parents[1]/'reports/stage2/monitor_frozen_evaluation.py'
spec=importlib.util.spec_from_file_location('monitor_fixture',P)
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


def release(tmp_path,cpu3d=100):
    r=tmp_path/'release';r.mkdir()
    M.write(r/'COMPLETE.json',dict(global_adapter_calls=100))
    M.write(r/'APPROVED_ENVELOPE.json',dict(ceilings={'2d':{'test':10800},'3d':{'test':21600}}))
    for d,cpu in [('2d',10780),('3d',cpu3d)]:
        jobs=[dict(id=str(i),query_wall_s=120,adapter_call_cap=5) for i in range(3)]
        M.write(r/f'test_{d}_jobs.json',dict(jobs=jobs));p=r/f'test_{d}';p.mkdir()
        (p/'outcomes.jsonl').write_text(json.dumps(dict(job_id='0',verified=None,status='UNRESOLVED'))+'\n')
        M.write(p/'ACCOUNTING.json',dict(cpu_s=cpu,active_wall_s=10))
    M.write(r/'SELECTION_FREEZE.json',dict(selected_eta={'2d':0,'3d':0}))
    return r


def test_pid_identity_never_adopts_reused_pid():
    record=dict(pid=os.getpid(),proc_stat=Path(f'/proc/{os.getpid()}/stat').read_text())
    assert M.alive(record)
    fields=record['proc_stat'].rpartition(')')[2].split();fields[19]='0'
    record['proc_stat']=record['proc_stat'].rpartition(')')[0]+') '+' '.join(fields)
    assert not M.alive(record)


def test_unknown_attempt_not_rescheduled_and_cumulative_caps_apply(tmp_path):
    r=release(tmp_path)
    gate=M.continuation_gate(r)
    assert gate['domains']['2d']['pending']==2
    assert not gate['domains']['2d']['can_continue']
    assert gate['domains']['3d']['can_continue']
    assert gate['remaining_global_calls']==5423
    assert not M.continuation_gate(r,monitor_cpu=21400)['can_continue']


def test_duplicate_attempt_aborts_instead_of_rescheduling(tmp_path):
    r=release(tmp_path);p=r/'test_3d/outcomes.jsonl';p.write_text(p.read_text()*2)
    with pytest.raises(ValueError,match='Invalid prior'):M.continuation_gate(r)


def test_exhausted_run_publishes_final_pointer_without_any_process_launch(tmp_path,monkeypatch):
    r=release(tmp_path,cpu3d=21550);report=tmp_path/'report';report.mkdir()
    M.write(report/'FINISH_COMPLETE.json',dict(physical_queries=0))
    launch=tmp_path/'launch.json';M.write(launch,dict(pid=999999999,proc_stat=') '+('0 '*25),output=str(r),command=['fixture']))
    rp=tmp_path/'report_launch.json';M.write(rp,dict(pid=999999999,proc_stat=') '+('0 '*25),command=['fixture']))
    config=tmp_path/'config.json';M.write(config,dict(initial_launch=str(launch),initial_report_launch=str(rp),initial_report=str(report),
        initial_version='v5',max_elapsed_s=60,max_continuations=1))
    def forbid(*a,**kw):raise AssertionError('No new process permitted in exhausted fixture')
    monkeypatch.setattr(M.subprocess,'Popen',forbid)
    out=tmp_path/'monitor';M.run(config,out)
    a=M.read(out/'FINAL.json')
    assert a['status']=='FINAL_WITH_LIMITATIONS' and not a['gate']['can_continue']
    assert a['gate']['domains']['3d']['pending']==2
    assert (report/'CAMPAIGN_MONITOR_ACCOUNTING.json').exists()
