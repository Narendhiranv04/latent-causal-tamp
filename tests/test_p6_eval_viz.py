"""P6 evaluation metrics, baselines and GIF writer (synthetic inputs; no teacher, no training data)."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import p6_train as pt  # noqa: E402
import p6_viz as pv  # noqa: E402


def _ev(ps, ys, ms):
    cands = [{"query": f"q{i}", "p": p, "y": y, "m": m, "energy": -p} for i, (p, y, m) in enumerate(zip(ps, ys, ms))]
    return {"root": "k", "cands": cands, "effects": [{"kind": "scene", "pred": 0.2, "observed": 1}],
            "order_pairs": [{"orders": ["q1", "q2"], "y": [1, 0], "p": [0.9, 0.1]}], "rank_acc": 1.0, "selected_label": 1}


def test_metrics_auc_order_and_masking():
    m = pt.metrics([_ev([0.9, 0.8, 0.1, 0.3], [1, 1, 0, None], [0, 2, 2, 1])])
    assert m["decided"] == 3 and m["accuracy"] == 1.0 and m["auroc"] == 1.0 and m["order_accuracy"] == 1.0
    assert abs(m["effect_mae"]["scene"] - 0.8) < 1e-12 and m["effect_mae"]["omission"] is None
    assert pt._auc(np.array([1, 0]), np.array([0.4, 0.4])) == 0.5
    u = pt.uniform_baseline([_ev([0.5] * 3, [1, 0, 0], [1, 1, 2])])
    assert abs(u["expected_selection_success"] - 1 / 3) < 1e-12


def test_gif_frame_rate_hold_and_hash(tmp_path):
    pv.INDEX.clear()
    frames = [np.full((20, 20, 3), i * 40, np.uint8) for i in range(4)]
    pv.gif(tmp_path / "x.gif", frames, "synthetic")
    im = Image.open(tmp_path / "x.gif")
    durs = []
    for i in range(im.n_frames):
        im.seek(i)
        durs.append(im.info["duration"])
    assert durs[:-1] == [pv.FRAME_MS] * 3 and durs[-1] >= 1000 and 1000 / pv.FRAME_MS in range(8, 13)
    assert (tmp_path / "x.gif.sha256").read_text().strip() == pv.INDEX[0]["sha256"]
