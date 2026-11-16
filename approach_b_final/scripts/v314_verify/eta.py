# per-leg ETA (final 3D legs) from the change since the previous call; state in .prog_state3.json.  args: l3 g3 r3
import json, sys, time
from pathlib import Path
S = Path.home() / "abf_v314_verify/.prog_state3.json"
cur = dict(zip(["l3", "g3", "r3"], map(int, sys.argv[1:4]))); now = time.time(); tgt = {"l3": 458, "g3": 133, "r3": 0}
prev = json.loads(S.read_text()) if S.exists() else {"t": time.mktime(time.strptime("2026-11-17 00:41", "%Y-%m-%d %H:%M")), "l3": 0, "g3": 0, "r3": 0}
S.write_text(json.dumps({"t": now, **cur})); dt = max(1e-9, (now - prev["t"]) / 60)
def eta(k):
    left = tgt[k] - cur[k]
    if left <= 0: return 0.0
    r = (cur[k] - prev[k]) / dt
    return left / r if r > 0 else float("inf")
fmt = lambda m: "done" if m == 0 else ("pending" if m == float("inf") else time.strftime("%H:%M", time.localtime(now + 60 * m)))
e = {k: eta(k) for k in tgt}
print(f"ETA 3D {fmt(max(e.values()))} (lap {fmt(e['l3'])}, gv {fmt(e['g3'])}, girish {fmt(e['r3'])})")
