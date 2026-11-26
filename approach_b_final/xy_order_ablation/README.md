# Structured-energy readout and execution-order ablation (RSS RQ2a/b)

`plan.md` (v1.0) is the controlling protocol and `starting_prompt.md` the owner prompt; both are byte copies. `protocol.json` holds the frozen decisions and `AMENDMENTS.md` every change to them. Reports are in `reports/`.

| File | Role |
|---|---|
| `readout.py` | Planner side: frozen J/X/Y/XC readouts and the shared streamed selectors (public rows + bundle only) |
| `labels.py` | Evaluator side: exact-contract label ledger (strict / operational, quarantine) |
| `ordering.py` | Matched-order metrics (concordance, learned / canonical / random / oracle) |
| `run.py` | Audit, panel, parity, inference, seal, teacher, statistics CLI |
| `stats.py` | Discrimination metrics, family bootstrap, sign-flip randomization, Holm |
| `viz.py` | Figures (`reports/figures/`) |
| `tests/test_contracts.py` | Contract tests (CPU) |

**Result:** `reports/P4_FINAL_DECISION.md` and `reports/paper_tables.md`.

```
python run.py audit && python run.py panel
XYO_DEVICE=cpu python -m pytest tests -q                    # 14 passed
python run.py parity 2d && python run.py parity 3d
python run.py dev 2d && python run.py dev 3d
for d in 2d 3d; do python run.py infer $d; python run.py panel_score $d; done
python run.py seal && python run.py manifest                # commit + push before teacher
python run.py teach 3d 20; python run.py teach 3d; python run.py teach 2d
python run.py analyze && python viz.py
```
