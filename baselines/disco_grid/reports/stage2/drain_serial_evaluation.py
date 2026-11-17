"""Drain one identity-verified DISCO trial before changing worker topology.

Freeze only our controller, supervise its existing child under unchanged query
caps, then let the controller reap and journal that child before exiting.
No other user's process or workload is signalled.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import time


def read(path):return json.loads(Path(path).read_text())
def fields(pid):return Path(f'/proc/{pid}/stat').read_text().rpartition(')')[2].split()
def alive(pid,ticks):
    try:f=fields(pid);return f[19]==ticks and f[0]!='Z'
    except FileNotFoundError:return False


def unpublished_trials(release):
    trials=[]
    for fragment in release.glob('*_girish_fragment'):
        outcomes=fragment/'outcomes.jsonl'
        published={json.loads(s)['job_id'] for s in outcomes.read_text().splitlines()} if outcomes.exists() else set()
        for directory in fragment.iterdir():
            job=directory/'job.json'
            if directory.is_dir() and job.exists() and not (directory/'WATCHDOG_ACCOUNTING.json').exists() and read(job)['id'] not in published:
                trials.append(directory)
    return trials


def drain(launch_path,out):
    launch=read(launch_path);wrapper=launch['pid'];ticks=launch['proc_stat'].rpartition(')')[2].split()[19]
    if not alive(wrapper,ticks):raise RuntimeError('Serial run already exited; audit it without signals')
    controllers=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            f=fields(int(p.name));cmd=(p/'cmdline').read_bytes()
            if int(f[1])==wrapper and b'continue_physical_laptop.py' in cmd:controllers.append(int(p.name))
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    if len(controllers)!=1:raise RuntimeError('Cannot uniquely identify owned serial controller')
    parent=controllers[0];parent_stat=fields(parent);parent_ticks=parent_stat[19]
    os.kill(parent,signal.SIGSTOP)
    children=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            f=fields(int(p.name));cmd=(p/'cmdline').read_bytes()
            if int(f[1])==parent and b'multiprocessing.spawn' in cmd:children.append((int(p.name),f[19]))
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    if len(children)>1:
        os.kill(parent,signal.SIGCONT);raise RuntimeError('Unexpected serial worker count')
    release=Path(launch['output']);trials=unpublished_trials(release)
    if children and len(trials)!=1:
        os.kill(parent,signal.SIGCONT);raise RuntimeError('Cannot uniquely bind worker to trial journal')
    began=time.time();reason='DRAINED_RETURNED_TRIAL';directory=trials[0] if trials else None
    while children and alive(*children[0]):
        pid,child_ticks=children[0]
        try:f=fields(pid)
        except FileNotFoundError:break
        job=read(directory/'job.json')
        lifetime=float(Path('/proc/uptime').read_text().split()[0])-int(child_ticks)/os.sysconf('SC_CLK_TCK')
        active=directory/'ACTIVE_QUERY.json'
        try:query=read(active)
        except FileNotFoundError:query=None
        if query and time.monotonic()-query['monotonic_s']>=job['query_wall_s']:
            reason='DRAIN_QUERY_WALL_LIMIT'
        elif lifetime>=job['trial_wall_s']:reason='DRAIN_TRIAL_WALL_LIMIT'
        mem={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')}
        if mem['MemAvailable']<8*2**20:reason='DRAIN_RESOURCE_HEADROOM_LOST'
        if os.getloadavg()[0]>(os.cpu_count() or 1)-3:reason='DRAIN_RESOURCE_HEADROOM_LOST'
        if int(f[21])*os.sysconf('SC_PAGE_SIZE')>=3*2**30:reason='DRAIN_CHILD_RAM_LIMIT'
        if reason!='DRAINED_RETURNED_TRIAL':
            os.kill(pid,signal.SIGTERM);deadline=time.monotonic()+5
            while alive(pid,child_ticks) and time.monotonic()<deadline:time.sleep(.1)
            if alive(pid,child_ticks):os.killpg(pid,signal.SIGKILL) if os.getpgid(pid)==pid else os.kill(pid,signal.SIGKILL)
            break
        time.sleep(.1)
    # SIGINT is delivered while the controller is frozen. On continuation its
    # existing watchdog catches it, reaps the completed child, and records CPU.
    resumed=time.time();os.kill(parent,signal.SIGINT);os.kill(parent,signal.SIGCONT)
    deadline=time.monotonic()+20
    while alive(parent,parent_ticks) and time.monotonic()<deadline:time.sleep(.1)
    if alive(parent,parent_ticks):raise RuntimeError('Owned controller did not finish cleanup; do not start the pool')
    if children and alive(*children[0]):raise RuntimeError('Owned physical child survived drain')
    end=time.time();parent_cpu=(int(parent_stat[11])+int(parent_stat[12]))/os.sysconf('SC_CLK_TCK')
    fragments=[d for d in release.glob('*_girish_fragment') if (d/'manifest.json').exists()]
    latest=max(fragments,key=lambda d:(d/'manifest.json').stat().st_mtime)
    active_phase='_'.join(latest.name.split('_')[:2])
    # The parent was frozen throughout the drain. Only the measured cleanup
    # interval can add parent CPU; it is charged conservatively at one thread.
    record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason=reason,
        launch=str(launch_path),controller_pid=parent,controller_start_ticks=parent_ticks,
        controller_stat_at_freeze=parent_stat,controller_cpu_at_freeze_s=parent_cpu,
        controller_final_cpu_upper_bound_s=parent_cpu+(end-resumed),cleanup_wall_s=end-resumed,
        drain_wall_s=end-began,release=str(release),trial=str(directory) if directory else None,active_phase=active_phase,
        child_ids=children,finished_result_present=bool(directory and (directory/'result.json').exists()),
        no_physical_restart=True,physical_children_exited=True,finished_utc_epoch=end)
    with out.open('x') as f:json.dump(record,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('launch',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();print(json.dumps(drain(args.launch,args.out),indent=2))
