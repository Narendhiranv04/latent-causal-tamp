import json,sys,collections
for p in sys.argv[1:]:
    c=collections.Counter(); keys=collections.Counter(); ex={}
    for l in open(p):
        r=json.loads(l); c[r.get("split")]+=1
        for k,v in r.items():
            keys[k]+=1
            if k not in ex: ex[k]=str(v)[:90]
    print("==",p,dict(c)); [print("  ",k,n,"|",ex[k]) for k,n in keys.items()]
