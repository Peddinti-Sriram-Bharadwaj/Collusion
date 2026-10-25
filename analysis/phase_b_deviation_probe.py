import json, numpy as np, sys
sys.path.insert(0,'/home/claude/run/repo/analysis')
from phase_b_probes import probe_cv
d=json.load(open('qwen7b_b1.json')); rows=d['rows']; arr=np.load('qwen7b_b1.npz')
P={"flat_3": (3,3,3), "flat_5": (5,5,5), "rise_0": (0,2,4),"fall_9": (9,7,5), "rise_4": (4,6,8), "fall_6": (6,4,2)}
pred=np.array([np.clip(P[r['family']][-1]+(P[r['family']][-1]-P[r['family']][-2]),0,9) for r in rows])
fin=np.array([r['final_rival_index'] for r in rows]); dev=np.abs(fin-pred).astype(float)
fam=np.array([r['family'] for r in rows]); v1=np.array([r['template']=='v1' for r in rows])
out={}
for site in ('answer','rival'):
    X=arr[f'acts_{site}']
    out[site]=[probe_cv(X[v1][:,l,:].astype(np.float32), dev[v1], fam[v1]) for l in range(X.shape[1])]
    print(site, np.round(out[site],2).tolist(), flush=True)
json.dump({'deviation_r2':out,'definition':'|final rival index - linear extrapolation of rounds 1-3|, clipped 0..9'},open('b/deviation_probe.json','w'))
