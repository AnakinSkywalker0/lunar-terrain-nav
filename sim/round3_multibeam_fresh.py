"""Fresh-world check of the multi-beam comparison (never touches Site04).

  group A: procedural worlds 14, 15, 16 (never used for training or tuning), seed 101
  group B: the four tuning worlds again with a new seed 202 (seed robustness only)

DECISION RULES, written BEFORE this script was run and before the tuning-world multi-beam table was read (group A only, mean of the 3 worlds,
100 descents each; sensor geometry assumed, 3 beams at 22.5 deg). Disclosure: a 30-descent smoke run on one tuning world (procedural 11, x8 noise)
had been seen, in which PITFAL multi-beam, tolerance multi-beam + noise floor and the version with consensus all scored 96.7% and plain
tolerance multi-beam 76.7%.
  M1  Consensus helps against independent beam faults: in INDEPENDENT fault mode, "tolerance multi-beam + noise floor + consensus" beats
      "tolerance multi-beam + noise floor" by at least 3 points in cliff + faults at nominal noise.
  M2  The noise-floor gate with consensus is no more than 3 points below PITFAL multi-beam at each of cliff + faults, x4, x8 and x16
      (independent mode).
  M3  Common-mode faults: "tolerance multi-beam + noise floor" is no more than 3 points below PITFAL multi-beam at each of those four conditions.
Anything else (group B, false-rejection and missed-fault columns, other pairs) is exploratory. A failed rule is reported as failed.

  python sim/round3_multibeam_fresh.py          output: out/round3/multibeam_fresh.csv
"""
import multiprocessing as mp
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import pipeline as P  # noqa: E402
from ml2_noise_normal import CONDS  # noqa: E402
from round3_multibeam import MB, REF, SHORT  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round3")
N = 100
GA, GB = "A fresh worlds (seed 101)", "B tuning worlds, new seed 202"
WORLDS = [(("proc", s), 101, GA) for s in (14, 15, 16)] + [(("proc", s), 202, GB) for s in P.TUNE_SEEDS] + \
         [(("site01", P.SUN_EL, P.SUN_AZ), 202, GB)]
CONDN = ["cliff", "x4", "x8", "x16"]


def task(spec):
    (wk, seed, group), cond, mode = spec
    w, tr = P.get_world(wk)
    sc = CONDS[SHORT[cond]]
    cfgs = dict(MB)
    if mode == "independent":
        cfgs.update(REF)
    rows = []
    for name, (judge, extra) in cfgs.items():
        kw = dict(P.tuned())
        kw["cam_policy"] = "conf"
        kw["fault_label_noise_aware"] = True
        kw.update(extra)
        if judge in engine.MB_JUDGES:
            kw.update(beams=3, beam_fault=mode)
        r = engine.simulate(w, tr, sc, judge, engine.Draws(w, sc, N, seed), **kw)
        s = engine.summarize(r)
        rows.append(dict(group=group, world=str(wk[:2]), condition=SHORT[cond], fault_mode=mode if judge in engine.MB_JUDGES else "n/a",
                         config=name, success_pct=s["success_pct"], false_rej_pct=s["false_rej_pct"], missed_fault_pct=s["missed_fault_pct"]))
    print(time.strftime("%H:%M:%S"), group[:1], wk[:2], cond, mode, flush=True)
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    specs = [(w, c, m) for w in WORLDS for c in CONDN for m in ("independent", "common")]
    with mp.Pool(4) as pool:
        rows = [r for part in pool.imap_unordered(task, specs) for r in part]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "multibeam_fresh.csv"), index=False)
    order = list(MB) + list(REF)
    for g, sub in df.groupby("group"):
        for mode in ("independent", "common"):
            s = sub[sub.fault_mode.isin([mode, "n/a"])] if mode == "independent" else sub[sub.fault_mode == mode]
            t = s.groupby(["condition", "config"]).success_pct.mean().unstack()
            print("\n" + g + " | fault mode:", mode, "| landing success % (mean over worlds, n=100 each)\n",
                  t[[c for c in order if c in t.columns]].round(1).to_string())
    A = df[df.group == GA]
    def mean(mode, cond, cfg):                                   # noqa: E306
        s = A[(A.fault_mode == mode) & (A.condition == SHORT[cond]) & (A.config == cfg)]
        return s.success_pct.mean()
    PB, FL, FC = "PITFAL multi-beam", "tolerance multi-beam + noise floor", "tolerance multi-beam + noise floor + consensus"
    m1 = mean("independent", "cliff", FC) - mean("independent", "cliff", FL)
    m2 = {c: round(mean("independent", c, FC) - mean("independent", c, PB), 1) for c in CONDN}
    m3 = {c: round(mean("common", c, FL) - mean("common", c, PB), 1) for c in CONDN}
    print("\nM1 (consensus helps, +3 needed):", "CONFIRMED" if m1 >= 3 else "NOT confirmed", round(m1, 1))
    print("M2 (floor + consensus within 3 of PITFAL multi-beam):", "CONFIRMED" if all(v >= -3 for v in m2.values()) else "NOT confirmed", m2)
    print("M3 (common mode, floor within 3 of PITFAL multi-beam):", "CONFIRMED" if all(v >= -3 for v in m3.values()) else "NOT confirmed", m3)


if __name__ == "__main__":
    mp.freeze_support()
    main()
