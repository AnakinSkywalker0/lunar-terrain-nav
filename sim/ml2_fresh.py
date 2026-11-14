"""Fresh worlds and fresh random draws for the learned-noise result.

Everything so far was found and confirmed on procedural worlds 11-13 + Site01 with random seed 7, and the best variant was picked after
looking at those numbers. This script re-runs the final candidates, with nothing changed and nothing tuned, on
  group A: procedural worlds 14, 15, 16 (never used for training (21-26) or tuning (11-13)), random seed 101
  group B: the four tuning worlds again with a new random seed 202
Judges: PITFAL, trust v2, ml2 + learned noise (flagged + unflagged), ml2 + running-innovation noise (the non-ML control).
Six noise conditions as in sim/ml2_noise_normal.py. 100 descents per cell. Site04 is NOT used.

  python sim/ml2_fresh.py        output: out/ml2/fresh.csv
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
B = dict(ml2_mode="hard", ml2_terrain_R=True)
LEARNED = "ml2 + learned noise (flagged + unflagged)"
HEUR = "ml2 + running-innovation noise (non-ML control)"
JUDGES = {"pitfal": ("pitfal", {}, False), "trust2": ("trust2", {}, False),
          LEARNED: ("ml2", dict(B, ml2_noise_normal=True), True), HEUR: ("ml2", dict(B, ml2_noise_heuristic=True), False)}
TASKS = [(("proc", 14), 101, "A fresh worlds (seed 101)"), (("proc", 15), 101, "A fresh worlds (seed 101)"), (("proc", 16), 101, "A fresh worlds (seed 101)")] + \
        [(("proc", s), 202, "B tuning worlds, new seed 202") for s in P.TUNE_SEEDS] + \
        [(("site01", P.SUN_EL, P.SUN_AZ), 202, "B tuning worlds, new seed 202")]


def task(spec):
    wk, seed, group = spec
    w, tr = P.get_world(wk)
    clf = pickle.load(open(os.path.join(ROOT, "models", "fault_clf_v3.pkl"), "rb"))
    reg = pickle.load(open(os.path.join(ROOT, "models", "err_reg_v3.pkl"), "rb"))
    rows = []
    for cname, sc in N.CONDS.items():
        for jname, (judge, extra, use_reg) in JUDGES.items():
            d = engine.Draws(w, sc, 100, seed)
            kw = dict(P.tuned()); kw["cam_policy"] = "conf"; kw.update(extra)
            if use_reg:
                kw["ml2_noise_model"] = reg
            r = engine.simulate(w, tr, sc, judge, d, ml_model=clf if judge == "ml2" else None, **kw)
            rows.append(dict(group=group, world=str(wk[:2]), condition=cname, judge=jname, success=int(r["success"].sum()),
                             alt_rms=float(np.sqrt(r["alt_sq"].sum() / max(r["alt_n"].sum(), 1)))))
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    P.warm(list(dict.fromkeys(t[0] for t in TASKS)))
    rows = []
    with mp.Pool(4) as pool:
        for r in pool.imap_unordered(task, TASKS):
            rows += r
            print("  done", r[0]["group"], r[0]["world"], flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "fresh.csv"), index=False)
    order = ["pitfal", "trust2", HEUR, LEARNED]
    for g, sub in df.groupby("group"):
        t = sub.pivot_table(index="condition", columns="judge", values="success").reindex(list(N.CONDS))[order].round(1)
        print(f"\n{g}: landing success % (mean over {sub.world.nunique()} worlds, 100 descents each)\n", t.to_string(), flush=True)
    t = df.pivot_table(index="condition", columns="judge", values="success").reindex(list(N.CONDS))[order].round(1)
    print("\nAll 7 world runs pooled\n", t.to_string())
    wins = (df.pivot_table(index=["group", "world", "condition"], columns="judge", values="success"))
    print("\nLearned minus non-ML control, per cell: mean %.1f, positive in %d of %d cells" %
          ((wins[LEARNED] - wins[HEUR]).mean(), int(((wins[LEARNED] - wins[HEUR]) > 0).sum()), len(wins)))
    print("Learned minus PITFAL, per cell: mean %.1f, positive in %d of %d cells" %
          ((wins[LEARNED] - wins["pitfal"]).mean(), int(((wins[LEARNED] - wins["pitfal"]) > 0).sum()), len(wins)))
    print("Learned minus trust v2, per cell: mean %.1f, positive in %d of %d cells" %
          ((wins[LEARNED] - wins["trust2"]).mean(), int(((wins[LEARNED] - wins["trust2"]) > 0).sum()), len(wins)))


if __name__ == "__main__":
    mp.freeze_support()
    main()
