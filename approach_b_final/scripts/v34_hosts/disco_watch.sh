#!/bin/bash
# girish only: every 60 s set Approach B generation WORKERS = min(MAX, 24 - 4 reserved - ceil(DISCO cpu%/100) - 2 headroom); log to RESOURCE.log.
# Never touches DISCO; only writes our own control file.  usage: disco_watch.sh GEN_OUT MAX
while [ ! -f $1/DONE ]; do
  d=$(ps -eo pcpu,args | grep "[d]isco_grid" | awk '{s+=$1}END{printf "%d", (s+99)/100}')
  g=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | wc -l)
  w=$(( 24 - 4 - d - 2 )); [ $w -gt $2 ] && w=$2; [ $w -lt 0 ] && w=0
  echo $w > $1/WORKERS
  echo "$(date -u +%FT%TZ) disco_cores=$d gpu_procs=$g load=$(cut -d' ' -f1 /proc/loadavg) workers=$w" >> $1/RESOURCE.log
  sleep 60
done
