"""Does the CLASSIFIER matter? Ablation of the fault classifier inside the strong non-ML structure.

Starting point (sim/ml2_control_noise.py): ml2 hard mode + terrain-variance fix + running-innovation noise floor (no learned noise model).
Here the classifier's decision on gate-failing readings is replaced by a constant:
  accept all flagged readings  (threshold 1.01): no fault rejection at all, flagged readings are used with the terrain-aware noise
  reject all flagged readings  (threshold -0.01): every reading that fails the 99% gate is thrown away (like a fixed gate, but with the
                                                  terrain variance and adaptive noise on the readings that pass)
Compared with the full control (classifier at 0.5), PITFAL and trust v2 (from out/ml2/noise_normal.csv / control_noise.csv, same worlds
and seed 7). If both ablations are as good as the full control, the classifier adds nothing in this structure. Tuning worlds only.

  python sim/ml2_ablate.py       output: out/ml2/ablate.csv
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
B = dict(ml2_mode="hard", ml2_terrain_R=True, ml2_noise_heuristic=True)
FULL = "ml2 + running noise, classifier at 0.5 (full control)"
VARIANTS = {"ablation: accept ALL flagged readings (no classifier)": dict(B, ml2_threshold=1.01),
            "ablation: reject ALL flagged readings (no classifier)": dict(B, ml2_threshold=-0.01)}


def task(spec):
    wk, = spec
    w, tr = P.get_world(wk)
    clf = pickle.load(open(os.path.join(ROOT, "models", "fault_clf_v3.pkl"), "rb"))
    rows = []
    for cname, sc in N.CONDS.items():
        for vname, extra in VARIANTS.items():
            d = engine.Draws(w, sc, 100, 7)
            kw = dict(P.tuned()); kw["cam_policy"] = "conf"; kw.update(extra)
            r = engine.simulate(w, tr, sc, "ml2", d, ml_model=clf, **kw)
            rows.append(dict(world=str(wk[:2]), condition=cname, judge=vname, success=int(r["success"].sum()),
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
    new.to_csv(os.path.join(OUT, "ablate.csv"), index=False)
    old = pd.read_csv(os.path.join(OUT, "noise_normal.csv"))
    ctl = pd.read_csv(os.path.join(OUT, "control_noise.csv")).assign(judge=FULL)
    df = pd.concat([old[old.judge.isin(["pitfal", "trust2"])], ctl, new])
    order = ["pitfal", "trust2", FULL] + list(VARIANTS)
    t = df.pivot_table(index="condition", columns="judge", values="success").reindex(list(N.CONDS))[order].round(1)
    print("\nLanding success % (mean of 4 tuning worlds, 100 descents each, seed 7)\n", t.to_string())
    pw = new.pivot_table(index=["condition", "judge"], columns="world", values="success")
    print("\nAblations per world\n", pw.to_string())


if __name__ == "__main__":
    mp.freeze_support()
    main()
