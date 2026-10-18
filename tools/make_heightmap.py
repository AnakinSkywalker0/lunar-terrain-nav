"""Convert PGDA Site04 5 m/px GeoTIFF to a Unity 16-bit RAW heightmap (2049x2049) + metadata.

Usage: python tools/make_heightmap.py data/Site04_final_adj_5mpp_surf.tif LANTERN/Assets/Terrain
"""
import sys, os, json
import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
N = 2049
z = np.array(Image.open(src), dtype=np.float64)
bad = (z < -1e5) | (z > 1e5)
z[bad] = np.nan
zmin, zmax = float(np.nanmin(z)), float(np.nanmax(z))
z = np.where(np.isnan(z), zmin, z)
im = Image.fromarray(z.astype(np.float32), mode="F").resize((N, N), Image.BILINEAR)
h = np.asarray(im, dtype=np.float64)
u16 = np.round((h - zmin) / (zmax - zmin) * 65535).astype("<u2")
u16 = u16[::-1]  # Unity terrain row 0 is south; GeoTIFF row 0 is north
os.makedirs(out, exist_ok=True)
u16.tofile(os.path.join(out, "site04_height.raw"))
side = z.shape[1] * 5.0
meta = dict(resolution=N, side_m=side, min_m=zmin, max_m=zmax, bad_px=int(bad.sum()))
json.dump(meta, open(os.path.join(out, "site04_height.json"), "w"), indent=1)
print(meta)
