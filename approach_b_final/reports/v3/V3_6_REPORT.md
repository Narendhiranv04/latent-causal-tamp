# V3-6: final test evaluation (2D and 3D)

## Protocol

- **Split.** TEST: 749 2D and 370 3D roots; task roots n = 412 / 241.
- **Rules.** Frozen on validation in V3-5 (`v3_5/rule_*.json`); V2-scorer arms keep the frozen V2 rule. Nothing was tuned on test.
- **Generation.** Every arm uses the direct one-shot construction of V3-1 (M = 4, B = 4,096), except the old V2 iterative baseline. That baseline was regenerated on gvlab2 with the frozen V2 models; earlier parity checks showed identical candidate sets and selections.
- **Verification.** Every selected repair of every arm and seed was physically verified by the unchanged finalized teachers, with 0 unverified. Hosts were gvlab2, gvlab and the laptop, with parity-checked teacher copies and deterministic root sharding.
- **Seeds.** The primary arm and the V2 baseline are seed-averaged over 3 seeds; the other arms use seed 0.
- **Statistics.** The paired root-cluster bootstrap (2,000 resamples) compares per-root seed-averaged outcomes.
- **Exposure caveat (plan §6.3).** The test roots were used for V1 / V2 reporting. V3 made every choice (sampler, scorer, rule) on validation only, but this is not a fresh cohort.

## Results (`v3_6/TABLE_TEST.json`, `v3_6/TRAVEL_TEST.json`, `v3_6/test_top1.png`)

| 2D test | Task | K1 / K2 / K3 | Repair | No-op | Abstain | Δ task vs primary [95 % CI] | Δ task vs V2 iterative | Travel J (successes) |
|---|---:|---|---:|---:|---:|---|---|---:|
| **V3 primary: task cVAE + V3 D** (3 seeds) | **43.6** | 72 / 61 / 12 | 20.7 | 89.7 | 92.7 | — | **+18.0 [+14.6, +21.4]** | 5.29 |
| Old V2 iterative (Q2 cVAE + V2 D) (3 seeds) | 25.6 | 51 / 30 / 5 | 18.4 | 90.4 | 94.0 | −18.0 [−21.2, −14.7] | — | 4.35 |
| E: task cVAE + V2 D (frozen) | 20.4 | 46 / 20 / 3 | 12.3 | 88.2 | 68.7 | −23.2 [−27.6, −19.0] | −5.3 [−9.1, −1.5] | 4.62 |
| E: Q2 cVAE + V3 D | 29.4 | 66 / 31 / 3 | 15.8 | 88.8 | 95.3 | −14.2 [−18.1, −10.3] | +3.7 [−0.6, +7.7] | 4.65 |
| E: Q2 cVAE + V2 D (V3-1 direct) | 20.4 | 50 / 19 / 1 | 13.1 | 88.2 | 95.3 | −23.2 [−27.8, −18.9] | −5.3 [−9.0, −1.6] | 4.20 |
| F: task cVAE + V3 E (uncoupled) | 43.7 | 70 / 61 / 13 | 16.0 | 89.8 | 96.0 | +0.1 [−3.6, +4.0] | +18.0 [+13.9, +22.4] | 5.56 |
| F: task cVAE + V3 G (order-invariant) | 40.8 | 68 / 58 / 9 | 24.0 | 90.9 | 87.3 | −2.8 [−6.5, +0.9] | +15.1 [+10.9, +19.3] | 5.11 |
| F: task cVAE + V3 DIRECT | 30.6 | 46 / 48 / 8 | 7.2 | 87.2 | 59.3 | −13.0 [−17.1, −8.7] | +4.9 [+0.6, +9.5] | 5.70 |
| Control: uniform + V3 D | 34.0 | 57 / 52 / 5 | 18.5 | 88.8 | 95.3 | −9.6 [−13.7, −5.5] | +8.3 [+4.3, +12.4] | 4.87 |
| Control: band-stratified + V3 D | 21.6 | 48 / 25 / 1 | 9.6 | 88.8 | 91.3 | −22.0 [−25.8, −18.4] | −4.0 [−8.1, −0.1] | 4.49 |
| Control: goal-ablated repair cVAE + V3 D | 38.8 | 66 / 52 / 10 | 23.5 | 88.8 | 88.7 | −4.8 [−8.5, −1.0] | +13.2 [+9.1, +17.3] | 5.13 |

