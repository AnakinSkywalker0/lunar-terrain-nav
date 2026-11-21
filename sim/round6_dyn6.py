"""Round-6 DEVELOPMENT study: does the ranking of the altimeter rules survive a 6-DOF lander? (exploratory; development worlds only)

Never uses Site04, the reserved worlds 41-50 or the round-4 held-out worlds 17-20.  Nothing here is a pre-registered result.
Vehicle variants (sim/dyn6.py; every number ASSUMED): 3-DOF (the old point mass), 6-DOF default, "sluggish" (weak reaction control, slow
throttle) and "degraded" (large thrust misalignment and centre-of-mass offset, gyro-only attitude with a 10x gyro bias).

  python sim/round6_dyn6.py [--n 60] [--workers 4]        output: out/round6/dyn6_dev.csv
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
import dyn6  # noqa: E402
import engine  # noqa: E402
import pipeline as P  # noqa: E402
import round4_dev as R4  # noqa: E402
import round5_dev as R5  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round6")
D0 = dyn6.Dyn6Config()
VARIANTS = {
    "3-DOF (point mass)": None,
    "6-DOF default": D0,
    "6-DOF sluggish": dataclasses.replace(D0, torque_max=150.0, tau_thr=1.0),
    "6-DOF degraded": dataclasses.replace(D0, misalign_deg=0.5, com_offset_m=0.08, st_gain=0.0, gyro_bias_dps=0.05),
}
CONDS = ("cliff", "x8", "x16")
SINGLE = {k: R5.SINGLE[k] for k in ("baseline: PITFAL-style", "A: tolerance + noise floor", "B2 Student-t (4 dof) + floor")}
MULTI = {k: R5.MULTI[k] for k in ("baseline: PITFAL-style multi-beam", "A: floor both + footprint terrain", "B2 Student-t (4 dof) + floor")}


def one(part, wk, seed, cname, n):
    if wk[0] == "site04":
        raise RuntimeError("Site04 is not used")
    w, tr = P.get_world(wk)
    scen = R4.NOISE[cname]
    cfgs = SINGLE if part == "single" else MULTI
    rows = []
    for vname, vcfg in VARIANTS.items():
        for name, (judge, extra, _) in cfgs.items():
            kw = dict(P.tuned())
            kw["cam_policy"] = "conf"
            kw["fault_label_noise_aware"] = True
            kw.update(R5.resolve(extra))
            if part == "multi":
                kw.update(beams=3, beam_fault="independent")
            t0 = time.time()
            r = engine.simulate(w, tr, scen, judge, engine.Draws(w, scen, n, seed), dyn6=vcfg, **kw)
            s = engine.summarize(r)
            six = vcfg is not None
            rows.append(dict(part=part, world=str(wk[:2]), seed=seed, condition=cname, variant=vname, config=name, n=n, success_pct=s["success_pct"],
                             legacy_pct=100.0 * float(r["success_legacy"].mean()) if six else s["success_pct"],
                             crash_pct=100.0 * float(np.mean(r["outcome"] == "crash")), rough_pct=100.0 * float(np.mean(r["outcome"] == "rough")),
                             timeout_pct=100.0 * float(np.mean(r["outcome"] == "timeout")), alt_rms_m=s["alt_rms_m"],
                             tilt_max_deg=float(np.median(r["tilt_max"])) if six else float("nan"),
                             impact_tilt_deg=float(np.median(r["impact_tilt"])) if six else float("nan"),
                             att_err_deg=float(np.median(r["att_err_rms_deg"])) if six else float("nan"),
                             rcs_fuel_kg=float(np.median(r["rcs_fuel"])) if six else float("nan"), secs=round(time.time() - t0, 1)))
    print(time.strftime("%H:%M:%S"), part, wk[:2], seed, cname, flush=True)
    return rows


def task(spec):
    return one(*spec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.workers > 6:
        raise SystemExit("at most 6 workers (memory)")
    os.makedirs(OUT, exist_ok=True)
    jobs = [(part, wk, seed, c, a.n) for wk, seed in R4.WORLDS for c in CONDS for part in ("single", "multi")]
    rows = []
    with mp.Pool(a.workers) as pool:
        for k, part_rows in enumerate(pool.imap_unordered(task, jobs)):
            rows.extend(part_rows)
            if k % 5 == 0 or k == len(jobs) - 1:
                pd.DataFrame(rows).to_csv(os.path.join(OUT, "dyn6_dev.csv"), index=False)
    print("done", len(rows))


if __name__ == "__main__":
    mp.freeze_support()
    main()
