"""P17 custody after the sealed runs (sealed-output manifest -> push -> unseal), the prospective oracle guide, and the final analyses:
the frozen p17_analysis functions applied to the unsealed prospective outputs and to the retrospective P16-root re-analysis. Reads and
hashes outputs only; every decision rule it applies is in the PREREG-hashed code."""
from __future__ import annotations

import collections
from pathlib import Path

import config as cf
from p17_eval import OUT, rd, sha

from p17_data import DATA, _plan, merged

T = DATA / "p17test"
EVAL = OUT / "eval"
ADMIT_ARMS = ("LB", "LB+G", "LB+G|nocpl", "LB-W", "FULLB", "LB-F2", "LC", "A", "SF")


# ------------------------------------------------------------------ custody: manifest -> push -> unseal
def p_manifest() -> dict:
    """runs/p17/data/p17test/SEALED_MANIFEST.json: sha256 of every sealed output; refuses while a sealed worker runs or a roster is incomplete
    (counts root keys only, never outcomes)."""
    import p17_prosp as pp
    run = [f.name for f in (OUT / "running").glob("p17_4_seal_*.json")]
    if run:
        raise SystemExit(f"sealed workers still running: {run}")
    ro = pp.p_rosters()
    n = {kind: len(merged("p17test", f"sealed_{kind}")) for kind in ("labels", "exec_b", "exec_d")}
    want = {"labels": len(ro["b"]), "exec_b": len(ro["b"]), "exec_d": len(ro["d"])}
    if n != want:
        raise SystemExit(f"incomplete sealed outputs: {n} vs {want}")
    files = sorted(str(f) for f in T.glob("sealed_*.json"))
    m = {"files": {f: sha(f) for f in files}, "n": len(files), "roots": n, "prereg": sha(OUT / "PREREG.json")}
    cf.write_json(T / "SEALED_MANIFEST.json", m)
    return m


def p_unseal() -> None:
    import p16_eval as p16e
    m = T / "SEALED_MANIFEST.json"
    if not p16e._on_origin(str(m)):
        raise SystemExit("sealed manifest not on origin/main")
    if any(sha(f) != h for f, h in rd(m)["files"].items()):
        raise SystemExit("sealed file changed after the manifest")
    (T / "UNSEALED").write_text(sha(m) + "\n")


def _unsealed():
    if not (T / "UNSEALED").exists():
        raise SystemExit("sealed")


# ------------------------------------------------------------------ prospective oracle guide (non-deployable reference)
def p_oracles() -> dict:
    """{root: ({pool object: in union}, lattice type)} on the D roster: P17 parking-lattice union from the sealed labels (PREREG); None where
    the lattice gives no defined mask."""
    import p17_mechjobs as mj
    import p17_prosp as pp
    _unsealed()
    labs, out = merged("p17test", "sealed_labels"), {}
    for k in pp.p_rosters()["d"]:
        d, pool = mj._lat(labs[k])
        out[k] = ({o: m for o, m in zip(pool, d["mask"])} if d["mask"] is not None else None, d["type"])
    return out


def run_p_oracle(part) -> None:
    import p17_exec as ex
    import p17_prosp as pp
    orc = {k: v[0] for k, v in p_oracles().items() if v[0] is not None}
    ex.run_roots("p17test", [k for k in pp.p_rosters()["d"] if k in orc], part, "d", guides=["oracle"], oracles=orc, tag="exec_oracle",
                 claims=T / "oracle_claims")


# ------------------------------------------------------------------ analyses
def _unions(orc) -> dict:
    return {k: {o for o, m in x[0].items() if m} for k, x in orc.items() if x[0] is not None}


def _d_sets(rows, orc_rows, unions) -> dict:
    """All roots without the oracle (primary contrast), the oracle-defined subset with it, and NAT / constructed strata. The P17 guide
    record names its order trace 'trace' (same entries, incl. 'first'); the frozen p16 analysis reads it as 'order_trace' (key alias only)."""
    import p17_analysis as pa
    al = lambda x: {**x, "order_trace": x["trace"]}  # noqa: E731
    base = {k: {"family": v["family"], "guides": {g: al(x) for g, x in v["guides"].items() if g != "oracle"}} for k, v in rows.items()}
    wo = {k: {"family": base[k]["family"], "guides": {**base[k]["guides"], "oracle": al(orc_rows[k])}} for k in base if k in orc_rows and k in unions}
    st = {s: {k: v for k, v in base.items() if (v["family"] == "NAT") == (s == "NATURAL")} for s in ("NATURAL", "CONSTRUCTED")}
    return {"all_roots": pa.d_analysis(base, unions), "oracle_subset": pa.d_analysis(wo, unions) if wo else None,
            "strata": {s: pa.d_analysis(r, unions) if r else None for s, r in st.items()}}


