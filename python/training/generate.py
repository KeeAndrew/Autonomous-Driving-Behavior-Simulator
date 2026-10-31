"""Stratified independent scenarios. No simulator outcomes enter generation."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from python.common import SCHEMA, KINDS, save_json, sha256

def generate(count, seed, id_offset=0):
    if count < 1 or seed < 0 or id_offset < 0:
        raise ValueError('Count must be positive, seed and offset nonnegative')
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(count):
        kind = i % 8
        speed = rng.uniform(8,28)
        gap = rng.uniform(12,85)
        lead = rng.uniform(4,25)
        ped_x, ped_y, ped_speed = rng.uniform(25,100), rng.uniform(-8,-2), rng.uniform(.8,2.2)
        visible = 0.
        if kind == 3:
            lead = 0.
            visible = rng.uniform(.2,1.5)
            gap = rng.uniform(30,100)
        if kind in [4,5]:
            gap = 160.
            lead = 25.
            if kind == 5:
                visible = rng.uniform(.5,2.5)
        adjacent = rng.uniform(-90,-20) if kind != 7 else rng.uniform(-30,-6)
        adj_speed = rng.uniform(12,32) if kind != 7 else rng.uniform(25,40)
        if kind == 6:
            lead = rng.uniform(4,12)
        rows.append([id_offset+i, kind, seed, speed, rng.uniform(max(15,speed),32), gap,
                     lead, rng.uniform(1,6), -rng.uniform(2,8), ped_x,ped_y,ped_speed,
                     visible,adjacent,adj_speed,.05,15.,3.6,200.])
    return pd.DataFrame(rows, columns=SCHEMA)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--count', type=int, default=10000)
    p.add_argument('--seed', type=int, default=3001)
    p.add_argument('--id-offset', type=int, default=200000)
    a=p.parse_args()
    df=generate(a.count,a.seed,a.id_offset)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out,index=False,float_format='%.12g')
    save_json(a.out.with_suffix('.manifest.json'), {'count':len(df),'seed':a.seed,
        'id_offset':a.id_offset,'scenario_sha256':sha256(a.out),
        'distribution':{KINDS[k]:int(n) for k,n in df.kind.value_counts().items()},
        'generator':'numpy.default_rng; uniform parameter draws; equal stratum allocation'})
    print(f'Generated {len(df)} scenarios: {a.out}')
if __name__=='__main__': main()