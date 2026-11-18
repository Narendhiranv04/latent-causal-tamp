"""MO-SeGMan (Tuncer, Toussaint & Oguz, arXiv 2511.01476; reference github.com/CankutBoraTuncer/MO-SeGMan src/SeGManv2.py) on the K<=3
repair benchmark (2D and 3D).  Single goal object T (fixed target task), so the placement sequence is [T] and the planner is SeGMan's
remove_obstacle + Selective Guided Forward Search (SGFS) over critical obstacles.

Kept from the reference: critical objects (1 blocker -> it; 2..4 -> the smallest subset whose removal makes the task feasible; > 4 -> the 4
closest to the robot); Global Occupancy Matrix (obstacle 0, free 80, task-trajectory 200) and reachability wave front (1.1 / 0.99), scene
score = sum(GOM * reach) / (h w 10); object weights = raw-score gain of hiding the object minus 80 per object pixel; node score = scene score
+ 5 / sqrt(visit + 1); select_node with the weight update and the secondary-obstacle rule (no improvement -> the object with most collisions
in failed relocations joins the critical set, score = pixels * 200 * 0.6); relocation points: free floor off the task trajectory with
clearance (EDT) >= 75th percentile, k = min(max(ceil(3 %), amount), n) random samples, <= 20 tried until `amount` succeed, amount =
int(w / sum w * 5 * ceil(sqrt(|critical|))), the 3 best new nodes kept; reachability of an object before relocating it; SGFS goal check on
every newly selected node; stagnation limit 2; a second SGFS with an alternative critical set.
FIXES (legacy mosegman.py): (a) subset feasibility is recomputed in every hypothetical scene from SEVERAL obstacle-ignorant target plans
(grasp homotopies): subset S is feasible iff some plan's blockers in that scene are within S -- the legacy single gamma made the test
vacuous (the full blocker set always) -- (b) the critical set of a node is recomputed after every executed move (refresh), (c) the
alternative SGFS starts from the next minimal critical set (a different homotopy) instead of `objects minus the first set`, which could
never succeed for 2-4 blockers, and all alternatives stay available up to `sgfs_attempts`.
Adapted: RRT / KOMO -> RepairEnv transitions (executed from the carried state) and the X+Y terminal check; the reference re-runs RRT per
subset, we test subsets on the plans' swept cells (no re-plan); images are a 1 cm raster of the public board (camera image in the
reference); the wave front starts at the board point nearest the robot base; is_reachable = the linear picking path from the base is free
of other objects; collisions of failed relocations = objects on the linear paths base->object / object->destination; iteration limit
K_MAX + 1 = 4 (reference |O_g| + 1 = 2 cannot reach K = 3); destinations = legal ORIGINALLY-empty cells (never the goal cell)."""
from __future__ import annotations

import collections
import itertools
import math
from collections import deque

import numpy as np

from .common import Solver
from .contract import K_MAX, legal_dests

FREE, OBST, TRAJ = 80.0, 0.0, 200.0


class Node:
    _ids = itertools.count()

    def __init__(self, state, seq, objs, scores, path, raw_prev, moved_obj=None):
        self.id = next(Node._ids)
        self.state, self.seq, self.path = state, list(seq), path
        self.objs, self.obj_scores = list(objs), dict(scores)
        self.obj_weights = self._norm(self.obj_scores)
        self.scene_score_raw_prev, self.moved_obj = raw_prev, moved_obj
        self.visit, self.scene_score, self.scene_score_raw, self.total_score = 1, 0.0, 0.0, 0.0

    @staticmethod
    def _norm(sc):
        tot = sum(sc.values())
        return {o: (s / tot if tot > 0 else 1.0 / len(sc)) for o, s in sc.items()}