| 3D test | Task | K1 / K2 / K3 | Repair | No-op | Abstain | Δ task vs primary [95 % CI] | Δ task vs V2 iterative | Travel J (successes) |
|---|---:|---|---:|---:|---:|---|---|---:|
| **V3 primary: task cVAE + V3 D** (3 seeds) | **77.3** | 80 / 79 / 74 | **56.0** | 77.6 | 76.9 | — | **+24.9 [+20.1, +29.3]** | 10.32 |
| Old V2 iterative (Q2 cVAE + V2 D) (3 seeds) | 52.4 | 67 / 53 / 44 | 38.0 | 78.1 | 84.4 | −24.9 [−29.5, −20.3] | — | 10.26 |
| E: task cVAE + V2 D (frozen) | 68.9 | 68 / 70 / 69 | 46.2 | 73.1 | 45.2 | −8.4 [−14.2, −3.0] | +16.5 [+10.8, +22.5] | 10.58 |
| E: Q2 cVAE + V3 D | 60.6 | 70 / 69 / 49 | 40.8 | 62.7 | 100 | −16.7 [−23.1, −10.2] | +8.2 [+1.9, +14.8] | 10.35 |
| E: Q2 cVAE + V2 D (V3-1 direct) | 53.5 | 64 / 55 / 47 | 37.8 | 73.1 | 90.3 | −23.8 [−30.6, −17.2] | +1.1 [−4.7, +6.8] | 10.22 |
| F: task cVAE + V3 E (uncoupled) | 80.1 | 70 / 86 / 80 | 52.9 | 88.1 | 71.0 | +2.8 [−1.9, +7.6] | +27.7 [+22.1, +33.5] | 10.63 |
| F: task cVAE + V3 G (order-invariant) | 61.4 | 81 / 71 / 43 | 45.0 | 73.1 | 93.5 | −15.9 [−21.7, −10.0] | +9.0 [+2.6, +15.2] | 9.81 |
| F: task cVAE + V3 DIRECT | 68.0 | 79 / 79 / 53 | 50.4 | 73.1 | 45.2 | −9.3 [−15.1, −3.6] | +15.6 [+9.5, +21.4] | 10.13 |
| Control: uniform + V3 D | 50.2 | 62 / 47 / 47 | 35.7 | 62.7 | 95.2 | −27.1 [−33.7, −20.3] | −2.2 [−8.4, +4.6] | 10.42 |
| Control: band-stratified + V3 D | 54.8 | 68 / 56 / 47 | 38.7 | 62.7 | 96.8 | −22.5 [−29.0, −16.3] | +2.4 [−3.7, +8.3] | 10.48 |
| Control: goal-ablated repair cVAE + V3 D | 74.7 | 75 / 77 / 73 | 54.2 | 62.7 | 88.7 | −2.6 [−7.2, +2.4] | +22.3 [+16.0, +28.4] | 10.34 |

Notes on the columns:
- Latency (median per root, construction + scoring, 0 planner calls): primary 0.32 s (2D) and 0.12 s (3D); V2 iterative 0.25 / 0.22 s.
- No-op and abstain are protocol-relative: correct no-op on legacy K0 roots, and correct abstention on legacy NONE roots.
- Travel is witnessed J_complete over verified successes, with 100 % witness coverage in every arm. It is computed per arm over different success sets, so it is descriptive and not paired.

## Interpretation

1. **The V3 method beats the old V2 iterative search by a wide margin** in both domains:
   - 2D: +18.0 points, CI [+14.6, +21.4]. K2 rises from 30 to 61 % and K3 from 5 to 12 %.
   - 3D: +24.9 points, CI [+20.1, +29.3]. K3 rises from 44 to 74 %, and Repair (exactly the certified K) from 38.0 to 56.0 %.
   - It needs a single sampler pass and no hypothetical re-querying, at a similar or lower latency.
2. **Both learned components are necessary (experiment E, the 2×2).**
   - The repair-trained sampler helps only once the scorer is retrained on its candidates. With the frozen V2 scorer it drops to 20.4 % in 2D and collapses NONE abstention: 69 % in 2D and 45 % in 3D.
   - A retrained scorer with the old Q2 sampler reaches only 29.4 % (2D) and 60.6 % (3D).
   - Primary minus each single change is −14 to −23 points (2D) and −8 to −17 points (3D).
   - This is the sampler / scorer distribution coupling predicted in plan §5.1, confirmed on test.
3. **Coupling (F5) gives no measurable benefit.** The uncoupled E matches D: 2D +0.1 [−3.6, +4.0], 3D +2.8 [−1.9, +7.6], although E abstains less in 3D (71.0 vs 76.9 %). D remains the declared main model; the null result is reported, consistent with V1 / V2.
4. **Order modelling matters, especially in 3D.** The order-invariant G loses 15.9 points in 3D, with K3 at 43 vs 74 %, and 2.8 points in 2D (n.s.). Its matched-endpoint order accuracy is 0.50 vs 0.79–0.81 for D (V3-5).
5. **The direct binary-success predictor is worse.** DIRECT loses 13.0 (2D) and 9.3 (3D) points, and abstains poorly: 59 % in 2D and 45 % in 3D.
6. **Repair supervision is the main source of the sampler gain; goal conditioning adds a little.**
   - The goal-ablated repair cVAE is −4.8 [−8.5, −1.0] in 2D (significant) and −2.6 [−7.2, +2.4] in 3D (n.s.).
   - Broad analytic proposals (uniform or band-stratified) fall far behind with the same V3 scorer.
7. **Residual weaknesses:**
   - 2D K3 remains hard (12 %).
   - 3D abstention and no-op are slightly lower than the V2 iterative arm (76.9 vs 84.4 % and 77.6 vs 78.1 %). This reflects the repair-like candidate pool, even with the retrained scorer.
   - 2D successful repairs travel more on average (5.29 vs 4.35). V3 solves many more K2 / K3 problems, which need more moves, and γ = 0 was selected on validation, so no travel optimisation is claimed.

## Limitations

- **Test-split exposure:** see Protocol above.
- **Single-seed arms.** Ablation and control arms use seed 0; the primary and V2 arms use 3 seeds. CIs reflect root sampling, not seed variance, for single-seed arms.
- **Fixed budget.** Results hold at M = 4 and B = 4,096; a full budget curve was not run on test.
- **Protocol-relative NONE.** Abstention on NONE is protocol-relative. No new repair was found on 100 TRAIN NONE roots (V3-4), but that is not a proof of impossibility.
- **V3-7 not run.** The teammate-data extension was dropped by the user, and V3-8 options (adaptive M, rank loss) were not needed.
