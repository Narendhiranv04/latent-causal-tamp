cd /home/naren/Desktop/boltzmann_lfd
export OMP_NUM_THREADS=1
B=$1; i=1
while [ ! -f runs/p12/p12_5/DONE_$B ] && [ $i -le 4 ]; do
  python -c "import p12_closure as p; p.job('p12_5_exec_${B}_$i', 'exec_batch(\"$B\")', 2900.0, category='execution', wall=9000)" 2>&1 | tail -1 | cut -c1-160
  i=$((i+1))
done
echo EXEC_END_$B
