#!/bin/bash
# shared host: every 60 s WORKERS = min(MAX, NCPU - RESERVE - ceil(CPU% of every process outside OUR v34_gen.py process trees / 100)).
# Works when other jobs share our uid (gvlab2).  Only writes our own control file.  usage: [PSCMD="flatpak-spawn --host ps"] share_watch.sh GEN_OUT MAX [RESERVE=4]
n=$(nproc); R=${3:-4}
while [ ! -f $1/DONE ]; do
  o=$(${PSCMD:-ps} -eo pid=,ppid=,pcpu=,args= | awk '
      {pid[NR]=$1; pp[NR]=$2; cpu[NR]=$3; mine[$1]=($0 ~ /v34_gen\.py/); par[$1]=$2; c[$1]=$3; ids[NR]=$1}
      END { for (k=0;k<4;k++) for (i=1;i<=NR;i++) if (mine[par[ids[i]]]) mine[ids[i]]=1;
            for (i=1;i<=NR;i++) if (!mine[ids[i]]) s+=c[ids[i]]; printf "%d", (s+99)/100 }')
  w=$(( n - R - o )); [ $w -gt $2 ] && w=$2; [ $w -lt 0 ] && w=0
  echo $w > $1/WORKERS
  echo "$(date -u +%FT%TZ) other_cores=$o load=$(cut -d' ' -f1 /proc/loadavg) workers=$w" >> $1/RESOURCE.log
  sleep 60
done
