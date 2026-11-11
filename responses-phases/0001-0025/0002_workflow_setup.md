# 0002 — Workflow setup: response reports, GitHub synchronization, G0 preservation

| Field | Value |
|---|---|
| Report number | 0002 |
| Date | 15 October 2026 |
| Stage | none (between G0 and G1; **no research functionality added**) |
| Scope authorised | read `instruction-phase-md/`, set up `responses-phases/`, archive G0 report, rerun G0 checks, set up Git/GitHub, commit and push |
| Repository | `https://github.com/Narendhiranv04/latent-causal-tamp` (public), branch `main` |
| Previous report | [`0001_G0_completion.md`](0001_G0_completion.md) |

## 1. What was requested

Two permanent, project-wide workflow rules were requested before G1:

1. **Response documentation.** Every substantive response is saved as a complete, numbered Markdown file in `responses-phases/`.
2. **GitHub synchronization.** Every substantive response is committed and pushed together with the work it describes.

The same request asked to archive the G0 report, rerun the G0 checks without changing research code, record source and config hashes, and **not** start G1.

## 2. Instruction file read

`instruction-phase-md/G0_review_and_next_Claude_message.md` (9,442 bytes) was read in full. It has two parts:

- **An external audit of G0:** a provisional PASS for G0, not yet certified for G1. Its key technical points are folded into the G1 requirements in §6.
- **A drafted message** defining the same two rules (Rule A: a response file every turn; Rule B: commit and push after every turn), plus G1 acceptance checks.

### Conflicts between the instruction file and the user's direct message, and how they were resolved

| Topic | Instruction file | User's direct message (this turn) | Applied |
|---|---|---|---|
| Report directory | `reports/` | `responses-phases/` (already created by the user) | **`responses-phases/`**: the newer, explicit instruction |
| Filenames | `NNNN_<short_topic>.md` | `0001_G0_completion.md`, `0002_workflow_setup.md`, `0003_G1_completion.md`, … | **`NNNN_<topic>.md`** with the user's names; the two schemes are compatible |
| When to write a report | "every turn" | "every substantive response" | every substantive response; a pure clarification question with no project change gets no report |

Every other rule in the instruction file is adopted unchanged:
- Reports are immutable; corrections go in a new report that links to the original.
- Never claim a report was saved without creating and inspecting it.
- No force-push or history rewriting, and no change of repository visibility.
- Never commit secrets, local environments or caches.
- Use an explicit policy for large artifacts.
- A push failure marks the turn `NOT_SYNCED`.

## 3. Response-documentation convention (permanent)

- **Location and naming:** `responses-phases/NNNN_<topic>.md`, with a four-digit, strictly increasing number. Stage reports are named `NNNN_G<k>_completion.md`. A stage that takes several conversations gets several numbered files (for example `NNNN_G1_progress.md`, then `NNNN_G1_completion.md`).
- **Content:** the complete substantive response, not a summary. Stage-completion reports use the A–G structure:
  - A. objective and outcome
  - B. files and line counts
  - C. configuration and reproducibility
  - D. tests and verification
  - E. visualizations
  - F. scientific interpretation
  - G. next-stage readiness, ending with the STOP line
- **Self-containment:** each report states the project context, the decisions taken and the evidence, so it can be reviewed on its own in another conversation.
- **Artifacts:** linked by relative path (`../runs/<run>/overview.png`, `trace.gif`, …). Images are never copied into `responses-phases/`.
- **Immutability:** a committed report is never edited. Corrections go in a new report that references the old one. Report 0001 already uses this rule: one line-count correction is recorded in its archival section, and the original text is left as it was.
- **Commit hash convention:** a report can't contain the hash of the commit that adds it, because the hash depends on the file's own contents. Each report therefore records the *planned* branch and remote. The resulting commit hash and push outcome are:
  - (a) confirmed in the chat message;
  - (b) recorded in the "Previous turn sync" line of the **next** report;
  - (c) always recoverable with `git log --oneline -- responses-phases/NNNN_*.md`.

## 4. G0 preservation and re-verification

