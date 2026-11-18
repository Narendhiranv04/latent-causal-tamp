"""Public-input geometry shared by the planners (pure numpy, no planner, no teacher, no private field).

* object discs: centre = public cell centre, radius = attrs radius (2D attrs[0]; 3D footprint attrs[2], floor 2 cm as NOR-Grid graph.py);
* linear paths: the straight segment robot base -> object (MS-MCTS's "linear picking path"; MO-SeGMan collision attribution) and the
  objects / cells whose disc comes within the margin of it;
* the 4-connected lattice of declared cells (E-M4M's MAPF grid)."""
from __future__ import annotations

import collections
import functools

import numpy as np

MARGIN = 0.01


class Geo:
    def __init__(self, row: dict):
        self.row, self.inp, self.dom = row, row["inputs"], row["domain"]
        self.cxy = {int(k): np.asarray(v, float) for k, v in self.inp["cell_xy"].items()}
        self.base = np.asarray(self.inp["base"], float)
        self.rad = [float(a[0]) if self.dom == "2d" else float(max(a[2], 0.02)) for a in self.inp["attrs"]]
        P = np.array(list(self.cxy.values()))
        d = np.linalg.norm(P[:, None] - P[None], axis=-1)
        self.pitch = float(d[d > 1e-9].min())
        self.adj = {c: [k for k in self.cxy if k != c and abs(np.linalg.norm(self.cxy[k] - self.cxy[c]) - self.pitch) < 1e-6]
                    for c in self.cxy}

    def xy(self, c) -> np.ndarray:
        return self.cxy[int(c)]

    def dist(self, a, b) -> float:
        return float(np.linalg.norm(self.xy(a) - self.xy(b)))

    @staticmethod
    def seg_dist(p, a, b) -> float:
        ab = b - a
        t = float(np.clip(np.dot(p - a, ab) / (np.dot(ab, ab) + 1e-12), 0.0, 1.0))
        return float(np.linalg.norm(p - (a + t * ab)))

    def seg_blockers(self, cells, a, b, skip=(), width=None) -> list[int]:
        """Objects whose disc comes within MARGIN of the segment a -> b (a gripper of `width` half-width sweeps it)."""
        w = self.rad[int(self.inp["tid"])] if width is None else width
        return [i for i, c in enumerate(cells) if i not in skip and self.seg_dist(self.xy(c), a, b) < self.rad[i] + w + MARGIN]

    def pick_blockers(self, cells, o) -> list[int]:
        """Objects on the linear picking path of object o (robot base -> o)."""
        return self.seg_blockers(cells, self.base, self.xy(cells[o]), skip={o})

    def seg_cells(self, a, b, r) -> set[int]:
        return {c for c, p in self.cxy.items() if self.seg_dist(p, a, b) < 2 * r + MARGIN}

    @functools.lru_cache(maxsize=4096)
    def _bfs(self, src: int, blocked: frozenset) -> dict:
        legal = {int(c) for c in self.inp["legal_cells"]}
        d, dq = {src: 0}, collections.deque([src])
        while dq:
            c = dq.popleft()
            for n in self.adj[c]:
                if n in legal and n not in blocked and n not in d:
                    d[n] = d[c] + 1
                    dq.append(n)
        return d

    def lattice_dist(self, src, blocked) -> dict:
        """4-connected BFS distances over declared legal cells avoiding `blocked` cells."""
        return self._bfs(int(src), frozenset(int(b) for b in blocked))


def hungarian(C: np.ndarray) -> list[tuple[int, int]]:
    """Exact min-cost assignment of every row of an n x m cost matrix (n <= m) -- scipy-free linear_sum_assignment
    (shortest augmenting path, O(n^2 m))."""
    C = np.asarray(C, float)
    n, m = C.shape
    assert n <= m
    INF = float("inf")
    u, v, p, way = [0.0] * (n + 1), [0.0] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = [INF] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = C[i0 - 1, j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    return sorted((p[j] - 1, j - 1) for j in range(1, m + 1) if p[j])
