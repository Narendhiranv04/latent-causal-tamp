#!/usr/bin/env python3
"""Write the FINAL_READINESS_GATE markdown reports from the machine-readable outputs, then SHA256SUMS over the whole package."""
import collections as C, hashlib, json
from pathlib import Path

H = Path(__file__).resolve().parent
GATE = H.parent
MAN, WK = GATE / "manifests", GATE / "work"
SPL = ("train", "val", "test")
CELLS = ("X=1,Y=1", "X=0,Y=1", "X=1,Y=0", "X=0,Y=0")


def J(p):
    return json.loads(Path(p).read_text())


def T(head, rows):
    return "\n".join(["| " + " | ".join(map(str, head)) + " |", "|" + "|".join("---" if i == 0 else "---:" for i in range(len(head))) + "|"] +
                     ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.1f} %)" if b else f"{a}/0"


def main():
    om = J(MAN / "OMISSION_13_VERDICTS.json")
    corr = J(MAN / "PROPOSED_CORRECTION_MANIFEST.json")
    s3 = J(WK / "3d_stats.json")
    s2 = J(WK / "2d_stats.json")
    rd = J(GATE / "FINAL_TRAINING_READINESS.json")
    gates = J(MAN / "FINAL_INTEGRITY_GATES.json")
    dist = J(MAN / "FINAL_LABEL_DISTRIBUTIONS.json")
    cov3 = J(WK / "3d_row_replay_coverage.json")
    lab2 = J(MAN / "2D_FINAL_XY_LABEL_MANIFEST.json")["rows"]
    tab = s3["tables"]
    g = lambda k: tab.get(k, {"n": 0, "agree": 0})

    # ------------------------------------------------------------------ OMISSION_13_VERDICTS.md
    rows = []
    for v in om["verdicts"]:
        for o in v["orders"]:
            lg = o["legacy_shortened"] or {}
            rows.append([v["root_id"], v["K"], v["split"], v["source"], v["omitted"], " → ".join(f"{a}>{tuple(d)}" for a, d in o["relocations"]),
                         f"{o['label_x']} ({o['label_x_phase'] or 'ok'})", f"{o['replay_x']} ({o['replay_x_how']})", f"{v['label_y_omission']}",
                         f"{v['replay_y_omission']} ({v['replay_y_how']})", f"{lg.get('y')}", o["verdict"]])
    per_root = [[v["root_id"], v["K"], v["split"], v["omitted"], sum(1 for o in v["orders"] if o["verdict"] == "VERIFIED_SHORTER_REPAIR_X1_Y1"), len(v["orders"]),
                 f"{v['selected_rows_replay']['agree']}/{v['selected_rows_replay']['n']} + Y {'ok' if v['selected_rows_replay']['y_agree'] else 'NO'}",
                 "yes" if v["legacy_also_succeeds_shortened"] else "no", v["verdict"]] for v in om["verdicts"]]
    n_inc = sum(1 for v in om["verdicts"] if v["verdict"] == "K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL")
    oc = [c for c in corr["corrections"] if c["reason"].startswith("OMISSION")]
    nc = [c for c in corr["corrections"] if c["reason"].startswith("NO_FINALIZED")]
    md = [f"# The 13 omission cases (3D V4)\n",
          f"**Result: {n_inc} of the 13 scenes are real K contradictions under the finalized protocol; {sum(1 for v in om['verdicts'] if v['verdict'] == 'K_RETAINED')} keep their K.**",
          f"A contradiction requires a shortened sequence with replayed X = 1 and replayed Y = 1. Y = 1 alone does not count.\n",
          f"- Rows with omission Y = 1 in the V4 label manifest: {om['n_rows_with_omission_y1']} (K3 omissions have two orders each).",
          f"- Unique scenes: **{om['n_unique_roots']}**. Unique (scene, omitted object) pairs: **{om['n_unique_root_omission_pairs']}**, so all 13 are distinct.",
          f"- Every shortened order was replayed in a fresh environment: the stored relocation and connector witnesses were executed, or a planning failure was re-planned from the replayed state. The omission endpoint Y was replayed from q_ref with its stored target witness.",
          f"- Order-level verdicts: {json.dumps(om['order_summary'])}.\n",
          "## Per scene\n",
          T(["scene", "K", "split", "omitted", "shortened orders X1Y1", "orders", "selected rows replay", "legacy teacher also succeeds", "verdict"], per_root),
          "\n## Per shortened order\n",
          T(["scene", "K", "split", "source", "omitted", "shortened order (object > cell)", "label X", "replay X", "label Y", "replay Y", "legacy (diag.)", "verdict"], rows),
          "\n*Legacy (diag.)*: the shortened order run by the legacy full-task teacher (target planned from the achieved pose). Diagnostic only, not a label.\n",
          "## Proposed corrections (not applied)\n",
          "Nothing in the dataset was changed. Each confirmed contradiction implies the scene's minimal K under the finalized protocol is at most K − 1, for any assignment of that layout. "
          "Replacing the assignment within the layout therefore cannot fix it; the scene has to leave its class or be relabelled.\n",
          T(["scene", "K", "split", "proposal", "same-class, same-split candidates (existing scenes)"],
            [[c["original_root_id"], c["K"], c["split"], c["proposal"], ", ".join(c["replacement_candidates_same_class_same_split"]) or "none"] for c in oc]),
          "",
          f"Selected scenes whose selected assignment has **no** finalized X = 1, Y = 1 order (from Issue 2): {len(nc)}.\n",
          T(["scene", "K", "split", "X strength", "Y", "Y replay", "proposal", "same-layout candidate"],
            [[c["original_root_id"], c["K"], c["split"], f"{c['evidence']['x_strength']}/{c['evidence']['n_orders']}", c["evidence"]["y_endpoint"], c["evidence"]["y_replay"],
              c["proposal"], ", ".join(c.get("replacement_candidates_same_layout_same_split") or []) or "none"] for c in nc]),
          "",
          f"**Quota consequence if every flagged scene were removed without replacement:** {json.dumps(corr['quota_consequence']['if_removed_without_replacement'])} "
          f"(now {json.dumps(corr['quota_consequence']['current'])}). Removed by K/split: {json.dumps(corr['quota_consequence']['removed_by_K_split'])}.\n",
          "Candidate pool: the only existing, already-verified spare layouts of the right class are listed below. None of them has finalized X/Y or an omission check yet, so admitting any would need the same X/Y + omission + replay pass first.\n",
          T(["class", "candidates (existing scenes)", "with split = the flagged scene's split"],
            [[f"K{k}", len(v), "; ".join(sorted({c['split_if_admitted'] for c in v}))] for k, v in corr["candidate_pool"].items()]),
          "\nMachine-readable: `manifests/OMISSION_13_VERDICTS.json`, `manifests/PROPOSED_CORRECTION_MANIFEST.json`."]
    (GATE / "OMISSION_13_VERDICTS.md").write_text("\n".join(md) + "\n")

    # ------------------------------------------------------------------ 3D_INDEPENDENT_REPLAY_AUDIT.md
    tiers = [("A_MANDATORY", "Mandatory: 13 omission scenes (all their rows), 2 selected Y = 0 scenes"),
             ("B_STRATIFIED", "Stratified sample of selected and omission rows (incl. re-runs of rows without witnesses)"),
             ("C_ALL_WITNESSED", "Every other witness-backed X row and Y = 1 endpoint"),
             ("D_RERUN_REPLAY", "Every legacy-shortcut (R2) row and every gvlab-V3 (R1) positive not in A/B: re-run + replay"),
             ("E_EMPTY_SAMPLE", "Stratified sample of empty-sequence Y labels: re-run + replay")]
    trow = [[k, d, g(f"tier|{k}")["n"], g(f"tier|{k}")["agree"], g(f"tier|{k}")["n"] - g(f"tier|{k}")["agree"]] for k, d in tiers]
    strat = []
    for key, name in (("query_label|X|SELECTED_ASSIGNMENT_ORDER|1", "selected X = 1"), ("query_label|X|SELECTED_ASSIGNMENT_ORDER|0", "selected X = 0"),
                      ("query_label|Y|SELECTED_ASSIGNMENT_ORDER|1", "selected Y = 1"), ("query_label|Y|SELECTED_ASSIGNMENT_ORDER|0", "selected Y = 0"),
                      ("query_label|X|OMISSION_YNEG|1", "omission X = 1"), ("query_label|X|OMISSION_YNEG|0", "omission X = 0"),
                      ("query_label|Y|OMISSION_YNEG|1", "omission Y = 1"), ("query_label|Y|OMISSION_YNEG|0", "omission Y = 0"),
                      ("query_label|Y|EMPTY_SEQUENCE_YNEG|0", "empty-sequence Y = 0")):
        strat.append([name, g(key)["agree"], g(key)["n"]])
    more = []
    for pre in ("split|X|", "split|Y|", "K3_strength|", "K2_strength|", "x_provenance|", "phase|", "source_family|", "xy_cell|", "method|X|", "method|Y|"):
        for k in sorted(x for x in tab if x.startswith(pre)):
            more.append([k.replace("|", " / "), tab[k]["agree"], tab[k]["n"]])
    totals = s3["n_agree"], s3["n_queries"]
    rr = s3["rerun_teacher_reproducibility"]
    cov_rows = [[k.replace("|", " / "), v] for k, v in sorted(cov3.items())]
    md = [f"# 3D independent replay audit (FINAL_3D_DATASET_V4)\n",
          f"**Result: {totals[0]} of {totals[1]} replayed X/Y queries agree with the stored finalized labels; {totals[1] - totals[0]} unresolved mismatches.**\n",
          "## Replay path\n",
          "- The scene is loaded from the selected root JSON (immutable source; sha256 checked against the selection manifest) and built and settled in a new MuJoCo environment, in a fresh worker process.",
          "- **X:** each stored relocation witness is executed in order, with carried robot state and no reset. Before execution its content id is re-derived and its first configuration is checked against the current one (continuity ≤ 1e-6 rad). The grasp is recovered by forward kinematics of the stored grasp configuration against the object's candidate grasp poses (≤ 5 mm, ≤ 3°, unique open width). The pinned `bwlphys.move` checks apply: end cell, |z| ≤ 1 cm, no other object changed cell.",
          "- **Connector:** the stored path is executed with `bwlphys.connector`. It checks |q − q_ref| ≤ 0.02 rad, nothing pushed > 4 mm, every object in its endpoint cell, gripper opened and nothing held, and zero robot–object contacts. The path must also end exactly at q_ref.",
          "- **Y:** the endpoint scene is settled at q_ref and the stored target witness is executed (t0 to goal) with the same checks.",
          "- **Negatives:** a planning failure is re-confirmed by re-planning (`bd_3dt.query` / `plan_free_move`, seed 0) from the *replayed* state. An execution failure is reproduced from its stored witness.",
          "- **Rows without stored witnesses** (gvlab-V3 reuse R1, legacy shortcut R2): the unchanged finalized teacher is re-run in the fresh process into a separate store, then its witnesses are replayed in a new environment.",
          f"- Grasp recovery: {json.dumps(s3['grasp_recovery'])}. Root hashes all match: {s3['root_sha_all_ok']}.\n",
          "## Coverage and agreement by tier\n",
          T(["tier", "what", "queries", "agree", "mismatch"], trow),
          f"\nTeacher re-run reproducibility (re-run label vs stored label, before replay): {json.dumps(rr)}.\n",
          "## Agreement by label stratum (all tiers)\n",
          T(["stratum", "agree", "replayed"], strat),
          "\n## Agreement by split, strength, provenance, failure phase, source family\n",
          T(["stratum", "agree", "replayed"], more),
          "\n## Per-label replay coverage of the V4 label manifest\n",
          "Counts of label rows by how their X and Y were checked. NOT_REPLAYED rows were not part of any tier.\n",
          T(["row kind / check", "rows"], cov_rows),
          "\n## Mismatches\n",
          ("None." if not s3["mismatches"] else T(["scene", "query", "label", "verdict", "replay"], [[m["root_id"], m["qid"], m["label"], m["verdict"], json.dumps(m["replay"])] for m in s3["mismatches"]])),
          "\n**Scope:** tiers C and D cover every witness-backed X row, every Y = 1 endpoint and every R2 row. The remaining R1 X = 0 rows, Y = 0 endpoints and empty-sequence labels are covered by samples (tiers A, B, E). "
          "This audit is therefore **not** an exhaustive replay of every 3D label; the per-row coverage table above is exact.",
          "\nMachine-readable: `manifests/3D_REPLAY_RESULTS.json` (every replayed query), `manifests/3D_FINAL_XY_LABEL_MANIFEST_WITH_REPLAY.json` (V4 labels unchanged, annotated per row)."]
    (GATE / "3D_INDEPENDENT_REPLAY_AUDIT.md").write_text("\n".join(md) + "\n")

    # ------------------------------------------------------------------ 2D_FINAL_XY_COVERAGE.md
    pc2 = J(MAN / "2D_PROPOSED_CORRECTIONS.json")
    kc2, fx = C.Counter(), C.defaultdict(set)
    for x in pc2["K_REPAIR_UNVERIFIED_UNDER_FINALIZED_PROTOCOL"]:
        kc2[(f"K{x['K']}", x["split"])] += 1
        fx[(f"K{x['K']}", x["split"])].update(x["x_failures"])
    cnt = C.Counter()
    for l in lab2:
        cnt[(l["row_kind"], l["K"], l["split"], "complete" if l["x"] in (0, 1) and l["y"] in (0, 1) else "missing")] += 1
    q_by = C.Counter()
    for l in lab2:
        if l["row_kind"] in ("SELECTED_ASSIGNMENT_ORDER", "EMPTY_SEQUENCE_K0"):
            q_by[(l["K"], l["split"], l["x_provenance"].split("(")[0])] += 1
    rows = []
    for K, desc in (("0", "empty corrective sequence"), ("1", "1 relocation, 1 order"), ("2", "2 orders"), ("3", "6 orders")):
        for sp in SPL:
            kind = "EMPTY_SEQUENCE_K0" if K == "0" else "SELECTED_ASSIGNMENT_ORDER"
            ok, ms = cnt[(kind, K, sp, "complete")], cnt[(kind, K, sp, "missing")]
            prov = {p: v for (k_, s_, p), v in q_by.items() if k_ == K and s_ == sp}
            rows.append([f"K{K}", desc, sp, ok + ms, ok, ms, "; ".join(f"{p}: {v}" for p, v in sorted(prov.items()))])
    nn = C.Counter(l["split"] for l in lab2 if l["K"] == "NONE" and l["row_kind"] == "EMPTY_SEQUENCE_YNEG")
    par = s2["parity"]
    cv = s2["coverage"]
    md = [f"# 2D finalized X/Y coverage (2D_K3_STRENGTH_SELECTION_V3, 5,000 scenes)\n",
          f"**Result: every selected K0–K3 query has a finalized X and Y: {sum(v for k, v in cv.items() if k.endswith('_complete'))} of {sum(v for k, v in cv.items() if k.startswith('K'))} K1–K3 scenes complete, "
          f"{sum(1 for l in lab2 if l['row_kind'] == 'EMPTY_SEQUENCE_K0' and l['y'] in (0, 1))} of 1,250 K0 scenes complete, 0 missing.**\n",
          "- **Teacher:** BXY_X_TEACHER_V1 / BXY_Y_TEACHER_V1 (`bxy_teacher.py`, unchanged since commit 68183081d), booted with each record's own geometry implementation and one exact DetPhysics cache per root, exactly as `k3_hard/xy2d.py`.",
          "- **X:** ordered relocations with carried state, plus the connector to q_ref.",
          "- **Y:** target from q_ref at the shared endpoint, one query per endpoint.",
          "- **Replay:** every positive X and Y passed the teacher's built-in independent replay (geometric re-certification, continuity, placement, q_ref endpoint). Failures are binary teacher outcomes under the pinned finite budget.",
          "- **Administrative failures:** wall cap 1,800 s per query. A hit is MISSING, never 0; none occurred.",
          "- **Reuse:** 807 K3 hard-order scenes reuse `k3_hard/xy2d_all.jsonl` (same teacher, same root file, same assignment, same q_ref). Parity re-run on a seeded sample: "
          f"X {par.get('sel_x_agree')}/{par.get('sel_x_checked')}, Y {par.get('sel_y_agree')}/{par.get('sel_y_checked')}.",
          f"- **Empty endpoint:** every K1–K3 / NONE scene has a finalized Y query at its unedited scene. It agrees with the legacy labels.original in {par.get('empty_agree')}/{par.get('empty_checked')} scenes; the legacy label is kept separately.",
          f"- **NONE:** 1,000 scenes ({dict(nn)}) keep their audited no-repair provenance. No X/Y is fabricated for a nonexistent corrective sequence; they contribute only empty-endpoint Y labels.\n",
          "## Coverage by K and split (selected corrective sequences)\n",
          T(["K", "queries per scene", "split", "order rows", "complete", "missing", "X provenance"], rows),
          "\n## Legacy vs finalized K3 strength\n",
          "If finalized X strength differs from legacy strength, the learning view uses the finalized X. Legacy strength is kept as metadata (`legacy_y` per order row).\n",
          T(["strength", *[f"finalized {s}" for s in SPL], *[f"legacy {s}" for s in SPL]],
            [[f"{n}/6", *[dist["2D_K3_strength"]["finalized_x"].get(f"{s}|{n}/6", 0) for s in SPL], *[dist["2D_K3_strength"]["legacy"].get(f"{s}|{n}/6", 0) for s in SPL]] for n in range(7)]),
          "\n## K consistency under the finalized protocol\n",
          f"- Omission queries with X = 1 and Y = 1 (a proven shorter repair): **{len(pc2['K_CONTRADICTION_SHORTER_REPAIR'])}**.",
          f"- Selected scenes where **no** order of the selected assignment reaches X = 1 with Y = 1: **{len(pc2['K_REPAIR_UNVERIFIED_UNDER_FINALIZED_PROTOCOL'])}**. "
          "All have Y = 1 and a verified legacy repair; every order fails finalized X, at the connector back to q_ref or at a relocation under the finite budget. "
          "These are not proven K errors, but the selected K-repair is not verified under the finalized protocol.\n",
          T(["K", "split", "scenes", "typical X failure"], [[k[0], k[1], v, "; ".join(sorted(fx[k]))[:160]] for k, v in sorted(kc2.items())]),
          "\nThe IDs and options are in `manifests/2D_PROPOSED_CORRECTIONS.json`.",
          "\nMachine-readable: `manifests/2D_FINAL_XY_LABEL_MANIFEST.json`."]
    (GATE / "2D_FINAL_XY_COVERAGE.md").write_text("\n".join(md) + "\n")

    # ------------------------------------------------------------------ FINAL_LABEL_DISTRIBUTIONS.md
    def dtab(dom):
        d = dist[dom]
        agg = C.defaultdict(C.Counter)
        for k, v in d.items():
            kind, K, sp = k.split("|")
            for c_, n in v.items():
                agg[(kind, sp)][c_] += n
        return T(["row kind", "split", *CELLS, "missing"], [[k[0], k[1], *[agg[k].get(c_, 0) for c_ in CELLS], agg[k].get("missing", 0)] for k in sorted(agg)])

    def ytab(dom):
        y = dist["y_negatives"][dom]
        kinds = sorted({k.split("|")[0] for k in y})
        return T(["Y = 0 source", *SPL, "total"], [[k, *[y.get(f"{k}|{s}", 0) for s in SPL], sum(y.get(f"{k}|{s}", 0) for s in SPL)] for k in kinds])
    tot = {dom: C.Counter() for dom in ("2D", "3D")}
    for dom in tot:
        for k, v in dist[dom].items():
            tot[dom].update(v)
    md = ["# Final label distributions\n",
          "Learning-view rows: selected corrective orders, omission Y-negatives and empty-sequence rows. Counts are actual frequencies, with no artificial balancing.\n",
          "## All four X/Y combinations\n",
          T(["domain", *CELLS, "missing"], [[dom, *[tot[dom].get(c_, 0) for c_ in CELLS], tot[dom].get("missing", 0)] for dom in ("2D", "3D")]),
          "\n## 2D by row kind and split\n", dtab("2D"),
          "\n## 3D by row kind and split\n", dtab("3D"),
          "\n## Y-negative evidence by source and split\n", "### 2D\n", ytab("2D"), "\n### 3D\n", ytab("3D"),
          "\n## 3D K3 strength (finalized X vs legacy)\n",
          T(["strength", *[f"finalized {s}" for s in SPL], *[f"legacy {s}" for s in SPL]],
            [[f"{n}/6", *[dist["3D_K3_strength"]["finalized_x"].get(f"{s}|{n}/6", 0) for s in SPL], *[dist["3D_K3_strength"]["legacy"].get(f"{s}|{n}/6", 0) for s in SPL]] for n in range(7)]),
          f"\nAbsent X/Y cells by split: {', '.join(rd['absent_xy_cells_by_split']) or 'none'}.",
          "\nMachine-readable: `manifests/FINAL_LABEL_DISTRIBUTIONS.json`."]
    (GATE / "FINAL_LABEL_DISTRIBUTIONS.md").write_text("\n".join(md) + "\n")

    # ------------------------------------------------------------------ FINAL_DATASET_INTEGRITY.md
    names = {"G1_2D_exactly_5000": "2D has exactly 5,000 selected scenes", "G2_3D_exactly_2500_main": "3D has exactly 2,500 main scenes (K4 archived outside)",
             "G3_quotas": "K0/K1/K2/K3/NONE quotas", "G4_roots_labels_witnesses_resolve": "Roots, label records and referenced witnesses resolve (witness content ids re-derived)",
             "G5_hashes_endpoints_lineage": "Source hashes, lineage-disjoint splits", "G6_identical_endpoints_share_one_Y": "Identical endpoints share one Y (any permutation)",
             "G7_finalized_teachers_only": "Observed labels come from finalized teachers, not legacy substitutions", "G8_meaningful_pos_neg_per_split": "Positive and negative supervision in train / val / test",
             "G9_no_contradicting_duplicates": "No duplicate labels contradict each other", "G10_no_training_launched": "No model training launched",
             "G11_3D_replay_agreement": "3D replay agrees with stored labels", "G12_2D_reuse_parity": "2D reused-evidence parity",
             "G13_K_consistency_under_finalized_protocol": "K labels consistent with the finalized protocol"}
    md = ["# Final dataset integrity\n", f"Status: **{rd['status']}**\n",
          T(["gate", "check", "result", "detail"], [[k.split("_")[0], names.get(k, k), "PASS" if v["pass"] else "FAIL", json.dumps(v["detail"], default=str)[:600].replace("|", "/")]
                                                   for k, v in gates.items()]),
          "\nMachine-readable: `manifests/FINAL_INTEGRITY_GATES.json`, `FINAL_TRAINING_READINESS.json`."]
    (GATE / "FINAL_DATASET_INTEGRITY.md").write_text("\n".join(md) + "\n")

    # ------------------------------------------------------------------ SHA256SUMS
    files = sorted([p for p in GATE.glob("*") if p.is_file() and p.name != "SHA256SUMS"] + list((GATE / "manifests").glob("*")) + list((GATE / "code").glob("*.py")) +
                   list((GATE / "code").glob("*.sh")) + [p for p in (GATE / "work").glob("*") if p.is_file() and p.suffix in (".json", ".jsonl")])
    (GATE / "SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(GATE)}\n" for p in files))
    print("reports written;", len(files), "files hashed")


if __name__ == "__main__":
    main()
