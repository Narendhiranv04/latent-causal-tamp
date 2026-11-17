"""Bounded supervision of never-attempted frozen jobs; never retry an episode.

The existing physical engine retains all guards, journals and cumulative quotas.
This monitor waits for headroom after a clean resource stop and starts a new,
versioned continuation. It does not inspect success values or select models.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def read(path):return json.loads(Path(path).read_text())
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    path=Path(path);temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def alive(record):
    try:stat=Path(f'/proc/{record["pid"]}/stat').read_text().rpartition(')')[2].split()
    except FileNotFoundError:return False
    return stat[0]!='Z' and stat[19]==record['proc_stat'].rpartition(')')[2].split()[19]


def continuation_gate(release,monitor_cpu=0.):
    """Use identities and cost ledgers only, never task success for scheduling."""
    release=Path(release);complete=read(release/'COMPLETE.json');envelope=read(release/'APPROVED_ENVELOPE.json')
    result={}
    for domain in ('2d','3d'):
        jobs=read(release/f'test_{domain}_jobs.json')['jobs']
        observed=[json.loads(s) for s in (release/f'test_{domain}/outcomes.jsonl').read_text().splitlines()]
        seen=[r['job_id'] for r in observed];ids={j['id'] for j in jobs}
        if len(set(seen))!=len(seen) or not set(seen)<=ids:raise ValueError('Invalid prior attempt identities')
        pending=[j for j in jobs if j['id'] not in set(seen)]
        cost=read(release/f'test_{domain}/ACCOUNTING.json');cap=envelope['ceilings'][domain]['test']
        wall_cap=envelope.get('wall_ceilings',envelope['ceilings'])[domain]['test']
        cpu=cap-cost['cpu_s']-monitor_cpu;wall=wall_cap-cost['active_wall_s']
        calls=5523-complete['global_adapter_calls']
        viable=any(cpu>j['query_wall_s']+100 and wall>j['query_wall_s']+100 and calls>=j['adapter_call_cap'] for j in pending)
        result[domain]=dict(pending=len(pending),remaining_cpu_s=cpu,remaining_active_wall_s=wall,
            pending_adapter_call_caps=sum(j['adapter_call_cap'] for j in pending),can_continue=viable)
    return dict(domains=result,can_continue=any(x['can_continue'] for x in result.values()),
        remaining_global_calls=5523-complete['global_adapter_calls'])


def headroom(root):
    mem=next(int(s.split()[1])*1024 for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    return dict(load1=os.getloadavg()[0],ram_available=mem,disk_free=shutil.disk_usage(root).free)


def run(config_path,out):
    config=read(config_path);out=Path(out);out.mkdir(exist_ok=False)
    start=time.monotonic();cpu=time.process_time();launch=read(config['initial_launch'])
    record_path=Path(config['initial_launch']);report_record=read(config['initial_report_launch'])
    report=Path(config['initial_report']);version=config['initial_version'];base=Path(launch['output']).parent
    frozen=digest(Path(launch['output'])/'SELECTION_FREEZE.json')
    physical_template=list(launch['command']);report_template=list(report_record['command'])
    continuations=0;states=[];final_gate=None
    def save(status,**extra):
        value=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=status,
            config_sha256=digest(config_path),current_launch=str(record_path),current_release=launch['output'],
            report=str(report),version=version,continuations=continuations,monitor_cpu_s=time.process_time()-cpu,
            monitor_elapsed_wall_s=time.monotonic()-start,history=states,**extra)
        write(out/'STATUS.json',value);return value
    def wait():
        # Idle observation is recorded separately from physical active wall.
        time.sleep(config.get('poll_s',30))
    def stable():
        samples=0
        while samples<3:
            h=headroom(config['disco_root'])
            samples=samples+1 if h['load1']<=18 and h['ram_available']>=8*2**30 and h['disk_free']>=20*2**30 else 0
            save('WAITING_HEADROOM',headroom=h,stable_samples=samples)
            if time.monotonic()-start>config['max_elapsed_s']:return False
            wait()
        return True
    try:
        while True:
            while alive(launch):
                save('RUNNING_PHYSICS');wait()
            release=Path(launch['output'])
            if not (release/'COMPLETE.json').exists():raise RuntimeError('Missing clean completed ledger; no automatic physical restart')
            if digest(release/'SELECTION_FREEZE.json')!=frozen:raise RuntimeError('VAL selection changed')
            # Let the already launched report worker finish before new physics.
            while alive(report_record):save('REPORTING');wait()
            if not (report/'FINISH_COMPLETE.json').exists():
                if not stable():raise RuntimeError('No reporting headroom within monitor window')
                report=Path(config['report_base'])/f'final_monitor_recovery_{continuations}'
                cmd=list(report_template);cmd[-3]=str(record_path);cmd[-2]=str(report)
                log=out/f'report_recovery_{continuations}.log'
                with log.open('x') as f:p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
                report_record=dict(pid=p.pid,proc_stat=Path(f'/proc/{p.pid}/stat').read_text(),command=cmd)
                write(out/f'report_recovery_{continuations}_launch.json',report_record)
                while alive(report_record):save('REPORTING_RECOVERY');wait()
                if not (report/'FINISH_COMPLETE.json').exists():raise RuntimeError('Bounded report recovery failed; evidence retained')
            final_gate=continuation_gate(release,time.process_time()-cpu)
            states.append(dict(release=str(release),report=str(report),gate=final_gate))
            if not final_gate['can_continue']:break
            if continuations>=config['max_continuations'] or time.monotonic()-start>=config['max_elapsed_s']:break
            if time.process_time()-cpu>5:raise RuntimeError('Monitor CPU safety reserve reached')
            if not stable():break
            # The immutable runner audits costs and attempts again and subtracts
            # its own startup reserves; this monitor never resets its ceilings.
            continuations+=1
            target=base/f'{config["run_prefix"]}_{continuations}'
            cmd=list(physical_template);cmd[-2:]=[str(release),str(target)]
            log=out/f'physical_{continuations}.log'
            with log.open('x') as f:p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
            launch=dict(pid=p.pid,proc_stat=Path(f'/proc/{p.pid}/stat').read_text(),output=str(target),
                log=str(log),command=cmd,source_commit=config['physical_source_commit'])
            record_path=out/f'physical_{continuations}_launch.json';write(record_path,launch)
            report=Path(config['report_base'])/f'final_monitor_physical_{continuations}'
            version=f'v{config.get("version_base",100)+continuations}'
            cmd=list(report_template);cmd[-3]=str(record_path);cmd[-2]=str(report)
            with (out/f'report_{continuations}.log').open('x') as f:p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
            report_record=dict(pid=p.pid,proc_stat=Path(f'/proc/{p.pid}/stat').read_text(),command=cmd)
            write(out/f'report_{continuations}_launch.json',report_record)
        # At most five CPU seconds of the runner's >=30-second reserve are
        # spent by this monitor. Account them explicitly without double-counting
        # elapsed observation and concurrent physical phase wall times.
        actual_cpu=time.process_time()-cpu
        charge=read(Path(launch['output'])/'test_3d/ACCOUNTING.json')['cpu_s']
        if actual_cpu>10 or charge+actual_cpu>21600:raise RuntimeError('Monitor/physical cumulative CPU safety check failed')
        account=dict(monitor_cpu_s=actual_cpu,monitor_elapsed_wall_s=time.monotonic()-start,
            charged_3d_physical_plus_monitor_cpu_s=charge+actual_cpu,physical_cpu_ceiling_s=21600,
            observation_wall_scope='Includes idle headroom waits and concurrent physics; never add to physical phase wall',
            additional_physical_attempts_are_never_retries=True,gate=final_gate,history=states)
        write(report/'CAMPAIGN_MONITOR_ACCOUNTING.json',account)
        result=save('FINAL_WITH_LIMITATIONS',gate=final_gate)
        write(out/'FINAL.json',result)
    except BaseException as exc:
        write(out/'ERROR.json',save('STOPPED_NEEDS_AUDIT',error=repr(exc)))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();run(a.config,a.out)
