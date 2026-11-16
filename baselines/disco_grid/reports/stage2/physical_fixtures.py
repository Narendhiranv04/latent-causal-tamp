"""Fresh TRAIN order-parity only, with durable per-adapter evidence and external caps."""
import argparse, fcntl, json, multiprocessing as mp, os, pickle, resource, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(HERE))
import collect as C, data as D, env as E, journal as J

class JournalledEnv(E.RepairEnv):
    def __init__(self,dom,out):
        super().__init__(dom,witness_dir=out/'witnesses');self.journal=J.QueryJournal(out);self.qid=0;self.last_state=None
    def reset(self,*args,**kwargs):
        self.last_state=super().reset(*args,**kwargs)
        J.atomic_bytes(self.journal.directory/'initial_state.pkl',self.clone_or_serialize(self.last_state))
        return self.last_state
    def invoke(self,kind,state,fn,*args,**kwargs):
        self.qid+=1
        self.journal.start(self.qid,kind,self.clone_or_serialize(state),dict(root_id=state.root_id,depth=state.depth,
            parent_state_hash=state.state_hash(),action=list(args[0]) if kind=='transition' else None))
        result=fn(state,*args,**kwargs);self.journal.finish(result)
        if kind=='transition' and result.next_state:self.last_state=result.next_state
        return result
    def transition(self,state,action):return self.invoke('transition',state,super().transition,action)
    def terminal_query(self,state,**kw):return self.invoke('terminal',state,super().terminal_query,**kw)
    def endpoint_y_query(self,root_id,seq):
        self.qid+=1;state=self.last_state
        self.journal.start(self.qid,'endpoint_y',self.clone_or_serialize(state),dict(root_id=root_id,seq=seq,depth=state.depth))
        result=super().endpoint_y_query(root_id,seq);self.journal.finish(result);return result

def worker(case,out):
    os.setsid();os.nice(10)
    import torch;torch.set_num_threads(1)
    C.require_headroom();J.atomic_bytes(out/'IN_FLIGHT',b'full sequence fixture')
    start=time.monotonic();cpu=time.process_time();env=JournalledEnv(case['domain'],out)
    res=env.execute_complete_sequence(case['root_id'],[tuple(a) for a in case['seq']],evaluate_y_on_x_fail=True)
    J.atomic_bytes(out/'sequence_result.pkl',pickle.dumps(res))
    compact={k:v for k,v in res.items() if k not in ('step_results','stop_result')}
    compact.update(domain=case['domain'],expected=case,agree=all(res[k]==case['expected_'+k] for k in ['x','y']),
        adapter_invocations=env.qid,wall_s=time.monotonic()-start,cpu_s=time.process_time()-cpu,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    J.atomic_json(out/'result.json',compact);(out/'IN_FLIGHT').unlink()

def run(out, indices=None):
    C.require_headroom()
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise ValueError('CPU only')
    out.mkdir(parents=True,exist_ok=False)
    prior=json.loads((HERE/'reports/validation_v2/physical_parity.json').read_text())
    cases=[dict(domain=r['domain'],root_id=r['case']['root_id'],seq=r['case']['seq'],expected_x=r['case']['expected_x'],expected_y=r['case']['expected_y']) for r in prior['records']]
    if indices is not None:cases=[cases[i] for i in indices]
    J.atomic_json(out/'manifest.json',dict(cases=cases,source_commit=os.environ['DISCO_SOURCE_COMMIT'],
        source_sha256={p.name:D.sha256_file(p) for p in HERE.glob('*.py')},teacher_sources={dom:C.teacher_sources(dom) for dom in ['2d','3d']},
        root_wall_s=600,query_wall_s=240,aggregate_wall_s=1500,max_adapter_calls=12,scope='TRAIN parity, not task evaluation'))
    start=time.monotonic();results=[]
    with (D.DISCO_ROOT/'active_physical.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for i,case in enumerate(cases):
            C.require_headroom();folder=out/f'case_{i}';folder.mkdir()
            child=mp.get_context('spawn').Process(target=worker,args=(case,folder));child.start()
            killed=J.wait_for_child(child,min(600,1500-(time.monotonic()-start)),directory=folder,query_wall_s=240,resource_check=C.require_headroom)
            if killed or child.exitcode:break
            res=json.loads((folder/'result.json').read_text());results.append(res)
            J.atomic_json(out/'results.json',results)
            if not res['agree']:raise RuntimeError('Physical source parity contradiction')
    return results
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--case-indices',type=int,nargs='+');args=a.parse_args();print(json.dumps(run(args.out,args.case_indices),indent=2))