def label_summary(labs) -> dict:
    fam = collections.defaultdict(collections.Counter)
    seq = collections.defaultdict(collections.Counter)
    for v in labs.values():
        fam[v["family"]][v["original"]["status"]] += 1
        for x in v["sequences"].values():
            seq[str(x["len"])][{1: "VERIFIED", 0: "CERTIFIED"}.get(x["y"], "UNKNOWN")] += 1
    return {"roots": len(labs), "original_by_family": {f: dict(c) for f, c in fam.items()}, "sequences_by_length": {n: dict(c) for n, c in sorted(seq.items())},
            "cpu_s": sum(v["cpu_s"] for v in labs.values())}


def matched_rows(labs, b, d, rs, kinds=("Dp16", "Dp17")) -> dict:
    """Per D-roster root (B and D both executed): original label status, every B arm's choice / execution status / replay, every D guide's
    found / replay / moves, and each D family's raw original-target feasibility (seed-ensemble mean; the same quantity d_offline scores)."""
    import numpy as np
    import d_blockers as db
    import p17_d as pd
    ms = {kind: pd.models(kind) for kind in kinds}
    by = {r["key"]: r for r in rs}
    out = {}
    for k in d:
        if k not in b or k not in labs or k not in by:
            continue
        r, pool = by[k], labs[k]["catalogue"]["pool"]
        ix = [r["ids"].index(o) for o in pool]
        out[k] = {"family": d[k]["family"], "original": labs[k]["original"]["status"],
                  "b": {a: {"choice": x["choice"], "status": x["status"], "replay": bool(x.get("replay"))} for a, x in b[k]["b"]["arms"].items()},
                  "d": {g: {"found": x["found"], "replay": x["replay"], "moves": x["moves"]} for g, x in d[k]["d"].items()},
                  "d_pfeas": {kind: float(np.mean([db.predict(m, r["R"], ix)["p_feasible"] for m in mm])) for kind, mm in ms.items()}}
    return out


def _w(name, obj) -> None:
    EVAL.mkdir(parents=True, exist_ok=True)
    cf.write_json(EVAL / name, obj)


def analyze_prospective() -> dict:
    import p17_analysis as pa
    import p17_b as pb
    _unsealed()
    labs = merged("p17test", "sealed_labels")
    b = merged("p17test", "sealed_exec_b")
    brows = {k: {"family": v["family"], "b": v["b"]} for k, v in b.items()}
    nat = {s: {k: v for k, v in brows.items() if (v["family"] == "NAT") == (s == "NATURAL")} for s in ("NATURAL", "CONSTRUCTED")}
    B = {"analysis": pa.b_analysis(brows), "strata": {s: pa.b_analysis(r) for s, r in nat.items() if r}, "offline": pa.b_offline(brows, labs),
         "noop_kappa": pa.noop_kappa(brows), "admission": pa.admission_curves(brows, labs, ADMIT_ARMS),
         "cpu_root_mean": sum(v["cpu_root"] for v in b.values()) / len(b)}
    orc = p_oracles()
    d = merged("p17test", "sealed_exec_d")
    orc_rows = {k: v["d"]["oracle"] for k, v in merged("p17test", "exec_oracle").items()}
    D = _d_sets({k: {"family": v["family"], "guides": v["d"]} for k, v in d.items()}, orc_rows, _unions(orc))
    D["oracle_types"] = dict(collections.Counter(x[1] for x in orc.values()))
    rs = pb.prepare(pb.records(_plan("p17test")["roots"], labs, "p17test"))
    D["offline"] = {kind: pa.d_offline(kind, rs, labs) for kind in ("D", "Dp", "Dp16", "Dp17")}
    out = {"cohort": "p17test", "unsealed": (T / "UNSEALED").read_text().strip(), "labels": label_summary(labs), "b": B, "d": D,
           "matched": matched_rows(labs, b, d, rs)}
    _w("P17_PROSPECTIVE.json", out)
    return out


def analyze_retrospective() -> dict:
    """P17_REANALYSIS_OF_P16_ROOTS: every guide incl. the oracle (P16 unsealed parking-lattice union) on all 48 P16 D test roots."""
    import p16_eval as p16e
    import p17_prosp as pp
    r = merged("test", "retro")
    miss = [k for k in pp.retro_keys() if k not in r]
    orc = p16e.test_oracles()
    rows = {k: {"family": v["family"], "guides": v["d"]} for k, v in r.items()}
    orc_rows = {k: v["d"]["oracle"] for k, v in r.items() if "oracle" in v["d"]}
    out = {"label": "P17_REANALYSIS_OF_P16_ROOTS", "roots": len(r), "missing": miss, **_d_sets(rows, orc_rows, _unions(orc)),
           "oracle_types": dict(collections.Counter(x[1] for x in orc.values())), "cpu_root_total": sum(v["cpu_root"] for v in r.values())}
    _w("P17_RETROSPECTIVE.json", out)
    return out
