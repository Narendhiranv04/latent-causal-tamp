cd /home/naren/Desktop/boltzmann_lfd
for b in 2 3 4 5; do sh runs/p10b/collect_batch.sh runs/p10b/batch$b p10b2_b$b; done
echo P10B2_END
