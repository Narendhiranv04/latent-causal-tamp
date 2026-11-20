# K<=3 ablation environment on gvlab2 (source with bash).  Every ablation process runs under taskset -c 0-42 (5 CPUs reserved).
export K3=/home/projects/long-horizon/naren_workspace/k3abl ABF_ROOT=/home/projects/long-horizon/naren_workspace/k3abl/abf V3OUT=/home/projects/long-horizon/naren_workspace/k3abl/runs K3_BUNDLE=/home/projects/long-horizon/naren_workspace/k3abl/stage/bundle K3_V34_IDS=/home/projects/long-horizon/naren_workspace/k3abl/meta/V34_ROOT_IDS_METADATA_ONLY.json
export FIN3D_CODE=/home/projects/long-horizon/approachb_final_gen/final3d_v4/code FIN3D_SRC=/home/projects/long-horizon/approachb_final_gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass
export ABF_SNAPSHOT=/home/projects/long-horizon/naren_workspace/k3abl/abf/snapshot/abf_9de85710c2a7103f
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=disable PYTHONDONTWRITEBYTECODE=1
export PYG=/home/projects/long-horizon/abf_v3/envgpu/bin/python PY2D=/home/projects/long-horizon/abf_v2/env2d/bin/python PY3D=/home/projects/long-horizon/abf_v2/env3d/bin/python
export CODE=/home/projects/long-horizon/naren_workspace/k3abl/code/approach_b_final
export K3CPUS=0-42
