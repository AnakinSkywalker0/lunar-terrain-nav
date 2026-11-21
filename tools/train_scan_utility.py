"""Fit v2 local correction utility on new collection data, never v1 test outcomes."""
import csv
import hashlib
import json
from pathlib import Path
import pickle
import shutil
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sim.scan_utility import FEATURES,TASK,predict_portable

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    data=Path((ROOT/'out/scan_utility/latest_collect.txt').read_text().strip())
    assert (data/'status.txt').read_text().startswith('Complete;')
    dest=ROOT/'out/scan_utility/model_v2';dest.mkdir(parents=True,exist_ok=False)
    runs=pd.read_csv(data/'summary.csv'); scans=pd.read_csv(data/'scans.csv')
    assert len(runs)==3840 and len(scans)==7680 and runs.id.is_unique
    df=scans.merge(runs[['id','site_id']],on='id',validate='many_to_one')
    assert not df[['id','scan_index']].duplicated().any()
    assert np.isfinite(df[list(FEATURES)].to_numpy()).all()
    eligible=df.valid & df.accepted
    df['split']=np.where(df.site_id.isin(['original','area01','area02']),'train','validation')
    train=df.split.eq('train') & eligible;val=df.split.eq('validation') & eligible
    X=df[list(FEATURES)].to_numpy(np.float32); y=df.optimal_gain.to_numpy(float)
    assert np.isfinite(y).all() and ((y>=0)&(y<=1)).all()
    tr=df[train];count=tr.groupby('id').id.transform('size').to_numpy()
    cases=tr.groupby('site_id').id.transform('nunique').to_numpy()
    weights=1/(count*cases);weights*=len(weights)/weights.sum()
    reports=[]; selected=None
    for seed in (11,22,33):
        model=RandomForestRegressor(n_estimators=32,max_depth=8,min_samples_leaf=12,random_state=seed,n_jobs=1)
        model.fit(X[train],y[train],sample_weight=weights)
        score=model.predict(X)
        reports.append(dict(seed=seed,validation_mae=float(mean_absolute_error(y[val],score[val])),
            validation_rmse=float(mean_squared_error(y[val],score[val])**.5)))
        if seed==11:selected=model;predictions=score
    bundle=dict(version=2,task=TASK,features=list(FEATURES),model_id='scan_utility_v2_seed11',trees=[])
    for estimator in selected.estimators_:
        t=estimator.tree_
        bundle['trees'].append(dict(feature=t.feature.tolist(),left=t.children_left.tolist(),right=t.children_right.tolist(),
                                   threshold=t.threshold.tolist(),value=t.value[:,0,0].tolist()))
    portable=predict_portable(bundle,X)
    difference=float(np.abs(portable-predictions).max());assert difference<1e-10
    (dest/'model.json').write_text(json.dumps(bundle,separators=(',',':'))+'\n')
    with (dest/'model.pkl').open('wb') as f:pickle.dump(selected,f)
    with (dest/'parity.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow((*FEATURES,'expected_gain'))
        for row,p in zip(X,predictions):w.writerow((*map(float,row),float(p)))
    df[['id','scan_index','site_id','split','valid','accepted','optimal_gain']].assign(predicted_gain=predictions).to_csv(dest/'predictions.csv',index=False)
    df[['id','scan_index',*FEATURES]].to_csv(dest/'features.csv',index=False)
    plan=json.loads((data/'plan.json').read_text())
    report=dict(task=TASK,fit_rows=int(train.sum()),validation_rows=int(val.sum()),
                training_sites=['original','area01','area02'],validation_sites=['area03','area04'],
                source=str(data),source_scans_sha256=sha(data/'scans.csv'),source_summary_sha256=sha(data/'summary.csv'),
                plan_sha256=sha(data/'plan.json'),protocol_sha256=sha(data/'protocol.md'),
                evaluation_sites=plan['evaluation_sites'],expected_evaluation_cases=plan['expected_evaluation_cases'],
                seeds=reports,selected_seed=11,selection_reason='Predetermined seed; policies selected later on complete development landings',
                portable_max_difference=difference,refit_on_validation=False,uses_prior_final_evaluation=False,
                validation_always_gain1_mae=float(mean_absolute_error(y[val],np.ones(int(val.sum())))),
                validation_training_mean_mae=float(mean_absolute_error(y[val],np.full(int(val.sum()),np.average(y[train],weights=weights)))),
                model_sha256=sha(dest/'model.json'),nodes=sum(t.tree_.node_count for t in selected.estimators_),
                feature_importances=dict(zip(FEATURES,map(float,selected.feature_importances_))))
    (dest/'training_report.json').write_text(json.dumps(report,indent=2)+'\n')
    assets=ROOT/'LANTERN/Assets/Experiments/ScanUtility'
    for name in ['model.json','parity.csv']:shutil.copyfile(dest/name,assets/name)
    for name in ['plan.json','protocol.md']:shutil.copyfile(data/name,dest/name)
    shutil.copyfile(Path(__file__),dest/Path(__file__).name)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
