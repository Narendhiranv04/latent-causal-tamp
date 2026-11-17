"""Fetch a completed measured release and publish only this dedicated worktree.

No physics, fitting, selection or SSH permission changes. Refuses to replace
concurrent edits. Can observe the already-authorized remote finisher while idle.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import time

HOST = 'girish'
REMOTE = '/home/longhorizon/disco_grid_stage2/final_parallel_physical_release_v1'
BRANCH = 'naren/disco-grid-stage2'
CANONICAL = ('FINAL_METRICS.json','FINAL_METRICS.csv','ABLATIONS.csv',
    'CENSORING_LEDGER.csv','RESOURCE_ACCOUNTING.csv','PHYSICAL_RESOURCE_TOTALS.json',
    'FINAL_DISCO_STAGE2_REPORT.md','PAPER_METHODS_AND_RESULTS.md',
    'STAGE2_FINAL_STATUS.json','ROOT_STOP_DIAGNOSTICS.json','FAILURE_EXAMPLES.json',
    'final_predictions.jsonl','final_verifications.jsonl','final_config.json',
    'final_root_manifest.json','final_checkpoints.json','SELECTION_FREEZE.json')


def command(args, cwd=None):
    return subprocess.run(args,cwd=cwd,text=True,capture_output=True,check=True).stdout


def sync(worktree, wait=False, remote=REMOTE, version="v1"):
    if not re.fullmatch(r"v[1-9][0-9]*",version):raise ValueError("Version must be v followed by a positive integer")
    worktree=worktree.resolve()
    reports=worktree/'baselines/disco_grid/reports/stage2'
    if command(['git','branch','--show-current'],worktree).strip()!=BRANCH:
        raise RuntimeError('Dedicated Stage 2 branch required')
    initial_head=command(['git','rev-parse','HEAD'],worktree).strip()
    initial_status=command(['git','status','--porcelain'],worktree)
    if initial_status:
        raise RuntimeError('Commit current work before starting the publication observer')
    while True:
        probe=subprocess.run(['ssh',HOST,'test','-f',remote+'/FINISH_COMPLETE.json'],capture_output=True)
        if probe.returncode==0:
            break
        if probe.returncode not in (1,):
            raise RuntimeError('SSH observation failed; physical run is not restarted')
        if not wait:
            return {'status':'REMOTE_NOT_COMPLETE'}
        time.sleep(60)
    if command(['git','rev-parse','HEAD'],worktree).strip()!=initial_head or command(['git','status','--porcelain'],worktree):
        raise RuntimeError('Worktree changed during evaluation; refusing to overwrite concurrent work')
    destination=reports/f'physical_release_V15_F25_{version}'
    if destination.exists():
        raise FileExistsError('Do not overwrite a versioned physical release')
    staging=reports/'.physical_release_download'
    staging.mkdir(exist_ok=False)
    command(['scp','-r',f'{HOST}:{remote}/.',str(staging)])
    marker=json.loads((staging/'FINISH_COMPLETE.json').read_text())
    if marker.get('physical_queries')!=0 or marker.get('automatic_physical_restarts')!=0:
        raise ValueError('Unexpected finisher scope')
    manifest={str(p.relative_to(staging)):dict(bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in staging.rglob('*') if p.is_file()}
    # Atomic versioned publication precedes changes to current report aliases.
    staging.rename(destination)
    for name in CANONICAL:
        source=destination/name
        if source.exists():
            shutil.copyfile(source,reports/name)
    status=json.loads((destination/'STAGE2_FINAL_STATUS.json').read_text())
    record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=HOST,
        remote=remote,publication_base_commit=initial_head,files=manifest,
        physical_status=status['physical_task_results'],scope='Measured evidence transfer and report publication; no physical execution')
    (reports/'PHYSICAL_RELEASE_PUBLICATION.json').write_text(json.dumps(record,indent=2)+'\n')
    index=reports/'INDEX.md';text=index.read_text()
    start=text.index('**PARTIAL')
    stop=text.index('**',start+2)+2
    text=text[:start]+('**PARTIAL Stage 2 release. Physical evaluation status: '+status['physical_task_results']+
        '. Measured results and execution limits are recorded below; missing evidence stays explicit.**')+text[stop:]
    text+='\n## Measured physical release\n\n'
    text+='- [Standalone measured report](FINAL_DISCO_STAGE2_REPORT.md), [metrics](FINAL_METRICS.csv), and [paired ablations](ABLATIONS.csv).\n'
    text+=f'- [Versioned physical evidence package](physical_release_V15_F25_{version}/FINISH_COMPLETE.json), [query/state byte inventory](physical_release_V15_F25_{version}/physical_evidence_index.json), and [publication hashes](PHYSICAL_RELEASE_PUBLICATION.json).\n'
    text+='- [Root STOP diagnostics](ROOT_STOP_DIAGNOSTICS.json), [failure examples](FAILURE_EXAMPLES.json), and [physical resource totals](PHYSICAL_RESOURCE_TOTALS.json).\n'
    text+='\nEarlier pending-run statements in this index describe preparation history; the measured report and status JSON are current.\n'
    index.write_text(text)
    relative='baselines/disco_grid/reports/stage2'
    published=[f'{relative}/physical_release_V15_F25_{version}',f'{relative}/PHYSICAL_RELEASE_PUBLICATION.json',f'{relative}/INDEX.md']
    published.extend(f'{relative}/{name}' for name in CANONICAL if (destination/name).exists())
    command(['git','add','--',*published],worktree)
    command(['git','commit','--only','-m','Publish measured standalone DISCO physical release and limitations','--',*published],worktree)
    commit=command(['git','rev-parse','HEAD'],worktree).strip()
    command(['git','push','origin',BRANCH],worktree)
    return dict(status='PUSHED',commit=commit,physical_status=status['physical_task_results'])


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('worktree',type=Path)
    parser.add_argument('--wait',action='store_true')
    parser.add_argument('--remote',default=REMOTE)
    parser.add_argument('--version',default='v1')
    args=parser.parse_args()
    print(json.dumps(sync(args.worktree,args.wait,args.remote,args.version),indent=2),flush=True)
