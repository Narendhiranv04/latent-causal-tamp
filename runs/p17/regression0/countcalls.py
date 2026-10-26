"""G4C-LF-P4 regression helper (pytest plugin): counts in-process planner/skill calls per test
file and records each test outcome, flushing after every test so a guard kill loses nothing."""
import collections
import json
import os
import sys

COUNTS = collections.Counter()
CUR = {"file": None}


def _wrap(mod, fn):
    real = getattr(mod, fn)

    def w(*a, **k):
        COUNTS[(CUR["file"], f"{mod.__name__}.{fn}")] += 1
        return real(*a, **k)
    setattr(mod, fn, w)


def pytest_configure(config):
    sys.path.insert(0, os.getcwd())
    import planner
    import skill
    _wrap(planner, "plan")
    _wrap(skill, "plan_skill")


def pytest_runtest_setup(item):
    CUR["file"] = item.fspath.basename


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        with open(os.environ["PROGRESS"], "a") as fh:
            fh.write(json.dumps({"test": report.nodeid, "outcome": report.outcome}) + "\n")
        by = collections.defaultdict(dict)
        for (f, k), v in COUNTS.items():
            by[f][k] = v
        tmp = os.environ["COUNT_OUT"] + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(by, fh, indent=1, sort_keys=True)
        os.replace(tmp, os.environ["COUNT_OUT"])
