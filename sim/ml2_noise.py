"""Test two ideas for the 'shadow + noisy altimeter' gap (ML judges ~47% vs PITFAL 77%, trust v2 78%).

  B  reject threshold: the classifier is trained unweighted, so 0.5 may let faults through -> try 0.3 and 0.2
  A  predicted noise: accepted flagged readings get a variance floor from the error-size model (models/err_reg_v3.pkl),
     so a reading from an altimeter that is currently 8x noisier than nominal is no longer trusted as if it were nominal.
     Scale 1.0 = median-calibrated magnitude (the model's median |error| / prediction is ~1.0 on an unseen world);
     scale 1.5 ~ the Gaussian standard deviation (median |e| = 0.674 sigma).
All variants use ml2 hard mode + the terrain-variance fix (ml2_terrain_R). Tuning worlds only.

  python sim/ml2_noise.py        output: out/ml2/noise.csv
"""
import collections
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
H = dict(ml2_mode="hard", ml2_terrain_R=True)
VARIANTS = {
    "pitfal (reference)": ("pitfal", {}, False),
    "ml2_hard + terrain_R (thr 0.5)": ("ml2", dict(H), False),
    "  thr 0.3": ("ml2", dict(H, ml2_threshold=0.3), False),
    "  thr 0.2": ("ml2", dict(H, ml2_threshold=0.2), False),
    "  + predicted noise x1.0": ("ml2", dict(H, ml2_noise_scale=1.0), True),
    "  + predicted noise x1.5": ("ml2", dict(H, ml2_noise_scale=1.5), True),
    "  thr 0.3 + predicted noise x1.5": ("ml2", dict(H, ml2_threshold=0.3, ml2_noise_scale=1.5), True),
}
SCEN = ["cliff_fault", "shadow_noisy"]


def task(spec):
    wk, = spec
    w, tr = P.get_world(wk)
    clf = pickle.load(open(os.path.join(ROOT, "models", "fault_clf_v3.pkl"), "rb"))
    reg = pickle.load(open(os.path.join(ROOT, "models", "err_reg_v3.pkl"), "rb"))
    rows = []
    for sname in SCEN:
        sc = engine.SCENARIOS[sname]
        for vname, (judge, extra, use_reg) in VARIANTS.items():
            d = engine.Draws(w, sc, 100, 7)
            kw = dict(P.tuned()); kw["cam_policy"] = "conf"; kw.update(extra)
            if use_reg:
                kw["ml2_noise_model"] = reg
            r = engine.simulate(w, tr, sc, judge, d, ml_model=clf if judge == "ml2" else None, **kw)
            oc = collections.Counter(r["outcome"])
            rows.append(dict(world=str(wk[:2]), scenario=sc.name, variant=vname, success=int(r["success"].sum()), rough=oc.get("rough", 0),
                             crash=oc.get("crash", 0), alt_rms=float(np.sqrt(r["alt_sq"].sum() / max(r["alt_n"].sum(), 1)))))
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
    df.to_csv(os.path.join(OUT, "noise.csv"), index=False)
    order = list(VARIANTS)
    g = df.groupby(["scenario", "variant"])[["success", "rough", "crash", "alt_rms"]].mean().round(1)
    print("\nMean over the 4 tuning worlds (success / rough / crash = counts out of 100)\n", g.to_string())
    pw = df.pivot_table(index=["scenario", "variant"], columns="world", values="success")
    print("\nPer world (landings out of 100)\n", pw.to_string())


if __name__ == "__main__":
    mp.freeze_support()
    main()
