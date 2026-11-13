"""Compare the new 'ml2' judge with the existing judges on the TUNING worlds (procedural 11-13 + real Site01).

  python sim/ml2_compare.py                   # n=100 descents per cell, scenarios cliff_fault / shadow_noisy / delayed
  python sim/ml2_compare.py --n 500           # the size used for the paper tables
  python sim/ml2_compare.py --scen cliff dropout --worlds tune

Judges: pitfal, tolerance, wait, trust2 (existing), ml (old random forest; only if out/mc/ml_model.pkl exists),
        ml2_hard / ml2_soft (new). Every judge gets the confidence-gated camera, as in round 2.

PROTOCOL: this is a TUNING comparison. It never touches Site04 unless you pass --allow-site04, and you should not do that
before the round-3 settings are frozen and pre-registered (see HANDOFF.md). Output: out/ml2/compare_<worlds>.csv
"""
import argparse
import multiprocessing as mp
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import pipeline as P  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "ml2")
MODEL2 = os.path.join(ROOT, "models", "fault_clf_v3.pkl")
JUDGES = ["pitfal", "tolerance", "wait", "trust2", "ml", "ml2_hard", "ml2_soft"]
_models = {}


def _model(kind):
    if kind not in _models:
        path = MODEL2 if kind == "ml2" else os.path.join(P.OUT, "ml_model.pkl")
        _models[kind] = pickle.load(open(path, "rb")) if os.path.exists(path) else None
    return _models[kind]


def task(spec):
    wk, scen, n, seed = spec
    w, tr = P.get_world(wk)
    sc = engine.SCENARIOS[scen]
    rows = []
    for j in JUDGES:
        if j == "ml" and _model("ml") is None:
            continue
        d = engine.Draws(w, sc, n, seed)
        kw = dict(P.tuned()); kw["cam_policy"] = "conf"
        if j.startswith("ml2"):
            judge, kw["ml2_mode"] = "ml2", j.split("_")[1]
            mdl = _model("ml2")
        else:
            judge, mdl = j, _model("ml") if j == "ml" else None
        t0 = time.time()
        r = engine.simulate(w, tr, sc, judge, d, ml_model=mdl, **kw)
        s = engine.summarize(r)
        rows.append(dict(world=str(wk[:2]), scenario=sc.name, judge=j, n=n, success_pct=s["success_pct"],
                         ci_lo=s["success_lo"], ci_hi=s["success_hi"], alt_rms_m=s["alt_rms_m"], false_rej_pct=s["false_rej_pct"],
                         missed_fault_pct=s["missed_fault_pct"], secs=time.time() - t0))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--scen", nargs="+", default=["cliff_fault", "shadow_noisy", "delayed"])
    ap.add_argument("--worlds", default="tune", choices=["tune", "site04"])
    ap.add_argument("--allow-site04", action="store_true", help="only after settings are frozen and pre-registered")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.worlds == "site04":
        if not a.allow_site04:
            sys.exit("Refusing to run Site04 without --allow-site04. Site04 is the held-out test site: freeze settings and pre-register first.")
        worlds = [("site04", P.SUN_EL, P.SUN_AZ)]
    else:
        worlds = [("proc", s) for s in P.TUNE_SEEDS] + [("site01", P.SUN_EL, P.SUN_AZ)]
    os.makedirs(OUT, exist_ok=True)
    P.warm(worlds)
    specs = [(wk, s, a.n, a.seed) for wk in worlds for s in a.scen]
    rows = []
    with mp.Pool(min(a.workers, len(specs))) as pool:
        for r in pool.imap_unordered(task, specs):
            rows += r
            print(f"  done {r[0]['world']} {r[0]['scenario'][:30]}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, f"compare_{a.worlds}.csv"), index=False)
    piv = df.pivot_table(index="judge", columns="scenario", values="success_pct", aggfunc="mean").reindex([j for j in JUDGES if j in set(df.judge)])
    print("\nLanding success %, mean over worlds\n", piv.round(1).to_string())
    per = df.pivot_table(index=["scenario", "judge"], columns="world", values="success_pct").round(1)
    print("\nPer world\n", per.to_string())


if __name__ == "__main__":
    mp.freeze_support()
    main()
