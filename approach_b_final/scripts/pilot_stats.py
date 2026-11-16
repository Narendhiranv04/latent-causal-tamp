"""Phase C pilot statistics: per stratum ('why') Y / X / Z yield, unresolved, teacher CPU; per-root cost.  usage: pilot_stats.py ITEMS.json LABELS.jsonl[,..] DOM"""
import json, sys, collections, statistics
its = {i["root"]: i for i in json.load(open(sys.argv[1]))}
d = sys.argv[3]
st = collections.defaultdict(collections.Counter); cpu = []
for p in sys.argv[2].split(","):
    for l in open(p):
        r = json.loads(l); it = its[r["root"]]; cpu.append(r["cpu_s"])
        why = dict(zip(map(json.dumps, it["cands"]), it["why"]))
        for x in r["results"]:
            w = why.get(json.dumps(x["seq"]), "?").split("_M")[0].rstrip("0123456789_")
            xr, yr = x["x"] or {}, x["y"] or {}
            ok = (lambda q, k: q.get(k) if (d == "2d" or q.get("resolution", "EVALUATED") == "EVALUATED") else None)
            yv, xv = ok(yr, "y"), (ok(xr, "x") if x["x"] else "notq")
            for key in (w, "ALL"):
                c = st[key]; c["n"] += 1
                c["y1" if yv == 1 else "y0" if yv == 0 else "y_unres"] += 1
                c["x_notq" if xv == "notq" else "x1" if xv == 1 else "x0" if xv == 0 else "x_unres"] += 1
                c["z1"] += (yv == 1 and xv == 1)
for k, c in sorted(st.items(), key=lambda kv: -kv[1]["n"]):
    print(f"{k:14s} n {c['n']:4d}  Y1 {c['y1']:3d} Y0 {c['y0']:3d} Yunres {c['y_unres']:2d} | X1 {c['x1']:3d} X0 {c['x0']:3d} Xnotq {c['x_notq']:3d} Xunres {c['x_unres']:2d} | Z1 {c['z1']:3d}")
print("roots", len(cpu), "cpu_s/root median %.0f p90 %.0f total %.0f" % (statistics.median(cpu), sorted(cpu)[int(0.9 * len(cpu))], sum(cpu)))
