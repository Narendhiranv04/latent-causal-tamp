# fig3_retarget: faithful Fig. 3(a) recursive retargeting with home-anchored chunking (R1)

This package holds the planner and the physical adapters for the Fig. 3 study. The R1 report is `reports/R1_REPORT.md`.

## Inference side (planner only: PUBLIC rows and the frozen bundle)

| File | Contents |
|---|---|
| `views.py` | Retargets and rebases views; masks and grammar. |
| `models.py` | Counted, cached frozen readouts. |
| `rank.py` | E_home, with a DP over chunks of 1–3 actions; B0. |
| `recursive.py` | The R-FIG3, R-GATED, F-FLAT and R-TOPO arms. |
| `run.py` | Parity runs and model-only demos. |

## Evaluator side (teachers)

| File | Contents |
|---|---|
| `physical3d.py` | 3D adapter on SHELF66V3 (`fin3d`) with CONNECTOR_TO_QREADY_V1. |
| `physical2d.py` | 2D adapter built on the BXY teacher primitives. |
| `tt_adapter.py` | TT_ADAPTER_V1, copied verbatim from `e9fa587c3b`. |
| `jobs.py` | Smoke-job builders. |
| `viz.py` | Figures. |

## Tests

    cd fig3_retarget && python -m pytest tests/test_fig3.py
