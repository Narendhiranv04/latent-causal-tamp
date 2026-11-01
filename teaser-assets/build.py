"""Text-free K4 teaser illustration assets: a CONCEPTUAL planar-3R rearrangement example (not a verified dataset witness).

    python teaser-assets/build.py            # writes svg/, png/, manifest.json and previews/ inside teaser-assets/

Geometry (lattice pitch, disc radius, base, link lengths/widths, gripper, home q) is read from config.toml so the figure matches the
2D domain. Every SVG shares one viewBox (world metres -> px, y up). Poses come from analytic IK; a schematic capsule-vs-disc check
confirms the drawn blocked modes collide and the drawn repaired poses clear (a drawing sanity check, not planner certification)."""
from __future__ import annotations

import json
import math
import subprocess
import tomllib
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CFG = tomllib.loads((HERE.parent / "config.toml").read_text())
SU, ARM, GR = CFG["suite"], CFG["arm2d"], CFG["gripper2d"]
H, R = SU["pitch_m"], SU["obstacle_radius_m"]
BASE, LL, LW = np.array(ARM["base_xy_m"]), ARM["link_lengths_m"], ARM["link_full_widths_m"]
Q_CFG_HOME = ARM["q_home_rad"]
Q_HOME = [math.pi, math.pi / 2, math.pi / 2]                                  # figure reference pose: config home rotated +90 deg about the base (faces right)
GC = GR["grasp_center_x_m"]

PAPER, SLATE, CLAY = "#F7F5F0", "#263840", "#B56852"
X0, X1, Y0, Y1, S = -0.60, 0.76, -0.08, 0.84, 1000.0                       # world window [m] and px per metre
VW, VH = round((X1 - X0) * S), round((Y1 - Y0) * S)
VIEWBOX = f"0 0 {VW} {VH}"

# ---- conceptual scene (cells are (row, col); centre = ((c + 1/2) h, (r + 1/2) h), as scene.Lattice.center) --------------------------
TARGET, GOAL = (4, 3), (2, 6)
ORDER = ["b1", "b2", "b3", "b4"]                                             # relocation order
BLOCK = {"b1": (5, 2), "b2": (3, 2), "b3": (4, 2), "b4": (2, 5)}            # NW, SW, W of target; W of goal
PARK = {"b1": (7, 3), "b2": (1, 1), "b3": (6, 4), "b4": (0, 5)}            # outside the final elbow-up sweep
CONTEXT = [(7, 6), (5, 6), (0, 0), (1, 3), (0, 7), (2, 0)]                   # discs that never matter
ELBOW = -1                                                                   # elbow-up branch (keeps the arm above the lattice)
TARGET_MODES = [0.0, math.pi / 4, -math.pi / 4]                              # declared side-grasp approach headings at the target
GOAL_MODES = [0.0]                                                            # declared placement heading at the goal


def xy(cell):
    r, c = cell
    return np.array([(c + 0.5) * H, (r + 0.5) * H])


def P(p):
    return (p[0] - X0) * S, (Y1 - p[1]) * S


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


# ---- kinematics ----------------------------------------------------------------------------------------------------------------
def fk(q):
    pts, a, p = [BASE.copy()], 0.0, BASE.copy()
    for qi, li in zip(q, LL):
        a += qi
        p = p + li * np.array([math.cos(a), math.sin(a)])
        pts.append(p)
    return pts, a                                                            # joints p0..p3 (p3 = TCP at palm tip), tool heading


def ik(obj, a, elbow):
    """Joint angles placing the grasped-object centre at `obj` with tool heading `a` (approach direction), or None."""
    u = np.array([math.cos(a), math.sin(a)])
    w = obj - GC * u - LL[2] * u - BASE
    d = float(np.linalg.norm(w))
    c2 = (d * d - LL[0] ** 2 - LL[1] ** 2) / (2 * LL[0] * LL[1])
    if abs(c2) > 1:
        return None
    q2 = elbow * math.acos(c2)
    q1 = math.atan2(w[1], w[0]) - math.atan2(LL[1] * math.sin(q2), LL[0] + LL[1] * math.cos(q2))
    return [q1, q2, a - q1 - q2]


