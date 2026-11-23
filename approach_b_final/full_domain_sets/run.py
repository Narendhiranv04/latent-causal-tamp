#!/usr/bin/env python3
"""Frozen-model driver for the full-legal-domain K<=2 set-search study (plan.md v1.1).  PUBLIC inputs only (root_id, domain, inputs).
  p0     bundle hashes, archived top-6 parity of the reconstructed S1 marginal (every VAL root), marginal support / normalization
  pilot  DEV roots: every arm x budget x seed x grid point, model-only (shared per-root memo of ACTUAL scorer outputs; budgets charged per arm)
  eval   frozen protocol (P3_FROZEN_PARAMS) over every EVAL root -> sealed predictions
  live   predeclared timing subset: frozen arms with LIVE scorer calls, no memo, CUDA-synchronized, warm-up + repeats
Memo = every sequence any arm asks for is scored once per root by the frozen scorer and shared; each arm is still charged for every unique
ordered sequence it requests (search.Oracle).  Validity rests on the scorer's batch-composition invariance (P0, max |dp11| <= 1e-6).
    python run.py p0|pilot|eval|live [--n N]     (env FDS_PUB, FDS_BUNDLE, FDS_OUT)"""
from __future__ import annotations

import hashlib, itertools, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import domain as DM  # noqa: E402
import fsearch as FS  # noqa: E402  (named fsearch, NOT search: a local search.py would shadow the frozen approach_b_final/search.py)

PUB = Path(os.environ.get("FDS_PUB", str(Path.home() / "abf_v34/parity/public_val_2d.jsonl")))
BUNDLE = Path(os.environ.get("FDS_BUNDLE", str(Path.home() / "abf_v34/approach_b_bundle")))
OUT = Path(os.environ.get("FDS_OUT", str(Path.home() / "fds_runs")))


def jl(p):
    return [json.loads(l) for l in open(p)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hx(tag, rid):
    return int(hashlib.sha256((tag + rid).encode()).hexdigest(), 16)


def split_of(rid):
    """Same K-blind DEV/EVAL split as the completed fixed-pool study: DEV = lowest 20 % of sha256('MCTS_DEV|'+root_id)."""
    return "DEV" if hx("MCTS_DEV|", rid) < (2 ** 256) // 5 else "EVAL"


def models(device="cuda"):
    import benchmark as BM
    return BM.load_bundle(BUNDLE, "2d", device, 0)                # asserts every 2d bundle file hash against MANIFEST.json


def root_rows(n=None, split=None):
    rows = [r for r in jl(PUB) if r["domain"] == "2d"]
    if split:
        rows = [r for r in rows if split_of(r["root_id"]) == split]
    rows.sort(key=lambda r: hashlib.sha256(("MCTS_ORDER|" + r["root_id"]).encode()).hexdigest())
    return rows[:n] if n else rows


def build(r, samp, man, eps):
    """Original public root -> (Root, Domain, seconds spent on the cVAE marginal)."""
    import search as S
    root = S.Root(r, "2d")
    t0 = time.perf_counter(); raw, D6, _ = DM.cvae_raw(root, samp, man["config"]["proposal_seed"], man["config"]["n_z"])
    return root, DM.Domain(raw, D6, eps), time.perf_counter() - t0


def p0():
    import torch
    import exhaustive as EX
    import search as S
    samp, scor, man = models()
    rep = {"bundle_manifest_sha256": sha(BUNDLE / "MANIFEST.json"), "config": man["config"], "public_sha256": sha(PUB), "torch": torch.__version__,
           "device": torch.cuda.get_device_name(0), "roots": 0, "D6_parity": 0, "mismatch": [], "marginal_sum": [9, -9], "zero_mass_legal_actions": 0,
           "legal_actions": 0, "objects": [], "legal_cells": [], "full_unordered_pairs": []}
    keys = set().union(*(set(r) for r in jl(PUB))) | set().union(*(set(r["inputs"]) for r in jl(PUB)))
    rep["public_keys"] = sorted(keys)
    rep["public_has_private_fields"] = bool(keys & {"K", "K_legacy", "labels", "masks", "witness", "split", "certificate", "B", "verified_K"})
    for r in root_rows():
        root = S.Root(r, "2d"); raw, D6, _ = DM.cvae_raw(root, samp, 0, 64); ref = EX.proposals(root, samp, 0)
        rep["roots"] += 1; rep["D6_parity"] += ref == D6
        if ref != D6:
            rep["mismatch"].append(r["root_id"])
        for v in raw.values():
            s = sum(v.values()); rep["marginal_sum"] = [min(rep["marginal_sum"][0], s), max(rep["marginal_sum"][1], s)]
            rep["zero_mass_legal_actions"] += sum(x <= 0 for x in v.values()); rep["legal_actions"] += len(v)
        d = DM.Domain(raw, D6, 0.25)
        rep["objects"].append(len(d.objs)); rep["legal_cells"].append(len(d.L)); rep["full_unordered_pairs"].append(d.n_pairs())
    q = lambda x: {"min": min(x), "median": sorted(x)[len(x) // 2], "max": max(x)}  # noqa: E731
    for k in ("objects", "legal_cells", "full_unordered_pairs"):
        rep[k] = q(rep[k])
    (OUT / "P0_PARITY.json").write_text(json.dumps(rep, indent=1)); print(json.dumps(rep))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    a = sys.argv[1:]; n = int(a[a.index("--n") + 1]) if "--n" in a else None
    {"p0": p0}[a[0]]()
