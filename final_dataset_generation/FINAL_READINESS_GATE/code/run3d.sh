#!/bin/bash
# 3D replay audit: tiers A (mandatory) + B (stratified sample), then tier C (every remaining witness-backed label); 7 workers, CPUs 5-11.
cd /home/naren/Desktop/boltzmann_lfd/final_dataset_generation/FINAL_READINESS_GATE
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=disable
PY=/home/naren/Desktop/boltzmann_lfd/order_classification_3d/venv313_pinned/bin/python
$PY code/rpl3d.py run work/rpl3d_items.json work/rpl3d_AB.jsonl 7 5 >> work/rpl3d_AB.log 2>&1
[ -e work/STOP3D ] || $PY code/rpl3d.py run work/rpl3d_items_C.json work/rpl3d_C.jsonl 7 5 >> work/rpl3d_C.log 2>&1
