"""SORC-Grid data layer: read-only snapshot loading, P0 audit, and teacher-aligned supervision (no fabricated negatives).

Sources (local, hash-verified in the audit): base snapshot abf_9de85710c2a7103f (TRAIN/VAL/TEST rows) and its superset abf_v3_e8a496bc66266fca
(identical VAL/TEST rows; TRAIN rows add V2 on-policy and V3 direct-candidate teacher labels).  Supervision per TRAIN root (contracts.py schema):
  X rows  {seq [[obj_index, cell], ...] ordered, x 0/1, kind, x_phase ('relocation:j' | 'connector' | None), x_witnesses}
  Y rows  {edit (sorted endpoint), y 0/1}            -- Y is shared by every order of one endpoint (never duplicated here)
Derived samples (all with provenance):
  SEQ   (prefix, positive next objects)  from successful repairs (X=1 and Y(endpoint)=1), prefixes in their verified order
  PLACE (prefix, object, positive cells) from the same successful repairs
  EXEC  (prefix, move, label)            relocation-step executability: steps before a localised failure = 1, the failed step = 0,
                                         every step of an X=1 sequence = 1; X=0 without a localised phase -> no step label (masked)
  STOP  (endpoint edit, y)               target-from-q_ref feasibility of the hypothetical endpoint scene (Y labels, deduplicated)"""
import collections, hashlib, json, os, platform, subprocess, sys
from pathlib import Path

SNAP = Path(os.environ.get("SORC_SNAP_ROOT", str(Path.home() / "abf_v3_2_audit/root/snapshot")))
BASE, EXT = "abf_9de85710c2a7103f", "abf_v3_e8a496bc66266fca"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rows(dom, snap=EXT, split=None):
    out = []
    for l in open(SNAP / snap / f"data{dom}.jsonl"):
        r = json.loads(l)
        if split is None or r["split"] == split:
            out.append(r)
    return out


def ekey(seq):
    return json.dumps(sorted(map(tuple, map(lambda m: (int(m[0]), int(m[1])), seq))))


def okey(seq):
    return json.dumps([[int(a), int(b)] for a, b in seq])


def movable(inp, dom):
    fixed = [bool(a[3]) for a in inp["attrs"]] if dom == "2d" else [False] * len(inp["ids"])
    return [i for i in range(len(inp["ids"])) if i != inp["tid"] and not fixed[i]]


def supervision(r, dom):
    """-> dict of SEQ / PLACE / EXEC / STOP samples of one root (indices into inputs), plus counters.  Never invents a negative."""
    Y = {ekey(y["edit"]): y["y"] for y in r["labels"]["Y"] if y["y"] in (0, 1)}
    X = {}
    conflicts = 0
    for q in r["labels"]["X"]:
        if q["x"] not in (0, 1):
            continue
        k = okey(q["seq"])
        if k in X and X[k]["x"] != q["x"]:
            conflicts += 1
            continue
        X.setdefault(k, q)
    succ = [json.loads(k) for k, q in X.items() if q["x"] == 1 and Y.get(ekey(q["seq"])) == 1]
    seq, place = collections.defaultdict(set), collections.defaultdict(set)
    for s in succ:
        for j in range(len(s)):
            p = okey(s[:j])
            seq[p].add(s[j][0])
            place[(p, s[j][0])].add(s[j][1])
    ex, exc = {}, 0
    for k, q in X.items():
        s = json.loads(k)
        ph = q.get("x_phase")
        fail = int(ph.split(":")[1]) if isinstance(ph, str) and ph.startswith("relocation:") else None
        for j in range(len(s)):
            if q["x"] == 1 or ph == "connector" or (fail is not None and j < fail):
                lab = 1
            elif fail == j:
                lab = 0
            else:
                continue                                           # unattributed: masked, never a negative
            kk = (okey(s[:j]), int(s[j][0]), int(s[j][1]))
            if kk in ex and ex[kk] != lab:
                exc += 1
                ex[kk] = None                                      # contradictory step evidence -> masked
            elif kk not in ex:
                ex[kk] = lab
    return {"SEQ": [(json.loads(p), sorted(v)) for p, v in seq.items()],
            "PLACE": [(json.loads(p), o, sorted(v)) for (p, o), v in place.items()],
            "EXEC": [(json.loads(p), o, d, lab) for (p, o, d), lab in ex.items() if lab is not None],
            "STOP": [(json.loads(k), y) for k, y in Y.items()],
            "n_success": len(succ), "x_conflicts": conflicts, "exec_conflicts": exc}


