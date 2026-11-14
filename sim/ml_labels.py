"""Experiment: are the fault labels right, and do history + vertical-speed features help?

Why this exists (found by reading sim/engine.py):
  * The label `fault_lbl` (engine.py:335) is |reading - truth| > 5*NOMINAL_sigma + 1. In the 'shadow + noisy' scenario the
    altimeter noise is multiplied by 8 (engine.py:328) but the label still uses the nominal sigma, so about half of the
    perfectly valid (just noisy) readings are labelled 'fault'. That is label noise, and it teaches a classifier to reject
    valid noisy readings.
  * The classifier sees only 4 past innovations (1 s); injected fault bursts last 2-5 s.
  * It is never given the vertical speed, which explains stale (delayed) readings: innovation ~ -delay * vertical speed.

What it does
  1. Collects the same rows as pipeline.stage_ml, plus ground-truth side information (true error, true noise sigma, burst
     flag, stale offset, run id, time step, vertical speed) that the simulator already computes. This is done WITHOUT editing
     engine.py: a patched `_features` reads the caller's local variables (sys._getframe). That is a hack for analysis only;
     the clean version is a 3-line hook in engine.py once the simulation owner agrees.
  2. Compares labels (old vs new) and measures how many valid readings the old label calls faults.
  3. Builds history ('persistence') features from earlier flagged readings of the same descent (causal: past rows only).
  4. Leave-one-world-out comparison of feature sets / labels, evaluated against the NEW label, per scenario.
  5. Regression of the reading's error magnitude (what the filter needs to set its noise).

Usage: python sim/ml_labels.py      Output: out/ml_labels/   Cache: out/cache/ml_data_v3.npz
"""
import json
import multiprocessing as mp
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import ml_eval as E  # noqa: E402  (reused: features_v2, SCENARIOS list, pipeline handle)

ROOT = E.ROOT
CACHE = os.path.join(ROOT, "out", "cache", "ml_data_v3.npz")
OUT = os.path.join(ROOT, "out", "ml_labels")
SCEN = E.SCENARIOS
EXTRA = ["run", "tt", "err", "sig_true", "sig_nom", "burst", "vz", "stale"]
N2 = len(E.FEATURES) + len(E.FEATURES_V2_EXTRA)        # 15 features from ml_eval's v2 set
F_V1 = E.FEATURES
F_V2 = E.FEATURES + E.FEATURES_V2_EXTRA
PERS = ["n_prev", "mean_z_prev", "std_z_prev", "mean_abs_z_prev", "frac_same_sign", "dt_prev"]
WINDOW = 40  # steps of 0.25 s = 10 s of history


def features_with_truth(nu, S0, R, stats, x_est, rad, agl_true, nu_hist):
    """Same call signature as engine._features. Returns the 15 v2 features + 8 ground-truth side columns."""
    base = E.features_v2(nu, S0, R, stats, x_est, rad, agl_true, nu_hist)
    L = sys._getframe(1).f_locals            # the simulate() frame: has r_true, r_src, r_meas, sig_nom, mult, burst, tt
    n = len(nu)
    sig_nom = np.broadcast_to(L["sig_nom"], (n,))
    mult = np.broadcast_to(L["mult"], (n,))
    extra = np.stack([np.arange(n), np.full(n, L["tt"]), L["r_meas"] - L["r_true"], sig_nom * mult, sig_nom,
                      L["burst"].astype(float), x_est[:, 5], L["r_src"] - L["r_true"]], axis=1)
    return np.concatenate([base, extra], axis=1)


engine._features = features_with_truth     # applied in every process (spawned workers re-import this module)


