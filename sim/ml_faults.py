"""Experiment: do the classifier's gains survive fault types it was not trained on?

Concern (from reading sim/engine.py): every injected fault is a burst of independent random-sign, random-size errors
(30-400 m) per sample. Features such as 'how erratic were the last readings' would then separate faults from terrain
in THIS simulator only. Real altimeter faults can be a constant offset, a slow drift or a single spike.

What it does
  * Re-runs the simulator with five fault types, keeping the simulator's own burst timing and only changing the shape
    of the error inside each burst (engine.py untouched; the burst error array of `Draws` is rewritten before the run):
      random        independent random sign/size per sample   (the existing model)
      offset        one constant error for the whole burst     (30-400 m)
      small_offset  one constant error, small                  (6-40 m, close to the gate: hard)
      drift         error ramps from 0 to 30-400 m over the burst
      spike         1-2 sample bursts, random size             (rate x6 so the fault count is comparable)
    Not covered: 'stuck at last value' (needs the true range at run time, which Draws does not have).
  * Leave-one-fault-type-out: train on 5 worlds and 4 fault types, test on the 6th world and the held-out type.
    Compared with 'in-distribution' (trained on all 5 types). The gap is the price of meeting a new fault type.
  * Two feature sets: C (15 features, no history) and D (C + vertical speed + 10 s history of flagged readings).
  Labels: the corrected one (|error| > 5 * true noise sigma + 1).  Scenarios: cliff, cliff_fault, shadow_noisy.

Usage: python sim/ml_faults.py       Output: out/ml_faults/      Cache: out/cache/ml_data_faults.npz
"""
import dataclasses
import multiprocessing as mp
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import ml_labels as L  # noqa: E402  (patches engine._features to also record ground truth; reuses persistence())
import ml_eval as E  # noqa: E402

ROOT = E.ROOT
CACHE = os.path.join(ROOT, "out", "cache", "ml_data_faults.npz")
OUT = os.path.join(ROOT, "out", "ml_faults")
TYPES = ["random", "offset", "small_offset", "drift", "spike"]
SCEN3 = ["cliff", "cliff_fault", "shadow_noisy"]
N_RUNS = 50
N2 = L.N2


def apply_fault_type(d, ftype, seed):
    """Rewrite the error inside each burst of `Draws` d. Bursts are runs of consecutive True in d.burst."""
    if ftype in ("random", "spike"):
        return
    rng = np.random.default_rng(seed + 77)
    bias = d.burst_bias
    for i in np.nonzero(d.burst.any(axis=1))[0]:
        idx = np.flatnonzero(d.burst[i])
        for seg in np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1):
            n = len(seg)
            sign = rng.choice([-1.0, 1.0])
            if ftype == "offset":
                bias[i, seg] = sign * rng.uniform(30.0, 400.0)
            elif ftype == "small_offset":
                bias[i, seg] = sign * rng.uniform(6.0, 40.0)
            elif ftype == "drift":
                bias[i, seg] = sign * rng.uniform(30.0, 400.0) * np.arange(1, n + 1) / n


def job(spec):
    P = E.P
    seed, ftype = spec
    w, tr = P.get_world(("proc", seed))
    out = []
    for name in SCEN3:
        sc = engine.SCENARIOS[name]
        if ftype == "spike":
            sc = dataclasses.replace(sc, burst_len=(1, 2), burst_rate=sc.burst_rate * 6.0)
        d = engine.Draws(w, sc, N_RUNS, 5000 + seed)
        apply_fault_type(d, ftype, seed)
        col = []
        engine.simulate(w, tr, sc, "pitfal", d, ml_model=None, collect=col, **P.tuned())
        for X, y in col:
            out.append((X.astype(np.float32), np.full(len(y), SCEN3.index(name), dtype=np.int8)))
    X = np.concatenate([a for a, _ in out]); sc = np.concatenate([b for _, b in out])
    return seed, ftype, X, sc


