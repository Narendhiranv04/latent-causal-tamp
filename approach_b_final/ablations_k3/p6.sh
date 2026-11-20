#!/bin/bash
# P6: historical TEST, opened only after the VAL protocol lock + P5 review.  Same arms / weights / rules; predictions (<=16 GPU processes),
# then seal -> TEST lock -> union teach -> evaluate -> tables (p5.sh test).  Never re-tuned.
cd /home/projects/long-horizon/naren_workspace/k3abl
grep -q P5_DONE_val runs/logs/p5_val.log && [ -f runs/manifests/FINAL_ABLATION_PROTOCOL_LOCK_val.json ] || { echo "VAL not frozen"; exit 1; }
PAR=16 bash predict_all2.sh test > runs/logs/predict_test.log 2>&1
until [ "$(bash complete.sh test)" -ge 60 ]; do sleep 30; done
bash p5.sh test > runs/logs/p5_test.log 2>&1
