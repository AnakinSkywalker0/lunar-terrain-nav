"""Round-4 DEVELOPMENT grid (exploratory; tuning and fresh worlds only, never Site04).  docs/NEXT_DIRECTION_REVIEW_AND_BUILD.md, C3.4.

Question: when does the running-noise floor absorb systematic mismatch (map error, beam-footprint mismatch) as if it were sensor noise,
and where should the floor enter (gate, update variance, both)?  Arms: plain gate (fixed), PITFAL-style single and multi-beam, tolerance
with the floor in "both" / "gate" / "variance", the oracle noise level (upper bound, not deployable), the map-independent second-difference
floor, VB-AKF, trust v2; multi-beam tolerance with the same floor modes and with the terrain variance at the beam footprint.

  python sim/round4_dev.py [--n 100] [--workers 4] [--part single|multi|all]     output: out/round4/dev_single.csv, dev_multi.csv
Simulation only. Nothing here is a pre-registered result.
"""
import argparse
import dataclasses
import multiprocessing as mp
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import pipeline as P  # noqa: E402
from ml2_noise_normal import CONDS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round4")
CLIFF = CONDS["cliff + faults (nominal noise)"]
NOISE = {"cliff": CLIFF, "x4": CONDS["x4 below 6000 m"], "x8": CONDS["x8 below 6000 m (TRAINING)"], "x16": CONDS["x16 below 6000 m"]}
SINGLE_CONDS = dict(NOISE, **{
    "wrong2000": dataclasses.replace(CLIFF, map_mode="wrong", wrong_offset_m=2000.0),
    "wrong100": dataclasses.replace(CLIFF, map_mode="wrong", wrong_offset_m=100.0),
    "delayed_ts": engine.SCENARIOS["delayed"], "delayed_nots": engine.SCENARIOS["delayed"],
    "dropout": engine.SCENARIOS["dropout"]})
MULTI_CONDS = dict(NOISE, wrong2000=SINGLE_CONDS["wrong2000"])
# (world key, seed): tuning 11-13 + Site01 at seed 7, world 11 and 12 again at seed 202, fresh 14-16 at seed 101
WORLDS = [(("proc", s), 7) for s in (11, 12, 13)] + [(("site01", P.SUN_EL, P.SUN_AZ), 7)] + [(("proc", s), 202) for s in (11, 12)] + \
         [(("proc", s), 101) for s in (14, 15, 16)]
SINGLE = {
    "fixed": ("fixed", {}), "pitfal": ("pitfal", {}), "tolerance": ("tolerance", {}), "trust2": ("trust2", {}),
    "tolerance + floor (both)": ("tolerance", dict(tol_noise_floor=True)),
    "tolerance + floor (gate only)": ("tolerance", dict(tol_noise_floor=True, tol_floor_mode="gate")),
    "tolerance + floor (variance only)": ("tolerance", dict(tol_noise_floor=True, tol_floor_mode="variance")),
    "tolerance + oracle noise (not deployable)": ("tolerance", dict(oracle_R=True)),
    "tolerance + second-difference floor (both)": ("tolerance", dict(tol_noise_floor=True, tol_floor_source="diff")),
    "tolerance + second-difference floor (variance only)": ("tolerance", dict(tol_noise_floor=True, tol_floor_source="diff", tol_floor_mode="variance")),
    "VB-AKF": ("vbakf", {}),
}
MULTI = {
    "pitfal_mb": ("pitfal_mb", {}), "tolerance_mb": ("tolerance_mb", {}),
    "tol_mb + floor (both)": ("tolerance_mb", dict(tol_noise_floor=True)),
    "tol_mb + floor (gate only)": ("tolerance_mb", dict(tol_noise_floor=True, tol_floor_mode="gate")),
    "tol_mb + floor (variance only)": ("tolerance_mb", dict(tol_noise_floor=True, tol_floor_mode="variance")),
    "tol_mb + oracle noise (not deployable)": ("tolerance_mb", dict(oracle_R=True)),
    "tol_mb + floor (both) + footprint terrain": ("tolerance_mb", dict(tol_noise_floor=True, mb_terrain_at_footprint=True)),
    "tol_mb + floor (variance only) + footprint terrain": ("tolerance_mb", dict(tol_noise_floor=True, tol_floor_mode="variance", mb_terrain_at_footprint=True)),
}


def one(part, wk, seed, cname, scen, cfgs, n, mode=None):
    w, tr = P.get_world(wk)
    rows = []
    for name, (judge, extra) in cfgs.items():
        kw = dict(P.tuned())
        kw["cam_policy"] = "conf"
        kw["fault_label_noise_aware"] = True
        kw.update(extra)
        if part == "multi":
            kw.update(beams=3, beam_fault=mode)
        if cname in ("delayed_ts", "delayed_nots"):
            kw["timestamps"] = cname == "delayed_ts"
        if wk[0] == "site04":
            raise RuntimeError("Site04 is not used in the development grid")
        t0 = time.time()
        r = engine.simulate(w, tr, scen, judge, engine.Draws(w, scen, n, seed), **kw)
        s = engine.summarize(r)
        rows.append(dict(part=part, world=str(wk[:2]), seed=seed, condition=cname, fault_mode=mode or "single", config=name, n=n,
                         success_pct=s["success_pct"], success_lo=s["success_lo"], success_hi=s["success_hi"], alt_rms_m=s["alt_rms_m"],
                         false_rej_pct=s["false_rej_pct"], missed_fault_pct=s["missed_fault_pct"], miss_m_median=s["touchdown_miss_m_median"],
                         s_hat_max_median=float(np.median(r["s_hat_max"])), secs=round(time.time() - t0, 1)))
    print(time.strftime("%H:%M:%S"), part, wk[:2], seed, cname, mode or "", flush=True)
    return rows


def task(spec):
    return one(*spec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--part", choices=["single", "multi", "all"], default="all")
    a = ap.parse_args()
    if a.workers > 6:
        raise SystemExit("at most 6 workers (memory)")
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    if a.part in ("single", "all"):
        jobs += [("single", wk, seed, c, sc, SINGLE, a.n, None) for wk, seed in WORLDS for c, sc in SINGLE_CONDS.items()]
    if a.part in ("multi", "all"):
        jobs += [("multi", wk, seed, c, sc, MULTI, a.n, m) for wk, seed in WORLDS for c, sc in MULTI_CONDS.items() for m in ("independent", "common")]
    done = {"single": [], "multi": []}
    with mp.Pool(a.workers) as pool:
        for k, part_rows in enumerate(pool.imap_unordered(task, jobs)):
            done[part_rows[0]["part"]].extend(part_rows)
            if k % 10 == 0 or k == len(jobs) - 1:      # keep a partial CSV in case the run is stopped
                for p_, rows in done.items():
                    if rows:
                        pd.DataFrame(rows).to_csv(os.path.join(OUT, "dev_%s.csv" % p_), index=False)
    print("done", {k: len(v) for k, v in done.items()})


if __name__ == "__main__":
    mp.freeze_support()
    main()
