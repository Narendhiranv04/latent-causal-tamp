#!/bin/bash
# R8B relay (laptop): copy generation ledgers + roots of genL (laptop) and genW (Blackwell) to gvlab2 every 3 min.  Read-only on sources.
R=/home/projects/long-horizon/naren_workspace/fig3/final/r8b
while [ ! -f /home/naren/r8b/RELAY_STOP ]; do
  tar c -C /home/naren/r8b genL/ledger.jsonl genL/roots 2>/dev/null | ssh -o BatchMode=yes gvlab2.iiit.ac.in "tar x -C $R"
  ssh -o BatchMode=yes user1@10.4.25.63 "tar c -C ~/legolas_r8b genW/ledger.jsonl genW/roots 2>/dev/null" | ssh -o BatchMode=yes gvlab2.iiit.ac.in "tar x -C $R"
  ssh -o BatchMode=yes gvlab "tar c -C ~/r8b genG/ledger.jsonl genG/roots 2>/dev/null" | ssh -o BatchMode=yes gvlab2.iiit.ac.in "tar x -C $R"
  echo "$(date -u +%FT%TZ) relayed" >> /home/naren/r8b/relay.log
  sleep 180
done
