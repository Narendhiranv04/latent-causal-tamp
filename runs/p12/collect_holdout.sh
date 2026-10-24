cd /home/naren/Desktop/boltzmann_lfd
export OMP_NUM_THREADS=1
for b in 1 2 3 4; do
  B=runs/p12/holdout/batch$b
  [ -f $B/static_admission.json ] || python -c "import p10b_dataset as d, p12_families; import p12_closure as p; p.job('p12_3_admit_b$b', 'admit(\"$B\")', 1500.0, module='p10b_dataset', category='teacher')" 2>&1 | tail -1 | cut -c1-160
  i=1
  while [ ! -f $B/COLLECTED ] && [ $i -le 8 ]; do
    python -c "import p12_closure as p; p.job('p12_3_collect_b${b}_$i', 'collect(\"$B\", 2600.0)', 2900.0, module='p10b_dataset', category='teacher', wall=8000)" 2>&1 | tail -1 | cut -c1-160
    python -c "import p12_closure as p, sys; sys.exit(0 if p.CAPS['teacher']-p.spent('teacher')[0] > 1000 else 1)" || { echo BUDGET_STOP; break 2; }
    i=$((i+1))
  done
done
echo COLLECT_END
