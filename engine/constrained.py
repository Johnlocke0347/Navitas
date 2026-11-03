"""Constraint layer on top of the verified GECAD solver (engine/solve2.py is NOT modified).

Constraint types (plain JSON, produced from plain English by Muse Spark in the agent):
  {"type": "machine_down", "machine": "MAQ119", "day": 3}
  {"type": "avoid_window", "task": "Harden[2]" | "*", "start": "18:30", "end": "22:30", "days": "all" | [1,2,...]}
Day 1..6, clock times are local plant time; each plant day starts 07:00 (192 five-minute periods, ends 23:00).
"""
import time, json
import numpy as np
from ortools.sat.python import cp_model
try:
    from engine.engine import *
    from engine.solve2 import collections_counter
except ImportError:  # run from inside engine/
    from engine import *
    from solve2 import collections_counter

DAY_START_MIN = 7 * 60
N_DAYS = T // DAY
DEFAULT_TARIFF = {"peak": 35.68, "off": 22.83, "window": ["18:30", "22:30"]}   # Rs/kWh, illustrative, window UNVERIFIED
DAY_SCALE = 1000


def hhmm_to_k(s):
    h, m = [int(x) for x in s.split(":")]
    return max(0, min(DAY, (h * 60 + m - DAY_START_MIN) // 5))


def k_to_hhmm(k):
    mins = DAY_START_MIN + 5 * k
    return f"{mins // 60:02d}:{mins % 60:02d}"


def make_price(tariff=None):
    t = dict(DEFAULT_TARIFF); t.update(tariff or {})
    p = np.full(T, float(t["off"]) / 1000.0)
    k0, k1 = hhmm_to_k(t["window"][0]), hhmm_to_k(t["window"][1])
    for d in range(N_DAYS): p[d * DAY + k0:d * DAY + k1] = float(t["peak"]) / 1000.0
    return p


def normalize(constraints):
    """validate + expand into blocked windows. Returns (clean_list, blocked_machine, blocked_task, errors)."""
    clean, errs = [], []
    bm, bt = {}, {}
    for c in constraints or []:
        ty = c.get("type")
        if ty == "machine_down":
            m, d = c.get("machine"), c.get("day")
            if m not in MACH_MODES: errs.append(f"unknown machine {m!r} (have {sorted(MACH_MODES)})"); continue
            if not isinstance(d, int) or not 1 <= d <= N_DAYS: errs.append(f"day must be 1..{N_DAYS}, got {d!r}"); continue
            bm.setdefault(m, []).append(((d - 1) * DAY, d * DAY)); clean.append({"type": ty, "machine": m, "day": d})
        elif ty == "avoid_window":
            task = c.get("task", "*")
            if task != "*" and task not in TASK_MODES: errs.append(f"unknown task {task!r} (have {sorted(TASK_MODES)})"); continue
            try: k0, k1 = hhmm_to_k(c["start"]), hhmm_to_k(c["end"])
            except Exception: errs.append("start/end must look like '18:30'"); continue
            if k1 <= k0: errs.append("end must be after start (same plant day, 07:00-23:00)"); continue
            days = c.get("days", "all"); days = list(range(1, N_DAYS + 1)) if days in ("all", None) else days
            if not all(isinstance(x, int) and 1 <= x <= N_DAYS for x in days): errs.append("days must be 'all' or a list of 1..6"); continue
            for d in days: bt.setdefault(task, []).append(((d - 1) * DAY + k0, (d - 1) * DAY + k1))
            clean.append({"type": ty, "task": task, "start": k_to_hhmm(k0), "end": k_to_hhmm(k1), "days": "all" if len(days) == N_DAYS else days})
        else:
            errs.append(f"unknown constraint type {ty!r}")
    return clean, bm, bt, errs


def _hit(s, d, wins):
    return any(s < b and a < s + d for a, b in wins)


def blocked_at(machine, task, s, d, bm, bt):
    return _hit(s, d, bm.get(machine, [])) or _hit(s, d, bt.get(task, [])) or _hit(s, d, bt.get("*", []))


def _union_len(wins):
    if not wins: return 0
    pts = sorted(wins); tot = 0; cs, ce = pts[0]
    for a, b in pts[1:]:
        if a <= ce: ce = max(ce, b)
        else: tot += ce - cs; cs, ce = a, b
    return tot + ce - cs


def check_constraints(sched, bm, bt):
    """violations of the user constraints (separate from the dataset checker)"""
    v = []
    for (i, m, tm, s) in sched:
        d = len(TM[tm]); task = instances[i]["task"]
        if blocked_at(m, task, s, d, bm, bt): v.append(("user-constraint", i, m, task, s))
    return v


def baseline_blocked(bm, bt):
    """tariff-blind earliest-deadline schedule that also respects the user constraints (what the plant would do 'today')."""
    units = {}
    for i, ins in enumerate(instances): units.setdefault(ins['unit'], []).append(i)
    order = sorted(units, key=lambda u: (instances[units[u][0]]['deadline'], u))
    occ = {m: np.zeros(T, dtype=bool) for m in MACH_MODES}; sched = []; h2 = []; sub = []; h15_end = []
    for u in order:
        ready = 0
        for i in sorted(units[u], key=lambda k: instances[k]['seq']):
            ins = instances[i]; best = None
            for (mm, tm) in eligible(ins['task']):
                d = len(TM[tm]); s = ready
                while s + d <= T:
                    if day_ok(s, d) and not occ[mm][s:s + d].any() and not blocked_at(mm, ins['task'], s, d, bm, bt):
                        bad = False
                        if ins['task'] == 'Sublimation': bad = any(s < b and a < s + d for a, b in h2)
                        if ins['task'] == 'Harden[2]': bad = any(s < b and a < s + d for a, b in sub)
                        if not bad: break
                    s += 1
                if s + d <= T and (best is None or s + d < best[0]): best = (s + d, mm, tm, s, d)
            if best is None: return None
            e, mm, tm, s, d = best; occ[mm][s:s + d] = True; sched.append((i, mm, tm, s)); ready = e
            if ins['task'] == 'Sublimation': sub.append((s, s + d))
            if ins['task'] == 'Harden[2]': h2.append((s, s + d))
    return sched


def assign(counts, seed=7):
    """spread the chosen (machine,mode) options over task instances (same logic as solve2.assign, seedable)"""
    import random
    pools = {}
    for t in set(i['task'] for i in instances):
        pool = []
        for (mm, tm) in eligible(t): pool += [(mm, tm)] * counts[(t, tm)]
        pools[t] = pool
    rnd = random.Random(seed)
    for t in pools: rnd.shuffle(pools[t])
    idx = {t: 0 for t in pools}; out = {}
    for i, ins in enumerate(instances):
        t = ins['task']; out[i] = pools[t][idx[t]]; idx[t] += 1
    return out


def stage1_caps(caps):
    m = cp_model.CpModel(); cnt = collections_counter(); N = {}
    for t, c in cnt.items():
        for (mm, tm) in eligible(t): N[(t, tm)] = m.NewIntVar(0, c, f'n_{tm}')
        m.Add(sum(N[(t, tm)] for (_, tm) in eligible(t)) == c)
    for mm in MACH_MODES:
        m.Add(sum(N[(t, tm)] * len(TM[tm]) for t in cnt for (m2, tm) in eligible(t) if m2 == mm) <= caps[mm])
    m.Minimize(sum(N[(t, tm)] * int(sum(TM[tm])) for t in cnt for (_, tm) in eligible(t)))
    sv = cp_model.CpSolver(); sv.parameters.max_time_in_seconds = 20; st = sv.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): return None
    return {k: sv.Value(v) for k, v in N.items()}


def stage2_blocked(assg, price, scale, hint, tl, bm, bt, workers=1):
    m = cp_model.CpModel(); n = len(instances)
    S = [m.NewIntVar(0, T - 1, f's{i}') for i in range(n)]
    ivs = {mm: [] for mm in MACH_MODES}; special = []; terms = []
    for i, ins in enumerate(instances):
        mm, tm = assg[i]; pw = np.array(TM[tm], float); d = len(pw)
        allowed = [s for s in range(T - d + 1) if day_ok(s, d) and s + d <= ins['deadline'] and not blocked_at(mm, ins['task'], s, d, bm, bt)]
        if not allowed: return None, dict(status="INFEASIBLE", wall=0, why=f"no allowed start for task {i} ({ins['task']} on {mm})")
        m.AddAllowedAssignments([S[i]], [(s,) for s in allowed])
        iv = m.NewFixedSizeIntervalVar(S[i], d, f'iv{i}'); ivs[mm].append(iv)
        if ins['task'] in ('Sublimation', 'Harden[2]'): special.append(iv)
        aset = set(allowed)
        tab = [int(round((pw * price[s:s + d]).sum() * scale)) if s in aset else 0 for s in range(T)]
        ce = m.NewIntVar(0, max(tab) + 1, f'c{i}'); m.AddElement(S[i], tab, ce); terms.append(ce)
    for l in ivs.values(): m.AddNoOverlap(l)
    m.AddNoOverlap(special)
    units = {}
    for i, ins in enumerate(instances): units.setdefault(ins['unit'], []).append((ins['seq'], i))
    for u, l in units.items():
        l.sort()
        for (a, ia), (b, ib) in zip(l, l[1:]):
            if instances[ia]['task'] in ('Harden[2]', 'Harden[1.5]') and instances[ib]['task'] in ('Harden[2]', 'Harden[1.5]'): continue
            m.Add(S[ib] >= S[ia] + len(TM[assg[ia][1]]))
    h2 = [i for i, ins in enumerate(instances) if ins['task'] == 'Harden[2]']
    h15 = [i for i, ins in enumerate(instances) if ins['task'] == 'Harden[1.5]']
    for j, i2 in enumerate(h2): m.Add(S[i2] >= S[h15[j]] + len(TM[assg[h15[j]][1]]))
    m.Minimize(sum(terms))
    if hint:
        for (i, mm, tm, s) in hint: m.AddHint(S[i], s)
    sv = cp_model.CpSolver(); sv.parameters.max_time_in_seconds = tl; sv.parameters.num_workers = workers; sv.parameters.random_seed = 3
    t0 = time.time(); st = sv.Solve(m)
    info = dict(status=sv.StatusName(st), wall=round(time.time() - t0, 1))
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): return None, info
    info['bound'] = sv.BestObjectiveBound() / scale; info['obj'] = sv.ObjectiveValue() / scale
    return [(i, assg[i][0], assg[i][1], sv.Value(S[i])) for i in range(n)], info


