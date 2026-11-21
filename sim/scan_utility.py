"""Portable regression inference and truth-only label calculation for utility v2."""
import math
import numpy as np

FEATURES=('normalized_rms','confidence_feature','correction_norm_m','agl_feature_m','consistency_m','has_previous')
TASK='scan_optimal_gain_v2'


def optimal_gain(before,proposed,norm):
    if not all(math.isfinite(x) and x>=0 for x in (before,proposed,norm)):
        raise ValueError('Nonfinite or negative evaluation distance')
    return 1. if norm<.5 else float(np.clip((before*before-proposed*proposed+norm*norm)/(2*norm*norm),0,1))


def predict_portable(bundle,X):
    if bundle.get('task')!=TASK or tuple(bundle.get('features',()))!=FEATURES or bundle.get('version')!=2:
        raise ValueError('Wrong utility schema/task')
    X=np.asarray(X,dtype=np.float32)
    if X.ndim!=2 or X.shape[1]!=6 or not np.isfinite(X).all():
        raise ValueError('Invalid utility feature matrix')
    scores=[]
    for row in X:
        total=0.
        for tree in bundle['trees']:
            node=0
            while tree['left'][node]>=0:
                node=tree['left'][node] if float(row[tree['feature'][node]])<=tree['threshold'][node] else tree['right'][node]
            total+=tree['value'][node]
        scores.append(float(np.clip(total/len(bundle['trees']),0,1)))
    return np.asarray(scores)


def policy_gain(policy,prediction,norm,agl,valid=True,accepted=True):
    if not valid or not accepted:return 0.
    if policy in ('off','collect'):return 0.
    if policy=='geometric':return 1.
    if policy!='bounded' and not math.isfinite(prediction):return 0.
    p=float(np.float32(np.clip(prediction,0,1)))
    gain=float(p>=.5) if policy=='utility_hard' else p if policy=='utility_soft' else (1. if p>=.75 else p) if policy=='utility_hybrid' else 1. if policy=='bounded' else 0.
    if policy in ('bounded','utility_hybrid'):gain=min(gain,max(5,.5*agl)/max(.001,norm))
    return gain
