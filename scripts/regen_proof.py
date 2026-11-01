"""Regenerate results/SAVINGS_PROOF_v2.md from results/runs.jsonl (append-only log). Read-only on results/.
Usage (repo root):  python scripts/regen_proof.py
Needs data/gecad/Input_JSON_Schedule_Optimization.json. Optional: data/gecad/Output_JSON_Schedule_Optimization.json (authors comparison)."""
import json, hashlib, pathlib, statistics as st, collections, numpy as np, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from engine.engine import *   # baseline_edf, check, cost, load_profile, pk_tariff, P_MIBEL, SOL
ROOT = pathlib.Path(__file__).resolve().parent.parent
rows = [json.loads(l) for l in open(ROOT/'results'/'runs.jsonl', encoding='utf-8') if l.strip()]
base = baseline_edf(); pkp = pk_tariff(); mb = P_MIBEL
bc = {'pk': cost(base, pkp), 'mibel': cost(base, mb)}
imp_cost = lambda s: float((np.maximum(0, load_profile(s) - SOL) * mb).sum())
authors = None
op = ROOT/'data'/'gecad'/'Output_JSON_Schedule_Optimization.json'
if op.exists(): authors = json.load(open(op))['statistics']['cost']

last = {}
for r in rows:
    if r.get('success'): last[(r['params']['tariff'], r['params']['cap'], r['params']['seed_assign'])] = r
ver = []
for k, r in sorted(last.items()):
    p = ROOT / r['schedule_path'].replace('\\', '/'); raw = p.read_bytes()
    s = [tuple(x) for x in json.loads(raw)]; price = pkp if k[0] == 'pk' else mb
    c = cost(s, price)
    ver.append(dict(t=k[0], cap=k[1], seed=k[2], sha=hashlib.sha256(raw).hexdigest() == r['schedule_sha256'], viol=len(check(s)),
                    logged=r['full']['cost'], c=c, sav=100*(1-c/bc[k[0]]), kwh=load_profile(s).sum()/1000,
                    vs_auth=(100*(1-imp_cost(s)/authors) if (authors and k[0] == 'mibel') else None), tl=r['params']['time_limit']))
L = []; A = L.append
A('# SAVINGS_PROOF v2 (regenerated from results/runs.jsonl)\n')
A(f'Log lines: {len(rows)} (append-only; failures included). Configs with a successful run: {len(last)} of 18.')
A(f'Independent re-check of every schedule file (SHA256 vs log, my own constraint check, cost recomputed): '
  f'{sum(v["sha"] and v["viol"]==0 and abs(v["c"]-v["logged"])<1e-3*max(1,abs(v["c"])) for v in ver)} of {len(ver)} pass.\n')
A('## 1. Headline (saving vs tariff-blind fastest-mode baseline, no solar)\n')
A('| tariff | cap | machine load (cap/1152) | saving range over 3 seeds | median | optimized kWh (baseline 1315.7) |\n|---|---|---|---|---|---|')
for t in ('pk', 'mibel'):
    for cap in (1000, 1060, 1100):
        v = [x for x in ver if x['t'] == t and x['cap'] == cap]
        if v: A(f"| {'Pakistan TOU (illustrative)' if t=='pk' else 'MIBEL (dataset prices)'} | {cap} | {100*cap/1152:.0f}% | {min(x['sav'] for x in v):.1f}% to {max(x['sav'] for x in v):.1f}% | {st.median(x['sav'] for x in v):.1f}% | {v[0]['kwh']:.1f} |")
A('\nThe capacity cap is a modelling choice (how busy a machine may get). Every number is conditional on lower-energy modes giving the same product (UNCONFIRMED).\n')
if authors:
    vs = [x['vs_auth'] for x in ver if x['vs_auth'] is not None]
    A('## 2. Against the dataset authors\' published GA solution (MIBEL prices, dataset solar, grid-import-only cost)\n')
    A(f'Authors\' reported cost: {authors:.2f} EUR. Baseline (ours): {imp_cost(base):.2f} EUR. Our schedules were NOT optimized for solar.\n')
    A('| cap | seed | our cost with solar (EUR) | below authors |\n|---|---|---|---|')
    for x in ver:
        if x['vs_auth'] is not None:
            sched = [tuple(y) for y in json.load(open(ROOT/'results'/f"sched2_mibel_{x['cap']}_seed{x['seed']}.json"))]
            A(f"| {x['cap']} | {x['seed']} | {imp_cost(sched):.2f} | {x['vs_auth']:.1f}% |")
    A(f'\nAcross {len(vs)} runs: min {min(vs):.1f}%, median {st.median(vs):.1f}%, max {max(vs):.1f}%. Quote the range, not one run.\n')
A('## 3. All runs in the log\n')
A('| # | UTC | tariff | cap | seed | time limit | status | success | optimized cost | git dirty |\n|---|---|---|---|---|---|---|---|---|---|')
for i, r in enumerate(rows, 1):
    A(f"| {i} | {r['utc'][:19]} | {r['params']['tariff']} | {r['params']['cap']} | {r['params']['seed_assign']} | {r['params']['time_limit']:.0f} | {(r.get('stage2_info') or {}).get('status')} | {r['success']} | {(r.get('full') or {}).get('cost','-')} | {r['git_dirty']} |")
A('\n(modes_only is NOT reported anywhere: that intermediate schedule can violate constraints.)\n')
A('## 4. Assumptions and limits\n- Lower-energy mode substitution: product quality unconfirmed (ask GECAD authors).\n- Baseline is our own definition (tariff-blind earliest-deadline, fastest-finishing mode).\n- Tariff: B2 35.68/22.83 Rs/kWh via news reports only; peak window 18:30-22:30 and export Rs8.13 UNVERIFIED.\n- Solar array size in the dataset is unresolved (paper says 3 kW; file looks ~10x larger).\n- Solver: CP-SAT, 1 core, 90-240 s; gap to bound not closed.\n- Many runs show git_dirty=True because results/ and logs/ change during runs; code hashes are in runs.jsonl.\n- Data is a hang-tag textile line (3 machines, 6 days), not a Pakistani mill.')
(ROOT/'results'/'SAVINGS_PROOF_v2.md').write_text('\n'.join(L), encoding='utf-8'); print('wrote results/SAVINGS_PROOF_v2.md')