def solve_with_constraints(constraints=None, tariff=None, cap=1060, time_limit=60, workers=1, seed=7):
    """Full pipeline. Returns a JSON-serialisable result dict (schedules included) -- never raises on infeasibility."""
    t0 = time.time()
    clean, bm, bt, errs = normalize(constraints)
    if errs: return {"ok": False, "error": "; ".join(errs), "constraints": clean}
    price = make_price(tariff)
    base = baseline_blocked(bm, bt)      # None = the plain fastest-mode schedule cannot meet the deadline under these constraints
    # effective machine capacity shrinks with blocked time
    caps = {}
    for mm in MACH_MODES:
        blocked = _union_len(bm.get(mm, []) + bt.get("*", []))
        caps[mm] = int(cap * (T - blocked) / T)
    cnts = stage1_caps(caps)
    if cnts is None: return {"ok": False, "error": "No mode/machine assignment fits the remaining capacity.", "constraints": clean, "caps": caps}
    assg = assign(cnts, seed)
    # hint: EDF placement honouring blocked windows
    hint = _edf_hint(assg, bm, bt)
    sched, info = stage2_blocked(assg, price, DAY_SCALE if price.max() > 0.01 else 10**6, hint, time_limit, bm, bt, workers)
    if sched is None: return {"ok": False, "error": f"Solver status {info.get('status')}: {info.get('why','no feasible placement found in the time limit')}", "constraints": clean, "caps": caps, "info": info}
    vio = check(sched); uv = check_constraints(sched, bm, bt)
    out = {
        "ok": True, "constraints": clean, "tariff": {**DEFAULT_TARIFF, **(tariff or {})}, "cap": cap, "caps": caps,
        "baseline": _summ(base, price, bm, bt) if base else None, "optimized": _summ(sched, price, bm, bt),
        "baseline_note": None if base else "The plain tariff-blind fastest-mode schedule cannot fit all tasks before the deadline under these constraints; the optimised plan can (it picks faster or lower-load modes where needed).",
        "violations_dataset": len(vio), "violations_user": len(uv), "solver": info,
        "mode_counts": {f"{k[1]}": v for k, v in cnts.items() if v}, "wall_s": round(time.time() - t0, 1),
        "schedule": {"baseline": [list(x) for x in base] if base else [], "optimized": [list(x) for x in sched]},
    }
    out["saving_pct"] = round(100 * (1 - out["optimized"]["cost"] / out["baseline"]["cost"]), 2) if base else None
    return out