def gripper_rects(tcp, a, gap):
    """Palm, rail and two fingers as (centre, heading, length along heading, width) rectangles."""
    u, n = np.array([math.cos(a), math.sin(a)]), np.array([-math.sin(a), math.cos(a)])
    t, fl = GR["finger_thickness_m"], GR["finger_length_m"]
    rail_w = gap + 2 * t
    out = [(tcp - 0.5 * GR["palm_length_m"] * u, a, GR["palm_length_m"], GR["palm_full_width_m"]),
           (tcp + 0.5 * GR["rail_depth_m"] * u, a, GR["rail_depth_m"], rail_w)]
    for s in (-1, 1):
        out.append((tcp + 0.5 * fl * u + s * (gap / 2 + t / 2) * n, a, fl, t))
    return out


# ---- schematic collision (capsules / rect-as-capsule vs discs) ---------------------------------------------------------------------
def seg_dist(p, a, b):
    ab = b - a
    s = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1)
    return float(np.linalg.norm(p - (a + s * ab)))


def body(q, gap):
    pts, a = fk(q)
    caps = [(pts[i], pts[i + 1], LW[i] / 2) for i in range(3)]
    for c, h, ln, wd in gripper_rects(pts[3], a, gap):
        u = np.array([math.cos(h), math.sin(h)]) * ln / 2
        n = np.array([-math.sin(h), math.cos(h)]) * max(wd / 2 - min(ln, wd) / 2, 0)
        r = min(ln, wd) / 2
        caps += [(c - u + n, c + u + n, r), (c - u - n, c + u - n, r)] if wd > ln else [(c - u, c + u, r)]
    return caps, pts, a


def hits(q, discs, gap, carried=None):
    """Discs (by key) the arm body or the carried disc overlaps."""
    caps, pts, a = body(q, gap)
    out = set()
    for k, c in discs.items():
        if any(seg_dist(c, p0, p1) < R + r for p0, p1, r in caps):
            out.add(k)
        if carried is not None and np.linalg.norm(c - carried) < 2 * R:
            out.add(k)
    return out


def carried_xy(q):
    pts, a = fk(q)
    return pts[3] + GC * np.array([math.cos(a), math.sin(a)])


# ---- SVG primitives -------------------------------------------------------------------------------------------------------------------
def circle(p, r, **st):
    x, y = P(p)
    return f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r * S)}"{attrs(st)}/>'


def attrs(st):
    return "".join(f' {k.replace("_", "-")}="{v}"' for k, v in st.items())


def path(pts, **st):
    d = " ".join(("M" if i == 0 else "L") + f"{f(P(p)[0])},{f(P(p)[1])}" for i, p in enumerate(pts))
    return f'<path d="{d}"{attrs(st)}/>'


def rect(c, h, ln, wd, **st):
    x, y = P(c)
    return (f'<rect x="{f(-ln * S / 2)}" y="{f(-wd * S / 2)}" width="{f(ln * S)}" height="{f(wd * S)}" '
            f'transform="translate({f(x)} {f(y)}) rotate({f(-math.degrees(h))})"{attrs(st)}/>')


def arrowhead(tip, d, size, **st):
    d = d / np.linalg.norm(d)
    n = np.array([-d[1], d[0]])
    a, b = tip - size * d + 0.42 * size * n, tip - size * d - 0.42 * size * n
    back = tip - 0.78 * size * d
    return path([tip, a, back, b, tip], **st)


def group(gid, body_, **st):
    return f'<g id="{gid}"{attrs(st)}>{body_}</g>'


# ---- layers -----------------------------------------------------------------------------------------------------------------------------
def lattice():
    lines = [path([np.array([i * H, 0]), np.array([i * H, 8 * H])]) for i in range(9)]
    lines += [path([np.array([0, i * H]), np.array([8 * H, i * H])]) for i in range(9)]
    inner = group("lattice-lines", "".join(lines), stroke=SLATE, stroke_width="0.9", stroke_opacity="0.13", fill="none")
    dots = "".join(circle(xy((r, c)), 0.0016, fill=SLATE, fill_opacity="0.16") for r in range(8) for c in range(8))
    return group("lattice", inner + group("lattice-centres", dots))


