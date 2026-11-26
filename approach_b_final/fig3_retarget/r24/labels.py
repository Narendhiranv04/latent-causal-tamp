#!/usr/bin/env python3
"""R2.4 exact-compatible LOCAL chunk labels from archived physical traces (evaluator side) + frozen readouts on the same chunks.

A chunked teacher run (relocations from the carried arm state, planned + executed connector to q_ref at every declared boundary) starts every
chunk from q_ref in the cell-level scene reached by the previous chunks, i.e. exactly the canonical hypothetical prefix scene used by the
planner.  Per run (order, bounds, X):
  chunk fully executed (its relocations and its closing connector)                      -> label 1  ("chunk_pos")
  chunk containing the failing relocation                                                -> label 0  ("chunk_neg")
  closing connector of a chunk fails (boundary:j)                                        -> label 0, connector_fail ("chunk_conn_neg")
  continuous run longer than 3 failing at relocation i <= 2: prefixes of length i+1..3 -> label 0  ("continuous_prefix_neg"; the failing
                                                                                            relocation does not depend on later moves)
  chunks after a failure: unobserved.  UNKNOWN teacher outcomes (2D UNKNOWN_*): no negative is emitted.
Sources (non-TEST only): K45 primary / oracle evaluations, R1 / R2.1 / R2.2 / R2.3 Fig.3 jobs, and (later) the R2.4 jobs.
Endpoint Y labels (identical endpoints): Y_global (original-root edit node) vs Y_rebased (fresh-root no-op on the hypothetical endpoint).
    python labels.py build DOM OUT.jsonl [EXTRA_JOBS.json EXTRA_RESULTS.jsonl ...]"""
from __future__ import annotations

import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent), str(HERE.parent / "r2")]
import order as OD  # noqa: E402
import views as V  # noqa: E402

NW = Path("/home/projects/long-horizon/naren_workspace")


def _fail(X):
    ph = str(X.get("phase") or X.get("failed_phase") or "")
    kind, _, j = ph.partition(":")
    return kind, int(j) if j.isdigit() else None


def chunks_of(order, bounds, X, unknown=False):
    b = [0] + list(bounds)
    ch = [(b[i], b[i + 1]) for i in range(len(b) - 1)]
    kind, j = _fail(X) if X.get("x") == 0 else (None, None)
    out = []
    rec = lambda s, e, lab, k, cf=False: {"prefix": order[:s], "chunk": order[s:e], "prefix_len": s, "label": lab, "kind": k, "connector_fail": cf}  # noqa: E731
    if X.get("x") == 1:
        return [rec(s, e, 1, "chunk_pos") for s, e in ch if e - s <= 3]
    if kind not in ("relocation", "boundary"):
        return []
    for s, e in ch:
        if kind == "relocation" and j >= e or kind == "boundary" and j > e:
            if e - s <= 3:
                out.append(rec(s, e, 1, "chunk_pos"))
            continue
        if unknown:
            break
        if kind == "boundary" and j == e and e - s <= 3:
            out.append(rec(s, e, 0, "chunk_conn_neg", True))
        elif kind == "relocation" and s <= j < e:
            if e - s <= 3:
                out.append(rec(s, e, 0, "chunk_neg"))
            elif j - s <= 2:
                out += [rec(s, s + k, 0, "continuous_prefix_neg") for k in range(j - s + 1, 4)]
        break
    return out


def _unknown(X):
    st = str(X.get("teacher_status") or X.get("status") or "")
    return st.startswith("UNKNOWN") or X.get("negative_kind") == "UNKNOWN" or X.get("resolution") == "UNRESOLVED"


def sources(dom):
    """[(jobs list, results path, source tag)] of archived non-TEST physical runs."""
    F = NW / "fig3"
    S = [(F / "r2/r23" / f"jobs_S_{dom}.json", F / "r2" / f"phys_S_{dom}.jsonl", "R2.3"),
         (F / "r2/jobs" / f"all_{dom}.json", F / "r2" / f"phys_{dom}.jsonl", "R2.1-2.2"),
         (F / "runs" / f"jobs{dom}.json", F / "runs" / f"p{dom}.jsonl", "R1")]
    if dom == "3d":
        S += [(NW / "k45/eval/primary_jobs.json", NW / "k45/eval/eval_primary.jsonl", "K45-primary"),
              (NW / "k45/eval/oracle_jobs.json", NW / "k45/eval/oracle_eval_alias", "K45-oracle")]
    return S


def _load(jf, rf):
    J = json.loads(Path(jf).read_text())
    J = J if isinstance(J, list) else [x for v in J.values() for x in v]
    if str(rf).endswith("oracle_eval_alias"):
        rf = NW / "k45/eval/eval_oracle.jsonl"
    R = {}
    if Path(rf).exists():
        for l in open(rf):
            e = json.loads(l)
            R[e["key"]] = e
    return J, R


_REC = {}


def _rec(path):
    if path not in _REC:
        _REC[path] = json.loads(Path(path).read_text())
    return _REC[path]


