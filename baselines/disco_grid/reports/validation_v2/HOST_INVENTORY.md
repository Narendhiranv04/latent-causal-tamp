# Four-host inventory

Measured 16 November 2026 (UTC timestamps in host_inventory.json); point-in-time
facts, not reservations. Existing key access worked for all four hosts. Shared
ownership; no exclusive machine allocation inferred. No credentials recorded.

| Alias → actual hostname | CPU physical/logical | RAM total/available MiB | GPU measured | Role / DISCO permission |
|---|---|---|---|---|
| gvlab → gvlab | Xeon Gold 5317, 12/24 | 63908/~41381 | 2×RTX4090, 24564 MiB each; ~23276/17214 MiB used | Only authorized execution host; busy GPU0 and GPU1, 16 live Approach B workers, load ~20 |
| gvlab2 → cstar | Threadripper7960X, 24/48 | 128298/~110787 | RTX5090, 32607 MiB, ~8 used | Inventory only; no DISCO jobs |
| blackwell → server | Ultra9 285K, 24/24 topology reported | 128268/~123886 | RTX PRO5000 Blackwell, 48935 MiB, ~2 used | Inventory only; shared users/tmux; no DISCO jobs |
| girish-laptop (SSH alias girish) → gvcstar | i9-12900HX, 16 cores/24 threads | 31759/~27684 | RTX3080Ti Laptop, 16384 MiB, ~15 used | Inventory only; distinct from local editing laptop |

Drivers respectively 560.35.05 / 580.95.05 / 595.99.02 / 580.178.04;
CUDA driver maxima 12.6 / 13.0 / 13.2 / 13.0 (not runtime library versions).
gvlab isolated Python `/scratch/nav/disco_grid/venv/bin/python`;
Python/Torch/MuJoCo versions verified separately in runtime artifact logs.
Other hosts' Python package versions UNKNOWN (no environment selected).
gvlab `/scratch` 200 GiB available at first inventory, root 42 GiB;
blackwell `/data` 2.5 TiB available, not assumed shared. gvlab2 root 39 GiB,
girish root 115 GiB. Full mounts and process/tmux observations in JSON.

Caps this session: GPU usage 0, lightweight test thread 1 at nice +10,
physical collection workers 0 until resource gate clears; absolute initial pilot
worker ceiling 1–2 after remeasurement. No jobs, transfers or installs on the
other hosts. Relevant gvlab paths exist and DISCO path writable. Dataset/checkpoint
hashes are measured separately; datasets on other hosts UNVERIFIED.
