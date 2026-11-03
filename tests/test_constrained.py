from engine.constrained import *
from engine.engine import check, baseline_edf, cost, load_profile


def test_time_helpers():
    assert hhmm_to_k("07:00") == 0 and hhmm_to_k("18:30") == 138 and hhmm_to_k("22:30") == 186 and hhmm_to_k("23:00") == 192
    assert k_to_hhmm(138) == "18:30"


def test_default_price_matches_tariff():
    p = make_price()
    assert abs(p[0] * 1000 - 22.83) < 1e-9 and abs(p[138] * 1000 - 35.68) < 1e-9 and abs(p[186] * 1000 - 22.83) < 1e-9


def test_normalize_rejects_bad_input():
    _, _, _, errs = normalize([{"type": "machine_down", "machine": "MAQ999", "day": 3}, {"type": "machine_down", "machine": "MAQ119", "day": 9},
                               {"type": "avoid_window", "task": "Nope", "start": "18:00", "end": "19:00"}, {"type": "avoid_window", "task": "*", "start": "20:00", "end": "19:00"}, {"type": "x"}])
    assert len(errs) == 5


def test_normalize_expands_windows():
    clean, bm, bt, errs = normalize([{"type": "machine_down", "machine": "MAQ119", "day": 3}, {"type": "avoid_window", "task": "Harden[2]", "start": "18:30", "end": "22:30"}])
    assert not errs and bm["MAQ119"] == [(384, 576)] and len(bt["Harden[2]"]) == 6 and bt["Harden[2]"][0] == (138, 186)


def test_baseline_unconstrained_equals_verified_baseline():
    b = baseline_blocked({}, {})
    assert check(b) == [] and abs(cost(b, make_price()) - cost(baseline_edf(), make_price())) < 1e-6


def test_baseline_respects_user_constraints():
    clean, bm, bt, _ = normalize([{"type": "machine_down", "machine": "MAQ119", "day": 3}, {"type": "avoid_window", "task": "Ironing", "start": "21:00", "end": "22:30"}])
    b = baseline_blocked(bm, bt)
    assert b is not None and check(b) == [] and check_constraints(b, bm, bt) == []


def test_check_constraints_catches_violation():
    clean, bm, bt, _ = normalize([{"type": "machine_down", "machine": "MAQ120", "day": 1}])
    b = baseline_edf()                      # the plain schedule uses MAQ120 on day 1
    assert len(check_constraints(b, bm, bt)) > 0
