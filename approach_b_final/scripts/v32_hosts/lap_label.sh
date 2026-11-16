#!/bin/bash
# V3.2 Phase C TRAIN labelling on the laptop (onpolicy.v3_label = unchanged teachers; laptop envs parity PASS in PARITY_V32.json).
# usage: lap_label.sh 2D|3D WORKERS CPU0
D=$1; TAG=${TAG:-v32c}; L=$HOME/abf_v3_laptop; cd /home/naren/Desktop/boltzmann_lfd/.claude/worktrees/approach-b-v3-2-training/approach_b_final
export ABF_ROOT=$L/root V3OUT=$HOME/abf_v32/label_out V34_DIR=${V34:-$HOME/abf_v32/v3_2c} FIN3D_CODE=$L/gen/final3d_v4/code FIN3D_SRC=$L/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
d=${D,,}; mkdir -p $V3OUT
nice -n 10 $L/env${d:0:1}d/bin/python onpolicy.py v3label $D $TAG $2 $3 laptop > $V34_DIR/$d/label_${TAG}_laptop.log 2>&1
echo "$(date +%T) LAP_LABEL_${D}_DONE" >> $V34_DIR/$d/label_${TAG}_laptop.log
