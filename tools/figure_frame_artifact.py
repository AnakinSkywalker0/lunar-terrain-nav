"""Figure + table: the same landings scored in the true frame vs the map frame (existing runs only).

Needs rescored_per_run.csv, produced by tools/rescore_thresholds.py. Unit of analysis is the area, so the
transfer set (3 areas) is shown per area; the Site04 eval set is a single area.
Usage: python tools/figure_frame_artifact.py <out_dir> <rescored_folder> [<rescored_folder> ...]
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main(out_dir, folders):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    frames = [pd.read_csv(Path(f) / "rescored_per_run.csv").assign(run=Path(f).name) for f in folders]
    r = pd.concat(frames, ignore_index=True)
    r = r[r.arm.isin(["off", "geometric", "bounded", "utility"])]
    g = r.groupby(["run", "site_id", "condition", "arm"]).agg(
        n=("id", "size"), abs10=("abs_ok_10", "mean"), map10=("rel_ok_10", "mean"),
        abs50=("abs_ok_50", "mean"), map50=("rel_ok_50", "mean")).reset_index()
    g.to_csv(out / "frame_artifact_per_area.csv", index=False)
    pooled = g.groupby(["condition", "arm"]).agg(areas=("site_id", "nunique"), abs10=("abs10", "mean"),
                                                 map10=("map10", "mean"), abs50=("abs50", "mean"), map50=("map50", "mean")).reset_index()
    pooled.to_csv(out / "frame_artifact_by_condition.csv", index=False)
    arms = ["off", "geometric", "bounded", "utility"]
    conds = ["aligned", "map_shift", "relief_positive"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
    w = 0.38
    for ax, c in zip(axes, conds):
        sub = pooled[pooled.condition == c].set_index("arm").reindex(arms)
        ax.bar(np.arange(4) - w / 2, sub.abs10, w, label="true frame (as originally scored)")
        ax.bar(np.arange(4) + w / 2, sub.map10, w, label="map frame (target chosen in the map)")
        ax.set_xticks(range(4)); ax.set_xticklabels(arms, rotation=20); ax.set_title(c)
    axes[0].set_ylabel("success (miss < 10 m, vz < 2, vh < 1)\nmean over areas"); axes[0].legend(fontsize=7)
    fig.suptitle("Same landings, two scoring frames: a map offset cannot be observed from the map")
    fig.tight_layout(); fig.savefig(out / "fig_frame_artifact.png", dpi=130)
    print(pooled.round(3).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
