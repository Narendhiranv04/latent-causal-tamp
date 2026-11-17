#!/usr/bin/env python3
"""V3.4 enrichment orchestrator (one per host): raw parents of REPARK / HARD slots -> order classification -> frozen re-park / hard-order
(scripts/v34_enrich.py via v34_hosts/enrich.sh) -> SLOT_CHILDREN.json.  A parent whose enrichment yields no accepted child (ineligible start,
no dependent child, gate failure) is REJECTED: its slot goes to a replacement raw run (gen/<base>_r<k>, name <name>r<k>, V34_ONLY_SLOTS) and
the new parent is enriched in the next round.  Loops until every enrichment slot of this host has a child or is exhausted (MAX_ROUNDS).

    v34_orch.py DOM SLOT_PLAN GEN_BASE NAME HOST ENRICH_OUT WORKERS CPUSET GEN_PY GEN_CODE [MAXW_GEN]
Env for enrich.sh: CODE2D/CODE3D, PY2D/PY3D, V34E_FDG.  Never touches the raw generator's own run (only reads its STATUS / ledger)."""
import json, os, subprocess, sys, time
from pathlib import Path

DOM, PLAN, BASE, NAME, HOST, EO, W, CPUS, GPY, GCODE = sys.argv[1:11]
MAXW = sys.argv[11] if len(sys.argv) > 11 else "8"
EO, BASE = Path(EO), Path(BASE)
D = Path(__file__).resolve().parent
MAX_ROUNDS = 4
plan = json.loads(Path(PLAN).read_text())
SL = {s["slot_id"]: s for s in plan["slots"] if s["domain"] == DOM and s["kind"] in ("REPARK", "HARD")}


def log(*a):
    print(time.strftime("%FT%TZ", time.gmtime()), *a, flush=True)


def stores():
    """[(round, store dir)] original run first, then replacement rounds."""
    out = [(0, BASE)]
    k = 1
    while (Path(f"{BASE}_r{k}")).exists():
        out.append((k, Path(f"{BASE}_r{k}")))
        k += 1
    return out


def filled(store):
    try:
        return json.loads((store / "STATUS.json").read_text()).get("filled_map", {})
    except (OSError, ValueError):
        return {}


def stage(store, rnd, name, jobs, extra):
    if not jobs:
        return []
    out = EO / f"r{rnd}" / name
    out.mkdir(parents=True, exist_ok=True)
    jf = out / "jobs_v34.json"
    jf.write_text(json.dumps(jobs))
    cmd = ["bash", str(D / "v34_hosts/enrich.sh"), DOM, CPUS, name.split("_")[0], "--store", str(store), "--jobs", str(jf), "--out", str(out),
           "--workers", W] + extra
    log("run", name, "round", rnd, len(jobs), "jobs")
    subprocess.run(cmd, stdout=open(out / "orch_stage.log", "a"), stderr=subprocess.STDOUT)
    f = out / ("order_summary.jsonl" if name == "order" else "accepted.jsonl")
    return [json.loads(l) for l in open(f)] if f.exists() else []


def main():
    EO.mkdir(parents=True, exist_ok=True)
    stf = EO / "SLOT_CHILDREN.json"
    st = json.loads(stf.read_text()) if stf.exists() else {}
    while True:
        rej_all = {}
        for rnd, store in stores():
            fm = {k: v for k, v in filled(store).items() if k in SL}
            todo = {k: v for k, v in fm.items() if st.get(k, {}).get("child") is None and v not in st.get(k, {}).get("rejected", [])}
            if not todo:
                continue
            order = stage(store, rnd, "order", [[p, "order", k] for k, p in todo.items()], ["--impl", "both"] if DOM == "3d" else [])
            ok = {r["root_id"] for r in order if r.get("n_orders")}
            rp = [[p, ("K2_REPARK" if SL[k]["raw_class"] == "2" else "K3_REPARK"), k] for k, p in todo.items() if SL[k]["kind"] == "REPARK" and p in ok]
            acc = stage(store, rnd, "repark", rp, ["--host", f"{HOST}R{rnd}"])
            hv = {"v3": [], "v4": []}
            for k, p in todo.items():
                if SL[k]["kind"] == "HARD" and p in ok:
                    hv["v4" if SL[k]["ref_source"].endswith("V4") else "v3"].append([p, "K3_HARD", k])
            known = ["--known", str(EO / f"r{rnd}" / "repark")]
            if DOM == "2d":
                acc += stage(store, rnd, "hard", hv["v3"] + hv["v4"], ["--order-out", str(EO / f"r{rnd}" / "order")] + known)
            else:
                acc += stage(store, rnd, "hard_v3", hv["v3"], ["--order-out", str(EO / f"r{rnd}" / "order"), "--variant", "v3", "--host", f"{HOST}R{rnd}"] + known)
                acc += stage(store, rnd, "hard_v4", hv["v4"], ["--order-out", str(EO / f"r{rnd}" / "order"), "--variant", "v4", "--host", f"{HOST}R{rnd}4"])
            by = {}
            for a in acc:
                if a.get("slot_id") in todo and a.get("gate_consistent", True) is not False:
                    by.setdefault(a["slot_id"], a)
            for k, p in todo.items():
                e = st.setdefault(k, {"child": None, "rejected": [], "parents": []})
                e["parents"].append({"round": rnd, "parent": p})
                if k in by:
                    e.update(child=by[k]["root_id"], child_path=by[k].get("path"), strength=by[k].get("strength"), parent=p, round=rnd)
                else:
                    e["rejected"].append(p)
                    rej_all.setdefault(rnd, []).append(k)
            stf.write_text(json.dumps(st, indent=1))
        n_done = sum(1 for k in SL if st.get(k, {}).get("child"))
        open_ = [k for k in SL if not st.get(k, {}).get("child")]
        log("children", n_done, "open", len(open_), "rejected_now", sum(len(v) for v in rej_all.values()))
        need = [k for k in open_ if len(st.get(k, {}).get("rejected", [])) > len(st.get(k, {}).get("repl", []))
                and len(st[k]["rejected"]) < MAX_ROUNDS]
        if need:                                                     # replacement raw run for slots whose last parent was rejected
            k_new = len(stores())
            rb = Path(f"{BASE}_r{k_new}")
            rb.mkdir(parents=True, exist_ok=True)
            (rb / "ONLY_SLOTS").write_text("\n".join(sorted(need)))
            for f in ("MAX_TEMP_C", "MIN_FREE_MB"):
                if (BASE / f).exists():
                    (rb / f).write_text((BASE / f).read_text())
            env = {**os.environ, "V34_ONLY_SLOTS": str(rb / "ONLY_SLOTS")}
            subprocess.Popen(["setsid", "nohup", "bash", str(D / "v34_hosts/gen.sh"), DOM, PLAN, str(rb), f"{NAME}r{k_new}", MAXW, CPUS, GPY, GCODE,
                              "RAW,REPARK,HARD"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            for k in need:
                st[k].setdefault("repl", []).append(k_new)
            stf.write_text(json.dumps(st, indent=1))
            log("replacement run", rb, len(need), "slots")
        base_done = (BASE / "DONE").exists() and all((s / "DONE").exists() for _, s in stores())
        if base_done and not need and all(st.get(k, {}).get("child") or len(st.get(k, {}).get("rejected", [])) >= MAX_ROUNDS
                                          or not any(k in filled(s) for _, s in stores()) for k in SL):
            log("ORCH_DONE")
            (EO / "DONE").write_text(time.strftime("%FT%TZ", time.gmtime()))
            return
        time.sleep(300)


if __name__ == "__main__":
    main()
