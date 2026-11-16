# Stop this host's 2D verify once every root it must finish itself (its remaining roots minus the tail handed to girish-laptop) is in its cache.
# usage: stop_when_done.py MUST_ROOTS_JSON CACHE_FILE BASELINE_LINES PID LOG
import json, os, signal, sys, time, subprocess
must = set(json.load(open(sys.argv[1]))); cache, base, pid, log = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
while True:
    try:
        os.kill(pid, 0)
    except OSError:
        open(log, 'a').write(f"{time.strftime('%T')} 2D process already exited\n"); break
    done = set()
    for i, l in enumerate(open(cache)):
        if i >= base:
            try: done.add(json.loads(l)['root'])
            except Exception: pass
    if must <= done:
        kids = subprocess.run(['pgrep', '-P', str(pid)], capture_output=True, text=True).stdout.split()
        os.kill(pid, signal.SIGTERM)
        for k in kids:
            try: os.kill(int(k), signal.SIGTERM)
            except OSError: pass
        open(log, 'a').write(f"{time.strftime('%T')} own roots done ({len(must)}); stopped 2D pid {pid} + {len(kids)} workers (remaining tail is girish-laptop's)\n"); break
    time.sleep(60)
