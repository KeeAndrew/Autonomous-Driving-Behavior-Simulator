import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from python.common import load_metrics, save_json, sha256

def reduction(baseline, other):
    return None if baseline==0 else float(100*(baseline-other)/baseline)

def paired_bootstrap(baseline,other,seed=61,repeats=1000):
    b=np.asarray(baseline,float); h=np.asarray(other,float)
    if b.shape!=h.shape or len(b)==0: raise ValueError('Paired bootstrap requires equal nonempty arrays')
    rng=np.random.default_rng(seed); differences=[]; reductions=[]
    for _ in range(repeats):
        ids=rng.integers(0,len(b),len(b)); bm=b[ids].mean(); hm=h[ids].mean()
        differences.append(hm-bm)
        if bm>0: reductions.append(100*(bm-hm)/bm)
    return {'mean_difference':float((h-b).mean()),'difference_95ci':np.quantile(differences,[.025,.975]).tolist(),
            'reduction_percent':reduction(float(b.mean()),float(h.mean())),
            'reduction_95ci':np.quantile(reductions,[.025,.975]).tolist() if reductions else None,
            'bootstrap_replicates':repeats,'valid_reduction_replicates':len(reductions)}

def main():
    p=argparse.ArgumentParser()
    for c in ['baseline','ml','hybrid','out']: p.add_argument('--'+c,type=Path,required=True)
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    frames={c:load_metrics(getattr(a,c)) for c in ['baseline','ml','hybrid']}
    b=frames['baseline']
    if any(not b.index.equals(f.index) or not b.kind.equals(f.kind) for f in frames.values()): raise ValueError('Unpaired reports')
    summary=[]
    for c,f in frames.items():
        summary.append({'controller':c,'scenarios':len(f),'collisions':int(f.collision.sum()),'collision_rate':float(f.collision.mean()),
         'hard_brakes':int(f.hard_brakes.sum()),'hard_brakes_per_km':float(f.hard_brakes.sum()/max(f.distance.sum()/1000,1e-12)),
         'near_miss_episodes':int(f.near_misses.sum()),'mean_min_separation':float(f.min_separation.mean()),'mean_min_following_gap':float(f.min_following_gap.mean()),
         'mean_min_ttc_capped_30':float(f.min_ttc.clip(upper=30).mean()),
         'mean_distance':float(f.distance.mean()),'mean_speed':float(f.average_speed.mean()),
         'route_completion':float(f.completed.mean()),'mean_arrival_completed_only':float(f.loc[f.completed.eq(1),'arrival'].mean()) if f.completed.any() else None,
         'mean_progress':float(f.progress.mean()),'mean_rms_jerk':float(f.rms_jerk.mean()),
         'mean_acceleration_variance':float(f.acceleration_variance.mean()),'mean_braking_time':float(f.braking_time.mean()),
         'max_peak_deceleration':float(f.peak_deceleration.max()),'mean_rms_lateral_jerk':float(f.rms_lateral_jerk.mean())})
    table=pd.DataFrame(summary); table.to_csv(a.out/'comparison.csv',index=False)
    uncertainty={c:{metric:paired_bootstrap(b[metric],frames[c][metric]) for metric in ['collision','hard_brakes','rms_jerk','progress']} for c in ['ml','hybrid']}
    save_json(a.out/'report.json',{'scenarios_per_controller':len(b),'total_runs':3*len(b),'summary':summary,'paired_bootstrap':uncertainty,
        'input_sha256':{c:sha256(getattr(a,c)) for c in frames},'disclaimer':'Synthetic simplified simulation; no real-world safety claim. Hybrid evaluated as a predeclared hypothesis, not guaranteed improvement.'})
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for ax,col,title in zip(axes,['collision_rate','hard_brakes_per_km','mean_rms_jerk'],['Collision rate','Hard brakes / km','Mean RMS jerk (m/s³)']):
        ax.bar(table.controller,table[col],color=['#5879a2','#d69242','#4b9678']); ax.set_title(title)
    fig.tight_layout(); fig.savefig(a.out/'comparison.png',dpi=160); plt.close(fig)
    lines=['# Measured controller evaluation','',f'{len(b):,} held-out scenarios per controller; {3*len(b):,} runs.','',
           '| Controller | Collisions | Hard-braking events | Completion | RMS jerk |','|---|---:|---:|---:|---:|']
    for s in summary: lines.append(f'| {s["controller"]} | {s["collisions"]} | {s["hard_brakes"]} | {s["route_completion"]:.1%} | {s["mean_rms_jerk"]:.3f} |')
    lines.extend(['','Positive reduction means fewer events; negative means an increase. Undefined reductions use null when baseline is zero.'])
    for c in ['ml','hybrid']:
        for metric in ['collision','hard_brakes']:
            r=uncertainty[c][metric]
            lines.append(f'- {c} {metric}: reduction {r["reduction_percent"]}%; paired bootstrap 95% interval {r["reduction_95ci"]}.')
    lines.extend(['','Intervals describe sampling uncertainty within this synthetic distribution, not model error or real-world uncertainty. Arrival times are conditional on completion and should be interpreted alongside collision and completion rates.'])
    (a.out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(table[['controller','scenarios','collisions','hard_brakes','route_completion']].to_string(index=False))
if __name__=='__main__': main()