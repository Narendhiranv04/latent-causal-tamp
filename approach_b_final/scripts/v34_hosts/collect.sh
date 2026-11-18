#!/bin/bash
# V3.4 collection: gen/ + enrich/ from every host -> ~/abf_v34/collect/<host>/ (incremental; read-only on remotes)
C=$HOME/abf_v34/collect; mkdir -p $C
R="rsync -a --exclude viz/"
mkdir -p $C/laptop; $R $HOME/abf_v34/gen $HOME/abf_v34/enrich $C/laptop/ && echo laptop ok
for spec in gvlab:abf_v34 girish:/home/longhorizon/abf_v34 gvlab2.iiit.ac.in:/home/projects/long-horizon/abf_v34 enigma:/scratch2/ennovatex.Rath/naren-m4m dinesh:naren-m4m; do
  h=${spec%%:*}; p=${spec#*:}; n=${h%%.*}; mkdir -p $C/$n
  $R -e "ssh -o BatchMode=yes" $h:$p/gen $h:$p/enrich $C/$n/ && echo "$n ok" || echo "$n FAIL"
done
du -sh $C
