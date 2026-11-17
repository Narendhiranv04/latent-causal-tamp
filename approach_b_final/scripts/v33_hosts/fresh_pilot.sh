#!/bin/bash
# V3.3 fresh-cohort GENERATION throughput pilot (laptop CPU only; frozen generators untouched: a wrapper filters bc.SPECS to family templates absent
# from every existing ledger/snapshot and sets a tiny quota).  Outcomes are never used for any model decision.  usage: fresh_pilot.sh 2d|3d OUT CPUS
set -e; X=$HOME/abf_v33/fresh; OUT=$2; mkdir -p $OUT
export CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=disable PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS=ignore
if [ $1 = 2d ]; then
  L=$HOME/abf_v3_laptop/root/mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/code; cd $L/latent-causal-tamp
  PYTHONPATH=$L/dataset-bd:$L:$L/latent-causal-tamp taskset -c $3 nice -n 10 $HOME/abf_v3_laptop/env2d/bin/python -c 'import sys,json,bd_core as bc,run_2d_plus as R
ex=set(json.load(open(sys.argv[1]))["families"]);n0=len(bc.SPECS);bc.SPECS[:]=[s for s in bc.SPECS if "fam-"+bc.sha(["2d",{k:s[k] for k in bc.FACTORS}])[:10] not in ex]
print("specs",n0,"->",len(bc.SPECS),flush=True)
R.QUOTA.update({"NONE":2,"0":2,"1":2,"2":2,"3":2,"4":0});R.K4_MODE="harvest"
sys.argv=["x","--out",sys.argv[2],"--name","fc2dp","--workers","4"];R.main()' $X/EXCL2D.json $OUT > $OUT/../pilot_2d.log 2>&1
else
  S=$HOME/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass; cd $S/code
  echo 0 > $OUT/K4_MAX_RUNNING; echo '{"NONE":0,"0":2,"1":1,"2":1,"3":1,"4":0}' > $OUT/QUOTA.json
  taskset -c $3 nice -n 10 $HOME/abf_v3_laptop/env3d/bin/python -c 'import sys,json;sys.path.insert(0,"shelf66_v3");import run_shelf66_full as F;bc=F.bc
ex=set(json.load(open(sys.argv[1]))["families"]);n0=len(bc.SPECS);bc.SPECS[:]=[s for s in bc.SPECS if "fam-"+bc.sha(["3ds66",{k:s[k] for k in bc.FACTORS}])[:10] not in ex]
print("specs",n0,"->",len(bc.SPECS),flush=True)
sys.argv=["x","--out",sys.argv[2],"--name","fc3dp","--workers","4"];F.main()' $X/EXCL3D.json $OUT > $OUT/../pilot_3d.log 2>&1
fi
echo "$(date +%T) FRESH_PILOT_$1_DONE" >> $OUT/../pilot_$1.log
