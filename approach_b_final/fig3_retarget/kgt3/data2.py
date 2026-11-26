#!/usr/bin/env python3
"""KGT3 P2 matched ordered-chunk data (FIG3_KGT3_PREREG P2).  Evaluator side only: construction may use offline teacher artefacts
(2D kill tables, 3D planner probes); none of it is ever a planner input.  Splits are fixed by family before any label.
  2D  prep2d      (PY2D)  clean R3COH2D generator layouts -> records + public rows (one layout per seed family)
      build2d     (PYG)   kill-table-screened discordant pairs / triples / controls at h0 and after a prefix + ordinary stratum -> jobs (sealed)
  3D  construct3d (PY3D)  per clean family: fin3d A.query probes -> one new enabler obstacle E blocking B, E parks, B plans again; Z plans
      build3d     (PYG)   labelled matched-permutation jobs on the constructed records + ordinary stratum -> jobs (sealed)
  labels DOM      exact chunk labels (labels.chunks_of; UNKNOWN never negative; no anchored singleton labels from completed chunks)
Queries are physical X_CHUNKED runs (no Y); every 3D A.query probe counts as one construction query."""
from __future__ import annotations

import collections, hashlib, itertools, json, os, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
C, LB = K.C, K.LB
O = C.FIG3 / "kgt3"
K3S = Path(os.environ.get("K3SCALE", str(C.NW / "k3scale")))
CAPS = {"2d": {"GATE": 210, "SELECT": 150, "TRAIN": 240}, "3d": {"GATE": 210, "SELECT": 150, "TRAIN": 240}}
ORD_SHARE = 0.15


def h(*a):
    return hashlib.sha256(("KGT3|" + "|".join(map(str, a))).encode()).hexdigest()


def split_of(fam, pool):
    """pool 'gen' (generator seeds: GATE 35 % / SELECT 25 % / TRAIN 40 %) or 'val' (original VAL: GATE 58 % / SELECT 42 %) or 'train'."""
    if pool == "train":
        return "TRAIN"
    u = int(h("split", fam)[:8], 16) / 16 ** 8
    if pool == "gen":
        return "GATE" if u < 0.35 else ("SELECT" if u < 0.60 else "TRAIN")
    return "GATE" if u < 0.58 else "SELECT"


def used_fams(dom):
    out = set()
    for f in (K.O / f"scenes_31_{dom}.json", K.O / f"scenes_33a_{dom}.json", K.O / "scenes_31d_2d.json"):
        if f.exists():
            d = json.loads(f.read_text())
            out |= {s["fam"] for s in (d["scenes"] if isinstance(d, dict) else d)}
    return out


# =========================================================================================================== 2D
def coh_seeds():
    coh = json.loads((HERE.parent / "r3" / "reports" / "r31" / "DEV_ORDER_2D_cohort.json").read_text())
    return {r["root_id"].split("-")[1] for r in coh["cohort"] + coh["reserve"]}


