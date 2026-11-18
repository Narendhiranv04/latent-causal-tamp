#!/bin/bash
# V3.4 re-target round 1 run: rt_launch.sh BASE DRVDIR PY SRC FDG NAME MAXW CPUS RESERVE
set -e; B=$1; DRV=$2; PY=$3; SRC=$4; FDG=$5; N=$6; W=$7; C=$8; R=$9
O=$B/gen/g3_${RT:-rt1}_$N; mkdir -p $O; cp $B/cohort/${SLOTS:-RT1_SLOTS.txt} $O/ONLY_SLOTS; echo $W > $O/WORKERS
for f in MAX_TEMP_C MIN_FREE_MB; do [ -f $B/gen/g3_rt1_cfg/$f ] && cp $B/gen/g3_rt1_cfg/$f $O/; done
export V34E_FDG=$FDG V34_RESERVE=$R
cd $B
V34_ONLY_SLOTS=$O/ONLY_SLOTS setsid nohup bash $DRV/v34_hosts/gen.sh 3d $B/cohort/${PLAN:-SLOT_PLAN_RT1.json} $O fc34${RT:-rt1}$N $W $C $PY $SRC RAW,REPARK,HARD >/dev/null 2>&1 < /dev/null &
sleep 2
setsid nohup $PY $DRV/v34_orch.py 3d $B/cohort/${PLAN:-SLOT_PLAN_RT1.json} $O fc34${RT:-rt1}$N V34${RT:-rt1}$N $B/enrich/e3_${RT:-rt1}_$N 3 $C $PY $SRC $W > $O/orch.log 2>&1 < /dev/null &
setsid nohup bash $DRV/v34_hosts/share_watch.sh $O $W $R > $O/watch.log 2>&1 < /dev/null &
echo "launched $O"
