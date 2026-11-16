#!/bin/bash
# V3.2 Phase C pilot mining (laptop RTX 5060; frozen cVAE + frozen V3 D seed 0; TRAIN roots only); 2 CPUs.
cd /home/naren/Desktop/boltzmann_lfd/.claude/worktrees/approach-b-v3-2-training/approach_b_final
export ABF_ROOT=$HOME/abf_v3_2_audit/root V3OUT=$HOME/abf_v3_2_audit/runs V34_DIR=$HOME/abf_v32/v3_2c V3_TASK_STAGE=v3_3 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2
P="taskset -c 30,31 nice -n 5 $HOME/miniconda3/envs/rkit-rpx-sm120/bin/python"
$P v32c.py mine 3d 6 6 6 3 3 && $P v32c.py items 3d
$P v32c.py mine 2d 8 8 8 4 4 && $P v32c.py items 2d
echo MINE_PILOT_DONE
