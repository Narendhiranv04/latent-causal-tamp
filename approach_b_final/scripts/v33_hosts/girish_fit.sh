#!/bin/bash
# V3.3 scratch TaskCVAE fits on girish GPU (registered budget).  usage: girish_fit.sh "DOMS" "ARMS" "SEEDS"
cd $HOME/abf_v33/code
declare -A SNAP=([control]=abf_v3_e8a496bc66266fca [expanded]=abf_v32_fb0eef4f5ff433ee) STEPS=([2d]=2400 [3d]=1520) EV=([2d]=30 [3d]=19)
for d in $1; do for a in $2; do for s in $3; do
  ABF_ROOT=$HOME/abf_v31/root V3OUT=$HOME/abf_v33/runs V3_TASK_STAGE=v33/$a ABF_DEVICE=cuda CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 \
  V33_TRAIN_SNAP=$HOME/abf_v33/snap/${SNAP[$a]} V33_VAL_SNAP=$HOME/abf_v33/snap/abf_9de85710c2a7103f V33_STEPS=${STEPS[$d]} V33_EVAL_EVERY=${EV[$d]} \
  nice -n 10 $HOME/abf_v31/env/bin/python placement.py fit_task $d scratch_all $s >> $HOME/abf_v33/logs/fit.log 2>&1
done; done; done
echo "$(date +%T) FIT_DONE $1 $2 $3" >> $HOME/abf_v33/logs/fit.log
