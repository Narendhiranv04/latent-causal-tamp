"""Read-only notification and process-identity safety checks, no teacher calls."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import subprocess

P=Path(__file__).resolve().parents[1]/'reports/stage2/monitor_ten_minute_updates.py'
spec=importlib.util.spec_from_file_location('disco_ten_minute_observer',P)
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


def test_resource_wait_is_not_a_crash_but_stale_identity_is_flagged():
    record=dict(status=dict(status='WAITING_HEADROOM'),queue_alive=True,
        physical_alive=False,heartbeat_age_s=12,physical_source_commit='frozen',source=dict(sha256='same'))
    assert M.audit(record,'frozen','same')==[]
    record['queue_alive']=False
    assert 'PID identity absent' in M.audit(record,'frozen','same')[0]
    record['queue_alive']=True;record['heartbeat_age_s']=181
    assert 'heartbeat stale' in M.audit(record,'frozen','same')[0]


def test_source_changes_are_reported_even_after_terminal():
    record=dict(final=dict(status='FINAL_WITH_LIMITATIONS'),physical_source_commit='different',source=dict(sha256='changed'))
    issues=M.audit(record,'frozen','same')
    assert len(issues)==2
    assert all('needs audit' in x for x in issues)


def test_notification_failure_is_not_delivery(monkeypatch):
    monkeypatch.setattr(M.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=1,stderr='No desktop bus'))
    assert M.notify('progress')==dict(attempted=True,accepted=False,returncode=1,error='No desktop bus')
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired('notify-send',10)
    monkeypatch.setattr(M.subprocess,'run',timeout)
    assert not M.notify('progress')['accepted']


def test_publication_requires_success_not_traceback():
    assert not M.publication_complete('RuntimeError: failed to write "commit"')
    assert not M.publication_complete('{"status":"REMOTE_NOT_COMPLETE"}')
    assert M.publication_complete('other log\n{"status":"PUSHED","commit":"abcd"}\n')


def test_partial_phase_counts_prior_once_and_respects_combined_account():
    prior=dict(n_attempted=460);fragment=dict(n_attempted=13)
    assert M.checkpoint_count(None,prior,fragment)==473
    assert M.checkpoint_count(dict(n_attempted=473),prior,fragment)==473
    assert M.checkpoint_count(None,dict(n_attempted=414),None)==414
    assert M.checkpoint_count(None,None,fragment) is None


def test_bound_remote_observation_keeps_arguments_quoted(monkeypatch):
    seen={}
    def run(command,**kwargs):
        seen.update(command=command,kwargs=kwargs)
        return SimpleNamespace(returncode=0,stdout='{"queue_alive":true}')
    monkeypatch.setattr(M.subprocess,'run',run)
    assert M.snapshot(Path('/safe path; echo nope'),dict(pid=42,proc_stat='identity'))['queue_alive']
    assert seen['command'][-1].startswith("python3 -c '")
    assert seen['kwargs']['timeout']==50
    assert '-o' in seen['command']
