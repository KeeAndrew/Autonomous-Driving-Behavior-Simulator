"""Shared schema and validation: names/order are a versioned C++ inference contract."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

FEATURES = ['obs_speed', 'target', 'obs_gap', 'lead_speed', 'closing', 'obs_ttc',
            'ped_gap', 'ped_eta', 'adj_front', 'adj_rear', 'adj_closing', 'obs_acceleration']
KINDS = ['following', 'sudden_braking', 'stop_go', 'delayed_obstacle',
         'pedestrian', 'occluded_pedestrian', 'lane_change', 'unsafe_merge']
SCHEMA = ['id','kind','seed','ego_speed','target_speed','gap','lead_speed','brake_time',
          'lead_brake','ped_x','ped_y','ped_speed','visible_time','adj_x','adj_speed',
          'dt','duration','lane_width','destination']

def features(frame):
    missing = set(FEATURES) - set(frame.columns)
    if missing:
        raise ValueError(f'Missing features: {sorted(missing)}')
    values = frame[FEATURES].to_numpy(dtype=np.float64)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError('Features must be nonempty and finite')
    return values

def load_metrics(path):
    df = pd.read_csv(path)
    required = {'id','kind','controller','collision','hard_brakes','distance','rms_jerk','progress'}
    if not required.issubset(df) or df.empty or df.id.duplicated().any():
        raise ValueError('Metrics require unique scenario IDs and complete schema')
    if not df.collision.isin([0,1]).all() or (df.hard_brakes < 0).any():
        raise ValueError('Invalid metrics')
    return df.set_index('id').sort_index()

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')