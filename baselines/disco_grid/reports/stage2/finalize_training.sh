#!/bin/sh
# Serial byte audit, TRAIN reporting and saved-state display, never held-out physics.
set -eu
stage_source=$1
stage_campaign=$2
stage_commit=$3
stage_evidence=$4
stage_python=/scratch/nav/disco_grid/venv/bin/python
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export DISCO_SOURCE_COMMIT="$stage_commit"
while [ ! -f "$stage_campaign/posttrain_v2/COMPLETE.json" ]; do sleep 30; done
stage_out="$stage_campaign/training_release_v1"
mkdir "$stage_out"
cd "$stage_source"
timeout --kill-after=5s 240s "$stage_python" -m pytest baselines/disco_grid/tests/test_d0_audit.py baselines/disco_grid/tests/test_d2_policy.py baselines/disco_grid/tests/test_d3_d4_mcts_distill.py baselines/disco_grid/tests/test_d6_d7_evaluate.py baselines/disco_grid/tests/test_validation_v2.py baselines/disco_grid/tests/test_stage2.py baselines/disco_grid/tests/test_physical_eval.py -q > "$stage_out/tests.log" 2>&1
"$stage_python" baselines/disco_grid/reports/stage2/audit_inputs.py "$stage_out/archive_audit" > "$stage_out/archive_audit.log" 2>&1
"$stage_python" baselines/disco_grid/reports/stage2/summarize_campaign.py "$stage_campaign" "$stage_out" > "$stage_out/coverage.log" 2>&1
/usr/bin/time -v "$stage_python" baselines/disco_grid/reports/stage2/training_figures.py "$stage_campaign" "$stage_out/training_coverage.json" "$stage_out/train_figures" > "$stage_out/figures.log" 2> "$stage_out/figures_cost.log"
timeout --kill-after=5s 300s /usr/bin/time -v "$stage_python" - "$stage_source" "$stage_campaign" "$stage_out" > "$stage_out/scenes.log" 2> "$stage_out/scenes_cost.log" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
source,campaign,out=map(Path,sys.argv[1:]);cohorts=json.loads((campaign/'manifest.json').read_text())['cohorts'];paths=[];selection=[]
for dom in ('2d','3d'):
    for k in ('0','1','2','3','NONE'):
        root=next(r for r in cohorts['domains'][dom]['train_roots'] if str(r['K_legacy'])==k)
        path=campaign/f'trees/{dom}/R0'/root['root_id']/root['root_id']/'query_000001_parent.pkl'
        if not path.is_file():raise FileNotFoundError(path)
        paths.append(path);selection.append(dict(domain=dom,K=k,path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),selection='first frozen TRAIN root in stratum; original saved physical state'))
for case in (0,2):
    for query in (1,2,3):
        path=Path('/scratch/nav/disco_grid/stage2/verification/train_parity_d1ccb34')/f'case_{case}'/f'query_{query:06d}_parent.pkl'
        paths.append(path);selection.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),selection='all three saved states in successful ordered TRAIN parity fixture; executed endpoint poses, not an invented motion path'))
(out/'SCENE_SELECTION.json').write_text(json.dumps(selection,indent=2)+'\n')
subprocess.run([sys.executable,str(source/'baselines/disco_grid/reports/stage2/scene_evidence.py'),'--states',*map(str,paths),'--out',str(out/'scenes')],check=True)
PY
printf '%s\n' '{"status":"TRAIN_RELEASE_PREPARED","heldout_physical_results":"NOT_RUN","source_commit":"'"$stage_commit"'"}' > "$stage_out/COMPLETE.json"
"$stage_python" baselines/disco_grid/reports/stage2/artifact_index.py "$stage_campaign" "$stage_out/COMPLETE.json" "$stage_evidence/E16_training_inventory_v1.json" > "$stage_evidence/E16_training_inventory_v1.log" 2>&1