def disc(cell, gid, kind):
    p = xy(cell)
    st = {"context": dict(fill=SLATE, fill_opacity="0.16", stroke=SLATE, stroke_opacity="0.42", stroke_width="1.1"),
          "highlight": dict(fill=CLAY, fill_opacity="0.20", stroke=CLAY, stroke_width="1.8"),
          "parked": dict(fill=CLAY, fill_opacity="0.20", stroke=CLAY, stroke_width="1.8"),
          "vacated": dict(fill="none", stroke=CLAY, stroke_opacity="0.55", stroke_width="1.1", stroke_dasharray="3 3.5")}[kind]
    return circle(p, R, id=gid, **st)


def target(p=None, ghost=False):
    p = xy(TARGET) if p is None else p
    if ghost:
        return circle(p, R, id="target-ghost", fill=SLATE, fill_opacity="0.18", stroke=SLATE, stroke_opacity="0.5", stroke_width="1.1")
    return group("target", circle(p, R, fill=SLATE) + circle(p, 0.0075, fill=PAPER))


def goal():
    p = xy(GOAL)
    return group("goal", circle(p, R + 0.006, fill="none", stroke=SLATE, stroke_width="1.3", stroke_dasharray="4.5 3.5")
                 + circle(p, 0.0032, fill=SLATE))


def robot(q, gid, gap=None, opacity=1.0, links=True):
    gap = GR["open_gap_m"] if gap is None else gap
    pts, a = fk(q)
    seg = "".join(path([pts[i], pts[i + 1]], stroke=SLATE, stroke_width=f(LW[i] * S), stroke_linecap="round") for i in range(3) if links or i == 2)
    grip = "".join(rect(c, h, ln, wd, fill=SLATE) for c, h, ln, wd in gripper_rects(pts[3], a, gap))
    joints = "".join(circle(pts[i], ARM["joint_housing_radius_m"] * (0.62 if i == 3 else 1), fill=PAPER, stroke=SLATE, stroke_width="1.6")
                     for i in range(1 if links else 2, 3))
    base = ""
    if links:
        b = BASE
        base = (rect(b, 0, 0.052, 0.052, fill=PAPER, stroke=SLATE, stroke_width="1.4") +
                circle(b, ARM["base_radius_m"], fill=SLATE) + circle(b, 0.0055, fill=PAPER))
    return group(gid, base + seg + grip + joints, opacity=f"{opacity:g}")


def robot_outline(q, gid, opacity, gap):
    """Fine-line pose ghost: link centrelines, joint rings and gripper outline (for stroboscopic execution traces)."""
    pts, a = fk(q)
    st = dict(stroke=SLATE, stroke_width="1.2", stroke_linecap="round", stroke_linejoin="round", fill="none")
    out = path(pts, **st)
    out += "".join(rect(c, h, ln, wd, fill=PAPER, stroke=SLATE, stroke_width="1") for c, h, ln, wd in gripper_rects(pts[3], a, gap))
    out += "".join(circle(pts[i], 0.0055, fill=PAPER, stroke=SLATE, stroke_width="1.1") for i in (1, 2))
    return group(gid, out, opacity=f"{opacity:g}")


def ghost_tool(q, gid, opacity=0.85, u_mark=True):
    """Distal link (dashed) + an open-gripper U only: a restrained 'attempted mode' mark."""
    pts, a = fk(q)
    u, n = np.array([math.cos(a), math.sin(a)]), np.array([-math.sin(a), math.cos(a)])
    off, fl = GR["open_gap_m"] / 2 + GR["finger_thickness_m"] / 2, GR["finger_length_m"]
    tcp = pts[3]
    u_shape = [tcp + fl * u + off * n, tcp + off * n, tcp - off * n, tcp + fl * u - off * n]
    out = path([pts[2], tcp - GR["palm_length_m"] * u], stroke=CLAY, stroke_width="1.2", stroke_dasharray="4 3.5", stroke_linecap="round")
    out += path([tcp - GR["palm_length_m"] * u, tcp], stroke=CLAY, stroke_width="1.6", stroke_linecap="round")
    if u_mark:
        out += path(u_shape, stroke=CLAY, stroke_width="1.6", stroke_linecap="round", stroke_linejoin="round", fill="none")
    return group(gid, out, opacity=f"{opacity:g}")


def distal_hits(q, discs, gap):
    """Discs overlapped by the distal link + gripper alone (what the ghost mark draws)."""
    caps = body(q, gap)[0][2:]
    return {k for k, c in discs.items() if any(seg_dist(c, p0, p1) < R + r for p0, p1, r in caps)}


