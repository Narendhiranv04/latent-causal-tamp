#!/usr/bin/env python3
"""For this user's re-target-run orchestrators (OUT under gen/g[23]_rt*): stop the orchestrator PID, drop parent rejections that came from
INFRASTRUCTURE rounds (an enrichment stage log with 'cd: ... No such file or directory' = CODE2D/CODE3D unset), remove those parents
from the stores' REJECT_ROOTS, and restart it with CODE<D>/PY<D> set.  Writes SPURIOUS_REJECTIONS.json next to the state."""
import glob, json, os, re, signal, subprocess, time
from pathlib import Path
uid = os.getuid()
for p in os.listdir("/proc"):
    if not p.isdigit():
        continue
    try:
        if os.stat(f"/proc/{p}").st_uid != uid:
            continue
        argv = [a.decode() for a in open(f"/proc/{p}/cmdline", "rb").read().split(b"\0")[:-1]]
    except OSError:
        continue
    i = next((k for k, a in enumerate(argv) if a.endswith("v34_orch.py")), None)
    if i is None or not re.search(r"/gen/g[23]_rt", argv[i + 3]):
        continue
    env = dict(l.split("=", 1) for l in open(f"/proc/{p}/environ", "rb").read().decode().split("\0") if "=" in l)
    cwd = os.readlink(f"/proc/{p}/cwd")
    dom, base, eo, py, src = argv[i + 1], Path(argv[i + 3]), Path(argv[i + 6]), argv[i + 9], argv[i + 10]
    os.kill(int(p), signal.SIGTERM)
    time.sleep(1)
    bad_rounds = set()
    for f in glob.glob(str(eo / "r*" / "*" / "orch_stage.log")):
        if re.search(r"cd: .*No such file or directory", open(f, errors="ignore").read()):
            bad_rounds.add(int(Path(f).parts[-3][1:]))
    stf = eo / "SLOT_CHILDREN.json"
    st = json.loads(stf.read_text()) if stf.exists() else {}
    drop = []
    for k, e in st.items():
        bad = {q["parent"] for q in e.get("parents", []) if q["round"] in bad_rounds} - ({e.get("parent")} if e.get("child") else set())
        if bad:
            e["rejected"] = [r for r in e["rejected"] if r not in bad]
            e["parents"] = [q for q in e["parents"] if q["parent"] not in bad]
            drop += [(k, b) for b in bad]
    if drop:
        stf.write_text(json.dumps(st, indent=1))
        ids = {b for _, b in drop}
        for store in [base] + sorted(Path(str(base) + "_r" + str(n)) for n in range(1, 99) if Path(str(base) + "_r" + str(n)).exists()):
            rf = store / "REJECT_ROOTS"
            if rf.exists():
                keep = [x for x in rf.read_text().split() if x not in ids]
                rf.write_text("\n".join(keep) + ("\n" if keep else ""))
        (eo / "SPURIOUS_REJECTIONS.json").write_text(json.dumps({"bad_rounds": sorted(bad_rounds), "dropped": drop}, indent=1))
    D = dom.upper()
    env[f"CODE{D}"], env[f"PY{D}"] = src, py
    log = open(base / "orch.log", "a")
    subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    print(base.name, "bad_rounds", len(bad_rounds), "dropped", len(drop), "restarted")
