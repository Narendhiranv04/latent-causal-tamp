#!/bin/bash
# Retry 2D queries that hit the 1,800 s administrative cap, with a 7,200 s cap, on one worker (CPU 4), after the main 2D run (pid 54511) exits.
cd /home/naren/Desktop/boltzmann_lfd/final_dataset_generation/FINAL_READINESS_GATE
while kill -0 54511 2>/dev/null; do sleep 30; done
PYTHONDONTWRITEBYTECODE=1 XYFIN2D_WALL=7200 python3 code/xyfin2d.py run work/xy2d_items_retry.json work/xy2d_retry.jsonl 1 4 >> work/xy2d_retry.log 2>&1
