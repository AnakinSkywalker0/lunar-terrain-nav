"""Freeze terrain-only Site01 areas and unchanged v2 transfer settings; no training."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import maximum_filter

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'LANTERN/Assets/Experiments/ScanUtilityTransfer'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    if (DEST / 'plan.json').exists():
        raise FileExistsError('Transfer plan already frozen')
    source = ROOT / 'data/Site01_final_adj_5mpp_surf.tif'
    with Image.open(source) as image:
        heights = np.array(image, dtype=np.float32)
        scale = list(image.tag_v2[33550])
        tiepoint = list(image.tag_v2[33922])
    assert heights.shape == (3200, 3200) and scale[:2] == [5., 5.]
    assert np.isfinite(heights).all() and (np.abs(heights) < 1e5).all()
    lo, hi = float(heights.min()), float(heights.max())
    resized = np.asarray(Image.fromarray(heights).resize((2049, 2049), Image.Resampling.BILINEAR), dtype=np.float64)
    raw = np.round((resized-lo)/(hi-lo)*65535).astype('<u2')[::-1].copy()
    raw.tofile(DEST / 'site01_height.raw')
    meta = dict(resolution=2049, side_m=16000., min_m=lo, max_m=hi,
                source=str(source.relative_to(ROOT)), source_sha256=sha(source),
                pixel_scale=scale, tiepoint=tiepoint, bad_px=0)
    (DEST / 'site01_height.json').write_bytes((json.dumps(meta, indent=2)+'\n').encode())
    grid = raw.astype(float)/65535*(hi-lo)+lo
    spacing = 16000/2048
    gz, gx = np.gradient(grid, spacing)
    slope = maximum_filter(np.rad2deg(np.arctan(np.hypot(gx, gz))), size=7)
    j, i = np.where(slope < 5)
    coordinates = np.column_stack((i*spacing, j*spacing))
    coordinates = coordinates[(coordinates.min(axis=1) >= 1400) & (coordinates.max(axis=1) <= 14600)]
    centres = []
    for k in range(4):
        if not centres:
            ix = int(np.argmin(((coordinates-8000)**2).sum(axis=1)))
        else:
            delta = np.abs(coordinates[:, None, :]-np.array(centres)[None, :, :])
            eligible = (delta.max(axis=2) >= 2400).all(axis=1)
            distances = (delta**2).sum(axis=2).min(axis=1)
            distances[~eligible] = -1
            ix = int(np.argmax(distances))
            assert distances[ix] >= 0, 'Insufficient separate eligible areas'
        centres.append(coordinates[ix].tolist())
    sites = [dict(id=f'site01_transfer{k:02d}', x=x, z=z,
                  target_window_max_slope_deg=float(slope[round(z/spacing), round(x/spacing)]))
             for k, (x, z) in enumerate(centres)]
    old_plan = json.loads((ROOT / 'LANTERN/Assets/Experiments/ScanUtility/plan.json').read_text())
    frozen = ['LANTERN/Assets/Experiments/ScanUtility/model.json',
              'LANTERN/Assets/Experiments/ScanUtility/policy.json',
              'LANTERN/Assets/Experiments/ScanTrust/model.json',
              'LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs',
              'LANTERN/Assets/Scripts/Experiments/ScanUtilityPolicy.cs',
              'LANTERN/Assets/Scripts/Experiments/PortableScanTrust.cs',
              'LANTERN/Assets/Scripts/Experiments/TerrainTouchdownRecorder.cs']
    plan = dict(dataset='Site01', smoke_sites=sites[:1], evaluation_sites=sites[1:],
                evaluation_errors=old_plan['evaluation_errors'], expected_evaluation_cases=810,
                expected_smoke_cases=15, raw_sha256=sha(DEST/'site01_height.raw'),
                source_sha256=sha(source),
                protocol_sha256=sha(ROOT/'docs/SCAN_UTILITY_TRANSFER_PROTOCOL.md'),
                frozen_sha256={p: sha(ROOT/p) for p in frozen},
                baseline_evaluation='out/scan_utility/20261021_204054_eval',
                prior_exposure='Site01 used in older separate sensor studies; excluded from scan-utility fitting/selection')
    (DEST / 'plan.json').write_bytes((json.dumps(plan, indent=2)+'\n').encode())
    print(json.dumps({k: plan[k] for k in ['dataset','smoke_sites','evaluation_sites','expected_evaluation_cases']}, indent=2))


if __name__ == '__main__':
    main()