def collect():
    P = E.P
    P.warm([("proc", s) for s in P.TRAIN_SEEDS])
    jobs = []
    for s in P.TRAIN_SEEDS:
        for name in SCEN:
            jobs.append(dict(world=("proc", s), scen=engine.SCENARIOS[name], judge="pitfal", n=100, seed=1000 + s,
                             collect=True, tag=f"{s}|{name}"))
    res = P.pmap(jobs, workers=E.WORKERS)
    Xs, yo, ws, ss = [], [], [], []
    for r in res:
        seed, name = r["tag"].split("|")
        for X, y in r["_collect"]:
            Xs.append(X.astype(np.float32)); yo.append(np.asarray(y).astype(np.int8))
            ws.append(np.full(len(y), int(seed), dtype=np.int16)); ss.append(np.full(len(y), SCEN.index(name), dtype=np.int8))
    X = np.concatenate(Xs); y_old = np.concatenate(yo); w = np.concatenate(ws); sc = np.concatenate(ss)
    # unique descent id (world, scenario, run) and make sure it survives float32 (< 2^24)
    X[:, N2] = ((w.astype(np.int64) - 21) * 4 + sc) * 100 + X[:, N2]
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    np.savez_compressed(CACHE, X=X, y_old=y_old, world=w, scen=sc)
    return X, y_old, w, sc


def load():
    if os.path.exists(CACHE):
        d = np.load(CACHE)
        return d["X"], d["y_old"], d["world"], d["scen"]
    return collect()


def persistence(X):
    """History features from EARLIER flagged readings of the same descent within the last WINDOW steps (causal)."""
    run = X[:, N2].astype(np.int64); tt = X[:, N2 + 1].astype(np.int64)
    key = run * 10000 + tt
    order = np.argsort(key, kind="stable")
    k = key[order]; z = X[order, 0].astype(np.float64); t = tt[order]
    lo = np.searchsorted(k, k - WINDOW, side="left")
    idx = np.arange(len(k))
    n_prev = idx - lo

    def pref(a):
        return np.concatenate([[0.0], np.cumsum(a)])
    c1, c2, ca, cs = pref(z), pref(z * z), pref(np.abs(z)), pref(np.sign(z))
    cnt = np.maximum(n_prev, 1)
    s1 = c1[idx] - c1[lo]; s2 = c2[idx] - c2[lo]; sa = ca[idx] - ca[lo]; ss = cs[idx] - cs[lo]
    mean = np.where(n_prev > 0, s1 / cnt, 0.0)
    std = np.where(n_prev > 1, np.sqrt(np.maximum(s2 / cnt - (s1 / cnt) ** 2, 0.0)), 0.0)
    mabs = np.where(n_prev > 0, sa / cnt, 0.0)
    same = np.where(n_prev > 0, (n_prev + np.sign(z) * ss) / 2.0 / cnt, 0.5)
    dt = np.full(len(k), float(WINDOW)); has = n_prev > 0
    dt[has] = np.minimum(t[has] - np.concatenate([[0], t[:-1]])[has], WINDOW)
    out = np.empty((len(k), 6), dtype=np.float32)
    out[order] = np.stack([n_prev, mean, std, mabs, same, dt], axis=1)
    return out


def auc_by_scenario(y, p, sc):
    from sklearn.metrics import roc_auc_score
    r = {}
    for k, name in enumerate(SCEN):
        m = sc == k
        if m.any() and 0 < y[m].mean() < 1:
            r[name] = roc_auc_score(y[m], p[m])
    return r


