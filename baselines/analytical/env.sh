# Source before running (laptop layout; override L / AB_OUT on other hosts).  Physics: python3 (2D), MuJoCo-3.16 python (3D).
L=${L:-$HOME/abf_v3_laptop}
export ABF_ROOT=$L/root FIN3D_CODE=$L/gen/final3d_v4/code FIN3D_SRC=$L/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass
export AB_OUT=${AB_OUT:-$HOME/analytical_baselines} MUJOCO_GL=disable CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export DISCO_ROOT=$AB_OUT/disco_root
export PY2D=${PY2D:-python3} PY3D=${PY3D:-$L/env3d/bin/python}
