"""Independent verifier - reads only schedule JSON and input JSON, shares no code with solver.
Recomputes from scratch: overlap, machine/mode eligibility, day boundary (time leap),
deadline, unit sequence, Sublimation/Harden[2] collision, Harden[1.5]-before-Harden[2],
plus total cost and kWh. Prints PASS/FAIL per check. Also runs on baseline.
"""
import json, pathlib, sys, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "data" / "gecad" / "Input_JSON_Schedule_Optimization.json"

def load_input():
    p = DATA_JSON
    if not p.exists():
        p = Path("data/gecad/Input_JSON_Schedule_Optimization.json")
    d = json.load(open(p, encoding="utf-8"))
    TM = {t['id']: t['power'] for t in d['task_modes']}
    TASK_MODES = {t['id']: t['task_modes'] for t in d['tasks']}
    MACH_MODES = {m['id']: set(m['task_modes']) for m in d['machines']}
    PROD = {p['id']: [(x['task'], x['runs']) for x in p['tasks']] for p in d['products']}
    PRICE = d['energy_sources'][0]['price']
    SOLAR = d['energy_sources'][1]['availability']
    T = d['configuration']['time_window']
    LEAP = d['configuration']['time_leap']
    DAY = 192
    instances = []
    uid = 0
    for r in d['product_requests']:
        for u in range(r['amount']):
            seq = 0
            for task, runs in PROD[r['product']]:
                for _ in range(runs):
                    instances.append(dict(unit=uid, product=r['product'], task=task, seq=seq, deadline=r.get('deadline', T)))
                    seq += 1
            uid += 1
    def eligible(task):
        out=[]
        for tm in TASK_MODES[task]:
            for m,s in MACH_MODES.items():
                if tm in s:
                    out.append((m,tm))
        return out
    return {
        "d": d, "TM": TM, "TASK_MODES": TASK_MODES, "MACH_MODES": MACH_MODES,
        "PROD": PROD, "PRICE": PRICE, "SOLAR": SOLAR, "T": T, "LEAP": LEAP, "DAY": DAY,
        "instances": instances, "eligible": eligible
    }

def pk_tariff(T, DAY, peak=35.68, off=22.83):
    import numpy as np
    p = np.full(T, off/1000.0)
    for d_ in range(6):
        p[d_*DAY+138:d_*DAY+186] = peak/1000.0
    return p

def verify(sched, info, tariff="pk"):
    TM = info["TM"]; TASK_MODES = info["TASK_MODES"]; MACH_MODES = info["MACH_MODES"]
    instances = info["instances"]; T = info["T"]; DAY = info["DAY"]; PRICE = info["PRICE"]
    import numpy as np
    if tariff == "mibel":
        price = np.array(PRICE, dtype=float)
    else:
        price = pk_tariff(T, DAY)
    def day_ok(s,d):
        return s//DAY == (s+d-1)//DAY and s+d <= T
    results = []
    ok_mm = True; fails=[]
    for (i,m,tm,s) in sched:
        ins = instances[i]; d = len(TM[tm])
        if tm not in MACH_MODES[m]:
            ok_mm = False; fails.append(('machine-mode', i, m, tm))
        if tm not in TASK_MODES[ins['task']]:
            ok_mm = False; fails.append(('task-mode', i, ins['task'], tm))
    results.append(("machine/mode eligibility", ok_mm, fails))
    ok_day = True; fails=[]
    for (i,m,tm,s) in sched:
        d=len(TM[tm])
        if not day_ok(s,d):
            ok_day=False; fails.append(('timeleap', i, s, d))
    results.append(("day boundary (time leap)", ok_day, fails))
    ok_dead=True; fails=[]
    for (i,m,tm,s) in sched:
        ins=instances[i]; d=len(TM[tm])
        if s+d > ins['deadline']:
            ok_dead=False; fails.append(('deadline', i, s, d, ins['deadline']))
    results.append(("deadline", ok_dead, fails))
    ok_over=True; fails=[]
    byM={}
    for (i,m,tm,s) in sched:
        d=len(TM[tm])
        byM.setdefault(m, []).append((s,s+d,i))
    for m,l in byM.items():
        l.sort()
        for a,b in zip(l,l[1:]):
            if b[0] < a[1]:
                ok_over=False; fails.append(('overlap', m, a[2], b[2], a,b))
    results.append(("overlap (no machine overlap)", ok_over, fails))
    ok_seq=True; fails=[]
    when={i:(s,s+len(TM[tm])) for (i,m,tm,s) in sched}
    units={}
    for i,ins in enumerate(instances):
        units.setdefault(ins['unit'], []).append((ins['seq'], i))
    for u,l in units.items():
        l.sort()
        for (a,ia),(b,ib) in zip(l,l[1:]):
            if instances[ia]['task'] in ('Harden[2]','Harden[1.5]') and instances[ib]['task'] in ('Harden[2]','Harden[1.5]'):
                continue
            if ia in when and ib in when and when[ib][0] < when[ia][1]:
                ok_seq=False; fails.append(('sequence', ia, ib, when[ia], when[ib]))
    results.append(("unit sequence", ok_seq, fails))
    ok_coll=True; fails=[]
    sub=[when[i] for i,ins in enumerate(instances) if ins['task']=='Sublimation' and i in when]
    h2=[when[i] for i,ins in enumerate(instances) if ins['task']=='Harden[2]' and i in when]
    for a in sub:
        for b in h2:
            if a[0] < b[1] and b[0] < a[1]:
                ok_coll=False; fails.append(('collision', a,b))
    results.append(("collision Sublimation vs Harden[2]", ok_coll, fails))
    ok_order=True; fails=[]
    h15e=sorted(when[i][1] for i,ins in enumerate(instances) if ins['task']=='Harden[1.5]' and i in when)
    h2s=sorted(when[i][0] for i,ins in enumerate(instances) if ins['task']=='Harden[2]' and i in when)
    for k,st in enumerate(h2s):
        if k>=len(h15e) or st < h15e[k]:
            ok_order=False; fails.append(('order H1.5->H2', k, st, h15e[k] if k < len(h15e) else None))
    results.append(("order H1.5-before-H2 (paired)", ok_order, fails))
    ok_miss = len(sched)==len(instances)
    fails = [] if ok_miss else [('missing-tasks', len(instances)-len(sched))]
    results.append(("missing-tasks", ok_miss, fails))
    import numpy as np
    L=np.zeros(T)
    for (i,m,tm,s) in sched:
        pw=TM[tm]; L[s:s+len(pw)]+=pw
    kwh = float(L.sum()/1000)
    cost = float((L * price).sum()) if len(sched)>0 else 0.0
    results.append(("cost/kWh recomputed", True, []))
    return results, {"kwh": kwh, "cost": cost, "price": price}