# ------------------------------------------------------------------------------------------------ P0 audit
def hardware():
    def sh(c):
        try:
            return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception as e:  # noqa: BLE001
            return f"ERROR {e}"
    hw = {"hostname": platform.node(), "uname": " ".join(platform.uname()), "nproc": os.cpu_count(),
          "meminfo": sh("grep -E 'MemTotal|MemAvailable' /proc/meminfo"), "disk_home": sh("df -h ~ | tail -1"),
          "nvidia_smi": sh("flatpak-spawn --host nvidia-smi --query-gpu=name,memory.used,memory.total,driver_version --format=csv,noheader || nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader")}
    try:
        import torch
        hw.update(torch=torch.__version__, cuda=torch.version.cuda, cuda_available=torch.cuda.is_available(),
                  gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
    except ImportError:
        hw["torch"] = None
    return hw


def audit(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    man = {"snapshots": {}, "domains": {}, "q2": {}, "hardware": hardware(),
           "source_commit": subprocess.run("git rev-parse HEAD", shell=True, capture_output=True, text=True).stdout.strip()}
    for s in (BASE, EXT):
        d = SNAP / s
        man["snapshots"][s] = {"path": str(d.resolve()), **{f.name: {"sha256": sha(f), "bytes": f.stat().st_size} for f in sorted(d.iterdir()) if f.is_file()}}
    for dom in ("2d", "3d"):
        R = rows(dom, EXT)
        B = {r["root_id"]: r for r in rows(dom, BASE)}
        D = {"splits": dict(collections.Counter(r["split"] for r in R)), "K_by_split": {}, "train": {}, "val": {}}
        D["val_test_rows_identical_to_base"] = all(json.dumps(r, sort_keys=True) == json.dumps(B[r["root_id"]], sort_keys=True)
                                                   for r in R if r["split"] != "train")
        for sp in ("train", "val", "test"):
            D["K_by_split"][sp] = dict(collections.Counter(r["K_legacy"] for r in R if r["split"] == sp))
        fam, lay = collections.defaultdict(set), collections.defaultdict(set)
        for r in R:
            fam[r["parent_family_id"]].add(r["split"]); lay[r["layout_root_id"]].add(r["split"])
        D["leakage"] = {"families_in_2plus_splits": sum(len(v) > 1 for v in fam.values()), "layouts_in_2plus_splits": sum(len(v) > 1 for v in lay.values())}
        D["max_objects"] = max(len(r["inputs"]["ids"]) for r in R)
        D["grid"] = R[0]["inputs"]["grid"]
        D["n_legal_cells"] = sorted({len(r["inputs"]["legal_cells"]) for r in R})
        for sp in ("train", "val"):
            c, kinds, phases = collections.Counter(), collections.Counter(), collections.Counter()
            byK = collections.defaultdict(collections.Counter)
            orders = collections.Counter()
            for r in (x for x in R if x["split"] == sp):
                S = supervision(r, dom)
                for k in ("n_success", "x_conflicts", "exec_conflicts"):
                    c[k] += S[k]
                for k in ("SEQ", "PLACE", "EXEC", "STOP"):
                    c[k] += len(S[k])
                c["EXEC_pos"] += sum(e[3] == 1 for e in S["EXEC"]); c["STOP_pos"] += sum(s[1] == 1 for s in S["STOP"])
                byK[r["K_legacy"]]["roots"] += 1; byK[r["K_legacy"]]["roots_with_success"] += S["n_success"] > 0
                for q in r["labels"]["X"]:
                    kinds[q["kind"]] += 1
                    phases[str(q.get("x_phase")) if q["x"] == 0 else "x=1"] += 1
                eps = collections.defaultdict(set)
                for q in r["labels"]["X"]:
                    if q["x"] in (0, 1) and len(q["seq"]) > 1:
                        eps[ekey(q["seq"])].add(q["x"])
                orders["endpoints_multi_order"] += len(eps); orders["order_contrast_endpoints"] += sum(len(v) == 2 for v in eps.values())
            D[sp] = {"samples": dict(c), "X_kinds": dict(kinds), "X0_phase": dict(phases), "by_K": {k: dict(v) for k, v in sorted(byK.items())},
                     "order": dict(orders)}
        man["domains"][dom] = D
    q2_2d = Path.home() / "approachb3d_v3/2d_q2_spillover/src/gh-yadu-iiith/planar_2d/dataset_relocations_v1/q2_spillover/merged/q2_canonical_v4"
    q2_3d = Path.home() / "approachb3d_v3/repo/gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v2/production_v4"
    man["q2"] = {"2d": {"path": str(q2_2d), "status": "PRESENT" if q2_2d.exists() else "NOT_LOCAL (gvlab-only merge; contract forbids fetching)"},
                 "3d": {"path": str(q2_3d), "status": "PRESENT" if q2_3d.exists() else "NOT_LOCAL (gvlab-only production set; a partial off-host parity mirror is not a provenance-verified copy)"},
                 "consequence": "optional auxiliary conditional-placement head not trained; PLACE learns only from target-repair evidence"}
    (out_dir / "sorc_dataset_manifest.json").write_text(json.dumps(man, indent=1))
    return man


if __name__ == "__main__":
    m = audit(sys.argv[1])
    print(json.dumps({d: {"splits": v["splits"], "train": v["train"]["samples"], "val": v["val"]["samples"], "leak": v["leakage"],
                          "identical": v["val_test_rows_identical_to_base"]} for d, v in m["domains"].items()}, indent=1))
