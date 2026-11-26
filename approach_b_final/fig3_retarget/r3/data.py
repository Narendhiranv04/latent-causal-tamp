#!/usr/bin/env python3
"""R3.1 3D targeted local-X supervision: presealed candidate policy, job builder and exact chunk-label extraction (evaluator side).

Scenes: one root per CLEAN family (no DEV lineage, no R1/R2/R2.4 physical exposure); TRAIN_SCALE from original TRAIN families, VAL_SCALE from
original VAL families (family-disjoint by construction).  N in [5, 9], K_legacy >= 1 first (target initially blocked), sha256 order.
Start scene: S0 (fresh root, q_ref) or, for every third scene, HYPSTART = S0 with 1-2 non-target bodies statically moved to empty legal
cells adjacent to another body (a crowded static layout settled at ideal poses; NOT an executed prefix; reported separately).
Action sources at the start scene (all legal: distinct non-target objects, distinct initially-empty legal non-goal cells):
  P  frozen cVAE proposals (D4)         R  uniform random legal actions        H  model-hard: top frozen marginal pX among 48 P/R singles
  W  verified original X = 1 sequence of the root (S0 scenes only; fragments / permutations)
Templates per scene (chunked teacher runs; every chunk ends with the planned + executed connector to q_ref; a chunk after a failure is unobserved):
  T1 [b]                 b = highest-pX P single                         -> b @ h0
  T2 [a | b]             a = R action on another object                  -> a @ h0, b @ h1            (same action before / after a relocation)
  T3 [hd | x y]          hd in H; (x, y) from P u R                      -> hd @ h0, pair @ h1
  T4 [C]                 C = W fragment (else P), |C| = 2 / 3 by scene   -> C @ h0
  T5 [perm(C)]           another permutation of C (same endpoint)       -> C' @ h0
  T6 [r | t1 t2 t3]      r in R u P; triple from P u R                   -> r @ h0, triple @ h1
  T7 [b' | x]            b' = b's object, alternative destination        -> b' @ h0, x @ h1           (changed destination)
    python data.py build N_TRAIN N_VAL     (GPU: proposals + frozen pX for H)  -> jobs_31_3d.json (+ SEAL), scenes_31_3d.json
    python data.py labels                              -> labels_31_3d.jsonl (+ frozen readouts)"""
from __future__ import annotations

import hashlib, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common3 as K  # noqa: E402
C, LB = K.C, K.LB
import views as V  # noqa: E402

NMIN, NMAX = 5, 9


def hk(*a):
    return hashlib.sha256(("R3.1|" + "|".join(map(str, a))).encode()).hexdigest()


