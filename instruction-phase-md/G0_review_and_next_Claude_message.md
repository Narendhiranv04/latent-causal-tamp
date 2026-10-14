# G0 audit and next message to Claude — 15 October 2026

## Assessment of the submitted G0 response

**Verdict: provisionally PASS for G0, not yet certified for G1.** This verdict is based on the pasted completion report, not on an independent inspection of the repository, unit tests, or `runs/g0_scene/overview.png` (not supplied here). The stage claims 14 passing tests and a four-panel rendered schematic, matching the main G0 contract in Implementation Guide v1.6. Keep the 3R arm proportions for now; do not redesign or shorten it merely because it looks long.

- **Reach estimate:** 0.42 + 0.34 + 0.20 = **0.96 m** maximum nominal tool reach. With the stated base (-0.14, 0.32) m and cell centers 0.04 to 0.60 m in x/y, the farthest corner-center distance is **about 0.791 m**. This is nominally within reach, but **does not certify side-grasp IK, a collision-free configuration, closure, or an executable trajectory**.
- **Orientation matters:** for the farthest right corner at (0.60, 0.04) m, with third-link orientation phi=0 (tool pointing +x), the approximate two-link wrist distance is 0.608 m (within the 2R wrist maximum of 0.76 m). With phi=pi (tool pointing -x), it is about 0.981 m (outside that limit). Some approach orientations are impossible even though the corner is inside the nominal 0.96 m reach disc.
- **Gripper:** if the open clear gap is 0.070 m and each finger is 0.007 m thick, overall external width is about 0.084 m, larger than the 0.034 m palm width. A schematic with visually floating jaws is **fine at G0 only**, but G1 must define physically coherent jaw mounting/actuation geometry and apply collisions to actual finger bodies. The initial closed gap of 0.046 m is smaller than a 0.048 m disc diameter: it must mean **closure stops at contact**, never artificial object compression. A 0.070 m aperture nominally fits a 0.048 m diameter, but cluttered access is separate.
- **Home:** q_home=[0,0,0] is provisional and may collide with dense clutter, or place the straight arm beyond the grid. G1 must replace it with a numerically checked, repeatable home if needed.
- **Code structure:** `scene.py` ~255 logical lines falls inside the stated ~120–280 guideline, though 365 physical lines deserve monitoring. No immediate split is required. Move the six-line drawing-only FK out of `viz.py` to the single validated FK in `geometry.py` at G1, as planned. No broad refactor.
- **Cell candidates:** one target cell excluded, one current object cell represented by stay index zero, 62 other non-stay positions is internally consistent for one target; compare against physical spot IDs and clearance checks.
- **Current evidence boundary:** G0 merely draws an illustrative arm. Do not call it `PLANAR_ARM_VERIFIED`. In arbitrary 35-object clutter, no fixed-base arm can be promised access to every object. The reasonable requirement is **corner reach and executable manipulation in unobstructed/sparse development fixtures**, with dense-scene failures faithfully reported.

To independently audit the G0 gate later, provide `runs/g0_scene/overview.png`, `config.toml`, `scene.py`, `viz.py`, `run.py` and the corresponding test/JSON results.

## Exact next message to send Claude Opus 5.5 High Thinking

Before any G1 work, I need you to install two permanent workflow rules. These are mandatory for **every subsequent message and every implementation stage**, not just milestones.

### Rule A — a complete response file, every turn

For each user prompt, write your entire substantive answer, including reasoning summary, evidence, file changes, commands/results, visualization interpretation, open questions and next-stage status, into one sequentially numbered Markdown file:

`reports/0001_<short_topic>.md`, then `reports/0002_<short_topic>.md`, etc.

`reports/` is the **single deliberately permitted additional top-level documentation directory**. Do not add nested reporting frameworks. Treat the file as the source of truth for that turn. The response in chat should give a concise overview and the exact report filename; do not omit essential details from the file. Existing reports are immutable; corrections use a new numbered report that links to the earlier one. Do not claim a report was saved unless you created and inspected it.

For each implementation stage, also keep the guide's normal `runs/<stage>/` evidence: configurations, machine-readable results, tests, scene figures and motion GIFs as appropriate. Store the report links to these artifacts. If a required image or result is absent, state that explicitly.

