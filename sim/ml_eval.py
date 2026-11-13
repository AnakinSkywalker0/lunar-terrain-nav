"""Honest evaluation of the fault-or-terrain classifier (ML judge).

What it does
  1. Collects training rows (cached): every altimeter reading that FAILS the chi-square gate, with 8 features and a
     label (1 = sensor fault, 0 = real terrain). Same jobs as `pipeline.stage_ml`, so the data is identical.
  2. Leave-one-world-out cross-validation: train on 5 procedural worlds, test on the 6th, repeat for all 6.
     (The committed report tests on one world only, so it cannot show how much the score varies between worlds.)
  3. Compares models: the gate statistic alone (no learning), logistic regression, random forest (the repo's model),
     gradient boosting.
  4. Reports accuracy, AUC, Brier score, calibration error (ECE), AUC per scenario, permutation feature importance.

Usage:  python sim/ml_eval.py            (collect if needed, then evaluate)
        python sim/ml_eval.py --quick    (subsample rows; fast sanity check)
Output: out/ml_eval/ (metrics.csv, per_scenario.csv, importance.csv, calibration.png, summary.json)
Data cache: out/cache/ml_data.npz (git-ignored).
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import pipeline as P  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "out", "cache", "ml_data.npz")
OUT = os.path.join(ROOT, "out", "ml_eval")
FEATURES = ["nu_over_sd", "nu", "h_std", "h_range", "abs_nu_over_sqrtR", "mean_abs_nu_hist", "agl_km", "ellipse_rad"]
SCENARIOS = ["cliff", "cliff_fault", "shadow_noisy", "delayed"]
WORKERS = 4  # 16 GB machine: more workers ran out of memory in the original project


def collect():
    """Run the same simulations as pipeline.stage_ml and keep the rows with their world and scenario ids."""
    P.warm([("proc", s) for s in P.TRAIN_SEEDS])
    jobs = []
    for s in P.TRAIN_SEEDS:
        for name in SCENARIOS:
            jobs.append(dict(world=("proc", s), scen=engine.SCENARIOS[name], judge="pitfal", n=100, seed=1000 + s,
                             collect=True, tag=f"{s}|{name}"))
    res = P.pmap(jobs, workers=WORKERS)
    Xs, ys, ws, ss = [], [], [], []
    for r in res:
        seed, name = r["tag"].split("|")
        for X, y in r["_collect"]:
            Xs.append(X)
            ys.append(np.asarray(y).astype(int))
            ws.append(np.full(len(y), int(seed)))
            ss.append(np.full(len(y), SCENARIOS.index(name)))
    X = np.concatenate(Xs); y = np.concatenate(ys); w = np.concatenate(ws); sc = np.concatenate(ss)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    np.savez_compressed(CACHE, X=X, y=y, world=w, scen=sc)
    return X, y, w, sc


def load():
    if os.path.exists(CACHE):
        d = np.load(CACHE)
        return d["X"], d["y"], d["world"], d["scen"]
    return collect()


# ------------------------------------------------------------------ metrics
def ece(y, p, bins=10):
    """Expected calibration error: average gap between predicted probability and observed fault rate."""
    idx = np.minimum((p * bins).astype(int), bins - 1)
    tot = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            tot += m.mean() * abs(p[m].mean() - y[m].mean())
    return tot


def metrics(y, p):
    from sklearn.metrics import roc_auc_score, brier_score_loss, balanced_accuracy_score
    return dict(acc=float(((p > 0.5) == y).mean()), bal_acc=float(balanced_accuracy_score(y, p > 0.5)),
                auc=float(roc_auc_score(y, p)), brier=float(brier_score_loss(y, p)), ece=float(ece(y, p)))


# ------------------------------------------------------------------ models
def make_models():
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return {
        "logistic": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=300, class_weight="balanced")),
        "random_forest": lambda: RandomForestClassifier(n_estimators=120, max_depth=14, min_samples_leaf=20, n_jobs=-1,
                                                        random_state=0, class_weight="balanced"),
        "grad_boost": lambda: HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, max_leaf_nodes=31,
                                                              class_weight="balanced", random_state=0),
    }


def gate_only_score(X):
    """No learning: the further past the gate, the likelier a fault. Squash |nu/sd| into (0,1) for AUC/Brier."""
    z = np.abs(X[:, 0])
    return z / (z + 2.576)  # 2.576 sigma = the 99% gate, so 0.5 sits at the gate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="subsample 15%% of rows")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    X, y, w, sc = load()
    print(f"rows {len(y)}, fault fraction {y.mean():.3f}, worlds {sorted(set(w))}, load {time.time()-t0:.0f}s", flush=True)
    if args.quick:
        keep = np.random.default_rng(0).random(len(y)) < 0.15
        X, y, w, sc = X[keep], y[keep], w[keep], sc[keep]
        print("quick mode, rows", len(y))

    models = make_models()
    rows, per_scen, preds = [], [], {}
    for name in ["gate_only"] + list(models):
        pred = np.zeros(len(y))
        for held in sorted(set(w)):
            te = w == held
            if name == "gate_only":
                pred[te] = gate_only_score(X[te])
            else:
                m = models[name]()
                m.fit(X[~te], y[~te])
                pred[te] = m.predict_proba(X[te])[:, 1]
            rows.append(dict(model=name, held_out_world=held, **metrics(y[te], pred[te])))
            print(f"  {name:14s} held-out world {held}: AUC {rows[-1]['auc']:.3f}  acc {rows[-1]['acc']:.3f}", flush=True)
        preds[name] = pred
        for k, sname in enumerate(SCENARIOS):
            m = sc == k
            if m.any() and 0 < y[m].mean() < 1:
                per_scen.append(dict(model=name, scenario=sname, n=int(m.sum()), fault_frac=float(y[m].mean()), **metrics(y[m], pred[m])))

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "metrics.csv"), index=False)
    pd.DataFrame(per_scen).to_csv(os.path.join(OUT, "per_scenario.csv"), index=False)
    summ = df.groupby("model")[["acc", "bal_acc", "auc", "brier", "ece"]].agg(["mean", "std"]).round(4)
    print("\nLeave-one-world-out summary (mean, std across 6 worlds)\n", summ.to_string(), flush=True)

    # calibration plot (pooled out-of-world predictions)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="perfect")
    for name, pred in preds.items():
        b = np.minimum((pred * 10).astype(int), 9)
        xs = [pred[b == i].mean() for i in range(10) if (b == i).sum() > 50]
        ys = [y[b == i].mean() for i in range(10) if (b == i).sum() > 50]
        ax.plot(xs, ys, "o-", label=name)
    ax.set_xlabel("predicted fault probability"); ax.set_ylabel("observed fault rate"); ax.legend(); ax.set_title("Calibration, out-of-world")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "calibration.png"), dpi=130); plt.close(fig)

    # permutation importance: random forest trained on 5 worlds, tested on the 6th, 40k test rows
    from sklearn.inspection import permutation_importance
    held = sorted(set(w))[-1]
    te = np.nonzero(w == held)[0]
    te = np.random.default_rng(1).choice(te, min(40000, len(te)), replace=False)
    m = models["random_forest"](); m.fit(X[w != held], y[w != held])
    pi = permutation_importance(m, X[te], y[te], scoring="roc_auc", n_repeats=5, random_state=0, n_jobs=1)
    imp = pd.DataFrame(dict(feature=FEATURES, auc_drop=pi.importances_mean, std=pi.importances_std)).sort_values("auc_drop", ascending=False)
    imp.to_csv(os.path.join(OUT, "importance.csv"), index=False)
    print("\nPermutation importance (AUC drop, world", held, ")\n", imp.round(4).to_string(index=False))

    json.dump(dict(rows=int(len(y)), fault_frac=float(y.mean()), quick=args.quick,
                   summary={k: {f"{a}_{b}": float(v) for (a, b), v in r.items()} for k, r in summ.iterrows()}),
              open(os.path.join(OUT, "summary.json"), "w"), indent=2)
    print(f"\ndone in {time.time()-t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    mp.freeze_support()
    main()