def cell(d):
    return [int(d) // 6, int(d) % 6]


def raw_paths(dom):
    out = {}
    for sp in ("train", "val"):
        for l in open(C.PRIV / f"private_{sp}_{dom}.jsonl"):
            e = json.loads(l)
            out[e.get("root_id", e.get("evaluation_group_id"))] = e["path"]
    return out


def pick_scenes(n_train, n_val):
    lin = json.loads((K.O / "lineage_3d.json").read_text())
    out = {}
    for sp, n in (("train", n_train), ("val", n_val)):
        el = [e for e in lin["eligible"][sp] if NMIN <= e["N"] <= NMAX]
        el.sort(key=lambda e: (str(e["K"]) in ("0", "None"), hk("scene", e["root_id"])))
        seen, sel = set(), []
        for e in el:
            if e["fam"] not in seen:
                seen.add(e["fam"]); sel.append(e)
            if len(sel) >= n:
                break
        out[sp] = sel
    return out


def free_cells(row):
    inp = row["inputs"]
    return sorted(set(int(c) for c in inp["legal_cells"]) - set(int(c) for c in inp["cells0"]) - {int(inp["goal_cell"])})


def crowd(row, rng):
    """1-2 non-target bodies moved to empty legal cells 8-adjacent to another body (static layout edit)."""
    inp = row["inputs"]
    occ = {int(c) for c in inp["cells0"]}
    out = []
    for _ in range(rng.choice((1, 2))):
        el = [o for o in V.eligible(row) if o not in {a for a, _ in out}]
        fr = [d for d in free_cells(V.rebase(row, out)) if any(max(abs(d // 6 - c // 6), abs(d % 6 - c % 6)) == 1 for c in occ)]
        if not el or not fr:
            break
        a = [rng.choice(el), rng.choice(fr)]
        out.append(a); occ.add(a[1])
    return out


class Scene:
    def __init__(self, fz, row0, rid, sp, path, train_rows, hyp):
        self.rng = random.Random(hk("rng", rid))
        self.base = crowd(row0, self.rng) if hyp else []
        self.row = V.rebase(row0, self.base) if self.base else row0
        self.row0, self.rid, self.sp, self.path, self.fz = row0, rid, sp, path, fz
        self.el = V.eligible(self.row)
        self.free = free_cells(self.row)
        D = fz.proposals(self.row, self.el, m=4)
        self.P = sorted({(int(o), int(d)) for o, ds in D.items() for d in ds if int(d) in self.free})
        self.R = sorted({(self.rng.choice(self.el), self.rng.choice(self.free)) for _ in range(32)}) if self.el and self.free else []
        pool = sorted(set(self.P) | set(self.R))
        self.rng.shuffle(pool); pool = pool[:48]
        sc = fz.score(self.row, [[list(a)] for a in pool]) if pool else []
        self.px = {a: s["px"] for a, s in zip(pool, sc)}
        self.H = [a for a, _ in sorted(self.px.items(), key=lambda t: (-t[1], t[0]))[:8]]
        self.W = []
        if not hyp and rid in train_rows:
            ws = [q["seq"] for q in train_rows[rid]["labels"]["X"] if q["x"] == 1 and len(q["seq"]) >= 2]
            if ws:
                self.W = [tuple(map(int, a)) for a in self.rng.choice(sorted(ws))]

    def ok(self, seq):
        return len({o for o, _ in seq}) == len(seq) and len({d for _, d in seq}) == len(seq) and all(d in self.free and o in self.el for o, d in seq)

    def draw(self, src, avoid=(), n=1, tries=200):
        """n distinct legal actions from the source union, avoiding objects / cells used by `avoid`."""
        pool = [a for s in src for a in getattr(self, s)]
        for _ in range(tries):
            if len(pool) < n:
                return None
            c = self.rng.sample(pool, n)
            if self.ok(list(avoid) + c):
                return c
        return None

    def jobs(self, k3):
        T, S = [], {}
        b = max(self.P, key=lambda a: (self.px.get(a, -1), a)) if self.P else (self.draw("R") or [None])[0]
        if b is None:
            return T
        S["b"] = b
        T.append(("T1", [b], [1], ["P"]))
        a = self.draw("R", avoid=[b])
        if a:
            T.append(("T2", [a[0], b], [1, 2], ["R", "P"]))
        hd = next((h for h in self.H if h[0] != b[0]), None)
        if hd:
            xy = self.draw(("P", "R"), avoid=[hd], n=2)
            if xy:
                T.append(("T3", [hd] + xy, [1, 3], ["H", "PR"]))
        k = 3 if k3 else 2
        Cs = None
        if len(self.W) >= k:
            Cs = list(self.W[:k]) if self.ok(list(self.W[:k])) else None
        src = "W" if Cs else "P"
        Cs = Cs or self.draw(("P",), n=k) or self.draw(("P", "R"), n=k)
        if Cs:
            T.append(("T4", Cs, [k], [src]))
            perms = [p for p in __import__("itertools").permutations(Cs) if list(p) != Cs]
            T.append(("T5", list(self.rng.choice(perms)), [k], [src + "-perm"]))
        r = self.draw(("R", "P"))
        if r:
            tr = self.draw(("P", "R"), avoid=r, n=3)
            if tr:
                T.append(("T6", r + tr, [1, 4], ["RP", "PR"]))
        alt = [d for d in self.free if d != b[1]]
        if alt:
            b2 = (b[0], self.rng.choice(alt))
            x = self.draw(("P",), avoid=[b2]) or self.draw(("R",), avoid=[b2])
            if x:
                T.append(("T7", [b2, x[0]], [1, 2], ["P-altdest", "P"]))
        return T


def build(n_train, n_val):
    from models import Frozen
    fz = Frozen("3d"); fz.caps = {}
    rows = C.snapshot_rows("3d", snap=C.SNAP_TRAIN)
    paths = raw_paths("3d")
    sel = pick_scenes(int(n_train), int(n_val))
    jobs, scenes = [], []
    for sp, tag in (("val", "VAL_SCALE"), ("train", "TRAIN_SCALE")):          # validation reserved first
        for i, e in enumerate(sel[sp]):
            rid = e["root_id"]; row0 = rows[rid]
            hyp = i % 3 == 2
            S = Scene(fz, row0, rid, tag, paths[rid], rows, hyp)
            ids = row0["inputs"]["ids"]
            rec = json.loads(Path(paths[rid]).read_text())
            cells0 = None
            if S.base:
                cells0 = {k: list(v) for k, v in rec["initial_cells"].items()}
                for o, d in S.base:
                    cells0[ids[o]] = cell(d)
            T = S.jobs(k3=i % 2 == 0)
            scenes.append({"root_id": rid, "fam": e["fam"], "split": tag, "N": e["N"], "K": e["K"], "scene_type": "HYPSTART" if S.base else "S0",
                           "base": S.base, "n_P": len(S.P), "n_R": len(S.R), "W": bool(S.W), "n_jobs": len(T)})
            for t, seq, bounds, src in T:
                j = {"key": f"R31|{rid}|{t}|{json.dumps(seq)}|{json.dumps(bounds)}", "root_id": rid, "fam": e["fam"], "split": tag, "template": t,
                     "scene_type": "HYPSTART" if S.base else "S0", "base": S.base, "seq": [list(a) for a in seq], "src": src,
                     "path": paths[rid], "kind": "X_CHUNKED", "order": [[ids[o], cell(d)] for o, d in seq], "bounds": bounds, "y": None}
                if cells0:
                    j["cells0"] = cells0
                jobs.append(j)
    cap = K.CEIL["3d"]["R3.1_pilot"][0]
    assert len(jobs) <= cap, len(jobs)
    jf = K.O / "jobs_31_3d.json"; jf.write_text(json.dumps(jobs, indent=1))
    (K.O / "scenes_31_3d.json").write_text(json.dumps(scenes, indent=1))
    (K.O / "jobs_31_3d.json.SEAL").write_text(K.sha(jf))
    import collections
    print(json.dumps({"jobs": len(jobs), "scenes": collections.Counter(s["split"] for s in scenes), "hyp": sum(s["scene_type"] == "HYPSTART" for s in scenes),
                      "templates": collections.Counter(j["template"] for j in jobs), "by_split": collections.Counter(j["split"] for j in jobs),
                      "W_scenes": sum(s["W"] for s in scenes), "seal": K.sha(jf)[:16]}))


def build2d(n_scenes, jobs_per=("T2", "T3", "T6", "T7"), lo=13, hi=20):
    """2D local-X diagnostic (R3.1 3B, <= 60 X-only queries): clean original-VAL families, N in [lo, hi], K_legacy != 0, one root per family;
    S0 scenes only (the 2D teacher has no static start override); templates with an h0 and an h1 label each."""
    from models import Frozen
    fz = Frozen("2d"); fz.caps = {}
    rows = C.snapshot_rows("2d", snap=C.SNAP_TRAIN)
    pg = {}
    for sp in ("val",):
        for l in open(C.PRIV / f"private_{sp}_2d.jsonl"):
            e = json.loads(l); pg[e.get("root_id", e.get("evaluation_group_id"))] = (e["path"], e.get("geom", "original"))
    lin = json.loads((K.O / "lineage_2d.json").read_text())
    el = [e for e in lin["eligible"]["val"] if lo <= e["N"] <= hi and str(e["K"]) not in ("0", "None") and e["root_id"] in pg]
    el.sort(key=lambda e: hk("scene2d", e["root_id"]))
    seen, sel = set(), []
    for e in el:
        if e["fam"] not in seen and len(sel) < int(n_scenes):
            seen.add(e["fam"]); sel.append(e)
    jobs, scenes = [], []
    for e in sel:
        rid = e["root_id"]; row0 = rows[rid]; ids = row0["inputs"]["ids"]
        S = Scene(fz, row0, rid, "VAL_DIAG", pg[rid][0], rows, False)
        T = [t for t in S.jobs(k3=False) if t[0] in jobs_per]
        scenes.append({"root_id": rid, "fam": e["fam"], "split": "VAL_DIAG", "N": e["N"], "K": e["K"], "n_jobs": len(T)})
        for t, seq, bounds, src in T:
            jobs.append({"key": f"R31D|{rid}|{t}|{json.dumps(seq)}|{json.dumps(bounds)}", "root_id": rid, "fam": e["fam"], "split": "VAL_DIAG", "template": t,
                         "scene_type": "S0", "base": [], "seq_idx": [list(a) for a in seq], "src": src, "path": pg[rid][0], "geom": pg[rid][1],
                         "kind": "X_CHUNKED", "seq": [[ids[o], int(d)] for o, d in seq], "bounds": bounds})
    assert len(jobs) <= K.CEIL["2d"]["R3.1_diag"][0], len(jobs)
    jf = K.O / "jobs_31_2d.json"; jf.write_text(json.dumps(jobs, indent=1))
    (K.O / "scenes_31_2d.json").write_text(json.dumps(scenes, indent=1))
    (K.O / "jobs_31_2d.json.SEAL").write_text(K.sha(jf))
    import collections
    print(json.dumps({"jobs": len(jobs), "scenes": len(scenes), "templates": collections.Counter(j["template"] for j in jobs), "seal": K.sha(jf)[:16]}))


def labels(dom="3d"):
    """Exact chunk labels from the R3.1 runs (labels.chunks_of contract; UNKNOWN never negative) + frozen readouts at the start scene."""
    from models import Frozen
    rows = C.snapshot_rows(dom, snap=C.SNAP_TRAIN)
    jobs = json.loads((K.O / f"jobs_31_{dom}.json").read_text())
    R = {json.loads(l)["key"]: json.loads(l) for l in open(K.O / f"phys_31_{dom}.jsonl")}
    out = []
    for j in jobs:
        r = R.get(j["key"])
        if not r or r.get("censored") or r.get("error"):
            continue
        X = r.get("X") or {}
        for c in LB.chunks_of(j.get("seq_idx") or j["seq"], j["bounds"], X, unknown=LB._unknown(X)):
            out.append({"root_id": j["root_id"], "fam": j["fam"], "split": j["split"], "scene_type": j["scene_type"], "template": j["template"],
                        "key": j["key"], "base": j["base"], "prefix": c["prefix"], "chunk": c["chunk"], "h": c["prefix_len"], "m": len(c["chunk"]),
                        "label": c["label"], "kind": c["kind"], "connector_fail": c["connector_fail"], "N": len(rows[j["root_id"]]["inputs"]["ids"]),
                        "status": str(X.get("teacher_status") or X.get("status") or ""), "phase": X.get("phase") or X.get("failed_phase"), "src": j["src"][0] if c["prefix_len"] == 0 else j["src"][-1]})
    fz = Frozen(dom); fz.caps = {}
    for e in out:
        sc = fz.score(V.rebase(rows[e["root_id"]], e["base"] + e["prefix"]), [e["chunk"]])[0]
        e.update({f"f0_{k}": sc[k] for k in ("px", "px1", "px0", "py", "p11")})
    with open(K.O / f"labels_31_{dom}.jsonl", "w") as f:
        for e in out:
            f.write(json.dumps(e) + "\n")
    import collections
    print(json.dumps({"labels": len(out), "by": {f"{k}": v for k, v in collections.Counter((e["split"], e["h"] > 0, e["label"]) for e in out).items()}}))


if __name__ == "__main__":
    {"build": lambda: build(*sys.argv[2:4]), "build2d": lambda: build2d(sys.argv[2]), "labels": lambda: labels(sys.argv[2] if len(sys.argv) > 2 else "3d")}[sys.argv[1]]()
