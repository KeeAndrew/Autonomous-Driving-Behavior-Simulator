"""Record validation evidence and predeclared hybrid logic before held-out execution."""
import argparse
from pathlib import Path
import pandas as pd
from python.common import save_json, sha256, KINDS

def main():
    p=argparse.ArgumentParser();p.add_argument('--paired',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); df=pd.read_csv(a.paired)
    wins=df[df.collision_b.gt(df.collision_m)]
    losses=df[df.collision_b.lt(df.collision_m)]
    save_json(a.out,{'validation_scenarios':len(df),'ml_collision_wins':len(wins),'ml_collision_losses':len(losses),
        'wins_by_kind':{KINDS[int(k)]:int(v) for k,v in wins.kind.value_counts().items()},
        'paired_sha256':sha256(a.paired),'controller_source_sha256':sha256(Path('src/controllers/controllers.cpp')),
        'hybrid_logic':'baseline plus 1.6s relative-speed headway; TTC < 3s braking; pedestrian stopping distance v²/6 + 8m',
        'status':'Frozen hypothesis before held-out evaluation; no parameters fit to evaluation results',
        'causal_limit':'Validation identifies related cases; no claim that imitation discovers novel behavior or proves causality'})
    print(f'Validation evidence: {len(wins)} ML collision wins, {len(losses)} losses. Hybrid hypothesis frozen.')
if __name__=='__main__':main()