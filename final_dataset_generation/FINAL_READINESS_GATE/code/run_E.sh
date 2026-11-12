#!/bin/bash
# 3D empty-endpoint fresh rerun + replay sample, after run_after2d.sh (pid 64287) has finished; 20 workers CPUs 12-31.
cd /home/naren/Desktop/boltzmann_lfd/final_dataset_generation/FINAL_READINESS_GATE
while kill -0 64287 2>/dev/null; do sleep 30; done
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=disable
[ -e work/STOP3D ] || /home/naren/Desktop/boltzmann_lfd/order_classification_3d/venv313_pinned/bin/python code/rpl3d.py run work/rpl3d_items_E.json work/rpl3d_E.jsonl 20 12 >> work/rpl3d_E.log 2>&1
