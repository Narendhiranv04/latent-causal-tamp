# P7 visualizations

Generated from recorded P7 data only: `python run.py p7a-viz` (diagnostic renders, no robot execution) and `python run.py p7b-viz`.
Sources: `runs/p7/a_training` (P7a checkpoints + snapshots), `runs/p7/collection` (teacher records, recorded witness arrays), `runs/p7/training` (P7b checkpoints, rankings hash in `rankings.json`), `runs/p7/execution` (one-shot episodes, own recorded arrays).

## Label legend

- **VERIFIED - recorded trajectory** / **NEW ONE-SHOT EXECUTION (recorded)**: motion replayed from stored, re-checked arrays of that exact run.
- **CERTIFIED INFEASIBLE (kind)**: accepted certificate (incl. LINK0_SECTOR_PICK sweep proofs); nothing drawn as motion.
- **BUDGET_INFEASIBLE (operational) - NO VERIFIED TRACE**: clean 3-seed OPNEG-v1 exhaustion; policy-relative, not a proof.
- **UNKNOWN / NOT RUN - NO VERIFIED TRACE**: censored, cap-stopped or lineage-stopped; never a negative.
- **HYPOTHETICAL SCENE EDIT - NOT A ROBOT RELOCATION**: fixed-robot target-only query; **DIAGNOSTIC RENDER**: P7a model inspection.
- **PROPOSED, NOT EXECUTED** / **MODEL PROPOSALS - NOT EXECUTED**: candidates; numbered arrows give the order.

## Files

