#!/bin/bash
# V3.2 Phase C full TRAIN mining on Blackwell (frozen cVAE + frozen V3 D s0; GPU 0); one pinned CPU per shard, nice 10, own output dir per shard.
# usage: bw_mine.sh DOM "N1 N2 N3 N0 NNONE" PART CPU
cd $HOME/abf_v32/code
p=${3/\//of}
export ABF_ROOT=$HOME/abf_v32/root V3OUT=$HOME/abf_v32/runs V34_DIR=$HOME/abf_v32/v3_2c_shard_$p V3_TASK_STAGE=v3_3 CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
taskset -c $4 nice -n 10 $HOME/approachb_3d_learning/venv/bin/python v32c.py mine $1 $2 $3 > $V34_DIR.$1.log 2>&1
echo "$(date +%T) BW_MINE_${1}_${p}_DONE" >> $V34_DIR.$1.log
