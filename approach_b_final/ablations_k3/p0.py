#!/usr/bin/env python3
"""P0 source / host preflight for the K<=3 ablation (gvlab2).  Read-only: hashes, counts, contamination, hardware.
    python p0.py OUT_DIR        -> EXPERIMENT_LOCK.json, CPU_GPU_POLICY.json, GATES_P0.json (printed summary)"""
import collections, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABF = Path(os.environ["ABF_ROOT"])                      # k3abl/abf: snapshot/, data/, mirror/, teacher2d_wt/
BUNDLE = Path(os.environ["K3_BUNDLE"])
FIN3D = Path(os.environ["FIN3D_CODE"]).parent
V34_IDS = Path(os.environ["K3_V34_IDS"])
ORIG, EXP = ABF / "snapshot/abf_9de85710c2a7103f", ABF / "snapshot/abf_v32_fb0eef4f5ff433ee"
EXPECT = {"2d": {"split": {"train": 3500, "val": 751, "test": 749}, "K": {"0": 1250, "1": 800, "2": 800, "3": 1150, "NONE": 1000}},
          "3d": {"split": {"train": 1766, "val": 364, "test": 370}, "K": {"0": 511, "1": 357, "2": 612, "3": 612, "NONE": 408}}}
PINS = {"2d/sampler.pt": "a01f25eba31684a78384e8406a2066ed1d3a098899b56f7ec90a4f987af1e918", "3d/sampler.pt": "6a0e26c47781fefe5e9fb84043bf772230b22758cb21f47358836d11e84be472",
        "2d/scorer_s0.pt": "0fa126da80ceecb19ef4d3cf7c21287abc6e5965151b1e4ddc37e0ffe99623d4", "2d/scorer_s1.pt": "ea6dba7a9d054242ff72ada9668f2b16eb0336443ac5f44bc3b141f9b2ffb3af",
        "2d/scorer_s2.pt": "928a6e2b79c84398ca6c03e2233812db724ca2d694df6bd431d7303446c44097", "3d/scorer_s0.pt": "c02afcbc29a9552fd4631c1fd46dfa196a19029151251078bed9f4e3b72dfde1",
        "3d/scorer_s1.pt": "88f49a606bd42f76f6d77215082b8dbeb72dec0a602af1396f09de1aa902551e", "3d/scorer_s2.pt": "948ac82026b6ba273cb7f764f9f470a7e4fa0fd23b349ce9598fee5a01d58f40",
        "2d/scalers.json": "884b35673692a98adf73a6662fdb05e7a489112d6340f32be72e4a1a7e744095", "3d/scalers.json": "36a94926ddd875cc2271827d1c01bbba65ad487a8c7387cf1d3f827bb916dee6"}
