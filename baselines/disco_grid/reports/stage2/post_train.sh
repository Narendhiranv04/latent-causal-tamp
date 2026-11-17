#!/bin/sh
# Serial post-TRAIN gates. This script NEVER executes VAL or TEST physics.
set -eu
stage_source=$1
stage_campaign=$2
stage_engine=$3
stage_commit=$4
stage_python=/scratch/nav/disco_grid/venv/bin/python
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export DISCO_SOURCE_COMMIT="$stage_commit"
while [ ! -f "$stage_campaign/continuation_001/COMPLETE.json" ]; do sleep 30; done
stage_out="$stage_campaign/posttrain_v1"
mkdir "$stage_out"
cd "$stage_source"
timeout --kill-after=5s 240s "$stage_python" -m pytest baselines/disco_grid/tests/test_d0_audit.py baselines/disco_grid/tests/test_d2_policy.py baselines/disco_grid/tests/test_d3_d4_mcts_distill.py baselines/disco_grid/tests/test_d6_d7_evaluate.py baselines/disco_grid/tests/test_validation_v2.py baselines/disco_grid/tests/test_stage2.py baselines/disco_grid/tests/test_physical_eval.py -q > "$stage_out/tests.log" 2>&1
"$stage_python" baselines/disco_grid/reports/stage2/recover_prefixes.py --engine "$stage_engine" --campaign "$stage_campaign" --out "$stage_campaign/certified_prefixes" > "$stage_out/prefix_recovery.log" 2>&1
"$stage_python" baselines/disco_grid/reports/stage2/fit_known_prefixes.py --engine "$stage_engine" --campaign "$stage_campaign" --recovered "$stage_campaign/certified_prefixes" --controller-commit "$stage_commit" > "$stage_out/prefix_fit.log" 2>&1
"$stage_python" baselines/disco_grid/reports/stage2/prepare_evaluation.py --campaign "$stage_campaign" --cohorts "$stage_source/baselines/disco_grid/reports/stage2/cohorts.json" --out "$stage_campaign/evaluation_preparation_v1" > "$stage_out/evaluation_preparation.log" 2>&1
"$stage_python" baselines/disco_grid/reports/stage2/summarize_campaign.py "$stage_campaign" "$stage_out" > "$stage_out/coverage.log" 2>&1
"$stage_python" baselines/disco_grid/reports/stage2/scene_evidence.py --states /scratch/nav/disco_grid/stage2/verification/train_parity_d1ccb34/case_2/query_000003_parent.pkl --out "$stage_out/native_3d" > "$stage_out/native_3d.log" 2>&1
"$stage_python" baselines/disco_grid/reports/stage2/scene_evidence.py --states /scratch/nav/disco_grid/stage2/verification/train_parity_d1ccb34/case_0/query_000003_parent.pkl --out "$stage_out/native_2d" > "$stage_out/native_2d.log" 2>&1
printf '%s\n' '{"status":"PREPARED","VAL_TEST_physics":"NOT_AUTHORIZED_NOT_EXECUTED"}' > "$stage_out/COMPLETE.json"
