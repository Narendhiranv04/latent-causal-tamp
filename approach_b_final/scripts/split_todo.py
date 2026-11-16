"""Deterministic weighted split of a verify list by root (all of a root's sequences stay on one host, one job): greedy by query count, largest
roots first, ties by sha256(root).  usage: split_todo.py TODO.jsonl OUTPREFIX host:weight[,host:weight...]  -> OUTPREFIX_<host>.jsonl + manifest"""
import collections, hashlib, json, sys
todo, pre, w = sys.argv[1], sys.argv[2], dict((h, float(x)) for h, x in (a.split(":") for a in sys.argv[3].split(",")))
by = collections.defaultdict(list)
for l in open(todo):
    by[json.loads(l)["root_id"]].append(l)
load, asg = {h: 0.0 for h in w}, {h: [] for h in w}
for r in sorted(by, key=lambda r: (-len(by[r]), hashlib.sha256(r.encode()).hexdigest())):
    h = min(w, key=lambda h: ((load[h] + len(by[r])) / w[h], h)); asg[h].append(r); load[h] += len(by[r])
man = {}
for h in w:
    with open(f"{pre}_{h}.jsonl", "w") as f:
        for r in sorted(asg[h]):
            f.writelines(by[r])
    man[h] = {"roots": len(asg[h]), "queries": int(load[h])}
json.dump({"todo": todo, "todo_sha256": hashlib.sha256(open(todo, "rb").read()).hexdigest(), "weights": w, "split": man}, open(f"{pre}_MANIFEST.json", "w"), indent=1)
print(json.dumps(man))