def contact_arc(centre, towards, gid):
    d = towards - centre
    th = math.atan2(d[1], d[0])
    r = R + 0.0065
    a0, a1 = th - 0.62, th + 0.62
    p0, p1 = centre + r * np.array([math.cos(a0), math.sin(a0)]), centre + r * np.array([math.cos(a1), math.sin(a1)])
    (x0, y0), (x1, y1) = P(p0), P(p1)
    return f'<path id="{gid}" d="M{f(x0)},{f(y0)} A{f(r * S)},{f(r * S)} 0 0 0 {f(x1)},{f(y1)}" fill="none" stroke="{CLAY}" stroke-width="2.6" stroke-linecap="round"/>'


def arrow(p0, p1, gid, color=CLAY, width=2.2, gap0=R + 0.008, gap1=R + 0.006, head=0.017, **st):
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    a, tip = p0 + gap0 * d, p1 - gap1 * d
    shaft = path([a, tip - 0.7 * head * d], stroke=color, stroke_width=f"{width:g}", stroke_linecap="round", fill="none", **st)
    return group(gid, shaft + arrowhead(tip, d, head, fill=color, stroke="none"))


def bezier_pts(p0, p1, bulge, n=40):
    m = (p0 + p1) / 2
    d = p1 - p0
    c = m + bulge * np.array([-d[1], d[0]])
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * c + t ** 2 * p1


def trim(pts, g0, g1):
    """Drop the polyline ends inside discs of radius g0 / g1 around its endpoints."""
    a, b = pts[0], pts[-1]
    keep = [p for p in pts if np.linalg.norm(p - a) >= g0 and np.linalg.norm(p - b) >= g1]
    return np.array(keep)


def transit_cost(pts, obst, arrows, drawn=()):
    """Visual clearance score for a transit curve: disc overlaps >> arrow / arm / earlier-transit crossings >> length."""
    near_disc = sum(1 for p in pts for c in obst if np.linalg.norm(p - c) < R + 0.014)
    near_arrow = sum(1 for p in pts for a, b in arrows if seg_dist(p, a, b) < 0.016)
    near_arrow += sum(1 for p in pts[3:-3] for q in drawn for c in q[3:-3] if np.linalg.norm(p - c) < 0.014)
    out = sum(1 for p in pts if not (X0 + 0.02 < p[0] < X1 - 0.02 and Y0 + 0.02 < p[1] < Y1 - 0.02))
    length = float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))
    return 10 * near_disc + 3 * near_arrow + 50 * out + 4 * length


def chevron(pts, gid):
    i = len(pts) // 2
    d = pts[i + 1] - pts[i - 1]
    d /= np.linalg.norm(d)
    n = np.array([-d[1], d[0]])
    s = 0.0075
    return path([pts[i] - s * d + s * n, pts[i], pts[i] - s * d - s * n], id=gid, stroke=SLATE, stroke_opacity="0.6", stroke_width="1.3",
                fill="none", stroke_linecap="round", stroke_linejoin="round")


# ---- scene logic + checks -----------------------------------------------------------------------------------------------------------------
def scene_discs(moved):
    d = {f"c{i}": xy(c) for i, c in enumerate(CONTEXT)}
    d.update({k: xy(PARK[k] if k in moved else BLOCK[k]) for k in ORDER})
    return d


def best_ik(obj, a, discs, gap, carried=False, elbows=(-1, 1)):
    """Elbow branch with the fewest overlaps (ties -> elbow-up)."""
    best = None
    for e in elbows:
        q = ik(obj, a, e)
        if q is None:
            continue
        h = hits(q, discs, gap, carried_xy(q) if carried else None)
        if best is None or len(h) < len(best[1]):
            best = (q, h, e)
    return best


def any_free_pose(obj, discs, gap, carried):
    for deg in range(-180, 180, 5):
        b = best_ik(obj, math.radians(deg), discs, gap, carried)
        if b and not b[1]:
            return deg, b[2]
    return None


def interp_clear(qa, qb, discs, n=120):
    bad = set()
    for t in np.linspace(0, 1, n):
        q = [(1 - t) * x + t * y for x, y in zip(qa, qb)]
        bad |= hits(q, discs, GR["closed_gap_m"], carried_xy(q))
    return bad


