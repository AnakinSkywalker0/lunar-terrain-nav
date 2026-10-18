"""Terrain, onboard map, lighting and region statistics for the sensor-trust test bench.

Coordinates: x = column * px (east), y = row * px (image rows). Heights in metres.
"""
import hashlib
import os
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import (gaussian_filter, maximum_filter, minimum_filter, uniform_filter, zoom)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from render_site import shadow_mask  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


class Grid:
    """Raster with bilinear sampling."""

    def __init__(self, z, px):
        self.z = np.ascontiguousarray(z, dtype=np.float32)
        self.px = float(px)
        self.h, self.w = self.z.shape

    @property
    def size_m(self):
        return self.w * self.px

    def height(self, x, y):
        fx = np.clip(np.asarray(x) / self.px, 0, self.w - 1.001)
        fy = np.clip(np.asarray(y) / self.px, 0, self.h - 1.001)
        ix = fx.astype(np.int32)
        iy = fy.astype(np.int32)
        ax = fx - ix
        ay = fy - iy
        z = self.z
        return ((z[iy, ix] * (1 - ax) + z[iy, ix + 1] * ax) * (1 - ay) +
                (z[iy + 1, ix] * (1 - ax) + z[iy + 1, ix + 1] * ax) * ay)

    def grad(self, x, y, step=None):
        s = step or self.px
        gx = (self.height(x + s, y) - self.height(x - s, y)) / (2 * s)
        gy = (self.height(x, y + s) - self.height(x, y - s)) / (2 * s)
        return gx, gy

    def slope_deg(self, x, y, step=None):
        gx, gy = self.grad(x, y, step)
        return np.degrees(np.arctan(np.hypot(gx, gy)))

    def inside(self, x, y, margin=0.0):
        return (x >= margin) & (y >= margin) & (x <= self.size_m - margin) & (y <= self.size_m - margin)


LEVELS_M = np.array([60., 120., 240., 480., 960., 1920., 3840.])


class RegionStats:
    """Min / max / std of heights and lit fraction inside discs of several radii, from coarse rasters."""

    def __init__(self, grid, coarse_px=20.0, shadow=None):
        f = max(1, int(round(coarse_px / grid.px)))
        zc = grid.z[::f, ::f]
        self.px = grid.px * f
        self.h, self.w = zc.shape
        self.mn, self.mx, self.sd, self.lit = [], [], [], []
        for r in LEVELS_M:
            k = int(2 * r / self.px) | 1
            k = max(k, 3)
            self.mn.append(minimum_filter(zc, size=k, mode="nearest"))
            self.mx.append(maximum_filter(zc, size=k, mode="nearest"))
            m1 = uniform_filter(zc.astype(np.float64), size=k, mode="nearest")
            m2 = uniform_filter(zc.astype(np.float64) ** 2, size=k, mode="nearest")
            self.sd.append(np.sqrt(np.maximum(m2 - m1 * m1, 0)).astype(np.float32))
        if shadow is not None:
            sc = shadow[::f, ::f] if shadow.shape == grid.z.shape else shadow
            litf = (~sc).astype(np.float64)
            for r in LEVELS_M:
                k = max(int(2 * r / self.px) | 1, 3)
                self.lit.append(uniform_filter(litf, size=k, mode="nearest").astype(np.float32))

    def _level(self, radius):
        return np.clip(np.searchsorted(LEVELS_M, radius), 0, len(LEVELS_M) - 1)

    def _lookup(self, stack, x, y, radius):
        ix = np.clip((np.asarray(x) / self.px).astype(np.int32), 0, self.w - 1)
        iy = np.clip((np.asarray(y) / self.px).astype(np.int32), 0, self.h - 1)
        lev = self._level(radius)
        out = np.empty(np.broadcast(ix, iy, lev).shape, dtype=np.float32)
        lev = np.broadcast_to(lev, out.shape)
        ixb, iyb = np.broadcast_to(ix, out.shape), np.broadcast_to(iy, out.shape)
        for k in np.unique(lev):
            m = lev == k
            out[m] = stack[k][iyb[m], ixb[m]]
        return out

    def hmin(self, x, y, r): return self._lookup(self.mn, x, y, r)
    def hmax(self, x, y, r): return self._lookup(self.mx, x, y, r)
    def hstd(self, x, y, r): return self._lookup(self.sd, x, y, r)
    def litfrac(self, x, y, r): return self._lookup(self.lit, x, y, r)


