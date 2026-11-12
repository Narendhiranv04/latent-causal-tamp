#!/bin/bash
# hard3d on the laptop: the 47 locally generated K3 layouts (read-only ds_view = published roots + generated roots, pins_v4_all), 27 workers
V4=/home/naren/Desktop/boltzmann_lfd/final_dataset_generation/final3d_v4
cd $V4/code
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MUJOCO_GL=disable
export DEP3D_PINS=pins_v4_all.json HK_SOURCE_COMMIT=fb1120a30ab1be2ede6e0e4c585a93f0aacdb907+GEN_V4_LOCAL HK_MAXC=14 HK_CPU_CAP=6000 HK_TEMPS=96,92,99
nice -n 5 /home/naren/Desktop/boltzmann_lfd/order_classification_3d/venv313_pinned/bin/python hard3d.py LAP4 $V4/ds_view $V4/hard $V4/work/$1 27 0-26 >> $V4/hard/run.log 2>&1
echo "DONE $(date -u +%FT%TZ) $1" >> $V4/hard/run.log
