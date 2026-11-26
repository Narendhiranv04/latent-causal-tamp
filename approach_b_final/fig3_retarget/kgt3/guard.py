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
    return "UNKNOWN" if st.startswith("UNKNOWN") or st.startswith("UNRESOLVED") else "DONE"


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
    return {"status": "COMPLETE" if not why else "INCOMPLETE", "why": why, "n_sealed": len(ks), "n_records": len(R), "kinds": kinds,
            "manifest_sha256": sha(manifest), "results_sha256": sha(out) if Path(out).exists() else None}


def decide(path, payload, inputs, manifests=()):
    for m, o in manifests:
        c = complete(m, o)
        if c["status"] != "COMPLETE":
            raise NotAuthorized(f"{m}: {c['why']}")
    rec = {"decision": payload, "bound": {str(p): sha(p) for p in inputs}, "manifests": [[str(m), str(o)] for m, o in manifests],
           "utc": time.strftime("%FT%TZ", time.gmtime())}
    Path(path).write_text(json.dumps(rec, indent=1))
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
