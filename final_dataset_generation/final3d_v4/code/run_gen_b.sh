#!/bin/bash
# published SHELF66V3 generator (run_shelf66_full.py, unmodified), laptop, K3 requests only (QUOTA.json: K3 577 = 517 published + 60, others 0),
# K4 off (K4_MAX_RUNNING 0), namespace lap5 (second instance, own out dir), isolated out dir (ledger seeded with the published ledger for the request planner's yields)
SRC=/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass
OUT=/home/naren/Desktop/boltzmann_lfd/final_dataset_generation/final3d_v4/gen_k3b/raw
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONWARNINGS=ignore MUJOCO_GL=disable PYTHONDONTWRITEBYTECODE=1
cd $SRC/code
nice -n 5 /home/naren/Desktop/boltzmann_lfd/order_classification_3d/venv313_pinned/bin/python shelf66_v3/run_shelf66_full.py --out $OUT --name lap5 --workers 13 >> $OUT/../gen.log 2>&1
echo "DONE $(date -u +%FT%TZ)" >> $OUT/../gen.log
