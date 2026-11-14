"""Non-ML control: does the LEARNED error model matter, or would a simple running noise estimate do the same?

ml2 (hard mode + terrain fix) with the measurement variance floor taken from
  - nothing                                   (earlier: ml2_hard + terrain_R)
  - the running innovation-size estimate s_hat (trust v2's rule, ml2_noise_heuristic)   <- this script, the non-ML control
  - the learned error-size model, flagged only / flagged + unflagged readings            (earlier: out/ml2/noise_normal.csv)
Same classifier, same terrain fix, same worlds and seed (7) as out/ml2/noise_normal.csv, so the columns are directly comparable.

  python sim/ml2_control_noise.py       output: out/ml2/control_noise.csv
"""
import multiprocessing as mp
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import ml2_noise_normal as N  # noqa: E402  (reuses CONDS)
import pipeline as P  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "ml2")
NAME = "ml2 + running-innovation noise (NON-ML control)"


def task(spec):
    wk, = spec
    w, tr = P.get_world(wk)
    clf = pickle.load(open(os.path.join(ROOT, "models", "fault_clf_v3.pkl"), "rb"))
    rows = []
    for cname, sc in N.CONDS.items():
        d = engine.Draws(w, sc, 100, 7)
        kw = dict(P.tuned()); kw.update(cam_policy="conf", ml2_mode="hard", ml2_terrain_R=True, ml2_noise_heuristic=True)
        r = engine.simulate(w, tr, sc, "ml2", d, ml_model=clf, **kw)
        rows.append(dict(world=str(wk[:2]), condition=cname, judge=NAME, success=int(r["success"].sum()),
                         alt_rms=float(np.sqrt(r["alt_sq"].sum() / max(r["alt_n"].sum(), 1)))))
    return rows


def main():
    worlds = [("proc", s) for s in P.TUNE_SEEDS] + [("site01", P.SUN_EL, P.SUN_AZ)]
    os.makedirs(OUT, exist_ok=True)
    P.warm(worlds)
    rows = []
    with mp.Pool(4) as pool:
        for r in pool.imap_unordered(task, [(wk,) for wk in worlds]):
            rows += r
            print("  done", r[0]["world"], flush=True)
    new = pd.DataFrame(rows)
    new.to_csv(os.path.join(OUT, "control_noise.csv"), index=False)
    old = pd.read_csv(os.path.join(OUT, "noise_normal.csv"))
    df = pd.concat([old, new])
    order = ["pitfal", "trust2", NAME, "ml2 + predicted noise (flagged only)", "ml2 + predicted noise (flagged + unflagged)"]
    t = df.pivot_table(index="condition", columns="judge", values="success").reindex(list(N.CONDS))[order].round(1)
    print("\nLanding success % (mean of 4 tuning worlds, 100 descents each, seed 7)\n", t.to_string())
    pw = new.pivot_table(index=["condition"], columns="world", values="success")
    print("\nNon-ML control per world\n", pw.to_string())


if __name__ == "__main__":
    mp.freeze_support()
    main()
