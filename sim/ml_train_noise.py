"""Train the error-size model used by ml2's predicted-noise option (models/err_reg_v3.pkl).

Target: t = log1p(|reading - truth| / sigma_nominal), predicted from the same 22 features as the classifier.
The engine turns the prediction into a noise standard deviation  s = sigma_nominal * expm1(t_hat)  and uses s**2 as a floor
for the measurement variance of accepted flagged readings. This is what lets the filter stop over-trusting readings when the
altimeter is much noisier than nominal (the 'shadow + noisy' scenario).

  python sim/ml_train_noise.py       uses the cached rows (out/cache/ml_data_v3.npz); about 1 minute
"""
import os
import pickle
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ml_features as MF  # noqa: E402
import ml_labels as L  # noqa: E402
import ml_train as T  # noqa: E402

PATH = os.path.join(L.ROOT, "models", "err_reg_v3.pkl")


def main():
    import sklearn
    from scipy.stats import spearmanr
    from sklearn.ensemble import HistGradientBoostingRegressor
    t0 = time.time()
    X, y_old, w, sc = L.load()
    err = X[:, L.N2 + 2]; sig_nom = X[:, L.N2 + 4]
    t = np.log1p(np.abs(err) / sig_nom)
    F = T.build(X).astype(np.float32)
    mk = lambda: HistGradientBoostingRegressor(max_iter=150, learning_rate=0.1, max_leaf_nodes=31, random_state=0)
    te = w == 26
    m = mk().fit(F[~te], t[~te])
    th = np.clip(m.predict(F[te]), 0.0, 7.0)
    s_pred = sig_nom[te] * np.expm1(th)
    chk = {}
    for k, name in enumerate(L.SCEN):
        s = sc[te] == k
        if s.any():
            ratio = np.abs(err[te][s]) / np.maximum(s_pred[s], 1e-6)
            chk[name] = dict(spearman=float(spearmanr(th[s], t[te][s])[0]), median_ratio_abs_err_over_pred=float(np.median(ratio)),
                             frac_err_below_pred=float((np.abs(err[te][s]) <= s_pred[s]).mean()),
                             frac_err_below_3x_pred=float((np.abs(err[te][s]) <= 3 * s_pred[s]).mean()))
    print("hold-out (train 21-25, test 26):")
    for k, v in chk.items():
        print(f"  {k:13s} spearman {v['spearman']:.3f}  median |err|/pred {v['median_ratio_abs_err_over_pred']:.2f}  "
              f"|err|<=pred {v['frac_err_below_pred']:.2f}  |err|<=3*pred {v['frac_err_below_3x_pred']:.2f}", flush=True)
    final = mk().fit(F, t)
    pickle.dump(dict(model=final, feature_names=MF.NAMES, sklearn_version=sklearn.__version__,
                     target="log1p(|reading - truth| / sigma_nominal); s = sigma_nominal * expm1(clip(pred, 0, 7))", holdout_check=chk), open(PATH, "wb"))
    print(f"saved {PATH} ({os.path.getsize(PATH)/1024:.0f} KB) in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