No source, config, fixture or run artifact was modified. The rerun checks are listed in [`0001_G0_completion.md` §4](0001_G0_completion.md#4-archival-re-verification-performed-15-october-2026-before-committing). In brief:

| Check | Result |
|---|---|
| `python -m pytest tests -q -p no:cacheprovider` | **14 passed**, exit 0 |
| `runs/g0_scene/` | all 8 artifacts present and readable; 0 SHA-256 mismatches against `manifest.json`, so nothing was regenerated |
| Scene hash (re-hashed on load) | `sha256:4e4af59618663f88741a3fc0e2625617d9f83e077387a58ab33b82bf01ab77fa` |
| Config hash | `sha256:8544e825b33d354915d15fcb310623f826319dfa066386268c1c17a089a6b808` |
| Robot profile hash (PROVISIONAL) | `sha256:b2e15d0778c12ad88048fdc08073b5495b8ff71f5d30242318e9a12660db99f3` |

Source and configuration SHA-256 at archival time:

| File | SHA-256 |
|---|---|
| `scene.py` | `c2e20716d9fffc5ba5dfec8f4b5688b4caa2832e8b07a4abf725d9c99b9f2e02` |
| `viz.py` | `7946f160397006b9b953d283c5df9e4625be1efbb7e9b6ab1786adb993d30af4` |
| `run.py` | `f989521a12a83611bdb45b55113af009982a75977c10931a088dfaff07c6b97f` |
| `tests/test_scene.py` | `8f2cf8fcc693010f9b6f6a8b2ce11ba8c29575336c348c07bde73d64184867c4` |
| `config.toml` | `0d7a2310f8908cf06583cfec8b707e5c9355d7b747d15cf0d7c6dd5484a65316` |
| `fixtures.json` | `847efc8e52eb5e59ae2d6b4b412eeea9b7f68f193dcdc62173f08a00c647fcfc` |
| `requirements.lock` | `009c2ed27bff87c1d39f919b3e6da39bd3f8bb4e209b7f5d6258b6d7bffce0de` |

The robot geometry is untouched, as instructed: base (−0.14, 0.32) m, links (0.42, 0.34, 0.20) m, open gap 0.070 m, palm width 0.034 m, finger thickness 0.007 m, `q_home = [0,0,0]`.

**Correction carried into 0001:** in the G0 report, `viz.py` was given as "~280 / ~205" lines. The exact count is 271 physical / 197 logical. This does not affect any conclusion.

The G0 overview and clean observation are preserved and committed:
- [`../runs/g0_scene/overview.png`](../runs/g0_scene/overview.png)
- [`../runs/g0_scene/observation.png`](../runs/g0_scene/observation.png)

## 5. Git and GitHub setup

### Initial state inspected

| Item | Found |
|---|---|
| Git repository | **none** (`fatal: not a git repository`) |
| Global `user.name` / `user.email` | **not set** |
| GitHub CLI | authenticated as `Narendhiranv04` (HTTPS, token scopes include `repo`); credential helper `store` |
| Git LFS | installed (git-lfs 3.7.1), global filter configured |
| Matching existing repo | none named for this project. `causal-infeasibility-ebm` exists but was **not** used, to avoid mixing with existing work. |

### Decisions requested from the user (asked; nothing was invented)

| Question | User's answer |
|---|---|
| Repository | **new public repo** `Narendhiranv04/latent-causal-tamp` |
| Branch | **`main`** |
| Commit identity | **GitHub noreply**: `Narendhiran V <127112785+Narendhiranv04@users.noreply.github.com>`, set **repo-locally** only |

### Actions

1. `git init -b main` in the project root; the identity above was set with `git config` (local scope only).
2. Added `.gitignore`. It excludes `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `venv/` and `.env`, and nothing else; no results are ignored.
3. Updated `README.md`: added rows for `responses-phases/` and `instruction-phase-md/`, a note on the per-response workflow, and a link from G0's status row to report 0001. No code changes.
4. **Secret scan** over every tracked text file. The patterns covered GitHub tokens, API keys, `password`/`secret`/`token`, private-key headers and AWS keys. Only hit: the words "passwords, tokens" in prose inside the instruction file, a false positive. No credentials, keys or environments are tracked.
5. Created the public GitHub repository with `gh repo create` (no auto-push), added `origin` and pushed `main` with plain `git push -u origin main`, without `--force`.

### What is committed (22 files, ≈ 0.96 MB)

| Group | Files |
|---|---|
| Source | `scene.py`, `viz.py`, `run.py`, `tests/test_scene.py` |
| Configuration and fixtures | `config.toml`, `fixtures.json`, `requirements.lock`, `.gitignore` |
| Documentation | `README.md`, both authoritative PDFs (214 KB and 218 KB), `instruction-phase-md/G0_review_and_next_Claude_message.md` |
| Reports | `responses-phases/0001_G0_completion.md`, `responses-phases/0002_workflow_setup.md` |
| G0 evidence | `runs/g0_scene/{arrays.npz, config.json, manifest.json, metrics.csv, observation.png, overview.png, result.json, scene.json}` (largest: `overview.png`, 402 KB) |

**Visibility note:** the repository is public by the user's choice. That means the methodology and guide PDFs, the external review text and every future report are publicly readable.

**Excluded:** only generated caches (`__pycache__`, `.pytest_cache`). No intended result was omitted.

### Large-artifact policy (proposed; needs explicit approval before first use)

| Artifact type (expected from) | Typical size | Proposal |
|---|---|---|
| PNG figures, JSON, CSV, small NPZ (G0 onward) | KB–a few MB | normal Git |
| Motion GIFs (G1 onward) | 0.2–5 MB each | normal Git; keep GIFs compact (downsampled frames, ≤ ~5 MB each) |
| Model checkpoints `*.pt` (G5 onward) | 1–50+ MB | **Git LFS** (`git lfs track "*.pt"`) |
| Dataset shards / large NPZ (G4 onward) | 10 MB–GB | **Git LFS**; if the total would exceed the account's LFS quota, keep a manifest with SHA-256 in Git and store the shards externally under a location you specify |
| Videos `*.mp4` (if any) | MB+ | Git LFS |

GitHub warns for files over 50 MB and rejects files over 100 MB without LFS. Nothing currently comes close. LFS tracking will be proposed in the report of the stage that first produces such files, and turned on only after your approval.

## 6. Recorded G1 requirements (to apply when G1 is authorised; **not implemented now**)

These add to the G1 contract in Guide v1.6 §5, combining the user's message and the instruction file:

1. **64-cell coverage audit:** for every supported cell centre, search for at least one candidate side-grasp pose that respects 3R joint limits, the full arm and finger geometry, and collision checks in a declared obstacle-free reference. Report each unreachable cell with its cause. Maximum nominal reach (0.96 m, against a farthest corner-centre distance of about 0.791 m) is **not** treated as grasp reachability.
2. **Four corners** `(0,0)`, `(0,7)`, `(7,0)`, `(7,7)`: show the full articulated sequence on real recorded joint paths: side approach → contact closure → attachment → continuous fixed-height transport → release on a grid cell → retreat. Include valid robot-state connectors and a repeatable home. Run obstacle-free first, then designated sparse scenes. Access in arbitrary dense clutter is not promised.
3. **Approach orientation matters:** for example, at (0.60, 0.04) with φ = π the wrist distance is about 0.981 m, beyond the 2R wrist limit of 0.76 m. The audit records which approach directions are feasible for each cell.
4. **Visualization:** a 2×2 corner overview and at least one animation of the actual robot and finger geometry, from recorded trajectories (never straight-line interpolation), with object pose traces and first-collision diagnostics for failures.
5. **Gripper model:** fingers physically connected to a defined palm or slide mounting in the G1 collision model, with the inner clear gap kept distinct from the external width. Closure stops at contact and never compresses the object. Verify that a 0.048 m disc is grasped without penetration.
6. **Numerical checks:** FK–IK round trips; joint limits; self-collision and body collision; continuous swept-interval checks, especially near corners. Fix `q_home` only if necessary, then freeze a **tested** robot profile hash.
7. **Robot dimensions:** keep the current dimensions unless tests show a concrete limitation. If a corner fails, propose the smallest principled change (base mounting, approach orientation, home, link lengths or gripper profile), backed by numerical evidence, before editing the profile. Never shorten links or ignore collisions just to get a pass.
8. **Scope of claims:** G1 success is claimed only for the exact scope of the certified tests. Dense-scene failures are reported faithfully.

Notes for later stages, also recorded:
- **Cupboard stage:** the G6/G7 conflict for the cupboard is resolved by the G0–G10 stage registry, which is the sole authority: `cupboard.toml` and the xArm7 assets arrive at **G7**.
- **Undefined fixtures:** T01, T02, T06, T11 and C00–C07 (except C04) are documented as undefined when their stage arrives, never fabricated.

## 7. Repository status and synchronization

| Item | Value |
|---|---|
| Remote | `origin` → `https://github.com/Narendhiranv04/latent-causal-tamp.git` |
| Branch | `main` (upstream `origin/main`) |
| Commit content | everything in §5 "What is committed", including this report |
| Commit hash and push result | can't be written inside this file (see §3). Confirmed in the chat reply and recorded as "Previous turn sync" in report 0003. |

## 8. Next-stage readiness

- G0 is preserved and re-verified (14/14 tests, artifacts intact).
- The workflow rules are in force for all future stages G1–G10:
  1. Do only the authorised work.
  2. Run tests and checks.
  3. Generate and inspect visualizations.
  4. Write the numbered report.
  5. Review the diff and scan for secrets.
  6. Commit the work and the report together.
  7. Push to `main`.
  8. Confirm the hash, branch, push result and report path in chat.
  9. STOP.
- **Next stage, G1, not started:** 3R FK/IK, the full-body collision model including the connected gripper, continuous robot phases, the 64-cell coverage audit, four-corner manipulation sequences and the first validated nominal skill, then freezing the tested robot profile hash.

**STOP — Awaiting explicit approval before proceeding to G1.**
