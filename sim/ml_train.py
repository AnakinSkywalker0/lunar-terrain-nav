"""Train and save the 'ml2' fault classifier (corrected label, map-consistency + vertical speed + history features).

  python sim/ml_train.py            -> models/fault_clf_v3.pkl  (small, a few hundred KB; safe to commit)

Training data: the same 6 procedural worlds as the original classifier (Site04 is never used). If the cached rows
(out/cache/ml_data_v3.npz) do not exist they are generated first (about 10-15 minutes with 4 workers).
Label: reading error > 5 x TRUE noise sigma + 1 m (see sim/ml_labels.py for why the old label was wrong).
Trained WITHOUT class weights so that predict_proba is usable as a probability (the engine uses it to inflate noise).
A world-26 hold-out check (train on 21-25) is reported and stored next to the model.
"""
import os
import pickle
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ml_features as MF  # noqa: E402
import ml_labels as L  # noqa: E402

ROOT = L.ROOT
MODEL_PATH = os.path.join(ROOT, "models", "fault_clf_v3.pkl")


def build(X):
    pers = L.persistence(X)
    return np.concatenate([X[:, :L.N2], X[:, L.N2 + 6:L.N2 + 7], pers], axis=1)


def ece(y, p, bins=10):
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum((idx == b).mean() * abs(p[idx == b].mean() - y[idx == b].mean()) for b in range(bins) if (idx == b).any()))


def main():
    import sklearn
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import brier_score_loss, roc_auc_score
    t0 = time.time()
    X, y_old, w, sc = L.load()
    err = X[:, L.N2 + 2]; sig_true = X[:, L.N2 + 3]
    y = (np.abs(err) > 5.0 * sig_true + 1.0).astype(np.int8)
    F = build(X).astype(np.float32)
    assert F.shape[1] == len(MF.NAMES), (F.shape, len(MF.NAMES))
    held = 26
    te = w == held
    mk = lambda: HistGradientBoostingClassifier(max_iter=150, learning_rate=0.1, max_leaf_nodes=31, random_state=0)
    m = mk().fit(F[~te], y[~te])
    p = m.predict_proba(F[te])[:, 1]
    chk = dict(held_out_world=held, auc=float(roc_auc_score(y[te], p)), brier=float(brier_score_loss(y[te], p)), ece=ece(y[te], p),
               acc=float(((p > 0.5) == y[te]).mean()), fault_frac=float(y[te].mean()))
    per = {}
    for k, name in enumerate(L.SCEN):
        s = te & (sc == k)
        if s.any() and 0 < y[s].mean() < 1:
            per[name] = float(roc_auc_score(y[s], m.predict_proba(F[s])[:, 1]))
    chk["auc_by_scenario"] = per
    print("hold-out check (train 21-25, test 26):", chk, flush=True)
    final = mk().fit(F, y)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    pickle.dump(dict(model=final, feature_names=MF.NAMES, window=MF.WINDOW, sklearn_version=sklearn.__version__,
                     label="|reading - truth| > 5*true_noise_sigma + 1 m (1 = outlier/fault)", trained_on_worlds=sorted(set(w.tolist())),
                     rows=int(len(y)), holdout_check=chk), open(MODEL_PATH, "wb"))
    print(f"saved {MODEL_PATH} ({os.path.getsize(MODEL_PATH)/1024:.0f} KB) in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
