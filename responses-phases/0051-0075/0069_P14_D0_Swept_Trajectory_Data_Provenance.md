# 0069 — P14-D0: provenance of swept-trajectory evidence (STOP gate passed)

**Actual result.**
- **Gate:** `runs/p14/P14_D0_GATE.json` → **PASS**.
- **Real evidence exists:** the repository already stores **real, complete relocation witnesses**. No instrumentation was needed and no trajectory was fabricated (`runs/p14/lookup/PROVENANCE_AUDIT.json`, `p14_sweep_index.audit`).

## 1. What a stored witness contains

Every executed or teacher-witnessed relocation writes `relocation.npz`, with one record per relocation `r{i}`:

| field | content |
|---|---|
| `q` | joint-space waypoints, N × 3, typically 29; the segments are joint-linear, exactly what the certifier checks |
| `gap` | finger aperture per waypoint |
| `phase` | per-segment phase: pregrasp → approach → close_attach → carry → release → retreat (one schedule in all records) |
| `attached` | per-segment attachment flag (the carried disc is part of the moving body during carry) |
| `held_local` | the carried object's centre in the tool frame |
| `place_xy` | placement point |

**Provenance** comes from the sibling `job.json` / `result.json`:
- plan path and root id;
- query or choice;
- seed or episode arm hash;
- executed move sequence, hence the relocation index and the moved object.

The scene **at the time of each relocation** is reconstructed exactly from the root scene plus the executed prefix (`scene_at`).

## 2. Counts

| | records |
|---|---|
| **total relocation records with full provenance** | **6,032** |
| teacher, train | 1,039 |
| teacher, validation | 352 |
| teacher, dev | 393 |
| teacher, blind (P10b / P12 / P13 holdouts) | 3,159 |
| strict-TOP1 episodes, blind | 1,089 |
| fields present (q, gap, phase, attached, held_local, place_xy) | 6,032 / 6,032 |
| distinct absolute (source cell, destination cell) keys | 291 |
| records per key (median / max) | 10 / 155 |
| independent roots per key: median | 2 |
| keys with ≥ 2 independent roots | 184 |
| keys with ≥ 5 independent roots | 99 |

**Index used for D3** (`INDEX.json`, hash `sha256:4c29bbd3…`):
- **4,838 entries**: every record from the 169 P13 blind / natural roots (1,194 records) is excluded, because the D3 evaluation roots are drawn from them;
- 278 keys and 805 motion modes.

## 3. Trace fidelity

A stratified random sample of **150** records was replayed in its own reconstructed scene with the exact continuous certifier (`motion.certify_trajectory`: Lipschitz-bounded bisection over every joint-linear segment in its phase context, plus record-consistency checks):
- **150 / 150 ALL_CLEAR**;
- 0 inconsistent records.

## 4. Swept occupancy (derived, conservative, never decisive)

- **How it is computed:** per phase, the set of grid cells whose obstacle disc (r = 0.024 m) would come within the safety margin δ of any robot body (links, joint housings, palm, finger rail, fingers) or the carried disc anywhere along the recorded path.
- **Sampling:** dense enough that no body point moves more than 4 mm between samples (bound ρ · |Δq|, with ρ the reach beyond each joint plus 0.08 m), and the 4 mm is added to the threshold.
- **Use:** indexing, mode clustering and visual screening only.
- **What decides reuse:** the exact certifier in the current scene. A sampled mask is not a proof of clearance.

## 5. Missing or limited data, and the safety rules adopted

- **Not stored and not needed:** timestamps / velocities (geometric sweep only), and per-waypoint scene snapshots (reconstructed from root + prefix).
- **Excluded:** P10a and historical G-stage witnesses without job provenance.
- **Fixed base, so absolute cells only.** A witness moves a specific object from a specific absolute cell to a specific absolute cell, starting at a specific configuration. Identical relative displacement at other cells is **not** reusable; no translation or rotation of joint paths is done.
- **The start configuration is not canonical.** Each relocation starts where the previous retreat ended. Reuse therefore requires a **certified joint-linear transit** from the current configuration to the witness start: a new motion checked by the same exact certifier. Otherwise the witness is not used.
- **A lookup miss means UNKNOWN,** never infeasibility. Online-planner witnesses found during evaluation are used within that root only and are **not** added to the index before the evaluation ends.
