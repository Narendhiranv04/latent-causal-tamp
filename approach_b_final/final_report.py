#!/usr/bin/env python3
"""Assemble reports/FINAL_REPORT.md from the recorded result files only (no new computation).   python final_report.py"""
from __future__ import annotations

import json, os
from pathlib import Path

ABF = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
R = ABF / "runs"
ROWS = [("uncoupled", "Uncoupled (F5=0, E)", "E"), ("orderinv", "Order-invariant (G)", "G"), ("direct", "Direct success predictor (DIRECT)", "DIRECT"),
        ("analytic", "Analytical sampler (band-stratified)", None), ("flow", "Flow matching", None), ("oneshot", "One-shot selection", None),
        ("notravel", "No travel-cost term (γ=0)", None), ("full", "**Our approach (F2,F3,F5, D)**", "D")]


def J(p):
    return json.loads(Path(p).read_text())


def pct(x):
    return "—" if x is None else f"{100 * x:.1f}"


def f3(x):
    return "—" if x is None else f"{x:.3f}"


def table_ib(p5, p2, title):
    t = J(p5 / "table_test.json")
    r2 = J(p2 / "report_test.json")
    s = t["summary"]
    lines = [f"### {title}", "", f"Frozen stopping rule (validation-tuned): `{json.dumps(t['rule'])}`. Test roots × 3 seeds; paired root-cluster "
             "bootstrap 95 % CI of the difference to the full approach (task success).", "",
             "| Row | NLL ↓ | Order ↑ | Repair % ↑ | Task % ↑ | Calls ↓ | Travel ↓ | Δ Task vs full [95 % CI] |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for key, name, arm in ROWS:
        a = s.get(key)
        if not a:
            continue
        nll = r2["arms"][arm]["nll_z"]["mean"] if arm else None
        order = r2["arms"][arm].get("order_acc", {}).get("mean") if arm else None
        d = t["paired_vs_full"].get(key, {}).get("task") if key != "full" else None
        ci = "—" if not d else f"{100 * d['delta']:+.1f} [{100 * d['ci95'][0]:+.1f}, {100 * d['ci95'][1]:+.1f}]"
        tr = a["travel_success_mean"]
        lines.append(f"| {name} | {f3(nll)} | {f3(order)} | {pct(a['repair_success'])} | {pct(a['task_success'])} | 0 | "
                     f"{'—' if tr is None else f'{tr:.2f}'} | {ci} |")
    f = s["full"]
    lines += ["", f"Full approach, other strata: correct no-op on K0 {pct(f['noop_correct'])} % (n = {f['n_k0']}), correct abstention on NONE "
              f"{pct(f['abstain_correct'])} % (n = {f['n_none']}); Task n = {f['n_task']}, Repair n = {f['n_repair']} (certified roots × seeds); "
              f"successful repairs shorter than the legacy K: {f['shorter_than_K']}.", ""]
    return lines


def main():
    out = ["# Approach B: final implementation and experiment report", "",
           "Everything here was computed on gvlab (GPU 0 only) and gvlab2 (CPU teacher queries, exact parity with gvlab). "
           "No result was tuned on test. V1 = the pre-registered design of plan.md; V2 = the same architectures retrained with on-policy X/Y labels "
           "(user decision after the V1 validation failure analysis). Calls = motion-planner calls inside the learned search (0 by construction; "
           "the independent physical verification is reported separately and is identical for every row).", ""]
    out += ["## Table I(b): 2D component ablations (test)", ""]
    out += table_ib(R / "p5_2d", R / "p2_2d", "V1 (pre-registered)")
    if (R / "v2/p5_2d/table_test.json").exists():
        out += table_ib(R / "v2/p5_2d", R / "v2/p2_2d", "V2 (on-policy labels)")
    out += ["## 3D: our approach (test; external baselines deferred by the user)", "",
            "| Version | Task % | Repair % | No-op % | Abstain % | Travel | Rule |", "|---|---:|---:|---:|---:|---:|---|"]
    for ver, p in (("V1", R / "p5_3d"), ("V2", R / "v2/p5_3d")):
        if (p / "table_test.json").exists():
            t = J(p / "table_test.json"); a = t["summary"]["full"]
            out.append(f"| {ver} | {pct(a['task_success'])} | {pct(a['repair_success'])} | {pct(a['noop_correct'])} | {pct(a['abstain_correct'])} | "
                       f"{f3(a['travel_success_mean'])} | `{json.dumps(t['rule'])}` |")
    out += ["", "## Supporting evidence", "", "### P1 placement samplers (test hit@4 / known-label precision @4; Δ hit@4 vs cVAE)", "",
            "| Sampler | 2D | 3D |", "|---|---|---|"]
    e2, e3 = J(R / "p1_2d/eval_test.json"), J(R / "p1_3d/eval_test.json")
    for k in ("cvae", "fm", "stratified", "uniform"):
        cell = lambda e: f"{e['arms'][k]['mean']['4']['hit']:.3f} / {e['arms'][k]['mean']['4']['known_label_precision']:.3f}" + (  # noqa: E731
            "" if k == "cvae" else f" (Δ {e['paired_hit4_vs_cvae'][k]['delta']:+.3f} [{e['paired_hit4_vs_cvae'][k]['ci95'][0]:+.3f}, {e['paired_hit4_vs_cvae'][k]['ci95'][1]:+.3f}])")
        out.append(f"| {k} | {cell(e2)} | {cell(e3)} |")
    out += ["", "### V1 vs V2 on the search's own validation candidates (physically labelled; never trained on)", "",
            "| Domain / version / arm | Z NLL | AUROC | ECE | mean p11 |", "|---|---:|---:|---:|---:|"]
    c = J(R / "v2/V1_vs_V2_search_candidates_val.json")
    for k, v in c.items():
        if not k.endswith("|n"):
            out.append(f"| {k} | {v['nll']:.3f} | {v['auroc']:.3f} | {v['ece']:.3f} | {v['mean_p']:.3f} |")
    out += ["", "### Coverage diagnostic (train roots; labelled candidates)", ""]
    for d in ("2d", "3d"):
        cv = J(R / f"v2/{d}/COVERAGE_DIAGNOSTIC.json")
        out.append(f"- {d.upper()}: {json.dumps(cv['summary'])}; by K {json.dumps(cv['by_K'])}")
    out += ["", "### Validation end-to-end (300-root tuning subset)", "", "| | Task % | Repair % | No-op % | Abstain % |", "|---|---:|---:|---:|---:|"]
    for d in ("2d", "3d"):
        for ver, p in (("V1", R / f"p5_{d}"), ("V2", R / f"v2/p5_{d}")):
            s = J(p / "tune_val.json")[0]["summary"]
            out.append(f"| {d.upper()} {ver} | {pct(s['task_success'])} | {pct(s['repair_success'])} | {pct(s['noop_correct'])} | {pct(s['abstain_correct'])} |")
    out += ["", "## Caveats", "",
            "- Repair uses a relative certificate (legacy-verified minimal K + finalized X=1/Y=1 order + no shorter repair found by omission); "
            "successful repairs shorter than K are counted separately.",
            "- 3D K1 / K0 finalized labels were completed with the unchanged teacher (replay 1,225 / 1,225 agree); 70 flagged scenes are excluded from Repair only.",
            "- The coverage diagnostic labelled the top 100 + 50 random (2D) / top 30 + 15 random (3D) candidates per root, so 'no successful candidate' is a lower bound.",
            "- V2 stopping rules chose γ = 0 on validation in both domains, so the 'no travel-cost term' row equals the full row for V2.",
            "- External 3D baselines (Table I(a)) are not run (deferred by the user)."]
    p = ABF / "runs" / "FINAL_REPORT.md"
    p.write_text("\n".join(out) + "\n")
    print(p)


if __name__ == "__main__":
    main()
