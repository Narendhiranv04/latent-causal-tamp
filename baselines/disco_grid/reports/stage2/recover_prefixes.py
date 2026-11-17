"""Certify completed iteration prefixes from quarantined E16 TRAIN attempts.

No physical dispatch, original mutation, unknown-label conversion, or resumption.
The original interrupted directory stays quarantined. Only its hashed atomic
checkpoint and the exact completed journal prefix are copied into a new artifact.
Completed tail queries beyond that checkpoint remain archived but are not used.
"""
import argparse, hashlib, json, pickle, sys
from pathlib import Path


def recover(source,dest,J,D):
    if not (source/'IN_FLIGHT').exists() and not (source/'ACTIVE_QUERY.json').exists():raise ValueError('Recovery is only for quarantined attempts')
    if not (source/'checkpoint.pkl').exists():return dict(status='NO_COMPLETED_CHECKPOINT',source=str(source))
    raw=(source/'checkpoint.pkl').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=(source/'checkpoint.sha256').read_text():raise ValueError('Original checkpoint corruption')
    ck=pickle.loads(raw)
    if ck['version']!=2 or ck['completed_iterations']<=0:raise ValueError('Not a completed iteration checkpoint')
    calls=ck['sim_transition_calls']+ck['sim_terminal_calls'];events=J.read_events(source)
    prefix=[e for e in events if e['query_id']<=calls]
    # Verify the copied prefix independently; do not truncate or rewrite the original.
    dest.mkdir(parents=True,exist_ok=False)
    for name in ('checkpoint.pkl','checkpoint.sha256'):J.atomic_bytes(dest/name,(source/name).read_bytes())
    for e in prefix:
        keys=('parent_blob',) if e['event']=='started' else ('result_blob',)
        for key in keys:J.atomic_bytes(dest/e[key],(source/e[key]).read_bytes())
    J.atomic_bytes(dest/'queries.jsonl',''.join(json.dumps(e,sort_keys=True)+'\n' for e in prefix).encode())
    J.certify_journal(dest,calls)
    # Disposable extraction mirror is rebuilt from the authoritative checkpoint.
    J.atomic_bytes(dest/'nodes.pkl',pickle.dumps(ck['nodes'],protocol=pickle.HIGHEST_PROTOCOL))
    J.atomic_json(dest/'tree.json',dict(summary=ck['summary'],resolved_config=ck['config']))
    record=dict(status='CERTIFIED_COMPLETED_ITERATION_PREFIX',source=str(source),destination=str(dest),
        original_checkpoint_sha256=D.sha256_file(source/'checkpoint.pkl'),original_journal_sha256=D.sha256_file(source/'queries.jsonl'),
        prefix_journal_sha256=D.sha256_file(dest/'queries.jsonl'),completed_iterations=ck['completed_iterations'],retained_calls=calls,
        completed_tail_queries_not_reconstructed=sum(e['event']=='finished' and e['query_id']>calls for e in events),
        unfinished_queries_not_labelled=sum(e['event']=='started' for e in events)-sum(e['event']=='finished' for e in events),
        original_remains_quarantined=True,physical_queries=0,
        interpretation='Eligible historical checkpoint only; not certification of the whole interrupted attempt')
    J.atomic_json(dest/'RECOVERY_PROVENANCE.json',record);return record


def run(engine,campaign,out):
    sys.path.insert(0,str(engine));import data as D, journal as J
    if not (campaign/'continuation_001/COMPLETE.json').exists():raise RuntimeError('Wait for serial collection/fitting to finish')
    if not out.resolve().is_relative_to(campaign.resolve()):raise ValueError('Recovery must remain inside campaign disk budget')
    out.mkdir(parents=True,exist_ok=False);records=[]
    for p in sorted(campaign.glob('trees/*/*/*/ATTEMPT_COMPLETE.json')):
        status=json.loads(p.read_text())
        if status['status']!='QUARANTINED_UNRESOLVED':continue
        rel=p.parent.relative_to(campaign/'trees');source=p.parent/status['root_id']
        records.append(recover(source,out/rel,J,D))
    J.atomic_json(out/'manifest.json',dict(records=records,scope='TRAIN-only offline certification; originals unmodified',
        script_sha256=D.sha256_file(__file__),physical_queries=0))
    return records
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--engine',type=Path,required=True);p.add_argument('--campaign',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.engine,a.campaign,a.out),indent=2))
