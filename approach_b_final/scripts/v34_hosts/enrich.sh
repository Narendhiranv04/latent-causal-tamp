#!/bin/bash
# V3.4 dependence enrichment (scripts/v34_enrich.py) on one host.  usage: enrich.sh 2d|3d CPUSET order|repark|hard [wrapper args, ABSOLUTE paths]
#   e.g. enrich.sh 2d 28-31 order --store /abs/store --jobs /abs/jobs.json --out /abs/out --workers 4
set -e; D=$1; CPUS=$2; ST=$3; shift 3; W=$(realpath $(dirname $0)/../v34_enrich.py)
export CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=disable PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS=ignore
if [ $D = 2d ]; then C=${CODE2D:-/home/naren/abf_v34/src2d/code}; PY=${PY2D:-/home/naren/abf_v3_laptop/env2d/bin/python}
  cd $C/latent-causal-tamp; export PYTHONPATH=$C/dataset-bd:$C:$C/latent-causal-tamp
else C=${CODE3D:-/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass/code}
  PY=${PY3D:-/home/naren/abf_v3_laptop/env3d/bin/python}; cd $C; fi
exec taskset -c $CPUS nice -n ${NICE:-10} $PY $W $ST $D --code $C "$@"
