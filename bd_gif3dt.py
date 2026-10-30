"""GIFs of how 3D open-tabletop (3dt) roots were generated: each stored root is re-run the way bd_3dt.teach built it (same scene file,
same deterministic bd_3dt.query from the settled scene, same MuJoCo run_plan) and filmed. Order follows the teacher: original target
query, scene-only D edits (stills), then every recorded B sequence executed from the initial scene. Every re-planned motion is compared
array-for-array with the stored witness before it is filmed, and each replayed outcome with the recorded y (REPLAY.json); records are
read-only.
    MUJOCO_GL=egl python bd_gif3dt.py <dataset_dir> <out_dir> <root_id> [<root_id> ...]"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import bd_3dt as T

W, H, BAND, EVERY = 360, 270, 64, 120         # panel size, caption band, physics steps per frame (0.24 s of sim at 2 ms)
GOAL, DEST = (0.1, 0.8, 0.2, 0.45), (1.0, 0.85, 0.0, 0.55)   # overlay squares: target goal cell, this step's destination(s)
VIEWS = ({"distance": 1.25, "azimuth": 215, "elevation": -32}, {"distance": 1.05, "azimuth": 180, "elevation": -89})


def font(n):
    try:
        return ImageFont.load_default(size=n)
    except TypeError:
        return ImageFont.load_default()


class Film:
    def __init__(self, e, head):
        import mujoco
        self.e, self.head, self.on, self.n, self.cap, self.marks = e, head, False, 0, "", []
        self.mj = mujoco
        self.frames, self.dur = [], []
        self.r = mujoco.Renderer(e.model, H, W)
        self.cams = []
        for v in VIEWS:
            c = mujoco.MjvCamera()
            c.lookat[:] = [e.x0, 0, e.table_z]
            c.distance, c.azimuth, c.elevation = v["distance"], v["azimuth"], v["elevation"]
            self.cams.append(c)
        step = e.step

        def tick(n=1):
            for _ in range(n):
                step(1)
                self.n += 1
                if self.on and self.n % EVERY == 0:
                    self.shot(60)
        e.step = tick

    def shot(self, ms, cap=None):
        img = Image.new("RGB", (W * len(self.cams), H + BAND), "white")
        for k, c in enumerate(self.cams):
            self.r.update_scene(self.e.data, c)
            self.mark(self.r.scene)
            img.paste(Image.fromarray(self.r.render()), (k * W, BAND))
        d = ImageDraw.Draw(img)
        d.text((8, 5), self.head, fill="#222", font=font(14))
        d.text((8, 44), "green square = target goal cell, yellow = destination(s); cells (row, col), row 0 nearest the robot", fill="#666", font=font(12))
        d.text((8, 24), cap if cap is not None else self.cap, fill="#a01010" if any(x in (cap or self.cap) for x in ("FAIL", "y = 0")) else "#0b5d1e", font=font(13))
        self.frames.append(img)
        self.dur.append(ms)

    def mark(self, scn):
        """Flat translucent squares on the table top (render-only scene geoms; the simulation is untouched)."""
        h = 0.45 * T.env()["geometry"]["pitch"]
        for cell, rgba in self.marks:
            if scn.ngeom < scn.maxgeom:
                self.mj.mjv_initGeom(scn.geoms[scn.ngeom], self.mj.mjtGeom.mjGEOM_BOX, np.array([h, h, 0.0008]),
                                     np.array([*self.e.cell_xy(cell), self.e.table_z + 0.001]), np.eye(3).flatten(), np.array(rgba, np.float32))
                scn.ngeom += 1

    def save(self, path):
        self.frames[0].save(path, save_all=True, append_images=self.frames[1:], duration=self.dur, loop=0, optimize=True)


def cname(r):
    col = {o["id"]: o["color"] for o in r["objects"]}
    return lambda o: f"{o} ({'green, target' if o == 't0' else col.get(o, '?')})"


def load_w(ds, wid):
    z = np.load(Path(ds) / "witnesses" / wid[:2] / f"{wid}.npz")
    return {k: z[k] for k in z.files}


def same(p, w):
    q = [np.asarray(s["q"], float) for s in p["segments"] if s["kind"] != "grip"]
    ph = [k for k, s in enumerate(p["segments"]) if s["kind"] != "grip" for _ in s["q"]]
    a = {"q": np.vstack(q), "segment": np.asarray(ph), "carry_xy": np.asarray(p["carry_xy"], float), "phases": np.asarray([s["phase"] for s in p["segments"]])}
    return all(np.array_equal(a[k], w[k]) for k in a)


def replay(ds, f, e, r, b, nm):
    """One recorded B sequence from the initial scene, filmed; returns per-step witness agreement and the replayed y."""
    cells0, goal = {k: tuple(v) for k, v in r["initial_cells"].items()}, tuple(r["goal"])
    steps = [(o, tuple(d)) for o, d in b["sequence"]] + [("t0", goal)]
    T.settle(e, cells0)
    f.marks = [(goal, GOAL)] + [(tuple(d), DEST) for _, d in b["sequence"]]
    seq = ", ".join(f"{o}->{tuple(d)}" for o, d in b["sequence"]) or "none"
    f.shot(1400, f"B '{b['role']}' sequence [{seq}] then target -> {goal}; recorded y = {b['y']}")
    out, wi = [], 0
    for j, (o, d) in enumerate(steps):
        before = {n: e.cell_of(n) for n in e.obj_index if n != o}
        p, qi = T.query(e, o, d)
        lab = f"step {j + 1}/{len(steps)}: {nm(o)} -> {d}"
        f.marks = [(goal, GOAL)] + ([(d, DEST)] if o != "t0" else [])
        if p is None:
            out.append({"object": o, "dest": list(d), "planned": False})
            f.shot(1800, f"{lab}: FAIL, no feasible side grasp ({qi['tried']} grasp poses tried)")
            return out, 0
        ok = wi < len(b["witnesses"]) and same(p, load_w(ds, b["witnesses"][wi]))
        wi += 1
        f.cap = f"{lab} | grasp {qi['grasp_id']} (azimuth {qi['azimuth']}) | motion == stored witness: {ok}"
        f.on = True
        try:
            e.run_plan(p)
        except T.env()["TS"].GraspFailed as err:
            f.on = False
            out.append({"object": o, "dest": list(d), "planned": True, "witness_match": ok, "executed": False})
            f.shot(1800, f"{lab}: FAIL, grasp failed ({str(err)[:60]})")
            return out, 0
        f.on = False
        h = next(x["height"] for x in r["objects"] if x["id"] == o)
        z = e.obj_pos(o)[2] - e.table_z - h / 2
        moved = sorted(n for n in before if e.cell_of(n) != before[n])
        good = e.cell_of(o) == tuple(d) and abs(z) <= 0.01 and not moved
        out.append({"object": o, "dest": list(d), "planned": True, "witness_match": ok, "executed": good})
        if not good:
            f.shot(1800, f"{lab}: FAIL, execution not verified (end {e.cell_of(o)}, z err {z:.3f}, displaced {moved})")
            return out, 0
    f.shot(1800, f"SUCCESS: all {len(steps)} actions executed and verified (in cell, upright, nothing displaced)")
    return out, 1


def film(ds, root_id, out):
    r = json.loads((Path(ds) / "roots" / f"{root_id}.json").read_text())
    nm, L = cname(r), r["labels"]
    cells0, goal = {k: tuple(v) for k, v in r["initial_cells"].items()}, tuple(r["goal"])
    e = T.build(r["objects"], cells0)
    f = Film(e, f"{root_id} | requested K {r['spec']['K']}, verified K {r['verified_K']} | target {nm('t0')} {tuple(r['target_src'])} -> {goal}")
    T.settle(e, cells0)
    f.marks = [(goal, GOAL)]
    o = L["original"]
    f.shot(2200, f"original scene: target query -> y = {o['y']} ({o['reason']}"
                 + (f"; hits {', '.join(o['hit_objects'])})" if o.get("hit_objects") else ")"))
    for d in L["D"]:
        T.settle(e, {**cells0, **{k: tuple(v) for k, v in d["edit"].items()}})
        f.marks = [(goal, GOAL)] + [(tuple(v), DEST) for v in d["edit"].values()]
        f.shot(1300, f"D edit (scene only, re-query target): park {', '.join(f'{k}->{tuple(v)}' for k, v in d['edit'].items())} -> y = {d['y']}")
    res = []
    for b in L["B"]:
        steps, y = replay(ds, f, e, r, b, nm)
        res.append({"role": b["role"], "recorded_y": b["y"], "replayed_y": y, "steps": steps})
    Path(out).mkdir(parents=True, exist_ok=True)
    f.save(Path(out) / f"{root_id}.gif")
    return {"root_id": root_id, "frames": len(f.frames), "B": res,
            "all_witnesses_match": all(s.get("witness_match", True) for x in res for s in x["steps"]),
            "all_outcomes_match": all(x["recorded_y"] == x["replayed_y"] for x in res)}


if __name__ == "__main__":
    ds, out = sys.argv[1], sys.argv[2]
    for rid in sys.argv[3:]:
        res = film(ds, rid, out)
        (Path(out) / f"{rid}.json").write_text(json.dumps(res, indent=1))
        print(rid, res["frames"], "frames | witnesses match:", res["all_witnesses_match"], "| outcomes match:", res["all_outcomes_match"])
