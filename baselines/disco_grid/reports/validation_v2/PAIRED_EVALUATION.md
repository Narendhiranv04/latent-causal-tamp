# Paired evaluation status: BLOCKED

Candidate original-root pairing has been built from locked base scene inputs, raw scene hashes, goal/robot hashes, DISCO prediction trials and V3 archived slim selections. Every candidate root has a V3 selection in seeds 0, 1, 2:75 overall/45 task roots 2D;30 overall/18 task roots 3D. This is an identity candidate manifest, not a fully provenance-attested comparison.

The invented V3 snapshot path advertised by DISCO config is absent on gvlab. V3 sampler/scorer checkpoint bytes and complete hash-attested inference/verifier manifests were not found in the inventoried gvlab V3 stores. Slim selections contain only root IDs, sequences and decisions. Current deployed construct.py points to the base snapshot, but that alone cannot attest the inputs/weights/teacher revision used to generate every archived selection. V3.1 has separate provenance and ongoing verification; it was not substituted for V3.

No new cross-method success rate or paired CI is reported. Historical43.6%/77.3% Approach B and8.15%/27.78% DISCO remain unpaired preliminary aggregates. Primary protocol remains O0, one committed K≤3 plan, zero physical calls for proposal/ranking, one independent X/Y verification, no runner-up retry. O1 closed-loop no-retry/retry results must be separate.

Ready candidate manifest: paired_root_manifest.json. Regenerate on gvlab:

```sh
PY=/scratch/nav/disco_grid/venv/bin/python
$PY baselines/disco_grid/reports/validation_v2/build_pairing.py \
  --out /scratch/nav/disco_grid/validation_v2/evidence/paired_root_manifest.json
```

This command prepares pairing evidence; it does not bypass the provenance gate. Final paired verification cannot honestly be made runnable from missing checkpoints. Required inputs are the actual V3 and V3.1 checkpoint/run registries on the authorized host, hash-attested original inputs and teacher settings, and common administrative-censoring semantics. After these are frozen, both methods must use identical roots and final-verifier criteria; paired bootstrap requires exact domain/root sets and optionally identical seed coverage, rejects duplicates, and resamples roots after within-root seed averaging.
