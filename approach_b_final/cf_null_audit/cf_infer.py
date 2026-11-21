#!/usr/bin/env python3
"""Frozen-weight, inference-only scoring of target-Y for every state of the CF/NULL manifests (labels are never read here).
  Ours (3D / 2D): frozen D bundle scorer s0/s1/s2, ENDPOINT-Y readout p_Y = sigmoid(b) of the empty-edit query (XYNet.predict 'p_noop') on the
                  learner view of the edited scene (contracts.view3d / view2d of the raw record with the edited cells); never p11 / repairs.
  GRN (3D only):  teammates' frozen checkpoints runs/s{0,1,2}/best.pt (yadu/GRN 986cce3a), native graph via build_graphs.make_graph(rec, cells,
                  goal, ...) exactly as evaluate_grn.scene_graphs scores candidate layouts; output = sigmoid of the 'action' head.
PIGINet-noimg (3D only): teammates' frozen runs/noimg_s{0,1,2}/best.pt (yadu/PIGINet 1045e070, image branch off -- new states have no
                  renders), native "move T" sample on the EDITED initial state (build_data.root_samples form: objects in record order, cells =
                  edited cells, plan [(t0, start, goal)]) scored by train.predict(use_image=False) = sigmoid of the plan-feasibility head.
SCNet (3D only):  teammates' frozen runs/adam_s{0,1,2}/best.pt, state score = max over the target's 32 grasps of P(grasp works)
                  (train_scn.score_states); point cloud scn_geometry.scene_cloud(objects, edited cells, n_total 8192) with a COMMON seed per
                  base lineage (sha256('CFSCN|root_id')) so BASE / CF / NULL differ only by the moved obstacle; grasp poses / goal shift rebuilt
                  from the teacher (scn_geometry.grasps_of) -- parity 240/240 with the stored roots_scn.pkl; needed for 48 D3H TEST roots
                  absent from it.  Inputs are computed in env3d by `cf_scnroots.py MANIFEST OUT.pkl` (teacher import, no torch).
Visibility assert: the moved obstacle's model input differs between BASE and the edited state (Ours: its xy0 row; GRN: its node pose).
    python cf_infer.py 3d|2d MANIFEST.jsonl OUT.jsonl            (manifest rows: {qid, root_id, path, cells, geom?})"""
import json, os, sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import contracts as CT  # noqa: E402
import xy as XY  # noqa: E402

BUNDLE = Path(os.environ.get("CF_BUNDLE", str(Path.home() / "abf_v34/approach_b_bundle")))
GRN_DIR = Path(os.environ.get("CF_GRN", ""))