def _edf_hint(assg, bm, bt):
    units = {}
    for i, ins in enumerate(instances): units.setdefault(ins['unit'], []).append(i)
    order = sorted(units, key=lambda u: (instances[units[u][0]]['deadline'], u))
    occ = {m: np.zeros(T, dtype=bool) for m in MACH_MODES}; sched = []; h2 = []; sub = []
    for u in order:
        ready = 0
        for i in sorted(units[u], key=lambda k: instances[k]['seq']):
            ins = instances[i]; mm, tm = assg[i]; d = len(TM[tm]); s = ready
            while s + d <= T:
                if day_ok(s, d) and not occ[mm][s:s + d].any() and not blocked_at(mm, ins['task'], s, d, bm, bt):
                    bad = False
                    if ins['task'] == 'Sublimation': bad = any(s < b and a < s + d for a, b in h2)
                    if ins['task'] == 'Harden[2]': bad = any(s < b and a < s + d for a, b in sub)
                    if not bad: break
                s += 1
            if s + d > T: return None
            occ[mm][s:s + d] = True; sched.append((i, mm, tm, s)); ready = s + d
            if ins['task'] == 'Sublimation': sub.append((s, s + d))
            if ins['task'] == 'Harden[2]': h2.append((s, s + d))
    return sched


def _summ(sched, price, bm, bt):
    L = load_profile(sched)
    return {"cost": round(float((L * price).sum()), 2), "kwh": round(float(L.sum() / 1000), 1), "peak_kw": round(float(L.max() * 12 / 1000), 1),
            "makespan": int(max(s + len(TM[tm]) for i, m, tm, s in sched)), "dataset_violations": len(check(sched)), "user_violations": len(check_constraints(sched, bm, bt))}
