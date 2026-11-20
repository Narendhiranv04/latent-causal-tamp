#!/bin/bash
# P6 relaunch after a GPU OOM caused by another user's added GPU jobs: <=10 concurrent GPU processes, resumable passes until all 60 TEST
# prediction files are complete (max 4 passes), then seal -> TEST lock -> union teach -> evaluate (p5.sh test).  Arms / weights / rules unchanged.
cd /home/projects/long-horizon/naren_workspace/k3abl
for pass in 1 2 3 4; do
  [ "$(bash complete.sh test)" -ge 60 ] && break
  PAR=10 bash predict_all2.sh test >> runs/logs/predict_test.log 2>&1
done
[ "$(bash complete.sh test)" -ge 60 ] || { echo "TEST predictions incomplete after 4 passes"; exit 1; }
bash p5.sh test > runs/logs/p5_test.log 2>&1
