"""Round-5 DEVELOPMENT grid (exploratory; development worlds 11-16 + Site01 only; never Site04, never the reserved worlds 41-50, never 17-20).
docs/LANTERN_Architecture_and_Build_Plan.docx, Sections 4-6.

Every technique of the plan is an engine switch (default off) and one row of the registries below; all use untuned constants and the same
cells, so differences are paired per world.  Not run: B5 (point-mass filter) and B6 (learned gain, KalmanNet), see docs/ROUND5_DEV_RESULTS.md.

  python sim/round5_dev.py [--n 100] [--workers 4] [--part single|multi|all]       output: out/round5/dev_single.csv, dev_multi.csv
Needs out/round5/selector.pkl and conformal.json (python sim/round5_train.py).  Simulation only. Nothing here is a pre-registered result.
"""
import argparse
import dataclasses
import json
import multiprocessing as mp
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import pipeline as P  # noqa: E402
import round4_dev as R4  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round5")
CLIFF = R4.CLIFF
WORLDS = R4.WORLDS
_SPARSE = dict(burst_rate=1 / 60.0, burst_len=(40, 80))      # long, rare bursts so slow faults have time to develop
SINGLE_CONDS = dict(R4.SINGLE_CONDS)
SINGLE_CONDS.update({
    "stuck": dataclasses.replace(CLIFF, fault_type="stuck", **_SPARSE),
    "drift": dataclasses.replace(CLIFF, fault_type="drift", **_SPARSE),
    "scale": dataclasses.replace(CLIFF, fault_type="scale", **_SPARSE),
    "shadow": engine.SCENARIOS["shadow_noisy"],
})
MULTI_CONDS = dict(R4.NOISE, wrong2000=R4.SINGLE_CONDS["wrong2000"], beam_dropout=dataclasses.replace(CLIFF, fault_type="beam_dropout"))
FL = dict(tol_noise_floor=True)
# name -> (judge, extra kwargs, conditions where it is run (None = all))
SINGLE = {
    "baseline: fixed": ("fixed", {}, None), "baseline: PITFAL-style": ("pitfal", {}, None), "baseline: tolerance": ("tolerance", {}, None),
    "baseline: trust v2": ("trust2", {}, None), "baseline: VB-AKF": ("vbakf", {}, None),
    "A: tolerance + noise floor": ("tolerance", dict(FL), None),
    "oracle noise (not flyable)": ("tolerance", dict(oracle_R=True), None),
    "A3 IMM-style noise modes": ("tolerance", dict(imm=True), None),
    "A4 delay estimation (no stamps)": ("tolerance", dict(FL, delay_est=True, timestamps=False), ["delayed_nots"]),
    "A5 map-offset search": ("tolerance", dict(FL, map_search=True), ["cliff", "x8", "wrong100", "wrong2000"]),
    "B1 conformal gate limit": ("tolerance", dict(FL, gate_chi2="CONF_SINGLE"), None),
    "B2 Student-t (4 dof), no floor": ("tolerance", dict(robust_t=4.0), None),
    "B2 Student-t (4 dof) + floor": ("tolerance", dict(FL, robust_t=4.0), None),
    "B3 CUSUM + floor": ("tolerance", dict(FL, cusum=True), None),
    "B4 soft camera weighting + floor": ("tolerance", dict(FL, cam_policy="soft"), ["cliff", "x8", "shadow"]),
    "B8 second altimeter + floor": ("tolerance", dict(FL, alt2=True), None),
}
FP = dict(FL, mb_terrain_at_footprint=True)
MULTI = {
    "baseline: PITFAL-style multi-beam": ("pitfal_mb", {}, None), "baseline: tolerance_mb": ("tolerance_mb", {}, None),
    "A: floor both + footprint terrain": ("tolerance_mb", dict(FP), None),
    "B: floor update-only + footprint terrain": ("tolerance_mb", dict(FP, tol_floor_mode="variance"), None),
    "oracle noise (not flyable)": ("tolerance_mb", dict(oracle_R=True), None),
    "A1 joint three-beam update": ("tolerance_mb", dict(FP, joint_update=True), None),
    "A2 learned gate selector": ("tolerance_mb", dict(FP, selector="SELECTOR"), None),
    "B1 conformal gate limit": ("tolerance_mb", dict(FP, gate_chi2="CONF_MULTI"), None),
    "B2 Student-t (4 dof) + floor": ("tolerance_mb", dict(FP, robust_t=4.0), None),
    "B7 solution separation": ("tolerance_mb", dict(FP, solsep=True), None),
    "A1+A2 joint update + selector": ("tolerance_mb", dict(FP, joint_update=True, selector="SELECTOR"), None),
}
_CACHE = {}


