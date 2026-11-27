#!/usr/bin/env python3
"""R4 execution GIFs from ACTUAL logged physical runs (never re-planned, never artistic):
  2D  certified BXY joint records of an x_chunked run (move + connector witnesses from FIG3_WOUT), drawn with the teacher's own robot geometry
      (geometry.bodies: links, housings, palm, rail, fingers; held disc at the tool point); failures end on a captioned still.
  3D  independent MuJoCo re-execution of the stored move / connector witnesses of a run (same code path as physical3d.replay), filmed with the
      teacher's bd_gif3dt.Film (two views); failures end on a captioned still of the reached state.
    $PY2D gifs.py 2d SPEC.json OUT_DIR      SPEC = [{"rec": path, "trace": [...], "seq": [[o, d]], "bounds": [...], "title": str, "fail": str|null}]
    MUJOCO_GL=egl $PY3D gifs.py 3d SPEC.json OUT_DIR   SPEC = [{"path": rec path, "x": X result (with trace), "title": str, "cells0": optional}]"""
from __future__ import annotations

import json, os, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]


def gif2d(spec, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon
    from PIL import Image
    import physical2d as P2
    P2.boot("original")
    import geometry as ge
    robot = P2.M["E"]["robot"]
    wout = Path(os.environ.get("FIG3_WOUT", P2.M["out"]))
    rec = json.loads(Path(spec["rec"]).read_text())
    cells = {o["id"]: int(o["cell"]) for o in rec["scene"]["objects"]}
    goal = rec["goal_cell"]
    xy = lambda c: (0.04 + 0.08 * (c % 8), 0.04 + 0.08 * (c // 8))  # noqa: E731
    dests = {o: int(d) for o, d in spec["seq"]}
    frames = []

    def draw(q, gap, held, cap, color="#0b5d1e"):
        fig, ax = plt.subplots(figsize=(4.6, 5.0), dpi=80)
        for c in range(64):
            ax.add_patch(Polygon([[0.08 * (c % 8), 0.08 * (c // 8)], [0.08 * (c % 8 + 1), 0.08 * (c // 8)], [0.08 * (c % 8 + 1), 0.08 * (c // 8 + 1)], [0.08 * (c % 8), 0.08 * (c // 8 + 1)]],
                                 fc="#f6f8fa" if (c % 8 + c // 8) % 2 else "white", ec="#eaeef2", lw=0.4))
        for o, d in dests.items():
            ax.add_patch(Circle(xy(d), 0.026, fc="none", ec="#bf8700", lw=1.2, ls="--"))
            ax.text(*xy(d), o[1:], ha="center", va="center", fontsize=6, color="#bf8700")
        ax.add_patch(Polygon([[0.08 * (goal % 8) + 0.01, 0.08 * (goal // 8) + 0.01], [0.08 * (goal % 8) + 0.07, 0.08 * (goal // 8) + 0.01],
                              [0.08 * (goal % 8) + 0.07, 0.08 * (goal // 8) + 0.07], [0.08 * (goal % 8) + 0.01, 0.08 * (goal // 8) + 0.07]], fc="#dafbe1", ec="#1a7f37", lw=0.8))
        for o, c in cells.items():
            if held and o == held[0]:
                continue
            ax.add_patch(Circle(xy(c), 0.024, fc="#1a7f37" if o == "t0" else ("#cf222e" if o in dests else "#8c959f"), ec="#1f2328", lw=0.5))
            ax.text(*xy(c), o if o == "t0" else o[1:], ha="center", va="center", fontsize=6, color="white")
        if held:
            ax.add_patch(Circle(held[1], 0.024, fc="#cf222e", ec="#1f2328", lw=0.5))
        for name, (core, r) in ge.bodies(robot, q, gap).items():
            core = np.asarray(core)
            if len(core) == 1:
                ax.add_patch(Circle(core[0], max(r, 0.004), fc="#0969da", ec="#0a3069", lw=0.4, alpha=0.9))
            elif r > 0:
                a, b = core[0], core[-1]
                n = np.array([-(b - a)[1], (b - a)[0]]); n = n / (np.linalg.norm(n) + 1e-12) * r
                ax.add_patch(Polygon([a + n, b + n, b - n, a - n], fc="#0969da", ec="#0a3069", lw=0.4, alpha=0.9))
            else:
                ax.add_patch(Polygon(core, fc="#0550ae", ec="#0a3069", lw=0.4))
        ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(spec["title"], fontsize=7.5, loc="left")
        ax.text(lim[0][0] + 0.01, lim[1][0] + 0.01, cap, fontsize=7, color=color)
        fig.canvas.draw()
        img = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).convert("RGB")
        plt.close(fig)
        return img
    q0 = np.asarray(rec["q0"], float)
    pts = np.vstack([np.asarray(c).reshape(-1, 2) for c, _ in ge.bodies(robot, q0, 0.07).values()] + [np.array([[0, 0], [0.64, 0.64]])])
    lim = [(pts[:, 0].min() - 0.06, pts[:, 0].max() + 0.06), (pts[:, 1].min() - 0.08, pts[:, 1].max() + 0.06)]
    frames.append((draw(q0, 0.07, None, "initial scene; dashed = declared destinations, green square = target goal"), 1200))
    j = 0
    for it in spec["trace"]:
        z = np.load(wout / "witnesses" / it["witness"][:2] / f"{it['witness']}.npz")
        a = {k: z[k] for k in z.files}
        Q = np.asarray(a["q"], float); G = np.asarray(a["gap"], float)
        att = np.asarray(a.get("attached", np.zeros(len(Q), bool)))
        hl = np.asarray(a.get("held_local", np.zeros((0,))))
        n_ = min(len(Q), len(G), len(att)) if att.ndim else min(len(Q), len(G))
        Q, G = Q[:n_], G[:n_]
        att = att[:n_] if att.ndim else np.full(n_, bool(att))
        step = max(1, len(Q) // 14)
        for t in list(range(0, len(Q), step)) + [len(Q) - 1]:
            held = None
            if it["kind"] == "move" and att[t] and hl.size:
                loc = hl[t] if hl.ndim == 2 else hl
                held = (it["object"], ge.tool_point(robot, Q[t], loc))
            cap = f"move {j + 1}: {it['object']} -> cell {it['dest']}" if it["kind"] == "move" else f"connector to q_ref after move {it['after_move']} (chunk boundary)"
            frames.append((draw(Q[t], G[t], held, cap, "#0a3069" if it["kind"] == "connector" else "#0b5d1e"), 90))
        if it["kind"] == "move":
            cells[it["object"]] = int(it["dest"]); j += 1
    qend = Q[-1] if spec["trace"] else q0
    fin = spec.get("fail")
    frames.append((draw(qend, 0.07, None, fin or "SUCCESS: every relocation and boundary connector certified; independent replay passed", "#cf222e" if fin else "#0b5d1e"), 2200))
    frames[0][0].save(out, save_all=True, append_images=[f for f, _ in frames[1:]], duration=[d for _, d in frames], loop=0, optimize=True)


class Film3:
    """Shelf-env film: the environment scene camera + a low side view (the shelf roof hides a top view); a frame every EVERY physics steps (e.step hook, render only)."""
    EVERY, W, H, BAND = 220, 320, 240, 58

    def __init__(self, e, head):
        import mujoco
        from PIL import Image, ImageDraw, ImageFont
        self.mj, self.Image, self.Draw, self.F = mujoco, Image, ImageDraw, ImageFont.load_default()
        self.e, self.head, self.on, self.n, self.cap, self.frames, self.dur = e, head, False, 0, "", [], []
        self.r = mujoco.Renderer(e.model, self.H, self.W)
        sc = e.scene["camera"]
        self.cams = []
        for d, az, el in ((sc["distance"], sc["azimuth"], sc["elevation"]), (sc["distance"] * 0.8, sc["azimuth"] + 70.0, -18.0)):
            c = mujoco.MjvCamera(); c.lookat[:] = sc["lookat"]; c.distance, c.azimuth, c.elevation = d, az, el
            self.cams.append(c)
        step = e.step

        def tick(n=1):
            for _ in range(n):
                step(1); self.n += 1
                if self.on and self.n % self.EVERY == 0:
                    self.shot(110)
        e.step = tick

    def shot(self, ms, cap=None):
        img = self.Image.new("RGB", (self.W * 2, self.H + self.BAND), "white")
        for k, c in enumerate(self.cams):
            self.r.update_scene(self.e.data, c)
            img.paste(self.Image.fromarray(self.r.render()), (k * self.W, self.BAND))
        d = self.Draw.Draw(img)
        txt = cap if cap is not None else self.cap
        d.text((6, 4), self.head[:120], fill="#222", font=self.F)
        d.text((6, 22), txt[:120], fill="#a01010" if "FAIL" in txt else "#0b5d1e", font=self.F)
        d.text((6, 40), "left: scene camera, right: side view; actual MuJoCo re-execution of the stored teacher witnesses", fill="#666", font=self.F)
        self.frames.append(img); self.dur.append(ms)

    def save(self, path):
        self.frames[0].save(path, save_all=True, append_images=self.frames[1:], duration=self.dur, loop=0, optimize=True)


def gif3d(spec, out):
    sys.path.insert(0, str(HERE.parent.parent / "compose3d_k45"))
    import evaluate_k45 as EV
    EV.boot(os.environ["FIG3_STORE"])
    W = EV.W; A, S, BP = W["A"], W["S"], W["BP"]
    rec = json.loads(Path(spec["path"]).read_text())
    if spec.get("cells0"):
        rec = {**rec, "initial_cells": spec["cells0"]}
    e = A.build(rec["objects"], rec["initial_cells"]); A.settle(e, rec["initial_cells"])
    f = Film3(e, spec["title"])
    expected = {k: tuple(v) for k, v in rec["initial_cells"].items()}
    f.shot(1200, "initial scene")
    for st in spec["x"]["trace"]:
        if st["kind"] == "move":
            w = BP.witness(st["witness"], W["base"])
            f.cap = f"relocation: {st['object']} -> cell {tuple(st['dest'])} (stored teacher witness, re-executed)"; f.on = True
            r = BP.move(e, S, rec, st["object"], tuple(st["dest"]), w, st["grasp_id"])
            f.on = False
            expected[st["object"]] = tuple(st["dest"])
            if not r["ok"]:
                f.shot(1800, f"FAIL during replay: {r.get('failure')}"); break
        else:
            z = np.load(Path(W["base"]) / "witnesses" / st["witness"][:2] / f"{st['witness']}.npz")
            f.cap = f"connector to q_ref after move {st['after_move']} (chunk boundary)"; f.on = True
            BP.connector(e, S, expected, path=z["connector_q"])
            f.on = False
    x = spec["x"]
    f.shot(2400, "SUCCESS: all relocations + boundary connectors executed and replayed" if x.get("x") == 1 else f"FAIL at {x.get('phase')}: {x.get('status')} (teacher outcome; reached state shown)")
    f.save(out)


if __name__ == "__main__":
    dom, sp, od = sys.argv[1:4]
    Path(od).mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(json.loads(Path(sp).read_text())):
        p = Path(od) / s.get("name", f"{dom}_{i:02d}.gif")
        try:
            (gif2d if dom == "2d" else gif3d)(s, p)
            print("wrote", p, flush=True)
        except Exception as e:  # noqa: BLE001
            import traceback
            print("FAILED", p, type(e).__name__, str(e)[:200], traceback.format_exc()[-500:], flush=True)
