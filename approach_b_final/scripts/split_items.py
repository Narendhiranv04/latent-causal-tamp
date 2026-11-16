"""Split a v32c items file by root across hosts (weighted greedy by candidate count), skipping roots already labelled in any given label file.
usage: split_items.py ITEMS.json DONE_LABELS(comma or -) OUTDIR TAGBASE host:weight[,...] -> OUTDIR/items_<TAGBASE>_<host>.json + manifest"""
import json, sys, hashlib
its, done_files, out, tb = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3], sys.argv[4]
w = dict((h, float(x)) for h, x in (a.split(":") for a in sys.argv[5].split(",")))
done = set()
if done_files != "-":
    for p in done_files.split(","):
        done |= {json.loads(l)["root"] for l in open(p)}
todo = [i for i in its if i["root"] not in done]
load, asg = {h: 0.0 for h in w}, {h: [] for h in w}
for i in sorted(todo, key=lambda i: (-len(i["cands"]), hashlib.sha256(i["root"].encode()).hexdigest())):
    h = min(w, key=lambda h: ((load[h] + len(i["cands"])) / w[h], h)); asg[h].append(i); load[h] += len(i["cands"])
for h in w:
    json.dump(asg[h], open(f"{out}/items_{tb}_{h}.json", "w"))
man = {"items": sys.argv[1], "skipped_already_labelled_roots": len(its) - len(todo), "split": {h: {"roots": len(asg[h]), "candidates": int(load[h])} for h in w}}
json.dump(man, open(f"{out}/SPLIT_{tb}.json", "w"), indent=1); print(json.dumps(man))
