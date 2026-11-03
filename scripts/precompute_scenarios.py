"""Pre-solve the demo scenarios and store them in app/cache (run once; the demo then answers instantly).
Usage: python scripts/precompute_scenarios.py [time_limit_s] [workers]"""
import sys, pathlib, json, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from engine.constrained import solve_with_constraints
from engine import cache
tl = float(sys.argv[1]) if len(sys.argv) > 1 else 90
workers = int(sys.argv[2]) if len(sys.argv) > 2 else 1
SCEN = [
  ("base", []),
  ("maq119_down_day3", [{"type": "machine_down", "machine": "MAQ119", "day": 3}]),
  ("no_evening_peak", [{"type": "avoid_window", "task": "*", "start": "18:30", "end": "22:30", "days": "all"}]),
]
only = sys.argv[3].split(',') if len(sys.argv) > 3 else None
for name, cons in SCEN:
    if only and name not in only: continue
    t0 = time.time()
    try: r = solve_with_constraints(cons, time_limit=tl, workers=workers)
    except Exception as e:
        import traceback; traceback.print_exc(); print(name, "CRASHED", flush=True); continue
    if r.get("ok"):
        cache.save(r, cons, label=name)
        print(name, "OK saving", r["saving_pct"], "% cost", r["optimized"]["cost"], "vs", (r["baseline"] or {}).get("cost", "baseline infeasible"), "viol", r["violations_dataset"], r["violations_user"], "wall", round(time.time()-t0), flush=True)
    else:
        print(name, "FAILED:", r.get("error"), flush=True)
print("DONE", flush=True)
