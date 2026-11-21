"""Analyse the IMU-bias stress stage (eval_imu) next to the bias-free g3 runs.

Question: does the classical Kalman + chi-square gate's advantage survive when the navigation state drifts?
Usage: python tools/analyze_imu_stress.py <out_dir> <imu_run_folder> <g3_run_folder>
Bias is a constant accelerometer bias (m/s^2, random horizontal direction per seed), 0 = the g3 runs.
Gate constants are NOT retuned for bias, so a gate whose process noise is too small is expected to suffer.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_guidance_ablation import load  # noqa: E402

ARMS = ["off", "geometric", "authority", "kf_chi2", "kf_q1", "kf_q10"]
CONDS = ["aligned", "tie8", "relief_positive"]


def main(out_dir, imu_folder, g3_folder):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    imu = load([imu_folder]); g3 = load([g3_folder])
    imu["bias"] = imu.id.str.extract(r"_b([0-9.]+)_")[0].astype(float)
    g3 = g3[g3.arm.isin(["off", "geometric", "authority", "kf_chi2"]) & g3.condition.isin(CONDS)].copy()
    g3["bias"] = 0.0
    r = pd.concat([g3, imu], ignore_index=True)
    pa = r.groupby(["area", "condition", "bias", "arm"]).agg(
        miss=("map_miss", "mean"), violation=("violation", "mean"), ok10=("map_ok_10", "mean"),
        noncontact=("noncontact", "mean")).reset_index()
    pa.to_csv(out / "imu_per_area.csv", index=False)
    t = pa.groupby(["condition", "bias", "arm"]).agg(areas=("area", "nunique"), miss=("miss", "mean"),
                                                    violation=("violation", "mean"), ok10=("ok10", "mean"),
                                                    noncontact=("noncontact", "mean")).reset_index()
    t.to_csv(out / "imu_by_condition_bias_arm.csv", index=False)
    fig, axes = plt.subplots(2, 3, figsize=(15, 7), sharex=True)
    xs = lambda b: np.where(np.asarray(b) == 0, 0.00005, b)  # noqa: E731
    for j, c in enumerate(CONDS):
        for arm in ARMS:
            s = t[(t.condition == c) & (t.arm == arm)].sort_values("bias")
            if s.empty:
                continue
            axes[0, j].plot(xs(s.bias), s.miss, marker="o", label=arm)
            axes[1, j].plot(xs(s.bias), s.ok10, marker="o", label=arm)
        axes[0, j].set_title(c); axes[0, j].set_xscale("log"); axes[0, j].set_yscale("log")
        axes[1, j].set_xlabel("accelerometer bias (m/s^2); leftmost = none")
    axes[0, 0].set_ylabel("mean miss (m, map frame)"); axes[1, 0].set_ylabel("success (miss<10 m, vz<2, vh<1)")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Does the classical gate's advantage survive navigation drift? (12 areas, constants not retuned)")
    fig.tight_layout(); fig.savefig(out / "fig_imu_stress.png", dpi=130)
    pd.set_option("display.width", 220)
    print(t.round(3).to_string(index=False))


if __name__ == "__main__":
    main(*sys.argv[1:4])
