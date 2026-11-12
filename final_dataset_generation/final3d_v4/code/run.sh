#!/bin/bash
# run.sh MODE ITEMS OUT WORKERS CPUS  -- one fin3d pass on the laptop with the pinned 3D venv (MuJoCo 3.16.0, numpy 2.2.6)
cd /home/naren/Desktop/boltzmann_lfd/final_dataset_generation/final3d_v4/work
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MUJOCO_GL=disable FIN3D_CPUS=$5
nice -n ${NICE:-5} /home/naren/Desktop/boltzmann_lfd/order_classification_3d/venv313_pinned/bin/python ../code/fin3d.py $1 $2 $3 $4 >> ${3%.jsonl}.log 2>&1
echo "DONE $(date -u +%FT%TZ)" >> ${3%.jsonl}.log
