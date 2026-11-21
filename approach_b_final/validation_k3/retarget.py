"""Learner-view task reassignment (Experiment C): a new designated target and/or goal for the SAME object geometry, with every task-specific
input field updated consistently (contracts.view2d / view3d semantics):
  2D: tid; attrs[i] = [radius, is_target, is_obstacle, is_fixed] -> is_target / is_obstacle swapped; goal_cell, goal (x, y), ctx[6:8] = goal (x, y)
  3D: tid; attrs[i][4] = is_target; goal_cell, goal, ctx[14:16] = goal (x, y), ctx[16:19] = new target (size, height, is_box)
Robot reference pose, gripper gap, legal cells, object cells / geometry unchanged.  The identity reassignment returns the input exactly."""
import copy

GOAL_IDX = {"2d": (6, 7), "3d": (14, 15)}


def retarget(inp, dom, tid=None, goal_cell=None):
    new = copy.deepcopy(inp)
    old = inp["tid"]
    if goal_cell is not None:
        g = int(goal_cell)
        new["goal_cell"] = g
        new["goal"] = list(map(float, inp["cell_xy"][str(g)]))
        i, j = GOAL_IDX[dom]
        new["ctx"][i], new["ctx"][j] = new["goal"]
    if tid is not None and int(tid) != old:
        t = int(tid)
        assert t != old and 0 <= t < len(inp["ids"])
        if dom == "2d":
            assert not inp["attrs"][t][3], "a fixed object cannot become the target"
            new["attrs"][t][1], new["attrs"][t][2] = 1.0, 0.0
            new["attrs"][old][1], new["attrs"][old][2] = 0.0, 1.0
        else:
            new["attrs"][t][4], new["attrs"][old][4] = 1.0, 0.0
            a = inp["attrs"][t]
            new["ctx"][16:19] = [a[2], a[3], a[0]]
        new["tid"] = t
    return new


def selftest(rows, dom):
    """identity -> exact equality; round trip A -> B -> A -> exact equality."""
    bad = 0
    for r in rows:
        inp = r["inputs"]
        if retarget(inp, dom, inp["tid"], inp["goal_cell"]) != inp:
            bad += 1
        mv = [i for i in range(len(inp["ids"])) if i != inp["tid"] and not (dom == "2d" and inp["attrs"][i][3])]
        if mv:
            b = retarget(inp, dom, mv[0], None)
            if retarget(b, dom, inp["tid"], inp["goal_cell"]) != inp:
                bad += 1
    return {"rows": len(rows), "failures": bad}