def prep2d():
    sys.path.insert(0, str(K3S))
    import witness as W
    import contracts as CT
    Ls = {}
    for f in ("gen2d_layouts.jsonl", "gen2d_layouts_w1.jsonl"):
        for l in open(K.O / f):
            x = json.loads(l); Ls.setdefault(x["fingerprint"], x)
    wit = {json.loads(l)["root_id"]: json.loads(l) for l in open(K.O / "gen2d_witness.jsonl")}
    dev = coh_seeds()
    fams = collections.defaultdict(list)
    for L in Ls.values():
        s = L["root_id"].split("-")[1]
        if s not in dev:
            fams[s].append(L)
    (O / "rec2d").mkdir(parents=True, exist_ok=True)
    rows = []
    for s, Lv in sorted(fams.items()):
        def pre(L):
            w = wit.get(L["root_id"])
            return [t["seq"] for t in (w or {}).get("tries", []) if t.get("x") == 1 and not t.get("final") and len(t["seq"]) <= 2]
        Lv.sort(key=lambda L: (not pre(L), L["K_lb"], h("layout", L["root_id"])))
        L = Lv[0]
        rec, ids = W.rec_of({"cells0": L["cells0"], "goal_cell": L["goal_cell"], "root_id": L["root_id"]}, "original")
        p = O / "rec2d" / f"{L['root_id']}.json"; p.write_text(json.dumps(rec))
        inp = CT.view2d(rec)
        assert dict(zip(inp["ids"], inp["cells0"])) == dict(zip(ids, L["cells0"]))
        rows.append({"root_id": L["root_id"], "domain": "2d", "parent_family_id": f"R3COH2D-seed-{s}", "inputs": inp, "path": str(p), "geom": "original",
                     "layout": {k: L[k] for k in ("cells0", "goal_cell", "K_lb", "witness_set", "n_objects")}, "verified_prefixes": pre(L), "gen_ids": ids})
    with open(O / "rows2d_gen.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print("PREP2D", len(rows), "families", collections.Counter(split_of(r["parent_family_id"], "gen") for r in rows), "with_prefix", sum(bool(r["verified_prefixes"]) for r in rows))


class Screen:
    """Offline kill-table screen (k3scale MINK_TABLE_original): ordered chunk -> SCREEN_LIVE / SCREEN_DEAD (dead = a pick or place with every
    candidate killed by the current occupancy; live is NOT a feasibility certificate)."""
    def __init__(self):
        T = json.loads((K3S / "G1" / "MINK_TABLE_original.json").read_text())
        self.T = T
        self.qc = set(json.loads((K3S / "G1" / "QCLEAR_original.json").read_text())["cells"])

    def live(self, base, tab, x, occ):
        k = 0
        for q in occ:
            k |= int(self.T[tab][str(x)].get(str(q), 0))
        return int(self.T[base][str(x)]) & ~k

    def chunk(self, cur, C):
        cur = dict(cur)
        for o, d in C:
            others = [c for i, c in cur.items() if i != o]
            if d in cur.values() or not self.live("pick0", "pickkill", cur[o], others) or not self.live("place0", "placekill", d, others):
                return False
            cur[o] = d
        return True

    def park(self, goal, occ0):
        pc = lambda v: bin(int(v)).count("1")  # noqa: E731
        foot = {c: sum(pc(self.T["pickkill"][str(x)].get(str(c), 0)) + pc(self.T["placekill"][str(x)].get(str(c), 0)) for x in range(64) if x != c) for c in range(64)}
        return sorted((c for c in range(64) if c in self.qc and c != goal and c not in occ0 and pc(self.T["place0"][str(c)])), key=lambda c: (foot[c], c))


def chain_queries(S, row, rng):
    """-> list of (template, ordered actions as (gen idx, cell), bounds, screen tags) for one generator family."""
    L = row["layout"]; cells0 = list(L["cells0"]); goal = L["goal_cell"]
    M = [o for o in L["witness_set"] if o != 0]
    dests = S.park(goal, set(cells0))[:8]
    out = []

    def pick_sets(cur, avoid_o, avoid_d, k):
        acts = [(o, d) for o in M if o not in avoid_o for d in dests if d not in avoid_d and d not in cur.values()]
        cands = []
        for combo in itertools.combinations(acts, k):
            if len({o for o, _ in combo}) < k or len({d for _, d in combo}) < k:
                continue
            lv = {p: S.chunk(cur, p) for p in itertools.permutations(combo)}
            cands.append((combo, lv))
        cands.sort(key=lambda t: h("set", row["root_id"], json.dumps(t[0])))
        return cands

    def take(cands, want):
        for combo, lv in cands:
            n = sum(lv.values())
            if want == "DISC" and 0 < n < len(lv):
                return combo, lv
            if want == "BOTH_LIVE" and n == len(lv):
                return combo, lv
            if want == "BOTH_DEAD" and n == 0:
                return combo, lv
        return None

    def orders(combo, lv, k):
        if k == 2:
            return list(itertools.permutations(combo))
        live = sorted([p for p, v in lv.items() if v], key=lambda p: h("o", json.dumps(p)))
        dead = sorted([p for p, v in lv.items() if not v], key=lambda p: h("o", json.dumps(p)))
        return (live[:1] + dead[:2] + live[1:] + dead[2:])[:3]

    def state(prefix_names):
        cur = dict(enumerate(cells0))
        ids = row["gen_ids"]
        for o, d in prefix_names:
            cur[ids.index(o)] = int(d)
        return cur
    for tag, pre in (("h0", []), ("h1", row["verified_prefixes"][-1] if row["verified_prefixes"] else None)):
        if pre is None:
            cur = dict(enumerate(cells0))
            first = next(((o, d) for o in M for d in dests if S.chunk(cur, [(o, d)])), None)
            if first is None:
                continue
            pre = [[row["gen_ids"][first[0]], first[1]]]; ptag = "kill_table_first"
        else:
            ptag = "verified" if pre else "none"
        cur = state(pre)
        pidx = [(row["gen_ids"].index(o), int(d)) for o, d in pre]
        ao, ad = {o for o, _ in pidx}, {d for _, d in pidx}
        p2 = pick_sets(cur, ao, ad, 2)
        sel = [("PAIR_DISC", take(p2, "DISC"), 2)]
        if tag == "h0":
            sel.append(("PAIR_CTRL", take(p2, "BOTH_LIVE") or take(p2, "BOTH_DEAD"), 2))
        sel.append(("TRIPLE_DISC", take(pick_sets(cur, ao, ad, 3), "DISC"), 3))
        for name, got, k in sel:
            if not got:
                continue
            combo, lv = got
            for p in orders(combo, lv, k):
                out.append({"template": f"{tag}_{name}", "prefix": pidx, "prefix_kind": ptag if pidx else "none", "chunk": list(p),
                            "screen": "LIVE" if lv[p] else "DEAD", "group": h("grp", row["root_id"], tag, name)[:12]})
    return out


def build2d(expand=0):
    """expand > 0: the preregistered expansion -- the SAME rules with the GATE budget raised by `expand`; only jobs not in the sealed initial
    manifest are written (jobs_p2x_2d.json)."""
    from models import Frozen
    if int(expand):
        CAPS["2d"] = {**CAPS["2d"], "GATE": CAPS["2d"]["GATE"] + int(expand)}
    import data as DA
    S = Screen()
    gen = [json.loads(l) for l in open(O / "rows2d_gen.jsonl")]
    jobs, fams = [], []
    budget = {s: CAPS["2d"][s] for s in CAPS["2d"]}
    chain_cap = {s: int(round(budget[s] * (1 - ORD_SHARE))) for s in budget}
    used = {s: 0 for s in budget}
    for row in sorted(gen, key=lambda r: h("fam", r["parent_family_id"])):
        sp = split_of(row["parent_family_id"], "gen")
        Q = chain_queries(S, row, random.Random(h("rng", row["root_id"])))
        if not Q or used[sp] + len(Q) > chain_cap[sp]:
            continue
        used[sp] += len(Q)
        ids = row["inputs"]["ids"]; gids = row["gen_ids"]
        fams.append({"root_id": row["root_id"], "fam": row["parent_family_id"], "split": sp, "stratum": "CHAIN", "n_jobs": len(Q), "N": len(ids)})
        for q in Q:
            seq = [(gids[o], d) for o, d in q["prefix"] + q["chunk"]]
            bounds = ([len(q["prefix"])] if q["prefix"] else []) + [len(q["prefix"]) + len(q["chunk"])]
            jobs.append({"key": f"KGT3-2D|{row['root_id']}|{q['template']}|{json.dumps(seq)}|{json.dumps(bounds)}", "root_id": row["root_id"],
                         "fam": row["parent_family_id"], "split": sp, "stratum": "CHAIN", "template": q["template"], "group": q["group"], "screen": q["screen"],
                         "prefix_kind": q["prefix_kind"], "scene_type": "S0", "base": [], "path": row["path"], "geom": "original", "kind": "X_CHUNKED",
                         "seq": [[o, int(d)] for o, d in seq], "seq_idx": [[ids.index(o), int(d)] for o, d in seq], "bounds": bounds})
    # ordinary stratum: clean original families with a v32 X = 1 single prefix (R3.1D design, new families)
    fz = Frozen("2d"); fz.caps = {}
    rows = C.snapshot_rows("2d", snap=C.SNAP_TRAIN)
    pg = {}
    for sp_ in ("train", "val"):
        for l in open(C.PRIV / f"private_{sp_}_2d.jsonl"):
            e = json.loads(l); pg[e.get("root_id", e.get("evaluation_group_id"))] = (e["path"], e.get("geom", "original"))
    lin = json.loads((K.O / "lineage_2d.json").read_text()); usedf = used_fams("2d")
    for pool in ("val", "train"):
        el = [e for e in lin["eligible"][pool] if 9 <= e["N"] <= 20 and str(e["K"]) not in ("0", "None") and e["root_id"] in pg and e["fam"] not in usedf
              and any(q["x"] == 1 and len(q["seq"]) == 1 for q in rows[e["root_id"]]["labels"]["X"])]
        el.sort(key=lambda e: h("ord", e["root_id"])); seen = set()
        for e in el:
            if e["fam"] in seen:
                continue
            seen.add(e["fam"]); sp = split_of(e["fam"], pool)
            if used[sp] + 6 > budget[sp]:
                continue
            rid = e["root_id"]; row0 = rows[rid]; ids = row0["inputs"]["ids"]
            p = [list(map(int, sorted((q["seq"] for q in row0["labels"]["X"] if q["x"] == 1 and len(q["seq"]) == 1), key=lambda s: h("p", rid, json.dumps(s)))[0][0]))]
            Sc = DA.Scene(fz, row0, rid, sp, pg[rid][0], rows, False)
            c0 = int(row0["inputs"]["cells0"][p[0][0]])
            ok = lambda a: a[0] != p[0][0] and a[1] != p[0][1] and a[1] != c0  # noqa: E731
            Sc.P = [a for a in Sc.P if ok(a)]; Sc.R = [a for a in Sc.R if ok(a)]
            xy_ = Sc.draw(("P", "R"), n=2); xyz = Sc.draw(("P", "R"), n=3)
            if not xy_ or not xyz:
                continue
            Q = [("h1_ORD_PAIR", p + [list(a) for a in xy_], [1, 3]), ("h1_ORD_PAIR", p + [list(a) for a in reversed(xy_)], [1, 3]),
                 ("h1_ORD_TRIPLE", p + [list(a) for a in xyz], [1, 4]), ("h1_ORD_TRIPLE", p + [list(a) for a in xyz[::-1]], [1, 4]),
                 ("h0_ORD_PAIR", [list(a) for a in xy_], [2]), ("h0_ORD_PAIR", [list(a) for a in reversed(xy_)], [2])]
            used[sp] += len(Q)
            fams.append({"root_id": rid, "fam": e["fam"], "split": sp, "stratum": "ORD", "n_jobs": len(Q), "N": e["N"]})
            for t, seq, b in Q:
                jobs.append({"key": f"KGT3-2D|{rid}|{t}|{json.dumps(seq)}|{json.dumps(b)}", "root_id": rid, "fam": e["fam"], "split": sp, "stratum": "ORD",
                             "template": t, "group": h("grp", rid, t)[:12], "screen": None, "prefix_kind": "v32_verified" if t.startswith("h1") else "none",
                             "scene_type": "S0", "base": [], "path": pg[rid][0], "geom": pg[rid][1], "kind": "X_CHUNKED",
                             "seq": [[ids[o], int(d)] for o, d in seq], "seq_idx": seq, "bounds": b})
    assert sum(used.values()) <= 600 + int(expand)
    if int(expand):
        init = {j["key"] for j in json.loads((O / "jobs_p2_2d.json").read_text())}
        jobs = [j for j in jobs if j["key"] not in init]
        fams = [f for f in fams if any(j["root_id"] == f["root_id"] for j in jobs)]
        assert len(jobs) <= int(expand)
    tag = "p2x" if int(expand) else "p2"
    jf = O / f"jobs_{tag}_2d.json"; jf.write_text(json.dumps(jobs, indent=1))
    (O / f"fams_{tag}_2d.json").write_text(json.dumps(fams, indent=1))
    import guard as GD
    s = GD.seal(jf)
    print(json.dumps({"jobs": len(jobs), "used": used, "families": collections.Counter(f"{f['split']}:{f['stratum']}" for f in fams),
                      "templates": collections.Counter(j["template"] for j in jobs), "screen": collections.Counter(str(j["screen"]) for j in jobs), "seal": s["sha256"][:16]}))


# =========================================================================================================== 3D
BIG = {"shape": "cylinder", "size": 0.018, "height": 0.18}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _boot3d():
    sys.path.insert(0, str(HERE.parent.parent / "compose3d_k45"))
    import evaluate_k45 as EV
    EV.boot(os.environ["FIG3_STORE"])
    return EV


def construct_one(item):
    """One family: deterministic enabler construction with fin3d A.query probes -> dict (record or reason, probes, cpu)."""
    EV = _boot3d() if not hasattr(construct_one, "EV") else construct_one.EV
    construct_one.EV = EV
    F = EV.W["F"]; A = F.Q._M["A"]
    t0 = time.process_time(); n = {"probes": 0}
    rec = json.loads(Path(item["path"]).read_text())
    objs = [dict(o) for o in rec["objects"]]; cells = {k: tuple(v) for k, v in rec["initial_cells"].items()}
    goal = tuple(rec["goal"]); rid = item["root_id"]
    allc = [(r, c) for r in range(6) for c in range(6)]

    def plans(extra_obj, ccells, name, dst):
        n["probes"] += 1
        allo = objs + ([extra_obj] if extra_obj else [])
        e = A.build(allo, {k: list(v) for k, v in ccells.items()}); A.settle(e, {k: list(v) for k, v in ccells.items()})
        return A.query(e, name, list(dst))[0] is not None
    occ = set(cells.values())
    free = [x for x in allc if x not in occ and x != goal]
    srt = lambda xs, *k: sorted(xs, key=lambda x: h(*k, rid, x))  # noqa: E731
    Bs = srt([o["id"] for o in objs if o["id"] != "t0"], "B")[:3]
    eid = f"o{len(objs) - 1:02d}"
    while eid in cells:
        eid = f"o{int(eid[1:]) + 1:02d}"
    E = {**BIG, "id": eid, "color": "red"}
    out = {"root_id": rid, "ok": False}
    try:
        for B in Bs:
            pBs = srt([x for x in free if cheb(x, cells["t0"]) >= 2 and cheb(x, cells[B]) >= 2], "pB", B)[:2]
            pB = next((x for x in pBs if plans(None, cells, B, x)), None)
            if pB is None:
                continue
            for x in srt([x for x in free if cheb(x, cells[B]) == 1 and x != pB], "E", B)[:4]:
                c1 = {**cells, eid: x}
                if plans(E, c1, B, pB):
                    continue                                                     # E at x does not block B
                pEs = srt([y for y in free if y not in (x, pB) and cheb(y, cells[B]) >= 2 and cheb(y, x) >= 2], "pE", B, x)[:2]
                pE = next((y for y in pEs if plans(E, c1, eid, y)), None)
                if pE is None:
                    continue
                if not plans(E, {**cells, eid: pE}, B, pB):
                    continue                                                     # B still blocked with E parked
                Zs = srt([o["id"] for o in objs if o["id"] not in ("t0", B)], "Z")[:2]
                Z = pZ = None
                for z in Zs:
                    cand = srt([y for y in free if y not in (x, pB, pE) and cheb(y, cells[B]) >= 2], "pZ", z)[:1]
                    if cand and plans(E, c1, z, cand[0]):
                        Z, pZ = z, cand[0]; break
                rec2 = {**rec, "objects": objs + [E], "initial_cells": {**{k: list(v) for k, v in cells.items()}, eid: list(x)},
                        "ids": {**rec.get("ids", {}), "root_id": rid + "-KGT3E"},
                        "kgt3": {"parent_root": rid, "B": B, "pB": list(pB), "E": eid, "x": list(x), "pE": list(pE), "Z": Z, "pZ": list(pZ) if pZ else None}}
                out = {"root_id": rid, "ok": True, "rec": rec2}
                raise StopIteration
        out["why"] = "NO_VERIFIED_CHAIN"
    except StopIteration:
        pass
    except Exception as e:  # noqa: BLE001
        out = {"root_id": rid, "ok": False, "why": f"ERROR {type(e).__name__}: {str(e)[:160]}"}
    out.update(probes=n["probes"], cpu_s=round(time.process_time() - t0, 1))
    return out


def families3d():
    lin = json.loads((K.O / "lineage_3d.json").read_text()); usedf = used_fams("3d")
    import data as DA
    paths = DA.raw_paths("3d")
    out = []
    for pool in ("val", "train"):
        el = [e for e in lin["eligible"][pool] if 3 <= e["N"] <= 8 and e["fam"] not in usedf and e["root_id"] in paths]
        el.sort(key=lambda e: h("fam3", e["fam"], e["root_id"])); seen = set()
        for e in el:
            if e["fam"] not in seen:
                seen.add(e["fam"]); out.append({**e, "split": split_of(e["fam"], pool), "path": paths[e["root_id"]]})
    return out


EXPAND3D = {"GATE": 330, "TRAIN": 180, "SELECT": 90}       # preregistered expansion allocation (fixed before any expansion outcome)


def construct3d(workers, cpu_lo, max_cpu_h=10.0, expand=0):
    """Construction dispatcher: per split, families in sha order; a family is dispatched only if the split's remaining budget covers the
    worst case (24 probes + 9 labelled jobs); construction probes are charged to the split.  Ordinary share reserved."""
    import multiprocessing as mp
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + int(workers))))
    fams = families3d()
    if int(expand):
        CAPS["3d"] = {s: CAPS["3d"][s] + EXPAND3D[s] for s in CAPS["3d"]}
    cap = {s: int(round(CAPS["3d"][s] * (1 - ORD_SHARE))) for s in CAPS["3d"]}
    used = {s: 0 for s in cap}
    outp = O / "construct3d.jsonl"
    prior = [json.loads(l) for l in open(outp)] if outp.exists() else []
    done = {r["root_id"] for r in prior}
    for r in prior:
        used[r["split"]] += r["probes"] + (9 if r["ok"] else 0)
    queue = [f for f in fams if f["root_id"] not in done]
    pool = mp.get_context("spawn").Pool(int(workers), maxtasksperchild=8)
    running, f, qi, cpu = {}, open(outp, "a"), 0, sum(r.get("cpu_s", 0) for r in prior)
    W = 24 + 9
    while True:
        for k, (ar, fam, t) in list(running.items()):
            if ar.ready():
                r = ar.get(); running.pop(k); r["split"] = fam["split"]; r["fam"] = fam["fam"]; r["N"] = fam["N"]; r["K"] = fam["K"]
                f.write(json.dumps(r) + "\n"); f.flush(); used[fam["split"]] += r["probes"] + (9 if r["ok"] else 0); cpu += r["cpu_s"]
                print(time.strftime("%H:%M:%S"), r["root_id"], fam["split"], r["ok"], r.get("why"), r["probes"], r["cpu_s"], used, flush=True)
        resv = collections.Counter(fam["split"] for _, fam, _ in running.values())
        queue = [x for x in queue if used[x["split"]] + W <= cap[x["split"]]]            # a split closes only on its ACTUAL usage
        nxt = next((i for i, x in enumerate(queue) if used[x["split"]] + (resv[x["split"]] + 1) * W <= cap[x["split"]]), None)
        if nxt is not None and len(running) < int(workers) and (cpu + sum(time.time() - t for *_, t in running.values())) / 3600 < float(max_cpu_h):
            fam = queue.pop(nxt)                                                    # in-flight reservations only delay, never skip
            running[fam["root_id"]] = (pool.apply_async(construct_one, (fam,)), fam, time.time()); continue
        if not running:
            break
        time.sleep(1)
    pool.terminate()
    print("CONSTRUCT3D_DONE", json.dumps({"used": used, "cpu_h": cpu / 3600}))


