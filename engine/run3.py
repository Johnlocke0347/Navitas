import json,sys
try:
    from solve2 import *
except ImportError:
    from engine.solve2 import *
base=baseline_edf()
which=sys.argv[1]
price,scale=(P_MIBEL,10**6) if which=='mibel' else (pk_tariff(),10**3)
assg_base={i:(m,tm) for (i,m,tm,s) in base}
# timing-only: keep baseline's machine+mode choices, optimise start times
t_only,info=stage2(assg_base,price,scale,base,float(sys.argv[2]))
print(which,'timing-only info',info,'viol',len(check(t_only)))
res={'baseline':cost(base,price),'timing_only':cost(t_only,price)}
json.dump([list(x) for x in t_only],open(f'sched_timing_{which}.json','w'))
print(res, 'saving %', 100*(1-res['timing_only']/res['baseline']))
