"""Multi-beam consensus check vs the noise-floor gate, TUNING worlds only (procedural 11-13 + Site01). Never touches Site04.

Sensor: 3 beams canted 22.5 deg from nadir (ASSUMED NDL-like geometry), independent noise per beam; faults either hit one beam at a time
("independent", what a consensus check can catch) or all beams at once ("common", what it cannot). Judges (all see the same beam readings):
  PITFAL multi-beam        consensus check across beams + fixed 99% gate with noise inflation after a flag (our interpretation of PITFAL)
  tolerance multi-beam     per-beam tolerance gate (terrain + map variance), no consensus
  + noise floor            the running-noise-estimate floor of round 3
  + noise floor + consensus  the floor plus the consensus check
Single-beam references (pitfal, tolerance + noise floor) use the legacy altimeter and are not affected by the beam settings.

  python sim/round3_multibeam.py [--n 100] [--cond cliff x4 x8 x16]       output: out/round3/multibeam_tune.csv
Tuning comparison only (seed 7). Anything chosen from it must be pre-registered before a Site04 run.
"""
import argparse
import multiprocessing as mp
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import pipeline as P  # noqa: E402
from ml2_noise_normal import CONDS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round3")
SEED = 7
SHORT = {"cliff": "cliff + faults (nominal noise)", "x2": "x2 below 6000 m", "x4": "x4 below 6000 m",
         "x8": "x8 below 6000 m (TRAINING)", "x16": "x16 below 6000 m"}
MB = {
    "PITFAL multi-beam": ("pitfal_mb", {}),
    "tolerance multi-beam": ("tolerance_mb", {}),
    "tolerance multi-beam + noise floor": ("tolerance_mb", dict(tol_noise_floor=True)),
    "tolerance multi-beam + noise floor + consensus": ("tolerance_mb", dict(tol_noise_floor=True, mb_consensus=True)),
}
REF = {"pitfal (single beam)": ("pitfal", {}), "tolerance + noise floor (single beam)": ("tolerance", dict(tol_noise_floor=True))}


def task(spec):
    wk, cond, mode, n = spec
    w, tr = P.get_world(wk)
    sc = CONDS[cond]
    rows = []
    cfgs = dict(MB)
    if mode == "independent":
        cfgs.update(REF)
    for name, (judge, extra) in cfgs.items():
        kw = dict(P.tuned())
        kw["cam_policy"] = "conf"
        kw["fault_label_noise_aware"] = True
        kw.update(extra)
        if judge in engine.MB_JUDGES:
            kw.update(beams=3, beam_fault=mode)
        t0 = time.time()
        r = engine.simulate(w, tr, sc, judge, engine.Draws(w, sc, n, SEED), **kw)
        s = engine.summarize(r)
        rows.append(dict(world=str(wk[:2]), condition=cond, fault_mode=mode if judge in engine.MB_JUDGES else "n/a", config=name,
                         success_pct=s["success_pct"], alt_rms_m=s["alt_rms_m"], false_rej_pct=s["false_rej_pct"],
                         missed_fault_pct=s["missed_fault_pct"], secs=round(time.time() - t0, 1)))
    print(time.strftime("%H:%M:%S"), wk[:2], cond, mode, flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--cond", nargs="+", default=["cliff", "x4", "x8", "x16"], choices=list(SHORT))
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    worlds = [("proc", s) for s in P.TUNE_SEEDS] + [("site01", P.SUN_EL, P.SUN_AZ)]
    os.makedirs(OUT, exist_ok=True)
    specs = [(w, SHORT[c], m, a.n) for w in worlds for c in a.cond for m in ("independent", "common")]
    with mp.Pool(min(a.workers, 6)) as pool:
        rows = [r for part in pool.imap_unordered(task, specs) for r in part]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "multibeam_tune.csv"), index=False)
    order = list(MB) + list(REF)
    for mode in ("independent", "common"):
        sub = df[(df.fault_mode == mode) | (df.fault_mode == "n/a")] if mode == "independent" else df[df.fault_mode == mode]
        t = sub.groupby(["condition", "config"]).success_pct.mean().unstack()
        print("\nFAULT MODE:", mode, "- landing success %%, mean of the 4 tuning worlds (n=%d each)\n" % a.n,
              t[[c for c in order if c in t.columns]].round(1).to_string())
    m = df[df.fault_mode != "n/a"].groupby(["fault_mode", "condition", "config"])[["false_rej_pct", "missed_fault_pct"]].mean().round(1)
    print("\nFalse rejection / missed fault (%, noise-aware label, per beam reading)\n", m.to_string())


if __name__ == "__main__":
    mp.freeze_support()
    main()
