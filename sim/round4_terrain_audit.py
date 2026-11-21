"""Round-4 audit (descriptive only): what is unusual about procedural world 12, and does the multi-beam terrain variance (taken at nadir)
differ from the terrain spread where the canted beams actually land?   output: out/round4/terrain_stats.csv, out/round4/footprint_audit.csv
  python sim/round4_terrain_audit.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import pipeline as P  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "round4")
WORLDS = [("proc", s) for s in (11, 12, 13, 14, 15, 16)] + [("site01", P.SUN_EL, P.SUN_AZ)]
AGLS = (3000.0, 1000.0, 300.0)
TAN = np.tan(np.deg2rad(engine.BEAM_CANT_DEG))


def main():
    os.makedirs(OUT, exist_ok=True)
    stat_rows, foot_rows = [], []
    for wk in WORLDS:
        w, tr = P.get_world(wk)
        sx, sy = tr["start"]
        tx, ty = tr["target"]
        f = np.linspace(0.0, 1.0, 200)
        x, y = sx + f * (tx - sx), sy + f * (ty - sy)
        h = w.truth.height(x, y)
        e = 10.0
        gx = (w.truth.height(x + e, y) - w.truth.height(x - e, y)) / (2 * e)
        gy = (w.truth.height(x, y + e) - w.truth.height(x, y - e)) / (2 * e)
        slope = np.degrees(np.arctan(np.hypot(gx, gy)))
        stat_rows.append(dict(world=str(wk[:2]), track_len_m=float(np.hypot(tx - sx, ty - sy)), height_range_m=float(h.max() - h.min()),
                              height_std_m=float(h.std()), slope_median_deg=float(np.median(slope)), slope_p95_deg=float(np.percentile(slope, 95)),
                              frac_track_slope_gt15=float((slope > 15).mean()), map_sigma_m=float(w.map_sigma)))
        rad = 200.0
        nad = w.stats.hstd(x, y, np.full_like(x, rad)) ** 2
        for agl in AGLS:
            off = agl * TAN
            fp = np.mean([w.stats.hstd(x + off * np.cos(a), y + off * np.sin(a), np.full_like(x, rad)) ** 2 for a in (0.0, 2 * np.pi / 3, 4 * np.pi / 3)], axis=0)
            foot_rows.append(dict(world=str(wk[:2]), agl_m=agl, footprint_offset_m=off, nadir_var_median=float(np.median(nad)),
                                  footprint_var_median=float(np.median(fp)), ratio_of_medians=float(np.median(fp) / max(np.median(nad), 1e-9)),
                                  frac_track_footprint_var_gt_2x_nadir=float((fp > 2 * nad).mean())))
    pd.DataFrame(stat_rows).to_csv(os.path.join(OUT, "terrain_stats.csv"), index=False)
    pd.DataFrame(foot_rows).to_csv(os.path.join(OUT, "footprint_audit.csv"), index=False)
    print(pd.DataFrame(stat_rows).round(2).to_string(index=False))
    print(pd.DataFrame(foot_rows).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
