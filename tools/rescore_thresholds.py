"""Re-score finished descents at several miss thresholds, in two position frames.

No simulation is run. Reads summary.csv plus each descent's telemetry CSV (last row).

Frames (target is the origin in both):
  absolute     - true position at contact, |(x, z)|; identical to the recorded target_miss_m
  map-relative - contact point expressed in the onboard map's frame, |(x, z) - s|, where s is
                 the map_shift offset (0 for other conditions). The prior is DEM(x + s) and the
                 truth is DEM(x), so a feature at true position q sits at q - s in the map.
                 This is the Mars-2020 convention: the target is chosen in the map.
                 (An earlier draft used the filter's own estimate; that is wrong because the
                 estimate frame also contains the injected start error.)
Velocity limits stay fixed (vz < 2 m/s, vh < 1 m/s) and contact is required.

Usage: python tools/rescore_thresholds.py <run_folder> [<run_folder> ...]
Writes <run_folder>/rescored_per_run.csv and rescored_by_condition.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

THRESHOLDS = (10, 50, 100)
# map_shift offsets (east, north) by variant; identical in ScanUtilityRunner.cs and
# ScanUtilityTransferRunner.cs (sx / sz expressions).
MAP_SHIFT = {0: (30, -20), 1: (-25, 35), 2: (-28, 36), 3: (22, -31)}
VZ_LIMIT, VH_LIMIT = 2.0, 1.0


def last_row_positions(folder, ids):
    rows = []
    for run_id in ids:
        path = folder / f"{run_id}.csv"
        if not path.exists():
            rows.append((np.nan,) * 2)
            continue
        last = pd.read_csv(path).iloc[-1]
        rows.append((last.x, last.z))
    return pd.DataFrame(rows, columns=["x", "z"])


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def rescore(folder):
    folder = Path(folder)
    r = pd.read_csv(folder / "summary.csv")
    r = r[r.kind == "descent"].reset_index(drop=True)
    pos = last_row_positions(folder, r.id)
    missing = int(pos.x.isna().sum())
    if missing:
        raise SystemExit(f"{folder}: {missing} descents lack telemetry; refusing to score partially")
    r["abs_miss_check"] = np.hypot(pos.x, pos.z)
    shift = np.array([MAP_SHIFT[int(v)] if c == "map_shift" else (0, 0) for v, c in zip(r.variant, r.condition)])
    r["map_shift_m"] = np.hypot(shift[:, 0], shift[:, 1])
    r["map_rel_miss"] = np.hypot(pos.x - shift[:, 0], pos.z - shift[:, 1])
    # Sanity: recomputed absolute miss must equal the recorded one (contact rows only).
    contact = r.touchdown.astype(bool)
    drift = (r.abs_miss_check - r.target_miss_m)[contact].abs().max()
    if drift > 0.05:
        raise SystemExit(f"{folder}: recomputed miss differs from target_miss_m by {drift:.3f} m")
    speed_ok = contact & (r.impact_vz < VZ_LIMIT) & (r.impact_vh < VH_LIMIT)
    for t in THRESHOLDS:
        r[f"abs_ok_{t}"] = speed_ok & (r.target_miss_m < t)
        r[f"rel_ok_{t}"] = speed_ok & (r.map_rel_miss < t)
    r.to_csv(folder / "rescored_per_run.csv", index=False)

    out = []
    for (cond, arm), g in r.groupby(["condition", "arm"], sort=False):
        row = dict(condition=cond, arm=arm, n=len(g), speed_ok=int(((g.impact_vz < VZ_LIMIT) & (g.impact_vh < VH_LIMIT) & g.touchdown.astype(bool)).sum()),
                   mean_abs_miss=g.target_miss_m.mean(), mean_map_rel_miss=g.map_rel_miss.mean())
        for t in THRESHOLDS:
            for frame in ("abs", "rel"):
                k = int(g[f"{frame}_ok_{t}"].sum())
                lo, hi = wilson(k, len(g))
                row[f"{frame}_{t}m"] = k
                row[f"{frame}_{t}m_ci"] = f"{lo:.2f}-{hi:.2f}"
        out.append(row)
    table = pd.DataFrame(out)
    table.to_csv(folder / "rescored_by_condition.csv", index=False)
    return r, table


if __name__ == "__main__":
    for f in sys.argv[1:]:
        _, table = rescore(f)
        cols = ["condition", "arm", "n", "speed_ok", "mean_abs_miss", "mean_map_rel_miss"] + [
            f"{fr}_{t}m" for fr in ("abs", "rel") for t in THRESHOLDS]
        print(f"\n== {f}")
        print(table[cols].round(2).to_string(index=False))
