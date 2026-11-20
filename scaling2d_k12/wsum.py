import json,collections,sys
C=collections.Counter(); F=collections.Counter(); n=0
for p in sys.argv[1:]:
    for l in open(p):
        r=json.loads(l); n+=1; C[(r["K_lb"],r["verdict"])]+=1
        last=[t for t in r["tries"] if not t.get("final")]
        fin=[t for t in r["tries"] if t.get("final")]
        if r["verdict"]=="CERTIFIED_MIN_K": F["certified"]+=1
        elif fin: F["full-length X=1, Y fail:"+str(fin[0].get("y_status") if fin[0].get("x")==1 else "X fail "+str(fin[0].get("x_phase")))]+=1
        else:
            ok=sum(1 for t in last if t.get("x")==1 or str(t.get("x_phase","")).startswith("connector"))
            F[f"stuck after {min(ok,3)}{'+' if ok>=3 else ''} verified steps"]+=1
print(n, sorted(C.items())); print(sorted(F.items(), key=lambda t:-t[1]))
