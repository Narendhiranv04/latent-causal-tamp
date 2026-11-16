#!/bin/bash
# V3.2 Phase C TRAIN labelling on gvlab2/cstar (onpolicy.v3_label, unchanged teachers; V2 envs; parity in PARITY_V32.json).  usage: g2_label.sh 2D|3D WORKERS CPU0
D=$1; d=${D,,}; cd $HOME/abf_v32/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v32/label_out V34_DIR=$HOME/abf_v32/v3_2c MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p $V3OUT
nice -n 10 $HOME/abf_v2/env${d:0:1}d/bin/python onpolicy.py v3label $D v32c $2 $3 gvlab2 > $V34_DIR/$d/label_gvlab2.log 2>&1
echo "$(date +%T) G2_LABEL_${D}_DONE" >> $V34_DIR/$d/label_gvlab2.log