class MOSeGMan(Solver):
    name = "mosegman"
    DEFAULTS = {"px": 0.01, "edt_pct": 75, "max_pts": 20, "sample_count": 3, "c_expl": 5.0, "sgfs_attempts": 2, "stuck_lim": 2,
                "max_crit": 4}

    # ------------------------------------------------------------------ images (public board raster)
    def _raster(self):
        g, px = self.ph.geo, self.P["px"]
        P = np.array(list(g.cxy.values()))
        self.lo = P.min(0) - g.pitch / 2
        hi = P.max(0) + g.pitch / 2
        self.nx, self.ny = (int(round(v)) for v in (hi - self.lo) / px)
        ys, xs = np.mgrid[0:self.ny, 0:self.nx]
        self.pxy = np.stack([self.lo[0] + (xs + 0.5) * px, self.lo[1] + (ys + 0.5) * px], -1)
        self.rh = max(1, int(math.ceil(g.rad[int(self.inp["tid"])] / px)))
        self.cmask = {c: (np.abs(self.pxy[..., 0] - p[0]) <= g.pitch / 2) & (np.abs(self.pxy[..., 1] - p[1]) <= g.pitch / 2)
                      for c, p in g.cxy.items()}
        b = np.clip(g.base, self.lo, hi - 1e-9)
        self.start_px = (int((b[1] - self.lo[1]) / px), int((b[0] - self.lo[0]) / px))

    def disc(self, i, c):
        g = self.ph.geo
        return np.linalg.norm(self.pxy - g.xy(c), axis=-1) <= g.rad[i]

    def gom(self, cells, path, hide=()):
        img = np.full((self.ny, self.nx), FREE)
        for c in path["sweep"]:
            if c in self.cmask:
                img[self.cmask[c]] = TRAJ
        tid = int(self.inp["tid"])
        for i, c in enumerate(cells):
            if i != tid and i not in hide:
                img[self.disc(i, c)] = OBST
        return img

    def reach(self, img):
        h, w, rh = self.ny, self.nx, self.rh
        out, vis = np.full((h, w), 0.99), np.zeros((h, w), bool)
        ok = lambda y, x: rh <= y < h - rh and rh <= x < w - rh  # noqa: E731
        free = lambda y, x: (img[y - rh:y + rh + 1, x - rh:x + rh + 1] > 0).all()  # noqa: E731
        sy, sx = int(np.clip(self.start_px[0], rh, h - rh - 1)), int(np.clip(self.start_px[1], rh, w - rh - 1))
        dq = deque()
        if free(sy, sx):
            out[sy - rh:sy + rh + 1, sx - rh:sx + rh + 1] = 1.1
            vis[sy, sx] = True
            dq.append((sy, sx))
        st = max(1, rh // 2)
        while dq:
            y, x = dq.popleft()
            for dy, dx in ((st, 0), (-st, 0), (0, st), (0, -st), (st, st), (st, -st), (-st, st), (-st, -st)):
                a, b = y + dy, x + dx
                if ok(a, b) and not vis[a, b] and free(a, b):
                    out[a - rh:a + rh + 1, b - rh:b + rh + 1] = 1.1
                    vis[a, b] = True
                    dq.append((a, b))
        return out

    def scene_score(self, cells, path):
        img = self.gom(cells, path)
        return float((img * self.reach(img)).sum() / (img.size * 10.0)), float(img.sum())

    def edt(self, img):
        obs = np.argwhere(img <= OBST)
        if not len(obs):
            return np.full(img.shape, 1e3)
        yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
        pts = np.stack([yy.ravel(), xx.ravel()], 1)
        d = np.full(len(pts), np.inf)
        for k in range(0, len(obs), 256):
            d = np.minimum(d, np.sqrt(((pts[:, None, :] - obs[None, k:k + 256, :]) ** 2).sum(-1)).min(1))
        return d.reshape(img.shape) * self.P["px"]

    # ------------------------------------------------------------------ critical objects (recomputed per hypothetical scene)
    def critical_sets(self, s) -> list[tuple[list[int], dict]]:
        """Alternatives (critical set, the task plan it frees), smallest first.  Subset S is feasible iff some plan's blockers in THIS
        scene lie within S, so the minimal feasible subsets are the distinct per-plan blocker sets."""
        out, seen = [], set()
        g = self.ph.geo
        for p, b in self.path_blockers(s):
            if not b or frozenset(b) in seen:
                continue
            seen.add(frozenset(b))
            cells = self.ph.cells(s)
            if len(b) > self.P["max_crit"]:                               # > 4 blockers: the 4 closest to the robot
                b = sorted(b, key=lambda o: (float(np.linalg.norm(g.xy(cells[o]) - g.base)), o))[:self.P["max_crit"]]
            out.append((sorted(b), p))
        return out

    def weights(self, cells, objs, path):
        init = self.gom(cells, path).sum()
        sc = {o: max(0.0, float(self.gom(cells, path, hide=(o,)).sum() - self.disc(o, cells[o]).sum() * FREE - init)) for o in objs}
        return sc, float(init)

    def node_eval(self, n):
        n.scene_score, n.scene_score_raw = self.scene_score(self.ph.cells(n.state), n.path)
        n.total_score = n.scene_score + self.P["c_expl"] / math.sqrt(n.visit + 1)

    def refresh(self, n):
        """FIX (b): after a move, the node's critical set = its unmoved objects that still block its plan; if that plan is no longer
        usable (or already clear but the task failed), switch to the scene's current smallest critical set."""
        el = set(self.elig(n.state))
        cur = self.ph.blockers(n.path, n.state)
        if not cur <= el or not cur:
            cs = self.critical_sets(n.state)
            if not cs:
                return
            objs, n.path = cs[0]
            self.st["critical_recomputed"] += 1
        else:
            objs = sorted(cur)
        keep = [o for o in n.objs if o in el]
        new = [o for o in objs if o not in keep]
        if new:
            sc, _ = self.weights(self.ph.cells(n.state), new, n.path)
            n.obj_scores.update(sc)
        n.objs = keep + new
        n.obj_scores = {o: n.obj_scores.get(o, 0.0) for o in n.objs}
        n.obj_weights = Node._norm(n.obj_scores) if n.obj_scores else {}

    def select_node(self, N, prev, col):
        if prev is not None:
            prev.visit += 1
            prev.total_score = prev.scene_score + self.P["c_expl"] / math.sqrt(prev.visit + 1)
        best = max(N, key=lambda n: (n.total_score, -n.id))
        if prev is not None and prev.scene_score >= best.scene_score and col:
            red = max(col, key=lambda o: (col[o], -o))
            if red not in best.objs and red in self.elig(best.state):
                col.pop(red)
                best.objs.append(red)
                best.obj_scores[red] = float(self.disc(red, self.ph.cells(best.state)[red]).sum()) * 200 * 0.6
                best.obj_weights = Node._norm(best.obj_scores)
                self.st["secondary_added"] += 1
                return best
        if best.moved_obj is not None:
            delta = best.scene_score_raw - best.scene_score_raw_prev
            best.scene_score_raw_prev = best.scene_score_raw
            if delta > 0:
                z = sum(1 for v in best.obj_scores.values() if v == 0)
                if z:
                    best.obj_scores = {k: (v + delta / z if v == 0 else v) for k, v in best.obj_scores.items()}
            if best.moved_obj in best.obj_scores:
                best.obj_scores[best.moved_obj] = max(best.obj_scores[best.moved_obj] - delta, 0.001)
            best.obj_weights = Node._norm(best.obj_scores)
        return best

    # ------------------------------------------------------------------ relocation
    def reachable(self, n, o) -> bool:
        cells = self.ph.cells(n.state)
        self.st["reach_tests"] += 1
        return o == n.moved_obj or not self.ph.geo.pick_blockers(cells, o)

    def reloc_pts(self, n, o):
        cells = self.ph.cells(n.state)
        cand = [c for c in legal_dests(self.inp, cells) if c not in n.path["sweep"]]
        if not cand:
            return []
        img = self.gom(cells, n.path)
        e = self.edt(img)
        wmask = np.zeros(img.shape, bool)
        for c in cand:
            wmask |= self.cmask[c]
        thr = np.percentile(e[wmask], self.P["edt_pct"])
        g = self.ph.geo
        out = []
        for c in cand:
            iy, ix = (int(np.clip(v, 0, m - 1)) for v, m in zip(((g.xy(c) - self.lo) / self.P["px"])[::-1], (self.ny, self.nx)))
            if e[iy, ix] >= thr - 1e-12:
                out.append(c)
        return out

    def generate_new_nodes(self, n, o, N, col):
        amount = int((n.obj_weights.get(o, 0) / max(1e-12, sum(n.obj_weights.values()))) * 5 * math.ceil(math.sqrt(len(n.objs))))
        if amount <= 0:
            return
        pts = self.reloc_pts(n, o)
        if not pts:
            return
        k = min(max(math.ceil(len(pts) * 0.03), amount), len(pts))
        pts = [pts[i] for i in self.rng.choice(len(pts), size=k, replace=False)]
        new, count = [], 0
        g, cells = self.ph.geo, self.ph.cells(n.state)
        for c in pts[:self.P["max_pts"]]:
            if count >= amount:
                break
            self.st["relocation_attempts"] += 1
            nxt = self.ph.step(n.state, o, c)
            if nxt is None:
                for b in set(g.pick_blockers(cells, o)) | set(g.seg_blockers(cells, g.xy(cells[o]), g.xy(c), skip={o})):
                    if b not in n.objs and b in self.elig(n.state):
                        col[b] += 1
                continue
            count += 1
            u = Node(nxt, n.seq + [(o, c)], n.objs, n.obj_scores, n.path, n.scene_score_raw_prev, o)
            self.node_eval(u)
            new.append(u)
        new.sort(key=lambda u: (u.total_score, -u.id), reverse=True)
        N.extend(new[:self.P["sample_count"]])
        self.st["nodes"] += len(new)

    # ------------------------------------------------------------------ SGFS
    def sgfs(self, root):
        N, prev, idx, stuck, col = [root], None, 0, 0, collections.Counter()
        while idx < K_MAX + 1 and stuck < self.P["stuck_lim"]:
            idx += 1
            node = self.select_node(N, prev, col)
            if prev is not None and node.id != prev.id:
                if self.done(node.state):
                    return node
                self.refresh(node)
            stuck = stuck + 1 if (prev is not None and node.scene_score <= prev.scene_score) else 0
            prev = node
            any_reach = False
            for o in list(node.obj_weights):
                if o == node.moved_obj or o not in self.elig(node.state):
                    continue
                if not self.reachable(node, o):
                    continue
                any_reach = True
                self.generate_new_nodes(node, o, N, col)
            if not any_reach:
                N.remove(node)
                prev = None
                if not N:
                    return None
        return None

    def solve(self):
        s0, dec = self.start()
        if dec:
            return dec
        self._raster()
        alts = self.critical_sets(s0)
        self.st["critical_alternatives"] = len(alts)
        for crit, path in alts[:self.P["sgfs_attempts"]]:                  # FIX (c): alternatives = other minimal critical sets
            sc, init = self.weights(self.ph.cells(s0), crit, path)
            root = Node(s0, [], crit, sc, path, init)
            self.node_eval(root)
            self.st["sgfs_runs"] += 1
            res = self.sgfs(root)
            if res is not None:
                return "REPAIR", res.seq, "task feasible"
        return "ABSTAIN", [], "SGFS found no feasible configuration"
