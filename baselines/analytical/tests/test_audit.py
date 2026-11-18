"""Machine checks behind AUDIT.md: provenance of the legacy copy, the verified legacy defects (exact lines), and the presence of each fix."""
import re
import subprocess
from pathlib import Path

import pytest

H = Path(__file__).resolve().parents[1]
LEG = H / "legacy_2d_14ade19a"

BLOBS = {"README.md": "83d6fc9395876b0d4d6916b1c639b91058fea8c2", "RESULTS.md": "0d6afbb76dba1f5a90bb422cbbed4a9e672fbb28",
         "b2d/common.py": "b9db3ef27a4b505b03433cfa634b8507d9232fc2", "b2d/em4m2d.py": "53622d51bbf6f9e203de9d6bd67f4285b8603cb4",
         "b2d/mosegman.py": "c609474dedb49bb3dabb03ebdf8ca3ec73adf860", "b2d/msmcts.py": "69c8b272571b91313333bbfefba394731c438ae8",
         "b2d/teacher.py": "5887c6cc94994021636442db69332f41c278f5af", "b2d/run.py": "4f8fa5157002fee8b9c36c9b0ab71d671cbe89a9",
         "b2d/paths.py": "72a5bf5c90f3f915b72553d3e97b04b1340ffd11"}

# AUDIT.md claim id -> (legacy file, line, exact text on that line)
DEFECTS = {
    "D1a": ("em4m2d.py", 186, "key = tuple(sorted(cells.items()))"),
    "D1b": ("em4m2d.py", 191, "prev.parent, prev.seq, prev.q = v, v.seq + [(o, g)], r[0]"),
    "D2a": ("mosegman.py", 124, "return not [o for o in target_blockers(self.m, self.gamma, cells) if o not in removed]"),
    "D2b": ("mosegman.py", 283, "objs = [o for o in objs if o not in crit]"),
    "D3a": ("msmcts.py", 179, "return self.reward(cur.seq) if self.goal_ok(cur) else -FAIL_R"),
    "D3b": ("msmcts.py", 63, "k = (o, cells[o])"),
    "D3c": ("msmcts.py", 36, "M_REGIONS, MAX_TRIES, STUCK_DEPTH, FAIL_R = 2, 4, 2, 4.0"),
    "D4a": ("em4m2d.py", 158, "agents = sorted(o for o in self.ngr_objects(v.cells) if o not in moved)"),
    "D4b": ("msmcts.py", 116, "ob = [o for o in tb if o not in moved]"),
    "D4c": ("mosegman.py", 231, 'if b not in n.objs and b != "t0":'),
    "D4d": ("common.py", 31, "return [c for c in m.legal if c not in occ]"),
    "D4e": ("common.py", 18, "MAX_RELOC = 4"),
    "D4f": ("common.py", 45, 'return m.blockers(gamma, "t0", m.cells0["t0"], cells, [o for o in cells if o != "t0"])'),
    "D5": ("run.py", 127, 'v = TT.verify(rec, row["seq"], sh.cache)'),
    "D6": ("paths.py", 7, 'WORK = Path(os.environ.get("B2D_WORK", "/work"))'),
    "D7": ("teacher.py", 103, 'self.movable = sorted(rec["roles"])'),
}

# AUDIT.md fix id -> (new file, regex that must be present)
FIXES = {
    "F1": ("em4m.py", r'return self\.ph\.key\(s\) if self\.P\["transposition"\] == "physical"'),
    "F2a": ("mosegman.py", r"for p, b in self\.path_blockers\(s\):"),
    "F2b": ("mosegman.py", r"self\.refresh\(node\)"),
    "F2c": ("mosegman.py", r'for crit, path in alts\[:self\.P\["sgfs_attempts"\]\]'),
    "F3a": ("msmcts.py", r'return "REPAIR", plan, "objective achieved in rollout"'),
    "F3b": ("msmcts.py", r"k = \(tuple\(self\.ph\.cells\(s\)\), o\)"),
    "F3c": ("msmcts.py", r"if k in self\.table:"),
    "F4a": ("contract.py", r"int\(d\) not in occ0 and int\(d\) not in occ and int\(d\) != g"),
    "F4b": ("contract.py", r"^K_MAX = 3$"),
    "F4c": ("phys.py", r"legality\(self\.inp, self\.dom, prefix\) is not None"),
    "F5": ("eval.sh", r"benchmark\.py teach"),
    "F6": ("envs.py", r'os\.environ\.get\("ANALYTICAL_WORKTREES"'),
    "F7": ("envs.py", r'clean\["roles"\] = \{ids\[i\]: "movable"'),
}


@pytest.mark.parametrize("f,blob", sorted(BLOBS.items()))
def test_legacy_copy_is_verbatim(f, blob):
    out = subprocess.run(["git", "hash-object", str(LEG / f)], capture_output=True, text=True).stdout.strip()
    assert out == blob


@pytest.mark.parametrize("cid", sorted(DEFECTS))
def test_legacy_defect_lines(cid):
    f, n, text = DEFECTS[cid]
    assert (LEG / "b2d" / f).read_text().splitlines()[n - 1].strip().startswith(text)


@pytest.mark.parametrize("fid", sorted(FIXES))
def test_fix_present(fid):
    f, rx = FIXES[fid]
    assert re.search(rx, (H / f).read_text(), re.M), (fid, f)


def test_audit_md_lists_every_claim():
    md = (H / "AUDIT.md").read_text()
    for cid in list(DEFECTS) + list(FIXES):
        assert f"**{cid}**" in md, cid
