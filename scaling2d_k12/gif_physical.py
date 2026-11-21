#!/usr/bin/env python3
"""Physical-execution GIFs of the released scenes, drawn ONLY from the teacher's stored witness arrays (no schematic, no re-planning in the
renderer).  Adapted from the frozen teacher's own animation (teacher2d_wt/bxy_pilot_viz.gif_root).
  dump    per scene, in a fresh teacher process: X(witness) and Y(witness) with out=OUT so every record (relocation segments, the connector to
          q_ref, the target pick-and-place from q_ref) is written as content-addressed .npz; the record ids are compared with the certified ids
          (search / G5) -> 'hash_match' per scene (host numerics: girish-produced witnesses must be dumped on girish)
  render  frames: each relocation's records (the moved disc drawn at the tool point while carried), then the connector back to q_ref, then the
          target move T -> goal from q_ref (Y); scene state updated after every relocation; one fixed view per scene
    python gif_physical.py dump   LAYOUTS.jsonl WITNESS.jsonl OUT_DIR MANIFEST.jsonl
    python gif_physical.py render LAYOUTS.jsonl MANIFEST.jsonl OUT_DIR GIF_DIR [WORKERS]"""
import json, sys
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def dump(lay_f, wit_f, out, man_f):
    import mink as MK, witness as W
    Ls = {json.loads(l)["root_id"]: json.loads(l) for l in open(lay_f)}
    out = str(Path(out).resolve()); man_f = str(Path(man_f).resolve())
    rows = []
    for w in (json.loads(l) for l in open(wit_f)):
        L = Ls[w["root_id"]]
        MK.boot(L["geom"])
        import teacher_long as TL
        E = MK._M["E"]
        rec, ids = W.rec_of(L, L["geom"])
        fin = next(t for t in w["tries"] if t.get("final"))
        seq = [tuple(t) for t in fin["seq"]]
        x = TL.x_query(E, L["root_id"], rec, seq, {}, out=out)
        y = TL.y_query(E, L["root_id"], rec, seq, {}, out=out)
        steps = [st.get("witness") for st in (x.get("steps") or [])]
        rows.append({"root_id": L["root_id"], "K": len(seq), "seq": [list(t) for t in seq], "x": x.get("y"), "y": y.get("y"),
                     "steps_witness": steps, "witness_relocations": x.get("witness_relocations"), "witness_connector": x.get("witness_connector"),
                     "target_witness": y.get("target_witness"), "x_replay": x.get("independent_replay"), "y_replay": y.get("independent_replay"),
                     "hash_match": steps == fin.get("x_steps_witness") and y.get("target_witness") == fin.get("y_witness")})
        print(json.dumps({k: rows[-1][k] for k in ("root_id", "K", "x", "y", "hash_match")}), flush=True)
    with open(man_f, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _render(args):
    L, m, out, gdir = args
    import mink as MK, witness as W
    MK.boot(L["geom"])
    import bxy_teacher as T
    import bd_viz as BV
    import geometry as ge
    import motion as mo
    import p16_motion as pm
    import viz
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from dataclasses import replace
    from PIL import Image
    E = MK._M["E"]
    rec, ids = W.rec_of(L, L["geom"])
    k = L["root_id"]
    scene = lambda cells, q: pm.DetPhysics(T.task_of(k, rec), None).scene(cells, q)  # noqa: E731
    seq = [tuple(t) for t in m["seq"]]
    parts = []
    for j, ((o, d), ws) in enumerate(zip(seq, m["steps_witness"])):
        for wi, w in enumerate(ws):
            parts.append((f"relocation {j + 1}/{len(seq)}: {o} -> cell {d}", o, T.load_w(out, w), j if wi == len(ws) - 1 else None))
    parts.append(("connector back to q_ref", None, T.load_w(out, m["witness_connector"]), None))
    parts.append(("target T -> goal from q_ref (Y)", "t0", T.load_w(out, m["target_witness"]), None))
    import bxy_data as bd
    cells = bd.cells0(rec)
    q0 = T.qref(rec)
    f0, a0 = plt.subplots()
    BV._scene2d(a0, scene(cells, q0), rec["goal_cell"], E["robot"], rec["roles"], rec["fixed_ids"], (), (), "", q=q0)
    plt.close(f0)
    pts = np.array([p for _, _, a, _ in parts for qq, _, _ in mo.samples(a, 12) for p in ge.fk(E["robot"], qq)[0]])
    pad = 0.08
    lim = ((min(a0.get_xlim()[0], pts[:, 0].min() - pad), max(a0.get_xlim()[1], pts[:, 0].max() + pad)),
           (min(a0.get_ylim()[0], pts[:, 1].min() - pad), max(a0.get_ylim()[1], pts[:, 1].max() + pad)))
    frames = []

    def frame(cells_, qq, g, title, held, a):
        shown = {kk: v for kk, v in cells_.items() if kk != held}
        fig, ax = plt.subplots(figsize=(5.4, 4.6))
        s = scene(cells_, qq)
        s = replace(s, objects=tuple(ob for ob in s.objects if ob.id in shown))
        BV._scene2d(ax, s, rec["goal_cell"], E["robot"], rec["roles"], rec["fixed_ids"], (), (), title)
        viz.draw_robot(ax, E["robot"], qq, g, alpha=0.9, zorder=8)
        ax.set(xlim=lim[0], ylim=lim[1])
        if held:
            ax.add_patch(plt.Circle(ge.tool_point(E["robot"], qq, tuple(a["held_local"])), 0.024, fc="#f6b26b" if held != "t0" else "#1baf7a", ec="k", zorder=9))
        ax.title.set_fontsize(8)
        fig.canvas.draw()
        im = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3])
        plt.close(fig)
        return im
    hdr = f"{k}  K={len(seq)} (certified min)  {len(ids)} objects"
    frames += [frame(cells, q0, float(T.ref_gap(rec)), f"{hdr}\ninitial scene: target infeasible (Y0 = 0)", None, None)] * 6
    for lab, o, a, done_j in parts:
        n = 16 if lab.startswith("relocation") else (10 if lab.startswith("connector") else 16)
        for qq, g, ph in mo.samples(a, n):
            frames.append(frame(cells, qq, g, f"{hdr}\n{lab} [{ph}]", o if ph == "carry" else None, a))
        if done_j is not None:
            cells = {**cells, seq[done_j][0]: int(seq[done_j][1])}
    fin_cells = {**cells, "t0": rec["goal_cell"]}
    frames += [frame(fin_cells, q0, float(T.ref_gap(rec)), f"{hdr}\ndone: X = 1, Y = 1 (independently replayed)", None, None)] * 8
    gdir = Path(gdir); gdir.mkdir(parents=True, exist_ok=True)
    p = gdir / f"K{len(seq)}_{k}.gif"
    frames = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in frames]
    frames[0].save(p, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)
    return {"root_id": k, "gif": str(p), "frames": len(frames)}


def render(lay_f, man_f, out, gdir, workers=4):
    Ls = {json.loads(l)["root_id"]: json.loads(l) for l in open(lay_f)}
    M = [json.loads(l) for l in open(man_f)]
    out, gdir = str(Path(out).resolve()), str(Path(gdir).resolve())
    with get_context("spawn").Pool(int(workers), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(_render, [(Ls[m["root_id"]], m, out, gdir) for m in M]):
            print(json.dumps(r), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    dump(*a[1:5]) if a[0] == "dump" else render(*a[1:6])
