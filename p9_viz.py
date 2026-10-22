"""P9 figures (no robot motion: P9 executes nothing). Every file gets a SHA-256 sidecar and an entry in visualizations/p9/index.json.

  factor_instances        L0: a tiny root as a real factor graph per coupling mode (circles = binary outcome variables,
                          squares = factor instances, dashed = observed context; one shared circle for one physical query)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from matplotlib.patches import FancyBboxPatch

from viz import plt

OUT = Path("visualizations/p9")
FAM = {"F2": "#7a5195", "F3": "#2f6f9f", "F4": "#c26a1b", "F5": "#3b8a52", "F1": "#8f99a3"}


def _save(fig, name, what):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    h = "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT / (name + ".sha256")).write_text(h + "\n")
    idx = OUT / "index.json"
    files = [f for f in (json.loads(idx.read_text())["files"] if idx.exists() else []) if f["file"] != str(p)]
    idx.write_text(json.dumps({"files": files + [{"file": str(p), "sha256": h, "what": what}]}, indent=1) + "\n")
    return h


def factor_instances():
    V = {"z0": (1.0, 5.6), "zS[A]": (3.4, 5.6), "zS[B]": (5.8, 5.6), "zS[A+B]": (8.2, 5.6),
         "zR[r1]": (1.6, 1.7), "x": (5.0, 1.7), "zO[r1,1]": (8.4, 1.7)}
    label = {"x": "zO[r1,0]\n= zR[r2]"}
    # (family, position, touched variables, text, modes it exists in)
    U = ("full", "quadratic", "structured", "none")
    F = [("F3", (1.0, 6.75), ["z0"], "scene\nunary", U), ("F3", (3.4, 6.75), ["zS[A]"], "scene\nunary", U),
         ("F3", (5.8, 6.75), ["zS[B]"], "scene\nunary", U), ("F3", (8.2, 6.75), ["zS[A+B]"], "scene\nunary", U),
         ("F3", (2.2, 4.55), ["z0", "zS[A]"], "z0-zS\npair", U[:3]), ("F3", (3.6, 4.15), ["z0", "zS[B]"], "z0-zS\npair", U[:3]),
         ("F3", (5.0, 3.8), ["z0", "zS[A+B]"], "z0-zS\npair", U[:3]),
         ("F5", (4.6, 6.45), ["zS[A]", "zS[B]"], "generic", U[:2]), ("F5", (7.0, 6.45), ["zS[B]", "zS[A+B]"], "generic", U[:2]),
         ("F5", (5.8, 7.45), ["zS[A]", "zS[A+B]"], "generic", U[:2]),
         ("F5", (7.0, 3.5), ["zS[A+B]", "zR[r1]"], "scene-\nrepair", U[:2]), ("F5", (6.2, 2.75), ["zS[B]", "x"], "scene-\nrepair", U[:2]),
         ("F2", (1.6, 0.45), ["zR[r1]"], "seq unary\nr1", U), ("F4", (4.3, 0.45), ["x"], "omission\nunary (r1)", U),
         ("F2", (5.7, 0.45), ["x"], "seq unary\nr2", U), ("F4", (8.4, 0.45), ["zO[r1,1]"], "omission\nunary (r1)", U),
         ("F4", (3.3, 2.45), ["zR[r1]", "x"], "zR-zO\npair", U[:3]), ("F4", (5.0, 2.95), ["zR[r1]", "zO[r1,1]"], "zR-zO\npair", U[:3]),
         ("F5", (6.7, 1.05), ["x", "zO[r1,1]"], "generic", U[:2])]
    fig, axs = plt.subplots(2, 2, figsize=(16, 11.5))
    for ax, mode in zip(axs.flat, U):
        ax.set_xlim(-1.3, 11.4)
        ax.set_ylim(-0.3, 8.6)
        ax.axis("off")
        ax.set_title(f"B-{mode}", fontsize=13, loc="left")
        if mode == "full":                               # higher-order residuals: one factor on ALL bits of a block (hyperedge)
            for (x0, y0, w, h), txt in (((0.35, 5.0, 8.55, 1.2), "higher-order scene factor (all scene bits)"),
                                         ((0.95, 1.12, 8.1, 1.16), "higher-order\nrepair factor\n(all r1 bits\n+ scene bits)")):
                ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0.08", fc=FAM["F5"], alpha=0.12, ec=FAM["F5"], ls=":", zorder=0))
                side = "\n" in txt
                ax.text(x0 + w + (0.2 if side else 0), y0 + (h / 2 if side else -0.14), txt, ha="left" if side else "right",
                        va="center" if side else "top", fontsize=6.6, color=FAM["F5"])
        for fam, (x, y), vs, txt, modes in F:
            if mode not in modes:
                continue
            for v in vs:
                ax.plot([x, V[v][0]], [y, V[v][1]], color=FAM[fam], lw=1.0, alpha=0.7, zorder=1)
            ax.text(x, y, txt, ha="center", va="center", fontsize=6.6, color="white", zorder=3,
                    bbox={"boxstyle": "square,pad=0.3", "fc": FAM[fam], "ec": "none"})
        for v, (x, y) in V.items():
            ax.add_patch(plt.Circle((x, y), 0.42, fc="#dbeafe", ec="#285a84", lw=2.6 if v == "x" else 1.4, zorder=2))
            ax.text(x, y, label.get(v, v), ha="center", va="center", fontsize=7.4, zorder=4)
        ax.text(-1.2, 7.9, "c0: initial scene, robot q0, goal,\nDINOv2 + geometry (observed)", fontsize=7.5, va="top",
                bbox={"boxstyle": "round", "fc": "white", "ec": "#8f99a3", "ls": "--"})
        ax.text(-1.2, 3.35, "repairs (observed inputs):\nr1 = (A->a, B->b)\nr2 = (B->b)", fontsize=7.5, va="top",
                bbox={"boxstyle": "round", "fc": "white", "ec": "#8f99a3", "ls": "--"})
        ax.text(9.0, 8.5, "F1 static (not a z factor):\nU(A@a) U(B@b) V(A,B) on the\nendpoints of r1 -> E_static(r1);\n"
                "cancels from P(z | r); trained by\nstatic BCE; enters E_rank only", fontsize=6.6, va="top", ha="left",
                bbox={"boxstyle": "round", "fc": "#f1f3f5", "ec": FAM["F1"], "ls": "--"})
    handles = [plt.Line2D([], [], marker="s", ls="", color=c, ms=9, label=lab) for lab, c in
               (("F2 ordered sequence", FAM["F2"]), ("F3 scene intervention", FAM["F3"]), ("F4 repair omission", FAM["F4"]),
                ("F5 generic coupling", FAM["F5"]), ("F1 static (separate)", FAM["F1"]))]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=9, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.text(0.5, 0.035, "z0 = zR[empty] (the empty repair has no separate slot).  Thick circle: ONE physical query - omitting A from r1 IS the repair r2 - "
             "so factors of both repair blocks touch the same variable (equality-aware root model).  Scene-repair pairs: 2 of 12 drawn.",
             ha="center", fontsize=8.5)
    fig.suptitle("ABC7 / ABC9 factor instances on a tiny root (circles: binary outcomes; squares: factor instances)", fontsize=13)
    return _save(fig, "P9_factor_instances.png", "L0: factor instances of a tiny root for B-full / quadratic / structured / none (diagram of the code)")


FAMROWS = [("F1 static unary", ["unary"]), ("F1 static pair", ["pairh"]), ("F2 sequence", ["order_s", "pairo", "mix", "gru", "h0"]),
           ("F3 scene unary", ["scene"]), ("F3 z0-zS pair", ["pair_scene"]), ("F4 zR-zO pair", ["pair_omit"]),
           ("F5 generic pairs", ["cpl"]), ("F5 higher-order", ["ho_u", "ho_s", "ho_q"]), ("travel J head", ["cost"]),
           ("shared DINOv2 projection", ["vproj"])]


def _fam(mods, keys):
    return sum(mods.get(k, 0.0) ** 2 for k in keys) ** 0.5


def l1_math():
    """L1: exact evidence vs brute force, cost of the equality-blind product, legacy copy disagreement vs one shared
    variable, and which factor families each ABC9 term reaches."""
    import numpy as np
    import torch

    import abc7_train as t7
    import abc8
    import joint_likelihood as jl
    rows = json.loads(Path("runs/p9/l1/proof_rows.json").read_text())
    grads = json.loads(Path("runs/p9/l1/term_gradients.json").read_text())
    fig, ax = plt.subplots(2, 2, figsize=(13, 9.5))
    a = ax[0, 0]
    bf = [(x["brute_force_ll"], x["exact_ll"]) for x in rows if "brute_force_ll" in x]
    a.scatter(*zip(*bf), s=12, color="#2f6f9f")
    lim = [min(min(p) for p in bf) - 0.5, 0.2]
    a.plot(lim, lim, color="#8f99a3", lw=1)
    a.set(xlabel="brute-force log P(D_c) (all variables enumerated)", ylabel="exact elimination log P(D_c)",
          title=f"(a) {len(bf)} saved P8c roots: max |diff| {max(abs(x - y) for x, y in bf):.1e}")
    a = ax[0, 1]
    d = [x["exact_ll"] - x["duplicated_product_ll"] for x in rows if x["shared_vars"]]
    a.hist(d, bins=30, color="#c26a1b")
    a.set(xlabel="equality-blind product NLL - exact NLL (nats per root)", ylabel="roots",
          title=f"(b) untied copies: {len(d)} roots, mean +{np.mean(d):.2f} nats")
    a = ax[1, 0]
    roots = t7.prepare(torch.load("runs/p8/c_training/dataset_sealed.pt", weights_only=False))
    m = abc8.build("B-full")
    m.load_state_dict(torch.load("runs/p8/c_training/ckpt_B-full#s0.pt", weights_only=True))
    k = 0
    with torch.no_grad():
        for r in roots:
            if len(r["cands"]) < 2:
                continue
            S, blocks, lab, outs = jl.tables(m, r)
            pe = jl.marginals(S, blocks)
            cp = {}
            for c, o in zip(r["cands"], outs):
                for s, q, p in zip(o["slots"], c["z_q"], o["marg"].tolist()):
                    if s[:2] in ("zR", "zO"):
                        cp.setdefault(q, []).append(p)
            for q, ps in cp.items():
                if len(ps) > 1:
                    a.plot([k, k], [min(ps), max(ps)], color="#c26a1b", lw=2.2)
                    a.scatter([k] * len(ps), ps, s=10, color="#c26a1b")
                    a.scatter([k], [pe[q]], s=26, marker="D", color="#2f6f9f", zorder=3)
                    k += 1
    a.set(xlabel="physical sequence query with >= 2 copies (disclosed P8c test roots)", ylabel="P(success)", ylim=(-0.03, 1.03),
          title="(c) legacy B-full copies (orange) vs one tied variable (blue)")
    a = ax[1, 1]
    cols = [(arm, t) for arm in ("B-full", "B-structured", "C-full", "A", "SF") for t in ("nll", "static", "travel")]
    M = np.array([[_fam(grads[arm]["init_seed0"].get(t, {}), keys) for arm, t in cols] for _, keys in FAMROWS])
    im = a.imshow(np.log10(M + 1e-6), cmap="Blues", vmin=-6, vmax=1.5, aspect="auto")
    a.set_xticks(range(len(cols)), [f"{arm}\n{t}" for arm, t in cols], fontsize=6.3, rotation=90)
    a.set_yticks(range(len(FAMROWS)), [n for n, _ in FAMROWS], fontsize=7.5)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if M[i, j] == 0 and not (FAMROWS[i][0].startswith(("F3", "F4", "F5")) and cols[j][0] in ("A", "SF")):
                a.text(j, i, "0", ha="center", va="center", fontsize=6, color="#593b13")
    fig.colorbar(im, ax=a, label="log10 gradient norm (seed-0 init, 12 training roots)")
    a.set_title("(d) which factor families each ABC9 term reaches ('0' = no path)")
    fig.tight_layout()
    return _save(fig, "P9_L1_exact_likelihood.png", "L1: exact evidence vs brute force, cost of untied copies, legacy copy disagreement, per-term factor reach")


ORDER = ["B-full", "B-quadratic", "B-structured", "B-none", "C-full", "A", "SF"]
OBJ = {"P8 multi-loss": "#8f99a3", "ABC9 joint": "#2f6f9f"}


def _rows():
    s = json.loads(Path("runs/p9/l2/summary.json").read_text())
    return s, [v for v in s["rows"].values() if v["objective"] in OBJ]


def l2_nll():
    """L2: exact root NLL (validation, disclosed test), calibrated repair NLL and scene NLL, P8 multi-loss vs ABC9 joint, per seed."""
    import numpy as np
    s, rows = _rows()
    panels = [("val_root_nll", "validation: mean exact root NLL"), ("test_root_nll", "disclosed P8c test: mean exact root NLL"),
              ("root.test.nll", "disclosed test: calibrated repair NLL (root model)"), ("root.test.scene_nll", "disclosed test: scene-bit NLL (z0, zS)")]
    fig, axs = plt.subplots(2, 2, figsize=(13, 8.5))
    for ax, (k, title) in zip(axs.flat, panels):
        for i, arm in enumerate(ORDER):
            for j, (obj, col) in enumerate(OBJ.items()):
                v = [r[k] for r in rows if r["arm"] == arm and r["objective"] == obj and r.get(k) is not None]
                if not v:
                    continue
                x = i + (j - 0.5) * 0.32
                ax.bar(x, np.mean(v), 0.3, color=col, alpha=0.75)
                ax.scatter([x] * len(v), v, s=12, color="black", zorder=3)
        ax.set_xticks(range(len(ORDER)), ORDER, fontsize=8)
        ax.set_title(title, fontsize=10)
    axs[0, 0].legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.75, label=o) for o, c in OBJ.items()], fontsize=8)
    fig.suptitle("P9-L2: same init, same root batches, 200 updates; dots = seeds 0-2 (lower is better; test is a disclosed legacy diagnostic)", fontsize=10)
    fig.tight_layout()
    return _save(fig, "P9_L2_nll_vs_legacy.png", "L2: exact root NLL and calibrated NLLs, P8 multi-loss vs ABC9 joint, per arm and seed")


def l2_gradients():
    """L2: per-factor-family gradient norms over the 200 ABC9 updates (seed 0) and median pre-clip norms vs P8."""
    import numpy as np
    runs = {a: json.loads(Path(f"runs/p9/l2/runs/{a}#s0.json").read_text()) for a in ("B-full", "B-structured", "C-full", "SF")}
    fams = {"F2 sequence": ["order_s", "pairo", "mix", "gru", "h0"], "F3 scene unary": ["scene"], "F3 z0-zS pair": ["pair_scene"],
            "F4 zR-zO pair": ["pair_omit"], "F5 generic pairs": ["cpl"], "F5 higher-order": ["ho_u", "ho_s", "ho_q"],
            "F1 static": ["unary", "pairh"], "travel J": ["cost"], "SF head": ["head"], "DINOv2 projection": ["vproj"]}
    cols = dict(zip(fams, ["#7a5195", "#2f6f9f", "#5fa8d3", "#c26a1b", "#3b8a52", "#7fbf7b", "#8f99a3", "#593b13", "#d45087", "#bbbbbb"]))
    fig, axs = plt.subplots(1, 5, figsize=(19, 4.2), gridspec_kw={"width_ratios": [1, 1, 1, 1, 1.15]})
    for ax, (arm, r) in zip(axs, runs.items()):
        h = [x for x in r["history"] if "grad_by_module" in x]
        for f, mods in fams.items():
            if not any(m in h[0]["grad_by_module"] for m in mods):
                continue
            v = np.array([sum(x["grad_by_module"].get(m, 0) ** 2 for m in mods) ** 0.5 for x in h])
            ax.plot(np.convolve(v, np.ones(10) / 10, mode="valid"), color=cols[f], lw=1.3, label=f)
        ax.set_yscale("log")
        ax.set_title(f"ABC9 {arm} seed 0 (clip {r['clip']:.0f}, clipped {r['clip_fraction']:.0%})", fontsize=9)
        ax.set_xlabel("update (10-update mean)")
    axs[0].set_ylabel("gradient norm by factor family")
    axs[0].legend(fontsize=6.5, loc="lower left")
    s, rows = _rows()
    ax = axs[4]
    for i, arm in enumerate(ORDER):
        for j, (obj, col) in enumerate(OBJ.items()):
            v = [r["grad"]["grad_pre_median"] if obj == "ABC9 joint" else r["grad_pre_median"] for r in rows if r["arm"] == arm and r["objective"] == obj]
            if v:
                ax.bar(i + (j - 0.5) * 0.35, np.mean(v), 0.33, color=col, alpha=0.8, label=obj if i == 0 else None)
    ax.set_xticks(range(len(ORDER)), ORDER, rotation=45, fontsize=8)
    ax.set_yscale("log")
    ax.set_title("median pre-clip total gradient norm", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    return _save(fig, "P9_L2_gradient_health.png", "L2: per-factor gradient norms over ABC9 training (seed 0) and median pre-clip norms vs P8")


def l2_predictions():
    """L2: reliability of root-model repair probabilities (disclosed test, seed 0), selection funnel, and root-cluster contrasts."""
    import numpy as np
    import torch

    import abc8
    import p9_run as pr
    s, rows = _rows()
    fig = plt.figure(figsize=(16, 9.5))
    gs = fig.add_gridspec(2, 3)
    _, _, test = pr._data()
    ax = fig.add_subplot(gs[0, 0])
    ax.plot([0, 1], [0, 1], color="#cccccc", lw=1)
    for arm, ls in (("B-full", "-"), ("B-structured", "--"), ("SF", ":")):
        for obj, path, tau_key in (("ABC9 joint", f"runs/p9/l2/ckpt/ckpt_{arm}#s0.pt", "ABC9"), ("P8 multi-loss", f"runs/p8/c_training/ckpt_{arm}#s0.pt", "P8")):
            m = abc8.build(arm)
            m.load_state_dict(torch.load(path, weights_only=True))
            tau = s["rows"][f"{tau_key}|{arm}#s0"]["root.tau"]
            ps_, ys = [], []
            for r in test:
                for c in pr.root_eval(m, r)["root"]["cands"]:
                    if c["y"] is not None:
                        ps_.append(1 / (1 + np.exp(-c["u"] / tau)))
                        ys.append(c["y"])
            ps_, ys = np.array(ps_), np.array(ys)
            b = np.minimum((ps_ * 5).astype(int), 4)
            pts = [(ps_[b == i].mean(), ys[b == i].mean()) for i in range(5) if (b == i).sum()]
            ax.plot(*zip(*pts), ls=ls, marker="o", ms=4, color=OBJ[obj], label=f"{arm} {obj}")
    ax.set(xlabel="calibrated p (root model)", ylabel="observed success rate", title="(a) reliability, disclosed test, seed 0")
    ax.legend(fontsize=6.5)
    ax = fig.add_subplot(gs[0, 1:])
    cats = [("funnel_success", "success", "#3b8a52"), ("funnel_abstain", "abstain", "#bbbbbb"),
            ("funnel_false_feasible_empty", "false-feasible empty", "#c0392b")]
    labels, x = [], 0
    for arm in ORDER:
        for obj in OBJ:
            v = [r for r in rows if r["arm"] == arm and r["objective"] == obj]
            if not v:
                continue
            bottom = 0
            for k, lab, col in cats:
                m_ = np.mean([r[f"root.test.{k}"] for r in v])
                ax.bar(x, m_, 0.7, bottom=bottom, color=col, label=lab if x == 0 else None)
                bottom += m_
            ax.bar(x, 12 - bottom, 0.7, bottom=bottom, color="#f1c40f", alpha=0.5, label="other failure" if x == 0 else None)
            labels.append(f"{arm}\n{'ABC9' if obj.startswith('ABC9') else 'P8'}")
            x += 1
    ax.set_xticks(range(len(labels)), labels, fontsize=7, rotation=40)
    ax.set(ylabel="test roots (of 12), mean over seeds", title="(b) restricted-catalogue selection on disclosed test (validation-chosen tau, threshold; saved records)")
    ax.legend(fontsize=7, ncol=4)
    ax = fig.add_subplot(gs[1, :])
    con = s["root_nll_contrasts_negative_favours_first"]
    names = [k for k in con if k.startswith("validation|")]
    for i, k in enumerate(names):
        for j, split in enumerate(("validation", "test_disclosed")):
            c = con.get(k.replace("validation|", f"{split}|"))
            if c:
                y = i + (j - 0.5) * 0.3
                ax.plot(c["ci95"], [y, y], color=["#2f6f9f", "#c26a1b"][j], lw=2)
                ax.scatter([c["mean"]], [y], color=["#2f6f9f", "#c26a1b"][j], s=18, label=split if i == 0 else None)
    ax.axvline(0, color="#888888", lw=1)
    ax.set_yticks(range(len(names)), [k.split("|", 1)[1] for k in names], fontsize=7.5)
    ax.set(xlabel="per-root difference in exact root NLL (seed-averaged; root-cluster bootstrap 95 % CI); negative favours the first",
           title="(c) factor and objective contrasts (12 validation / 24 disclosed-test roots; not a fresh holdout)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, "P9_L2_predictions_selection.png", "L2: reliability, selection funnel and root-cluster NLL contrasts (disclosed legacy diagnostics)")


if __name__ == "__main__":
    import sys
    print(globals()[sys.argv[1]]())
