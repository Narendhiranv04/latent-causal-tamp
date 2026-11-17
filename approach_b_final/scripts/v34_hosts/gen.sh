#!/bin/bash
# V3.4 RAW generation on one host.  usage: gen.sh 2d|3d SLOTS OUT NAME MAXW CPUSET PY SRC_ROOT [KINDS]
#   SRC_ROOT: 2d = .../planar_2d/dataset_bd_classquota/code ; 3d = .../dataset_bd_classquota_without_home_position_no_overpass/code
set -e; D=$1; SL=$(realpath $2); OUT=$3; mkdir -p $OUT; OUT=$(realpath $OUT); DRV=$(realpath $(dirname $0)/../v34_gen.py)
export CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=disable PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS=ignore
if [ $D = 2d ]; then cd $8/latent-causal-tamp; export PYTHONPATH=$8/dataset-bd:$8:$8/latent-causal-tamp; else cd $8; fi
exec taskset -c $6 nice -n 10 $7 $DRV $D $SL $OUT $4 $5 $9 >> $OUT/driver.log 2>&1
