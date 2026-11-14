"""Does the predicted-noise result generalise to noise levels the models never saw?

The classifier and the error-size model were trained only on 'shadow + noisy' with the altimeter noise x8 below 6000 m AGL.
Here the models are used UNCHANGED on other noise levels (x2, x4, x16; x8 below 2500 m only), against PITFAL, the tolerance gate,
trust v2 and ml2 without the noise model. x8 / 6000 m is the training condition (kept as the reference row). Tuning worlds only.

  python sim/ml2_noise_levels.py        output: out/ml2/noise_levels.csv
"""
import dataclasses
import multiprocessing as mp
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import pipeline as P  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "ml2")
CONDS = {"x2 below 6000 m": (2.0, 6000.0), "x4 below 6000 m": (4.0, 6000.0), "x8 below 6000 m (TRAINING)": (8.0, 6000.0),
         "x16 below 6000 m": (16.0, 6000.0), "x8 below 2500 m": (8.0, 2500.0)}
H = dict(ml2_mode="hard", ml2_terrain_R=True)
JUDGES = {"pitfal": ("pitfal", {}, False), "tolerance": ("tolerance", {}, False), "trust2": ("trust2", {}, False),
          "ml2_hard + terrain_R": ("ml2", dict(H), False), "ml2_hard + terrain_R + predicted noise": ("ml2", dict(H), True)}


def task(spec):
    wk, = spec
    w, tr = P.get_world(wk)
    clf = pickle.load(open(os.path.join(ROOT, "models", "fault_clf_v3.pkl"), "rb"))
    reg = pickle.load(open(os.path.join(ROOT, "models", "err_reg_v3.pkl"), "rb"))
    rows = []
    for cname, (mult, cut) in CONDS.items():
        sc = dataclasses.replace(engine.SCENARIOS["shadow_noisy"], noise_mult_below_agl=mult, noise_mult_agl=cut)
        for jname, (judge, extra, use_reg) in JUDGES.items():
            d = engine.Draws(w, sc, 100, 7)
            kw = dict(P.tuned()); kw["cam_policy"] = "conf"; kw.update(extra)
            if use_reg:
                kw["ml2_noise_model"] = reg
            r = engine.simulate(w, tr, sc, judge, d, ml_model=clf if judge == "ml2" else None, **kw)
            rows.append(dict(world=str(wk[:2]), condition=cname, judge=jname, success=int(r["success"].sum())))
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
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "noise_levels.csv"), index=False)
    t = df.pivot_table(index="condition", columns="judge", values="success").reindex(list(CONDS))[list(JUDGES)].round(1)
    print("\nLanding success % (mean of 4 tuning worlds, 100 descents each)\n", t.to_string())


if __name__ == "__main__":
    mp.freeze_support()
    main()