def load_site04(px=10.0):
    z = np.array(Image.open(os.path.join(ROOT, "data", "Site04_final_adj_5mpp_surf.tif")), dtype=np.float32)
    f = int(round(px / 5.0))
    return z[::f, ::f]


def procedural_world(seed, n=1600, px=10.0):
    """Crater world: a large crater with a rim cliff and a flat floor, small craters and roughness."""
    rng = np.random.default_rng(seed)
    size = n * px
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) * px
    cx = size * (0.5 + rng.uniform(-0.12, 0.12))
    cy = size * (0.5 + rng.uniform(-0.12, 0.12))
    R = rng.uniform(5200, 7000)
    D = rng.uniform(2200, 4500)
    r = np.hypot(xx - cx, yy - cy)
    u = np.clip((r - 0.40 * R) / (0.60 * R), 0, 1)
    wall = u * u * (3 - 2 * u)
    z = -D * (1 - wall)
    z += 0.07 * D * np.exp(-((r - R) / (0.35 * R)) ** 2) * (r > 0.7 * R)
    z += 0.07 * D * (R / np.maximum(r, R)) ** 3 * (r > R)
    # small craters
    for _ in range(140):
        rr = rng.uniform(60, 700)
        x0, y0 = rng.uniform(0, size, 2)
        d = np.hypot(xx - x0, yy - y0)
        z -= 0.12 * rr * np.clip(1 - (d / rr) ** 2, 0, None) * (d < rr)
    # fractal roughness
    noise = np.zeros_like(z)
    for s, a in [(80, 18.), (30, 8.), (10, 3.), (3, 1.2)]:
        noise += a * gaussian_filter(rng.standard_normal((n, n)).astype(np.float32), s) * s ** 0.5 / 2.5
    z += noise
    z += rng.uniform(-300, 300) + 0.0
    return z.astype(np.float32)


def unmapped_features(shape, px, seed):
    """Small craters and roughness that the onboard map does not contain (fair-testing rule 1)."""
    rng = np.random.default_rng(seed + 9000)
    h, w = shape
    f = np.zeros(shape, dtype=np.float32)
    ys = rng.integers(0, h, 2500)
    xs = rng.integers(0, w, 2500)
    rad = rng.uniform(15, 120, 2500) / px
    for x0, y0, r in zip(xs, ys, rad):
        r_i = int(np.ceil(r))
        x1, x2, y1, y2 = max(0, x0 - r_i), min(w, x0 + r_i + 1), max(0, y0 - r_i), min(h, y0 + r_i + 1)
        yy, xx = np.mgrid[y1:y2, x1:x2]
        d = np.hypot(xx - x0, yy - y0)
        f[y1:y2, x1:x2] -= (0.15 * r * px * np.clip(1 - (d / r) ** 2, 0, None)).astype(np.float32)
    f += 0.8 * rng.standard_normal(shape).astype(np.float32)
    return f


def map_error_field(shape, px, seed, sigma_m=3.0, corr_m=150.0):
    rng = np.random.default_rng(seed + 4000)
    e = gaussian_filter(rng.standard_normal(shape).astype(np.float32), corr_m / px)
    e *= sigma_m / max(e.std(), 1e-6)
    return e


