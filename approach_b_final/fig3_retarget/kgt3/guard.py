"""Fail-closed stage completion and authorization (FIG3_KGT3_PREREG P0).  Worker messages are never evidence of completion.

seal(manifest)            -> writes MANIFEST.SEAL {sha256, n_jobs, keys_sha256}; job keys must be unique.
complete(manifest, out)   -> COMPLETE only if the seal matches, every sealed key has exactly ONE terminal record, no duplicate or unexpected
                             key exists, and no record is an in-flight placeholder.  Terminal kinds: DONE | UNKNOWN | ERROR | CENSORED
                             (missing = NOT_RUN, never a negative).  Anything else -> INCOMPLETE with the reasons (a labelled partial
                             diagnostic at most, never a gate).
decide(name, payload, inputs) -> writes a decision record bound to the sha256 of every input file (manifests, results, checkpoints, code);
                             refuses unless every manifest it cites is COMPLETE.
authorize(decision, field, value, inputs) -> raises unless the decision file exists, its bindings still match the files on disk and
                             decision[field] == value.  Every dispatch of a gated stage calls authorize first."""
from __future__ import annotations

import hashlib, json, time
from pathlib import Path


class NotAuthorized(Exception):
    pass


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _keys(manifest):
    J = json.loads(Path(manifest).read_text())
    J = J if isinstance(J, list) else [x for v in J.values() for x in v]
    return [j["key"] for j in J]


def seal(manifest):
    ks = _keys(manifest)
    if len(ks) != len(set(ks)):
        raise ValueError("duplicate job keys in manifest")
    s = {"sha256": sha(manifest), "n_jobs": len(ks), "keys_sha256": hashlib.sha256("\n".join(sorted(ks)).encode()).hexdigest(),
         "utc": time.strftime("%FT%TZ", time.gmtime())}
    Path(str(manifest) + ".SEAL").write_text(json.dumps(s, indent=1))
    return s


def kind(r):
    if r.get("censored"):
        return "CENSORED"
    if r.get("error"):
        return "ERROR"
    X = r.get("X") or r.get("Y") or {}
    st = str(X.get("teacher_status") or X.get("status") or X.get("resolution") or "")
    if st.startswith("UNKNOWN") or st.startswith("UNRESOLVED"):
        return "UNKNOWN"
    if X.get("x") not in (0, 1) and X.get("y") not in (0, 1):
        return "NO_OUTCOME"                                                  # R4.0: a record without a terminal X / Y value is never terminal
    return "DONE"


OUTCOMES = ("SUCCESS", "CERTIFIED_INFEASIBLE", "BUDGET_NO_PLAN", "OPERATIONAL_FAILURE", "UNRESOLVED", "CENSORED", "ERROR", "NO_OUTCOME")


def outcome(r, part="X"):
    """R4.0 evidence taxonomy of one teacher record (X or Y part):
    SUCCESS               value 1 (callers additionally require independent replay where the contract asks for it)
    CERTIFIED_INFEASIBLE  value 0 with a certificate (negative_kind CERTIFIED / CERTIFIED_INFEASIBLE status)
    BUDGET_NO_PLAN        value 0 because the planner found no plan within the FIXED budget (negative_kind NO_PLAN_FOUND, not UNKNOWN status):
                          budget-relative, NOT a certificate of infeasibility
    OPERATIONAL_FAILURE   value 0 from execution (grasp failed, execution not verified, other failure)
    UNRESOLVED            UNKNOWN_* / UNRESOLVED teacher status (never a negative)."""
    if r.get("censored"):
        return "CENSORED"
    if r.get("error"):
        return "ERROR"
    X = r.get(part) or {}
    v = X.get("x" if part == "X" else "y")
    st = str(X.get("teacher_status") or X.get("status") or X.get("resolution") or "")
    nk = str(X.get("negative_kind") or "")
    if v == 1:
        return "SUCCESS"
    if v != 0:
        return "NO_OUTCOME"
    if st.startswith(("UNKNOWN", "UNRESOLVED")) or nk == "UNKNOWN":
        return "UNRESOLVED"
    if nk == "CERTIFIED" or st.startswith("CERTIFIED"):
        return "CERTIFIED_INFEASIBLE"
    if nk == "NO_PLAN_FOUND":
        return "BUDGET_NO_PLAN"
    return "OPERATIONAL_FAILURE"


