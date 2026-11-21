# Post-ablation validation (k3val).  Reads k3abl artifacts READ-ONLY; writes only under k3val.  taskset 0-42 (5 CPUs reserved).
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh
export K3A=/home/projects/long-horizon/naren_workspace/k3abl K3V=/home/projects/long-horizon/naren_workspace/k3val
export CODE=$K3V/code/approach_b_final
