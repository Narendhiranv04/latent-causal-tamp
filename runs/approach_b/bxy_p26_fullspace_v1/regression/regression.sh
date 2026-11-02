set -u
R=${1:?regression dir}
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
rm -f $R/replay_exit.txt $R/pytest_exit.txt
for r in g1_robot g1_hardening g2_interventions g3_repairs g3_5_initial_scene g4a_evidence_audit; do
  python3 run.py replay --run runs/$r --report $R/replay_$r.json > $R/replay_$r.log 2>&1; echo "$r $?" >> $R/replay_exit.txt
done
python3 -m pytest -q -p no:cacheprovider tests > $R/pytest_full.log 2>&1; echo "pytest $?" >> $R/pytest_exit.txt
sed -i "s#$(pwd)/##g" $R/pytest_full.log
python3 -c "import bxy_p16_audit as A, json; A.FROZEN = A.FROZEN + tuple('runs/approach_b/bxy_p%s_v1' % p for p in ('16','17','18','19','20','21','22','23','23_1','24','24_report','25')); print(json.dumps(A.guard()))" > $R/hash_guard.json
