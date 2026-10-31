import json, collections
d=json.load(open('/mnt/user-data/uploads/Input_JSON_Schedule_Optimization.json'))
TM={t['id']:t['power'] for t in d['task_modes']}
TASK_MODES={t['id']:t['task_modes'] for t in d['tasks']}
MACH_MODES={m['id']:set(m['task_modes']) for m in d['machines']}
PROD={p['id']:[(x['task'],x['runs']) for x in p['tasks']] for p in d['products']}
PRICE=d['energy_sources'][0]['price']
SOLAR=d['energy_sources'][1]['availability']
T=d['configuration']['time_window']; LEAP=d['configuration']['time_leap']
DAY=192
# build task instances: one list per unit of each request
instances=[]  # dict(id, unit, product, task, seq, deadline)
uid=0
for r in d['product_requests']:
    for u in range(r['amount']):
        seq=0
        for task,runs in PROD[r['product']]:
            for _ in range(runs):
                instances.append(dict(unit=uid,product=r['product'],task=task,seq=seq,deadline=r.get('deadline',T)))
                seq+=1
        uid+=1
def eligible(task):
    out=[]
    for tm in TASK_MODES[task]:
        for m,s in MACH_MODES.items():
            if tm in s: out.append((m,tm))
    return out