def analyse():
    init, done = scene_discs(set()), scene_discs(set(ORDER))
    tgt, gl = xy(TARGET), xy(GOAL)
    blocked = []
    for a in TARGET_MODES:
        q, h, e = best_ik(tgt, a, init, GR["open_gap_m"], elbows=(ELBOW,))
        blocked.append(dict(where="target", heading_deg=round(math.degrees(a)), q=q, hits_initial=sorted(h),
                            distal_hits_initial=sorted(distal_hits(q, init, GR["open_gap_m"])),
                            hits_repaired=sorted(best_ik(tgt, a, done, GR["open_gap_m"], elbows=(ELBOW,))[1])))
    for a in GOAL_MODES:
        q, h, e = best_ik(gl, a, init, GR["closed_gap_m"], elbows=(ELBOW,))
        blocked.append(dict(where="goal", heading_deg=round(math.degrees(a)), q=q, hits_initial=sorted(h),
                            distal_hits_initial=sorted(distal_hits(q, init, GR["closed_gap_m"])),
                            hits_repaired=sorted(best_ik(gl, a, done, GR["closed_gap_m"], elbows=(ELBOW,))[1])))
    steps, moved = [], set()
    for k in ORDER:
        cur = scene_discs(moved)
        others = {x: v for x, v in cur.items() if x != k}
        others["target"] = tgt
        pick = any_free_pose(cur[k], others, GR["open_gap_m"], False)
        place = any_free_pose(xy(PARK[k]), others, GR["closed_gap_m"], True)
        steps.append(dict(obj=k, src=BLOCK[k], dst=PARK[k], pick_free_heading_deg=pick and pick[0], place_free_heading_deg=place and place[0]))
        moved.add(k)
    qg, hg, _ = best_ik(tgt, 0.0, done, GR["closed_gap_m"], elbows=(ELBOW,))
    qp, hp, _ = best_ik(gl, 0.0, done, GR["closed_gap_m"], carried=True, elbows=(ELBOW,))
    sweep = interp_clear(qg, qp, done)
    home_hits = hits(Q_HOME, {**init, "target": tgt}, GR["open_gap_m"])
    return dict(blocked=blocked, steps=steps, q_grasp=qg, q_place=qp, grasp_hits=sorted(hg), place_hits=sorted(hp),
                transfer_sweep_hits=sorted(sweep), home_hits=sorted(home_hits))


