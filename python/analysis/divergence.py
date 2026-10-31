"""Predeclared behavioral disagreement on aligned, commonly observed timesteps."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from python.common import load_metrics, save_json

CLUSTER_FEATURES=['command_rms','trajectory_rms','lane_disagreement','gap_delta',
                  'ttc_delta','hard_brakes_delta','progress_delta','jerk_delta']

def paired_divergences(baseline,ml,bt,mt):
    if not baseline.index.equals(ml.index) or not baseline.kind.equals(ml.kind):
        raise ValueError('Controllers must have identical IDs and scenario kinds')
    if bt.duplicated(['id','time']).any() or mt.duplicated(['id','time']).any():
        raise ValueError('Duplicate telemetry keys')
    if set(bt.id)!=set(baseline.index) or set(mt.id)!=set(ml.index):
        raise ValueError('Telemetry scenario IDs do not match metrics')
    pair=bt.merge(mt,on=['id','time'],suffixes=('_b','_m'),validate='one_to_one')
    if set(pair.id)!=set(baseline.index): raise ValueError('No common telemetry for some IDs')
    pair['command_squared']=(pair.command_m-pair.command_b)**2
    pair['trajectory_squared']=(pair.x_m-pair.x_b)**2+(pair.y_m-pair.y_b)**2
    pair['lane_disagreement']=(pair.lane_b!=pair.lane_m).astype(float)
    grouped=pair.groupby('id').agg(command_squared=('command_squared','mean'),
        trajectory_squared=('trajectory_squared','mean'),lane_disagreement=('lane_disagreement','mean'),
        paired_samples=('time','count'))
    out=baseline[['kind']].join(grouped)
    out['command_rms']=np.sqrt(out.pop('command_squared'))
    out['trajectory_rms']=np.sqrt(out.pop('trajectory_squared'))
    for result,source in [('gap_delta','min_following_gap'),('hard_brakes_delta','hard_brakes'),
                          ('progress_delta','progress'),('jerk_delta','rms_jerk')]:
        out[result]=ml[source]-baseline[source]
    out['ttc_delta']=ml.min_ttc.clip(upper=30)-baseline.min_ttc.clip(upper=30)
    out['collision_b']=baseline.collision; out['collision_m']=ml.collision
    out['divergent']=(out.command_rms>=1.) | (out.trajectory_rms>=5.) | (out.lane_disagreement>=.1) | (baseline.collision!=ml.collision)
    # Outcomes classify ML wins only after selection; they do not alter thresholds.
    out['ml_safety_win']=(baseline.collision>ml.collision)
    return out.reset_index()

def main():
    p=argparse.ArgumentParser()
    for name in ['baseline','ml','baseline-telemetry','ml-telemetry','out']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    cols=['id','time','command','x','y','lane']
    df=paired_divergences(load_metrics(a.baseline),load_metrics(a.ml),
                         pd.read_csv(a.baseline_telemetry,usecols=cols),pd.read_csv(a.ml_telemetry,usecols=cols))
    a.out.mkdir(parents=True,exist_ok=True)
    df.to_csv(a.out/'paired.csv',index=False)
    selected=df[df.divergent]
    selected.to_csv(a.out/'divergences.csv',index=False)
    wins=df[df.ml_safety_win].groupby('kind').size().to_dict()
    save_json(a.out/'divergence.json',{'paired_scenarios':len(df),'actual_divergences':len(selected),
        'selection':'command RMS >= 1 m/s² OR trajectory RMS >= 5 m OR lane disagreement >= 0.1 OR collision mismatch',
        'common_prefix_only':True,'ml_collision_wins_by_kind':{str(k):int(v) for k,v in wins.items()},
        'target_1500_reached':len(selected)>=1500})
    print(f'{len(selected)} actual divergences / {len(df)} paired scenarios')
if __name__=='__main__': main()