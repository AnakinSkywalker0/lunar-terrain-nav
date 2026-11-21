"""Prepare versioned Site01 crops and a correlated vertical-error *proxy*, not PGDA clones.

Run once before development. Existing output is never overwritten. Raster samples
are pixel-centred; Unity's +z is north, hence the vertical flip of TIFF rows.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates, maximum_filter

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "LANTERN/Assets/Experiments/NavigationV3"
SPAN = 2400.0


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_raster(path):
    with Image.open(path) as image:
        array = np.asarray(image, dtype=np.float32)[::-1].copy()
        geo = {str(k): list(image.tag_v2[k]) for k in (33550, 33922)}
    if array.shape != (3200, 3200) or not np.isfinite(array).all():
        raise ValueError(f"Invalid raster: {path}")
    if geo["33550"][:2] != [5.0, 5.0]:
        raise ValueError("Expected 5 m pixels")
    return array, geo


def sample(array, x, z, n):
    offsets = np.linspace(-SPAN / 2, SPAN / 2, n)
    xx, zz = np.meshgrid(x + offsets, z + offsets)
    return map_coordinates(array, [(zz - 2.5) / 5, (xx - 2.5) / 5], order=1, mode="nearest")


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if DEST.exists():
        raise FileExistsError(f"Refusing to replace frozen inputs: {DEST}")
    surface = ROOT / "data/Site01_final_adj_5mpp_surf.tif"
    errors = ROOT / "data/Site01_final_adj_5mpp_toterr.tif"
    heights, geo = read_raster(surface)
    sigma, error_geo = read_raster(errors)
    if error_geo != geo or np.any(sigma < 0) or np.max(np.abs(heights)) > 1e5:
        raise ValueError("Surface/error rasters are not compatible")
    old = json.loads((ROOT / "LANTERN/Assets/Experiments/ScanUtilityTransfer/plan.json").read_text())
    excluded = [(s["x"], s["z"]) for s in old["smoke_sites"] + old["evaluation_sites"]]
    dz, dx = np.gradient(heights, 5.0)
    slope = maximum_filter(np.degrees(np.arctan(np.hypot(dx, dz))), size=19)
    # Select only on terrain and previous exposure; no navigation outcomes.
    jj, ii = np.where(slope[::8, ::8] < 5)
    candidates = np.column_stack((ii * 40 + 2.5, jj * 40 + 2.5))
    candidates = candidates[(candidates.min(axis=1) > 1500) & (candidates.max(axis=1) < 14500)]
    sites = [dict(id="development", x=excluded[0][0], z=excluded[0][1], split="development")]
    occupied = list(excluded)
    for k in range(3):
        distance = np.abs(candidates[:, None, :] - np.asarray(occupied)[None, :, :])
        eligible = (distance.max(axis=2) > SPAN + 50).all(axis=1)
        scores = np.where(eligible, (distance ** 2).sum(axis=2).min(axis=1), -1)
        index = int(np.argmax(scores))
        if scores[index] < 0:
            raise ValueError("Not enough unexposed, separate crops")
        x, z = candidates[index]
        sites.append(dict(id=f"reserved_{k+1:02d}", x=float(x), z=float(z), split="reserved"))
        occupied.append((x, z))
    DEST.mkdir(parents=True)
    for k, site in enumerate(sites):
        x, z = site["x"], site["z"]
        centre = float(map_coordinates(heights, [[(z-2.5)/5], [(x-2.5)/5]], order=1)[0])
        prior = sample(heights, x, z, 301) - centre
        ground = sample(heights, x, z, 513) - centre
        ground_sigma = sample(sigma, x, z, 513)
        rng = np.random.default_rng(41000 + k)
        field = gaussian_filter(rng.normal(size=(513, 513)), sigma=50 / (SPAN / 512), mode="reflect")
        field = (field - field.mean()) / field.std()
        delta = field * ground_sigma
        ground += delta
        prior_sigma = sample(sigma, x, z, 301)
        path = DEST / f"{site['id']}.bytes"
        with path.open("xb") as stream:
            stream.write(struct.pack("<iif", 513, 301, SPAN))
            for array in (ground, prior, prior_sigma):
                stream.write(np.asarray(array, dtype="<f4").tobytes())
        site.update(file=path.name, sha256=sha(path),
                    vertical_error_rms_m=float(np.sqrt(np.mean(delta ** 2))),
                    sigma_median_m=float(np.median(ground_sigma)),
                    centre_elevation_m=centre)
    manifest = dict(version=3, sites=sites, source="NASA PGDA product 78 Site01",
                    raster_sha256={surface.name: sha(surface), errors.name: sha(errors)}, georeference=geo,
                    error_model="Synthetic Gaussian-smoothed field multiplied by local toterr. NOT a PGDA clone or independent lunar truth.",
                    assumed_smoothing_sigma_m=50, ground_spacing_m=SPAN/512, prior_spacing_m=SPAN/300,
                    prior_project_exposure="Site01 used previously; reserved crops exclude all four archived scan-utility transfer crops.",
                    development_seeds=[1201], reserved_seeds=[2201,2202,2203],
                    conditions=["nominal", "range_spike", "range_dropout", "scan_dropout", "gross_map_shift", "gross_relief"],
                    arms=["classical_pd", "classical_terminal", "ml_terminal"])
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
