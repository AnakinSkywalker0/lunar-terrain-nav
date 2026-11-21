"""Train the explicitly authorized small scan-trust experiment, not the old pipeline."""
import csv
import hashlib
import json
from pathlib import Path
import pickle
import shutil
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sim.scan_trust import FEATURES, TASK


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(y, accept, geometric, score=None):
    bad, safe = y.astype(bool), ~y.astype(bool)
    gb, gs = geometric & bad, geometric & safe
    a_bad, r_safe = int((accept & bad).sum()), int((~accept & gs).sum())
    out = dict(n=len(y), bad=int(bad.sum()), geometric_accepted=int(geometric.sum()),
               accepted=int(accept.sum()), accepted_bad=a_bad, rejected_safe=r_safe,
               bad_accept_rate=a_bad / max(1, int(gb.sum())),
               safe_reject_rate=r_safe / max(1, int(gs.sum())))
    out['objective'] = 4*out['bad_accept_rate'] + out['safe_reject_rate']
    if score is not None:
        out['auc'] = float(roc_auc_score(y, score)) if len(np.unique(y))==2 else None
        out['average_precision'] = float(average_precision_score(y, score))
        out['brier_uncalibrated'] = float(brier_score_loss(y, score))
        out['calibration_bins'] = []
        for lo in np.arange(0,1,.1):
            mask = (score>=lo)&(score < lo+.1 if lo<.9 else score<=1)
            if mask.any(): out['calibration_bins'].append(dict(n=int(mask.sum()),
                mean_score=float(score[mask].mean()), bad_fraction=float(y[mask].mean())))
    return out


def rank(m):
    return (m['objective'], m['safe_reject_rate'], m['bad_accept_rate'])


def portable_model(model, name, threshold):
    out = dict(task=TASK,features=list(FEATURES),model_id='scan_trust_v1_'+name,
               bad_score_threshold=float(threshold), version=1)
    if name=='logistic':
        scale, lr = model.steps[0][1], model.steps[1][1]
        out.update(kind='logistic', center=scale.mean_.tolist(), scale=scale.scale_.tolist(),
                   weights=lr.coef_[0].tolist(), intercept=float(lr.intercept_[0]))
    else:
        out.update(kind='forest',trees=[])
        for estimator in model.estimators_:
            tree=estimator.tree_; values=tree.value[:,0,:]
            out['trees'].append(dict(feature=tree.feature.tolist(),left=tree.children_left.tolist(),
                right=tree.children_right.tolist(),threshold=tree.threshold.tolist(),
                bad=(values[:,1]/values.sum(axis=1)).tolist()))
    return out


def portable_score(bundle, X):
    X=np.asarray(X,dtype=np.float32)
    if bundle['kind']=='logistic':
        z=((X.astype(float)-bundle['center'])/bundle['scale'])@np.array(bundle['weights'])+bundle['intercept']
        return 1/(1+np.exp(-np.clip(z,-700,700)))
    scores=[]
    for row in X:
        total=0.
        for tree in bundle['trees']:
            node=0
            while tree['left'][node]>=0:
                node=tree['left'][node] if row[tree['feature'][node]]<=tree['threshold'][node] else tree['right'][node]
            total+=tree['bad'][node]
        scores.append(total/len(bundle['trees']))
    return np.array(scores)


