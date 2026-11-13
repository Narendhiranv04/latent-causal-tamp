#!/bin/bash
# When V1 is fully done, give V2 labelling 18 workers (CPUs 6-23).
while ! grep -q ALL_P5_DONE /scratch/nav/approachb_final/logs/p5.log; do sleep 60; done
echo "{\"workers\": 18, \"lo\": 6}" > /scratch/nav/approachb_final/runs/v2/ALLOC
