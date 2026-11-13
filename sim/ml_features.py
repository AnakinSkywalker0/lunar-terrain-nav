"""Features for the 'ml2' judge (corrected-label classifier with history). Used in flight (engine.py) and in training.

Column order (22 features) - MUST match models/fault_clf_v3.pkl, which stores the same list in its metadata:
   0-7   the original 8: nu/sd, nu, h_std, h_range, |nu|/sqrt(R), mean|nu_hist|, reading/1000, ellipse radius
   8-14  map consistency: dist_outside_m, pos_in_interval, interval_width_m, range_over_rad, h_std_small, h_std_large, lit_frac
   15    vertical speed estimate
   16-21 history of EARLIER flagged readings of the same descent in the last 40 steps (10 s):
         n_prev, mean_z_prev, std_z_prev, mean_abs_z_prev, frac_same_sign, dt_prev
This module does not import the engine (the engine imports this module).
"""
import numpy as np

WINDOW = 40  # steps of 0.25 s
NAMES = ["nu_over_sd", "nu", "h_std", "h_range", "abs_nu_over_sqrtR", "mean_abs_nu_hist", "agl_km", "ellipse_rad",
         "dist_outside_m", "pos_in_interval", "interval_width_m", "range_over_rad", "h_std_small", "h_std_large", "lit_frac",
         "vz_est", "n_prev", "mean_z_prev", "std_z_prev", "mean_abs_z_prev", "frac_same_sign", "dt_prev"]


def base_features(nu, S0, R, stats, x_est, rad, agl_true, nu_hist):
    """The original 8 features (identical to engine._features) plus 7 map-consistency features (identical to ml_eval)."""
    sd = np.sqrt(S0)
    x, y, z = x_est[:, 0], x_est[:, 1], x_est[:, 2]
    v1 = np.stack([nu / sd, nu, stats.hstd(x, y, rad), stats.hmax(x, y, rad) - stats.hmin(x, y, rad),
                   np.abs(nu) / np.sqrt(R), np.abs(nu_hist).mean(axis=1), agl_true / 1000.0, rad], axis=1)
    hmax = stats.hmax(x, y, rad + 30.0); hmin = stats.hmin(x, y, rad + 30.0)
    r_lo, r_hi = z - hmax, z - hmin
    width = np.maximum(r_hi - r_lo, 0.0)
    dist_out = np.maximum(np.maximum(r_lo - agl_true, agl_true - r_hi), 0.0)
    pos = (agl_true - r_lo) / (width + 1.0)
    try:
        lit = stats.litfrac(x, y, rad)
    except Exception:  # worlds without a shadow raster
        lit = np.full(len(x), 0.5, dtype=np.float32)
    v2 = np.stack([dist_out, pos, width, width / (rad + 1.0), stats.hstd(x, y, 60.0), stats.hstd(x, y, 960.0), lit], axis=1)
    return np.concatenate([v1, v2], axis=1)


def history_features(z_now, z_buf):
    """History of EARLIER flagged readings. z_buf: (n, WINDOW) normalised innovations of the previous WINDOW steps,
    NaN where the reading was not flagged (column -1 = one step ago). z_now: (n,) current normalised innovation."""
    valid = ~np.isnan(z_buf)
    n_prev = valid.sum(axis=1).astype(np.float64)
    zb = np.where(valid, z_buf, 0.0)
    cnt = np.maximum(n_prev, 1.0)
    mean = zb.sum(axis=1) / cnt
    var = np.maximum((zb ** 2).sum(axis=1) / cnt - mean ** 2, 0.0)
    std = np.where(n_prev > 1, np.sqrt(var), 0.0)
    mabs = np.abs(zb).sum(axis=1) / cnt
    ss = np.where(valid, np.sign(zb), 0.0).sum(axis=1)
    same = np.where(n_prev > 0, (n_prev + np.sign(z_now) * ss) / 2.0 / cnt, 0.5)
    last = WINDOW - 1 - np.argmax(valid[:, ::-1], axis=1)          # index of the most recent flagged step
    dt = np.where(n_prev > 0, WINDOW - last, float(WINDOW))
    mean = np.where(n_prev > 0, mean, 0.0); mabs = np.where(n_prev > 0, mabs, 0.0)
    return np.stack([n_prev, mean, std, mabs, same, dt], axis=1)


def features_v3(nu, S0, R, stats, x_est, rad, agl_true, nu_hist, z_buf):
    base = base_features(nu, S0, R, stats, x_est, rad, agl_true, nu_hist)
    hist = history_features(nu / np.sqrt(S0), z_buf)
    return np.concatenate([base, x_est[:, 5:6], hist], axis=1)


def push_history(z_buf, flagged, z_now):
    """Advance the buffer by one step (call once per step, after the features were computed)."""
    return np.concatenate([z_buf[:, 1:], np.where(flagged, z_now, np.nan)[:, None]], axis=1)
