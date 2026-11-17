"""Serial independent physical evaluation of frozen DISCO-only jobs.

Preparing jobs does not grant execution. The separate evaluation envelope must
explicitly authorize this exact jobs file. E16 TRAIN authorization is rejected.
Each trial runs in a fresh process/cache, with durable decisions and query blobs.
"""
from __future__ import annotations
import argparse, dataclasses, fcntl, hashlib, json, multiprocessing as mp, os, pickle, sys, time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import collect as C, data as D, distill as DS, env as E, evaluate as EV, journal as J, policy as P


def read(p):return json.loads(Path(p).read_text())


def plain(x):
    if isinstance(x,dict):return {str(k):plain(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [plain(v) for v in x]
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,np.generic):return x.item()
    return x


class EvidenceEnv(E.RepairEnv):
    """Record the existing adapter; no new physics or feasibility rules."""
    def __init__(self,domain,out,cap):
        super().__init__(domain,witness_dir=out/'witnesses')
        self.out=out;self.journal=J.QueryJournal(out);self.qid=0;self.cap=cap;self.current=None
    def reset(self,*a,**kw):
        state=super().reset(*a,**kw);self.current=state
        J.atomic_bytes(self.out/'initial_state.pkl',self.clone_or_serialize(state));return state
    def invoke(self,kind,state,fn,*args,**kw):
        if self.qid>=self.cap:raise RuntimeError('ADAPTER_CALL_CAP')
        self.qid+=1
        self.journal.start(self.qid,kind,self.clone_or_serialize(state),dict(root_id=state.root_id,depth=state.depth,
            parent_state_hash=state.state_hash(),prefix=state.prefix,action=args[0] if kind=='transition' else None))
        result=fn(state,*args,**kw);self.journal.finish(result)
        if kind=='transition' and result.next_state is not None:self.current=result.next_state
        return result
    def transition(self,state,action):return self.invoke('transition',state,super().transition,action)
    def terminal_query(self,state,**kw):return self.invoke('terminal',state,super().terminal_query,**kw)
    def endpoint_y_query(self,root_id,seq):
        if self.qid>=self.cap:raise RuntimeError('ADAPTER_CALL_CAP')
        self.qid+=1
        self.journal.start(self.qid,'endpoint_y',self.clone_or_serialize(self.current),dict(root_id=root_id,seq=seq))
        result=super().endpoint_y_query(root_id,seq);self.journal.finish(result);return result


def load_proposal(job):
    for name in ('policy','value'):
        if job.get(name):
            if D.sha256_file(job[name])!=job[name+'_sha256']:raise ValueError('Frozen checkpoint changed')
    pol,ck=P.load_policy_checkpoint(job['policy'],'cpu',observation_schema=job['schema'])
    val=DS.load_value_checkpoint(job['value'],'cpu')[0] if job.get('use_value') else None
    return P.PolicyProposalWrapper(job['domain'],pol,ck['scalers'],'cpu',job['mode'],val)


def trial_worker(job,out,controller_pid):
    J.die_with_parent(controller_pid);os.setsid();os.nice(10)
    import torch;torch.set_num_threads(1)
    C.require_headroom()
    row=next(r for r in D.load_snapshot_rows(job['domain']) if r['root_id']==job['root_id'])
    if row['split']!=job['split'] or C.input_hash(row)!=job['input_sha256'] or D.sha256_file(D.raw_root_path(job['domain'],job['root_id']))!=job['root_sha256']:raise ValueError('Frozen root mismatch')
    for p,sha in job['teacher_sources'].items():
        if D.sha256_file(p)!=sha:raise ValueError('Teacher changed')
    J.atomic_bytes(out/'IN_FLIGHT',b'Independent evaluation trial')
    trace=[];original=EV.select_action_model_only
    def select(obs,*a,**kw):
        start=time.perf_counter();decision=original(obs,*a,**kw)
        record=plain(dict(step=len(trace),observation=dataclasses.asdict(obs),observation_hash=obs.obs_hash(),
            latency_ms=(time.perf_counter()-start)*1000,decision=decision))
        trace.append(record);J.atomic_json(out/'selection_trace.json',trace)
        return decision
    EV.select_action_model_only=select
    if job['protocol']=='open_loop':
        # Prediction was committed before this process and before simulator creation.
        pred=job['prediction']
        if any(pred['selection_physical_counters'].values()):raise ValueError('Open-loop oracle violation')
        if pred['status']=='ABSTAIN':
            result=dict(pred,verified=0,x=None,y=None,failed_phase='abstain',failure_kind='ABSTAIN')
        else:
            env=EvidenceEnv(job['domain'],out,job['adapter_call_cap'])
            raw=env.execute_complete_sequence(job['root_id'],[tuple(a) for a in pred['seq']],seed=job['seed'],evaluate_y_on_x_fail=False)
            J.atomic_bytes(out/'physical_result.pkl',pickle.dumps(raw,protocol=pickle.HIGHEST_PROTOCOL))
            result=dict(pred,verified=raw['z'],x=raw['x'],y=raw['y'],failed_phase=raw['failed_phase'],failure_kind=raw['failure_kind'])
    elif job['protocol']=='closed_loop':
        proposal=load_proposal(job);env=EvidenceEnv(job['domain'],out,job['adapter_call_cap'])
        result=EV.run_closed_loop_episode(env,row,proposal,B_test=job['B'],use_value=job['use_value'],rule=job['rule'],seed=job['seed'],max_action_retries=0)
        result.update(observation_schema=job['schema'],latency_ms=sum(r['latency_ms'] for r in trace),
            selection_physical_counters={k:sum(r['decision']['selection_physical_counters'][k] for r in trace) for k in ('physical_transition_calls','teacher_X_calls','teacher_Y_calls','simulator_initializations','MCTS_calls')})
    else:raise ValueError('Unknown protocol')
    events=J.read_events(out);starts=[e for e in events if e['event']=='started'];ends=[e for e in events if e['event']=='finished']
    J.certify_journal(out,len(starts))
    phases={k:sum((e.get('accounting') or {}).get(k,0) or 0 for e in ends) for k in ('transition_planner_calls','connector_calls','y_calls','y_cache_hits')}
    result.update(arm=job['arm'],family_id=job['family_id'],job_id=job['id'],adapter_calls=len(starts),physical_phases=phases,
        independent_verification=True,model_source={k:job.get(k) for k in ('policy','policy_sha256','value','value_sha256')},
        robot_travel=None,robot_travel_status='NOT_AGGREGATED; saved physical state/witness evidence available')
    J.atomic_json(out/'result.json',plain(result));(out/'IN_FLIGHT').unlink()


def validate_execution(jobs_path,envelope):
    if envelope.get('status')!='APPROVED' or envelope.get('scope')!='DISCO_PHYSICAL_EVALUATION' or not envelope.get('authorization_text'):
        raise PermissionError('Separate explicit evaluation authorization required; E16 TRAIN is insufficient')
    if envelope['jobs_sha256']!=D.sha256_file(jobs_path):raise ValueError('Approved jobs changed')
    if envelope['host']!='gvlab' or envelope['workers']!=1 or envelope['gpu'] is not False:raise PermissionError('Evaluation host/resource mismatch')
    jobs=read(jobs_path)['jobs']
    if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Duplicate job IDs')
    if any(j['split']!=envelope['split'] or j['protocol'] not in ('open_loop','closed_loop') for j in jobs):raise ValueError('Mixed or invalid split/protocol')
    if any(not 0<j['adapter_call_cap']<=5 or not 0<j['query_wall_s']<=j['trial_wall_s']<=900 for j in jobs):raise ValueError('Invalid bounded trial')
    if any(j['protocol']=='open_loop' and j['schema']!=P.O0 for j in jobs):raise ValueError('O1 open-loop prohibited')
    return jobs


def run(jobs_path,envelope_path,out):
    envelope=read(envelope_path);jobs=validate_execution(jobs_path,envelope)
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise PermissionError('CPU only')
    if not out.resolve().is_relative_to((D.DISCO_ROOT/'stage2').resolve()):raise ValueError('Isolated Stage 2 output required')
    C.require_headroom();out.mkdir(parents=True,exist_ok=False)
    J.atomic_json(out/'manifest.json',dict(envelope=envelope,jobs_sha256=D.sha256_file(jobs_path),
        source_commit=os.environ['DISCO_SOURCE_COMMIT'],source_sha256={p.name:D.sha256_file(p) for p in HERE.glob('*.py')}))
    cpu=wall=0.;calls=0;rows=[];start=time.monotonic();cpu_start=time.process_time()
    def headroom():
        C.require_headroom()
        if sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>envelope['disk_gib']*2**30:raise RuntimeError('EVALUATION_DISK_LIMIT')
    with (D.DISCO_ROOT/'active_physical.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for i,job in enumerate(jobs):
            headroom();remaining_wall=envelope['active_wall_s']-(time.monotonic()-start)-10
            total_cpu=cpu+time.process_time()-cpu_start
            if remaining_wall<=job['query_wall_s'] or total_cpu+10>=envelope['cpu_s'] or calls+job['adapter_call_cap']>envelope['adapter_calls']:break
            td=out/f'{i:04d}_{job["id"]}';td.mkdir();J.atomic_json(td/'job.json',job)
            worker=mp.get_context('spawn').Process(target=trial_worker,args=(job,td,os.getpid()));worker.start()
            J.wait_for_child(worker,min(job['trial_wall_s'],remaining_wall),directory=td,query_wall_s=job['query_wall_s'],
                cpu_seconds=envelope['cpu_s']-total_cpu-10,rss_limit_kib=3*2**20,resource_check=headroom)
            account=read(td/'WATCHDOG_ACCOUNTING.json');cpu+=account['reaped_child_cpu_s'];wall+=account['wall_s']
            calls+=sum(e['event']=='started' for e in J.read_events(td))
            if (td/'result.json').exists():res=read(td/'result.json')
            else:res=dict(root_id=job['root_id'],domain=job['domain'],seed=job['seed'],arm=job['arm'],protocol=job['protocol'],
                K_legacy=job['K_legacy'],family_id=job['family_id'],status='UNRESOLVED',verified=None,x=None,y=None,
                failure_kind=account['reason'] or 'WORKER_ERROR',job_id=job['id'],evidence=str(td))
            rows.append(res)
            J.atomic_bytes(out/'outcomes.jsonl',''.join(json.dumps(plain(r))+'\n' for r in rows).encode())
            J.atomic_json(out/'ACCOUNTING.json',dict(cpu_s=cpu+time.process_time()-cpu_start,worker_cpu_s=cpu,controller_cpu_s=time.process_time()-cpu_start,worker_wall_s=wall,active_wall_s=time.monotonic()-start,adapter_calls=calls,
                n_frozen_jobs=len(jobs),n_attempted=len(rows),n_not_run=len(jobs)-len(rows)))
            if sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>envelope['disk_gib']*2**30:break
    J.atomic_json(out/'COMPLETE.json',dict(attempted=len(rows),expected=len(jobs),status='COMPLETE' if len(rows)==len(jobs) else 'BUDGET_LIMITED'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--jobs',type=Path,required=True);p.add_argument('--envelope',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.jobs,a.envelope,a.out)
