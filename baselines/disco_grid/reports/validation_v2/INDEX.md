# DISCO-Grid validation evidence

Start with [FINAL_DECISION.md](FINAL_DECISION.md), then
[METHODS_RESULTS.md](METHODS_RESULTS.md). Historical D0–D8 reports remain unchanged.

- [SOURCE_AUDIT.md](SOURCE_AUDIT.md): implementation/evidence discrepancy matrix.
- [HOST_INVENTORY.md](HOST_INVENTORY.md): four-host hardware and permissions.
- [METHODOLOGY_ERRATA.md](METHODOLOGY_ERRATA.md): superseding scientific corrections.
- [Q_STATE_AND_MCTS_AUDIT.md](Q_STATE_AND_MCTS_AUDIT.md): O0/O1, search, STOP, resumability.
- [TRAINING_COVERAGE.md](TRAINING_COVERAGE.md): actual roots, seeds, queries and run costs.
- [PAIRED_EVALUATION.md](PAIRED_EVALUATION.md): candidate pairing and precise blockers.
- [tests.log](tests.log): final 35 passing tests; [baseline_tests.log](baseline_tests.log): original 10.

Machine-readable evidence: `manifest.json`, `resolved_config.json`,
`artifact_inventory.json`, `archive_replay.json`, `archive_statistics.json`,
`new_training.json`, `training_pilots.json`, `paired_root_manifest.json`,
`stop_calibration.json`, `physical_parity.json`, `teacher_sources.json`,
`release_verification.json`. Large trees, states, witnesses and model bytes remain
on gvlab under `/scratch/nav/disco_grid/validation_v2/`; Git contains hashes/paths.

Reproducers: `replay_archive.py`, `analyze_archive.py`, `build_pairing.py`,
`replay_physical_parity.py`, `inventory_artifacts.py`,
`audit_administrative_labels.py`, `collect_evidence.py`, `make_figures.py`.
Scripts with explicit on-host archive paths reproduce this session's frozen
snapshots; new runs should use `collect.py` and its parent watchdog. Do not use
the early physical-replay script's in-process timer as a hard 3D wall guarantee.

[Figures](figures/): actual scenes, fresh verified order pair, same-layout joint
configurations, historical root confidence intervals, corrected ablations,
physical edge depth, matched training curves, VAL STOP calibration, and method
diagram. Each has PNG/SVG exports. `case_registry.json` identifies scene hashes,
proposals, verification status and connector witness. Arrows are predicted cell
edits, not executed trajectories. Full 3D arm/video and independent-root
performance learning curves are explicitly unavailable/unexecuted.