TEACHER = {"teacher2d_wt/bxy_teacher.py": "c18ac91c89b9", "mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/code/latent-causal-tamp/p16_motion.py": "43f4c38c6418",
           "fin3d:code/fin3d.py": "29eb0b29ba76", "fin3d:code/bwlphys.py": "259652f14dab",
           "fin3d:src/dataset_bd_classquota_without_home_position_no_overpass/code/shelf66_v3/bd_3dt.py": "62dc853ccb50",
           "fin3d:src/dataset_bd_classquota_without_home_position_no_overpass/code/shelf66_v3/bd_shelf.py": "ef71dcf43c6d"}   # laptop reference (order audit)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rows(snap, dom):
    return [json.loads(l) for l in open(snap / f"data{dom}.jsonl")]


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    G, lock = {}, {"snapshots": {}, "bundle": {}, "teachers": {}, "code": {}}
    v34 = set(json.loads(V34_IDS.read_text()))
    for dom in ("2d", "3d"):
        o, e = rows(ORIG, dom), rows(EXP, dom)
        lk_o, lk_e = json.loads((ORIG / "data_snapshot.lock.json").read_text()), json.loads((EXP / "data_snapshot.lock.json").read_text())
        so, se = sha(ORIG / f"data{dom}.jsonl"), sha(EXP / f"data{dom}.jsonl")
        lock["snapshots"][dom] = {"original": {"path": str(ORIG), "sha256": so, "lock_sha256": lk_o["files"][f"data{dom}.jsonl"]},
                                  "expanded": {"path": str(EXP), "sha256": se, "lock_sha256": lk_e["files"][f"data{dom}.jsonl"]},
                                  "masks_sha256": sha(ORIG / "EVALUATION_MASKS.json")}
        G[f"{dom}_snapshot_hashes_match_locks"] = so == lk_o["files"][f"data{dom}.jsonl"] and se == lk_e["files"][f"data{dom}.jsonl"]
        c_split, c_K = collections.Counter(r["split"] for r in o), collections.Counter(r["K_legacy"] for r in o)
        G[f"{dom}_root_counts"] = dict(c_split) == EXPECT[dom]["split"] and dict(c_K) == EXPECT[dom]["K"]
        om, em = {r["root_id"]: r for r in o}, {r["root_id"]: r for r in e}
        G[f"{dom}_expanded_same_roots_and_splits"] = set(om) == set(em) and all(om[k]["split"] == em[k]["split"] for k in om)
        G[f"{dom}_expanded_val_test_rows_identical"] = all(json.dumps(om[k], sort_keys=True) == json.dumps(em[k], sort_keys=True) for k in om if om[k]["split"] != "train")
        added = {s: sum(len(em[k]["labels"]["X"]) + len(em[k]["labels"]["Y"]) - len(om[k]["labels"]["X"]) - len(om[k]["labels"]["Y"]) for k in om if om[k]["split"] == s) for s in ("train", "val", "test")}
        G[f"{dom}_added_labels_train_only"] = added["val"] == 0 and added["test"] == 0
        lock["snapshots"][dom]["expanded_added_labels_by_split"] = added
        G[f"{dom}_no_v34_root"] = not (set(om) & v34)
        ok = True
        for r in o:
            ys = collections.defaultdict(set)
            for y in r["labels"]["Y"]:
                ys[json.dumps(sorted(map(list, y["edit"])))].add(y["y"])
            ok &= all(len(v) == 1 for v in ys.values())
        G[f"{dom}_y_shared_per_endpoint"] = ok
        lock["snapshots"][dom]["K_status"] = dict(collections.Counter(f"{r['K_legacy']}|{r['meta']['K_status']}" for r in o))
        lock["snapshots"][dom]["mask_counts"] = {m: {s: sum(r["masks"][m] for r in o if r["split"] == s) for s in ("val", "test")}
                                                 for m in ("eval_task", "eval_repair", "eval_noop", "eval_abstain")}
    man = json.loads((BUNDLE / "MANIFEST.json").read_text())
    for n, h in PINS.items():
        lock["bundle"][n] = sha(BUNDLE / n)
    G["bundle_matches_final_protocol_pins"] = all(lock["bundle"][n] == h for n, h in PINS.items())
    G["bundle_matches_manifest"] = all(man["files"][n] == lock["bundle"][n] for n in PINS)
    for dom in ("2d", "3d"):
        G[f"{dom}_q2_scalers_match_bundle"] = sha(ABF / "data" / f"q2_{dom}" / "scalers.json") == PINS[f"{dom}/scalers.json"]
    for k, h in TEACHER.items():
        p = FIN3D / k[6:] if k.startswith("fin3d:") else ABF / k
        lock["teachers"][k] = sha(p)[:12] if p.exists() else None
    G["teacher_sources_match_laptop_reference"] = all(lock["teachers"][k] == h for k, h in TEACHER.items())
    code = HERE.parent
    lock["code"] = {f: sha(code / f) for f in ("placement.py", "xy.py", "search.py", "construct.py", "exhaustive.py", "benchmark.py", "evaluate.py",
                                               "contracts.py", "teacher2d.py", "config/final_protocol.yaml")}
    lock["v34_cohort_ids_metadata_only"] = {"path": str(V34_IDS), "n": len(v34), "sha256": sha(V34_IDS)}
    # hardware
    import torch
    aff = sorted(os.sched_getaffinity(0))
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    du = shutil.disk_usage(str(ABF))
    hw = {"hostname": os.uname().nodename, "logical_cpus": os.cpu_count(), "affinity_cpus_under_taskset": len(aff), "cgroup_cpu_max": (Path("/sys/fs/cgroup/cpu.max").read_text().strip() if Path("/sys/fs/cgroup/cpu.max").exists() else None),
          "gpu": gpu, "torch": torch.__version__, "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
          "ram_gib": round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30, 1), "disk_free_gib": round(du.free / 2 ** 30, 1)}
    G["gpu_available"] = torch.cuda.is_available()
    G["process_tree_pinned_to_43_of_48"] = len(aff) <= 43 and os.cpu_count() >= 48
    pol = {"logical_cpus": os.cpu_count(), "reserved": os.cpu_count() - 43, "ablation_ceiling": 43, "pinned_cpu_set": "0-42", "observed_affinity": len(aff),
           "enforcement": "every ablation process is started under taskset -c 0-42 (inherited by all children); OMP/MKL/OPENBLAS/NUMEXPR=1; torch threads<=1 in workers",
           "phases": {"gpu_fit": "1 controller + 1 CUDA trainer (<=8 threads)", "gpu_scoring": "1-2 GPU scorer processes, 1 thread each",
                      "verification": "<=41 teacher workers + 1-2 controllers"}, "gpu": "single RTX 5090; one heavy CUDA job at a time"}
    git = lambda *a: subprocess.run(["git", "-C", str(code), *a], capture_output=True, text=True).stdout.strip()  # noqa: E731
    lock.update(hardware=hw, git={"branch": git("rev-parse", "--abbrev-ref", "HEAD"), "commit": git("rev-parse", "HEAD"), "status": git("status", "--porcelain")} if git("rev-parse", "HEAD") else
                {"note": "rsync copy of the worktree; commit recorded by the launcher"})
    for n, obj in (("EXPERIMENT_LOCK.json", lock), ("CPU_GPU_POLICY.json", pol), ("GATES_P0.json", G)):
        (out / n).write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"gates": G, "hardware": hw}, indent=1))
    return all(G.values())


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1]) else 1)
