cd /home/naren/Desktop/boltzmann_lfd
export P10C_OUT=runs/p10c P10D_OUT=runs/p10d OMP_NUM_THREADS=1
B=$1; i=1
while [ ! -f runs/p10d/EPISODES_DONE_$B ] && [ $i -le 6 ]; do
  python -c "import p10b_dataset as d; d.job('p10d_episodes_${B}_$i', 'episodes_batch(\"$B\")', 3000.0, module='p10d_execute', category='execution', wall=9000)" 2>&1 | tail -1 | cut -c1-200
  i=$((i+1))
done
echo EPISODES_END_$B
