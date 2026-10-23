#!/bin/sh
# usage: collect_batch.sh <batch dir> <tag>; one teacher worker; resumable chunks charged to 'teacher'
cd /home/naren/Desktop/boltzmann_lfd
B=$1; T=$2
[ -f $B/static_admission.json ] || OMP_NUM_THREADS=1 python -c "import p10b_dataset as d; d.job('${T}_admit', 'admit(\"$B\")', 1500.0, category='teacher')" 2>&1 | tail -1
i=1
while [ ! -f $B/COLLECTED ] && [ $i -le 20 ]; do
  OMP_NUM_THREADS=1 python -c "import p10b_dataset as d; d.job('${T}_collect$i', 'collect(\"$B\")', 2900.0, category='teacher', wall=7000)" 2>&1 | tail -1 | cut -c1-200
  python -c "import p10b_dataset as d, sys; sys.exit(0 if d.CAPS['teacher'] - d.spent('teacher')[0] > 400 else 1)" || { echo BUDGET_STOP; break; }
  i=$((i+1))
done
echo BATCH_END
