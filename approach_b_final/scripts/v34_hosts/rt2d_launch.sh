#!/bin/bash
# V3.4 2D fix run (re-target round 1 + GEOM_V1 fingerprint guard): rt2d_launch.sh BASE DRVDIR PY SRC2D FDG NAME MAXW CPUS RESERVE SLOTS_FILE ORCH(0/1)
set -e; B=$1; DRV=$2; PY=$3; SRC=$4; FDG=$5; N=$6; W=$7; C=$8; R=$9; SL=${10}; ORCH=${11}
export CODE2D=$SRC PY2D=$PY   # orchestrator enrichment paths (fix 2026-11-18)
O=$B/gen/g2_rt1_$N; mkdir -p $O; cp $B/cohort/$SL $O/ONLY_SLOTS; echo $W > $O/WORKERS
for f in MAX_TEMP_C MIN_FREE_MB; do [ -f $B/gen/g3_rt1_cfg/$f ] && cp $B/gen/g3_rt1_cfg/$f $O/; done
export V34E_FDG=$FDG V34_RESERVE=$R V34_FP_EXCL=$B/cohort/FPX_2D.txt
cd $B
V34_ONLY_SLOTS=$O/ONLY_SLOTS setsid nohup bash $DRV/v34_hosts/gen.sh 2d $B/cohort/SLOT_PLAN_RT1b.json $O fc34rt1$N $W $C $PY $SRC RAW,REPARK,HARD >/dev/null 2>&1 < /dev/null &
sleep 2
[ "$ORCH" = 1 ] && setsid nohup $PY $DRV/v34_orch.py 2d $B/cohort/SLOT_PLAN_RT1b.json $O fc34rt1$N V34RT1$N $B/enrich/e2_rt1_$N 4 $C $PY $SRC $W > $O/orch.log 2>&1 < /dev/null &
setsid nohup bash $DRV/v34_hosts/share_watch.sh $O $W $R > $O/watch.log 2>&1 < /dev/null &
echo "launched $O"
