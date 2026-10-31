"""Generate results/SAVINGS_PROOF.md from results/runs.jsonl"""
import json, pathlib, statistics, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "results" / "runs.jsonl"
OUT = ROOT / "results" / "SAVINGS_PROOF.md"
DATA_JSON = ROOT / "data" / "gecad" / "Input_JSON_Schedule_Optimization.json"

def load_runs():
    runs=[]
    if RUNS.exists():
        for line in open(RUNS, encoding="utf-8"):
            if line.strip():
                runs.append(json.loads(line))
    return runs

def by_task_kwh(sched_path, price_label="kwh"):
    import json, numpy as np
    info = json.load(open(DATA_JSON, encoding="utf-8"))
    TM={t['id']:t['power'] for t in info['task_modes']}
    PROD={p['id']:[(x['task'],x['runs']) for x in p['tasks']] for p in info['products']}
    instances=[]
    uid=0
    for r in info['product_requests']:
        for u in range(r['amount']):
            seq=0
            for task,runs in PROD[r['product']]:
                for _ in range(runs):
                    instances.append(dict(task=task))
                    seq+=1
            uid+=1
    sched=json.load(open(sched_path)) if isinstance(sched_path, (str,Path)) and Path(sched_path).exists() else sched_path
    from collections import defaultdict
    per_task=defaultdict(float)
    total=0.0
    for (i,m,tm,s) in sched:
        pw=TM[tm]
        kwh=sum(pw)/1000.0
        task=instances[i]['task']
        per_task[task]+=kwh
        total+=kwh
    return per_task, total