def complete(manifest, out):
    why = []
    sp = Path(str(manifest) + ".SEAL")
    if not sp.exists():
        return {"status": "INCOMPLETE", "why": ["no seal"]}
    s = json.loads(sp.read_text())
    if s["sha256"] != sha(manifest):
        why.append("seal sha mismatch")
    ks = _keys(manifest)
    if len(ks) != s["n_jobs"]:
        why.append("seal job count mismatch")
    R = [json.loads(l) for l in open(out)] if Path(out).exists() else []
    seen = {}
    for r in R:
        seen.setdefault(r.get("key"), []).append(r)
    dup = [k for k, v in seen.items() if len(v) > 1]
    extra = [k for k in seen if k not in set(ks)]
    miss = [k for k in ks if k not in seen]
    if dup:
        why.append(f"{len(dup)} duplicate records")
    if extra:
        why.append(f"{len(extra)} unexpected keys")
    if miss:
        why.append(f"{len(miss)} missing (NOT_RUN)")
    kinds = {}
    for k in ks:
        if k in seen:
            kinds[kind(seen[k][0])] = kinds.get(kind(seen[k][0]), 0) + 1
    if kinds.get("NO_OUTCOME"):
        why.append(f"{kinds['NO_OUTCOME']} records without a terminal outcome")
    return {"status": "COMPLETE" if not why else "INCOMPLETE", "why": why, "n_sealed": len(ks), "n_records": len(R), "kinds": kinds,
            "manifest_sha256": sha(manifest), "results_sha256": sha(out) if Path(out).exists() else None}


def decide(path, payload, inputs, manifests=(), stage_dir=None, required=(), once=False):
    """R4.0 hardening: required = payload metrics that must be present and not None; stage_dir = every sealed manifest (*.SEAL) in that
    directory must be cited (no unbound expansion manifest); once = refuse a second opening (repeated gate opening) of the same decision."""
    if once and (Path(path).exists() or Path(str(path) + ".OPENED").exists()):
        raise NotAuthorized(f"{path}: decision already opened once")
    miss = [k for k in required if payload.get(k) is None]
    if miss:
        raise NotAuthorized(f"missing required metrics {miss}")
    if stage_dir is not None:
        cited = {str(Path(m).resolve()) for m, _ in manifests}
        unbound = [str(p)[:-5] for p in Path(stage_dir).glob("*.SEAL") if str(Path(str(p)[:-5]).resolve()) not in cited and Path(str(p)[:-5]).suffix == ".json"
                   and Path(str(p)[:-5]).name.startswith("jobs")]
        if unbound:
            raise NotAuthorized(f"unbound sealed manifests {unbound}")
    for m, o in manifests:
        c = complete(m, o)
        if c["status"] != "COMPLETE":
            raise NotAuthorized(f"{m}: {c['why']}")
    rec = {"decision": payload, "bound": {str(p): sha(p) for p in inputs}, "manifests": [[str(m), str(o)] for m, o in manifests],
           "utc": time.strftime("%FT%TZ", time.gmtime())}
    Path(path).write_text(json.dumps(rec, indent=1))
    if once:
        Path(str(path) + ".OPENED").write_text(rec["utc"])
    return rec


def authorize(path, field, value):
    p = Path(path)
    if not p.exists():
        raise NotAuthorized(f"no decision file {p}")
    rec = json.loads(p.read_text())
    for f, h in rec["bound"].items():
        if not Path(f).exists() or sha(f) != h:
            raise NotAuthorized(f"binding changed: {f}")
    for m, o in rec["manifests"]:
        if complete(m, o)["status"] != "COMPLETE":
            raise NotAuthorized(f"manifest no longer complete: {m}")
    if rec["decision"].get(field) != value:
        raise NotAuthorized(f"{field} = {rec['decision'].get(field)!r} != {value!r}")
    return rec
