import numpy as np
from load import *

SOL=np.array(SOLAR,dtype=float)
P_MIBEL=np.array(PRICE)           # EUR per Wh (dataset's own prices)
def pk_tariff(peak=35.68,off=22.83):   # Rs/kWh -> Rs/Wh, ILLUSTRATIVE, peak window UNVERIFIED
    p=np.full(T,off/1000.0)
    for d_ in range(6):
        p[d_*DAY+138:d_*DAY+186]=peak/1000.0   # 18:30-22:30 if day starts 07:00
    return p

def day_ok(s,d):  # no crossing day boundary (time leap)
    return s//DAY==(s+d-1)//DAY and s+d<=T

def load_profile(sched):
    L=np.zeros(T)
    for (i,m,tm,s) in sched:
        pw=TM[tm]; L[s:s+len(pw)]+=pw
    return L

def cost(sched,price,pv_scale=0.0,export_frac=0.5,export_price=None):
    L=load_profile(sched); S=SOL*pv_scale
    imp=np.maximum(0,L-S); exp=np.maximum(0,S-L)
    ex_p = price*export_frac if export_price is None else export_price
    return float((imp*price).sum()-(exp*ex_p).sum())

def check(sched):
    """returns list of violations"""
    v=[]
    byM={}
    for (i,m,tm,s) in sched:
        ins=instances[i]; d=len(TM[tm])
        if tm not in MACH_MODES[m]: v.append(('machine-mode',i))
        if tm not in TASK_MODES[ins['task']]: v.append(('task-mode',i))
        if not day_ok(s,d): v.append(('timeleap/window',i))
        if s+d>ins['deadline']: v.append(('deadline',i))
        byM.setdefault(m,[]).append((s,s+d,i))
    for m,l in byM.items():
        l.sort()
        for a,b in zip(l,l[1:]):
            if b[0]<a[1]: v.append(('overlap',m,a[2],b[2]))
    # unit sequence
    when={i:(s,s+len(TM[tm])) for (i,m,tm,s) in sched}
    units={}
    for i,ins in enumerate(instances): units.setdefault(ins['unit'],[]).append((ins['seq'],i))
    for u,l in units.items():
        l.sort()
        for (a,ia),(b,ib) in zip(l,l[1:]):
            if instances[ia]['task'] in ('Harden[2]','Harden[1.5]') and instances[ib]['task'] in ('Harden[2]','Harden[1.5]'): continue
            if ia in when and ib in when and when[ib][0]<when[ia][1]: v.append(('sequence',ia,ib))
    # collision Sublimation vs Harden[2]
    sub=[when[i] for i,ins in enumerate(instances) if ins['task']=='Sublimation' and i in when]
    h2=[when[i] for i,ins in enumerate(instances) if ins['task']=='Harden[2]' and i in when]
    for a in sub:
        for b in h2:
            if a[0]<b[1] and b[0]<a[1]: v.append(('collision',a,b))
    h15e=sorted(when[i][1] for i,ins in enumerate(instances) if ins['task']=='Harden[1.5]' and i in when)
    h2s=sorted(when[i][0] for i,ins in enumerate(instances) if ins['task']=='Harden[2]' and i in when)
    for k,st in enumerate(h2s):
        if k>=len(h15e) or st<h15e[k]: v.append(('order H1.5->H2',k))
    if len(sched)!=len(instances): v.append(('missing-tasks',len(instances)-len(sched)))
    return v

def baseline_edf():
    """Tariff-blind: units by deadline then request order; each task goes to the (machine,mode) that finishes earliest."""
    units={}
    for i,ins in enumerate(instances): units.setdefault(ins['unit'],[]).append(i)
    order=sorted(units,key=lambda u:(instances[units[u][0]]['deadline'],u))
    occ={m:np.zeros(T,dtype=bool) for m in MACH_MODES}
    sched=[]; h2=[]; sub=[]
    for u in order:
        ready=0
        for i in sorted(units[u],key=lambda k:instances[k]['seq']):
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
                if s+d<=T and (best is None or s+d<best[0]): best=(s+d,m,tm,s,d)
            if best is None: raise RuntimeError('baseline infeasible')
            e,m,tm,s,d=best; occ[m][s:s+d]=True; sched.append((i,m,tm,s)); ready=e
            if ins['task']=='Sublimation': sub.append((s,s+d))
            if ins['task']=='Harden[2]': h2.append((s,s+d))
    return sched