def main():
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    from sklearn.metrics import roc_auc_score
    from scipy.stats import spearmanr
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    X, y_old, w, sc = load()
    err = X[:, N2 + 2]; sig_true = X[:, N2 + 3]; sig_nom = X[:, N2 + 4]; burst = X[:, N2 + 5] > 0.5
    y_new = (np.abs(err) > 5.0 * sig_true + 1.0).astype(np.int8)
    print(f"rows {len(y_new)}  load {time.time()-t0:.0f}s", flush=True)

    # ---------- 1. label audit
    rows = []
    for k, name in enumerate(SCEN):
        m = sc == k
        valid_noburst = m & ~burst
        rows.append(dict(scenario=name, rows=int(m.sum()), old_fault=float(y_old[m].mean()), new_fault=float(y_new[m].mean()),
                         burst=float(burst[m].mean()),
                         old_label_fault_among_noburst=float(y_old[valid_noburst].mean()),
                         new_label_fault_among_noburst=float(y_new[valid_noburst].mean())))
    audit = pd.DataFrame(rows)
    audit.to_csv(os.path.join(OUT, "label_audit.csv"), index=False)
    print("\nLABEL AUDIT (fractions of gate-failing rows)\n", audit.round(3).to_string(index=False), flush=True)

    # ---------- 2. features
    pers = persistence(X)
    Xv1 = X[:, :len(F_V1)]
    Xv2 = X[:, :N2]
    vz = X[:, N2 + 6:N2 + 7]
    Xv3 = np.concatenate([Xv2, vz, pers], axis=1)
    arms = [("A  v1 feats, OLD label", Xv1, y_old), ("B  v1 feats, NEW label", Xv1, y_new),
            ("C  v2 feats, NEW label", Xv2, y_new), ("D  v3 feats (v2+vz+history), NEW label", Xv3, y_new)]

    # ---------- 3. leave-one-world-out
    res = []
    worlds = sorted(set(w.tolist()))
    for name, Xa, ya in arms:
        pred = np.zeros(len(ya), dtype=np.float32)
        per_world = []
        for held in worlds:
            te = w == held
            m = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.1, max_leaf_nodes=31, class_weight="balanced", random_state=0)
            m.fit(Xa[~te], ya[~te]); pred[te] = m.predict_proba(Xa[te])[:, 1]
            a = auc_by_scenario(y_new[te], pred[te], sc[te]); a_old = auc_by_scenario(y_old[te], pred[te], sc[te])
            per_world.append(dict(world=held, macro_new=np.mean(list(a.values())), macro_old=np.mean(list(a_old.values())), **{f"new_{k}": v for k, v in a.items()}))
            print(f"  {name[:40]:40s} world {held}: macro AUC vs new label {per_world[-1]['macro_new']:.3f}", flush=True)
        pw = pd.DataFrame(per_world)
        row = dict(arm=name, macro_new_mean=pw.macro_new.mean(), macro_new_std=pw.macro_new.std(), macro_vs_old_label=pw.macro_old.mean(),
                   **{f"AUC_{s}": pw[f"new_{s}"].mean() for s in SCEN})
        res.append(row)
        np.save(os.path.join(ROOT, "out", "cache", f"pred_{name[0]}.npy"), pred)
    rdf = pd.DataFrame(res)
    rdf.to_csv(os.path.join(OUT, "arms.csv"), index=False)
    print("\nLEAVE-ONE-WORLD-OUT, evaluated against the NEW label (per-scenario AUC, mean over 6 worlds)\n", rdf.round(3).to_string(index=False), flush=True)

    # ---------- 4. regression of error magnitude (what the filter needs to set R)
    target = np.log1p(np.abs(err) / sig_nom)          # error size in units of the nominal noise
    pred = np.zeros(len(target), dtype=np.float32)
    for held in worlds:
        te = w == held
        m = HistGradientBoostingRegressor(max_iter=150, learning_rate=0.1, max_leaf_nodes=31, random_state=0)
        m.fit(Xv3[~te], target[~te]); pred[te] = m.predict(Xv3[te])
    reg = []
    rng = np.random.default_rng(0)
    for k, name in enumerate(SCEN):
        mk = np.nonzero(sc == k)[0]
        s = rng.choice(mk, min(150000, len(mk)), replace=False)
        auc = roc_auc_score(y_new[mk], pred[mk]) if 0 < y_new[mk].mean() < 1 else np.nan
        reg.append(dict(scenario=name, spearman=float(spearmanr(pred[s], target[s])[0]), AUC_of_prediction_for_new_label=float(auc)))
    reg = pd.DataFrame(reg)
    reg.to_csv(os.path.join(OUT, "regression.csv"), index=False)
    print("\nERROR-MAGNITUDE REGRESSION (log1p(|err|/sigma_nominal)), out-of-world\n", reg.round(3).to_string(index=False), flush=True)
    print(f"\ndone in {time.time()-t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    mp.freeze_support()
    main()
