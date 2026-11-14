"""Confirmation grid for 'predicted noise on UNFLAGGED readings too' (ml2_noise_normal).

sim/ml2_x4.py found, on the tuning worlds, that applying the error-size model also to readings that passed the gate lifts
x4 noise from 73.0% to 92.0% landing success (PITFAL 88.2, trust v2 88.8). That variant was found by looking at tuning-world
results and the model was trained on flagged rows only, so it must be checked everywhere, including where noise is nominal
(cliff + faults), before it is believed.

  python sim/ml2_noise_normal.py       output: out/ml2/noise_normal.csv     (tuning worlds only, 100 descents per cell)
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
_N = engine.SCENARIOS["shadow_noisy"]
CONDS = {
    "cliff + faults (nominal noise)": engine.SCENARIOS["cliff_fault"],
    "x2 below 6000 m": dataclasses.replace(_N, noise_mult_below_agl=2.0),
    "x4 below 6000 m": dataclasses.replace(_N, noise_mult_below_agl=4.0),
    "x8 below 6000 m (TRAINING)": _N,
    "x16 below 6000 m": dataclasses.replace(_N, noise_mult_below_agl=16.0),
    "x8 below 2500 m": dataclasses.replace(_N, noise_mult_agl=2500.0),
}
B = dict(ml2_mode="hard", ml2_terrain_R=True)
JUDGES = {"pitfal": ("pitfal", {}, False), "trust2": ("trust2", {}, False),
          "ml2 + predicted noise (flagged only)": ("ml2", dict(B), True),
          "ml2 + predicted noise (flagged + unflagged)": ("ml2", dict(B, ml2_noise_normal=True), True)}


def task(spec):
    wk, = spec
    w, tr = P.get_world(wk)
    clf = pickle.load(open(os.path.join(ROOT, "models", "fault_clf_v3.pkl"), "rb"))
    reg = pickle.load(open(os.path.join(ROOT, "models", "err_reg_v3.pkl"), "rb"))
    rows = []
    for cname, sc in CONDS.items():
        for jname, (judge, extra, use_reg) in JUDGES.items():
            d = engine.Draws(w, sc, 100, 7)
            kw = dict(P.tuned()); kw["cam_policy"] = "conf"; kw.update(extra)
            if use_reg:
                kw["ml2_noise_model"] = reg
            r = engine.simulate(w, tr, sc, judge, d, ml_model=clf if judge == "ml2" else None, **kw)
            rows.append(dict(world=str(wk[:2]), condition=cname, judge=jname, success=int(r["success"].sum()),
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
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "noise_normal.csv"), index=False)
    t = df.pivot_table(index="condition", columns="judge", values="success").reindex(list(CONDS))[list(JUDGES)].round(1)
    print("\nLanding success % (mean of 4 tuning worlds, 100 descents each)\n", t.to_string())
    pw = df.pivot_table(index=["condition", "judge"], columns="world", values="success")
    print("\nPer world (landings out of 100)\n", pw.to_string())


if __name__ == "__main__":
    mp.freeze_support()
    main()
