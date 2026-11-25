# Amendments to plan.md / P0_PREREG.md (append-only)

None of these used held-out outcomes.

1. **2026-11-26, P0 (pre-registered):** training follows the released sampler's fixed-step budget (2D 2,400 / 3D 1,520 steps), not 80 epochs / patience 15. The roster is 50 K1 / 50 K2 / 50 K3 / 30 K0 / 30 NONE per domain. Audit code lives in `p0_audit.py`. Storage was capped at 1 GB by the owner.
2. **2026-11-26, P2 (DEV):** the full C0 run on 2D VAL took 5–15 s per large root. After 300 roots it was stopped, and the remaining 451 roots got C0 proposals and exact pool size only (`infer.py --c0props`). This affects DEV C0 decisions and timing only; recall, pool size and off-top-4 rate cover all 751 roots.
3. **2026-11-26, P2 (DEV):** a duplicate DEV writer had started by accident; it was stopped by PID. Its 40 duplicate rows were identical in pool hash and every decision, and were removed (raw file kept).
4. **2026-11-26, P4:** a secondary physical tier was added after primary coverage was complete, within the authorized 450 queries per domain. It covers K1–K3 picks of C1_common_gate, then C4, then C3, whole roots by sha256(`CRCVAE_QSEC_V1|root`). Its manifest was committed (`91e87fa423`) before the queries ran. 57 2D C3 picks were not queried because of the cap.
5. **2026-11-26, P5:** known-witness coverage on the cohort uses two sources: the generator's legacy-protocol witnesses (`labels.B`, y = 1) and finalized verified picks of any arm. Coverage from legacy witnesses alone is reported as the unbiased lower bound.
