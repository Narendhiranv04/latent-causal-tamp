"""Read-only ten-minute status observer; existing supervisor owns recovery.

No physical launch, restart, model selection, or remote filesystem mutation is
performed here. Desktop notification delivery is recorded, never assumed.
"""
import argparse
import datetime
import fcntl
import inspect
import json
import os
from pathlib import Path
import shlex
import subprocess
import time


BRANCH = 'naren/disco-grid-stage2'


REMOTE = r'''
import datetime,hashlib,json,os,time
from pathlib import Path
queue=Path(QUEUE);expected=EXPECTED
def read(p):
    try:return json.loads(Path(p).read_text())
    except FileNotFoundError:return None
def alive(record):
    if not record:return False
    try:s=Path('/proc/%s/stat'%record['pid']).read_text().rpartition(')')[2].split()
    except FileNotFoundError:return False
    return s[0]!='Z' and s[19]==record['proc_stat'].rpartition(')')[2].split()[19]
status=read(queue/'monitor/STATUS.json') or read(queue/'STATUS.json') or {}
final=read(queue/'FINAL.json');error=read(queue/'ERROR.json') or read(queue/'monitor/ERROR.json')
launch=read(status.get('current_launch',queue/'physical_initial_launch.json'))
release=Path((launch or {}).get('output',str(queue/'missing')))
envelope=read(release/'APPROVED_ENVELOPE.json') or {}
prior_release=Path(envelope['prior_release']) if envelope.get('prior_release') else None
phases={}
for domain in ('2d','3d'):
    jobs=read(release/('test_%s_jobs.json'%domain));combined=read(release/('test_%s/ACCOUNTING.json'%domain))
    fragment=read(release/('test_%s_pool_fragment/ACCOUNTING.json'%domain))
    prior=read(prior_release/('test_%s/ACCOUNTING.json'%domain)) if prior_release else None
    total=len(jobs['jobs']) if jobs else None
    attempted=checkpoint_count(combined,prior,fragment)
    phases[domain]=dict(total=total,attempted=attempted,accounting=combined,fragment=fragment)
source=None
if launch:
    script=next((Path(s) for s in launch.get('command',[]) if s.endswith('/continue_frozen_test.py')),None)
    if script and script.exists():source=dict(path=str(script),sha256=hashlib.sha256(script.read_bytes()).hexdigest())
stamp=queue/'monitor/STATUS.json'
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=status,
    final=final,error=error,queue_alive=alive(expected),physical_alive=alive(launch),
    physical_source_commit=(launch or {}).get('source_commit'),source=source,
    heartbeat_age_s=time.time()-stamp.stat().st_mtime if stamp.exists() else None,
    phases=phases,load1=os.getloadavg()[0])))
'''


def atomic(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def checkpoint_count(combined, prior, fragment):
    """Do not double count a fragment already merged into combined accounting."""
    if combined is not None:return combined['n_attempted']
    if prior is not None:return prior['n_attempted'] + (fragment['n_attempted'] if fragment else 0)
    return None


def snapshot(queue, launch, host='girish'):
    script = 'QUEUE=' + repr(str(queue)) + '\nEXPECTED=' + repr(launch) + '\n' + inspect.getsource(checkpoint_count) + '\n' + REMOTE
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
        '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=2', host,
        'python3 -c ' + shlex.quote(script)], capture_output=True, text=True, timeout=50)
    if result.returncode:
        raise RuntimeError('Bounded SSH observation failed: ' + result.stderr[-500:])
    return json.loads(result.stdout)


def audit(record, expected_source, initial_hash=None):
    issues = []
    if record.get('error'):issues.append('Supervisor stopped; needs audit/relocation qualification')
    if not record.get('final'):
        if not record.get('queue_alive'):issues.append('Supervisor PID identity absent; needs audit/relocation qualification')
        if (record.get('heartbeat_age_s') or 0) > 180:issues.append('Supervisor heartbeat stale; needs audit')
    if record.get('physical_source_commit') not in (None, expected_source):issues.append('Physical source commit changed; needs audit')
    source = record.get('source') or {}
    if initial_hash and source.get('sha256') != initial_hash:issues.append('Immutable physical runner hash changed; needs audit')
    return issues


