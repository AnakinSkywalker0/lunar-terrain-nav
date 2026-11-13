"""Why does ml2 land less often than PITFAL / tolerance / trust v2 although its classifier is better offline?

Tests two suspected causes with switchable fixes (both default OFF in engine.simulate):
  H1  vertical_only : an accepted flagged reading corrects altitude only, not the horizontal position through the map
                      gradient (which is wrong at a cliff / jump).
  H2  terrain_R     : unflagged readings get the terrain+map variance that the tolerance / trust judges use (the ml / ml2
                      path uses the bare altimeter noise).
2x2 grid on ml2 (hard mode) + PITFAL for reference, on the tuning worlds only.

  python sim/ml2_diagnose.py            output: out/ml2/diagnose.csv (landing success %, outcomes)
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
VARIANTS = {
    "pitfal (reference)": ("pitfal", {}),
    "ml2_hard": ("ml2", dict(ml2_mode="hard")),
    "ml2_hard + vertical_only (H1)": ("ml2", dict(ml2_mode="hard", ml2_vertical_only=True)),
    "ml2_hard + terrain_R (H2)": ("ml2", dict(ml2_mode="hard", ml2_terrain_R=True)),
    "ml2_hard + both": ("ml2", dict(ml2_mode="hard", ml2_vertical_only=True, ml2_terrain_R=True)),
}
SCEN = ["cliff_fault", "shadow_noisy"]


def task(spec):
    wk, = spec
    w, tr = P.get_world(wk)
    mdl = pickle.load(open(os.path.join(ROOT, "models", "fault_clf_v3.pkl"), "rb"))
    rows = []
    for sname in SCEN:
        sc = engine.SCENARIOS[sname]
        for vname, (judge, extra) in VARIANTS.items():
            d = engine.Draws(w, sc, 100, 7)
            kw = dict(P.tuned()); kw["cam_policy"] = "conf"; kw.update(extra)
            r = engine.simulate(w, tr, sc, judge, d, ml_model=mdl if judge == "ml2" else None, **kw)
            oc = collections.Counter(r["outcome"])
            rows.append(dict(world=str(wk[:2]), scenario=sc.name, variant=vname, success=int(r["success"].sum()), rough=oc.get("rough", 0),
                             crash=oc.get("crash", 0), timeout=oc.get("timeout", 0),
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
    df.to_csv(os.path.join(OUT, "diagnose.csv"), index=False)
    g = df.groupby(["scenario", "variant"])[["success", "rough", "crash", "timeout", "alt_rms"]].agg({"success": "mean", "rough": "mean", "crash": "mean", "timeout": "mean", "alt_rms": "mean"}).round(1)
    print("\nMean over the 4 tuning worlds (success/rough/crash/timeout are counts out of 100)\n", g.to_string())


if __name__ == "__main__":
    mp.freeze_support()
    main()
