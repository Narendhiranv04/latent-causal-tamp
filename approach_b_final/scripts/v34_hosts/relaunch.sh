#!/bin/bash
# Graceful driver restart with the CURRENT driver code (same OUT / name -> same ledger, attempt counts and ids continue):
# STOP -> wait for DONE (running jobs finish and are recorded) -> clear -> restart watchdog + driver.  Env vars (V34_*) are passed through.
# usage: relaunch.sh OUT WATCH_MAX WATCH_RESERVE -- <gen.sh args...>
OUT=$(realpath $1); WM=$2; WR=$3; shift 4; H=$(dirname $(realpath $0))
touch $OUT/STOP
until [ -f $OUT/DONE ]; do sleep 20; done
sleep 70; rm -f $OUT/STOP $OUT/DONE
(setsid nohup bash $H/share_watch.sh $OUT $WM $WR >/dev/null 2>&1 </dev/null &)
setsid nohup bash $H/gen.sh "$@" >/dev/null 2>&1 </dev/null &
echo "$(date -u +%FT%TZ) relaunched with current driver code" >> $OUT/RESOURCE.log
