import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: real-root physics checks (subprocess, minutes; set ANALYTICAL_SKIP_SLOW=1 to skip)")