| file | what it shows | sha256 |
|---|---|---|
| `a/scene_edits_A_B_AB.gif` | P7a: fixed-robot edits none / A / B / A+B, teacher outcome vs predicted root-level marginals (P6 B vs ABC7) | `6f7a02077ea78bdc...` |
| `a/P7a_loss_gradients.gif` | P7a: per-term losses, pre-clip global gradient norm with clip level, per-term unclipped gradient norms (A, B, C) | `a6b7d2c6c59a24fa...` |
| `a/B_C_coupling_ablation.gif` | P7a: scene marginals and kappa_hat over training for full / quadratic / no-coupling B and C on p6_2026102303 | `0f21f752cba72574...` |
| `b/roots/p7_2026102401_KP_train/scene_start.png` | p7_2026102401: initial scene, roles, goal (dashed), start stratum S2 | `9f25ffbd066b1031...` |
| `b/roots/p7_2026102401_KP_train/catalogue.png` | p7_2026102401: frozen catalogue with teacher statuses | `26ae79246ba3a1f8...` |
| `b/roots/p7_2026102401_KP_train/executed_repairs.gif` | p7_2026102401: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `1a3ccfd95774b197...` |
| `b/roots/p7_2026102401_KP_train/order_comparison.gif` | p7_2026102401: same-endpoint order pairs side by side (recorded traces or static status panels) | `3612e0870356db30...` |
| `b/roots/p7_2026102401_KP_train/interventions.gif` | p7_2026102401: fixed-robot scene edits (target-only evaluation in the edited scene) | `25ba671ce596dd88...` |
| `b/roots/p7_2026102401_KP_train/candidate_orders.gif` | p7_2026102401: every predeclared candidate (arrows numbered by order) and its teacher status | `b3de2d12eb49acb8...` |
| `b/roots/p7_2026102402_KP_validation/scene_start.png` | p7_2026102402: initial scene, roles, goal (dashed), start stratum S3 | `cc2315b12e5bb440...` |
| `b/roots/p7_2026102402_KP_validation/catalogue.png` | p7_2026102402: frozen catalogue with teacher statuses | `61010e6e8a7c114a...` |
| `b/roots/p7_2026102402_KP_validation/executed_repairs.gif` | p7_2026102402: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `cbec2df91328dee2...` |
| `b/roots/p7_2026102402_KP_validation/order_comparison.gif` | p7_2026102402: same-endpoint order pairs side by side (recorded traces or static status panels) | `3f99873b725d7818...` |
| `b/roots/p7_2026102402_KP_validation/interventions.gif` | p7_2026102402: fixed-robot scene edits (target-only evaluation in the edited scene) | `1dc7bd3b054f1fec...` |
| `b/roots/p7_2026102402_KP_validation/candidate_orders.gif` | p7_2026102402: every predeclared candidate (arrows numbered by order) and its teacher status | `70a8e494a50df2e3...` |
| `b/roots/p7_2026102403_KP_train/scene_start.png` | p7_2026102403: initial scene, roles, goal (dashed), start stratum S0 | `098e31b0991549d9...` |
| `b/roots/p7_2026102403_KP_train/catalogue.png` | p7_2026102403: frozen catalogue with teacher statuses | `fb455f16b9e800a8...` |
| `b/roots/p7_2026102403_KP_train/executed_repairs.gif` | p7_2026102403: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `c97362ef87c843bb...` |
| `b/roots/p7_2026102403_KP_train/order_comparison.gif` | p7_2026102403: same-endpoint order pairs side by side (recorded traces or static status panels) | `a30386450ec25ff5...` |
| `b/roots/p7_2026102403_KP_train/interventions.gif` | p7_2026102403: fixed-robot scene edits (target-only evaluation in the edited scene) | `64233d667a26aa24...` |
| `b/roots/p7_2026102403_KP_train/candidate_orders.gif` | p7_2026102403: every predeclared candidate (arrows numbered by order) and its teacher status | `a20f4cc6c23ebbc7...` |
| `b/roots/p7_2026102404_KP_test/scene_start.png` | p7_2026102404: initial scene, roles, goal (dashed), start stratum S1 | `88cc5eed02679f8f...` |
| `b/roots/p7_2026102404_KP_test/catalogue.png` | p7_2026102404: frozen catalogue with teacher statuses | `75d0b7e9ca5f3c3b...` |
| `b/roots/p7_2026102404_KP_test/executed_repairs.gif` | p7_2026102404: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `c536f510f9d4a5d4...` |
| `b/roots/p7_2026102404_KP_test/order_comparison.gif` | p7_2026102404: same-endpoint order pairs side by side (recorded traces or static status panels) | `e126748802df94f1...` |
| `b/roots/p7_2026102404_KP_test/interventions.gif` | p7_2026102404: fixed-robot scene edits (target-only evaluation in the edited scene) | `9c6b87176da7e9f1...` |
| `b/roots/p7_2026102404_KP_test/candidate_orders.gif` | p7_2026102404: every predeclared candidate (arrows numbered by order) and its teacher status | `d6b0ed5773a15989...` |
| `b/roots/p7_2026102405_KM_train/scene_start.png` | p7_2026102405: initial scene, roles, goal (dashed), start stratum S3 | `fe3ded87098f8646...` |
| `b/roots/p7_2026102405_KM_train/catalogue.png` | p7_2026102405: frozen catalogue with teacher statuses | `ab467d93f1410b05...` |
| `b/roots/p7_2026102405_KM_train/executed_repairs.gif` | p7_2026102405: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `cb4ba0aadeab6e3a...` |
| `b/roots/p7_2026102405_KM_train/order_comparison.gif` | p7_2026102405: same-endpoint order pairs side by side (recorded traces or static status panels) | `293ac87a3392c9a2...` |
| `b/roots/p7_2026102405_KM_train/interventions.gif` | p7_2026102405: fixed-robot scene edits (target-only evaluation in the edited scene) | `2853d9f7585b33a1...` |
| `b/roots/p7_2026102405_KM_train/candidate_orders.gif` | p7_2026102405: every predeclared candidate (arrows numbered by order) and its teacher status | `888703e07933c969...` |
| `b/roots/p7_2026102406_KM_validation/scene_start.png` | p7_2026102406: initial scene, roles, goal (dashed), start stratum S0 | `43e2a348896e470e...` |
| `b/roots/p7_2026102406_KM_validation/catalogue.png` | p7_2026102406: frozen catalogue with teacher statuses | `2d063e7d0579714b...` |
| `b/roots/p7_2026102406_KM_validation/executed_repairs.gif` | p7_2026102406: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `6c770f06bfed8582...` |
| `b/roots/p7_2026102406_KM_validation/order_comparison.gif` | p7_2026102406: same-endpoint order pairs side by side (recorded traces or static status panels) | `523b478a673b3254...` |
| `b/roots/p7_2026102406_KM_validation/interventions.gif` | p7_2026102406: fixed-robot scene edits (target-only evaluation in the edited scene) | `401da2ed5e1708d0...` |
| `b/roots/p7_2026102406_KM_validation/candidate_orders.gif` | p7_2026102406: every predeclared candidate (arrows numbered by order) and its teacher status | `af9f0cc7c7ce78a4...` |
| `b/roots/p7_2026102407_KM_train/scene_start.png` | p7_2026102407: initial scene, roles, goal (dashed), start stratum S1 | `f3496c2e9f7fcd0c...` |
| `b/roots/p7_2026102407_KM_train/catalogue.png` | p7_2026102407: frozen catalogue with teacher statuses | `7e7ee9d6e5ebf79a...` |
| `b/roots/p7_2026102407_KM_train/executed_repairs.gif` | p7_2026102407: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `3c2933996c6d7f5b...` |
| `b/roots/p7_2026102407_KM_train/order_comparison.gif` | p7_2026102407: same-endpoint order pairs side by side (recorded traces or static status panels) | `2900c7cfe7a661b8...` |
| `b/roots/p7_2026102407_KM_train/interventions.gif` | p7_2026102407: fixed-robot scene edits (target-only evaluation in the edited scene) | `6e8194eb73c6e39d...` |
| `b/roots/p7_2026102407_KM_train/candidate_orders.gif` | p7_2026102407: every predeclared candidate (arrows numbered by order) and its teacher status | `36786fd86d2c47cb...` |
| `b/roots/p7_2026102408_KM_test/scene_start.png` | p7_2026102408: initial scene, roles, goal (dashed), start stratum S2 | `15eb512e7da9efa6...` |
| `b/roots/p7_2026102408_KM_test/catalogue.png` | p7_2026102408: frozen catalogue with teacher statuses | `d70be9f957ce115f...` |
| `b/roots/p7_2026102408_KM_test/executed_repairs.gif` | p7_2026102408: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `49a3fd6a257a54ef...` |
| `b/roots/p7_2026102408_KM_test/order_comparison.gif` | p7_2026102408: same-endpoint order pairs side by side (recorded traces or static status panels) | `ede59bae27e2b2bc...` |
| `b/roots/p7_2026102408_KM_test/interventions.gif` | p7_2026102408: fixed-robot scene edits (target-only evaluation in the edited scene) | `a46dbd7284424745...` |
| `b/roots/p7_2026102408_KM_test/candidate_orders.gif` | p7_2026102408: every predeclared candidate (arrows numbered by order) and its teacher status | `a7f2f28fbd7bf903...` |
| `b/roots/p7_2026102409_K0_train/scene_start.png` | p7_2026102409: initial scene, roles, goal (dashed), start stratum S0 | `9fd72b043b3018f6...` |
| `b/roots/p7_2026102409_K0_train/catalogue.png` | p7_2026102409: frozen catalogue with teacher statuses | `18bc783a5d225140...` |
| `b/roots/p7_2026102409_K0_train/executed_repairs.gif` | p7_2026102409: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `6944a2bbbaaa537b...` |
| `b/roots/p7_2026102409_K0_train/order_comparison.gif` | p7_2026102409: same-endpoint order pairs side by side (recorded traces or static status panels) | `918743e59d2d052c...` |
| `b/roots/p7_2026102409_K0_train/interventions.gif` | p7_2026102409: fixed-robot scene edits (target-only evaluation in the edited scene) | `1612ee87ec01c3cd...` |
| `b/roots/p7_2026102409_K0_train/candidate_orders.gif` | p7_2026102409: every predeclared candidate (arrows numbered by order) and its teacher status | `12920fb6c4331da5...` |
| `b/roots/p7_2026102410_K0_validation/scene_start.png` | p7_2026102410: initial scene, roles, goal (dashed), start stratum S1 | `c341d48b6087dfe4...` |
| `b/roots/p7_2026102410_K0_validation/catalogue.png` | p7_2026102410: frozen catalogue with teacher statuses | `298e81ef9c3a61c9...` |
| `b/roots/p7_2026102410_K0_validation/executed_repairs.gif` | p7_2026102410: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `de36ceb28206938f...` |
| `b/roots/p7_2026102410_K0_validation/order_comparison.gif` | p7_2026102410: same-endpoint order pairs side by side (recorded traces or static status panels) | `fc0dcbeefebb0c11...` |
| `b/roots/p7_2026102410_K0_validation/interventions.gif` | p7_2026102410: fixed-robot scene edits (target-only evaluation in the edited scene) | `2d0fe401bfe820d9...` |
| `b/roots/p7_2026102410_K0_validation/candidate_orders.gif` | p7_2026102410: every predeclared candidate (arrows numbered by order) and its teacher status | `ce557ed77b712136...` |
| `b/roots/p7_2026102411_K0_train/scene_start.png` | p7_2026102411: initial scene, roles, goal (dashed), start stratum S2 | `866c244594daee78...` |
| `b/roots/p7_2026102411_K0_train/catalogue.png` | p7_2026102411: frozen catalogue with teacher statuses | `a4816c467d67d511...` |
| `b/roots/p7_2026102411_K0_train/executed_repairs.gif` | p7_2026102411: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `e3fb5beb468d2580...` |
| `b/roots/p7_2026102411_K0_train/order_comparison.gif` | p7_2026102411: same-endpoint order pairs side by side (recorded traces or static status panels) | `7c106bc27800c22f...` |
| `b/roots/p7_2026102411_K0_train/interventions.gif` | p7_2026102411: fixed-robot scene edits (target-only evaluation in the edited scene) | `c01661465de50b37...` |
| `b/roots/p7_2026102411_K0_train/candidate_orders.gif` | p7_2026102411: every predeclared candidate (arrows numbered by order) and its teacher status | `462c617be93e1b7f...` |
| `b/roots/p7_2026102412_K0_test/scene_start.png` | p7_2026102412: initial scene, roles, goal (dashed), start stratum S3 | `f01b06a36720a4b4...` |
| `b/roots/p7_2026102412_K0_test/catalogue.png` | p7_2026102412: frozen catalogue with teacher statuses | `d39aded8555b9afa...` |
| `b/roots/p7_2026102412_K0_test/executed_repairs.gif` | p7_2026102412: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `c8f7362d3cc372c7...` |
| `b/roots/p7_2026102412_K0_test/order_comparison.gif` | p7_2026102412: same-endpoint order pairs side by side (recorded traces or static status panels) | `92f9756c597a2071...` |
| `b/roots/p7_2026102412_K0_test/interventions.gif` | p7_2026102412: fixed-robot scene edits (target-only evaluation in the edited scene) | `5c7884cd3796190d...` |
| `b/roots/p7_2026102412_K0_test/candidate_orders.gif` | p7_2026102412: every predeclared candidate (arrows numbered by order) and its teacher status | `16eb092d1b609cdf...` |
| `b/roots/p7_2026102413_ORD_train/scene_start.png` | p7_2026102413: initial scene, roles, goal (dashed), start stratum S1 | `df318e488db2f5f6...` |
| `b/roots/p7_2026102413_ORD_train/catalogue.png` | p7_2026102413: frozen catalogue with teacher statuses | `d58f95495a44227a...` |
| `b/roots/p7_2026102413_ORD_train/executed_repairs.gif` | p7_2026102413: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `8653d32f0cb920d4...` |
| `b/roots/p7_2026102413_ORD_train/order_comparison.gif` | p7_2026102413: same-endpoint order pairs side by side (recorded traces or static status panels) | `5118b86c4c427ac2...` |
| `b/roots/p7_2026102413_ORD_train/interventions.gif` | p7_2026102413: fixed-robot scene edits (target-only evaluation in the edited scene) | `a03a3642a385e707...` |
| `b/roots/p7_2026102413_ORD_train/candidate_orders.gif` | p7_2026102413: every predeclared candidate (arrows numbered by order) and its teacher status | `1f7493c2478e9409...` |
| `b/roots/p7_2026102414_ORD_validation/scene_start.png` | p7_2026102414: initial scene, roles, goal (dashed), start stratum S2 | `18485431b4023c0f...` |
| `b/roots/p7_2026102414_ORD_validation/catalogue.png` | p7_2026102414: frozen catalogue with teacher statuses | `40f211d41ad36c83...` |
| `b/roots/p7_2026102414_ORD_validation/executed_repairs.gif` | p7_2026102414: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `07701c95274f68ab...` |
| `b/roots/p7_2026102414_ORD_validation/order_comparison.gif` | p7_2026102414: same-endpoint order pairs side by side (recorded traces or static status panels) | `ea35833bcc86ee28...` |
| `b/roots/p7_2026102414_ORD_validation/interventions.gif` | p7_2026102414: fixed-robot scene edits (target-only evaluation in the edited scene) | `c87048181a4326fe...` |
| `b/roots/p7_2026102414_ORD_validation/candidate_orders.gif` | p7_2026102414: every predeclared candidate (arrows numbered by order) and its teacher status | `8946c0804bc78008...` |
| `b/roots/p7_2026102415_ORD_train/scene_start.png` | p7_2026102415: initial scene, roles, goal (dashed), start stratum S3 | `aa1eecae2259061c...` |
| `b/roots/p7_2026102415_ORD_train/catalogue.png` | p7_2026102415: frozen catalogue with teacher statuses | `f92f93d42740bcce...` |
| `b/roots/p7_2026102415_ORD_train/executed_repairs.gif` | p7_2026102415: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `b734b7937d6568e7...` |
| `b/roots/p7_2026102415_ORD_train/order_comparison.gif` | p7_2026102415: same-endpoint order pairs side by side (recorded traces or static status panels) | `743e41adb1f10430...` |
| `b/roots/p7_2026102415_ORD_train/interventions.gif` | p7_2026102415: fixed-robot scene edits (target-only evaluation in the edited scene) | `52de1a155b7afca0...` |
| `b/roots/p7_2026102415_ORD_train/candidate_orders.gif` | p7_2026102415: every predeclared candidate (arrows numbered by order) and its teacher status | `9c18317549c65266...` |
| `b/roots/p7_2026102416_ORD_test/scene_start.png` | p7_2026102416: initial scene, roles, goal (dashed), start stratum S0 | `f72ac49d212370d4...` |
| `b/roots/p7_2026102416_ORD_test/catalogue.png` | p7_2026102416: frozen catalogue with teacher statuses | `1aceaabbe39b8f6d...` |
| `b/roots/p7_2026102416_ORD_test/executed_repairs.gif` | p7_2026102416: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `79589831880f000c...` |
| `b/roots/p7_2026102416_ORD_test/order_comparison.gif` | p7_2026102416: same-endpoint order pairs side by side (recorded traces or static status panels) | `235cdc755fc12bdb...` |
| `b/roots/p7_2026102416_ORD_test/interventions.gif` | p7_2026102416: fixed-robot scene edits (target-only evaluation in the edited scene) | `e4e89b1e1ae2d8fa...` |
| `b/roots/p7_2026102416_ORD_test/candidate_orders.gif` | p7_2026102416: every predeclared candidate (arrows numbered by order) and its teacher status | `e5ea498f1095f06c...` |
| `b/roots/p7_2026102417_MOT_train/scene_start.png` | p7_2026102417: initial scene, roles, goal (dashed), start stratum S3 | `eaa19d8bee684a43...` |
| `b/roots/p7_2026102417_MOT_train/catalogue.png` | p7_2026102417: frozen catalogue with teacher statuses | `86808b692a8f6597...` |
| `b/roots/p7_2026102417_MOT_train/executed_repairs.gif` | p7_2026102417: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `c48680149fff6619...` |
| `b/roots/p7_2026102417_MOT_train/order_comparison.gif` | p7_2026102417: same-endpoint order pairs side by side (recorded traces or static status panels) | `b6c6cdf67c7cc79c...` |
| `b/roots/p7_2026102417_MOT_train/interventions.gif` | p7_2026102417: fixed-robot scene edits (target-only evaluation in the edited scene) | `e7b63108709b6fcd...` |
| `b/roots/p7_2026102417_MOT_train/candidate_orders.gif` | p7_2026102417: every predeclared candidate (arrows numbered by order) and its teacher status | `5e208c3ef5ec941a...` |
| `b/roots/p7_2026102418_MOT_validation/scene_start.png` | p7_2026102418: initial scene, roles, goal (dashed), start stratum S0 | `d0855ec559f14704...` |
| `b/roots/p7_2026102418_MOT_validation/catalogue.png` | p7_2026102418: frozen catalogue with teacher statuses | `5a4eb33b843ba9e1...` |
| `b/roots/p7_2026102418_MOT_validation/executed_repairs.gif` | p7_2026102418: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `89841cb3c26e550e...` |
| `b/roots/p7_2026102418_MOT_validation/order_comparison.gif` | p7_2026102418: same-endpoint order pairs side by side (recorded traces or static status panels) | `e5daa3b919b6f790...` |
| `b/roots/p7_2026102418_MOT_validation/interventions.gif` | p7_2026102418: fixed-robot scene edits (target-only evaluation in the edited scene) | `3023413a2f058a34...` |
| `b/roots/p7_2026102418_MOT_validation/candidate_orders.gif` | p7_2026102418: every predeclared candidate (arrows numbered by order) and its teacher status | `193b3a807572bd6e...` |
| `b/roots/p7_2026102419_MOT_train/scene_start.png` | p7_2026102419: initial scene, roles, goal (dashed), start stratum S1 | `008b9398ecb103d2...` |
| `b/roots/p7_2026102419_MOT_train/catalogue.png` | p7_2026102419: frozen catalogue with teacher statuses | `bcac8785138248d2...` |
| `b/roots/p7_2026102419_MOT_train/executed_repairs.gif` | p7_2026102419: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `bcc70b2542176818...` |
| `b/roots/p7_2026102419_MOT_train/order_comparison.gif` | p7_2026102419: same-endpoint order pairs side by side (recorded traces or static status panels) | `d98d10700863c249...` |
| `b/roots/p7_2026102419_MOT_train/interventions.gif` | p7_2026102419: fixed-robot scene edits (target-only evaluation in the edited scene) | `cad5b8b3edbe5652...` |
| `b/roots/p7_2026102419_MOT_train/candidate_orders.gif` | p7_2026102419: every predeclared candidate (arrows numbered by order) and its teacher status | `0a78991c9131e5b1...` |
| `b/roots/p7_2026102420_MOT_test/scene_start.png` | p7_2026102420: initial scene, roles, goal (dashed), start stratum S3 | `95e8ac5819379b97...` |
| `b/roots/p7_2026102420_MOT_test/catalogue.png` | p7_2026102420: frozen catalogue with teacher statuses | `a372aaee72857ad4...` |
| `b/roots/p7_2026102420_MOT_test/executed_repairs.gif` | p7_2026102420: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `f95f4c42da4626b3...` |
| `b/roots/p7_2026102420_MOT_test/order_comparison.gif` | p7_2026102420: same-endpoint order pairs side by side (recorded traces or static status panels) | `bd3548768c15113f...` |
| `b/roots/p7_2026102420_MOT_test/interventions.gif` | p7_2026102420: fixed-robot scene edits (target-only evaluation in the edited scene) | `f8b00562a262d2d3...` |
| `b/roots/p7_2026102420_MOT_test/candidate_orders.gif` | p7_2026102420: every predeclared candidate (arrows numbered by order) and its teacher status | `7f920400adbdc144...` |
| `b/roots/p7_2026102421_ALT_train/scene_start.png` | p7_2026102421: initial scene, roles, goal (dashed), start stratum S3 | `28250a0dadd897b9...` |
| `b/roots/p7_2026102421_ALT_train/catalogue.png` | p7_2026102421: frozen catalogue with teacher statuses | `2cb6a71dae08e34e...` |
| `b/roots/p7_2026102421_ALT_train/executed_repairs.gif` | p7_2026102421: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `984e46de7c327b8c...` |
| `b/roots/p7_2026102421_ALT_train/order_comparison.gif` | p7_2026102421: same-endpoint order pairs side by side (recorded traces or static status panels) | `59a81e7f764a4311...` |
| `b/roots/p7_2026102421_ALT_train/interventions.gif` | p7_2026102421: fixed-robot scene edits (target-only evaluation in the edited scene) | `7478e4c3a677191a...` |
| `b/roots/p7_2026102421_ALT_train/candidate_orders.gif` | p7_2026102421: every predeclared candidate (arrows numbered by order) and its teacher status | `7a2b64a34efddd93...` |
| `b/roots/p7_2026102422_ALT_validation/scene_start.png` | p7_2026102422: initial scene, roles, goal (dashed), start stratum S0 | `05061b5eaf4a5969...` |
| `b/roots/p7_2026102422_ALT_validation/catalogue.png` | p7_2026102422: frozen catalogue with teacher statuses | `a71d6a1576e4e201...` |
| `b/roots/p7_2026102422_ALT_validation/executed_repairs.gif` | p7_2026102422: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `34b07b43b49b7548...` |
| `b/roots/p7_2026102422_ALT_validation/order_comparison.gif` | p7_2026102422: same-endpoint order pairs side by side (recorded traces or static status panels) | `0a36bdbe12dc336e...` |
| `b/roots/p7_2026102422_ALT_validation/interventions.gif` | p7_2026102422: fixed-robot scene edits (target-only evaluation in the edited scene) | `ea2f74f1e861a1cf...` |
| `b/roots/p7_2026102422_ALT_validation/candidate_orders.gif` | p7_2026102422: every predeclared candidate (arrows numbered by order) and its teacher status | `68cd53097c1b6889...` |
| `b/roots/p7_2026102423_ALT_train/scene_start.png` | p7_2026102423: initial scene, roles, goal (dashed), start stratum S1 | `98487353d8fe5833...` |
| `b/roots/p7_2026102423_ALT_train/catalogue.png` | p7_2026102423: frozen catalogue with teacher statuses | `79627f04b4c3e14d...` |
| `b/roots/p7_2026102423_ALT_train/executed_repairs.gif` | p7_2026102423: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `ac21948518c305b8...` |
| `b/roots/p7_2026102423_ALT_train/order_comparison.gif` | p7_2026102423: same-endpoint order pairs side by side (recorded traces or static status panels) | `936efad43016a314...` |
| `b/roots/p7_2026102423_ALT_train/interventions.gif` | p7_2026102423: fixed-robot scene edits (target-only evaluation in the edited scene) | `e598e835c699d64c...` |
| `b/roots/p7_2026102423_ALT_train/candidate_orders.gif` | p7_2026102423: every predeclared candidate (arrows numbered by order) and its teacher status | `32dd9bf706b22262...` |
| `b/roots/p7_2026102424_ALT_test/scene_start.png` | p7_2026102424: initial scene, roles, goal (dashed), start stratum S2 | `2e36903b891f2ad7...` |
| `b/roots/p7_2026102424_ALT_test/catalogue.png` | p7_2026102424: frozen catalogue with teacher statuses | `46ea6fa4cdda7b75...` |
| `b/roots/p7_2026102424_ALT_test/executed_repairs.gif` | p7_2026102424: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `1fbdfad60dda6ee9...` |
| `b/roots/p7_2026102424_ALT_test/order_comparison.gif` | p7_2026102424: same-endpoint order pairs side by side (recorded traces or static status panels) | `7680149ea45174b9...` |
| `b/roots/p7_2026102424_ALT_test/interventions.gif` | p7_2026102424: fixed-robot scene edits (target-only evaluation in the edited scene) | `5ab12e943896d3fe...` |
| `b/roots/p7_2026102424_ALT_test/candidate_orders.gif` | p7_2026102424: every predeclared candidate (arrows numbered by order) and its teacher status | `dcb68a865e40e617...` |
| `b/roots/p7_2026102425_KP_train/scene_start.png` | p7_2026102425: initial scene, roles, goal (dashed), start stratum S0 | `af2b2c8871f45a1c...` |
| `b/roots/p7_2026102425_KP_train/catalogue.png` | p7_2026102425: frozen catalogue with teacher statuses | `897b1b2b76ed22ff...` |
| `b/roots/p7_2026102425_KP_train/executed_repairs.gif` | p7_2026102425: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `73c30acd0dedabc9...` |
| `b/roots/p7_2026102425_KP_train/order_comparison.gif` | p7_2026102425: same-endpoint order pairs side by side (recorded traces or static status panels) | `366d78275ecf2edb...` |
| `b/roots/p7_2026102425_KP_train/interventions.gif` | p7_2026102425: fixed-robot scene edits (target-only evaluation in the edited scene) | `acd921c2f9e57282...` |
| `b/roots/p7_2026102425_KP_train/candidate_orders.gif` | p7_2026102425: every predeclared candidate (arrows numbered by order) and its teacher status | `84d69ced429c4ada...` |
| `b/roots/p7_2026102426_KP_validation/scene_start.png` | p7_2026102426: initial scene, roles, goal (dashed), start stratum S1 | `c688ccaedaa737d5...` |
| `b/roots/p7_2026102426_KP_validation/catalogue.png` | p7_2026102426: frozen catalogue with teacher statuses | `5d7b4fc965e668a2...` |
| `b/roots/p7_2026102426_KP_validation/executed_repairs.gif` | p7_2026102426: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `34cac2eaa9f87f20...` |
| `b/roots/p7_2026102426_KP_validation/order_comparison.gif` | p7_2026102426: same-endpoint order pairs side by side (recorded traces or static status panels) | `937f9d1251d03bce...` |
| `b/roots/p7_2026102426_KP_validation/interventions.gif` | p7_2026102426: fixed-robot scene edits (target-only evaluation in the edited scene) | `9b102da2b4090911...` |
| `b/roots/p7_2026102426_KP_validation/candidate_orders.gif` | p7_2026102426: every predeclared candidate (arrows numbered by order) and its teacher status | `4587f071ed930d73...` |
| `b/roots/p7_2026102427_KP_train/scene_start.png` | p7_2026102427: initial scene, roles, goal (dashed), start stratum S2 | `406bc7ab57f0d908...` |
| `b/roots/p7_2026102427_KP_train/catalogue.png` | p7_2026102427: frozen catalogue with teacher statuses | `3af0900236ea41e1...` |
| `b/roots/p7_2026102427_KP_train/executed_repairs.gif` | p7_2026102427: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `b4972669f915869d...` |
| `b/roots/p7_2026102427_KP_train/order_comparison.gif` | p7_2026102427: same-endpoint order pairs side by side (recorded traces or static status panels) | `f8896cd4e19235ba...` |
| `b/roots/p7_2026102427_KP_train/interventions.gif` | p7_2026102427: fixed-robot scene edits (target-only evaluation in the edited scene) | `f12ff19ab57b99c5...` |
| `b/roots/p7_2026102427_KP_train/candidate_orders.gif` | p7_2026102427: every predeclared candidate (arrows numbered by order) and its teacher status | `163774b882ad1227...` |
| `b/roots/p7_2026102428_KP_test/scene_start.png` | p7_2026102428: initial scene, roles, goal (dashed), start stratum S3 | `fe44cddb562773d8...` |
| `b/roots/p7_2026102428_KP_test/catalogue.png` | p7_2026102428: frozen catalogue with teacher statuses | `0e9ef20e81842ee2...` |
| `b/roots/p7_2026102428_KP_test/executed_repairs.gif` | p7_2026102428: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `a6305e6d798cedf8...` |
| `b/roots/p7_2026102428_KP_test/order_comparison.gif` | p7_2026102428: same-endpoint order pairs side by side (recorded traces or static status panels) | `b833de58c83912e7...` |
| `b/roots/p7_2026102428_KP_test/interventions.gif` | p7_2026102428: fixed-robot scene edits (target-only evaluation in the edited scene) | `a6a3b2d48951964d...` |
| `b/roots/p7_2026102428_KP_test/candidate_orders.gif` | p7_2026102428: every predeclared candidate (arrows numbered by order) and its teacher status | `439ecfb91094d2d0...` |
| `b/roots/p7_2026102429_KM_train/scene_start.png` | p7_2026102429: initial scene, roles, goal (dashed), start stratum S1 | `9138dcbf43bfbac4...` |
| `b/roots/p7_2026102429_KM_train/catalogue.png` | p7_2026102429: frozen catalogue with teacher statuses | `285ec995d1fc4c68...` |
| `b/roots/p7_2026102429_KM_train/executed_repairs.gif` | p7_2026102429: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `393b6f5ae8e206c2...` |
| `b/roots/p7_2026102429_KM_train/order_comparison.gif` | p7_2026102429: same-endpoint order pairs side by side (recorded traces or static status panels) | `ab31dd889f64f4f3...` |
| `b/roots/p7_2026102429_KM_train/interventions.gif` | p7_2026102429: fixed-robot scene edits (target-only evaluation in the edited scene) | `9222f38a391b9986...` |
| `b/roots/p7_2026102429_KM_train/candidate_orders.gif` | p7_2026102429: every predeclared candidate (arrows numbered by order) and its teacher status | `db30b2b9ddbd69f3...` |
| `b/roots/p7_2026102430_KM_validation/scene_start.png` | p7_2026102430: initial scene, roles, goal (dashed), start stratum S2 | `0a9bc476a9567d7e...` |
| `b/roots/p7_2026102430_KM_validation/catalogue.png` | p7_2026102430: frozen catalogue with teacher statuses | `d784055c072fd89c...` |
| `b/roots/p7_2026102430_KM_validation/executed_repairs.gif` | p7_2026102430: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `4410841f6efcd50c...` |
| `b/roots/p7_2026102430_KM_validation/order_comparison.gif` | p7_2026102430: same-endpoint order pairs side by side (recorded traces or static status panels) | `12f2abb748a87520...` |
| `b/roots/p7_2026102430_KM_validation/interventions.gif` | p7_2026102430: fixed-robot scene edits (target-only evaluation in the edited scene) | `de079bfc71a29e3f...` |
| `b/roots/p7_2026102430_KM_validation/candidate_orders.gif` | p7_2026102430: every predeclared candidate (arrows numbered by order) and its teacher status | `11fdd481846351f3...` |
| `b/roots/p7_2026102431_KM_train/scene_start.png` | p7_2026102431: initial scene, roles, goal (dashed), start stratum S3 | `d8aa1296cc286229...` |
| `b/roots/p7_2026102431_KM_train/catalogue.png` | p7_2026102431: frozen catalogue with teacher statuses | `dfa3cf8b8ab73e8a...` |
| `b/roots/p7_2026102431_KM_train/executed_repairs.gif` | p7_2026102431: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `0628a73bd0f53d35...` |
| `b/roots/p7_2026102431_KM_train/order_comparison.gif` | p7_2026102431: same-endpoint order pairs side by side (recorded traces or static status panels) | `e7bbbe514c757e67...` |
| `b/roots/p7_2026102431_KM_train/interventions.gif` | p7_2026102431: fixed-robot scene edits (target-only evaluation in the edited scene) | `e8c542b092e5335f...` |
| `b/roots/p7_2026102431_KM_train/candidate_orders.gif` | p7_2026102431: every predeclared candidate (arrows numbered by order) and its teacher status | `54d695c98d551cc0...` |
| `b/roots/p7_2026102432_KM_test/scene_start.png` | p7_2026102432: initial scene, roles, goal (dashed), start stratum S0 | `eb4c358e6e06741e...` |
| `b/roots/p7_2026102432_KM_test/catalogue.png` | p7_2026102432: frozen catalogue with teacher statuses | `5b4f845240a41db4...` |
| `b/roots/p7_2026102432_KM_test/executed_repairs.gif` | p7_2026102432: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `faa1c1f06d16f2e9...` |
| `b/roots/p7_2026102432_KM_test/order_comparison.gif` | p7_2026102432: same-endpoint order pairs side by side (recorded traces or static status panels) | `2c0bf6e68682f78c...` |
| `b/roots/p7_2026102432_KM_test/interventions.gif` | p7_2026102432: fixed-robot scene edits (target-only evaluation in the edited scene) | `b8fed1c49c7934ce...` |
| `b/roots/p7_2026102432_KM_test/candidate_orders.gif` | p7_2026102432: every predeclared candidate (arrows numbered by order) and its teacher status | `98b296d7a8b21e88...` |
| `b/roots/p7_2026102433_K0_train/scene_start.png` | p7_2026102433: initial scene, roles, goal (dashed), start stratum S2 | `c02da082a60ba423...` |
| `b/roots/p7_2026102433_K0_train/catalogue.png` | p7_2026102433: frozen catalogue with teacher statuses | `00abfac064f4995e...` |
| `b/roots/p7_2026102433_K0_train/executed_repairs.gif` | p7_2026102433: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `59cb41f8d082fe3c...` |
| `b/roots/p7_2026102433_K0_train/order_comparison.gif` | p7_2026102433: same-endpoint order pairs side by side (recorded traces or static status panels) | `8b1e2e4ef18b5341...` |
| `b/roots/p7_2026102433_K0_train/interventions.gif` | p7_2026102433: fixed-robot scene edits (target-only evaluation in the edited scene) | `bddcbc64bb2a68cf...` |
| `b/roots/p7_2026102433_K0_train/candidate_orders.gif` | p7_2026102433: every predeclared candidate (arrows numbered by order) and its teacher status | `41144b17f8542ec5...` |
| `b/roots/p7_2026102434_K0_validation/scene_start.png` | p7_2026102434: initial scene, roles, goal (dashed), start stratum S3 | `a78df36ee4f03e65...` |
| `b/roots/p7_2026102434_K0_validation/catalogue.png` | p7_2026102434: frozen catalogue with teacher statuses | `00a15b221065a912...` |
| `b/roots/p7_2026102434_K0_validation/executed_repairs.gif` | p7_2026102434: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `172e9878ad850285...` |
| `b/roots/p7_2026102434_K0_validation/order_comparison.gif` | p7_2026102434: same-endpoint order pairs side by side (recorded traces or static status panels) | `d3df0a588793f675...` |
| `b/roots/p7_2026102434_K0_validation/interventions.gif` | p7_2026102434: fixed-robot scene edits (target-only evaluation in the edited scene) | `85d54bedb9d3f7c6...` |
| `b/roots/p7_2026102434_K0_validation/candidate_orders.gif` | p7_2026102434: every predeclared candidate (arrows numbered by order) and its teacher status | `becaa08ed36afced...` |
| `b/roots/p7_2026102435_K0_train/scene_start.png` | p7_2026102435: initial scene, roles, goal (dashed), start stratum S0 | `bd60115a0ee820bd...` |
| `b/roots/p7_2026102435_K0_train/catalogue.png` | p7_2026102435: frozen catalogue with teacher statuses | `23adf5c0e8740a95...` |
| `b/roots/p7_2026102435_K0_train/executed_repairs.gif` | p7_2026102435: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `ced3f32523c4baba...` |
| `b/roots/p7_2026102435_K0_train/order_comparison.gif` | p7_2026102435: same-endpoint order pairs side by side (recorded traces or static status panels) | `4f2971befbe2f67e...` |
| `b/roots/p7_2026102435_K0_train/interventions.gif` | p7_2026102435: fixed-robot scene edits (target-only evaluation in the edited scene) | `6e10f6f51c8bafab...` |
| `b/roots/p7_2026102435_K0_train/candidate_orders.gif` | p7_2026102435: every predeclared candidate (arrows numbered by order) and its teacher status | `5ca61e7f9755806f...` |
| `b/roots/p7_2026102436_K0_test/scene_start.png` | p7_2026102436: initial scene, roles, goal (dashed), start stratum S1 | `529254583ee14b17...` |
| `b/roots/p7_2026102436_K0_test/catalogue.png` | p7_2026102436: frozen catalogue with teacher statuses | `c97ec1242f0bf1cb...` |
| `b/roots/p7_2026102436_K0_test/executed_repairs.gif` | p7_2026102436: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `9de504fe00204c4b...` |
| `b/roots/p7_2026102436_K0_test/order_comparison.gif` | p7_2026102436: same-endpoint order pairs side by side (recorded traces or static status panels) | `efde471f663c9124...` |
| `b/roots/p7_2026102436_K0_test/interventions.gif` | p7_2026102436: fixed-robot scene edits (target-only evaluation in the edited scene) | `2272b3613c68e087...` |
| `b/roots/p7_2026102436_K0_test/candidate_orders.gif` | p7_2026102436: every predeclared candidate (arrows numbered by order) and its teacher status | `304d444adcb4d325...` |
| `b/roots/p7_2026102437_ORD_train/scene_start.png` | p7_2026102437: initial scene, roles, goal (dashed), start stratum S3 | `cbbd41c4608481a2...` |
| `b/roots/p7_2026102437_ORD_train/catalogue.png` | p7_2026102437: frozen catalogue with teacher statuses | `b7577eeae2db12c9...` |
| `b/roots/p7_2026102437_ORD_train/executed_repairs.gif` | p7_2026102437: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `61b82395b54b5fbc...` |
| `b/roots/p7_2026102437_ORD_train/order_comparison.gif` | p7_2026102437: same-endpoint order pairs side by side (recorded traces or static status panels) | `81be465362d82365...` |
| `b/roots/p7_2026102437_ORD_train/interventions.gif` | p7_2026102437: fixed-robot scene edits (target-only evaluation in the edited scene) | `2b48e8b640fad005...` |
| `b/roots/p7_2026102437_ORD_train/candidate_orders.gif` | p7_2026102437: every predeclared candidate (arrows numbered by order) and its teacher status | `58e92e4900c857ec...` |
| `b/roots/p7_2026102438_ORD_validation/scene_start.png` | p7_2026102438: initial scene, roles, goal (dashed), start stratum S0 | `08f3bed2de2800d6...` |
| `b/roots/p7_2026102438_ORD_validation/catalogue.png` | p7_2026102438: frozen catalogue with teacher statuses | `4a70a791dc0e68ff...` |
| `b/roots/p7_2026102438_ORD_validation/executed_repairs.gif` | p7_2026102438: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `836121485705bd26...` |
| `b/roots/p7_2026102438_ORD_validation/order_comparison.gif` | p7_2026102438: same-endpoint order pairs side by side (recorded traces or static status panels) | `9fda53a9e614ef49...` |
| `b/roots/p7_2026102438_ORD_validation/interventions.gif` | p7_2026102438: fixed-robot scene edits (target-only evaluation in the edited scene) | `b74e7bec2744b50d...` |
| `b/roots/p7_2026102438_ORD_validation/candidate_orders.gif` | p7_2026102438: every predeclared candidate (arrows numbered by order) and its teacher status | `6e71a380bc648e4b...` |
| `b/roots/p7_2026102439_ORD_train/scene_start.png` | p7_2026102439: initial scene, roles, goal (dashed), start stratum S1 | `fdb60d3f618b0d95...` |
| `b/roots/p7_2026102439_ORD_train/catalogue.png` | p7_2026102439: frozen catalogue with teacher statuses | `2dd5b980bd3beda1...` |
| `b/roots/p7_2026102439_ORD_train/executed_repairs.gif` | p7_2026102439: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `2f5977ffd152f2d1...` |
| `b/roots/p7_2026102439_ORD_train/order_comparison.gif` | p7_2026102439: same-endpoint order pairs side by side (recorded traces or static status panels) | `29d69d189e3fc14a...` |
| `b/roots/p7_2026102439_ORD_train/interventions.gif` | p7_2026102439: fixed-robot scene edits (target-only evaluation in the edited scene) | `5ab61ff3becc54eb...` |
| `b/roots/p7_2026102439_ORD_train/candidate_orders.gif` | p7_2026102439: every predeclared candidate (arrows numbered by order) and its teacher status | `68fa8228067e0408...` |
| `b/roots/p7_2026102440_ORD_test/scene_start.png` | p7_2026102440: initial scene, roles, goal (dashed), start stratum S2 | `db2f9152869c1165...` |
| `b/roots/p7_2026102440_ORD_test/catalogue.png` | p7_2026102440: frozen catalogue with teacher statuses | `eb3cf242b9011884...` |
| `b/roots/p7_2026102440_ORD_test/executed_repairs.gif` | p7_2026102440: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `04671bb555835e1a...` |
| `b/roots/p7_2026102440_ORD_test/order_comparison.gif` | p7_2026102440: same-endpoint order pairs side by side (recorded traces or static status panels) | `4b123307d607fdf2...` |
| `b/roots/p7_2026102440_ORD_test/interventions.gif` | p7_2026102440: fixed-robot scene edits (target-only evaluation in the edited scene) | `42056287cc3b0366...` |
| `b/roots/p7_2026102440_ORD_test/candidate_orders.gif` | p7_2026102440: every predeclared candidate (arrows numbered by order) and its teacher status | `edfe473ec3972e6e...` |
| `b/roots/p7_2026102441_MOT_train/scene_start.png` | p7_2026102441: initial scene, roles, goal (dashed), start stratum S1 | `b1afd1ed80f6952d...` |
| `b/roots/p7_2026102441_MOT_train/catalogue.png` | p7_2026102441: frozen catalogue with teacher statuses | `87c8650ad1727fa5...` |
| `b/roots/p7_2026102441_MOT_train/executed_repairs.gif` | p7_2026102441: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `c148f30d6ea6751e...` |
| `b/roots/p7_2026102441_MOT_train/order_comparison.gif` | p7_2026102441: same-endpoint order pairs side by side (recorded traces or static status panels) | `ee7269fa89ff93ad...` |
| `b/roots/p7_2026102441_MOT_train/interventions.gif` | p7_2026102441: fixed-robot scene edits (target-only evaluation in the edited scene) | `4e541feec957824f...` |
| `b/roots/p7_2026102441_MOT_train/candidate_orders.gif` | p7_2026102441: every predeclared candidate (arrows numbered by order) and its teacher status | `fc98e89e8730601d...` |
| `b/roots/p7_2026102442_MOT_validation/scene_start.png` | p7_2026102442: initial scene, roles, goal (dashed), start stratum S3 | `a6097dbafe7eddf4...` |
| `b/roots/p7_2026102442_MOT_validation/catalogue.png` | p7_2026102442: frozen catalogue with teacher statuses | `0687950ac3f04ee9...` |
| `b/roots/p7_2026102442_MOT_validation/executed_repairs.gif` | p7_2026102442: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `313d1c480c214590...` |
| `b/roots/p7_2026102442_MOT_validation/order_comparison.gif` | p7_2026102442: same-endpoint order pairs side by side (recorded traces or static status panels) | `bc3bd39c173a0410...` |
| `b/roots/p7_2026102442_MOT_validation/interventions.gif` | p7_2026102442: fixed-robot scene edits (target-only evaluation in the edited scene) | `f9642619ce2fa029...` |
| `b/roots/p7_2026102442_MOT_validation/candidate_orders.gif` | p7_2026102442: every predeclared candidate (arrows numbered by order) and its teacher status | `f4fea70cb96f97a0...` |
| `b/roots/p7_2026102443_MOT_train/scene_start.png` | p7_2026102443: initial scene, roles, goal (dashed), start stratum S0 | `86f29f828020df28...` |
| `b/roots/p7_2026102443_MOT_train/catalogue.png` | p7_2026102443: frozen catalogue with teacher statuses | `d64e4170ef8f0139...` |
| `b/roots/p7_2026102443_MOT_train/executed_repairs.gif` | p7_2026102443: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `6708fcf2a9bd3f73...` |
| `b/roots/p7_2026102443_MOT_train/order_comparison.gif` | p7_2026102443: same-endpoint order pairs side by side (recorded traces or static status panels) | `f2c6668bf301c17a...` |
| `b/roots/p7_2026102443_MOT_train/interventions.gif` | p7_2026102443: fixed-robot scene edits (target-only evaluation in the edited scene) | `56f04633cb24eeb8...` |
| `b/roots/p7_2026102443_MOT_train/candidate_orders.gif` | p7_2026102443: every predeclared candidate (arrows numbered by order) and its teacher status | `56d1ff564d1ba76d...` |
| `b/roots/p7_2026102444_MOT_test/scene_start.png` | p7_2026102444: initial scene, roles, goal (dashed), start stratum S1 | `7192137744ea769f...` |
| `b/roots/p7_2026102444_MOT_test/catalogue.png` | p7_2026102444: frozen catalogue with teacher statuses | `cab9a881f9115a44...` |
| `b/roots/p7_2026102444_MOT_test/executed_repairs.gif` | p7_2026102444: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `75a8b83b27d23873...` |
| `b/roots/p7_2026102444_MOT_test/order_comparison.gif` | p7_2026102444: same-endpoint order pairs side by side (recorded traces or static status panels) | `f4cafe05c23c5a07...` |
| `b/roots/p7_2026102444_MOT_test/interventions.gif` | p7_2026102444: fixed-robot scene edits (target-only evaluation in the edited scene) | `c4ba993d08a366e0...` |
| `b/roots/p7_2026102444_MOT_test/candidate_orders.gif` | p7_2026102444: every predeclared candidate (arrows numbered by order) and its teacher status | `a120148a90c324c6...` |
| `b/roots/p7_2026102445_ALT_train/scene_start.png` | p7_2026102445: initial scene, roles, goal (dashed), start stratum S1 | `398acaaea4c9a80d...` |
| `b/roots/p7_2026102445_ALT_train/catalogue.png` | p7_2026102445: frozen catalogue with teacher statuses | `68cbc8f6c12c19c6...` |
| `b/roots/p7_2026102445_ALT_train/executed_repairs.gif` | p7_2026102445: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `6455052b8ccd4024...` |
| `b/roots/p7_2026102445_ALT_train/order_comparison.gif` | p7_2026102445: same-endpoint order pairs side by side (recorded traces or static status panels) | `27ad0c84b41c1476...` |
| `b/roots/p7_2026102445_ALT_train/interventions.gif` | p7_2026102445: fixed-robot scene edits (target-only evaluation in the edited scene) | `7a80df4e9bccef48...` |
| `b/roots/p7_2026102445_ALT_train/candidate_orders.gif` | p7_2026102445: every predeclared candidate (arrows numbered by order) and its teacher status | `ed7b9a1eca98281e...` |
| `b/roots/p7_2026102446_ALT_validation/scene_start.png` | p7_2026102446: initial scene, roles, goal (dashed), start stratum S2 | `78439c66e4f10830...` |
| `b/roots/p7_2026102446_ALT_validation/catalogue.png` | p7_2026102446: frozen catalogue with teacher statuses | `26f7769cc0a1f587...` |
| `b/roots/p7_2026102446_ALT_validation/executed_repairs.gif` | p7_2026102446: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `4366a4651c4efc6e...` |
| `b/roots/p7_2026102446_ALT_validation/order_comparison.gif` | p7_2026102446: same-endpoint order pairs side by side (recorded traces or static status panels) | `3033f00505def4ec...` |
| `b/roots/p7_2026102446_ALT_validation/interventions.gif` | p7_2026102446: fixed-robot scene edits (target-only evaluation in the edited scene) | `6cda32afdefd3a36...` |
| `b/roots/p7_2026102446_ALT_validation/candidate_orders.gif` | p7_2026102446: every predeclared candidate (arrows numbered by order) and its teacher status | `a1c9a398e838b491...` |
| `b/roots/p7_2026102447_ALT_train/scene_start.png` | p7_2026102447: initial scene, roles, goal (dashed), start stratum S3 | `47563ad34b17b5aa...` |
| `b/roots/p7_2026102447_ALT_train/catalogue.png` | p7_2026102447: frozen catalogue with teacher statuses | `f685e8da6e2f9d32...` |
| `b/roots/p7_2026102447_ALT_train/executed_repairs.gif` | p7_2026102447: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `fbb5dcef5ac0b43f...` |
| `b/roots/p7_2026102447_ALT_train/order_comparison.gif` | p7_2026102447: same-endpoint order pairs side by side (recorded traces or static status panels) | `e9249cf40b47e5af...` |
| `b/roots/p7_2026102447_ALT_train/interventions.gif` | p7_2026102447: fixed-robot scene edits (target-only evaluation in the edited scene) | `961376b6b53af1c9...` |
| `b/roots/p7_2026102447_ALT_train/candidate_orders.gif` | p7_2026102447: every predeclared candidate (arrows numbered by order) and its teacher status | `da624a4dc0a787a6...` |
| `b/roots/p7_2026102448_ALT_test/scene_start.png` | p7_2026102448: initial scene, roles, goal (dashed), start stratum S0 | `4253c99723751b10...` |
| `b/roots/p7_2026102448_ALT_test/catalogue.png` | p7_2026102448: frozen catalogue with teacher statuses | `b895bf22c20412ea...` |
| `b/roots/p7_2026102448_ALT_test/executed_repairs.gif` | p7_2026102448: recorded witness trajectories of VERIFIED repairs (main first, <= 4) | `e5e3fde28453304b...` |
| `b/roots/p7_2026102448_ALT_test/order_comparison.gif` | p7_2026102448: same-endpoint order pairs side by side (recorded traces or static status panels) | `0303fbd533296dff...` |
| `b/roots/p7_2026102448_ALT_test/interventions.gif` | p7_2026102448: fixed-robot scene edits (target-only evaluation in the edited scene) | `aaac1e5dd1d7a878...` |
| `b/roots/p7_2026102448_ALT_test/candidate_orders.gif` | p7_2026102448: every predeclared candidate (arrows numbered by order) and its teacher status | `df7935e1016222ff...` |
| `b/models/ABC_side_by_side.gif` | A | B | C (seed 0) on the same sealed P7b test roots: calibrated p_R, selection, per-edit marginals, kappa_hat vs teacher | `deda979e38416785...` |
| `b/models/A_training.gif` | A seed 0: loss curves and recorded validation snapshots over training | `aecf453931959402...` |
| `b/models/B_training.gif` | B seed 0: loss curves and recorded validation snapshots over training | `883d6533bca12ed2...` |
| `b/models/C_training.gif` | C seed 0: loss curves and recorded validation snapshots over training | `eb267c13ae079539...` |
| `b/models/ABC_boltzmann_samples.gif` | A | B | C learned sampling energy on p7_2026102416: exact Boltzmann vs chain samples (G4B kernels) | `f4d57f990cfe27a8...` |
| `b/models/oneshot_episodes.gif` | Independent model-chosen one-shot 2D episodes (A, B, C, uniform), recorded arrays of each episode only | `65748bd205181efa...` |
