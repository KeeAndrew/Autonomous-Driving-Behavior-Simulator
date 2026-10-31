import argparse
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
from python.common import FEATURES, features, save_json, sha256

def export_forest(model, path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='ascii',newline='\n') as stream:
        stream.write(f'DRIVING_FOREST 1 {len(FEATURES)} {len(model.estimators_)}\n')
        for estimator in model.estimators_:
            t=estimator.tree_
            stream.write(f'{t.node_count}\n')
            for i in range(t.node_count):
                stream.write(f'{t.children_left[i]} {t.children_right[i]} {t.feature[i]} {t.threshold[i]:.17g} {t.value[i,0,0]:.17g}\n')

def check_parity(exe,model,path,frame,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    x=features(frame)
    pd.DataFrame(x,columns=FEATURES).to_csv(out/'parity_features.csv',index=False,float_format='%.17g')
    subprocess.run([str(exe),'--model',str(path),'--infer',str(out/'parity_features.csv'),
                    '--predictions',str(out/'cpp_predictions.csv')],check=True)
    cpp=pd.read_csv(out/'cpp_predictions.csv').prediction.to_numpy()
    expected=model.predict(x)
    error=float(np.max(np.abs(cpp-expected)))
    if error>1e-10:
        raise AssertionError(f'C++ inference parity error: {error}')
    return {'rows':len(x),'max_absolute_error':error,'tolerance':1e-10}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--train',type=Path,required=True)
    p.add_argument('--validation',type=Path,required=True)
    p.add_argument('--model',type=Path,default=Path('models/controller.forest'))
    p.add_argument('--out',type=Path,default=Path('results/training'))
    p.add_argument('--exe',type=Path,required=True)
    a=p.parse_args()
    train=pd.read_csv(a.train); val=pd.read_csv(a.validation)
    if set(train.id)&set(val.id): raise ValueError('Scenario leakage between train and validation')
    if not train.controller.eq('teacher').all() or not val.controller.eq('teacher').all():
        raise ValueError('Training requires explicit teacher demonstrations')
    x,y=features(train),train.label.to_numpy()
    xv,yv=features(val),val.label.to_numpy()
    if not np.isfinite(y).all() or not np.isfinite(yv).all(): raise ValueError('Nonfinite labels')
    model=RandomForestRegressor(n_estimators=32,max_depth=10,min_samples_leaf=8,
        max_features=1.0,random_state=41,n_jobs=-1)
    model.fit(x,y)
    export_forest(model,a.model)
    joblib.dump(model,a.model.with_suffix('.joblib'))
    pred=model.predict(xv)
    # Include actual split-boundary values to exercise <= and float32 semantics.
    parity=val.sample(n=min(1000,len(val)),random_state=42).copy()
    boundaries=[]
    base=parity.iloc[0].copy()
    for tree in model.estimators_[:4]:
        for f,t in zip(tree.tree_.feature,tree.tree_.threshold):
            if f>=0:
                for v in [np.float32(t),np.nextafter(np.float32(t),np.float32(-np.inf)),np.nextafter(np.float32(t),np.float32(np.inf))]:
                    row=base.copy(); row[FEATURES[f]]=float(v); boundaries.append(row)
    parity=pd.concat([parity,pd.DataFrame(boundaries)],ignore_index=True)
    info={'training_rows':len(train),'validation_rows':len(val),
        'training_scenarios':int(train.id.nunique()),'validation_scenarios':int(val.id.nunique()),
        'mae':float(mean_absolute_error(yv,pred)),'rmse':float(np.sqrt(mean_squared_error(yv,pred))),
        'hyperparameters':model.get_params(),'features':FEATURES,'normalization':'none; tree splits in physical units, finite feature caps',
        'feature_importance':dict(zip(FEATURES,model.feature_importances_.tolist())),
        'model_sha256':sha256(a.model),'train_sha256':sha256(a.train),'validation_sha256':sha256(a.validation),
        'parity':check_parity(a.exe,model,a.model,parity,a.out)}
    save_json(a.out/'training.json',info)
    print(f'Validation MAE {info["mae"]:.4f} m/s²; parity {info["parity"]}')
if __name__=='__main__': main()