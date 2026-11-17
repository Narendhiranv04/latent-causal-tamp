"""Hash a quiescent campaign and certify all declared completed fit exports.

Standard-library only. No teacher, checkpoint deserialization or model loading.
Original interrupted evidence remains indexed with its existing markers.
"""
import argparse, datetime, fcntl, hashlib, json, os, resource, time
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def index(campaign,ledger,out):
    campaign=campaign.resolve();ledger=ledger.resolve();out=out.resolve()
    if not ledger.resolve().is_relative_to(campaign.resolve()) or not ledger.is_file():raise ValueError('Completed campaign ledger required')
    if out.exists():raise FileExistsError('Never overwrite an artifact index')
    began=time.monotonic();cpu=time.process_time()
    with (campaign/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        entries={}
        # Snapshot bytes/sizes and reject changes occurring during hashing.
        for path in sorted(campaign.rglob('*')):
            if not path.is_file() or path.resolve()==out.resolve():continue
            before=path.stat();sha=digest(path);after=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise RuntimeError('Evidence changed during inventory: '+str(path))
            entries[str(path.relative_to(campaign))]=dict(sha256=sha,bytes=after.st_size)
        checks=[]
        for path in sorted(campaign.glob('training/*/COMPLETE.json')):
            complete=json.loads(path.read_text())
            for name,expected in complete['checkpoint_sha256'].items():
                checkpoint=Path(name)
                if not checkpoint.resolve().is_relative_to(campaign.resolve()):raise ValueError('Completed fit references checkpoint outside campaign')
                actual=entries[str(checkpoint.relative_to(campaign))]['sha256']
                if actual!=expected:raise ValueError('Completed checkpoint hash mismatch: '+name)
                checks.append(dict(path=name,sha256=actual,ok=True))
        report=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=os.uname().nodename,source_commit=os.environ.get('DISCO_SOURCE_COMMIT'),
            campaign=str(campaign),completed_ledger=str(ledger),completed_ledger_sha256=digest(ledger),
            script_sha256=digest(Path(__file__)),files=entries,completed_checkpoint_checks=checks,
            total_files=len(entries),total_bytes=sum(e['bytes'] for e in entries.values()),
            cpu_s=time.process_time()-cpu,wall_s=time.monotonic()-began,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            physical_queries=0,scope='Byte inventory and completed-fit integrity only; no task-success inference')
        with out.open('x') as file:json.dump(report,file,indent=2);file.write('\n')
    return dict(files=report['total_files'],bytes=report['total_bytes'],completed_checkpoint_checks=len(checks),cpu_s=report['cpu_s'],wall_s=report['wall_s'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('campaign',type=Path);parser.add_argument('completed_ledger',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();print(json.dumps(index(args.campaign,args.completed_ledger,args.out),indent=2))
