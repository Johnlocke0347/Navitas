"""Checker tests: baseline has 0 violations, hand-broken schedule is caught."""
import pathlib
import sys
from engine.engine import check, baseline_edf, TM, day_ok, DAY, T
from engine.load import instances, TASK_MODES, MACH_MODES

def test_baseline_zero_violations():
    base = baseline_edf()
    v = check(base)
    assert len(v) == 0, f"baseline should have 0 violations, got {v}"
    assert len(base) == len(instances) == 275
def _make_broken_schedule():
    """Return a copy of baseline mutated to have 3 violations:
    - overlap on same machine
    - missed deadline (deadline 960)
    - Harden[2] before Harden[1.5] (order)
    """
    base = baseline_edf()
    sched = [list(x) for x in base]
    by_i = {i: idx for idx, (i, m, tm, s) in enumerate(base)}
    from collections import defaultdict
    by_m = defaultdict(list)
    for idx, (i, m, tm, s) in enumerate(base):
        by_m[m].append(idx)
    overlap_m = None
    for m, idxs in by_m.items():
        if len(idxs) >= 2:
            overlap_m = m
            break
    assert overlap_m is not None
    idxs = sorted(by_m[overlap_m], key=lambda k: base[k][3])
    first_idx = idxs[0]
    second_idx = idxs[1]
    first_start = base[first_idx][3]
    sched[second_idx][3] = first_start
    deadline_i = None
    for i, ins in enumerate(instances):
        if ins["deadline"] == 960:
            deadline_i = i
            break
    assert deadline_i is not None
    d_idx = by_i[deadline_i]
    tm_d = sched[d_idx][2]
    d_len = len(TM[tm_d])
    s_bad = 1050
    if not day_ok(s_bad, d_len) or s_bad + d_len > T:
        s_bad = 1000
        assert day_ok(s_bad, d_len) and s_bad + d_len <= T
    assert s_bad + d_len > 960
    sched[d_idx][3] = s_bad
    h2_ids = [i for i, ins in enumerate(instances) if ins["task"] == "Harden[2]"]
    h15_ids = [i for i, ins in enumerate(instances) if ins["task"] == "Harden[1.5]"]
    assert h2_ids and h15_ids
    h2_sched_idxs = [by_i[i] for i in h2_ids if i in by_i]
    h15_sched_idxs = [by_i[i] for i in h15_ids if i in by_i]
    h2_idx = h2_sched_idxs[0]
    h15_idx = h15_sched_idxs[0]
    h2_tm = sched[h2_idx][2]
    h15_tm = sched[h15_idx][2]
    h2_len = len(TM[h2_tm])
    h15_len = len(TM[h15_tm])
    s_h2_new = 10
    s_h15_new = 50
    assert day_ok(s_h2_new, h2_len) and day_ok(s_h15_new, h15_len)
    sched[h2_idx][3] = s_h2_new
    sched[h15_idx][3] = s_h15_new
    broken = [(int(i), m, tm, int(s)) for (i, m, tm, s) in sched]
    return broken, {
        "overlap_m": overlap_m,
        "overlap_pair": (first_idx, second_idx),
        "deadline_i": deadline_i,
        "deadline_s": s_bad,
        "h2_i": h2_ids[0],
        "h15_i": h15_ids[0],
    }

def test_hand_broken_is_caught():
    broken, info = _make_broken_schedule()
    v = check(broken)
    assert len(v) >= 3, f"broken schedule should have >=3 violations, got {v}"
    assert any(t[0] == "overlap" for t in v), f"overlap not caught, {v}"
    assert any(t[0] == "deadline" for t in v), f"deadline not caught, {v}"
    assert any(t[0] == "deadline" and t[1] == info['deadline_i'] for t in v), f"deadline for {info['deadline_i']} not found {v}"
    assert any(t[0] == "order H1.5->H2" for t in v), f"order H1.5->H2 not caught, {v}"
    assert not any(t[0] == "missing-tasks" for t in v)

def test_overlap_individually():
    base = baseline_edf()
    by_m = {}
    for idx, (i, m, tm, s) in enumerate(base):
        by_m.setdefault(m, []).append((s, idx))
    for m, lst in by_m.items():
        if len(lst) >= 2:
            lst.sort()
            _, first_idx = lst[0]
            _, second_idx = lst[1]
            break
    sched = [list(x) for x in base]
    sched[second_idx][3] = sched[first_idx][3]
    broken = [(int(i), m, tm, int(s)) for (i, m, tm, s) in sched]
    v = check(broken)
    assert any(t[0] == "overlap" and t[1] == m for t in v)

def test_deadline_individually():
    base = baseline_edf()
    target = None
    for idx, (i, m, tm, s) in enumerate(base):
        if instances[i]["deadline"] == 960:
            target = idx
            break
    assert target is not None
    d_len = len(TM[base[target][2]])
    sched = [list(x) for x in base]
    s_bad = 1100 if day_ok(1100, d_len) else 1000
    sched[target][3] = s_bad
    broken = [(int(i), m, tm, int(s)) for (i, m, tm, s) in sched]
    v = check(broken)
    assert any(t[0] == "deadline" for t in v)

def test_harden_order_individually():
    base = baseline_edf()
    h2_idx = None
    h15_idx = None
    for idx, (i, m, tm, s) in enumerate(base):
        if instances[i]["task"] == "Harden[2]" and h2_idx is None:
            h2_idx = idx
        if instances[i]["task"] == "Harden[1.5]" and h15_idx is None:
            h15_idx = idx
    assert h2_idx is not None and h15_idx is not None
    sched = [list(x) for x in base]
    sched[h2_idx][3] = 0
    sched[h15_idx][3] = 50
    broken = [(int(i), m, tm, int(s)) for (i, m, tm, s) in sched]
    v = check(broken)
    assert any(t[0] == "order H1.5->H2" for t in v)
