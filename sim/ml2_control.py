"""Control experiment: is the new classifier (ml2) better than the OLD random forest (ml) once both get the same fix?

sim/ml2_diagnose.py showed that giving unflagged readings the terrain+map variance (switch ml2_terrain_R) lifts ml2_hard from
79.8% to 87.2% landing success in 'cliff + faults'. That fix lives in the engine's handling of the ML judges, so the old
`ml` judge may profit just as much. If it does, the new classifier adds little; if not, it does.

  python sim/ml2_control.py          output: out/ml2/control.csv   (tuning worlds only)
"""
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
OLD = os.path.join(P.OUT, "ml_model.pkl")      # the original random forest (untracked; regenerate with: python sim/pipeline.py ml)
NEW = os.path.join(ROOT, "models", "fault_clf_v3.pkl")
VARIANTS = {
    "pitfal (reference)": ("pitfal", {}, None),
    "ml (old RF)": ("ml", {}, "old"),
    "ml (old RF) + terrain_R": ("ml", dict(ml2_terrain_R=True), "old"),
    "ml2_hard (new)": ("ml2", dict(ml2_mode="hard"), "new"),
    "ml2_hard + terrain_R": ("ml2", dict(ml2_mode="hard", ml2_terrain_R=True), "new"),
}
SCEN = ["cliff_fault", "shadow_noisy"]


def task(spec):
    wk, = spec
    w, tr = P.get_world(wk)
    models = {"old": pickle.load(open(OLD, "rb")), "new": pickle.load(open(NEW, "rb")), None: None}
    rows = []
    for sname in SCEN:
        sc = engine.SCENARIOS[sname]
        for vname, (judge, extra, which) in VARIANTS.items():
            d = engine.Draws(w, sc, 100, 7)
            kw = dict(P.tuned()); kw["cam_policy"] = "conf"; kw.update(extra)
            r = engine.simulate(w, tr, sc, judge, d, ml_model=models[which], **kw)
            rows.append(dict(world=str(wk[:2]), scenario=sc.name, variant=vname, success=int(r["success"].sum()),
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
    df.to_csv(os.path.join(OUT, "control.csv"), index=False)
    g = df.groupby(["scenario", "variant"])[["success", "alt_rms"]].mean().round(1)
    print("\nMean over the 4 tuning worlds (success = landings out of 100)\n", g.to_string())
    pw = df.pivot_table(index=["scenario", "variant"], columns="world", values="success")
    print("\nPer world\n", pw.to_string())


if __name__ == "__main__":
    mp.freeze_support()
    main()