def baseline_edf_independent(info):
    TM=info["TM"]; MACH_MODES=info["MACH_MODES"]; instances=info["instances"]; T=info["T"]; DAY=info["DAY"]
    def day_ok(s,d):
        return s//DAY==(s+d-1)//DAY and s+d<=T
    def eligible(task):
        return info["eligible"](task)
    import numpy as np
    units={}
    for i,ins in enumerate(instances):
        units.setdefault(ins['unit'], []).append(i)
    order=sorted(units, key=lambda u:(instances[units[u][0]]['deadline'],u))
    occ={m: np.zeros(T,dtype=bool) for m in MACH_MODES}
    sched=[]; h2=[]; sub=[]
    for u in order:
        ready=0
        for i in sorted(units[u], key=lambda k:instances[k]['seq']):
            ins=instances[i]; best=None
            for (m,tm) in eligible(ins['task']):
                d=len(TM[tm]); s=ready
                while s+d<=T:
                    if day_ok(s,d) and not occ[m][s:s+d].any():
                        bad=False
                        if ins['task']=='Sublimation': bad=any(s<b and a<s+d for a,b in h2)
                        if ins['task']=='Harden[2]': bad=any(s<b and a<s+d for a,b in sub)
                        if not bad: break
                    s+=1
                if s+d<=T and (best is None or s+d<best[0]):
                    best=(s+d,m,tm,s,d)
            if best is None:
                raise RuntimeError('baseline infeasible')
            e,m,tm,s,d=best
            occ[m][s:s+d]=True
            sched.append((i,m,tm,s))
            ready=e
            if ins['task']=='Sublimation': sub.append((s,s+d))
            if ins['task']=='Harden[2]': h2.append((s,s+d))
    return sched

def main():
    import argparse
    ap=argparse.ArgumentParser(description="Independent verifier for schedule JSON")
    ap.add_argument("schedule", nargs="?", help="path to schedule JSON (list of [i,m,tm,s])")
    ap.add_argument("--tariff", default="pk", choices=["pk","mibel"], help="tariff for cost")
    ap.add_argument("--baseline", action="store_true", help="also verify baseline schedule")
    ap.add_argument("--json", action="store_true", help="output JSON for proof")
    args=ap.parse_args()
    info=load_input()
    sched=None
    if args.schedule:
        p=Path(args.schedule)
        if not p.exists():
            print(f"schedule file not found: {p}", file=sys.stderr); sys.exit(2)
        data=json.load(open(p))
        sched=[tuple(x) for x in data]
        print(f"Verifying schedule: {p}  tariff={args.tariff}  tasks={len(sched)}/{len(info['instances'])}")
        results, metrics = verify(sched, info, tariff=args.tariff)
        for name, ok, fails in results:
            status="PASS" if ok else "FAIL"
            print(f"{status}: {name} - {len(fails)} fails")
            if not ok:
                for f in fails[:5]:
                    print(f"  fail: {f}")
        print(f"Recomputed cost={metrics['cost']:.2f} kWh={metrics['kwh']:.3f}")
        overall = all(ok for _,ok,_ in results)
        print(f"Overall: {'PASS' if overall else 'FAIL'}")
        if args.json:
            out={"schedule": str(p), "tariff": args.tariff, "results": [{"check":n,"pass":ok,"fails":fails} for n,ok,fails in results], "metrics": metrics, "overall": overall}
            print(json.dumps(out, indent=2))
    if args.baseline or not args.schedule:
        print("\n=== Baseline verification ===")
        base = baseline_edf_independent(info)
        results, metrics = verify(base, info, tariff=args.tariff)
        for name, ok, fails in results:
            status="PASS" if ok else "FAIL"
            print(f"{status}: {name}")
        print(f"Baseline cost={metrics['cost']:.2f} kWh={metrics['kwh']:.3f} tasks={len(base)}")
        overall = all(ok for _,ok,_ in results)
        print(f"Baseline Overall: {'PASS' if overall else 'FAIL'}")
        if args.json:
            out={"schedule":"baseline","tariff":args.tariff, "results": [{"check":n,"pass":ok,"fails":fails} for n,ok,fails in results], "metrics": metrics, "overall": overall}
            print(json.dumps(out, indent=2))

if __name__=="__main__":
    main()


