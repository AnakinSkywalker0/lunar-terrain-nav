"""Fresh-world check of the round-3 candidate switches (never touches Site04).

  group A: procedural worlds 14, 15, 16 (never used for training (21-26) or tuning (11-13)), seed 101
  group B: the four tuning worlds again with a new seed 202 (seed robustness only; the worlds are not fresh)

DECISION RULES, written BEFORE this script was run (group A only, mean of the 3 worlds, 100 descents each):
  R1  "tolerance + noise floor" is CONFIRMED if it beats plain tolerance by at least 10 points at x4, x8 and x16 noise, is at or above
      PITFAL-style at x8 and x16, and is no more than 3 points below PITFAL-style in cliff + faults at nominal noise.
  R2  "wait + terrain_R" and "ml + terrain_R" are CONFIRMED if each beats its plain judge by at least 5 points at nominal noise and at x8.
  Anything else (second + terrain_R, group B, other cells) is exploratory. A failed rule is reported as failed.

  python sim/round3_fresh.py        output: out/round3/fresh.csv
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
from round3_candidates import CONFIGS, ML_PATH, N  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round3")
GA, GB = "A fresh worlds (seed 101)", "B tuning worlds, new seed 202"
WORLDS = [(("proc", s), 101, GA) for s in (14, 15, 16)] + [(("proc", s), 202, GB) for s in P.TUNE_SEEDS] + \
         [(("site01", P.SUN_EL, P.SUN_AZ), 202, GB)]


def task(spec):
    (wk, seed, group), cond = spec
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
        d = engine.Draws(w, sc, N, seed)
        r = engine.simulate(w, tr, sc, judge, d, ml_model=mdl if judge == "ml" else None, **kw)
        rows.append(dict(group=group, world=str(wk[:2]), condition=cond, config=name, success=int(r["success"].sum()),
                         alt_rms=float(engine.summarize(r)["alt_rms_m"])))
    print(time.strftime("%H:%M:%S"), group[:1], wk[:2], cond, flush=True)
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    specs = [(w, c) for w in WORLDS for c in CONDS]
    with mp.Pool(4) as pool:
        rows = [r for part in pool.imap_unordered(task, specs) for r in part]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "fresh.csv"), index=False)
    order = [c for c in CONFIGS if c in set(df.config)]
    for g, sub in df.groupby("group"):
        t = sub.groupby(["condition", "config"]).success.mean().unstack()[order].round(1)
        print("\n" + g + ": landing success % (mean over worlds, 100 descents each)\n", t.to_string())
    A = df[df.group == GA].groupby(["condition", "config"]).success.mean().unstack()
    cl, x4, x8, x16 = "cliff + faults (nominal noise)", "x4 below 6000 m", "x8 below 6000 m (TRAINING)", "x16 below 6000 m"
    d = lambda a, b, c: A.loc[c, a] - A.loc[c, b]           # noqa: E731
    r1 = (all(d("tolerance + noise floor", "tolerance", c) >= 10 for c in (x4, x8, x16))
          and all(d("tolerance + noise floor", "pitfal", c) >= 0 for c in (x8, x16))
          and d("tolerance + noise floor", "pitfal", cl) >= -3)
    print("\nR1 (tolerance + noise floor):", "CONFIRMED" if r1 else "NOT confirmed")
    for j in ("wait", "ml"):
        if f"{j} + terrain_R" in A.columns:
            r2 = all(d(f"{j} + terrain_R", j, c) >= 5 for c in (cl, x8))
            print(f"R2 ({j} + terrain_R):", "CONFIRMED" if r2 else "NOT confirmed",
                  {c: round(d(f"{j} + terrain_R", j, c), 1) for c in (cl, x8)})


if __name__ == "__main__":
    mp.freeze_support()
    main()
