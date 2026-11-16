#!/bin/bash
# V3.2 Phase C TRAIN labelling on gvlab (onpolicy.v3_label, unchanged teachers; parity PASS in PARITY_V32.json; nice 10).  usage: g_label.sh 2D|3D TAG WORKERS CPU0
D=$1; d=${D,,}; cd /scratch/nav/abf_v32/code
export ABF_ROOT=/scratch/nav/approachb_final V3OUT=/scratch/nav/abf_v32/label_out V34_DIR=/scratch/nav/abf_v32/v3_2c_full MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
E=$HOME/approachb3d_v3/2d_q2_spillover/venv313/bin/python; [ $d = 3d ] && E=$HOME/approachb3d_mock/env/bin/python
mkdir -p $V3OUT
nice -n 10 $E onpolicy.py v3label $D $2 $3 $4 gvlab > $V34_DIR/$d/label_$2_gvlab.log 2>&1
echo "$(date +%T) G_LABEL_${D}_DONE" >> $V34_DIR/$d/label_$2_gvlab.log
