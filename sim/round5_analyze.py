"""Summarise out/round5/dev_*.csv: mean landing success per rule and condition, and paired per-world differences with bootstrap
intervals over the development cells (the world is the unit of evidence).   python sim/round5_analyze.py

Writes out/round5/summary_means.csv and summary_paired.csv and prints compact tables.  Exploratory (development cells only).
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round5")
REF = {"single": "A: tolerance + noise floor", "multi": "A: floor both + footprint terrain"}
BASE = {"single": "baseline: PITFAL-style", "multi": "baseline: PITFAL-style multi-beam"}
rng = np.random.default_rng(0)


def paired(df, ref):
    """mean and 95 % bootstrap interval of (config - ref) over the world cells, per condition / fault mode."""
    rows = []
    for (cond, mode), g in df.groupby(["condition", "fault_mode"]):
        pv = g.pivot_table(index=["world", "seed"], columns="config", values="success_pct")
        if ref not in pv:
            continue
        for cfg in pv.columns:
            if cfg == ref:
                continue
            d = (pv[cfg] - pv[ref]).dropna().to_numpy()
            if len(d) < 3:
                continue
            boots = [rng.choice(d, len(d)).mean() for _ in range(2000)]
            rows.append(dict(condition=cond, fault_mode=mode, config=cfg, ref=ref, cells=len(d), diff=d.mean(), lo=np.percentile(boots, 2.5), hi=np.percentile(boots, 97.5)))
    return pd.DataFrame(rows)


def main():
    means, pairs = [], []
    for part in ("single", "multi"):
        p = os.path.join(OUT, "dev_%s.csv" % part)
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p)
        m = df.groupby(["part", "condition", "fault_mode", "config"]).agg(
            success=("success_pct", "mean"), cells=("success_pct", "size"), false_rej=("false_rej_pct", "mean"),
            missed=("missed_fault_pct", "mean"), nees=("nees_mean", "mean"), offset_found=("offset_found_share", "mean")).reset_index()
        means.append(m)
        for ref in (REF[part], BASE[part]):
            pairs.append(paired(df, ref))
        wide = df.groupby(["condition", "fault_mode", "config"]).success_pct.mean().unstack(["condition", "fault_mode"]).round(0)
        pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_colwidth", 44)
        print("\n==", part, "(mean landing success %, development cells)")
        print(wide.to_string())
    pd.concat(means).to_csv(os.path.join(OUT, "summary_means.csv"), index=False)
    pd.concat(pairs).to_csv(os.path.join(OUT, "summary_paired.csv"), index=False)


if __name__ == "__main__":
    main()
