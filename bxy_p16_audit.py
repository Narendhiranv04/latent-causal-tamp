"""BXY-P16 audit: reproduction of the P12-P15 aggregate results from the committed artifacts, frozen-artifact hash guard, and the
machine-readable requirements-to-evidence matrix (methodology 2026-10-31 + execution contract BXY-P16..P18).
    python3 bxy_p16_audit.py reproduce | guard | matrix"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

OUT = Path("runs/approach_b/bxy_p16_v1")
FROZEN = ("runs/approach_b/bxy_pmin_v1", "runs/approach_b/bxy_p11_v1", "runs/approach_b/bxy_p11_1_v1", "runs/approach_b/bxy_p12_v1",
          "runs/approach_b/bxy_p13_v1", "runs/approach_b/bxy_p14_v1", "runs/approach_b/bxy_p15_v1", "runs/approach_b/bd2d_lb_v1",
          "runs/approach_b/bxy", "runs/approach_b/bxy_teacher_pilot_v1")


def reproduce() -> dict:
    """P12 (bxy_p13.reproduce), P14 (bxy_p14_eval.evaluate vs EVALUATION_P14.json, accounting excluded), P15 (summarize vs PILOT_SUMMARY)."""
    import bxy_p13 as P13
    import bxy_p14_eval as E14
    import bxy_p15 as P15
    t0 = time.process_time()
    out = {"P12": P13.reproduce()}
    new = json.loads(json.dumps(E14.evaluate(), sort_keys=True, default=str))
    old = json.loads((Path("runs/approach_b/bxy_p14_v1") / "EVALUATION_P14.json").read_text())
    for d in (new, old):
        d.pop("accounting", None)
    out["P14"] = {"identical": new == old, "differing": sorted(k for k in set(new) | set(old) if new.get(k) != old.get(k)),
                  "C3": old["contrasts"].get("C3", {}).get("primary") if isinstance(old.get("contrasts"), dict) else None}
    s = json.loads(json.dumps(P15.summarize(), sort_keys=True, default=str))
    o = json.loads((P15.OUT / "PILOT_SUMMARY.json").read_text())
    out["P15"] = {"identical": s == o, "verified_K": o["verified_K"], "roots": o["roots"]}
    out["cpu_s"] = round(time.process_time() - t0, 1)
    return out


def guard() -> dict:
    """Every tracked file under the frozen run directories equals HEAD (git diff empty) and no untracked file appeared inside them."""
    diff = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", *FROZEN], capture_output=True, text=True).stdout.split()
    new = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", *FROZEN], capture_output=True, text=True).stdout.splitlines()
    return {"modified": diff, "untracked_or_changed": new, "ok": not diff and not new}


S, W, U, M = "SUPPORTED", "EVIDENCE_WEAK", "IMPLEMENTED_UNTESTED", "MISSING"


def matrix() -> list:
    """Requirement rows at the START of P16 (evidence from P-min..P15 only). P16 / P17 / P18 add later columns in their own reports."""
    R = []

    def r(req, semantics, impl, tests, evidence, failures, status, missing, minimal_test):
        R.append({"requirement": req, "semantics": semantics, "implementation": impl, "tests": tests, "evidence": evidence,
                  "observed_failures": failures, "status_before_P16": status, "missing_work": missing, "minimal_test": minimal_test})
    r("F1 analytic screen", "sound identity / legal-cell / sequential occupancy / endpoint overlap / goal-blocked rules; never a label",
      "bxy_f1.screen / endpoint (BXY_F1_V1)", "tests/test_bxy_p11.py, test_bxy_teacher.py", "applied to every P-min / P15 query design",
      "none", S, "-", "order-specific DEST_OCCUPIED microcase (exists)")
    r("F2 ordered-prefix X unary", "a_q from object ids, destinations, robot start, ideal object prefixes (predecessor-aware tokens)",
      "bxy_v2.ModelXY2 / bxy_p11.Model order='pred'", "test_bxy_p11.py", "P12 order concordance on certified pairs ~chance (P13)",
      "order ranking near chance; few measured same-endpoint discordant pairs", W, "measured F1-admissible same-endpoint X-discordant pairs; "
      "order-invariant control", "order twins with recorded X discordance (P16 nested / interference families)")
    r("F3 hypothetical-scene Y unary", "b_s from the edited scene at fixed q_ref", "ModelXY2 scene head (+P14 GEO)", "test_bxy_p11.py",
      "P13: within-root edited-Y AUROC 0.42-0.48 OOF; P14 GEO 0.65", "universal edit bonus; harmful (1->0) edits ~0.14 agreement", W,
      "harmful-edit contrasts in nontrivial number of roots", "Y0=1 / Y_edit=0 contrasts in >= 12 roots")
    r("F4 omissions", "recomputed q_-t evaluated by the same F2 / F3 networks; no pair head", "bxy_pmin design classes 'omission'",
      "test_bxy_p11.py omission identity", "P-min omission X/Y queries", "omission sign accuracy weak (P12/P13)", W,
      "omissions of verified K>=2 repairs (both directions)", "omission of a verified K>=2 repair with recorded Y")
    r("F5 single quadratic XY coupling", "w_q x y inside a root-consistent normalized factorization", "bxy_core / bxy_p11.log_evidence",
      "brute-force 4-state microcases (test_bxy_p11.py)", "P12: no gain over capacity-matched uncoupled", "-", W,
      "matched w=0 control on harder data", "XYQ vs XY-UNC-SA same features / data / compute")
    r("root-consistent exact likelihood", "one Y node per endpoint; P(X|Y) normalized; unobserved marginalized exactly",
      "bxy_p11.log_evidence / root_terms", "microcases: marginal invariance to appended X, gradients", "P11-P14 training", "none", S, "-", "exists")
    for cell in ("00", "01", "10", "11"):
        r(f"X/Y cell {cell}", f"(X, Y) = ({cell[0]}, {cell[1]}) observed for a matched prefix", "teacher x_query / y_query pairs",
          "test_bxy_teacher.py", "P-min paired=2,222 (all four cells present)", "-", S if cell != "01" else W, "cells in hard, multi-blocker roots",
          "count per independent root in V2.1")
    r("Y shared across orders", "same endpoint -> one Y key regardless of order", "bxy_teacher.ykey (endpoint), bxy_p11 shared parent",
      "test_bxy_teacher.py, test_bxy_p11.py", "every design", "none", S, "-", "exists")
    r("no-op", "X_empty = 1; success = P(Y0); no movement invented if the no-op rule passes", "bxy_p11.choose noop_gate", "test_bxy_p11.py",
      "P12-P14 selection", "no-op overconfidence / unnecessary repairs (P14 CON+GEO +0.112)", W, "probability-consistent comparison P(Y0) vs p_succ",
      "unnecessary-repair rate on Y0=1 roots with harmful-edit alternatives")
    r("physical connector to q_ref", "X=1 requires a certified connector from the achieved state to q_ref, gripper free, edited scene",
      "bxy_teacher.x_query + replay_x", "test_bxy_teacher.py", "every positive X since P9", "none", S, "connector-sensitive negatives",
      "X=0 at failed_phase connector with relocations verified")
    r("achieved state carried between moves", "no q0 reset between relocations", "bxy_teacher.x_query (q carried), replay_x continuity",
      "test_bxy_teacher.py", "every X witness", "none", S, "-", "exists")
    r("prefixes 1..6", "every stopping prefix is an X (with connector) and a Y query", "P-min classes (complete / omission)", "test_bxy_p11.py",
      "P-min lengths <= 4 mostly; no prefix-complete repairs", "length-5/6 never labelled", W, "prefix-complete supervision of K>=2 repairs",
      "X and Y at every prefix of a verified K>=2 repair")
    r("K0-K4 coverage", "verified K (fewest moves within the finite catalogue)", "bxy_p15.summarize verified_K", "-",
      "P-min K>=2: 5 roots; P15 pilot: 1 K2 in 28", "generator easy", W, "V2.1 access-closure generator", ">= 12 verified K>=2 roots")
    r("redundant / harmful edits", "unnecessary moves and edits turning Y0=1 into 0", "P15 catalogue 'unnecessary_displacement'", "-",
      "few harmful contrasts", "P14 fails to predict 1->0", W, "designed harmful vs neutral contrasts", ">= 12 roots with Y0=1/Y_edit=0")
    r("physics vs search-budget failures", "negative_kind CERTIFIED vs TIMEOUT / NO_PLAN_FOUND kept evaluator-side", "bxy_teacher _neg", "-",
      "every negative carries negative_kind", "none", S, "-", "exists")
    r("outcome-blind candidate generation", "catalogue from geometry only", "bxy_p15.candidates", "test_bxy_p15.py", "P15 pilot",
      "too easy (21/28 K0)", W, "V2.1 access-closure catalogue", "label-flip invariance of the catalogue")
    r("travel J / J_hat", "complete-witness joint travel; J_hat supervised only on complete witnesses", "bxy_teacher.pair, bxy_v2 cost head",
      "test_bxy_p11.py", "P-min complete J = 1,452, no-op J = 142", "-", S, "matched successful-case travel comparison", "travel on matched successes")
    r("teacher / learner separation", "ScorerView never contains labels / roles / travel / witnesses", "bxy_p11.check_scorer FORBIDDEN",
      "test_bxy_p11.py, test_bxy_p13.py", "every run", "none", S, "V2 adapter for new roots", "privileged-mutation invariance (bxy_p16_inputs)")
    r("V2 learner inputs", "frozen DINOv2 + learner tensors for new roots, label-free", "MISSING before P16", "-", "-", "P15 roots had no inputs",
      M, "bxy_p16_inputs", "P-min equivalence to 0 tolerance + mutation invariance")
    return R



def matrix_after(waves) -> dict:
    """Evidence counts from the labelled P16 development waves (independent roots as denominators) and the updated status per requirement."""
    import collections
    import bxy_p16 as G
    rows = [r for w in waves for r in json.loads((G.wdir(w) / "SUMMARY.json").read_text())["rows"] if r["results"]]
    n = len(rows)
    cell_roots = {c: sum(r["cells"].get(c, 0) > 0 for r in rows) for c in ("00", "01", "10", "11")}
    prefix_len = collections.Counter(x["m"] for r in rows for x in r["rows"] if x["x"] is not None)
    rep2 = [r for r in rows if r["repair"] and r["repair"]["m"] >= 2]
    full_prefix = [r for r in rep2 if None not in r["repair"]["prefix_y"] and None not in r["repair"]["prefix_x"] and r["repair"]["y"] is not None]
    ver_prefix = [r for r in full_prefix if r["repair"]["x"] == 1 and r["repair"]["y"] == 1]
    omis = collections.Counter()
    for r in rows:
        byk = {x["kind"]: x for x in r["rows"]}
        rp = byk.get("repair")
        for k, x in byk.items():
            if k.startswith("omission_") and rp and rp["y"] is not None and x["y"] is not None:
                omis["observed"] += 1
                omis["Y_differs_from_full"] += x["y"] != rp["y"]
    neg = collections.Counter()
    for r in rows:
        for side in ("x_neg", "y_neg"):
            for k, v in r[side].items():
                neg[f"{side[0]}:{k}"] += v
    conn = sum(r["connector_failures"] for r in rows)
    disc = [d for r in rows for d in r["discordant"]]
    vk = collections.Counter(str(r["verified_K"]) for r in rows)
    ev = {"labelled_roots": n, "y0_0": sum(r["y0"] == 0 for r in rows), "y0_1": sum(r["y0"] == 1 for r in rows), "verified_K": dict(vk),
          "xy_cell_roots": cell_roots, "labelled_prefix_lengths": dict(sorted(prefix_len.items())), "repairs_m_ge2": len(rep2),
          "repairs_m_ge2_prefix_complete": len(full_prefix), "verified_repairs_prefix_complete": len(ver_prefix),
          "omissions": dict(omis), "negatives": dict(neg), "connector_failures": conn, "discordant_pairs": len(disc),
          "discordant_pairs_certified": sum(any(o[2] == "CERTIFIED" for o in d["orders"]) for d in disc),
          "harmful_contrast_roots": sum(bool(r["harmful"]) for r in rows)}
    st = lambda ok, weak: S if ok else (W if weak else U)  # noqa: E731
    upd = {"F2 ordered-prefix X unary": st(len(disc) >= 4, len(disc) > 0) + " (data); learned-order evidence: P17",
           "F3 hypothetical-scene Y unary": "data " + st(ev["harmful_contrast_roots"] >= 12, ev["harmful_contrast_roots"] > 0) + "; learning: P17",
           "F4 omissions": st(omis["Y_differs_from_full"] >= 10, omis["observed"] > 0) + " (data)",
           "X/Y cell 01": st(cell_roots["01"] >= 10, cell_roots["01"] > 0), "prefixes 1..6": st(len(ver_prefix) >= 5, len(full_prefix) > 0),
           "K0-K4 coverage": st(sum(v for k, v in vk.items() if k.isdigit() and int(k) >= 2) >= 12, True),
           "physical connector to q_ref": st(conn > 0, False) + f" ({conn} connector-phase negatives)",
           "redundant / harmful edits": st(ev["harmful_contrast_roots"] >= 12, ev["harmful_contrast_roots"] > 0),
           "V2 learner inputs": S, "outcome-blind candidate generation": S}
    return {"evidence": ev, "status_after_P16": upd, "waves": list(waves)}


if __name__ == "__main__":
    cmd = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    if cmd == "reproduce":
        res = reproduce()
        (OUT / "REPRODUCTION_P12_P15.json").write_text(json.dumps(res, indent=1, sort_keys=True, default=str))
        print(json.dumps(res, default=str))
    elif cmd == "guard":
        print(json.dumps(guard()))
    elif cmd == "after":
        m = matrix_after(sys.argv[2:])
        (OUT / "REQUIREMENTS_MATRIX_AFTER_P16.json").write_text(json.dumps(m, indent=1))
        print(json.dumps(m["evidence"]))
    elif cmd == "matrix":
        (OUT / "REQUIREMENTS_MATRIX_START.json").write_text(json.dumps(matrix(), indent=1))
        print(len(matrix()))
