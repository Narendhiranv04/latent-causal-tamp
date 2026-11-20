import json,sys
for p in sys.argv[1:]:
    for l in open(p):
        r=json.loads(l)
        if r["verdict"]=="CERTIFIED_MIN_K":
            w=[t for t in r["tries"] if t.get("x")==1 and t.get("y")==1][0]
            print(json.dumps({"file":p,"root_id":r["root_id"],"K":r["K_lb"],"n_objects":r["n_objects"],"geom":r["geom"],"Y0":r["Y0"]["y"],"witness":w["seq"],"x_replay":w.get("x_replay"),"y_replay":w.get("y_replay"),"cpu_s":r.get("cpu_s")}))
