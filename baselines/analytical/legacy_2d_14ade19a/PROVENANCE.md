# Provenance of the legacy 2D baselines (immutable reference, never imported)

Source: repository `rss-ebm-infeasibility` (partial clone at `/home/naren/Desktop/rss-ebm-infeasibility`), commit
`14ade19a950dbe5f24e2c0711ef83ed8c6238eb3` (author Abhinav Shukla, 2026-11-17 14:10:57 +0530, message "done"), folder `baselines2d/`.
Extracted with `git show 14ade19a9:baselines2d/<path>` (no checkout, nothing modified). Every file below is byte-identical to the
commit's blob (`git hash-object` = blob id, verified 2026-11-18):

| file | git blob id |
|---|---|
| README.md | 83d6fc9395876b0d4d6916b1c639b91058fea8c2 |
| RESULTS.md | 0d6afbb76dba1f5a90bb422cbbed4a9e672fbb28 |
| b2d/__init__.py | e69de29bb2d1d6434b8b29ae775ad8c2e48c5391 |
| b2d/common.py | b9db3ef27a4b505b03433cfa634b8507d9232fc2 |
| b2d/dataset.py | 3dad016947600945bace46e96062d321e752d17f |
| b2d/em4m2d.py | 53622d51bbf6f9e203de9d6bd67f4285b8603cb4 |
| b2d/mosegman.py | c609474dedb49bb3dabb03ebdf8ca3ec73adf860 |
| b2d/msmcts.py | 69c8b272571b91313333bbfefba394731c438ae8 |
| b2d/paths.py | 72a5bf5c90f3f915b72553d3e97b04b1340ffd11 |
| b2d/run.py | 4f8fa5157002fee8b9c36c9b0ab71d671cbe89a9 |
| b2d/table.py | 7fa74e7e9d775982d62147b2e1bffdb9738d4fa2 |
| b2d/teacher.py | 5887c6cc94994021636442db69332f41c278f5af |

Not copied: `baselines2d/out/` (motion caches, raw runs, witnesses), `scripts/`, `results/`, `Dockerfile`, `dk.ps1`. The historical
numbers in RESULTS.md (K <= 4, TEST split, 300 CPU-s) are historical only and are not comparable with the K <= 3 benchmark.
Check: `cd baselines/analytical/legacy_2d_14ade19a && for f in README.md RESULTS.md b2d/*.py; do git hash-object $f; done`.
