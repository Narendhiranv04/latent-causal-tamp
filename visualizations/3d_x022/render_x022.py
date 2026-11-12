"""Render recorded X-022 states (no simulation: set qpos + mj_forward on the pinned scene) to .npy images."""
import json, sys
from pathlib import Path
import numpy as np
src = Path("/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass")
sys.path.insert(0, str(src / "code/shelf66_v3"))
import bd_shelf  # noqa
import bd_3dt as A
import mujoco
z = np.load(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(exist_ok=True)
rec = json.loads((src / f"raw/roots/{str(z['root'])}.json").read_text())
e = A.build(rec["objects"], rec["initial_cells"])
m, d = e.model, e.data
W, H = 1800, 1350
m.vis.global_.offwidth, m.vis.global_.offheight = W, H
r = mujoco.Renderer(m, H, W)
root = m.body("link_base").id
robot_geoms = [g for g in range(m.ngeom) if m.body_rootid[m.geom_bodyid[g]] == m.body_rootid[root] and m.geom_bodyid[g] != 0]
ceil = [g for g in range(m.ngeom) if "ceil" in (m.geom(g).name or "")]
print("ceiling geoms", [m.geom(g).name for g in ceil], "robot geoms", len(robot_geoms))
rgba0 = m.geom_rgba.copy()
c = e.scene["camera"]; print("scene camera", c, "table_z", e.table_z)
cx = float(np.mean([e.obj_pos(n)[0] for n in e.obj_index]))
def shot(name, frame, az, el, dist, look, hide_robot=False, hide_ceiling=False):
    m.geom_rgba[:] = rgba0
    if hide_ceiling:
        m.geom_rgba[ceil, 3] = 0
    if hide_robot:
        m.geom_rgba[robot_geoms, 3] = 0
    d.qpos[:] = z["qpos"][frame]; mujoco.mj_forward(m, d)
    cam = mujoco.MjvCamera(); cam.lookat[:] = look; cam.azimuth, cam.elevation, cam.distance = az, el, dist
    r.update_scene(d, cam)
    np.save(out / f"{name}.npy", r.render().copy())
p00 = None
d.qpos[:] = z["qpos"][0]; mujoco.mj_forward(m, d); p00 = e.obj_pos("o00").copy()
shelf = np.array([0.54, 0.0, e.table_z])
for f in (118, 126, 134, 140):
    for az, el in ((-30, -42), (-20, -48)):
        shot(f"pre_f{f}_az{az}_el{el}", f, az, el, 0.95, (p00 + shelf) / 2 + [0, 0, 0.05], hide_ceiling=True)
print("done")
