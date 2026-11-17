"""Publish the bounded monitor's final measured package; no physics or fitting."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from sync_physical_release import command,sync,BRANCH


def run(worktree,monitor):
    worktree=worktree.resolve()
    head=command(['git','rev-parse','HEAD'],worktree).strip()
    if command(['git','status','--porcelain'],worktree):raise RuntimeError('Commit work before observing')
    if command(['git','branch','--show-current'],worktree).strip()!=BRANCH:raise RuntimeError('Dedicated branch required')
    while True:
        final=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','girish','cat',str(monitor/'FINAL.json')],capture_output=True,text=True)
        if final.returncode==0:
            record=json.loads(final.stdout);break
        if final.returncode!=1:raise RuntimeError('SSH observation failed; no physical restart')
        error=subprocess.run(['ssh','girish','cat',str(monitor/'ERROR.json')],capture_output=True,text=True)
        if error.returncode==0:raise RuntimeError('Remote monitor stopped for audit: '+error.stdout)
        if error.returncode!=1:raise RuntimeError('SSH error observation failed')
        time.sleep(30)
    if record['status']!='FINAL_WITH_LIMITATIONS':raise RuntimeError('Unexpected monitor terminal status')
    if command(['git','rev-parse','HEAD'],worktree).strip()!=head or command(['git','status','--porcelain'],worktree):
        raise RuntimeError('Concurrent worktree edits; evidence remains remote, no overwrite')
    remote=Path(record['report'])
    if not remote.is_relative_to('/home/longhorizon/disco_grid_stage2'):raise ValueError('Unexpected report store')
    return sync(worktree,False,str(remote),record['version'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('worktree',type=Path);p.add_argument('monitor',type=Path)
    a=p.parse_args();print(json.dumps(run(a.worktree,a.monitor),indent=2),flush=True)
