"""Round-4 development check for Direction 2: correlated altimeter noise (AR(1), phi 0.5 and 0.9, same variance), single beam.
Tuning and fresh worlds only. output: out/round4/dev_ar1.csv     python sim/round4_ar1.py"""
import multiprocessing as mp
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import round4_dev as D  # noqa: E402

ARMS = ["pitfal", "tolerance", "trust2", "tolerance + floor (both)", "tolerance + second-difference floor (both)",
        "tolerance + oracle noise (not deployable)", "VB-AKF"]


def task(spec):
    wk, seed, phi, cname = spec
    cfgs = {k: (D.SINGLE[k][0], dict(D.SINGLE[k][1], ar1_phi=phi)) for k in ARMS}
    rows = D.one("single", wk, seed, "%s_phi%.1f" % (cname, phi), D.NOISE[cname], cfgs, 100)
    return rows


if __name__ == "__main__":
    mp.freeze_support()
    jobs = [(wk, seed, phi, c) for wk, seed in D.WORLDS for phi in (0.5, 0.9) for c in ("x4", "x8", "x16")]
    with mp.Pool(4) as pool:
        rows = [r for part in pool.imap_unordered(task, jobs) for r in part]
    pd.DataFrame(rows).to_csv(os.path.join(D.OUT, "dev_ar1.csv"), index=False)
    print("done", len(rows))
