# V3.4 generator source recovery (2026-11-17)

**Where everything came from.** All sources were recovered from **blackwell** (`user1@10.4.25.63:~/yadu_bd`, the teammate's production server, which ran the `*-srv*` namespaces). They were copied read-only to `~/abf_v34/recovered/blackwell/` on the laptop. Nothing was executed on blackwell.

| Item | Recovered | Check |
|---|---|---|
| `bd_2d_cover_table.json` | `code/bd_samples/` (dated 2026-11-01), plus an identical copy in `test_v6/` | sha256 `78e890df…`; `config_hash` 90d3eb68e8a42108; loaded by the frozen `bd_2d_exact.side_ok` |
| 2D production code | `code/bd_samples/*.py` | 8/8 files byte-identical to the frozen mirror (`run_2d_plus`, `bd_2d_plus`, `bd_2d_exact`, `bd_2d_convert`, `convert_2d`, `fastgeom`, `bd_2d`, `bd_core`) |
| ROUTE2D_V1 (behind 98/120 VAL K1 conversions) | `bd_2d_plus.v1.py`, `run_2d_plus.v1.py` | V1 smoke: new V1 root, then frozen `bd_2d_convert.work`, gave a K1 conversion |
| 3D NONE trim V1 (13/63 NONE slots) | `code_nooverpass/bd_samples/shelf66_v3/trim_none66.py` | dense / cert / trim V3 code byte-identical to the local tree |
| Production NONE costs | `runs/.../none_dense` and `none_trim` ledgers | dense 1,420 s per NONE (430/434); trim confirms 332/706 |

**Construction per slot (registered in `config/final_protocol.yaml` and this amendment):**
- **2D refs that were `conv-*` roots (103 slots):** a new ROUTE2D_V1 raw root of the same template, then the frozen conversion (`scripts/v34_conv.py`). Only counted-class V1 roots are converted, as in production `bd_2d_convert.todo`.
- **Other 2D slots:** frozen V6 (`run_2d_plus.work`) with the original cover table. V5-era refs (32 slots) use V6: the only V5 code differences are in exact search, and V6 is the final production generator.
- **3D raw:** SHELF66V3 `run_shelf66_full.work`.
- **3D NONE:** `run_shelf66_none.work` (dense + certificate), then the trim version the ref root used (V1 or V3; `NONE3D_TRIM_MAP.json`), then the NONE gate (`scripts/v34_none3d.py`).
- **Enrichment:**
  - Frozen `perm2d` / `fin3d` + `perm3d` order classification, then `dep2d` / `dep3d` re-park and `hard2d` / `hard3d` (V3 or V4 as in the ref) with their consistency gates (`scripts/v34_enrich.py`, `v34_orch.py`).
  - On historical parents these wrappers reproduced the historical children, labels and strengths (2D parity runs byte-identical).
  - A parent that cannot be enriched sends its slot to a fresh raw instance (`*_r<k>` runs).
