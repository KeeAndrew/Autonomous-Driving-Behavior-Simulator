import os
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor
from python.common import FEATURES, features, load_metrics
from python.training.generate import generate
from python.training.train import export_forest, check_parity
from python.analysis.cluster import clustering_input
from python.analysis.divergence import paired_divergences, CLUSTER_FEATURES
from python.analysis.report import reduction, paired_bootstrap

ROOT=Path(__file__).resolve().parents[2]

def test_scenario_reproducibility_and_splits():
    a=generate(100,1001,0)
    pd.testing.assert_frame_equal(a,generate(100,1001,0))
    b=generate(100,2001,100000)
    assert not set(a.id)&set(b.id)
    assert a.gap.min()>=2 and a.kind.nunique()==8 and a.dt.eq(.05).all()
    assert not a.drop(columns=['id','seed']).equals(b.drop(columns=['id','seed']))

@pytest.mark.parametrize('count,seed',[(-1,1),(0,1),(5,-1)])
def test_invalid_generation(count,seed):
    with pytest.raises(ValueError): generate(count,seed)

def test_feature_contract():
    df=pd.DataFrame(np.zeros((2,12)),columns=FEATURES)
    assert features(df).shape==(2,12)
    df.loc[0,'closing']=np.inf
    with pytest.raises(ValueError): features(df)
    with pytest.raises(ValueError): features(pd.DataFrame({'speed':[2]}))

def test_metric_validation(tmp_path):
    p=tmp_path/'bad.csv'
    p.write_text('id,kind,controller,collision,hard_brakes,distance,rms_jerk,progress\n1,0,baseline,0,0,20,1,.1\n1,0,baseline,0,0,20,1,.1\n')
    with pytest.raises(ValueError): load_metrics(p)

def test_reductions_and_paired_ci():
    assert reduction(100,75)==25
    assert reduction(0,0) is None
    result=paired_bootstrap([1,1,1],[0,0,0],repeats=100)
    assert result['reduction_percent']==100 and result['difference_95ci']==[-1,-1]
    assert paired_bootstrap([0,0],[0,0],repeats=10)['reduction_95ci'] is None

@pytest.mark.parametrize('bad',[pd.DataFrame(),pd.DataFrame({'id':[1,1,2]})])
def test_cluster_validation(bad):
    with pytest.raises(ValueError): clustering_input(bad)

def test_divergence_selection_and_alignment():
    b=pd.DataFrame({'id':[1,2],'kind':[0,1],'collision':[0,0],'min_separation':[2.,3.],'min_following_gap':[10.,20.],
      'min_ttc':[np.inf,3.],'hard_brakes':[0,1],'progress':[1.,.8],'rms_jerk':[2.,3.]}).set_index('id')
    m=b.copy()
    bt=pd.DataFrame({'id':[1,2],'time':[.05,.05],'command':[0.,0.],'x':[1.,1.],'y':[0.,0.],'lane':[0,0]})
    mt=bt.copy();mt.loc[1,'command']=2.
    out=paired_divergences(b,m,bt,mt)
    assert out.divergent.tolist()==[False,True]
    assert np.isfinite(out[CLUSTER_FEATURES]).all().all()
    with pytest.raises(ValueError): paired_divergences(b,m.iloc[:1],bt,mt)


def simulator():
    candidate=Path(os.environ.get('SIM_EXE',ROOT/'build'/'Release'/'simulator.exe'))
    if not candidate.is_file() and 'SIM_EXE' not in os.environ:
        candidate=ROOT/'build-x64'/'Release'/'simulator.exe'
    if not candidate.is_file(): pytest.skip('Native simulator unavailable; set SIM_EXE after building')
    return candidate

def test_native_inference_parity(tmp_path):
    exe=simulator(); rng=np.random.default_rng(99); x=rng.normal(size=(500,12))
    model=RandomForestRegressor(n_estimators=5,max_depth=5,random_state=7).fit(x,3*x[:,0]-x[:,1])
    path=tmp_path/'tiny.forest';export_forest(model,path)
    result=check_parity(exe,model,path,pd.DataFrame(x,columns=FEATURES),tmp_path)
    assert result['max_absolute_error']<1e-10

def test_native_end_to_end_and_invalid_cli(tmp_path):
    exe=simulator(); scenario=tmp_path/'scenarios.csv';generate(8,77).to_csv(scenario,index=False)
    outputs=[]
    for mode in ['baseline','teacher','hybrid']:
        out=tmp_path/f'{mode}.csv'; subprocess.run([str(exe),'--scenarios',str(scenario),'--controller',mode,'--metrics',str(out)],check=True)
        df=load_metrics(out); assert len(df)==8 and df.distance.ge(0).all(); outputs.append(df)
    assert all(outputs[0].index.equals(df.index) for df in outputs)
    assert subprocess.run([str(exe),'--unknown','x'],capture_output=True).returncode!=0
    assert subprocess.run([str(exe),'--scenarios',str(scenario),'--controller','ml','--metrics',str(tmp_path/'missing.csv')],capture_output=True).returncode!=0

def test_observed_regressions(tmp_path):
    import json
    fixture=ROOT/'data'/'sample_scenarios'/'regressions.csv'
    expected=fixture.with_suffix('.json')
    if not expected.is_file(): pytest.skip('Failure-derived regression fixture has not been captured yet')
    exe=simulator(); reference=json.loads(expected.read_text())
    for mode in ['baseline','hybrid']:
        out=tmp_path/f'regression_{mode}.csv'
        subprocess.run([str(exe),'--scenarios',str(fixture),'--controller',mode,'--metrics',str(out)],check=True)
        actual=load_metrics(out)
        for row in reference[mode]:
            got=actual.loc[row['id']]
            assert int(got.collision)==row['collision']
            assert int(got.hard_brakes)==row['hard_brakes']
            assert got.distance==pytest.approx(row['distance'],abs=1e-7)