# ---- composition -----------------------------------------------------------------------------------------------------------------
def build_layers(an):
    L = {}
    L["lattice"] = lattice()
    L["goal"] = goal()
    L["target"] = target()
    L["robot-home"] = robot(Q_HOME, "robot-home")
    L["discs-context"] = group("discs-context", "".join(disc(c, f"c{i}", "context") for i, c in enumerate(CONTEXT)))
    L["blockers-initial"] = group("blockers-initial", "".join(disc(BLOCK[k], k, "context") for k in ORDER))
    L["blockers-highlight"] = group("blockers-highlight", "".join(disc(BLOCK[k], f"{k}-hl", "highlight") for k in ORDER))
    arcs, ghosts = "", ""
    for i, b in enumerate(an["blocked"]):
        ghosts += ghost_tool(b["q"], f"mode-{b['where']}-{i}")
    for k in ORDER:                                                          # one arc per blocker, on the side facing what it guards
        guard = xy(GOAL) if k == "b4" else xy(TARGET)
        arcs += contact_arc(xy(BLOCK[k]), guard, f"contact-{k}")
    L["blocked-modes"] = group("blocked-modes", ghosts)
    L["blocked-contacts"] = group("blocked-contacts", arcs)
    L["relocation-arrows"] = group("relocation-arrows", "".join(arrow(xy(BLOCK[k]), xy(PARK[k]), f"move-{k}") for k in ORDER))
    L["destinations"] = group("destinations", "".join(circle(xy(PARK[k]), R, id=f"dest-{k}", fill="none", stroke=CLAY, stroke_width="1.2",
                                                             stroke_dasharray="3 3.5") for k in ORDER))
    tcp_home = fk(Q_HOME)[0][3]
    stops = [tcp_home] + [p for k in ORDER for p in (xy(BLOCK[k]), xy(PARK[k]))] + [tcp_home]
    arrows = [(xy(BLOCK[k]), xy(PARK[k])) for k in ORDER]
    home_body = [(p0, p1) for p0, p1, _ in body(Q_HOME, GR["open_gap_m"])[0]]
    chain, drawn = "", []
    for j in range(5):
        a, b = stops[2 * j], stops[2 * j + 1]
        state = {**scene_discs(set(ORDER[:j])), "target": xy(TARGET)}
        obst = [c for c in state.values() if np.linalg.norm(c - a) > 1e-6 and np.linalg.norm(c - b) > 1e-6]
        g0, g1 = (0.012 if j == 0 else R + 0.010), (R + 0.010 if j < 4 else 0.012)
        pts = min((trim(bezier_pts(a, b, bu), g0, g1) for bu in np.linspace(-0.9, 0.9, 73)),
                  key=lambda q: transit_cost(q, obst, arrows + home_body, drawn))
        drawn.append(pts)
        chain += path(pts, stroke=SLATE, stroke_opacity="0.5", stroke_width="1.2", stroke_dasharray="1.4 3.6", stroke_linecap="round", fill="none")
        chain += chevron(pts, f"transit-dir-{j}")
    L["transit-chain"] = group("transit-chain", chain)
    L["blockers-vacated"] = group("blockers-vacated", "".join(disc(BLOCK[k], f"{k}-vacated", "vacated") for k in ORDER))
    L["blockers-parked"] = group("blockers-parked", "".join(disc(PARK[k], f"{k}-parked", "parked") for k in ORDER))
    qg, qp = an["q_grasp"], an["q_place"]
    path_pts = [carried_xy([(1 - t) * x + t * y for x, y in zip(qg, qp)]) for t in np.linspace(0, 1, 80)]
    tp = trim(np.array(path_pts), R + 0.010, R + 0.012)
    d = tp[-1] - tp[-2]
    L["transfer-path"] = group("transfer-path", path(tp[:-3], stroke=SLATE, stroke_width="2.2", stroke_linecap="round", fill="none")
                               + arrowhead(tp[-1], d, 0.017, fill=SLATE))
    L["target-at-goal"] = target(xy(GOAL), ghost=True)
    L["robot-grasp"] = robot(qg, "robot-grasp", gap=GR["closed_gap_m"])
    L["robot-place"] = robot(qp, "robot-place", gap=GR["closed_gap_m"], opacity=0.32)
    L["tool-at-goal"] = robot(qp, "tool-at-goal", gap=GR["closed_gap_m"], opacity=0.32, links=False)
    # diagram A: blocked approaches as soft rays, destinations with a faint fill
    L["blocked-rays"] = group("blocked-rays", "".join(ghost_tool(b["q"], f"ray-{b['where']}-{i}", opacity=0.55, u_mark=False)
                                                      for i, b in enumerate(an["blocked"])))
    L["destinations-filled"] = group("destinations-filled", "".join(
        circle(xy(PARK[k]), R, id=f"slot-{k}", fill=CLAY, fill_opacity="0.07", stroke=CLAY, stroke_width="1.3", stroke_dasharray="3 3.5")
        for k in ORDER))
    # diagram B: executed placement - stroboscopic full-arm ghosts carrying the target, final pose solid
    strobe = ""
    for i, t in enumerate(STROBE):
        q = [(1 - t) * x + t * y for x, y in zip(qg, qp)]
        op = 0.30 + 0.16 * i
        strobe += group(f"strobe-{i}", circle(carried_xy(q), R, fill=PAPER, stroke=SLATE, stroke_width="1.2", opacity=f"{op:g}")
                        + robot_outline(q, f"strobe-arm-{i}", op, GR["closed_gap_m"]))
    L["execution-strobe"] = group("execution-strobe", strobe)
    L["target-origin"] = circle(xy(TARGET), R, id="target-origin", fill="none", stroke=SLATE, stroke_opacity="0.55", stroke_width="1.2",
                                stroke_dasharray="3 3.5")
    L["blockers-parked-muted"] = group("blockers-parked-muted", "".join(
        circle(xy(PARK[k]), R, id=f"{k}-parked-muted", fill=CLAY, fill_opacity="0.14", stroke=CLAY, stroke_opacity="0.7", stroke_width="1.1")
        for k in ORDER))
    L["robot-executing"] = robot(qp, "robot-executing", gap=GR["closed_gap_m"])
    tp2 = trim(np.array(path_pts), R + 0.010, R + 0.040)
    L["transfer-path-short"] = group("transfer-path-short", path(tp2[:-3], stroke=SLATE, stroke_width="2.2", stroke_linecap="round", fill="none")
                                     + arrowhead(tp2[-1], tp2[-1] - tp2[-2], 0.017, fill=SLATE))
    L["target-placed"] = group("target-placed", target(xy(GOAL)))
    return L


