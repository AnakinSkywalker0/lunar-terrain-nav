"""Summarise out/round6/dyn6_dev.csv: mean landing success by vehicle variant and rule, and paired per-world differences with a bootstrap interval.
Exploratory (development worlds only).  python sim/round6_analyze.py"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round6")
df = pd.read_csv(os.path.join(OUT, "dyn6_dev.csv"))
df["cell"] = df.world + "|" + df.seed.astype(str)
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
order = ["3-DOF (point mass)", "6-DOF default", "6-DOF sluggish", "6-DOF degraded"]
means = df.groupby(["part", "condition", "config", "variant"]).success_pct.mean().unstack("variant")[order].round(1)
means.to_csv(os.path.join(OUT, "dyn6_means.csv"))
print("Mean landing success (%), mean over development worlds\n", means.to_string())
phys = df[df.variant != order[0]].groupby(["variant"])[["tilt_max_deg", "impact_tilt_deg", "att_err_deg", "rcs_fuel_kg", "crash_pct", "rough_pct", "timeout_pct"]].mean().round(2)
print("\nVehicle behaviour (median per cell, mean over cells)\n", phys.to_string())
loose = df[df.variant != order[0]].assign(gap=lambda d: d.legacy_pct - d.success_pct).groupby("variant").gap.mean().round(2)
print("\nLandings lost only to the touchdown tilt / spin rule (points)\n", loose.to_string())

rng = np.random.default_rng(0)


def paired(part, a, b):
    """mean over worlds of success(a) - success(b), per vehicle variant, with a bootstrap 95 % interval over worlds"""
    rows = []
    for cond in ("cliff", "x8", "x16"):
        for v in order:
            d = df[(df.part == part) & (df.condition == cond) & (df.variant == v)].pivot_table(index="cell", columns="config", values="success_pct")
            if a not in d or b not in d:
                continue
            x = (d[a] - d[b]).to_numpy()
            bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(2000)]
            rows.append(dict(part=part, condition=cond, variant=v, diff=round(x.mean(), 1), lo=round(np.percentile(bs, 2.5), 1), hi=round(np.percentile(bs, 97.5), 1)))
    return pd.DataFrame(rows)


res = pd.concat([paired("single", "A: tolerance + noise floor", "baseline: PITFAL-style"),
                 paired("single", "B2 Student-t (4 dof) + floor", "baseline: PITFAL-style"),
                 paired("multi", "A: floor both + footprint terrain", "baseline: PITFAL-style multi-beam"),
                 paired("multi", "B2 Student-t (4 dof) + floor", "baseline: PITFAL-style multi-beam"),
                 paired("multi", "B2 Student-t (4 dof) + floor", "A: floor both + footprint terrain")],
                keys=["single: floor A - PITFAL-style", "single: Student-t - PITFAL-style", "multi: floor A - PITFAL-style multi",
                      "multi: Student-t - PITFAL-style multi", "multi: Student-t - floor A"], names=["comparison"]).reset_index(level=0)
res.to_csv(os.path.join(OUT, "dyn6_paired.csv"), index=False)
print("\nPaired differences in points (bootstrap 95 % over worlds)\n", res.drop(columns="part").to_string(index=False))
