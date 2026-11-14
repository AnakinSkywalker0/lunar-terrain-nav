"""Why is ml2 + predicted noise still ~15 points behind PITFAL at moderate noise (x4 below 6000 m)?

Hypotheses tested (tuning worlds only, ml2 hard mode + terrain fix + predicted noise as the starting point):
  accept more / reject more : reject threshold 0.7 / 0.3
  noise on unflagged readings: the error-size model is also applied to readings that passed the gate (exploratory: it was trained on
                               flagged rows only)
  soft mode                  : keep every flagged reading, inflate by 1/(1-p)^2 on top of the predicted-noise floor
  no terrain fix             : to see how the pieces interact
Reports landing success, outcome breakdown (rough / crash) and altitude RMS at x4 and x2.

  python sim/ml2_x4.py        output: out/ml2/x4.csv
"""
import collections
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
CONDS = {"x4 below 6000 m": (4.0, 6000.0), "x2 below 6000 m": (2.0, 6000.0)}
B = dict(ml2_mode="hard", ml2_terrain_R=True)
VARIANTS = {
    "pitfal (reference)": ("pitfal", {}, False),
    "ml2 + terrain_R + predicted noise (reference)": ("ml2", dict(B), True),
    "  threshold 0.7 (accept more)": ("ml2", dict(B, ml2_threshold=0.7), True),
    "  threshold 0.3 (reject more)": ("ml2", dict(B, ml2_threshold=0.3), True),
    "  noise model also on unflagged readings": ("ml2", dict(B, ml2_noise_normal=True), True),
    "  soft mode": ("ml2", dict(B, ml2_mode="soft"), True),
    "  without terrain_R": ("ml2", dict(ml2_mode="hard"), True),
}


def task(spec):
    wk, = spec
    w, tr = P.get_world(wk)
    clf = pickle.load(open(os.path.join(ROOT, "models", "fault_clf_v3.pkl"), "rb"))
    reg = pickle.load(open(os.path.join(ROOT, "models", "err_reg_v3.pkl"), "rb"))
    rows = []
    for cname, (mult, cut) in CONDS.items():
        sc = dataclasses.replace(engine.SCENARIOS["shadow_noisy"], noise_mult_below_agl=mult, noise_mult_agl=cut)
        for vname, (judge, extra, use_reg) in VARIANTS.items():
            d = engine.Draws(w, sc, 100, 7)
            kw = dict(P.tuned()); kw["cam_policy"] = "conf"; kw.update(extra)
            if use_reg:
                kw["ml2_noise_model"] = reg
            r = engine.simulate(w, tr, sc, judge, d, ml_model=clf if judge == "ml2" else None, **kw)
            oc = collections.Counter(r["outcome"])
            rows.append(dict(world=str(wk[:2]), condition=cname, variant=vname, success=int(r["success"].sum()), rough=oc.get("rough", 0),
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
    df.to_csv(os.path.join(OUT, "x4.csv"), index=False)
    g = df.groupby(["condition", "variant"])[["success", "rough", "crash", "alt_rms"]].mean().round(1)
    print("\nMean over the 4 tuning worlds (success / rough / crash = counts out of 100)\n", g.to_string())
    pw = df.pivot_table(index=["condition", "variant"], columns="world", values="success")
    print("\nPer world (landings out of 100)\n", pw.to_string())


if __name__ == "__main__":
    mp.freeze_support()
    main()