def rid_of(dom, j):
    if j.get("root_id"):
        return j["root_id"]
    r = _rec(j["path"])
    return r["ids"]["root_id"]


def to_idx(dom, row, names):
    ids = row["inputs"]["ids"]
    return [[ids.index(o), int(d) if dom == "2d" else int(d[0]) * 6 + int(d[1])] for o, d in names]


def collect(dom, rows, extra=()):
    """-> chunk label rows and endpoint Y rows (names resolved to indices on PUBLIC rows; roots without a public row are skipped)."""
    CH, YE, skipped = [], {}, 0
    for jf, rf, tag in list(sources(dom)) + list(extra):
        if not Path(jf).exists():
            continue
        J, R = _load(jf, rf)
        for j in J:
            r = R.get(j["key"])
            if not r or r.get("censored") or r.get("error") or j.get("kind", "X_CHUNKED") != "X_CHUNKED":
                continue
            rid = rid_of(dom, j)
            row = rows.get(rid)
            if row is None:
                skipped += 1; continue
            names = j.get("order") or j.get("seq")
            try:
                seq = to_idx(dom, row, names)
                base = []
                if j.get("cells0"):                                          # hypothetical start: moved bodies become a prefix
                    ids = row["inputs"]["ids"]
                    for o, rc in j["cells0"].items():
                        c = int(rc[0]) * 6 + int(rc[1])
                        if c != int(row["inputs"]["cells0"][ids.index(o)]):
                            base.append([ids.index(o), c])
            except ValueError:
                skipped += 1; continue
            X = r.get("X") or {}
            for c in chunks_of(seq, j["bounds"], X, unknown=_unknown(X)):
                CH.append({"root_id": rid, "src": tag, "key": j["key"], "prefix": OD.canon(base + c["prefix"]), "chunk": c["chunk"],
                           "h": len(base) + c["prefix_len"], "m": len(c["chunk"]), "label": c["label"], "kind": c["kind"], "connector_fail": c["connector_fail"]})
            Y = r.get("Y") or {}
            if Y.get("y") in (0, 1) and (j.get("y") or j.get("y_endpoint") or j.get("y_cells")) and not _unknown(Y) and not j.get("cells0"):
                YE.setdefault((rid, json.dumps(OD.canon(seq))), set()).add(int(Y["y"]))
    dedup = {}
    for c in CH:
        k = (c["root_id"], json.dumps(c["prefix"]), json.dumps(c["chunk"]))
        dedup.setdefault(k, []).append(c)
    out = []
    for k, cs in dedup.items():
        labs = {c["label"] for c in cs}
        c = dict(cs[0]); c["n_obs"] = len(cs); c["srcs"] = sorted({x["src"] for x in cs}); c["conflict"] = len(labs) > 1
        c["label"] = min(labs) if len(labs) == 1 else None
        out.append(c)
    ye = [{"root_id": rid, "endpoint": json.loads(e), "m": len(json.loads(e)), "y": min(v) if len(v) == 1 else None} for (rid, e), v in YE.items()]
    return out, ye, skipped


def readouts(fz, rows, CH, YE):
    by = {}
    for c in CH:
        by.setdefault((c["root_id"], json.dumps(c["prefix"])), []).append(c)
    for (rid, pre), cs in by.items():
        sc = fz.score(V.rebase(rows[rid], json.loads(pre)), [c["chunk"] for c in cs])
        for c, x in zip(cs, sc):
            c.update({k: x[k] for k in ("px", "p11", "py", "px1", "px0")})
    for e in YE:
        e["y_global"] = fz.y_global(rows[e["root_id"]], [e["endpoint"]])[0]
        e["y_rebased"] = fz.p_noop(V.rebase(rows[e["root_id"]], e["endpoint"]))


def main():
    import common as C
    from models import Frozen
    dom, out = sys.argv[2], sys.argv[3]
    extra = [(sys.argv[i], sys.argv[i + 1], "R2.4") for i in range(4, len(sys.argv) - 1, 2)]
    rows = dict(C.snapshot_rows(dom))
    for l in open(NW / "fig3/r2/r23" / f"roster_{dom}.jsonl"):
        r = json.loads(l); rows[r["root_id"]] = r
    CH, YE, sk = collect(dom, rows, extra)
    fz = Frozen(dom); fz.caps = {}
    readouts(fz, rows, CH, YE)
    with open(out, "w") as f:
        for c in CH:
            f.write(json.dumps({"t": "chunk", **c}) + "\n")
        for e in YE:
            f.write(json.dumps({"t": "endpoint", **e}) + "\n")
    print(json.dumps({"dom": dom, "chunks": len(CH), "chunk_pos": sum(c["label"] == 1 for c in CH), "chunk_neg": sum(c["label"] == 0 for c in CH),
                      "h_ge1": sum(c["h"] >= 1 for c in CH), "conflicts": sum(c["conflict"] for c in CH), "endpoints": len(YE), "skipped_no_public_row": sk}))


if __name__ == "__main__" and sys.argv[1] == "build":
    main()
