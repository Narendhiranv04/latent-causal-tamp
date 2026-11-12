#!/bin/bash
# After the main 2D run (pid 54511) exits: (1) finalized Y at the empty endpoint for every K1-K3 / NONE root without one (18 workers, CPUs 12-29),
# (2) 3D tier D rerun + replay (20 workers, CPUs 12-31).
cd /home/naren/Desktop/boltzmann_lfd/final_dataset_generation/FINAL_READINESS_GATE
while kill -0 54511 2>/dev/null; do sleep 30; done
export PYTHONDONTWRITEBYTECODE=1
[ -e work/STOP ] || python3 code/xyfin2d.py run work/xy2d_items_empty.json work/xy2d_empty.jsonl 18 12 >> work/xy2d_empty.log 2>&1
export MUJOCO_GL=disable
[ -e work/STOP3D ] || /home/naren/Desktop/boltzmann_lfd/order_classification_3d/venv313_pinned/bin/python code/rpl3d.py run work/rpl3d_items_D.json work/rpl3d_D.jsonl 20 12 >> work/rpl3d_D.log 2>&1
