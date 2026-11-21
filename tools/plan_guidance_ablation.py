"""Choose extra Site01 terrain areas for the guidance ablation (deterministic).

Reuses the Site01 height raster and the three transfer areas. Extra areas are picked the way
the transfer areas were described: flat target window (max slope <= 5 deg), 2400 m scan window
inside the tile, areas at least 2400 m apart (non-overlapping scan windows). The slope window radius is calibrated so the
three transfer areas reproduce their recorded slopes.

Writes LANTERN/Assets/Experiments/GuidanceAblation/plan.json.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "LANTERN/Assets/Experiments/ScanUtilityTransfer"
OUT = ROOT / "LANTERN/Assets/Experiments/GuidanceAblation"
SEED = 20261104
N_EXTRA = 9
MIN_SPACING = 2400.0  # scan windows must not overlap
MAX_SLOPE = 5.0


def main():
    meta = json.loads((SRC / "site01_height.json").read_text())
    n, side = meta["resolution"], meta["side_m"]
    raw = np.fromfile(SRC / "site01_height.raw", dtype="<u2").reshape(n, n)
    h = meta["min_m"] + raw.astype(np.float64) / 65535.0 * (meta["max_m"] - meta["min_m"])
    step = side / (n - 1)
    gz, gx = np.gradient(h, step)
    slope = np.degrees(np.arctan(np.hypot(gx, gz)))

    plan = json.loads((SRC / "plan.json").read_text())
    originals = plan["evaluation_sites"]

    def window_max(x, z, radius):
        i, j, r = int(round(x / step)), int(round(z / step)), int(round(radius / step))
        return float(slope[j - r:j + r + 1, i - r:i + r + 1].max())

    best = min(range(25, 401, 25), key=lambda r: sum(
        abs(window_max(s["x"], s["z"], r) - s["target_window_max_slope_deg"]) for s in originals))
    err = [round(window_max(s["x"], s["z"], best) - s["target_window_max_slope_deg"], 2) for s in originals]
    print("calibrated slope window radius (m):", best, "recorded-vs-recomputed slope diffs:", err)

    grid = [(x, z) for x in np.arange(1500, 14600, 400.0) for z in np.arange(1500, 14600, 400.0)]
    chosen = []
    for attempt in range(200):  # greedy packing; retry with a new deterministic shuffle until enough fit
        rng = np.random.default_rng(SEED + attempt)
        chosen = []
        for k in rng.permutation(len(grid)):
            x, z = grid[k]
            if window_max(x, z, best) > MAX_SLOPE:
                continue
            if any(np.hypot(x - s["x"], z - s["z"]) < MIN_SPACING for s in originals + chosen):
                continue
            chosen.append({"id": f"site01_wide{len(chosen) + 1:02d}", "x": float(x), "z": float(z),
                           "target_window_max_slope_deg": window_max(x, z, best)})
            if len(chosen) == N_EXTRA:
                break
        if len(chosen) == N_EXTRA:
            print("packing attempt", attempt)
            break
    assert len(chosen) == N_EXTRA, f"only {len(chosen)} areas found"

    out = {
        "dataset": "Site01", "slope_window_radius_m": best, "seed": SEED,
        "smoke_sites": plan["smoke_sites"], "evaluation_sites": originals, "wide_sites": chosen,
        "evaluation_errors": plan["evaluation_errors"],
        "source_sha256": meta["source_sha256"],
        "raw_sha256": hashlib.sha256((SRC / "site01_height.raw").read_bytes()).hexdigest(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plan.json").write_text(json.dumps(out, indent=2) + "\n")
    for s in chosen:
        print(s)


if __name__ == "__main__":
    main()
