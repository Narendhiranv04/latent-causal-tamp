#!/bin/bash
# Every 60 s: WORKERS(GEN_OUT) = min(MAX, NCPU - RESERVE - ceil(CPU% of every process OUTSIDE this driver's own process tree / 100)).
# Other V3.4 drivers / enrichment / DISCO / other users all count as load, so several drivers on one host converge to <= NCPU - RESERVE.
# Only writes our own control file.  usage: [PSCMD="flatpak-spawn --host ps"] share_watch.sh GEN_OUT MAX [RESERVE=4]
n=$(getconf _NPROCESSORS_ONLN); R=${3:-4}; G=$(realpath $1)
while [ ! -f $G/DONE ]; do
  o=$(${PSCMD:-ps} -eo pid=,ppid=,pcpu=,args= | awk -v g="$G" '
      {par[$1]=$2; c[$1]=$3; ids[NR]=$1; mine[$1]=(index($0, "v34_gen.py") && index($0, g" "))}
      END { for (k=0;k<5;k++) for (i=1;i<=NR;i++) if (mine[par[ids[i]]]) mine[ids[i]]=1;
            for (i=1;i<=NR;i++) if (!mine[ids[i]]) s+=c[ids[i]]; printf "%d", (s+99)/100 }')
  w=$(( n - R - o )); [ $w -gt $2 ] && w=$2; [ $w -lt 0 ] && w=0
  echo $w > $G/WORKERS
  echo "$(date -u +%FT%TZ) other_cores=$o load=$(cut -d' ' -f1 /proc/loadavg) workers=$w" >> $G/RESOURCE.log
  sleep 60
done
