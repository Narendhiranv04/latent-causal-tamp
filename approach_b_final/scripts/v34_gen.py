#!/usr/bin/env python3
"""V3.4 fresh-cohort RAW generation driver (frozen generators and teachers untouched; only the request schedule differs).

    v34_gen.py DOM SLOTS.json OUT NAME MAXW [KINDS]   run inside the generator's cwd/env (wrapper: v34_hosts/gen.sh)

Requests the slot's 8-factor template (the generator's own `work()`), one attempt = one (name, wave = slot ordinal, slot = attempt) id, so
construction seeds / root ids are new and deterministic.  An accepted root fills the first unfilled slot (this host's list) with the same
template and raw_class == observed class; other accepted roots stay in the ledger unused.  Per slot <= CAP attempts (then CAPPED, recorded).
Env V34_SHARD="a,b/n" restricts to a disjoint slot shard.  Live controls in OUT: STOP (drain), WORKERS (int, <= MAXW), MIN_FREE_MB (default 2500), MAX_TEMP_C (default 95; laptop only).
Each ledger line = the runner's entry + v34 fields; the slot->root assignment is derived from the ledger (resumable, idempotent)."""
import glob, json, multiprocessing as mp, os, sys, time
from pathlib import Path

DOM, SLOTS, OUT, NAME, MAXW = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4], int(sys.argv[5])
KINDS = set(sys.argv[6].split(",")) if len(sys.argv) > 6 else None
CFG = {"2d": "90d3eb68e8a42108", "3d": "8d521b1f6d23db23"}[DOM]
CAP = {"2d": 16, "3d": 8}[DOM]
FACT = ("K", "displacement", "distractor_role", "distractors", "mechanism", "parking", "source", "start_pose")
if DOM == "3d":
    sys.path.insert(0, str(Path.cwd() / "shelf66_v3"))
    import run_shelf66_full as RUN
    WALL = RUN.TEACH_WALL_S + RUN.AUDIT_BUDGET_S
    A = RUN._modules()[1]                                  # bd_shelf first, then the SHELF66V3 bd_3dt (asserted by the runner)
else:
    import run_2d_plus as RUN
    WALL = RUN.WALL_S
    import bd_2d as A
bc = RUN.bc
if os.environ.get("V34_WORK") == "conv":                          # CONV1 slots: V1 raw root -> frozen conversion (v34_conv.work)
    import v34_conv
    WORK = v34_conv.work
elif os.environ.get("V34_WORK") == "none3d":                    # 3D NONE slots: dense + trim (v34_none3d.work)
    import v34_none3d
    WORK = v34_none3d.work
else:
    WORK = RUN.work


def ctl(name, default):
    try:
        return type(default)((OUT / name).read_text().strip())
    except (OSError, ValueError):
        return default


def guard_ok():
    mem = int(next(l.split()[1] for l in open("/proc/meminfo") if l.startswith("MemAvailable"))) // 1024
    temps = []
    for f in glob.glob("/sys/class/hwmon/hwmon*/temp1_input"):
        try:
            temps.append(int(open(f).read()) / 1000)
        except (OSError, ValueError):
            pass
    t = max(temps, default=0)
    return mem >= ctl("MIN_FREE_MB", 2500) and t <= ctl("MAX_TEMP_C", 95.0), mem, t