def main():
    data=ROOT/'out/scan_trust/20261022_preparation_v1'
    out=ROOT/'out/scan_trust/20261022_model_v1'
    out.mkdir(parents=True,exist_ok=False)
    started=time.time()
    source=json.loads((data/'manifest.json').read_text())
    for name,expected in source['artifact_sha256'].items():
        assert digest(data/name)==expected, name
    df=pd.read_csv(data/'features.csv').merge(pd.read_csv(data/'labels.csv'),on='sample_id',validate='one_to_one')
    df=df.merge(pd.read_csv(data/'groups.csv'),on='sample_id',validate='one_to_one')
    df=df.merge(pd.read_csv(data/'shadow_decisions.csv')[['sample_id','geometric_accept']],on='sample_id',validate='one_to_one')
    X=df[list(FEATURES)].to_numpy(dtype=np.float32); y=df.bad_match.to_numpy(dtype=int)
    geo=df.geometric_accept.to_numpy(dtype=bool)
    train=df.split.eq('train').to_numpy() & geo
    val=df.split.eq('validation').to_numpy()
    # Every area contributes equally, every case equally within an area.
    tr=df.loc[train].copy()
    counts=tr.groupby('run_id').sample_id.transform('size').to_numpy()
    runs_per_area=tr.groupby('site_id').run_id.transform('nunique').to_numpy()
    weights=1/(counts*runs_per_area); weights*=len(weights)/weights.sum()
    candidates={}; validation=[]; sensitivity=[]
    for name in ('logistic','forest_full','forest_residual'):
        for seed in ((11,) if name=='logistic' else (11,22,33)):
            Xt=X[train].copy()
            if name=='forest_residual': Xt[:,3:]=0
            if name=='logistic':
                model=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=2000,random_state=seed))
                model.fit(Xt,y[train],logisticregression__sample_weight=weights)
            else:
                model=RandomForestClassifier(n_estimators=32,max_depth=6,min_samples_leaf=20,
                                             n_jobs=1,random_state=seed)
                model.fit(Xt,y[train],sample_weight=weights)
                if name=='forest_residual':
                    assert all(not np.isin(t.tree_.feature,[3,4,5]).any() for t in model.estimators_)
            score=model.predict_proba(X)[:,1]
            if seed==11:
                trials=[]
                for threshold in np.linspace(.02,.98,25):
                    m=metrics(y[val],geo[val]&(score[val]<threshold),geo[val],score[val])
                    trials.append(dict(name=name,threshold=float(threshold),**m))
                best=min(trials,key=rank)
                candidates[name]=(model,best,score)
                validation.extend(trials)
            else:
                threshold=candidates[name][1]['threshold']
                sensitivity.append(dict(name=name,seed=seed,
                    **metrics(y[val],geo[val]&(score[val]<threshold),geo[val],score[val])))
    rule_trials=[]
    for rms in np.linspace(.5,8,15):
        for conf in np.linspace(.35,.99,5):
            accept=geo&(X[:,1]<=rms)&(X[:,2]>=conf)
            rule_trials.append(dict(name='rule',max_rms_m=float(rms),min_confidence=float(conf),
                                    **metrics(y[val],accept[val],geo[val])))
    rule=min(rule_trials,key=rank)
    name=min(candidates,key=lambda k:rank(candidates[k][1]))
    model,best,score=candidates[name]
    bundle=portable_model(model,name,best['threshold'])
    # Validate portable inference for every archived feature row after freezing.
    exported=portable_score(bundle,X)
    difference=float(np.max(np.abs(exported-score)))
    assert difference<1e-10, difference
    assert np.array_equal(exported<best['threshold'],score<best['threshold'])
    report=dict(selected=name,selection=best,rule=rule,validation_trials=validation,
                rule_trials=rule_trials,forest_seed_sensitivity=sensitivity,
                splits={},data_manifest_sha256=digest(data/'manifest.json'),
                protocol_sha256=digest(ROOT/'docs/SCAN_TRUST_PROTOCOL_V1.md'),
                portable_max_score_difference=difference,fit_rows=int(train.sum()),
                train_sites=['original','area01','area02'],refit_on_validation_or_test=False)
    predictions=[]
    ruleaccept=geo&(X[:,1]<=rule['max_rms_m'])&(X[:,2]>=rule['min_confidence'])
    for split in ('train','validation','retrospective_test'):
        mask=df.split.eq(split).to_numpy()
        report['splits'][split]={
            'geometric':metrics(y[mask],geo[mask],geo[mask]),
            'rule':metrics(y[mask],ruleaccept[mask],geo[mask])}
        for key,(_,selection,scores) in candidates.items():
            report['splits'][split][key]=metrics(y[mask],geo[mask]&(scores[mask]<selection['threshold']),geo[mask],scores[mask])
    df[['sample_id','split','site_id','condition']].assign(bad_label=y,bad_score=score,
        geometric_accept=geo,rule_accept=ruleaccept,ml_accept=geo&(score<best['threshold'])).to_csv(out/'predictions.csv',index=False)
    # Fixed fixtures exercise all historical inputs. Labels never cross into inference.
    with (out/'parity.csv').open('w',newline='') as f:
        writer=csv.writer(f); writer.writerow((*FEATURES,'geometric_accept','expected_bad_score','expected_accept'))
        for row,g,s in zip(X,geo,score):
            writer.writerow((*map(float,row),int(g),float(s),int(g and s<best['threshold'])))
    (out/'model.json').write_text(json.dumps(bundle,separators=(',',':'))+'\n')
    (out/'rule.json').write_text(json.dumps(dict(max_rms_m=rule['max_rms_m'],min_confidence=rule['min_confidence']),indent=2)+'\n')
    with (out/'model.pkl').open('wb') as f: pickle.dump(model,f)
    report['elapsed_seconds']=time.time()-started
    report['model_sha256']=digest(out/'model.json')
    report['artifacts_sha256']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
    (out/'training_report.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copyfile(ROOT/'docs/SCAN_TRUST_PROTOCOL_V1.md',out/'protocol.md')
    shutil.copyfile(Path(__file__),out/Path(__file__).name)
    dest=ROOT/'LANTERN/Assets/Experiments/ScanTrust'
    dest.mkdir(parents=True,exist_ok=True)
    for name in ('model.json','rule.json','parity.csv'):
        shutil.copyfile(out/name,dest/name)
    print(json.dumps({k:report[k] for k in ('selected','selection','rule','fit_rows','portable_max_score_difference','elapsed_seconds')},indent=2))


if __name__=='__main__': main()
