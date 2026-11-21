"""Round-5 calibration and training on NEW procedural worlds 27-32 (never used before; development worlds 11-16 + Site01 and the
held-out 41-50 are not touched).  Exploratory; nothing here is a pre-registered result.

  python sim/round5_train.py [--n 100] [--workers 4]       output: out/round5/selector.pkl, out/round5/conformal.json, out/round5/train_report.json

* A2 gate selector: gradient-boosted classifier choosing the tight gate or the noise-floor gate per beam reading. Training rows are the
  beam readings where the two gates disagree; the label is which gate made the correct decision (accept a valid reading, reject a
  faulty one). Collected while flying the floor-in-both rule. Validated on two held-back training worlds.
* B1 conformal gate limit: the 99th percentile of the normalised innovation chi = nu^2/S of VALID readings, separately for the single-
  and the three-beam tolerance + floor rule, pooled over the four noise conditions.
"""
import argparse
import json
import multiprocessing as mp
import os
import pickle
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import pipeline as P  # noqa: E402
from round4_dev import NOISE  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round5")
TRAIN_WORLDS = (27, 28, 29, 30, 31, 32)
VALID_WORLDS = (31, 32)            # held back from selector training for validation
TARGET_FALSE_REJECTION = 0.01      # conformal: accept the 99th percentile of valid-reading chi


def task(spec):
    part, wseed, cond, mode = spec
    w, tr = P.get_world(("proc", wseed))
    kw = dict(P.tuned())
    kw["cam_policy"] = "conf"
    kw["fault_label_noise_aware"] = True
    kw["tol_noise_floor"] = True
    scen = NOISE[cond]
    draws = engine.Draws(w, scen, 100, 6000 + wseed)
    if part == "sel":
        coll = []
        engine.simulate(w, tr, scen, "tolerance_mb", draws, beams=3, beam_fault=mode, mb_terrain_at_footprint=True, sel_collect=coll, **kw)
        X = np.concatenate([c[0] for c in coll]) if coll else np.zeros((0, 7))
        y = np.concatenate([c[1] for c in coll]) if coll else np.zeros(0, dtype=int)
        out = (spec, X, y)
    else:
        coll = []
        if part == "chi_single":
            engine.simulate(w, tr, scen, "tolerance", draws, chi_collect=coll, **kw)
        else:
            engine.simulate(w, tr, scen, "tolerance_mb", draws, beams=3, beam_fault=mode, mb_terrain_at_footprint=True, chi_collect=coll, **kw)
        out = (spec, np.concatenate(coll) if coll else np.zeros(0), None)
    print(time.strftime("%H:%M:%S"), spec, flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    conds = ("cliff", "x4", "x8", "x16")
    specs = [("sel", wd, c, m) for wd in TRAIN_WORLDS for c in conds for m in ("independent", "common")]
    specs += [("chi_single", wd, c, None) for wd in TRAIN_WORLDS for c in conds]
    specs += [("chi_multi", wd, c, m) for wd in TRAIN_WORLDS for c in conds for m in ("independent", "common")]
    with mp.Pool(a.workers) as pool:
        got = pool.map(task, specs)
    # --- conformal limits
    lim = {}
    for part in ("chi_single", "chi_multi"):
        chi = np.concatenate([g[1] for g in got if g[0][0] == part])
        lim[part] = dict(limit=float(np.quantile(chi, 1.0 - TARGET_FALSE_REJECTION)), n_valid_readings=int(chi.size),
                         fraction_above_6635=float((chi > engine.CHI2_99).mean()))
    json.dump(lim, open(os.path.join(OUT, "conformal.json"), "w"), indent=1)
    # --- selector
    from sklearn.ensemble import HistGradientBoostingClassifier
    tr_rows = [(g[1], g[2]) for g in got if g[0][0] == "sel" and g[0][1] not in VALID_WORLDS]
    va_rows = [(g[1], g[2]) for g in got if g[0][0] == "sel" and g[0][1] in VALID_WORLDS]
    Xtr, ytr = np.concatenate([r[0] for r in tr_rows]), np.concatenate([r[1] for r in tr_rows])
    Xva, yva = np.concatenate([r[0] for r in va_rows]), np.concatenate([r[1] for r in va_rows])
    clf = HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.1, random_state=0).fit(Xtr, ytr)
    rep = dict(train_rows=int(len(ytr)), valid_rows=int(len(yva)), train_floor_correct_share=float(ytr.mean()),
               valid_floor_correct_share=float(yva.mean()), valid_accuracy=float((clf.predict(Xva) == yva).mean()),
               valid_always_floor_accuracy=float(yva.mean()), valid_always_tight_accuracy=float(1.0 - yva.mean()), conformal=lim)
    final = HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.1, random_state=0).fit(
        np.concatenate([Xtr, Xva]), np.concatenate([ytr, yva]))
    pickle.dump(final, open(os.path.join(OUT, "selector.pkl"), "wb"))
    json.dump(rep, open(os.path.join(OUT, "train_report.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    mp.freeze_support()
    main()
