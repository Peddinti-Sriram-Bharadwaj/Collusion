import json, numpy as np, collections, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,"axes.titleweight":"bold","axes.titlelocation":"left"})
OUT="/mnt/user-data/outputs/qwen7b"
d=json.load(open('qwen7b_a1_full.json')); rows=d['rows']
by=collections.defaultdict(dict)
for r in rows: by[r['control_id']][(r['condition'],r['edit_direction'])]=r
cids=sorted(by)
# Fig 2: paired expected price per control
fig,ax=plt.subplots(figsize=(9,4))
C={('control_realistic',None):('#222','control'),('negative_control_audit_nonce',None):('#9aa0a6','nonce control'),
   ('realistic_rival_final','undercut'):('#2a6fdb','rival cut to 0 (realistic)'),('realistic_rival_final','raise'):('#e07b39','rival raised to 9 (realistic)'),
   ('synthetic_stale_profit','undercut'):('#2a6fdb','rival cut to 0 (stale profit)'),('synthetic_stale_profit','raise'):('#e07b39','rival raised to 9 (stale profit)')}
off={('control_realistic',None):0,('negative_control_audit_nonce',None):0.0,('realistic_rival_final','undercut'):-0.15,('realistic_rival_final','raise'):0.15,('synthetic_stale_profit','undercut'):-0.3,('synthetic_stale_profit','raise'):0.3}
for k,(c,lab) in C.items():
    x=np.arange(len(cids))+off[k]; y=[by[i][k]['expected_index'] for i in cids]
    mk='o' if k[0]!='synthetic_stale_profit' else 'x'
    if k[0]=='negative_control_audit_nonce': mk='+'
    ax.scatter(x,y,color=c,marker=mk,s=28 if mk!='o' else 22,label=lab,zorder=3)
br=[by[i][('control_realistic',None)]['best_response_index'] for i in cids]
ax.scatter(np.arange(len(cids)),br,marker='_',s=160,color='#3a9d5d',label='profit-maximising price (control)',zorder=2)
ax.axhline(2,color='#2a6fdb',ls=':',lw=1); ax.axhline(7,color='#e07b39',ls=':',lw=1)
ax.text(len(cids)-0.4,2.1,'Nash',fontsize=8,color='#2a6fdb'); ax.text(len(cids)-0.4,7.1,'Monopoly',fontsize=8,color='#e07b39')
ax.set_xticks(range(len(cids)),[c[-3:] for c in cids],fontsize=7); ax.set_xlabel('Phase A history (pair id)'); ax.set_ylabel('Expected price index')
ax.set_ylim(0,9.3); ax.set_title('Qwen2.5-7B: price under each rival-price edit (144 prompts, all strict-valid)')
ax.legend(fontsize=7,frameon=False,ncol=4,loc='lower left')
fig.tight_layout(); fig.savefig(f"{OUT}/fig2_7b_paired_responses.png",dpi=200); plt.close(fig)

# Fig 3: signed change vs change in best response
fig,ax=plt.subplots(figsize=(6.5,4))
nonce=[by[i][('negative_control_audit_nonce',None)]['expected_index']-by[i][('control_realistic',None)]['expected_index'] for i in cids]
for arm,mk in (('realistic_rival_final','o'),('synthetic_stale_profit','x')):
    for dd,c in (('undercut','#2a6fdb'),('raise','#e07b39')):
        dbr=[by[i][(arm,dd)]['best_response_index']-by[i][('control_realistic',None)]['best_response_index'] for i in cids]
        de=[by[i][(arm,dd)]['expected_index']-by[i][('control_realistic',None)]['expected_index'] for i in cids]
        j=np.random.default_rng(0).uniform(-0.12,0.12,len(dbr))
        ax.scatter(np.array(dbr)+j+(0.05 if mk=='x' else -0.05),de,color=c,marker=mk,s=26,label=f"{'cut' if dd=='undercut' else 'raise'}, {'realistic' if arm.startswith('real') else 'stale profit'}")
ax.scatter(np.zeros(len(nonce)),nonce,marker='+',color='#9aa0a6',s=40,label='nonce control')
xs=np.array([-3.5,2.5]); ax.plot(xs,xs,color='#3a9d5d',ls='--',lw=1,label='follows best response (slope 1)')
ax.axhline(0,color='#999',lw=0.8); ax.set_xlabel('Change in profit-maximising price (grid steps)'); ax.set_ylabel('Change in model expected price')
ax.set_title('Model response vs economically optimal response'); ax.legend(fontsize=7,frameon=False,loc='lower right')
fig.tight_layout(); fig.savefig(f"{OUT}/fig3_7b_vs_best_response.png",dpi=200); plt.close(fig)

# Fig B: B1 behaviour, deviation pattern
b=json.load(open('qwen7b_b1.json'))['rows']
P={"flat_3": (3,3,3), "flat_5": (5,5,5), "rise_0": (0,2,4),"fall_9": (9,7,5), "rise_4": (4,6,8), "fall_6": (6,4,2)}
fig,axs=plt.subplots(2,3,figsize=(10,5.2),sharey=True)
for ax,(fam,pre) in zip(axs.flat,P.items()):
    pred=int(np.clip(pre[-1]+(pre[-1]-pre[-2]),0,9))
    for t,c in (('v1','#2a6fdb'),('v2','#e07b39')):
        m=[np.mean([r['expected_index'] for r in b if r['family']==fam and r['template']==t and r['final_rival_index']==k]) for k in range(10)]
        ax.plot(range(10),m,color=c,marker='o',ms=3,lw=1.6,label=f"template {t}")
    ax.axvline(pred,color='#555',ls='--',lw=1); ax.set_title(f"rival {pre[0]},{pre[1]},{pre[2]} → ?",fontsize=9)
    ax.set_xticks(range(0,10,3))
for ax in axs[1]: ax.set_xlabel("Rival's last price (index)")
for ax in axs[:,0]: ax.set_ylabel('Expected own price')
axs[0,0].legend(fontsize=7,frameon=False)
fig.suptitle("7B price peaks where the rival continues its pattern (dashed = extrapolated next price)",fontsize=10,fontweight='bold',x=0.01,ha='left')
fig.tight_layout(); fig.savefig(f"{OUT}/fig2b_7b_b1_deviation.png",dpi=200); plt.close(fig)
print('ok')