### Rule B — commit and push after every turn

After creating or changing any project files or the Markdown report, commit and push **all appropriate project deliverables and report files** to the same user-approved GitHub branch before declaring the turn complete.

First inspect whether Git is initialized, the current branch, `git remote -v`, the working-tree status, and whether authentication is available. **The current G0 report says this is not yet a Git repository.** Do not invent a remote, branch, user identity or GitHub credentials. If any are missing, ask me for the repository URL and exact branch name and STOP before attempting a push. You may prepare the report and local commit if safe, but never claim remote synchronization.

When configured, preserve any existing user-owned contents; do not force-push, rewrite history, merge branches, delete unrelated files or change GitHub visibility. Commit source, configs, fixtures, tests, report Markdown, and compact visual evidence. Handle large run data with a clear, explicitly approved Git LFS or artifact policy; never upload passwords, tokens, private keys, local environments or generated caches. Do not quietly omit intended results. If a file cannot be pushed, show the reason and list that file. Record the branch, exact commit hash, remote push outcome, and any excluded artifacts in the report/chat response. Push failures leave the turn `NOT_SYNCED` rather than `COMPLETE`.

### Current G0 review — do not start G1 yet

G0 looks acceptable **as a visual and data-model foundation**, but the drawn arm is not yet a validated robot. Do not alter its proportions simply for cosmetic reasons. No extensive redesign is requested.

The configuration from the guide is provisional: base (-0.14,0.32) m; link lengths (0.42,0.34,0.20) m; open finger gap 0.070 m; palm width 0.034 m; finger thickness 0.007 m. The farthest corner-cell center is approximately 0.791 m from the base versus a maximum nominal reach of 0.96 m. That is encouraging, but it is **not an IK/motion certificate**.

At G1, add these precise **acceptance checks** to the existing guide-defined requirements without changing the project's overall architecture:

1. Audit all 64 supported cell centers for at least one candidate side-grasp pose with valid 3R joint limits, arm/finger geometry and collision checks in a declared obstacle-free reference. Report unreachable cells and their causes; do not assume nominal reach is sufficient.
2. For **all four corners** — `(0,0)`, `(0,7)`, `(7,0)`, `(7,7)` — demonstrate the full articulated side-approach → contact closure → attachment → continuous transport at fixed height → grid-cell release → retreat, using real recorded joint paths. Include valid robot-state connectors and a repeatable start/home configuration. Begin with obstacle-free then designated sparse scenes. Do not promise corner access in arbitrary dense clutter.
3. Provide a 2×2 corner overview and at least one animation of actual robot and finger geometry, with object pose traces and first-collision diagnostics for failures. Never draw straight-line fictitious motion between poses.
4. Make the two fingers visibly and physically connected to a defined palm/slide mounting arrangement in the **G1 collision model**, with correct aperture (inner-tip clear gap versus external width) and admissible contact-based closure. Verify that a 0.048 m disc can be grasped without penetration or arbitrary object compression. Do not require a production-grade mechanical design; require one coherent kinematic and collision model.
5. Run quantitative FK–IK round trips, joint-limit/self-collision/body collision and continuous swept-interval checks, especially near corner configurations. Fix provisional q_home only if necessary and freeze the **tested** robot profile hash.
6. Assess all 64 cells for workspace/pose feasibility, but only claim G1 success on the exact scope of certified grasp/transport tests. If a corner fails, investigate and propose the **smallest principled** change (base mounting, approach orientation, home, link lengths, or gripper profile) justified by numerical evidence before editing the robot profile. Do not shorten links or artificially ignore collisions just to obtain a pass.

For now, **do not implement G1**. First save this workflow/rule update and G0 audit as the next numbered Markdown report and configure GitHub synchronization. Then send the report path, repository/branch status and whether the push actually succeeded, and STOP awaiting my approval.

Also note for future stages: the cupboard file's G6/G7 naming conflict should be clarified according to the **G0–G10 stage registry**, which is the sole authoritative stage ordering. Document missing fixture definitions when their implementation stage is reached; do not fabricate passing results.
