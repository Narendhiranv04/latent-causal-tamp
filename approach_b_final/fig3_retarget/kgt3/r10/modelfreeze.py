#!/usr/bin/env python3
"""R10.2 model freeze: hash every R10 checkpoint, record the VAL-only selections (r7.py select), and emit one composition config + env per run.
    python3 modelfreeze.py        (gvlab2)  -> r10/R10_MODEL_FREEZE.json, r10/comp/configs/<run>.{json,env}"""
import glob, hashlib, json, time
from pathlib import Path

W = Path("/home/projects/long-horizon/naren_workspace/r10")
REL = W / "release/LEGOLAS_FINAL_v1"
R = W / "runs"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ck = {}
    for pat in ("abf/runs/p1_*/*/model.pt", "runs/r7_task/*/*/model.pt", "runs/xy/p2_*/*/model.pt", "runs/xl/ckpt/*/model.pt",
                "k3/runs/training/taskfm/*/*/model.pt", "cr/models/*/*/model.pt"):
        for p in sorted(glob.glob(str(W / pat))):
            ck[str(Path(p).relative_to(W))] = sha(p)
    F = {d: json.loads((R / f"freeze_{d}.json").read_text()) for d in ("2d", "3d")}
    cr = {}
    for d in ("2d", "3d"):
        c = {Path(x).parent.name: json.loads(Path(x).read_text())["best_select"] for x in glob.glob(str(W / f"cr/models/{d}/r10_s*/curve.json"))}
        cr[d] = {"all": c, "pick": min(c, key=c.get), "rule": "lowest VAL select criterion (neg ELBO + decoder CE), as R8A"}
    tfm = {d: {Path(x).parent.name: json.loads(Path(x).read_text())["best_val_fm"] for x in glob.glob(str(W / f"k3/runs/training/taskfm/{d}/*/curve.json"))} for d in ("2d", "3d")}
    summ = {}
    for d in ("2d", "3d"):
        f = F[d]
        summ[d] = {"x": f["x"]["name"], "x_sha256": f["x"]["sha256"], "x_rep": f["x"]["rep"], "x_seed": f["x"]["seed"], "x_val_fam_nll": f["x"]["val_fam_nll"],
                   "seed_mean_val": f["x"]["seed_mean_val"], "temperature": f["calibration"], "y_base": f["y_base"], "cvae": f["cvae"]["pick"],
                   "cvae_sha256": f["cvae"]["sha256"], "cvae_val_elbo": f["cvae"]["all"], "spec": f["spec"], "cr": cr[d], "taskfm_val": tfm[d],
                   "taskfm_pick_rule": "TASKFM uses the FINAL cVAE seed (r8a.py convention)"}
    MF = {"version": "R10_MODEL_FREEZE_V1", "frozen_utc": time.strftime("%FT%TZ", time.gmtime()), "host": "gvlab2",
          "release_seal_sha256": json.loads((REL / "R10_DATASET_SEAL.json").read_text())["release_sha256"],
          "snapshot": next(iter(glob.glob(str(REL / "snapshot/abf_r10_*")))), "q2_scalers": {d: sha(REL / f"q2/q2_{d}/scalers.json") for d in ("2d", "3d")},
          "local_split_sha256": sha(REL / "views/local_split.json"), "packs": {d: sha(W / f"pack/pack_{d}.pt") for d in ("2d", "3d")},
          "selection_rules": {"x": "R5.2 simplest representation within max(seed spread of best, 0.005) of the best seed-mean local-family VAL NLL; lowest-VAL seed",
                              "calibration": "R5.3: temperature adopted iff VAL family NLL improves >= 0.005", "cvae": "lowest VAL ELBO (q2init_all)",
                              "pairing": "X paired with its own stage-B Y (same seed); cVAE seed chosen independently (R7 convention)"},
          "summary": summ, "checkpoints": ck, "results_files": {f"xl/results_{d}.jsonl": sha(R / f"xl/results_{d}.jsonl") for d in ("2d", "3d")}}
    (W / "R10_MODEL_FREEZE.json").write_text(json.dumps(MF, indent=1))
    # ------------------------------------------------ composition configs (3D)
    f = F["3d"]; xs, cs, rep = str(f["x"]["seed"]), f["cvae"]["pick"].rsplit("_s", 1)[1], f["x"]["rep"]
    base_cfg = {"selection_rule": "S0", "S2_tau": None, "length_bias_fraction": 0.45, "admit_rule": "A1", "admit_m": 0.1, "admit_eta": None,
                "prop_GA": "S1", "prop_REC": "ANC64"}
    cv = lambda s, nt=False: f"runs/r7_task/3d/{'q2init_all_notask' if nt else 'q2init_all'}_s{s}/model.pt"  # noqa: E731
    runs = {"main": (f["spec"], cv(cs), None, {}),
            "g0": (f"R7:3d_G0_hi_base_s{xs}", cv(cs), "REC-ORDERED,GA", {}),
            "yonly": (f["spec"], cv(cs), "GA-YPURE,GA-YONLY", {}),
            "notask": (f["spec"], cv(cs, True), "H3,REC-ORDERED,GA", {}),
            "cr": (f["spec"], cv(cs), "REC-ORDERED,GA", {"prop_GA": "CR4", "prop_REC": "CR8"}),
            "propmatch": (f["spec"], cv(cs), "REC-ORDERED,GA", {"prop_GA": "ANC64", "prop_REC": "S1"})}
    for s in ("0", "1", "2"):
        if s != xs:
            runs[f"x{s}"] = (f"R7:3d_{rep}1_hi_base_s{s}", cv(cs), "H3,REC-ORDERED,GA", {})
        if not (s == xs and s == cs):
            runs[f"seed{s}"] = (f"R7:3d_{rep}1_hi_base_s{s}", cv(s), "H3,REC-ORDERED,GA", {})
    (W / "comp/configs").mkdir(parents=True, exist_ok=True)
    for name, (spec, cvp, arms, over) in runs.items():
        xname = spec[3:].split("@T=")[0]
        sd = xname.rsplit("_s", 1)[1]
        cfg = {"3d": {"spec": spec, "checkpoint": xname, **base_cfg, **over, "cvae": cvp, "run": name}}
        (W / f"comp/configs/{name}.json").write_text(json.dumps(cfg, indent=1))
        env = {"R7_ROOT": str(R), "R7_CVAE_3D": str(W / cvp), "R7_Q2_SCALERS_3D": str(REL / "q2/q2_3d/scalers.json"), "R10_STRICT": "1",
               "R7_SHA_X_3D": sha(R / "xl/ckpt" / xname / "model.pt"), "R7_SHA_CVAE_3D": sha(W / cvp), "R7_SHA_BASE_3D": sha(R / f"xy/p2_3d/D_s{sd}/model.pt"),
               "R6_FLOOR": "final"}
        if arms:
            env["R6_ARMS"] = arms
        if name == "cr":
            env["R10_CR_MODEL"] = str(W / f"cr/models/3d/{cr['3d']['pick']}/model.pt"); env["CR_SCALERS_DIR"] = str(REL / "q2"); env["CR_BUNDLE"] = "/home/projects/long-horizon/naren_workspace/k3abl/stage/bundle"
        (W / f"comp/configs/{name}.env").write_text("".join(f"export {k}={v}\n" for k, v in env.items()))
    print(json.dumps({"summary": {d: {k: summ[d][k] for k in ("x", "x_val_fam_nll", "cvae", "spec")} for d in summ}, "runs": sorted(runs),
                      "n_checkpoints": len(ck)}, indent=1))


if __name__ == "__main__":
    main()
