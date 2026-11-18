import json,glob,collections
F=('K','displacement','distractor_role','distractors','mechanism','parking','source','start_pose')
tk=lambda sp: json.dumps({k:sp.get(k) for k in F},sort_keys=True)
spec={}
for f in glob.glob('/home/naren/abf_v34/collect/*/gen/*/ledger.jsonl'):
  for l in open(f):
    e=json.loads(l)
    if e.get('root_id') and e.get('spec'): spec[e['root_id']]=e['spec']
rej=collections.defaultdict(list)
for f in glob.glob('/home/naren/abf_v34/collect/*/enrich/*/SLOT_CHILDREN.json'):
  for s,e in json.load(open(f)).items():
    for r in e.get('rejected',[]): rej[s].append(r)
out=[]
for rf in ['RETARGET_RT1_2D','RETARGET_RT2','RETARGET_RT3']:
  for r in json.load(open(f'/home/naren/abf_v34/cohort/{rf}.json')):
    if r.get('cap_reason')!='ENRICH_MAX_ROUNDS': continue
    g=[x for x in set(rej[r['slot_id']]) if x in spec and tk(spec[x])==tk(r['from_spec'])]
    out.append((rf,r['slot_id'],r['round'],len(g)))
    print(rf,r['slot_id'],'round',r['round'],'genuine rejections on from-template:',len(g),'VOID' if len(g)<4 else 'KEEP')
json.dump(out,open('/tmp/claude-1000/-home-naren-Desktop-boltzmann-lfd/2b63770c-8b68-4a44-bb5e-cd133b6e31dc/scratchpad/void.json','w'))
