#!/bin/bash
# V3.2 Phase C TRAIN labelling on girish-laptop (onpolicy.v3_label; exact laptop teacher env copies, parity PASS; nice 10).  usage: girish_label.sh 2D|3D TAG WORKERS CPU0
D=$1; d=${D,,}; H=$HOME/abf_v314v; cd $HOME/abf_v32_C/code
export ABF_ROOT=$H/root V3OUT=$HOME/abf_v32_C/label_out V34_DIR=$HOME/abf_v32_C FIN3D_CODE=$H/gen/final3d_v4/code FIN3D_SRC=$H/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p $V3OUT $V3OUT/teacher2d_witnesses; ln -sfn $H/runs/store $V3OUT/store
nice -n 10 $H/env${d:0:1}d/bin/python onpolicy.py v3label $D $2 $3 $4 girish > $V34_DIR/$d/label_$2_girish.log 2>&1
echo "$(date +%T) GIRISH_LABEL_${D}_DONE" >> $V34_DIR/$d/label_$2_girish.log
