#!/bin/bash
# stop exactly our P6 prediction tree (own uid only): p6.sh, predict_all2.sh, its xargs, and run.py predict ... test workers
U=$(id -u)
B=$(ps -u $U -o pid,args | awk '($2=="bash" && ($3=="p6.sh" || ($3=="predict_all2.sh" && $4=="test"))) {print $1}')
X=$(ps -u $U -o pid,args | awk '$2=="xargs" {print $1}')
Y=$(ps -u $U -o pid,args | awk '$2 ~ /python/ && $3=="run.py" && $4=="predict" && $7=="test" {print $1}')
echo "bash: $B xargs: $X python: $(echo $Y | wc -w)"
kill $B $X 2>/dev/null; kill $Y 2>/dev/null; sleep 3
ps -u $U -o args | awk '$1 ~ /python/' | grep -c "run.py predict"
