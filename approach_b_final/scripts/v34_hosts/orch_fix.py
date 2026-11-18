#!/usr/bin/env python3
"""Restart this user's V3.4 re-target-run orchestrators (OUT under gen/g[23]_rt*) that lack CODE{2D,3D}/PY{2D,3D}: same argv, cwd and env
+ CODE<D>=<argv SRC>, PY<D>=<argv PY>.  Kills only the orchestrator PID itself (its enrichment children finish or are re-run by the state)."""
import os, re, signal, subprocess, sys
uid = os.getuid()
for p in os.listdir("/proc"):
    if not p.isdigit():
        continue
    try:
        if os.stat(f"/proc/{p}").st_uid != uid:
            continue
        argv = open(f"/proc/{p}/cmdline", "rb").read().split(b"\0")[:-1]
        argv = [a.decode() for a in argv]
    except OSError:
        continue
    i = next((k for k, a in enumerate(argv) if a.endswith("v34_orch.py")), None)
    if i is None or not re.search(r"/gen/g[23]_rt", argv[i + 3]):
        continue
    env = dict(l.split("=", 1) for l in open(f"/proc/{p}/environ", "rb").read().decode().split("\0") if "=" in l)
    dom, py, src = argv[i + 1], argv[i + 9], argv[i + 10]
    D = dom.upper()
    if env.get(f"CODE{D}") == src:
        print("ok", p, argv[i + 3]); continue
    env[f"CODE{D}"], env[f"PY{D}"] = src, py
    cwd = os.readlink(f"/proc/{p}/cwd")
    os.kill(int(p), signal.SIGTERM)
    log = open(os.path.join(argv[i + 3], "orch.log"), "a")
    subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    print("restarted", p, argv[i + 3])
