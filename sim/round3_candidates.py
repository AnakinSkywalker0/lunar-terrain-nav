"""Round-3 candidate engine changes, TUNING worlds only (procedural 11-13 + real Site01). Never touches Site04.

Compares each existing judge with the same judge plus a candidate switch of sim/engine.py:
  tolerance            vs  tolerance + tol_noise_floor        (running innovation-size noise estimate s_hat)
  wait                 vs  wait + terrain_R                   (terrain + map variance on unflagged readings)
  second               vs  second + terrain_R
  ml (if the old forest exists) vs ml + terrain_R
plus pitfal and trust2 as references. Conditions: cliff + faults and the shadow_noisy noise levels used in the ml-eval study.
Second output: the same judges scored with the old and the noise-aware ground-truth fault label (decisions are identical; only the
false-rejection and missed-fault columns change).

  python sim/round3_candidates.py            output: out/round3/candidates_tune.csv, label_effect_tune.csv
This is a TUNING comparison (100 descents per world, seed 7). Anything chosen from it must be pre-registered before a Site04 run.
"""
import multiprocessing as mp
import os
import pickle
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import pipeline as P  # noqa: E402
from ml2_noise_normal import CONDS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round3")
N, SEED = 100, 7
ML_PATH = os.path.join(P.OUT, "ml_model.pkl")
CONFIGS = {
    "pitfal": ("pitfal", {}),
    "trust2": ("trust2", {}),
    "tolerance": ("tolerance", {}),
    "tolerance + noise floor": ("tolerance", dict(tol_noise_floor=True)),
    "wait": ("wait", {}),
    "wait + terrain_R": ("wait", dict(terrain_R=True)),
    "second": ("second", {}),
    "second + terrain_R": ("second", dict(terrain_R=True)),
    "ml": ("ml", {}),
    "ml + terrain_R": ("ml", dict(terrain_R=True)),
}


def task(spec):
    wk, cond, label_aware = spec
    w, tr = P.get_world(wk)
    sc = CONDS[cond]
    mdl = pickle.load(open(ML_PATH, "rb")) if os.path.exists(ML_PATH) else None
    rows = []
    for name, (judge, extra) in CONFIGS.items():
        if judge == "ml" and mdl is None:
            continue
        kw = dict(P.tuned())
        kw["cam_policy"] = "conf"
        kw.update(extra)
        kw["fault_label_noise_aware"] = label_aware
        d = engine.Draws(w, sc, N, SEED)
        r = engine.simulate(w, tr, sc, judge, d, ml_model=mdl if judge == "ml" else None, **kw)
        s = engine.summarize(r)
        rows.append(dict(world=str(wk[:2]), condition=cond, config=name, label_aware=label_aware, success_pct=s["success_pct"],
                         alt_rms_m=s["alt_rms_m"], false_rej_pct=s["false_rej_pct"], missed_fault_pct=s["missed_fault_pct"]))
    print(time.strftime("%H:%M:%S"), wk[:2], cond, "aware" if label_aware else "old", flush=True)
    return rows


def main():
    worlds = [("proc", s) for s in P.TUNE_SEEDS] + [("site01", P.SUN_EL, P.SUN_AZ)]
    os.makedirs(OUT, exist_ok=True)
    for wk in worlds:       # warm the world caches once, in the parent
        P.get_world(wk)
    specs = [(wk, c, False) for wk in worlds for c in CONDS]
    specs += [(wk, c, True) for wk in worlds for c in ("cliff + faults (nominal noise)", "x8 below 6000 m (TRAINING)")]
    with mp.Pool(4) as pool:
        rows = [r for part in pool.imap_unordered(task, specs) for r in part]
    df = pd.DataFrame(rows)
    df[~df.label_aware].drop(columns="label_aware").to_csv(os.path.join(OUT, "candidates_tune.csv"), index=False)
    df.to_csv(os.path.join(OUT, "label_effect_tune.csv"), index=False)
    main_t = df[~df.label_aware].groupby(["condition", "config"]).success_pct.mean().unstack().round(1)
    order = [c for c in CONFIGS if c in main_t.columns]
    print("\nLanding success %, mean of the 4 tuning worlds (100 descents each)\n", main_t[order].to_string())
    lab = df[df.condition.isin(["cliff + faults (nominal noise)", "x8 below 6000 m (TRAINING)"])]
    eff = lab.groupby(["condition", "config", "label_aware"])[["success_pct", "false_rej_pct", "missed_fault_pct"]].mean().round(1)
    print("\nEffect of the ground-truth label (success must not change)\n", eff.to_string())


if __name__ == "__main__":
    main()
