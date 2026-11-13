#!/bin/bash
# V2 step 2: coverage diagnostic labels first (2D, 3D), then the stratified collection (2D, 3D); CPU-yielding supervisor.
cd /scratch/nav/approachb_final/code
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ABF_SNAPSHOT=/scratch/nav/approachb_final/snapshot/abf_9de85710c2a7103f
true
../venv/bin/python onpolicy.py supervise 2D:coverage 3D:coverage >> ../logs/v2.log 2>&1
for d in 2D 3D; do ../venv/bin/python onpolicy.py coverage $d >> ../logs/v2.log 2>&1; done
echo V2_COVERAGE_DONE >> ../logs/v2.log
../venv/bin/python onpolicy.py supervise 2D:collect 3D:collect >> ../logs/v2.log 2>&1
echo V2_COLLECT_DONE >> ../logs/v2.log
