#!/usr/bin/env python3
"""One exhaustive pass per root over the IDENTICAL frozen M4 candidate pool (proposals of the sealed FULL_s0 prediction, pool hash checked),
scored by several frozen scorers at once; for each score variant the exact argmax repair under the frozen key
(round(-log max(p, 1e-12), 12), |r|, displacement, signature) = exhaustive.Selectors with alpha = beta = gamma = 0, plus p_noop.  With
alpha = beta = gamma = 0 every (noop_gate, eta) rule picks NOOP, this argmax repair or ABSTAIN from (p_noop, p_best) alone, so decisions for any
rule are derived offline (rules.py) and only the argmax repairs ever need physical verification.  No teacher, no label enters a decision;
snapshot labels are read only for the known-success rank diagnostic.
    python multipass.py DOM SPLIT [PART i/k]    -> $K3V/runs/out/multipass/{SPLIT}_{DOM}[.part].jsonl (resumable)
Variants: D-family (FULL_s0..2 frozen bundle): p11, p11_w0 (F5 knockout w <- 0), Y_only (sig b), X_marg, X_given_Y1 (sig(a + w));
E_s0..2: p11;  DIRECT_s0..2: p_succ."""
import hashlib, json, sys, time

import numpy as np
import torch

import vk
import xy as XY  # noqa: E402
import exhaustive as EX  # noqa: E402
import search as S  # noqa: E402

NETS = [f"FULL_s{s}" for s in (0, 1, 2)] + [f"E_s{s}" for s in (0, 1, 2)] + [f"DIRECT_s{s}" for s in (0, 1, 2)]
sig = torch.sigmoid


def variants(name, C, parent):
    b, a, w = C["b"], C["a"], C["w"]
    if name.startswith("DIRECT"):
        return {f"{name}:p11": sig(a)}
    if name.startswith("E"):
        return {f"{name}:p11": sig(b[parent]) * sig(a)}
    py, p1, p0 = sig(b[parent]), sig(a + w), sig(a)
    return {f"{name}:p11": py * p1, f"{name}:p11_w0": py * p0, f"{name}:Y_only": py, f"{name}:X_marg": py * p1 + (1 - py) * p0, f"{name}:X_given_Y1": p1}


class Best:
    def __init__(self):
        self.k, self.v = None, None

    def update(self, seqs, p, m, D, extra):
        cost = -np.log(np.maximum(p, 1e-12))
        near = np.nonzero(cost <= cost.min() + 1e-9)[0]
        k0, i0 = min((EX.key(float(cost[i]), m[i], D[i], seqs[i]), int(i)) for i in near)
        if self.k is None or k0 < self.k:
            self.k, self.v = k0, {"seq": [list(map(int, x)) for x in seqs[i0]], "p": float(p[i0]), "m": int(m[i0]), "D": float(D[i0]),
                                  **{k: float(v[i0]) for k, v in extra.items()}}


def run(dom, split, part=None, chunk=8192):
    torch.set_num_threads(1)
    pub = vk.jl(vk.K3A / "runs/public" / f"public_{split}_{dom}.jsonl")
    full = {r["root_id"]: r for r in vk.jl(vk.K3A / "runs/predictions/FULL_s0" / f"{split}_{dom}.jsonl")}
    snap = {r["root_id"]: r for r in vk.rows(dom, split)}
    if part:
        i_, k_ = map(int, part.split("/"))
        pub = [r for r in pub if int(hashlib.sha256(r["root_id"].encode()).hexdigest(), 16) % k_ == i_]
    fo = vk.OUT / "multipass" / (f"{split}_{dom}.jsonl" if not part else f"{split}_{dom}.part{part.replace('/', 'of')}.jsonl")
    fo.parent.mkdir(parents=True, exist_ok=True)
    done = {r["root_id"] for r in vk.jl(fo)}
    nets = {n: XY.load_model(vk.ckpt(n, dom), "cuda") for n in NETS}
    with open(fo, "a") as f, torch.no_grad():
        for r in pub:
            if r["root_id"] in done:
                continue
            t0 = time.time()
            root = S.Root(r, dom)
            Dm = {int(o): [int(d) for d in v] for o, v in full[r["root_id"]]["proposals"].items()}
            assert hashlib.sha256(json.dumps({str(o): v[:4] for o, v in sorted(Dm.items())}, sort_keys=True).encode()).hexdigest()[:20] == full[r["root_id"]]["pool_hash"]
            known = EX.known_success(snap[r["root_id"]]) if r["root_id"] in snap else set()
            inp = root.row["inputs"]
            P = lambda c: tuple(inp["cell_xy"][str(c)])  # noqa: E731
            best, kn, p_noop, wstat, n = {}, {}, {}, [0.0, 0.0, 0], 0
            buf = []

            def flush():
                nonlocal n
                if not buf and p_noop:
                    return
                v, _, xm = XY.make_view(root.id, inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], [],
                                        [[(i, P(d)) for i, d in s] for s in buf], XY._NoGeo)
                b, _ = XY.collate([v], device="cuda", dtype=torch.float32)
                par = torch.as_tensor(v["parent"], dtype=torch.long, device="cuda")
                qi = torch.as_tensor(xm, dtype=torch.long, device="cuda")
                m = np.array([len(s) for s in buf]); D = np.array([root.displacement(list(s)) for s in buf], float)
                for name, net in nets.items():
                    C = net.coeffs(b)
                    p_noop.setdefault(name, float(sig(C["b"][b["y0"]])[0]))
                    if not buf:
                        continue
                    V = variants(name, C, par)
                    if name == "FULL_s0":
                        dp = (sig(C["a"] + C["w"]) - sig(C["a"]))[qi]
                        wstat[0] += float(C["w"][qi].sum()); wstat[1] += float(dp.abs().sum()); wstat[2] += len(buf)
                    for vn, p in V.items():
                        pv = p[qi].double().cpu().numpy()
                        best.setdefault(vn, Best()).update(buf, pv, m, D, {})
                        for i, s in enumerate(buf):
                            if s in known:
                                kn.setdefault(vn, []).append(float(pv[i]))
                        if known:                                       # rank of the best known success: count strictly higher / equal
                            st = kn.setdefault(vn + "#scores", [])
                            st.append(pv.astype(np.float32))
                n += len(buf)
                buf.clear()
            for s, _ in EX.stream(Dm, 4):
                buf.append(s)
                if len(buf) >= chunk:
                    flush()
            flush()
            rec = {"root_id": r["root_id"], "K": snap.get(r["root_id"], {}).get("K_legacy"), "n_cand": n, "pool_hash": full[r["root_id"]]["pool_hash"],
                   "p_noop": p_noop, "variants": {}}
            for vn, bb in best.items():
                d = dict(bb.v)
                if vn in kn and kn[vn]:
                    allp = np.concatenate(kn[vn + "#scores"]); top = max(kn[vn])
                    d["known"] = {"n": len(kn[vn]), "best_p": top, "n_higher": int((allp > top).sum()), "n_equal": int((allp == np.float32(top)).sum()) - 1}
                rec["variants"][vn] = d
            rec["n_known_in_pool"] = len(kn.get("FULL_s0:p11", []))
            rec["w_pool_FULL_s0"] = {"w_mean": wstat[0] / max(1, wstat[2]), "absdp_mean": wstat[1] / max(1, wstat[2])}
            rec["wall_s"] = round(time.time() - t0, 2)
            f.write(json.dumps(rec) + "\n"); f.flush()
    print(json.dumps({"dom": dom, "split": split, "part": part, "n": len(vk.jl(fo))}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    run(a[0], a[1], a[2] if len(a) > 2 else None)
