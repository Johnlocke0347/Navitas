import sys, json, time, numpy as np
from ortools.sat.python import cp_model
try:
    from engine import *
except ImportError:
    from engine.engine import *

def stage1(cap, wprice=None):
    """choose how many instances of each task use each (machine,mode): min price-weighted energy s.t. machine capacity (periods)"""
    m=cp_model.CpModel(); cnt=collections_counter()
    N={}
    for t,c in cnt.items():
        for (mm,tm) in eligible(t): N[(t,tm)]=m.NewIntVar(0,c,f'n_{tm}')
        m.Add(sum(N[(t,tm)] for (_,tm) in eligible(t))==c)
    for mm in MACH_MODES:
        m.Add(sum(N[(t,tm)]*len(TM[tm]) for t in cnt for (m2,tm) in eligible(t) if m2==mm)<=cap)
    m.Minimize(sum(N[(t,tm)]*int(sum(TM[tm])*(wprice or 1)) for t in cnt for (_,tm) in eligible(t)))
    sv=cp_model.CpSolver(); sv.parameters.max_time_in_seconds=20; st=sv.Solve(m)
    if st not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return None
    return {k:sv.Value(v) for k,v in N.items()}
def collections_counter():
    import collections; return collections.Counter(i['task'] for i in instances)

def assign(counts):
    """spread chosen candidates over instances (round-robin so each unit gets a mix)"""
    pools={}
    for t in set(i['task'] for i in instances):
        pool=[]
        for (mm,tm) in eligible(t): pool+= [(mm,tm)]*counts[(t,tm)]
        # interleave
        pools[t]=pool
    idx={t:0 for t in pools}; out={}
    # deterministic shuffle to interleave candidates
    import random; rnd=random.Random(7)
    for t in pools: rnd.shuffle(pools[t])
    for i,ins in enumerate(instances):
        t=ins['task']; out[i]=pools[t][idx[t]]; idx[t]+=1
    return out

def edf_place(assg):
    units={}
    for i,ins in enumerate(instances): units.setdefault(ins['unit'],[]).append(i)
    order=sorted(units,key=lambda u:(instances[units[u][0]]['deadline'],u))
    occ={m:np.zeros(T,dtype=bool) for m in MACH_MODES}; sched=[]; h2=[]; sub=[]
    for u in order:
        ready=0
        for i in sorted(units[u],key=lambda k:instances[k]['seq']):
            ins=instances[i]; mm,tm=assg[i]; d=len(TM[tm]); s=ready
            while s+d<=T:
                if day_ok(s,d) and not occ[mm][s:s+d].any():
                    bad=False
                    if ins['task']=='Sublimation': bad=any(s<b and a<s+d for a,b in h2)
                    if ins['task']=='Harden[2]': bad=any(s<b and a<s+d for a,b in sub)
                    if not bad: break
                s+=1
            if s+d>T: return None
            occ[mm][s:s+d]=True; sched.append((i,mm,tm,s)); ready=s+d
            if ins['task']=='Sublimation': sub.append((s,s+d))
            if ins['task']=='Harden[2]': h2.append((s,s+d))
    return sched

def stage2(assg, price, scale, hint, tl):
    m=cp_model.CpModel(); n=len(instances)
    S=[m.NewIntVar(0,T-1,f's{i}') for i in range(n)]
    ivs={mm:[] for mm in MACH_MODES}; special=[]; terms=[]
    for i,ins in enumerate(instances):
        mm,tm=assg[i]; pw=np.array(TM[tm],float); d=len(pw)
        # allowed starts: day-fit, deadline
        allowed=[s for s in range(T-d+1) if day_ok(s,d) and s+d<=ins['deadline']]
        m.AddAllowedAssignments([S[i]],[(s,) for s in allowed])
        iv=m.NewFixedSizeIntervalVar(S[i],d,f'iv{i}'); ivs[mm].append(iv)
        if ins['task'] in ('Sublimation','Harden[2]'): special.append(iv)
        tab=[int(round((pw*price[s:s+d]).sum()*scale)) if s in set(allowed) else 0 for s in range(T)]
        ce=m.NewIntVar(0,max(tab)+1,f'c{i}'); m.AddElement(S[i],tab,ce); terms.append(ce)
    for l in ivs.values(): m.AddNoOverlap(l)
    m.AddNoOverlap(special)
    units={}
    for i,ins in enumerate(instances): units.setdefault(ins['unit'],[]).append((ins['seq'],i))
    for u,l in units.items():
        l.sort()
        for (a,ia),(b,ib) in zip(l,l[1:]):
            if instances[ia]['task'] in ('Harden[2]','Harden[1.5]') and instances[ib]['task'] in ('Harden[2]','Harden[1.5]'): continue
            m.Add(S[ib]>=S[ia]+len(TM[assg[ia][1]]))
    h2=[i for i,ins in enumerate(instances) if ins['task']=='Harden[2]']
    h15=[i for i,ins in enumerate(instances) if ins['task']=='Harden[1.5]']
    for j,i2 in enumerate(h2): m.Add(S[i2]>=S[h15[j]]+len(TM[assg[h15[j]][1]]))   # dataset Order rule: H1.5 before H2 (count-paired)
    m.Minimize(sum(terms))
    if hint:
        for (i,mm,tm,s) in hint: m.AddHint(S[i],s)
    sv=cp_model.CpSolver(); sv.parameters.max_time_in_seconds=tl; sv.parameters.num_workers=1; sv.parameters.random_seed=3
    t0=time.time(); st=sv.Solve(m)
    info=dict(status=sv.StatusName(st),wall=round(time.time()-t0,1))
    if st not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return None,info
    info['bound']=sv.BestObjectiveBound()/scale; info['obj']=sv.ObjectiveValue()/scale
    return [(i,assg[i][0],assg[i][1],sv.Value(S[i])) for i in range(n)],info

if __name__=='__main__':
    which=sys.argv[1]; cap=int(sys.argv[2]); tl=float(sys.argv[3])
    price,scale=(P_MIBEL,10**6) if which=='mibel' else (pk_tariff(),10**3)
    base=baseline_edf(); out=dict(which=which,cap=cap)
    out['baseline']=dict(cost=cost(base,price),kwh=load_profile(base).sum()/1000,viol=len(check(base)))
    cnts=stage1(cap); 
    if cnts is None: print('stage1 infeasible'); sys.exit()
    out['stage1_counts']={f'{k[1]}':v for k,v in cnts.items() if v}
    assg=assign(cnts); sched_a=edf_place(assg)
    if sched_a is None: print('EDF placement infeasible at cap',cap); sys.exit()
    out['modes_only']=dict(cost=cost(sched_a,price),kwh=load_profile(sched_a).sum()/1000,viol=len(check(sched_a)))
    sched_b,info=stage2(assg,price,scale,sched_a,tl)
    out['stage2_info']=info
    if sched_b:
        out['full']=dict(cost=cost(sched_b,price),kwh=load_profile(sched_b).sum()/1000,viol=len(check(sched_b)),makespan=max(s+len(TM[tm]) for i,m_,tm,s in sched_b))
        json.dump([list(x) for x in sched_b],open(f'sched2_{which}_{cap}.json','w'))
    json.dump(out,open(f'res2_{which}_{cap}.json','w'),indent=1); print(json.dumps(out,indent=1))