class World:
    """Truth surface, onboard map, coarse reference, shadow and statistics for one site."""

    def __init__(self, dem, px=10.0, seed=0, sun_el=2.0, sun_az=135.0, n_map_banks=4, name="site"):
        self.name = name
        self.px = px
        self.seed = seed
        self.truth_dem = dem
        self.truth = Grid(dem + unmapped_features(dem.shape, px, seed), px)
        self.map_banks = [Grid(dem + map_error_field(dem.shape, px, seed + k), px) for k in range(n_map_banks)]
        self.dem_grid = Grid(dem, px)
        # Coarse reference (global-topography style): what a mission without a LOLA-resolution DEM would use.
        c = 8
        coarse = gaussian_filter(dem[::c, ::c], 4000.0 / (px * c), mode="nearest")
        self.coarse_ref = Grid(coarse, px * c)
        # Lighting from the truth surface and from the onboard map (slightly different Sun elevation: ephemeris error).
        self.sun_el, self.sun_az = sun_el, sun_az
        self.stats = RegionStats(self.map_banks[0], 20.0, self._shadow(self.map_banks[0].z, sun_el + 0.1, sun_az))
        self.true_shadow = self._shadow(self.truth.z, sun_el, sun_az)
        self.true_lit = RegionStats(self.truth, 20.0, self.true_shadow)

    def _shadow(self, z, el, az):
        f = max(1, int(round(20.0 / self.px)))
        key = f"{self.name}_s{self.seed}_{hashlib.md5(z[::97, ::97].tobytes()).hexdigest()[:10]}_el{el:.2f}_az{az:.0f}.npy"
        path = os.path.join(ROOT, "out", "cache", key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            return np.load(path)
        sh, _unk = shadow_mask(z[::f, ::f], sun_el_deg=el, sun_az_deg=az, px=self.px * f, step=1)
        np.save(path, sh)
        return sh


def track_for(world, seed=0, start_agl=15000.0):
    """Planned track: from a start 15 km above the high ground, ~10 km across the rim cliff to a flat floor target."""
    from scipy.ndimage import maximum_filter as mxf
    z = world.dem_grid.z
    px = world.px
    gy, gx = np.gradient(z, px)
    sl = np.degrees(np.arctan(np.hypot(gx, gy)))
    flat = mxf(sl, size=7) < 5.0
    size = z.shape[0] * px
    # target: lowest flat area that is at least 10 km from the highest ground, away from the tile edge
    ys, xs = np.nonzero(flat)
    el = z[ys, xs]
    ok = (xs * px > 600) & (xs * px < size - 600) & (ys * px > 600) & (ys * px < size - 600)
    ys, xs, el = ys[ok], xs[ok], el[ok]
    low = el < np.percentile(el, 12)
    ys, xs, el = ys[low], xs[low], el[low]
    # choose the candidate whose track back toward high ground has the largest drop
    best = None
    rng = np.random.default_rng(world.seed)
    cand = rng.choice(len(el), size=min(400, len(el)), replace=False)
    for i in cand:
        tx, ty = xs[i] * px, ys[i] * px
        for ang in np.linspace(0, 2 * np.pi, 24, endpoint=False):
            L = 10000.0
            sx, sy = tx + L * np.cos(ang), ty + L * np.sin(ang)
            if not (600 < sx < size - 600 and 600 < sy < size - 600):
                continue
            t = np.linspace(0, 1, 60)
            prof = world.dem_grid.height(sx + (tx - sx) * t, sy + (ty - sy) * t)
            drop = prof.max() - prof[-1]
            if best is None or drop > best[0]:
                best = (drop, sx, sy, tx, ty)
    _, sx, sy, tx, ty = best
    return dict(start=(sx, sy), target=(tx, ty), start_agl=start_agl)


def site04_world(seed=0, sun_el=2.0, sun_az=135.0):
    return World(load_site04(), 10.0, seed, sun_el, sun_az, name="Site04")


def procedural(seed, sun_el=2.0, sun_az=135.0):
    return World(procedural_world(seed), 10.0, seed, sun_el, sun_az, name=f"proc{seed}")
