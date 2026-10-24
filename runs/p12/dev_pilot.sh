cd /home/naren/Desktop/boltzmann_lfd
export OMP_NUM_THREADS=1
for i in 1 2; do
  [ -f runs/p12/dev/COLLECTED ] && break
  python -c "import p12_closure as p; p.job('p12_1_dev_pilot$i', 'dev_pilot(8)', 2900.0, module='p12_families', category='dev', wall=8000)" 2>&1 | tail -1 | cut -c1-200
done
echo DEV_END
