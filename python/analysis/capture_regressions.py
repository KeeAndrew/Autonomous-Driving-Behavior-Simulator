"""Explicitly capture fixed validation failures; never silently rewrite fixtures in tests."""
import argparse
from pathlib import Path
import subprocess
import pandas as pd
from python.common import save_json, sha256, load_metrics

def main():
    p=argparse.ArgumentParser()
    for field in ['scenarios','paired','exe','out']: p.add_argument('--'+field,type=Path,required=True)
    a=p.parse_args(); scenario=pd.read_csv(a.scenarios); pairs=pd.read_csv(a.paired)
    # Prioritize actual outcome disagreements, then actual command divergences, across strata.
    pairs=pairs[pairs.divergent].copy()
    pairs['mismatch']=pairs.collision_b.ne(pairs.collision_m)
    selected=pairs.sort_values(['mismatch','command_rms'],ascending=False).groupby('kind',sort=True).head(2).head(16)
    if selected.empty: raise ValueError('No real validation divergences to capture')
    fixture=scenario[scenario.id.isin(selected.id)].sort_values('id')
    a.out.parent.mkdir(parents=True,exist_ok=True); fixture.to_csv(a.out,index=False,float_format='%.12g')
    reference={'provenance':{'scenarios_sha256':sha256(a.scenarios),'paired_sha256':sha256(a.paired),
        'reason':'Actual validation divergences; top 2 by collision mismatch then command RMS per kind',
        'cases':selected[['id','kind','collision_b','collision_m','command_rms']].to_dict('records')}}
    work=Path('results/regression_capture');work.mkdir(parents=True,exist_ok=True)
    for mode in ['baseline','hybrid']:
        out=work/f'{mode}.csv'
        subprocess.run([str(a.exe),'--scenarios',str(a.out),'--controller',mode,'--metrics',str(out)],check=True)
        reference[mode]=load_metrics(out).reset_index()[['id','collision','hard_brakes','distance']].to_dict('records')
    save_json(a.out.with_suffix('.json'),reference)
    print(f'Captured {len(fixture)} actual validation divergence regression cases')
if __name__=='__main__':main()