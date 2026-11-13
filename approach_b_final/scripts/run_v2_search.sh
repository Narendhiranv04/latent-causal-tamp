#!/bin/bash
# V2 step 1: frozen V1 full-arm search on K-stratified TRAIN subsets (2D 1,500 roots, 3D 450 roots), GPU 0 inference, CPU 5.
cd /scratch/nav/approachb_final/code
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ABF_SNAPSHOT=/scratch/nav/approachb_final/snapshot/abf_9de85710c2a7103f
taskset -c 5 ../venv/bin/python onpolicy.py search 2D 1500 0 >> ../logs/v2.log 2>&1
taskset -c 5 ../venv/bin/python onpolicy.py search 3D 450 0 >> ../logs/v2.log 2>&1
for d in 2D 3D; do taskset -c 5 ../venv/bin/python onpolicy.py items $d coverage >> ../logs/v2.log 2>&1; taskset -c 5 ../venv/bin/python onpolicy.py items $d collect >> ../logs/v2.log 2>&1; done
echo V2_SEARCH_DONE >> ../logs/v2.log