def resolve(extra):
    """Fill in the trained pieces (selector, conformal limits) by name."""
    out = dict(extra)
    if "selector" in out:
        if "sel" not in _CACHE:
            _CACHE["sel"] = pickle.load(open(os.path.join(OUT, "selector.pkl"), "rb"))
        out["selector"] = _CACHE["sel"]
    for k, key in (("CONF_SINGLE", "chi_single"), ("CONF_MULTI", "chi_multi")):
        if out.get("gate_chi2") == k:
            out["gate_chi2"] = json.load(open(os.path.join(OUT, "conformal.json")))[key]["limit"]
    return out


def one(part, wk, seed, cname, scen, cfgs, n, mode=None):
    w, tr = P.get_world(wk)
    if wk[0] == "site04":
        raise RuntimeError("Site04 is not used in the development grid")
    rows = []
    for name, (judge, extra, conds) in cfgs.items():
        if conds is not None and cname not in conds:
            continue
        kw = dict(P.tuned())
        kw["cam_policy"] = "conf"
        kw["fault_label_noise_aware"] = True
        kw.update(resolve(extra))
        if part == "multi":
            kw.update(beams=3, beam_fault=mode)
        if "timestamps" not in kw and cname in ("delayed_ts", "delayed_nots"):
            kw["timestamps"] = cname == "delayed_ts"
        t0 = time.time()
        d = engine.Draws(w, scen, n, seed)
        r = engine.simulate(w, tr, scen, judge, d, **kw)
        s = engine.summarize(r)
        found = float(np.mean(np.hypot(r["est_off_x"] - scen.wrong_offset_m, r["est_off_y"]) < 300.0)) if scen.map_mode == "wrong" else float("nan")
        lag_err = float(np.mean(np.abs(r["est_lag"] - d.delay_steps))) if kw.get("delay_est") else float("nan")
        rows.append(dict(part=part, world=str(wk[:2]), seed=seed, condition=cname, fault_mode=mode or "single", config=name, n=n,
                         success_pct=s["success_pct"], success_lo=s["success_lo"], success_hi=s["success_hi"], alt_rms_m=s["alt_rms_m"],
                         false_rej_pct=s["false_rej_pct"], missed_fault_pct=s["missed_fault_pct"], miss_m_median=s["touchdown_miss_m_median"],
                         nees_mean=float(np.sum(r["nees_sum"]) / max(np.sum(r["alt_n"]), 1.0)), offset_found_share=found, lag_error_steps=lag_err,
                         secs=round(time.time() - t0, 1)))
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
        for wk, seed in WORLDS:
            for c, sc in MULTI_CONDS.items():
                for m in (("independent",) if c == "beam_dropout" else ("independent", "common")):
                    jobs.append(("multi", wk, seed, c, sc, MULTI, a.n, m))
    done = {"single": [], "multi": []}
    with mp.Pool(a.workers) as pool:
        for k, part_rows in enumerate(pool.imap_unordered(task, jobs)):
            if part_rows:
                done[part_rows[0]["part"]].extend(part_rows)
            if k % 10 == 0 or k == len(jobs) - 1:
                for p_, rows in done.items():
                    if rows:
                        pd.DataFrame(rows).to_csv(os.path.join(OUT, "dev_%s.csv" % p_), index=False)
    print("done", {k: len(v) for k, v in done.items()})


if __name__ == "__main__":
    mp.freeze_support()
    main()