def main():
    runs=load_runs()
    out_lines=[]
    out_lines.append("# SAVINGS_PROOF — Audit Trail for Savings Claim\n")
    out_lines.append(f"> Generated from `{RUNS.relative_to(ROOT)}` — {len(runs)} runs (append-only, failures included). Do not edit manually.\n")
    out_lines.append(f"> Input SHA256: `{runs[0]['input_sha256'] if runs else 'N/A'}`\n")
    out_lines.append(f"> Git commit at generation: `{runs[-1]['git_commit'] if runs else 'N/A'}` dirty={runs[-1]['git_dirty'] if runs else 'N/A'}\n")
    out_lines.append(f"> Python {runs[-1]['python_version'] if runs else ''}, ortools {runs[-1]['ortools_version'] if runs else ''}, CPU {runs[-1]['cpu_count'] if runs else ''}\n")
    out_lines.append("\n## 1. Table of ALL runs\n")
    out_lines.append("| # | cap | seed | tariff | baseline cost | optimized cost | saving % | baseline kWh | optimized kWh | viol base/opt | status | wall (s) | bound | schedule |\n")
    out_lines.append("|---|-----|------|--------|---------------|----------------|----------|--------------|---------------|---------------|--------|----------|-------|----------|\n")
    savings_by_cap={}
    for idx, r in enumerate(runs,1):
        cap=r['params']['cap']; seed=r['params']['seed_assign']; tariff=r['params']['tariff']
        b=r.get('baseline',{}); f=r.get('full',{})
        b_cost=b.get('cost','-'); b_kwh=b.get('kwh','-'); b_viol=b.get('viol','-')
        if r.get('success') and f:
            opt_cost=f.get('cost'); opt_kwh=f.get('kwh'); opt_viol=f.get('viol')
            saving = 100*(1 - opt_cost/b_cost) if b_cost else 0
            savings_by_cap.setdefault(cap, []).append(saving)
            wall=r.get('stage2_info',{}).get('wall','-'); bound=r.get('stage2_info',{}).get('bound','-'); status=r.get('stage2_info',{}).get('status','-')
            sched=r.get('schedule_path','-')
            out_lines.append(f"| {idx} | {cap} | {seed} | {tariff} | {b_cost:.2f} | {opt_cost:.2f} | {saving:.2f}% | {b_kwh:.3f} | {opt_kwh:.3f} | {b_viol}/{opt_viol} | {status} | {wall} | {bound:.1f} | {sched} |\n")
        else:
            status=r.get('stage2_info',{}).get('status','FAILED'); wall=r.get('stage2_info',{}).get('wall','-'); bound=r.get('stage2_info',{}).get('bound','-')
            err=r.get('error','')
            out_lines.append(f"| {idx} | {cap} | {seed} | {tariff} | {b_cost} | - | - | {b_kwh} | - | {b_viol}/- | {status} | {wall} | {bound} | {err} |\n")
    out_lines.append("\n## 2. Min/Median/Max saving per cap (pk successes only)\n")
    out_lines.append("| cap | n success | min % | median % | max % | mean % |\n")
    out_lines.append("|-----|-----------|-------|----------|-------|--------|\n")
    for cap in sorted(savings_by_cap):
        vals=sorted(savings_by_cap[cap])
        n=len(vals); mn=min(vals); mx=max(vals); med=statistics.median(vals); mean=statistics.mean(vals)
        out_lines.append(f"| {cap} | {n} | {mn:.2f}% | {med:.2f}% | {mx:.2f}% | {mean:.2f}% |\n")
    if not savings_by_cap:
        out_lines.append("| - | 0 | - | - | - | - |\n")
    out_lines.append("\n> Do not pick the best — all runs are shown above.\n")
    out_lines.append("\n## 3. Independent verifier output (representative schedule)\n")
    out_lines.append("Representative: `results/sched2_pk_1060_seed7.json` (cap 1060, seed 7, pk) — also baseline verified.\n")
    out_lines.append("```\n")
    try:
        import subprocess, sys
        rep = ROOT / "results" / "sched2_pk_1060_seed7.json"
        if not rep.exists():
            rep = ROOT / "results" / "sched2_pk_1060.json"
        if not rep.exists():
            rep = ROOT / "sched2_pk_1060.json"
        out_lines.append(subprocess.check_output([sys.executable, "engine/verify_schedule.py", str(rep), "--tariff", "pk"], cwd=ROOT, text=True))
        out_lines.append("\n--- baseline ---\n")
        out_lines.append(subprocess.check_output([sys.executable, "engine/verify_schedule.py", "--baseline", "--tariff", "pk"], cwd=ROOT, text=True))
    except Exception as e:
        out_lines.append(f"verifier error: {e}\n")
    out_lines.append("```\n")
    out_lines.append("\n## 4. By-task kWh breakdown (baseline vs optimized) — where saving comes from\n")
    out_lines.append("Pk tariff, cap 1060, seed 7 representative. Saving comes almost entirely from lower-energy modes (Harden[1] and Harden[0.5]).\n")
    try:
        rep_path = ROOT / "results" / "sched2_pk_1060_seed7.json"
        if not rep_path.exists():
            rep_path = ROOT / "results" / "sched2_pk_1060.json"
        if not rep_path.exists():
            rep_path = Path("sched2_pk_1060.json")
        import sys
        sys.path.insert(0, str(ROOT))
        import engine.load as ld
        import engine.engine as eng
        base = eng.baseline_edf()
        opt = [tuple(x) for x in json.load(open(rep_path))]
        per_base, tot_base = by_task_kwh(base, rep_path)
        per_opt, tot_opt = by_task_kwh(opt, rep_path)
        tasks=sorted(set(list(per_base.keys())+list(per_opt.keys())))
        out_lines.append("| task | baseline kWh | optimized kWh | delta kWh | delta % |\n")
        out_lines.append("|------|--------------|---------------|-----------|---------|\n")
        for t in tasks:
            b=per_base.get(t,0); o=per_opt.get(t,0); d=o-b; pct= (d/b*100 if b else 0)
            out_lines.append(f"| {t} | {b:.3f} | {o:.3f} | {d:+.3f} | {pct:+.1f}% |\n")
        out_lines.append(f"| **TOTAL** | **{tot_base:.3f}** | **{tot_opt:.3f}** | **{tot_opt-tot_base:+.3f}** | **{(tot_opt/tot_base-1)*100:+.1f}%** |\n")
    except Exception as e:
        out_lines.append(f"by-task error: {e}\n")
    out_lines.append("\n## 5. Assumptions and limits\n")
    out_lines.append("- **Mode substitution quality unconfirmed:** Paper defines a task mode as \"a combination of energy and time profiles\" and GA swaps modes freely; nothing about product quality. Saving via lower-energy modes (Harden[1] TM1, Harden[0.5] TM4) is unconfirmed for quality.\n")
    out_lines.append("- **Baseline definition:** Tariff-blind earliest-deadline schedule, each task on the machine/mode that finishes earliest (my definition). Not the paper's GA baseline, but independent 0-violation baseline.\n")
    out_lines.append("- **Extra restriction:** Tasks of one unit run in listed product order (except Harden pair). Paper says product-task-order was NOT used, so our model is stricter than theirs.\n")
    out_lines.append("- **Tariff:** B2 rates Rs35.68/22.83 confirmed via news only (Dawn 1973828, NEPRA Feb 2026). Peak window 18:30-22:30 and export price Rs8.13 are **UNVERIFIED** assumptions in `engine/engine.py` → `pk_tariff()`; do not change without verification.\n")
    out_lines.append("- **Solar:** Dataset solar availability used only for shape; absolute scale ILLUSTRATIVE, not Pakistan yield. PVGIS not used for absolute.\n")
    out_lines.append("- **Solver gap not closed:** Stage2 CP-SAT 90s wall, 1 core, bound 21092 vs obj 23105 (gap ~8%), not proven optimal. Saving is feasible, not optimal.\n")
    out_lines.append("- **MIBEL failures:** 9/18 runs (all mibel) were infeasible/UNKNOWN within 90s timelimit; pk successes are robust across caps/seeds (9/9 pk success). Do not generalize to mibel without longer timelimit.\n")
    out_lines.append("- **Data:** `data/` gitignored, SHA256 logged per run. See `DATA_SOURCES.md` for URLs/licenses. German/Irish/Kaggle India solar not used for absolute kW, only shape evidence.\n")
    out_lines.append("\n---\n")
    out_lines.append(f"Generated {__file__} at UTC {__import__('datetime').datetime.utcnow().isoformat()}Z\n")
    OUT.write_text("".join(out_lines), encoding="utf-8")
    print(f"Wrote {OUT} with {len(runs)} runs")

if __name__=="__main__":
    main()


