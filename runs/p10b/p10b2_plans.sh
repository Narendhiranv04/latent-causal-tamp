cd /home/naren/Desktop/boltzmann_lfd
for b in 2 3 4 5; do
  [ -f runs/p10b/batch$b/plan.json ] || OMP_NUM_THREADS=1 python -c "
import p10b_dataset as d, p10b_prereg as p
specs=[s for s in p.roster() if s['batch']==$b]
d.job('p10b2_plan_batch$b', 'build_plan(\"runs/p10b/batch$b\", %r)' % specs, 2500.0, category='constructor_dev')" 2>&1 | tail -1 | cut -c1-120
done
echo PLANS_END
