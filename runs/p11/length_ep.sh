cd /home/naren/Desktop/boltzmann_lfd
export P10C_OUT=runs/p10c P10D_OUT=runs/p10d OMP_NUM_THREADS=1
B=$1
python -c "import p11_closure as p; p.job('p11_3_episodes_$B', 'length_episodes(\"$B\")', 1500.0, category='short_episodes', wall=9000)" 2>&1 | tail -1 | cut -c1-160
echo END_$B
