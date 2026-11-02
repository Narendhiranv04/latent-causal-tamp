set -u
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
for r in g1_robot g1_hardening g2_interventions g3_repairs g3_5_initial_scene g4a_evidence_audit; do
  python3 run.py replay --run runs/$r --report runs/approach_b/bxy_p25_v1/regression/replay_$r.json > runs/approach_b/bxy_p25_v1/regression/replay_$r.log 2>&1; echo "$r $?" >> runs/approach_b/bxy_p25_v1/regression/replay_exit.txt
done
python3 -m pytest -q tests > runs/approach_b/bxy_p25_v1/regression/pytest_full.log 2>&1; echo "pytest $?" >> runs/approach_b/bxy_p25_v1/regression/pytest_exit.txt
python3 -c "import bxy_p16_audit as A, json; A.FROZEN = A.FROZEN + tuple('runs/approach_b/bxy_p%s_v1' % p for p in ('16','17','18','19','20','21','22','23','23_1','24','24_report')); print(json.dumps(A.guard()))" > runs/approach_b/bxy_p25_v1/regression/hash_guard.json