STROBE = [0.0, 1 / 3, 2 / 3]                                               # interpolation fractions drawn as ghosts (final pose solid)


PANELS = {
    "01_initial_scene": ["lattice", "goal", "discs-context", "blockers-initial", "target", "robot-home"],
    "02_blocked_access": ["lattice", "goal", "discs-context", "blockers-initial", "target", "robot-home", "blocked-modes", "blocked-contacts"],
    "03_obstacle_highlight": ["lattice", "goal", "discs-context", "blockers-highlight", "target", "robot-home"],
    "04_relocation_arrows": ["lattice", "goal", "discs-context", "blockers-highlight", "destinations", "target", "robot-home",
                             "relocation-arrows"],
    "04b_relocation_with_transit": ["lattice", "goal", "discs-context", "blockers-highlight", "destinations", "target", "robot-home",
                                    "transit-chain", "relocation-arrows"],
    "05_repaired_scene": ["lattice", "goal", "discs-context", "blockers-vacated", "blockers-parked", "target", "robot-home"],
    "06_feasible_transfer": ["lattice", "goal", "discs-context", "blockers-parked", "target-at-goal", "tool-at-goal", "transfer-path",
                             "target", "robot-grasp"],
    "A_blocked_and_displacement_plan": ["lattice", "goal", "discs-context", "destinations-filled", "blocked-rays", "blockers-highlight",
                                        "blocked-contacts", "target", "robot-home", "transit-chain", "relocation-arrows"],
    "B_target_placement_execution": ["lattice", "goal", "discs-context", "blockers-parked-muted", "target-origin", "execution-strobe",
                                     "transfer-path-short", "robot-executing", "target-placed"],
}


def svg(inner, vb=VIEWBOX, w=None, h=None, bg=False):
    W, Hh = (w, h) if w else (VW, VH)
    back = f'<rect width="100%" height="100%" fill="{PAPER}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="{W}" height="{Hh}" fill="none" '
            f'shape-rendering="geometricPrecision">{back}{inner}</svg>\n')


def preview(L):
    """Two half-scale-free copies (same world->px map) side by side: blocked | repaired, joined by a small chevron."""
    gapx = 120
    left = "".join(L[k] for k in PANELS["02_blocked_access"][:-2] if k != "blockers-initial") + L["blockers-highlight"] + L["blocked-modes"] + L["blocked-contacts"]
    right = "".join(L[k] for k in PANELS["06_feasible_transfer"])
    cx, cy = VW + gapx / 2, VH / 2
    chev = f'<path d="M{cx - 14},{cy - 26} L{cx + 14},{cy} L{cx - 14},{cy + 26}" stroke="{SLATE}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
    inner = group("preview-blocked", left) + chev + group("preview-repaired", right, transform=f"translate({VW + gapx} 0)")
    return inner, f"0 0 {2 * VW + gapx} {VH}", 2 * VW + gapx