def message(record):
    progress = []
    for domain, phase in record.get('phases', {}).items():
        if phase.get('attempted') is not None:progress.append('%s %s/%s TEST attempts' % (domain.upper(), phase['attempted'], phase['total']))
    status = 'Final evidence ready; publication check follows' if record.get('final') else record.get('status', {}).get('status', 'Observation unavailable')
    if record.get('final') and publication_complete(record.get('publication',{}).get('publisher_log_tail','')):
        status='Final evidence published; documented limitations remain'
    if record.get('issues'):status = '; '.join(record['issues'])
    return status + ('. ' + '; '.join(progress) if progress else '')


def notify(body):
    try:
        completed = subprocess.run(['notify-send', '--app-name=DISCO status',
            'DISCO progress update', body], capture_output=True, text=True, timeout=10)
        return dict(attempted=True, accepted=completed.returncode == 0,
            returncode=completed.returncode, error=completed.stderr[-300:])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return dict(attempted=True, accepted=False, error=repr(exc))


def publication_complete(tail):
    """Require a successful publication result, not a traceback mentioning commit."""
    decoder=json.JSONDecoder()
    for offset,char in enumerate(tail):
        if char!='{':continue
        try:value,_=decoder.raw_decode(tail[offset:])
        except ValueError:continue
        if isinstance(value,dict) and value.get('status')=='PUSHED' and value.get('commit'):return True
    return False


def publication(worktree, publisher_log):
    try:
        git = subprocess.run(['git', 'log', '-1', '--format=%H %s'], cwd=worktree,
            capture_output=True, text=True, timeout=10)
        path = Path(publisher_log)
        tail = path.read_text(errors='replace')[-2500:] if path.exists() else ''
        return dict(head=git.stdout.strip(), publisher_log_tail=tail)
    except (OSError,subprocess.TimeoutExpired) as exc:
        return dict(head=None,publisher_log_tail='',error=repr(exc))


def run(args):
    out = args.output.resolve();out.mkdir(parents=True, exist_ok=True)
    lock = (out/'observer.lock').open('a+')
    try:fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('A status observer already owns this output directory')
    launch = json.loads(args.queue_launch.read_text())
    branch = subprocess.run(['git', 'branch', '--show-current'], cwd=args.worktree,
        capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    if branch != BRANCH:raise RuntimeError('Dedicated DISCO branch required')
    prior = json.loads((out/'latest.json').read_text()) if (out/'latest.json').exists() else {}
    initial_hash = prior.get('immutable_runner_sha256')
    atomic(out/'launch.json', dict(pid=os.getpid(), proc_stat=Path('/proc/self/stat').read_text(),
        queue=str(args.queue), interval_s=args.interval, source_commit=args.source_commit,
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    deadline=time.monotonic()+args.max_hours*3600
    while True:
        try:
            record=snapshot(args.queue, launch)
            if initial_hash is None:initial_hash=(record.get('source') or {}).get('sha256')
            record['issues']=audit(record,args.source_commit,initial_hash)
        except Exception as exc:
            record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                issues=['Observation unavailable; needs audit: '+repr(exc)])
        record['immutable_runner_sha256']=initial_hash
        record['recovery_authority']='Existing remote 30-second supervisor; this observer never launches physics'
        record['relocation_requirements']='Fresh authorized-host RAM>=8GiB/disk>=20GiB, qualified environment/data/teacher hashes, clean handoff and unchanged cumulative budgets; gvlab execution revoked'
        record['publication']=publication(args.worktree,args.publisher_log)
        record['notification']=notify(message(record))
        atomic(out/'latest.json',record)
        with (out/'updates.jsonl').open('a') as stream:
            stream.write(json.dumps(record,sort_keys=True)+'\n');stream.flush();os.fsync(stream.fileno())
        print(json.dumps(record),flush=True)
        # The publication observer emits a JSON result containing its commit.
        tail=record['publication']['publisher_log_tail']
        if record.get('final') and publication_complete(tail):
            atomic(out/'FINAL.json',dict(status='FINAL_EVIDENCE_AND_PUBLICATION_OBSERVED',utc=record['utc']))
            return
        if args.once or time.monotonic()>=deadline:return
        time.sleep(args.interval)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue',type=Path,required=True)
    parser.add_argument('--queue-launch',type=Path,required=True)
    parser.add_argument('--source-commit',required=True)
    parser.add_argument('--worktree',type=Path,required=True)
    parser.add_argument('--publisher-log',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--interval',type=int,default=600)
    parser.add_argument('--max-hours',type=float,default=24)
    parser.add_argument('--once',action='store_true')
    arguments=parser.parse_args()
    if arguments.interval<60 or arguments.max_hours<=0:parser.error('Bounded observation and interval >=60s required')
    run(arguments)