def key(spec):
    return json.dumps({k: spec[k] for k in FACT}, sort_keys=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    env = A.env()
    assert env["config_hash"] == CFG, ("teacher config drift", env["config_hash"])
    plan = json.loads(Path(SLOTS).read_text())
    slots = [s for s in plan["slots"] if s["domain"] == DOM and (KINDS is None or s["kind"] in KINDS)]
    if os.environ.get("V34_COVER") in ("0", "1"):                # 2D: only slots that do (1) / do not (0) need bd_2d_cover_table.json
        slots = [s for s in slots if s.get("needs_2d_cover_table") == (os.environ["V34_COVER"] == "1")]
    ex = os.environ.get("V34_EXCLUDE_REF")                        # e.g. "2d-conv": slots whose reference root id starts with it are skipped
    only = os.environ.get("V34_ONLY_REF")                         # e.g. "2d-conv": only those slots
    if ex:
        slots = [s for s in slots if not s["ref_root_id"].startswith(ex)]
    if os.environ.get("V34_ONLY_SLOTS"):                         # file with slot ids (replacement runs for rejected enrichment parents)
        keep_ids = set(Path(os.environ["V34_ONLY_SLOTS"]).read_text().split())
        slots = [s for s in slots if s["slot_id"] in keep_ids]
    if only:
        slots = [s for s in slots if s["ref_root_id"].startswith(only)]
    if os.environ.get("V34_SHARD"):                               # 'a,b/n': this host owns slots with sha256(slot_id) % n in {a, b}
        import hashlib
        keep, n = os.environ["V34_SHARD"].split("/")
        keep = {int(x) for x in keep.split(",")}
        slots = [s for s in slots if int(hashlib.sha256(s["slot_id"].encode()).hexdigest(), 16) % int(n) in keep]
    order = {s["slot_id"]: i for i, s in enumerate(plan["slots"])}
    store = bc.Store(OUT)
    running, t_log = {}, 0
    with mp.get_context("spawn").Pool(MAXW, maxtasksperchild=10) as pool:
        while True:
            for r in [r for r in running if r.ready()]:
                sid, att, t0 = running.pop(r)
                try:
                    e = r.get()
                except Exception as ex:  # noqa: BLE001
                    e = {"accepted": False, "reason": f"ERROR:pool:{ex}"}
                e.update(v34_slot=sid, v34_attempt=att, v34_host=os.uname().nodename, v34_cpu_wall_s=round(time.time() - t0, 1))
                store.append(e)
            for r in [r for r, (_, _, t0) in running.items() if time.time() - t0 > WALL + 900]:
                sid, att, t0 = running.pop(r)
                store.append({"accepted": False, "reason": "LOST_JOB", "v34_slot": sid, "v34_attempt": att})
            led = store.ledger()
            tries, filled = {}, {}
            for e in led:
                if "v34_slot" in e:
                    tries[e["v34_slot"]] = max(tries.get(e["v34_slot"], 0), e["v34_attempt"] + 1)
            try:                                                   # parents the enrichment stage could not use -> slot needs a new raw root
                rej = set((OUT / "REJECT_ROOTS").read_text().split())
            except OSError:
                rej = set()
            nrej = {}
            for e in led:
                if e.get("root_id") in rej and "v34_slot" in e:
                    nrej[e["v34_slot"]] = nrej.get(e["v34_slot"], 0) + 1
            used = set(rej)
            for e in (e for e in led if e.get("accepted")):                  # ledger (completion) order
                obs = str(e.get("observed"))
                cand = [s for s in slots if s["slot_id"] not in filled and key(s["spec"]) == key(e["spec"]) and s["raw_class"] == obs]
                cand.sort(key=lambda s: (s["slot_id"] != e["v34_slot"], order[s["slot_id"]]))
                if cand and e["root_id"] not in used:
                    filled[cand[0]["slot_id"]] = e["root_id"]
                    used.add(e["root_id"])
            inflight = {}
            for sid, _, _ in running.values():
                inflight[sid] = inflight.get(sid, 0) + 1
            cap = lambda sid: CAP * (1 + nrej.get(sid, 0))  # noqa: E731
            todo = [s for s in slots if s["slot_id"] not in filled and tries.get(s["slot_id"], 0) + inflight.get(s["slot_id"], 0) < cap(s["slot_id"])]
            ok, mem, temp = guard_ok()
            W = min(MAXW, ctl("WORKERS", MAXW))
            stop = (OUT / "STOP").exists()
            if time.time() - t_log > 300:
                t_log = time.time()
                st = {"utc": time.strftime("%FT%TZ", time.gmtime()), "slots": len(slots), "filled": len(filled), "running": len(running),
                      "attempts": sum(tries.values()), "capped": sum(1 for s in slots if s["slot_id"] not in filled and tries.get(s["slot_id"], 0) >= cap(s["slot_id"])), "rejected": len(rej),
                      "mem_mb": mem, "temp_c": temp, "workers": W, "guard_ok": ok, "stop": stop}
                (OUT / "STATUS.json").write_text(json.dumps({**st, "filled_map": filled}, indent=0))
                print(json.dumps(st), flush=True)
            if (stop or not todo) and not running:
                break
            if not stop and ok:
                for depth in (0, 1):                                   # first one attempt per open slot, then a 2nd parallel attempt
                    for s in sorted(todo, key=lambda s: order[s["slot_id"]]):
                        if len(running) >= W:
                            break
                        if inflight.get(s["slot_id"], 0) != depth or tries.get(s["slot_id"], 0) + depth >= cap(s["slot_id"]):
                            continue
                        att = tries.get(s["slot_id"], 0) + depth
                        spec = dict(s["spec"])
                        job = (NAME, order[s["slot_id"]], att, spec, str(OUT))
                        running[pool.apply_async(WORK, (job,))] = (s["slot_id"], att, time.time())
                        inflight[s["slot_id"]] = depth + 1
                        break                                          # one launch per loop pass: re-check the guard
            time.sleep(2)
    (OUT / "DONE").write_text(time.strftime("%FT%TZ", time.gmtime()))


if __name__ == "__main__":
    main()
