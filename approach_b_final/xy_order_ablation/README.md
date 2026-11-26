# Structured-energy readout and execution-order ablation (RSS RQ2a/b)

`plan.md` (v1.0) is the controlling protocol and `starting_prompt.md` the owner prompt; both are byte copies. `protocol.json` holds the frozen decisions and `AMENDMENTS.md` every change to them. Reports are in `reports/`.

| File | Role |
|---|---|
| `readout.py` | Planner side: frozen J/X/Y/XC readouts and the shared streamed selectors (public rows + bundle only) |
| `labels.py` | Evaluator side: exact-contract label ledger (strict / operational, quarantine) |
| `ordering.py` | Matched-order metrics (concordance, learned / canonical / random / oracle) |
| `run.py` | Audit, panel, parity, inference, seal, teacher, statistics CLI |
| `tests/test_contracts.py` | Contract tests (CPU) |

```
python run.py audit && python run.py panel
XYO_DEVICE=cpu python -m pytest tests -q
```