def main():
    an = analyse()
    L = build_layers(an)
    out = {d: HERE / d for d in ("svg", "svg/layers", "png", "png/layers", "previews")}
    for p in out.values():
        p.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, body_ in L.items():
        files[f"svg/layers/{name}.svg"] = svg(body_)
    for name, keys in PANELS.items():
        files[f"svg/{name}.svg"] = svg("".join(L[k] for k in keys))
    inner, vb, pw = preview(L)
    files["svg/07_preview_blocked_repaired.svg"] = svg(inner, vb=vb, w=pw // 4, h=VH // 4)
    for rel, txt in files.items():
        assert "<text" not in txt and "<title" not in txt and "<desc" not in txt and "font" not in txt, rel
        (HERE / rel).write_text(txt)
        png = HERE / rel.replace("svg/", "png/", 1).replace(".svg", ".png")
        width = 2 * (pw if "07_" in rel else VW) if "07_" not in rel else pw
        subprocess.run(["rsvg-convert", "-w", str(width), "-o", str(png), str(HERE / rel)], check=True)
    # inspection sheets on paper (not assets)
    for name, keys in PANELS.items():
        (HERE / "previews" / f"{name}_on_paper.svg").write_text(svg("".join(L[k] for k in keys), bg=True))
    (HERE / "previews" / "07_on_paper.svg").write_text(svg(inner, vb=vb, w=pw, h=VH, bg=True))
    for p in (HERE / "previews").glob("*.svg"):
        subprocess.run(["rsvg-convert", "-w", "1340", "-o", str(p.with_suffix(".png")), str(p)], check=True)
    manifest(an, L)


def manifest(an, L):
    cell = lambda c: dict(row=c[0], col=c[1], index=c[0] * 8 + c[1], world_m=[round(v, 4) for v in xy(c)],
                          svg_px=[round(v, 2) for v in P(xy(c))])
    pose = lambda q: dict(q_rad=[round(v, 5) for v in q], joints_svg_px=[[round(v, 2) for v in P(p)] for p in fk(q)[0]])
    m = {
        "status": "CONCEPTUAL ILLUSTRATION - not a physically verified K4 witness from the dataset",
        "viewBox": VIEWBOX, "width_px": VW, "height_px": VH,
        "world_to_svg": {"px_per_m": S, "x_px": f"(x_m - ({X0})) * {S:g}", "y_px": f"({Y1} - y_m) * {S:g}",
                         "world_window_m": {"x": [X0, X1], "y": [Y0, Y1]}, "note": "world y up; svg y down"},
        "palette": {"paper": PAPER, "slate": SLATE, "clay": CLAY},
        "geometry_source": "config.toml [suite] [arm2d] [gripper2d]",
        "lattice": {"rows": 8, "cols": 8, "pitch_m": H, "origin_world_m": [0, 0],
                    "extent_svg_px": [list(map(lambda v: round(v, 2), P(np.array([0, 8 * H])))), list(map(lambda v: round(v, 2), P(np.array([8 * H, 0]))))]},
        "disc_radius_m": R, "disc_radius_px": R * S,
        "robot": {"base_world_m": BASE.tolist(), "base_svg_px": [round(v, 2) for v in P(BASE)], "link_lengths_m": LL,
                  "home_figure_reference": pose(Q_HOME), "home_config_toml": pose(Q_CFG_HOME),
                  "home_note": "figure reference = config q_home with joint 1 rotated +90 deg so the folded arm faces right (illustrative choice)",
                  "execution_strobe_fractions": STROBE, "grasp_at_target": pose(an["q_grasp"]), "place_at_goal": pose(an["q_place"])},
        "target": cell(TARGET), "goal": cell(GOAL),
        "context_discs": {f"c{i}": cell(c) for i, c in enumerate(CONTEXT)},
        "relocations_in_order": [{"id": k, "role": r, "source": cell(BLOCK[k]), "destination": cell(PARK[k])}
                                 for k, r in zip(ORDER, ["NW of target", "SW of target", "W of target", "W of goal (placement side)"])],
        "declared_modes": [{k: v for k, v in b.items() if k != "q"} | {"pose": pose(b["q"])} for b in an["blocked"]],
        "schematic_checks": {
            "method": "capsule/rectangle-vs-disc overlap at drawn poses; joint-linear interpolation for the transfer; not planner certified",
            "home_overlaps": an["home_hits"], "grasp_overlaps": an["grasp_hits"], "place_overlaps": an["place_hits"],
            "transfer_sweep_overlaps": an["transfer_sweep_hits"], "relocation_steps": an["steps"]},
        "transit_chain": "home -> pick b1 -> place b1 -> pick b2 -> ... -> place b4 -> home (robot never homes between relocations)",
        "layers": {k: f"svg/layers/{k}.svg" for k in L},
        "panels": {k: {"svg": f"svg/{k}.svg", "png": f"png/{k}.png", "layers": v} for k, v in PANELS.items()}
                  | {"07_preview_blocked_repaired": {"svg": "svg/07_preview_blocked_repaired.svg", "png": "png/07_preview_blocked_repaired.png",
                                                    "viewBox": f"0 0 {2 * VW + 120} {VH}", "right_half_translate_px": [VW + 120, 0]}},
    }
    (HERE / "manifest.json").write_text(json.dumps(m, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)) + "\n")
    print(json.dumps(m["schematic_checks"], indent=1, default=str))
    print(json.dumps(m["declared_modes"], default=str)[:1500])


if __name__ == "__main__":
    main()