def view_of(dom, rec, cells):
    r = json.loads(json.dumps(rec))
    if dom == "3d":
        r["initial_cells"] = {k: list(v) for k, v in cells.items()}
        return CT.view3d(r)
    lat = r["scene"]["lattice"]
    for o in r["scene"]["objects"]:
        c = int(cells[o["id"]])
        o["cell"], o["xy_m"] = c, [lat["pitch_m"] * (c % lat["cols"] + 0.5), lat["pitch_m"] * (c // lat["cols"] + 0.5)]
    return CT.view2d(r)


@torch.no_grad()
def ours(dom, rows, recs):
    out = {}
    views = []
    for q in rows:
        inp = view_of(dom, recs[q["qid"]], q["cells"])
        v, _, _ = XY.make_view(q["qid"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], [], [], XY._NoGeo)
        views.append((q["qid"], v, inp))
    for s in (0, 1, 2):
        net = XY.load_model(BUNDLE / dom / f"scorer_s{s}.pt", "cuda")
        for i in range(0, len(views), 256):
            ch = views[i:i + 256]
            b, _ = XY.collate([c[1] for c in ch], device="cuda", dtype=torch.float32)
            p = net.predict(b)["p_noop"].double().cpu().numpy()
            for (qid, _, _), x in zip(ch, p):
                out.setdefault(qid, {})[f"ours_s{s}"] = float(x)
        del net; torch.cuda.empty_cache()
    return out, {qid: inp["xy0"] for qid, _, inp in views}


@torch.no_grad()
def grn(rows, recs):
    sys.path.insert(0, str(GRN_DIR))
    import build_graphs as BG
    import evaluate_grn as EG
    graphs = []
    for q in rows:
        rec = recs[q["qid"]]
        cells = {k: tuple(v) for k, v in q["cells"].items()}
        graphs.append(BG.make_graph(rec, cells, tuple(rec["goal"]), 0, None, q["root_id"], "cand", None, None))
    out = {}
    for s in ("s0", "s1", "s2"):
        m = EG.load(s)
        A, _, _, _ = EG.forward_all(m, graphs)
        for q, a in zip(rows, A):
            out.setdefault(q["qid"], {})[f"grn_{s}"] = float(a)
        del m; torch.cuda.empty_cache()
    return out, {q["qid"]: g for q, g in zip(rows, graphs)}


PIG_DIR = Path(os.environ.get("CF_PIG", ""))
SCN_DIR = Path(os.environ.get("CF_SCN", ""))


def objs_of(rec):
    return [dict(id=o["id"], shape=o["shape"], size=float(o["size"]), height=float(o["height"]), color=o.get("color")) for o in rec["objects"]]


@torch.no_grad()
def piginet(rows, recs):
    sys.path.insert(0, str(PIG_DIR))
    import train as PT
    from piginet import PIGINet, tokens
    S = []
    for q in rows:
        rec = recs[q["qid"]]
        cells = {k: tuple(v) for k, v in q["cells"].items()}
        goal = tuple(rec["goal"])
        S.append(dict(rid=q["root_id"], kind="D", idx=None, objects=objs_of(rec), cells=cells, plan=[("t0", cells["t0"], goal)], goal=goal, y=0))
    out = {}
    for s in (0, 1, 2):
        cfg = json.load(open(PIG_DIR / "runs" / f"noimg_s{s}" / "config.json"))
        assert cfg["no_image"] and not cfg["no_value"]
        m = PIGINet(use_image=False, use_value=True).to(PT.DEV)
        m.load_state_dict(torch.load(PIG_DIR / "runs" / f"noimg_s{s}" / "best.pt", map_location=PT.DEV))
        m.set_text(np.load(PIG_DIR / "data" / "text.npz")["feats"])
        p = PT.predict(m.eval(), S, False, bs=1024)
        for q, x in zip(rows, p):
            out.setdefault(q["qid"], {})[f"piginet_s{s}"] = float(x)
        del m; torch.cuda.empty_cache()
    import hashlib
    sig = {q["qid"]: hashlib.sha256(b"".join(np.ascontiguousarray(a).tobytes() for a in tokens(x)[1:3])).hexdigest()[:20] for q, x in zip(rows, S)}
    return out, sig


@torch.no_grad()
def scnet(rows, recs):
    import hashlib, pickle
    sys.path.insert(0, str(SCN_DIR))
    import scn_geometry as G
    import train_scn as ST
    from scn_model import SCN, feasible_logprob
    R = pickle.load(open(os.environ["CF_SCN_ROOTS"], "rb"))
    clouds, sig = [], {}
    for q in rows:
        r = R[q["path"]]
        cells = {k: tuple(v) for k, v in q["cells"].items()}
        assert cells["t0"] == r["start"]                        # target never moved by an edit: grasp poses are those of the base
        seed = int(hashlib.sha256(("CFSCN|" + q["root_id"]).encode()).hexdigest()[:8], 16) % (1 << 30)
        pts = G.scene_cloud(objs_of(recs[q["qid"]]), cells, n_total=8192, seed=seed)
        clouds.append(pts); sig[q["qid"]] = hashlib.sha256(pts.tobytes()).hexdigest()[:20]
    out = {}
    for s in (0, 1, 2):
        m = SCN(G.gripper_cloud()).to(ST.DEV)
        m.load_state_dict(torch.load(SCN_DIR / "runs" / f"adam_s{s}" / "best.pt", map_location=ST.DEV))
        m.eval()
        for i in range(0, len(rows), 32):
            ch = rows[i:i + 32]
            f = lambda k: torch.from_numpy(np.stack([R[q["path"]][k] for q in ch])).to(ST.DEV)  # noqa: E731
            zp, zl = m(torch.from_numpy(np.stack(clouds[i:i + 32])).to(ST.DEV), f("pos"), f("R"), f("shift"))
            P = feasible_logprob(zp, zl).exp().cpu().numpy()
            for q, x in zip(ch, P):
                out.setdefault(q["qid"], {})[f"scnet_s{s}"] = float(x.max())
                if q.get("grasp_id") is not None:                   # the paper's unit: P(the fixed grasp g* works)
                    out[q["qid"]][f"scnetgrasp_s{s}"] = float(x[int(q["grasp_id"])])
        del m; torch.cuda.empty_cache()
    return out, sig


def main(dom, man, outp):
    torch.manual_seed(0)
    rows = [json.loads(l) for l in open(man)]
    raw = {p: json.loads(Path(p).read_text()) for p in {q["path"] for q in rows}}
    recs = {}                                                     # per state: the record plus any INSERTED objects (PROP_INS_3D, amendment 4)
    for q in rows:
        r = raw[q["path"]]
        if q.get("extra_objects"):
            r = json.loads(json.dumps(r)); r["objects"] = r["objects"] + q["extra_objects"]
        recs[q["qid"]] = r
    sc, xy0 = ours(dom, rows, recs)
    gsig = None
    if dom == "3d" and GRN_DIR.name:
        g, graphs = grn(rows, recs)
        for k, v in g.items():
            sc[k].update(v)
        import hashlib
        gsig = {k: hashlib.sha256(np.asarray(gr["x"], float).round(6).tobytes() + np.asarray(gr["eattr"], float).round(6).tobytes()).hexdigest()[:20]
                for k, gr in graphs.items()}
    psig = ssig = None
    if dom == "3d" and PIG_DIR.name:
        g, psig = piginet(rows, recs)
        for k, v in g.items():
            sc[k].update(v)
    if dom == "3d" and SCN_DIR.name:
        g, ssig = scnet(rows, recs)
        for k, v in g.items():
            sc[k].update(v)
    with open(outp, "w") as f:
        for q in rows:
            f.write(json.dumps({"qid": q["qid"], "root_id": q["root_id"], **sc[q["qid"]], "ours_input_xy0": xy0[q["qid"]],
                                "grn_input_sig": gsig.get(q["qid"]) if gsig else None, "piginet_input_sig": psig.get(q["qid"]) if psig else None,
                                "scnet_input_sig": ssig.get(q["qid"]) if ssig else None}) + "\n")
    print(json.dumps({"dom": dom, "n": len(rows), "models": sorted(next(iter(sc.values())).keys())}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
