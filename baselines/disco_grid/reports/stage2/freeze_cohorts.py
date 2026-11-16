"""Freeze offline Stage 2 cohorts; this script NEVER dispatches physical work."""
import collections, hashlib, json, os, sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(HERE))
import data as D, collect as C

def select(rows,groups,split,counts,excluded,tag):
    chosen=[];seen=set(excluded)
    for k,n in counts.items():
        candidates=sorted((r for r in rows if r['split']==split and str(r['K_legacy'])==k),key=lambda r:hashlib.sha256(f'{tag}|{r["root_id"]}'.encode()).hexdigest())
        subset=[]
        for row in candidates:
            f=groups[row['root_id']]
            if f in seen:continue
            subset.append(dict(root_id=row['root_id'],family_id=f,legacy_family_id=D.root_family_key(row),split=split,K_legacy=k,input_sha256=C.input_hash(row),root_sha256=row['root_sha256']))
            seen.add(f)
            if len(subset)==n:break
        if len(subset)!=n:raise ValueError(f'Cannot fill declared {split} K{k} quota')
        chosen.extend(subset)
    return chosen

def freeze(out):
    out.mkdir(parents=True,exist_ok=False);report={}
    for dom in ['2d','3d']:
        rows=D.load_snapshot_rows(dom);groups=D.independence_groups(rows)
        old_ids={p.name for p in (D.DISCO_ROOT/'trees'/dom).glob('*/*') if p.is_dir()}
        for p in list((D.DISCO_ROOT/'validation_v2').glob('pilot_*/manifest.json'))+list((D.DISCO_ROOT/'stage2/trees').glob('*/manifest.json')):
            m=json.loads(p.read_text())
            if m['domain']==dom:old_ids.update(r['root_id'] for r in m['roots'])
        excluded={groups[r] for r in old_ids if r in groups}
        # Exposure audit reads IDs only, not outcomes or any external model.
        exposed=set()
        for p in (D.DISCO_ROOT/'caches').glob(f'verify_{dom}_test*.jsonl'):
            for line in p.read_text().splitlines():
                x=json.loads(line)
                if x.get('root_id') in groups:exposed.add(groups[x['root_id']])
        history=json.loads((HERE/'reports/d6_d7_d8_evaluation_summary.json').read_text())['domains'][dom]
        for x in history['open_loop_primary_per_prediction']:
            exposed.add(groups[x['root_id']])
        train=select(rows,groups,'train',{'0':3,'1':4,'2':3,'3':4,'NONE':2},excluded,f'stage2-train-v1|{dom}|20261117')
        val=select(rows,groups,'val',{k:2 for k in ['0','1','2','3','NONE']},set(),f'stage2-val-v1|{dom}|20261117')
        test=select(rows,groups,'test',{k:2 for k in ['0','1','2','3','NONE']},exposed,f'stage2-exploratory-test-v1|{dom}|20261117')
        assert not set(x['family_id'] for x in train)&set(x['family_id'] for x in val+test)
        report[dom]=dict(train_roots=train,validation_roots=val,exploratory_test_roots=test,
            all_source_components=len(set(groups.values())),preferred_parent_keys=len(set(D.root_family_key(r) for r in rows)),
            source_components_by_split=dict(collections.Counter(r['split'] for r in {groups[r['root_id']]:r for r in rows}.values())),
            excluded_training_components=sorted(excluded),known_exposed_test_components=sorted(exposed),
            confirmation_status='NO_UNTOUCHED_CONFIRMATION: own archived exposure excluded; complete external exposure history not attested',
            dataset_sha256=D.sha256_file(D.BASE_SNAP/f'data{dom}.jsonl'),teacher_source_sha256=C.teacher_sources(dom),
            planned_rounds=['P0','R0','P1Q1','R1 fresh, same root pool','P2Q2 cumulative R0+R1'],
            observation_controls='O0 and O1 trained on identical executed-node supervision; shared O0-guided R1, not separate O1 search',
            search_seed_schedule=[20261117,20261217],model_seeds=[0,1,2],
            execution_status='NOT_AUTHORIZED: larger rung requires an aggregate approved envelope')
    (out/'cohorts.json').write_text(json.dumps(dict(source_commit=os.environ['DISCO_SOURCE_COMMIT'],domains=report),indent=2)+'\n')
    print({d:dict(train=len(v['train_roots']),val=len(v['validation_roots']),test=len(v['exploratory_test_roots']),components=v['all_source_components']) for d,v in report.items()})
if __name__=='__main__':freeze(Path(sys.argv[1]))