def build3d(expand=0):
    """expand > 0: same rules with the EXPAND3D budgets added; only jobs not in the sealed initial manifest are written (jobs_p2x_3d.json)."""
    import contracts as CT
    if int(expand):
        CAPS["3d"] = {s: CAPS["3d"][s] + EXPAND3D[s] for s in CAPS["3d"]}
    import data as DA
    R = [json.loads(l) for l in open(O / "construct3d.jsonl")]
    (O / "rec3d").mkdir(parents=True, exist_ok=True)
    jobs, fams, rows = [], [], []
    used = collections.Counter()
    for r in R:
        used[r["split"]] += r["probes"]
    for r in sorted([r for r in R if r["ok"]], key=lambda r: h("fam", r["fam"])):
        rec = r["rec"]; kg = rec["kgt3"]; rid2 = rec["ids"]["root_id"]
        p = O / "rec3d" / f"{rid2}.json"; p.write_text(json.dumps(rec))
        inp = CT.view3d(rec); ids = inp["ids"]
        rows.append({"root_id": rid2, "domain": "3d", "parent_family_id": r["fam"], "inputs": inp, "path": str(p), "parent_root": r["root_id"]})
        cell = lambda rc: int(rc[0]) * 6 + int(rc[1])  # noqa: E731
        Ea, Ba = (kg["E"], cell(kg["pE"])), (kg["B"], cell(kg["pB"]))
        Za = (kg["Z"], cell(kg["pZ"])) if kg["Z"] else None
        Q = [("h0_PAIR_EB", [Ea, Ba], [2]), ("h0_PAIR_EB", [Ba, Ea], [2])]
        if Za:
            Q += [("h0_TRIPLE", [Ea, Ba, Za], [3]), ("h0_TRIPLE", [Za, Ea, Ba], [3]), ("h0_TRIPLE", [Ba, Ea, Za], [3]),
                  ("h1_PAIR_EB", [Za, Ea, Ba], [1, 3]), ("h1_PAIR_EB", [Za, Ba, Ea], [1, 3]), ("h0_CTRL_ZE", [Za, Ea], [2]), ("h0_CTRL_ZE", [Ea, Za], [2])]
        used[r["split"]] += len(Q)
        fams.append({"root_id": rid2, "fam": r["fam"], "split": r["split"], "stratum": "CHAIN", "n_jobs": len(Q), "N": len(ids), "probes": r["probes"]})
        for t, seq, b in Q:
            jobs.append({"key": f"KGT3-3D|{rid2}|{t}|{json.dumps(seq)}|{json.dumps(b)}", "root_id": rid2, "fam": r["fam"], "split": r["split"], "stratum": "CHAIN",
                         "template": t, "group": h("grp", rid2, t)[:12], "scene_type": "CONSTRUCTED", "base": [], "path": str(p), "kind": "X_CHUNKED",
                         "order": [[o, [d // 6, d % 6]] for o, d in seq], "seq": [[ids.index(o), d] for o, d in seq], "bounds": b, "y": None})
    # ordinary stratum: clean families with a v32 X = 1 sequence of length >= 2
    snap = C.snapshot_rows("3d", snap=C.SNAP_TRAIN)
    paths = DA.raw_paths("3d")
    consumed = {r["fam"] for r in R}
    for e in families3d():
        if e["fam"] in consumed or e["root_id"] not in snap:
            continue
        sp = e["split"]
        if used[sp] + 4 > CAPS["3d"][sp]:
            continue
        row0 = snap[e["root_id"]]; ids = row0["inputs"]["ids"]
        ws = sorted((q["seq"] for q in row0["labels"]["X"] if q["x"] == 1 and len(q["seq"]) >= 2), key=lambda s: h("w", e["root_id"], json.dumps(s)))
        if not ws:
            continue
        w = [list(map(int, a)) for a in ws[0]]
        Q = [("h0_ORD_PAIR", w[:2], [2]), ("h0_ORD_PAIR", w[:2][::-1], [2])]
        if len(w) >= 3:
            Q += [("h1_ORD_PAIR", [w[0], w[1], w[2]], [1, 3]), ("h1_ORD_PAIR", [w[0], w[2], w[1]], [1, 3])]
        used[sp] += len(Q)
        fams.append({"root_id": e["root_id"], "fam": e["fam"], "split": sp, "stratum": "ORD", "n_jobs": len(Q), "N": e["N"]})
        for t, seq, b in Q:
            jobs.append({"key": f"KGT3-3D|{e['root_id']}|{t}|{json.dumps(seq)}|{json.dumps(b)}", "root_id": e["root_id"], "fam": e["fam"], "split": sp,
                         "stratum": "ORD", "template": t, "group": h("grp", e["root_id"], t)[:12], "scene_type": "S0", "base": [], "path": paths[e["root_id"]],
                         "kind": "X_CHUNKED", "order": [[ids[o], [d // 6, d % 6]] for o, d in seq], "seq": seq, "bounds": b, "y": None})
    assert all(used[s] <= CAPS["3d"][s] for s in CAPS["3d"]), used
    with open(O / "rows3d_con.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    if int(expand):
        init = {j["key"] for j in json.loads((O / "jobs_p2_3d.json").read_text())}
        jobs = [j for j in jobs if j["key"] not in init]
        fams = [f for f in fams if any(j["root_id"] == f["root_id"] for j in jobs)]
    tag = "p2x" if int(expand) else "p2"
    jf = O / f"jobs_{tag}_3d.json"; jf.write_text(json.dumps(jobs, indent=1))
    (O / f"fams_{tag}_3d.json").write_text(json.dumps(fams, indent=1))
    import guard as GD
    s = GD.seal(jf)
    print(json.dumps({"jobs": len(jobs), "used_incl_probes": dict(used), "families": collections.Counter(f"{f['split']}:{f['stratum']}" for f in fams),
                      "templates": collections.Counter(j["template"] for j in jobs), "seal": s["sha256"][:16]}))


# =========================================================================================================== labels
def all_rows(dom):
    R = dict(C.snapshot_rows(dom, snap=C.SNAP_TRAIN))
    f = O / ("rows2d_gen.jsonl" if dom == "2d" else "rows3d_con.jsonl")
    if f.exists():
        R.update({json.loads(l)["root_id"]: json.loads(l) for l in open(f)})
    return R


def labels(dom):
    """Exact chunk labels of the P2 runs (guard-checked complete manifest)."""
    import guard as GD
    import views as V
    jobs, R, kinds = [], {}, {}
    for tag in ("p2", "p2x"):
        jf, rf = O / f"jobs_{tag}_{dom}.json", O / f"phys_{tag}_{dom}.jsonl"
        if tag == "p2x" and not jf.exists():
            continue
        c = GD.complete(jf, rf)
        if c["status"] != "COMPLETE":
            raise SystemExit(f"INCOMPLETE {tag} {c}")
        jobs += json.loads(jf.read_text()); R.update({json.loads(l)["key"]: json.loads(l) for l in open(rf)})
        kinds[tag] = c["kinds"]
    c = {"kinds": kinds}
    rows = all_rows(dom)
    out = []
    for j in jobs:
        r = R[j["key"]]
        if r.get("censored") or r.get("error"):
            continue
        X = r.get("X") or {}
        for ch in LB.chunks_of(j.get("seq_idx") or j["seq"], j["bounds"], X, unknown=LB._unknown(X)):
            out.append({"root_id": j["root_id"], "fam": j["fam"], "split": j["split"], "stratum": j["stratum"], "template": j["template"], "group": j["group"],
                        "scene_type": j["scene_type"], "key": j["key"], "base": [], "prefix": ch["prefix"], "chunk": ch["chunk"], "h": ch["prefix_len"],
                        "m": len(ch["chunk"]), "label": ch["label"], "kind": ch["kind"], "connector_fail": ch["connector_fail"], "N": len(rows[j["root_id"]]["inputs"]["ids"]),
                        "status": str(X.get("teacher_status") or X.get("status") or ""), "phase": X.get("phase") or X.get("failed_phase"), "screen": j.get("screen")})
    with open(O / f"labels_p2_{dom}.jsonl", "w") as f:
        for e in out:
            f.write(json.dumps(e) + "\n")
    print(json.dumps({"labels": len(out), "by": collections.Counter(f"{e['split']}|h{min(e['h'], 1)}|g{e['m']}|y{e['label']}" for e in out), "completion": c["kinds"]}))


if __name__ == "__main__":
    O.mkdir(parents=True, exist_ok=True)
    a = sys.argv[1]
    {"prep2d": prep2d, "build2d": lambda: build2d(*sys.argv[2:3]), "build3d": lambda: build3d(*sys.argv[2:3]), "labels": lambda: labels(sys.argv[2]),
     "construct3d": lambda: construct3d(*sys.argv[2:6])}[a]()
