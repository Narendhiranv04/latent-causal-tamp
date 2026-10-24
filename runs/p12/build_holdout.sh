cd /home/naren/Desktop/boltzmann_lfd
export OMP_NUM_THREADS=1 P10C_OUT=runs/p10c P10D_OUT=runs/p10d
python -c "import p12_closure as p; p.job('p12_2_build', 'build_batches(80)', 2900.0, category='teacher', wall=8000)" 2>&1 | tail -1 | cut -c1-200
echo BUILD_END
