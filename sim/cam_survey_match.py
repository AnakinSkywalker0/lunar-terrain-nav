"""Measure a simple landmark (ZNCC template) matcher on the Unity camera survey.

For each pair: the live image (true Sun, displaced by an unknown navigation error) is matched against the wider
reference image (onboard map, slightly wrong Sun). Sensor noise is added to the live image. Output: the position error
as a function of the lit fraction, saved as an empirical camera model for the simulator (out/camera_survey/cam_model.json).
"""
import json
import os
import numpy as np
from PIL import Image
from scipy.signal import fftconvolve
from scipy.ndimage import uniform_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "camera_survey")
DS = 2
READ_NOISE_DN = 2.0
SHOT_K = 0.6


def load(path):
    a = np.array(Image.open(path).convert("L"), dtype=np.float64)
    h = a.shape[0] // DS
    return a[:h * DS, :h * DS].reshape(h, DS, h, DS).mean(axis=(1, 3))


def zncc(ref, live):
    L = live.shape[0]
    R = ref.shape[0]
    t = live - live.mean()
    tn = np.sqrt((t * t).sum())
    n = L * L
    num = fftconvolve(ref, t[::-1, ::-1], mode="valid")
    s1 = fftconvolve(ref, np.ones((L, L)), mode="valid")
    s2 = fftconvolve(ref * ref, np.ones((L, L)), mode="valid")
    var = np.maximum(s2 - s1 * s1 / n, 1e-9)
    return num / (np.sqrt(var) * max(tn, 1e-9))


def main(seed=7, ref_mode='direct', read_noise=None, tag=''):
    global READ_NOISE_DN
    if read_noise is not None:
        READ_NOISE_DN = read_noise
    rng = np.random.default_rng(seed)
    items = json.load(open(os.path.join(D, "positions.json")))["items"]
    rows = []
    for it in items:
        i = it["id"]
        live = load(os.path.join(D, "img", f"{i}_live.png"))
        ref = load(os.path.join(D, "img", f"{i}_ref.png"))
        if ref_mode == 'direct':
            # onboard prediction = DEM + Sun only (direct light): pixels the Sun cannot reach are predicted flat black
            ref = np.where(ref < 40.0, 20.4, ref)
        live = live + rng.standard_normal(live.shape) * (READ_NOISE_DN + SHOT_K * np.sqrt(np.maximum(live, 0.0)))
        live = np.clip(np.round(live), 0, 255)
        pm = 2 * it["agl"] * np.tan(np.radians(20)) / 512.0 * DS          # metres per downsampled pixel
        c = zncc(ref, live)
        iy, ix = np.unravel_index(np.argmax(c), c.shape)
        peak = c[iy, ix]
        # sub-pixel parabola
        def sub(v, a, b, cc):
            d = a - 2 * b + cc
            return v + (0.5 * (a - cc) / d if abs(d) > 1e-12 else 0.0)
        cx = sub(ix, c[iy, ix - 1] if ix > 0 else peak, peak, c[iy, ix + 1] if ix < c.shape[1] - 1 else peak)
        cy = sub(iy, c[iy - 1, ix] if iy > 0 else peak, peak, c[iy + 1, ix] if iy < c.shape[0] - 1 else peak)
        half = (ref.shape[0] - live.shape[0]) / 2.0
        c0 = half + it["dx"] / pm
        r0 = half - it["dz"] / pm
        ex = (cx - c0) * pm
        ez = -(cy - r0) * pm
        mask = np.ones_like(c, bool)
        mask[max(0, iy - 4):iy + 5, max(0, ix - 4):ix + 5] = False
        second = c[mask].max() if mask.any() else 0.0
        rows.append(dict(id=i, lit=it["lit"], agl=it["agl"], rough=it["rough"], peak=float(peak), psr=float(peak - second),
                         ex=float(ex), ez=float(ez), err=float(np.hypot(ex, ez)), rel=float(np.hypot(ex, ez) / it["agl"])))
    import pandas as pd
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(D, f"results{tag}.csv"), index=False)
    bins = [0, 0.05, 0.25, 0.5, 0.8, 1.01]
    df["bin"] = pd.cut(df.lit, bins, right=False)
    g = df.groupby("bin", observed=True).agg(n=("err", "size"), median_err_m=("err", "median"), p90_err_m=("err", lambda x: np.percentile(x, 90)),
                                              median_rel=("rel", "median"), frac_over_100m=("err", lambda x: (x > 100).mean()),
                                              frac_over_300m=("err", lambda x: (x > 300).mean()), peak=("peak", "median"), psr=("psr", "median"))
    print(g.round(3).to_string())
    s = df.sort_values("lit")
    json.dump(dict(lit=s.lit.tolist(), rel_ex=(s.ex / s.agl).tolist(), rel_ez=(s.ez / s.agl).tolist(), peak=s.peak.tolist(), psr=s.psr.tolist(),
                   note="empirical camera model from Unity survey (ZNCC matcher, read noise 2 DN, shot k 0.6, Sun error 0.05-0.25 deg el, +-1 deg az)"),
              open(os.path.join(D, f"cam_model{tag}.json"), "w"))
    g.to_csv(os.path.join(D, f"summary_by_lit{tag}.csv"))


if __name__ == "__main__":
    import sys
    print("== reference predicted from direct light only (primary)")
    main(ref_mode="direct", tag="")
    print("== reference with the same scattered light as the live image (optimistic)")
    main(ref_mode="same", tag="_optimistic")