def collect():
    P = E.P
    P.warm([("proc", s) for s in P.TRAIN_SEEDS])
    specs = [(s, f) for s in P.TRAIN_SEEDS for f in TYPES]
    Xs, ws, ts, ss = [], [], [], []
    t0 = time.time()
    with mp.Pool(E.WORKERS) as pool:
        for k, (seed, ftype, X, sc) in enumerate(pool.imap_unordered(job, specs)):
            Xs.append(X); ws.append(np.full(len(X), seed, dtype=np.int16)); ts.append(np.full(len(X), TYPES.index(ftype), dtype=np.int8)); ss.append(sc)
            print(f"  job {k+1}/{len(specs)} world {seed} {ftype:12s} rows {len(X)}  ({time.time()-t0:.0f}s)", flush=True)
    X = np.concatenate(Xs); w = np.concatenate(ws); ft = np.concatenate(ts); sc = np.concatenate(ss)
    # unique descent id: (world, fault type, scenario, run) -> must stay below 2^24 to survive float32
    X[:, N2] = (((w.astype(np.int64) - 21) * len(TYPES) + ft) * 3 + sc) * 100 + X[:, N2]
    np.savez_compressed(CACHE, X=X, world=w, ftype=ft, scen=sc)
    return X, w, ft, sc


def load():
    if os.path.exists(CACHE):
        d = np.load(CACHE)
        return d["X"], d["world"], d["ftype"], d["scen"]
    return collect()


def macro_auc(y, p, sc):
    from sklearn.metrics import roc_auc_score
    a = [roc_auc_score(y[sc == k], p[sc == k]) for k in range(len(SCEN3)) if (sc == k).any() and 0 < y[sc == k].mean() < 1]
    return float(np.mean(a)) if a else np.nan


def main():
    from sklearn.ensemble import HistGradientBoostingClassifier
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    X, w, ft, sc = load()
    err = X[:, N2 + 2]; sig_true = X[:, N2 + 3]; burst = X[:, N2 + 5] > 0.5
    y = (np.abs(err) > 5.0 * sig_true + 1.0).astype(np.int8)
    print(f"rows {len(y)} load {time.time()-t0:.0f}s", flush=True)
    tab = []
    for k, f in enumerate(TYPES):
        m = ft == k
        tab.append(dict(fault_type=f, rows=int(m.sum()), fault_frac=float(y[m].mean()), injected_burst_frac=float(burst[m].mean()),
                        median_abs_err_of_faults_m=float(np.median(np.abs(err[m & (y == 1)]))) if (m & (y == 1)).any() else np.nan))
    pd.DataFrame(tab).to_csv(os.path.join(OUT, "fault_type_audit.csv"), index=False)
    print("\nFAULT TYPE AUDIT\n", pd.DataFrame(tab).round(3).to_string(index=False), flush=True)

    pers = L.persistence(X)
    XC = X[:, :N2]
    XD = np.concatenate([XC, X[:, N2 + 6:N2 + 7], pers], axis=1)
    arms = {"C (no history)": XC, "D (+vz +history)": XD}
    worlds = sorted(set(w.tolist()))
    rng = np.random.default_rng(0)
    CAP = 500_000

    def fit_predict(Xa, tr, te):
        idx = np.nonzero(tr)[0]
        if len(idx) > CAP:
            idx = rng.choice(idx, CAP, replace=False)
        m = HistGradientBoostingClassifier(max_iter=120, learning_rate=0.1, max_leaf_nodes=31, class_weight="balanced", random_state=0)
        m.fit(Xa[idx], y[idx])
        return m.predict_proba(Xa[te])[:, 1]

    rows = []
    for an, Xa in arms.items():
        for held in worlds:
            te_w = w == held
            # in-distribution model: all fault types seen in training
            p_in = fit_predict(Xa, ~te_w, te_w)
            for k, f in enumerate(TYPES):
                sel = (ft[te_w] == k)
                a_in = macro_auc(y[te_w][sel], p_in[sel], sc[te_w][sel])
                # unseen-type model: the held-out fault type is removed from training
                tr = (~te_w) & (ft != k)
                p_un = fit_predict(Xa, tr, te_w & (ft == k))
                a_un = macro_auc(y[te_w & (ft == k)], p_un, sc[te_w & (ft == k)])
                rows.append(dict(arm=an, world=held, fault_type=f, auc_seen_type=a_in, auc_unseen_type=a_un))
            print(f"  {an:18s} world {held} done ({time.time()-t0:.0f}s)", flush=True)
    r = pd.DataFrame(rows)
    r.to_csv(os.path.join(OUT, "results_by_world.csv"), index=False)
    s = r.groupby(["arm", "fault_type"])[["auc_seen_type", "auc_unseen_type"]].mean()
    s["drop"] = s.auc_seen_type - s.auc_unseen_type
    s = s.reset_index()
    s.to_csv(os.path.join(OUT, "summary.csv"), index=False)
    print("\nMACRO AUC (cliff, cliff_fault, shadow_noisy), mean over 6 worlds\n", s.round(3).to_string(index=False), flush=True)
    print(f"\ndone in {time.time()-t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    mp.freeze_support()
    main()
