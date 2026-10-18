"""Render PGDA LOLA 5 m/px GeoTIFFs: elevation, slope, low-Sun shadow and a cross-section profile.

Usage: python tools/render_site.py data/Site04_final_adj_5mpp_surf.tif data/Site04_final_adj_5mpp_slp.tif out_dir
"""
import sys, os
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

PX = 5.0  # metres per pixel


def load(path):
    a = np.array(Image.open(path), dtype=np.float64)
    a[(a < -1e5) | (a > 1e5)] = np.nan
    return a


def shadow_mask(z, sun_el_deg, sun_az_deg, px, step=1.0):
    """Cast shadows on a DEM: a pixel is dark if terrain toward the Sun rises above the Sun ray.

    Returns (shadow, unknown). unknown marks lit pixels whose Sun ray leaves the tile while still
    below the tile's highest point, so terrain outside the tile could be shading them.
    """
    h, w = z.shape
    tan_el = np.tan(np.radians(sun_el_deg))
    az = np.radians(sun_az_deg)
    dx, dy = np.sin(az), -np.cos(az)  # image x right, y down; azimuth clockwise from up
    zf = np.nan_to_num(z, nan=np.nanmin(z))
    zmax = zf.max()
    unknown = np.zeros_like(zf, dtype=bool)
    shadow = np.zeros_like(zf, dtype=bool)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    max_steps = int(np.hypot(h, w))
    for k in range(1, max_steps, int(step)):
        sx = np.rint(xx + dx * k).astype(int)
        sy = np.rint(yy + dy * k).astype(int)
        ok = (sx >= 0) & (sx < w) & (sy >= 0) & (sy < h)
        if not ok.any():
            break
        ray = zf + tan_el * k * px
        blocker = np.full_like(zf, -np.inf)
        blocker[ok] = zf[sy[ok], sx[ok]]
        shadow |= blocker > ray
        unknown |= ~ok & (ray < zmax)
        # early exit: once the ray is above the tallest peak everywhere it cannot be blocked
        if ray.min() > zmax:
            break
    return shadow, unknown & ~shadow


def main(surf, slp, out):
    os.makedirs(out, exist_ok=True)
    z = load(surf)
    try:
        s = load(slp)
    except OSError:
        # slope file missing or truncated: derive slope from the DEM
        gy, gx = np.gradient(z, PX)
        s = np.degrees(np.arctan(np.hypot(gx, gy)))
        print("slope computed from DEM")
    # downsample for the overview (full tile is large); 4x -> 20 m/px
    f = 4
    zs = z[::f, ::f]
    ss = s[::f, ::f]
    h, w = zs.shape
    ext_km = [0, w * PX * f / 1000, h * PX * f / 1000, 0]
    print("tile", z.shape, "km", z.shape[1] * PX / 1000, "x", z.shape[0] * PX / 1000,
          "elev m", np.nanmin(z), np.nanmax(z), "slope deg max", np.nanmax(s))

    ls = LightSource(azdeg=315, altdeg=35)
    fig, ax = plt.subplots(1, 2, figsize=(15, 7))
    rgb = ls.shade(np.nan_to_num(zs, nan=np.nanmin(zs)), cmap=plt.cm.gist_earth, vert_exag=2,
                   blend_mode="overlay", dx=PX * f, dy=PX * f)
    ax[0].imshow(rgb, extent=ext_km)
    sm = plt.cm.ScalarMappable(cmap=plt.cm.gist_earth,
                               norm=plt.Normalize(np.nanmin(zs) / 1000, np.nanmax(zs) / 1000))
    fig.colorbar(sm, ax=ax[0], label="Elevation (km)", shrink=0.8)
    ax[0].set_title("Elevation (shaded relief)")
    im = ax[1].imshow(ss, cmap="magma", vmin=0, vmax=40, extent=ext_km)
    fig.colorbar(im, ax=ax[1], label="Slope (degrees)", shrink=0.8)
    ax[1].contour(np.linspace(0, ext_km[1], w), np.linspace(0, ext_km[2], h), ss, levels=[10],
                  colors="cyan", linewidths=0.4)
    ax[1].set_title("Slope (cyan line = 10 deg, Nova-C landing limit)")
    for a in ax:
        a.set_xlabel("km"); a.set_ylabel("km")
    fig.suptitle("NASA PGDA Site04 - Shackleton crater rim, LOLA 5 m/pixel", fontsize=14)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "01_elevation_slope.png"), dpi=110)
    plt.close(fig)

    # low-Sun shadow at 2 deg, on a 10 m/px version for speed
    g = 2
    zg = z[::g, ::g]
    sh, unk = shadow_mask(zg, sun_el_deg=2.0, sun_az_deg=135, px=PX * g, step=1)
    np.savez_compressed(os.path.join(out, "shadow_sun2deg_10m.npz"), shadow=sh, unknown=unk)
    frac = np.mean(sh[np.isfinite(zg)])
    ufrac = np.mean(unk[np.isfinite(zg)])
    print("shadow fraction at 2 deg", frac)
    fig, ax = plt.subplots(figsize=(8, 7.5))
    shade = LightSource(azdeg=135, altdeg=2).hillshade(np.nan_to_num(zg, nan=np.nanmin(zg)),
                                                     vert_exag=1, dx=PX * g, dy=PX * g)
    gray = np.where(sh, 0.0, 0.25 + 0.75 * shade)
    rgb = np.dstack([gray, gray, gray])
    rgb[unk] = 0.6 * rgb[unk] + 0.4 * np.array([0.85, 0.35, 0.1])
    ax.imshow(rgb, extent=[0, zg.shape[1] * PX * g / 1000, zg.shape[0] * PX * g / 1000, 0])
    ax.set_title("What a camera sees: Sun 2 deg above horizon, from the south-east\n"
                 f"black = cast shadow ({frac*100:.0f}%), orange = unknown, Sun ray leaves the tile ({ufrac*100:.0f}%)")
    ax.set_xlabel("km"); ax.set_ylabel("km")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "02_low_sun_shadow.png"), dpi=110)
    plt.close(fig)

    # cross-section: the row with the largest height range (crosses the rim)
    r = int(np.nanargmax(np.nanmax(z, axis=1) - np.nanmin(z, axis=1)))
    prof = z[r, :]
    xkm = np.arange(prof.size) * PX / 1000
    drop = np.nanmax(prof) - np.nanmin(prof)
    fig, ax = plt.subplots(figsize=(13, 4.2))
    ax.fill_between(xkm, np.nanmin(prof) - 200, prof, color="#8a8172")
    ax.plot(xkm, prof, color="black", lw=0.8)
    ax.set_xlabel("Distance along track (km)"); ax.set_ylabel("Elevation (m)")
    ax.set_title(f"A lander's-eye cross-section (row {r}): {drop/1000:.1f} km height change across the tile")
    ax.set_xlim(xkm[0], xkm[-1])
    fig.tight_layout()
    fig.savefig(os.path.join(out, "03_cross_section.png"), dpi=110)
    plt.close(fig)
    print("profile row", r, "drop m", drop)


if __name__ == "__main__":
    main(*sys.argv[1:4])
