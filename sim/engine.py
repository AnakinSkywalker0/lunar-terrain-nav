"""Batched lunar-descent simulator: truth physics, sensors with faults, EKF with pluggable altimeter judges.

All state arrays have a leading run axis N so hundreds of descents run in lock-step with numpy.
Every judge sees identical truth-independent noise (common random numbers), see Draws.
"""
from dataclasses import dataclass, field
import types
import warnings
import numpy as np

import dyn6 as _dyn6

G = 1.62
G0 = 9.80665
CHI2_99 = 6.635          # 1-dof 99 % gate
DT = 0.25

# --- multi-beam slant-range sensor (round-3 extension; used only with beams >= 2 and the *_mb judges) ---
BEAM_CANT_DEG = 22.5     # ASSUMED beam cant from nadir (NDL-like); not the real instrument's geometry
MB_JUDGES = ("pitfal_mb", "tolerance_mb")
_F_GRID = np.geomspace(0.02, 4.0, 40)


def _slant_range(height, px, py, z, ux, uy, ct, st):
    """Slant range of a beam leaving (px, py, z) along horizontal direction (ux, uy), canted by angle theta from nadir
    (ct = cos, st = sin): first crossing of the ray with the terrain `height(x, y)`, by coarse marching then bisection.
    If the ray never meets the terrain within 4x the nadir range, the upper bound is returned."""
    agl = np.maximum(z - height(px, py), 0.5)
    s_nom = agl / ct
    S = s_nom[:, None] * _F_GRID[None, :]
    f = (z[:, None] - S * ct) - height((px[:, None] + S * st * ux).ravel(), (py[:, None] + S * st * uy).ravel()).reshape(S.shape)
    hit = f <= 0
    anyhit = hit.any(axis=1)
    first = np.where(anyhit, hit.argmax(axis=1), len(_F_GRID) - 1)
    rows = np.arange(len(S))
    hi = S[rows, first]
    lo = np.where(first > 0, S[rows, np.maximum(first - 1, 0)], 0.0)
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        above = (z - mid * ct - height(px + mid * st * ux, py + mid * st * uy)) > 0
        lo = np.where(above, mid, lo)
        hi = np.where(above, hi, mid)
    return np.where(anyhit, 0.5 * (lo + hi), hi)


def _slant_range_dir(height, px, py, z, dx, dy, cz):
    """Like _slant_range for an arbitrary beam direction: (dx, dy) = horizontal components of the unit direction, cz = its downward
    component (all arrays, one entry per run). Used by the 6-DOF dynamics, where the beams are fixed to the tilting body."""
    agl = np.maximum(z - height(px, py), 0.5)
    S = (agl / cz)[:, None] * _F_GRID[None, :]
    f = (z[:, None] - S * cz[:, None]) - height((px[:, None] + S * dx[:, None]).ravel(), (py[:, None] + S * dy[:, None]).ravel()).reshape(S.shape)
    hit = f <= 0
    anyhit = hit.any(axis=1)
    first = np.where(anyhit, hit.argmax(axis=1), len(_F_GRID) - 1)
    rows = np.arange(len(S))
    hi = S[rows, first]
    lo = np.where(first > 0, S[rows, np.maximum(first - 1, 0)], 0.0)
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        above = (z - mid * cz - height(px + mid * dx, py + mid * dy)) > 0
        lo = np.where(above, mid, lo)
        hi = np.where(above, hi, mid)
    return np.where(anyhit, 0.5 * (lo + hi), hi)


def _consensus_ok(zapp, var):
    """PITFAL-style consensus check (our interpretation) on the apparent altitudes of the K beams of each run.
    zapp, var: (m, K). A beam is inconsistent if its apparent altitude differs from the median of the beams by more than the
    99 % chi-square limit allows. Needs K >= 3 to tell which beam is the odd one out; with K < 3 every beam is kept."""
    K = zapp.shape[1]
    if K < 3:
        return np.ones(zapp.shape, dtype=bool)
    med = np.median(zapp, axis=1)
    chi = (zapp - med[:, None]) ** 2 / (var * (1.0 + 1.0 / K))
    return chi <= CHI2_99


# --- round-4 switches (all default off; see docs/NEXT_DIRECTION_REVIEW_AND_BUILD.md, Part C) ---
FLOOR_MODES = ("both", "gate", "variance")
VBAKF_RHO, VBAKF_ALPHA0, VBAKF_ITER = 0.97, 2.0, 3      # VB-AKF memory, prior degrees of freedom, fixed-point iterations
DIFF_WINDOW = 40                                         # samples in the second-difference noise estimator


# --- round-5 switches (all default off; see docs/LANTERN_Architecture_and_Build_Plan.docx) ---
CUSUM_K, CUSUM_H = 1.0, 6.0              # CUSUM allowance and alarm level (in units of the normalised innovation)
IMM_MULT = np.array([1.0, 4.0, 16.0, 64.0])  # noise modes of the IMM-style noise mixer (multiples of the nominal sigma)
IMM_EPS, IMM_PF, IMM_RANGE = 0.02, 0.03, 500.0   # mode switching probability, prior fault probability, outlier range (m)
DE_W, DE_MAX = 24, 16                    # delay estimator: window (steps) and largest lag tried (steps)
MS_EVERY, MS_W, MS_STEP, MS_SPAN = 16, 20, 8, 3000.0   # map-offset search: every steps, window samples, sample spacing, coarse span (m)
ALT2_MULT = 3.0                          # second (dissimilar) altimeter: noise relative to the first
SS_CHI2 = 11.345                         # 99 % chi-square limit, 3 dof, for the solution-separation test


def _t_weight(chi, dof):
    """Student-t (heavy-tailed noise) weight of a reading with normalised innovation chi = nu^2 / S (Agamennoni et al. 2012, one VB step)."""
    return (dof + 1.0) / (dof + chi)


def _joint_update(x, P, nu, Hm, Rd, Rc, ok):
    """One joint vector EKF update from K beams. x (m,9), P (m,9,9), nu (m,K), Hm (m,K,9), Rd (m,K) independent variances, Rc shared
    (map) variance common to all beams, ok (m,K) which beams are used. Returns new copies of x and P."""
    m, K = nu.shape
    Rdm = np.where(ok, Rd, 1e12)
    nu_m = np.where(ok, nu, 0.0)
    PHt = np.einsum("mij,mkj->mik", P, Hm)
    S = np.einsum("mki,mil->mkl", Hm, PHt) + Rc * np.ones((K, K))[None] + np.einsum("mk,kl->mkl", Rdm, np.eye(K))
    sol_nu = np.linalg.solve(S, nu_m[:, :, None])[:, :, 0]
    xn = x + np.einsum("mik,mk->mi", PHt, sol_nu)
    Pn = P - np.einsum("mik,mkj->mij", PHt, np.linalg.solve(S, np.swapaxes(PHt, 1, 2)))
    return xn, 0.5 * (Pn + np.swapaxes(Pn, 1, 2))


def _solution_separation(x, P, nu, Hm, Rd, Rc, ok):
    """ARAIM-style solution separation with single-fault exclusion: for each beam compare the full solution with the solution
    without it (position and altitude, covariance of the difference, 99 % chi-square, 3 dof). If any test fails, the beam with the
    largest separation is flagged (one fault assumed). Needs three accepted beams to isolate one."""
    m, K = nu.shape
    flagged = np.zeros((m, K), dtype=bool)
    full_x, full_P = _joint_update(x, P, nu, Hm, Rd, Rc, ok)
    can = ok.sum(axis=1) >= 3
    if not can.any():
        return flagged
    stats_j = np.full((m, K), -1.0)
    for j in range(K):
        okj = ok.copy()
        okj[:, j] = False
        xj, Pj = _joint_update(x, P, nu, Hm, Rd, Rc, okj)
        d = (full_x - xj)[:, :3]
        C = (Pj - full_P)[:, :3, :3]
        ok_c = np.trace(C, axis1=1, axis2=2) > 1e-6
        stat = np.einsum("mi,mi->m", d, np.linalg.solve(C + 1e-9 * np.eye(3)[None], d[:, :, None])[:, :, 0])
        stats_j[:, j] = np.where(ok[:, j] & can & ok_c, stat, -1.0)
    worst = stats_j.max(axis=1)
    return (stats_j == worst[:, None]) & (worst[:, None] > SS_CHI2)


def _sel_features(chi_t, chi_f, s_terr, s_ratio, ema_z, sig_h, s_p):
    """Features of the learned gate selector (tight gate or noise-floor gate), one row per beam reading."""
    return np.stack([np.log1p(chi_t), np.log1p(chi_f), s_terr, np.minimum(s_ratio, 100.0), ema_z, sig_h, s_p / 1000.0], axis=1)


def _floor_split(R_plain, R_floor, mode):
    """Where the running-noise floor enters: returns (measurement variance used in the gate, variance used in the update).
    mode "both" = floor in both (the round-3 behaviour); "gate" = gate only; "variance" = update only."""
    if mode == "both":
        return R_floor, R_floor
    if mode == "gate":
        return R_floor, R_plain
    return R_plain, R_floor


@dataclass
class Vehicle:
    dry: float = 1200.0
    fuel: float = 800.0
    tmax: float = 6000.0
    isp: float = 300.0


@dataclass
class Scenario:
    name: str
    burst_rate: float = 1 / 120.0      # fault bursts per second
    burst_len: tuple = (8, 20)          # samples
    noise_mult_below_agl: float = 1.0   # altimeter noise multiplier ...
    noise_mult_agl: float = 0.0         # ... applied below this true AGL (0 = never)
    dropout_agl: float = 0.0            # altimeter dead below this AGL (0 = never)
    delay_s: tuple = (0.0, 0.0)
    init_pos_sigma: float = 100.0
    map_mode: str = "ok"                # ok | wrong | missing
    divert: bool = False
    t_max: float = 800.0
    scan_ok: bool = True
    cam_sig_gain: float = 10.0          # how badly a shadowed camera is wrong (noise multiplier at full dark)
    cam_bias_gain: float = 0.7          # persistent shadow bias gain (assumed model only)
    cam_model: str = "empirical"        # 'empirical' (Unity camera survey) or 'assumed' (earlier hand-made curve)
    wrong_offset_m: float = 2000.0      # map_mode "wrong": offset of the altimeter's map lookups (m)
    fault_type: str = "burst"           # burst (bias, default) | stuck | drift | scale (single beam) | beam_dropout (multi-beam, independent)
    drift_rate: float = 3.0             # fault_type "drift": bias growth (m/s) up to the burst's drawn bias


SCENARIOS = {
    "cliff": Scenario("cliff (HAKUTO-R)", burst_rate=1 / 150.0),
    "cliff_fault": Scenario("cliff + faults", burst_rate=1 / 15.0),
    "shadow_noisy": Scenario("shadow + noisy altimeter (IM-2)", burst_rate=1 / 60.0,
                             noise_mult_below_agl=8.0, noise_mult_agl=6000.0),
    "delayed": Scenario("delayed altimeter (ispace M2)", burst_rate=1 / 300.0, delay_s=(1.0, 3.0)),
    "dropout": Scenario("altimeter dropout (IM-1)", burst_rate=1 / 300.0, dropout_agl=3000.0),
}


_CAM = {}


def _cam_model():
    if not _CAM:
        import json, os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "camera_survey", "cam_model.json")
        d = json.load(open(path))
        _CAM.update(lit=np.array(d["lit"]), rex=np.array(d["rel_ex"]), rez=np.array(d["rel_ez"]), peak=np.array(d["peak"]))
        pk = _CAM["peak"]
        rel = np.sqrt(0.5 * (_CAM["rex"] ** 2 + _CAM["rez"] ** 2))
        edges = np.quantile(pk, np.linspace(0.0, 1.0, 9))
        b = np.clip(np.searchsorted(edges, pk, side="right") - 1, 0, 7)
        _CAM["sigrel"] = np.array([np.sqrt(np.mean(rel[b == i] ** 2)) if (b == i).any() else 0.0 for i in range(8)])[b]
    return _CAM


class Draws:
    """Pre-drawn random numbers shared by all judges (same descents, noise and faults for everyone)."""

    def mb(self, K, scen):
        """Extra random numbers for a K-beam sensor (independent noise and fault bursts per beam), drawn from a SEPARATE generator so
        none of the legacy draws change. Cached per K."""
        if getattr(self, "_mb_cache", None) is not None and self._mb_cache[0] == K:
            return self._mb_cache[1]
        rng = np.random.default_rng([int(self.seed), 7919, int(K)])
        n, T = self.n, self.T
        g = rng.standard_normal((n, T, K)).astype(np.float32)
        starts = rng.random((n, T, K)) < scen.burst_rate * DT
        lens = rng.integers(scen.burst_len[0], scen.burst_len[1] + 1, (n, T, K))
        burst = np.zeros((n, T, K), dtype=bool)
        for i in np.nonzero(starts.any(axis=(1, 2)))[0]:
            for t0, k0 in zip(*np.nonzero(starts[i])):
                burst[i, t0:t0 + lens[i, t0, k0], k0] = True
        sign = np.where(rng.random((n, T, K)) < 0.5, -1.0, 1.0)
        bias = (sign * rng.uniform(30.0, 400.0, (n, T, K))).astype(np.float32)
        out = types.SimpleNamespace(g=g, burst=burst, bias=bias)
        self._mb_cache = (K, out)
        return out

    def alt2(self, scen):
        """Random numbers of the second (dissimilar) altimeter: independent noise and fault bursts, SEPARATE generator. Cached."""
        if getattr(self, "_alt2_cache", None) is not None:
            return self._alt2_cache
        rng = np.random.default_rng([int(self.seed), 104729])
        n, T = self.n, self.T
        g = rng.standard_normal((n, T)).astype(np.float32)
        starts = rng.random((n, T)) < scen.burst_rate * DT
        lens = rng.integers(scen.burst_len[0], scen.burst_len[1] + 1, (n, T))
        burst = np.zeros((n, T), dtype=bool)
        for i in np.nonzero(starts.any(axis=1))[0]:
            for k in np.nonzero(starts[i])[0]:
                burst[i, k:k + lens[i, k]] = True
        sign = np.where(rng.random((n, T)) < 0.5, -1.0, 1.0)
        bias = (sign * rng.uniform(30.0, 400.0, (n, T))).astype(np.float32)
        out = types.SimpleNamespace(g=g, burst=burst, bias=bias)
        self._alt2_cache = out
        return out

    def __init__(self, world, scen, n, seed, t_max=None):
        self.seed = seed
        rng = np.random.default_rng(seed)
        self.n = n
        self.T = int((t_max or scen.t_max) / DT) + 2
        T = self.T
        f32 = np.float32
        self.alt_g = rng.standard_normal((n, T)).astype(f32)
        self.cam_g = rng.standard_normal((n, T // 8 + 2, 2)).astype(f32)
        self.scan_g = rng.standard_normal((n, T // 2 + 2, 2)).astype(f32)
        self.imu_g = rng.standard_normal((n, T, 3)).astype(f32)
        # fault bursts: per-sample random bias while a burst is active
        burst = np.zeros((n, T), dtype=bool)
        starts = rng.random((n, T)) < scen.burst_rate * DT
        lens = rng.integers(scen.burst_len[0], scen.burst_len[1] + 1, (n, T))
        for i in np.nonzero(starts.any(axis=1))[0]:
            for k in np.nonzero(starts[i])[0]:
                burst[i, k:k + lens[i, k]] = True
        self.burst = burst
        sign = np.where(rng.random((n, T)) < 0.5, -1.0, 1.0)
        self.burst_bias = (sign * rng.uniform(30.0, 400.0, (n, T))).astype(f32)
        self.pos0_err = rng.standard_normal((n, 3)) * np.array([scen.init_pos_sigma, scen.init_pos_sigma, 30.0])
        self.vel0_err = rng.standard_normal((n, 3)) * 0.3
        self.bias_true = rng.standard_normal((n, 3)) * 0.002
        self.map_shift = rng.standard_normal((n, 2)) * 10.0
        self.map_bank = rng.integers(0, len(world.map_banks), n)
        self.cam_bias = rng.standard_normal((n, 2)) * 150.0
        d_lo, d_hi = scen.delay_s
        self.delay_steps = np.rint(rng.uniform(d_lo, d_hi, n) / DT).astype(int)
        self.cam_u = rng.random((n, T // 8 + 2))


def _scalar_update(x, P, H, nu, R, m):
    """Sequential scalar EKF update for runs where m is True. Returns nothing; mutates x, P."""
    if not m.any():
        return
    Hm, Pm = H[m], P[m]
    PHt = np.einsum("nij,nj->ni", Pm, Hm)
    S = np.einsum("ni,ni->n", Hm, PHt) + R[m]
    K = PHt / S[:, None]
    x[m] += K * nu[m][:, None]
    Pm = Pm - np.einsum("ni,nj->nij", K, PHt)
    Pm = 0.5 * (Pm + np.swapaxes(Pm, 1, 2))
    P[m] = Pm


class NavBatch:
    """Batched 9-state EKF: position, velocity, accelerometer bias."""

    def __init__(self, n, p0, v0, init_pos_sigma):
        self.x = np.zeros((n, 9))
        self.x[:, 0:3] = p0
        self.x[:, 3:6] = v0
        self.P = np.zeros((n, 9, 9))
        d = np.array([init_pos_sigma ** 2] * 2 + [30.0 ** 2] + [0.3 ** 2] * 3 + [0.004 ** 2] * 3)
        self.P[:] = np.diag(d)
        self.F = np.eye(9)
        self.F[0:3, 3:6] = DT * np.eye(3)
        self.F[3:6, 6:9] = -DT * np.eye(3)
        sa = 0.003
        self.Q = np.diag([(0.5 * sa * DT * DT) ** 2] * 3 + [(sa * DT) ** 2] * 3 + [(1e-4 * np.sqrt(DT)) ** 2] * 3)

    def predict(self, a_meas):
        x = self.x
        a = a_meas - x[:, 6:9] + np.array([0, 0, -G])
        x[:, 0:3] += x[:, 3:6] * DT + 0.5 * a * DT * DT
        x[:, 3:6] += a * DT
        P = self.F @ self.P @ self.F.T + self.Q
        self.P = 0.5 * (P + np.swapaxes(P, 1, 2))


class ProbationState:
    def __init__(self, n, K):
        self.K = K
        self.n = np.zeros(n, dtype=int)
        self.buf = np.zeros((n, K))
        self.Rbuf = np.zeros((n, K))
        self.fault = np.zeros((n, K), dtype=bool)

    def active(self):
        return self.n > 0


def simulate(world, track, scen, judge, draws, veh=None, scan=False, ml_model=None, collect=None,
             record_idx=None, sigma_probation=3.0, K_prob=10, ellipse_k=2.0, wide_gate=1.0, cam_policy=None, timestamps=None,
             ml2_mode="soft", ml2_vertical_only=False, ml2_terrain_R=False, ml2_threshold=0.5, ml2_noise_model=None,
             ml2_noise_scale=1.0, ml2_noise_normal=False, ml2_noise_heuristic=False, ml2_rule_gate=False,
             fault_label_noise_aware=False, terrain_R=False, tol_noise_floor=False,
             beams=0, beam_fault="independent", mb_consensus=False,
             tol_floor_mode="both", tol_floor_source="innovation", oracle_R=False, mb_terrain_at_footprint=False, ar1_phi=0.0,
             gate_chi2=CHI2_99, robust_t=0.0, cusum=False, imm=False, selector=None, sel_collect=None, chi_collect=None,
             delay_est=False, map_search=False, joint_update=False, solsep=False, alt2=False, dyn6=None):
    """Run all N descents for one judge. Returns a dict of per-run result arrays (+ optional recorded traces).

    Round-3 candidate switches (all default off, so every earlier result and tag stays reproducible bit for bit):
    fault_label_noise_aware = the ground-truth fault label uses the TRUE noise sigma (nominal sigma x the scenario's noise
    multiplier) instead of the nominal sigma, as sim/ml_labels.py does; it changes only the "false rejection" and "missed fault"
    bookkeeping, never a decision. terrain_R = judges wait / second / ml give unflagged readings the terrain + map variance
    that tolerance / trust already use (finding (i) of the ml-eval handoff). tol_noise_floor = the tolerance judge adds trust v2's
    running innovation-size noise estimate s_hat to its gate and its measurement variance (finding (ii)).

    judge "ml2" (added on branch ml-eval): learned fault/terrain classifier with a 10 s history of flagged readings
    (sim/ml_features.py, models/fault_clf_v3.pkl, passed as ml_model). ml2_mode: "soft" = accept every flagged reading but
    inflate its noise by 1/(1-p)^2 where p is the predicted fault probability; "hard" = reject if p > 0.5.
    Diagnostic switches (default off): ml2_vertical_only = an accepted flagged reading corrects altitude only (no horizontal
    terrain-gradient update); ml2_terrain_R = unflagged readings get the terrain+map variance that tolerance/trust use;
    ml2_threshold = reject threshold in hard mode (default 0.5); ml2_noise_model = error-size regressor (models/err_reg_v3.pkl):
    accepted flagged readings get a variance floor (sigma_nominal * expm1(pred) * ml2_noise_scale)^2; ml2_noise_normal = also for
    unflagged readings; ml2_noise_heuristic = NON-ML control: every accepted reading gets the floor s_hat^2 where s_hat is the running
    innovation-size estimate trust v2 uses (no learned model); ml2_rule_gate = EXPERIMENTAL non-ML replacement for the classifier:
    a tolerance-style chi-square gate whose noise level adapts through s_hat (use together with ml2_noise_heuristic=True).
    All other judges are unchanged.

    Round-4 switches (default off, bit-identical when off): tol_floor_mode = where the tolerance noise floor enters, "both" (round 3),
    "gate" or "variance"; tol_floor_source = "innovation" (s_hat) or "diff" (map-independent robust second-difference noise estimate,
    single-beam tolerance only); oracle_R = tolerance uses the TRUE noise level (R x multiplier^2), an upper bound, not deployable;
    mb_terrain_at_footprint = multi-beam terrain variance at each beam's footprint instead of at nadir; ar1_phi = AR(1) correlation of
    the altimeter noise (unit variance kept; single beam only); judge "vbakf" = variational-Bayes adaptive Kalman filter noise
    estimate (Sarkka & Nummenmaa 2009) inside the tolerance gate. Result key s_hat_max = per-run maximum of the running noise estimate.

    Round-5 switches (default off, bit-identical when off; judges "tolerance" = single beam, "tolerance_mb" = three beams):
    gate_chi2 = chi-square gate limit (default 6.635; conformal calibration sets it from valid-reading innovations); robust_t = Student-t
    degrees of freedom: no hard gate, every reading weighted by (dof+1)/(dof+chi); cusum = also reject while a CUSUM of normalised
    innovations is in alarm (single beam); imm = IMM-style mixing of noise-level modes with a fault mode, single filter state
    (single beam, not with the noise floor); selector = learned model choosing, per beam reading, the tight or the noise-floor gate
    (multi-beam, with tol_noise_floor); sel_collect / chi_collect = lists that collect training rows / valid-reading chi values;
    delay_est = estimate the unstamped reading delay from the history (single beam); map_search = search a grid of map offsets when
    most readings are rejected and adopt the best (single beam); joint_update = one joint vector update across the beams with a
    shared map error (multi-beam); solsep = ARAIM-style solution-separation screening of the beams (multi-beam, implies joint update);
    alt2 = a second, dissimilar altimeter (3x noise, independent faults, no dropout; single beam, ASSUMED model).
    Scenario.fault_type selects stuck-at, drift, scale-factor (single beam) or beam-dropout (multi-beam) faults instead of bias bursts.
    Result key nees_sum = summed position NEES (3 dof) over the descent.

    Round-6 switch (default off, bit-identical when off): dyn6 = a sim/dyn6.py Dyn6Config switches the truth dynamics from a point mass
    that obeys the commanded acceleration at once to a 6-DOF rigid body with one body-fixed engine (throttle lag, attitude control with
    a torque limit, inertia, thrust misalignment, centre-of-mass offset), a gyro + star-tracker attitude estimate, a strapdown
    accelerometer rotated with the ESTIMATED attitude and body-fixed altimeter beams. Touchdown also needs the tilt and body rate below
    the Dyn6Config limits. Result keys with dyn6: impact_tilt, impact_rate, tilt_max, att_err_rms_deg, rcs_fuel, success_legacy
    (the 3-DOF criteria only). Not with a missing map.
    """
    if dyn6 is not None and (scen.map_mode == "missing" or alt2):
        raise ValueError("dyn6 does not support a missing map or the second altimeter")
    if tol_floor_mode not in FLOOR_MODES:
        raise ValueError("tol_floor_mode must be one of %s" % (FLOOR_MODES,))
    if tol_floor_source not in ("innovation", "diff"):
        raise ValueError("tol_floor_source must be 'innovation' or 'diff'")
    if oracle_R and tol_noise_floor:
        raise ValueError("oracle_R cannot be combined with tol_noise_floor")
    if not 0.0 <= ar1_phi < 1.0:
        raise ValueError("ar1_phi must be in [0, 1)")
    if tol_floor_source == "diff" and not (tol_noise_floor and judge == "tolerance"):
        raise ValueError("tol_floor_source='diff' needs judge 'tolerance' with tol_noise_floor=True")
    mb_mode = judge in MB_JUDGES
    if mb_mode:
        if beams < 2:
            raise ValueError("judge %s needs beams >= 2" % judge)
        if scen.map_mode == "missing" or scen.delay_s != (0.0, 0.0):
            raise ValueError("multi-beam judges do not support a missing map or delayed readings")
        if beam_fault not in ("independent", "common"):
            raise ValueError("beam_fault must be 'independent' or 'common'")
        if ar1_phi > 0 or tol_floor_source == "diff":
            raise ValueError("ar1_phi and the diff floor are single-beam only")
    if scen.fault_type not in ("burst", "stuck", "drift", "scale", "beam_dropout"):
        raise ValueError("unknown fault_type %r" % scen.fault_type)
    if (cusum or imm or delay_est or map_search or alt2) and judge != "tolerance":
        raise ValueError("cusum, imm, delay_est, map_search and alt2 need judge 'tolerance' (single beam)")
    if imm and tol_noise_floor:
        raise ValueError("imm cannot be combined with tol_noise_floor")
    if (joint_update or solsep or selector is not None or sel_collect is not None) and not (judge == "tolerance_mb" and tol_noise_floor):
        raise ValueError("joint_update, solsep and selector need judge 'tolerance_mb' with tol_noise_floor=True")
    if (robust_t > 0 or gate_chi2 != CHI2_99 or chi_collect is not None) and judge not in ("tolerance", "tolerance_mb"):
        raise ValueError("robust_t, gate_chi2 and chi_collect apply to the tolerance judges only")
    if scen.fault_type == "beam_dropout" and not mb_mode:
        raise ValueError("fault_type 'beam_dropout' needs a multi-beam judge")
    if scen.fault_type in ("stuck", "drift", "scale") and mb_mode:
        raise ValueError("fault types stuck/drift/scale are single-beam only")
    if mb_mode and beam_fault == "common" and scen.fault_type == "beam_dropout":
        raise ValueError("beam_dropout is an independent-beam fault")
    veh = veh or Vehicle()
    if judge == "ml2":
        import ml_features as MF
    opts = {"cam": True, "prob": True, "phys": True}
    if judge == "trust_nocam": opts["cam"] = False
    if judge == "trust_noprob": opts["prob"] = False
    if judge == "trust_nophys": opts["phys"] = False
    is_trust = judge.startswith("trust")
    v2 = judge.startswith("trust2")
    use_ts = v2 if timestamps is None else timestamps      # time-stamped altimeter readings (delay compensation)
    # camera policies: naive (always use the fix) | conf (use the matcher's own confidence) | aware (predicted lit
    # fraction from Sun + DEM, the trust layer's step 3) | both. Default: trust layers 'both', all other judges 'conf'.
    if cam_policy is None:
        cam_policy = ("both" if opts["cam"] else "conf") if is_trust else "conf"
    cam_use_aware = cam_policy in ("aware", "both")
    cam_use_conf = cam_policy in ("conf", "both")
    cam_soft = cam_policy == "soft"      # round 5: every fix is used, weighted by the error size the survey saw at that confidence
    n = draws.n
    T = draws.T
    sx, sy = track["start"]
    tx, ty = track["target"]
    truth = world.truth
    banks = world.map_banks
    stats = world.stats
    coarse = world.coarse_ref
    shift = draws.map_shift
    missing = scen.map_mode == "missing"
    wrong = scen.map_mode == "wrong"
    use_map = judge != "fixed"
    # --- truth initial state
    h0 = world.dem_grid.height(sx, sy)
    p = np.tile([sx, sy, h0 + track["start_agl"]], (n, 1)).astype(np.float64)
    dirv = np.array([tx - sx, ty - sy]); L0 = np.hypot(*dirv); dirv = dirv / L0
    v = np.zeros((n, 3)); v[:, 0] = 100.0 * dirv[0]; v[:, 1] = 100.0 * dirv[1]; v[:, 2] = -140.0
    fuel = np.full(n, veh.fuel)
    alive = np.ones(n, dtype=bool)
    touched = np.zeros(n, dtype=bool)
    # --- nav filter (estimate frame = truth frame at start plus initial error)
    nav = NavBatch(n, p + draws.pos0_err, v + draws.vel0_err, scen.init_pos_sigma)
    prob = ProbationState(n, K_prob)
    flag_timer = np.zeros(n, dtype=int)
    a_cmd = np.zeros((n, 3))
    # results
    res = {k: np.zeros(n) for k in ["impact_vz", "impact_vh", "impact_slope", "fuel_left", "t_end", "miss_m",
                                    "alt_sq", "alt_n", "z_sq", "valid_total", "valid_rej", "fault_total", "fault_acc",
                                    "cam_w_sum", "cam_w_n", "z_final_true_agl", "s_hat_max", "nees_sum"]}
    res["success"] = np.zeros(n, dtype=bool)
    if dyn6 is not None:
        res["impact_tilt"], res["impact_rate"] = np.zeros(n), np.zeros(n)
        res["success_legacy"] = np.zeros(n, dtype=bool)
    dy = None                                       # 6-DOF state, created at the first step from the first thrust direction
    res["outcome"] = np.array(["flying"] * n, dtype=object)
    rec = None
    if record_idx is not None:
        rec = {k: [] for k in ["t", "x", "y", "z", "ex", "ey", "ez", "agl_true", "agl_est", "gate", "acc", "r", "fault", "fuel", "tgt_x", "tgt_y", "cam_w", "prob", "s_hat"]}
    r_hist = np.zeros((n, T), dtype=np.float32)
    alt_g = draws.alt_g
    if ar1_phi > 0:      # AR(1)-correlated altimeter noise with the same unit variance, built from the existing draws
        from scipy.signal import lfilter
        alt_g = lfilter([np.sqrt(1.0 - ar1_phi ** 2)], [1.0, -ar1_phi], draws.alt_g, axis=1).astype(draws.alt_g.dtype)
    rbuf = np.full((n, 3), np.nan)                 # last three altimeter readings (second-difference noise estimator)
    dbuf = np.full((n, DIFF_WINDOW), np.nan)       # |second differences| of the last DIFF_WINDOW steps
    sig_diff = np.zeros(n)
    vb_a = np.full(n, VBAKF_ALPHA0)                # VB-AKF noise-scale posterior (inverse-gamma, in units of the nominal variance R)
    vb_b = np.full(n, VBAKF_ALPHA0)
    last_valid_r = np.full(n, np.nan)
    cs = np.zeros(n)                               # CUSUM statistic
    imm_mu = np.tile(np.array([0.7, 0.2, 0.07, 0.03]), (n, 1))   # IMM-style noise-mode probabilities
    burst_age = np.zeros(n, dtype=int)             # samples since the current fault burst began (new fault types)
    stuck_val = np.zeros(n)
    r_prev_out = np.zeros(n)
    ema_z = np.ones(n)                             # running mean of normalised beam innovations (selector feature)
    est_off = np.zeros((n, 2))                     # estimated map offset (map-offset search); zero = trust the map as is
    rej_ema = np.zeros(n)
    est_lag = np.zeros(n, dtype=int)               # estimated reading delay in steps (delay estimator)
    lag_sum = np.zeros(n)
    lag_n = np.zeros(n)
    if delay_est:
        r_mh = np.full((n, T), np.nan, dtype=np.float32)
        pred_hist = np.full((n, T), np.nan, dtype=np.float32)
    if map_search:
        r_mh = np.full((n, T), np.nan, dtype=np.float32)
        x_hist = np.zeros((n, T), dtype=np.float32)
        y_hist = np.zeros((n, T), dtype=np.float32)
        z_hist = np.zeros((n, T), dtype=np.float32)
    target = np.tile([tx, ty], (n, 1)).astype(np.float64)
    diverted = np.zeros(n, dtype=bool)
    div_target = None
    if scen.divert:
        div_target = _find_divert(world, track)
    cam_period = int(2.0 / DT)
    scan_period = int(0.5 / DT)
    cam_i = 0
    scan_i = 0
    lit_cam_prev_ok = np.ones(n, dtype=bool)
    nu_hist = np.zeros((n, 4))
    z_buf = np.full((n, 40), np.nan)          # ml2: normalised innovations of flagged readings in the last 40 steps
    ml_feat_all = []

    def mapq(x, y, idx):
        """Onboard map height at estimated map-frame position (registration shift applied)."""
        out = np.empty(len(idx), dtype=np.float64)
        bank_ids = draws.map_bank[idx]
        for b in np.unique(bank_ids):
            m = bank_ids == b
            g = banks[b]
            out[m] = g.height(x[m] - shift[idx[m], 0] + (scen.wrong_offset_m if wrong else 0.0) - est_off[idx[m], 0], y[m] - shift[idx[m], 1] - est_off[idx[m], 1])
        return out

    def mapg(x, y, idx):
        gx = np.empty(len(idx)); gy = np.empty(len(idx))
        bank_ids = draws.map_bank[idx]
        for b in np.unique(bank_ids):
            m = bank_ids == b
            gxm, gym = banks[b].grad(x[m] - shift[idx[m], 0] + (scen.wrong_offset_m if wrong else 0.0) - est_off[idx[m], 0], y[m] - shift[idx[m], 1] - est_off[idx[m], 1], step=40.0)
            gx[m], gy[m] = gxm, gym
        return gx, gy

    def foot(kb, s, ux, uy):
        """Horizontal offset of the point a beam of slant range s reaches, on the nominal geometry or (6-DOF) on the estimated attitude."""
        if dy is None:
            return s * st * ux, s * st * uy
        return s * DXE[:, kb], s * DYE[:, kb]

    g_est = coarse.height(nav.x[:, 0], nav.x[:, 1]).astype(np.float64)
    s_hat = np.ones(n)
    use_gest = v2 and missing
    r_f = np.maximum(nav.x[:, 2] - g_est, 1.0)      # no-map mode: terrain-relative altitude and rate (alpha-beta filter)
    rate_f = nav.x[:, 5].copy()
    last_cam_w = np.zeros(n)
    allidx = np.arange(n)
    for k in range(T - 1):
        if not alive.any():
            break
        t = k * DT
        x_est = nav.x
        # ---------------- guidance on the estimate ----------------
        if use_gest:
            hb = g_est
        elif use_map and not missing:
            hb = mapq(x_est[:, 0], x_est[:, 1], allidx)
        else:
            hb = coarse.height(x_est[:, 0], x_est[:, 1])
        agl_b = x_est[:, 2] - hb
        vz_g = x_est[:, 5]
        if use_gest:    # no map: final approach flies on the terrain-relative altimeter filter
            fin = agl_b < 200.0
            agl_b = np.where(fin, r_f, agl_b)
            vz_g = np.where(fin, rate_f, vz_g)
        if div_target is not None:
            go = (agl_b < 5000.0) & ~diverted
            diverted |= go
            target[go] = div_target
        mass = veh.dry + fuel
        amax = veh.tmax / mass
        dvec = target - x_est[:, 0:2]
        dist = np.hypot(dvec[:, 0], dvec[:, 1]) + 1e-6
        vdes_h = np.minimum(110.0, np.sqrt(2.0 * 1.0 * dist))
        vdes_h = np.where(agl_b < 60.0, 0.0, vdes_h)
        vdes = dvec / dist[:, None] * vdes_h[:, None]
        ah = np.clip(0.5 * (vdes - x_est[:, 3:5]), -1.5, 1.5)
        ahm = np.hypot(ah[:, 0], ah[:, 1])
        ah *= np.minimum(1.0, 1.5 / np.maximum(ahm, 1e-9))[:, None]
        a_net = 0.5 * np.maximum(amax - G, 0.2)
        cone = 0.08 * dist
        h_eff = np.maximum(agl_b - cone, 0.0)
        vdes_z = -(0.7 + np.sqrt(2.0 * a_net * np.maximum(h_eff - 15.0, 0.0)))   # constant 0.7 m/s final 15 m
        av = np.clip(G + 1.5 * (vdes_z - vz_g), 0.0, amax)
        horiz_room = np.sqrt(np.maximum(amax ** 2 - av ** 2, 0.0))
        scale = np.minimum(1.0, horiz_room / np.maximum(np.hypot(ah[:, 0], ah[:, 1]), 1e-9))
        a_cmd = np.stack([ah[:, 0] * scale, ah[:, 1] * scale, av], axis=1)
        a_cmd[fuel <= 0.0] = 0.0
        a_cmd[~alive] = 0.0
        if use_gest:
            aA = a_cmd[:, 2] - G
            r_f = r_f + rate_f * DT + 0.5 * aA * DT * DT
            rate_f = rate_f + aA * DT
        # ---------------- truth dynamics ----------------
        if dyn6 is None:
            am = np.linalg.norm(a_cmd, axis=1)
            burn = mass * am / (veh.isp * G0) * DT
            fuel = np.maximum(0.0, fuel - burn * alive)
            acc = a_cmd + np.array([0, 0, -G])
            p_new = p + v * DT + 0.5 * acc * DT * DT
            v_new = v + acc * DT
        else:
            if dy is None:
                zd0, am0 = _dyn6.command_from_accel(a_cmd, dyn6)
                dir0 = np.where((am0 > 1e-6)[:, None], zd0, np.array([0.0, 0.0, 1.0]))
                dy = _dyn6.Dyn6(dyn6, n, draws.seed, dir0)
            p_new, v_new, f_body, t_mean, rcs_kg = dy.step(p, v, a_cmd, mass, veh.tmax, alive & (fuel > 0.0), DT)
            fuel = np.maximum(0.0, fuel - (t_mean / (veh.isp * G0) * DT + rcs_kg) * alive)
        ht_new = truth.height(p_new[:, 0], p_new[:, 1])
        contact = alive & (p_new[:, 2] <= ht_new)
        if contact.any():
            ci = np.nonzero(contact)[0]
            res["impact_vz"][ci] = -v_new[ci, 2]
            res["impact_vh"][ci] = np.hypot(v_new[ci, 0], v_new[ci, 1])
            res["impact_slope"][ci] = truth.slope_deg(p_new[ci, 0], p_new[ci, 1], step=20.0)
            res["fuel_left"][ci] = fuel[ci]
            res["t_end"][ci] = t + DT
            res["miss_m"][ci] = np.hypot(p_new[ci, 0] - tx, p_new[ci, 1] - ty) if div_target is None else \
                np.hypot(p_new[ci, 0] - div_target[0], p_new[ci, 1] - div_target[1])
            res["z_final_true_agl"][ci] = 0.0
            ok = (res["impact_vz"][ci] <= 2.0) & (res["impact_vh"][ci] <= 1.5) & (res["impact_slope"][ci] <= 10.0) & (fuel[ci] > 0)
            if dy is not None:      # 6-DOF: the vehicle must also touch down upright and not spinning
                res["success_legacy"][ci] = ok
                res["impact_tilt"][ci], res["impact_rate"][ci] = dy.tilt_deg()[ci], dy.rate_dps()[ci]
                ok = ok & (res["impact_tilt"][ci] <= dyn6.tilt_land_max_deg) & (res["impact_rate"][ci] <= dyn6.rate_land_max_dps)
            res["success"][ci] = ok
            res["outcome"][ci] = np.where(ok, "landed", np.where(res["impact_vz"][ci] > 2.0, "crash", "rough"))
            touched[ci] = True
            alive[ci] = False
        p = np.where(alive[:, None], p_new, p)
        v = np.where(alive[:, None], v_new, v)
        # ---------------- IMU + EKF predict ----------------
        if dy is None:
            a_meas = a_cmd + draws.bias_true + 0.003 * draws.imu_g[:, k, :]
        else:
            dy.estimate(k + 1, DT, alive)
            a_meas = dy.accel_world_meas(f_body, draws.bias_true, 0.003 * draws.imu_g[:, k, :])
        nav.predict(a_meas)
        x_est = nav.x
        tt = k + 1
        # ---------------- altimeter ----------------
        ht = truth.height(p[:, 0], p[:, 1])
        agl_true = p[:, 2] - ht
        r_true = agl_true
        if dy is not None and not mb_mode:      # body-fixed beam: true slant range, converted to a vertical range with the ESTIMATED tilt
            Rt = dy.R_true()
            s_t1 = _slant_range_dir(truth.height, p[:, 0], p[:, 1], p[:, 2], -Rt[:, 0, 2], -Rt[:, 1, 2], np.maximum(Rt[:, 2, 2], 0.2))
            r_true = s_t1 * np.maximum(dy.R_est()[:, 2, 2], 0.2)
        r_hist[:, tt] = r_true
        d_idx = np.maximum(tt - draws.delay_steps, 0)
        r_src = r_hist[allidx, d_idx]
        sig_nom = 1.0 + 0.0015 * np.maximum(r_src, 0)
        mult = np.ones(n)
        if scen.noise_mult_agl > 0:
            mult = np.where(agl_true < scen.noise_mult_agl, scen.noise_mult_below_agl, 1.0)
        r_meas = r_src + alt_g[:, tt] * sig_nom * mult
        burst = draws.burst[:, tt]
        if scen.fault_type == "burst":
            r_meas = r_meas + np.where(burst, draws.burst_bias[:, tt], 0.0)
        elif scen.fault_type != "beam_dropout":
            burst_age = np.where(burst, burst_age + 1, 0)
            sgn = np.sign(draws.burst_bias[:, tt])
            if scen.fault_type == "stuck":      # the output freezes at the last good value
                stuck_val = np.where(burst_age == 1, r_prev_out, stuck_val)
                r_meas = np.where(burst, stuck_val, r_meas)
            elif scen.fault_type == "drift":    # the error grows slowly up to the drawn bias
                r_meas = r_meas + np.where(burst, sgn * np.minimum(burst_age * DT * scen.drift_rate, np.abs(draws.burst_bias[:, tt])), 0.0)
            else:                               # scale: the reading is off by a percentage (2 to 30 %)
                r_meas = r_meas + np.where(burst, draws.burst_bias[:, tt] / 400.0 * 0.3 * r_src, 0.0)
            r_prev_out = r_meas.copy()
        avail = alive & (agl_true < 20000.0)
        if scen.dropout_agl > 0:
            avail &= agl_true > scen.dropout_agl
        if mb_mode:
            # ---- multi-beam slant-range sensor: `beams` beams canted BEAM_CANT_DEG from nadir, evenly spaced in azimuth ----
            idx = np.nonzero(avail)[0]
            if idx.size:
                Kb = beams
                ct, st = np.cos(np.deg2rad(BEAM_CANT_DEG)), np.sin(np.deg2rad(BEAM_CANT_DEG))
                mbd = draws.mb(Kb, scen)
                dirs = [(np.cos(2 * np.pi * kb / Kb), np.sin(2 * np.pi * kb / Kb)) for kb in range(Kb)]
                if dy is not None:      # beams fixed to the body: world directions from the true (sensor) and estimated (filter) attitude
                    Bb = np.array([(st * ux_, st * uy_, -ct) for ux_, uy_ in dirs])
                    Dt = np.einsum("nij,kj->nki", dy.R_true()[idx], Bb)
                    De = np.einsum("nij,kj->nki", dy.R_est()[idx], Bb)
                    DXE, DYE, CZE = De[:, :, 0], De[:, :, 1], np.maximum(-De[:, :, 2], 0.2)
                s_meas = np.zeros((idx.size, Kb))
                lbl_b = np.zeros((idx.size, Kb), dtype=bool)
                for kb, (ux, uy) in enumerate(dirs):
                    if dy is None:
                        s_t = _slant_range(truth.height, p[idx, 0], p[idx, 1], p[idx, 2], ux, uy, ct, st)
                    else:
                        s_t = _slant_range_dir(truth.height, p[idx, 0], p[idx, 1], p[idx, 2], Dt[:, kb, 0], Dt[:, kb, 1], np.maximum(-Dt[:, kb, 2], 0.2))
                    sig_t = (1.0 + 0.0015 * s_t) * mult[idx]
                    if beam_fault == "common":      # one fault burst hits all beams alike (consensus cannot see it)
                        bias = np.where(draws.burst[idx, tt], draws.burst_bias[idx, tt], 0.0)
                    elif scen.fault_type == "beam_dropout":
                        bias = np.zeros(idx.size)
                    else:
                        bias = np.where(mbd.burst[idx, tt, kb], mbd.bias[idx, tt, kb], 0.0)
                    s_meas[:, kb] = s_t + mbd.g[idx, tt, kb] * sig_t + bias
                    lbl_b[:, kb] = np.abs(s_meas[:, kb] - s_t) > 5.0 * sig_t + 1.0
                # state snapshot used for the consensus check and the terrain-variance term
                xi, yi = nav.x[idx, 0], nav.x[idx, 1]
                sig_hi = np.sqrt(np.maximum(nav.P[idx, 0, 0], nav.P[idx, 1, 1]))
                if mb_terrain_at_footprint:     # terrain spread where each beam actually lands, not under the vehicle
                    s_terr_b = np.stack([stats.hstd(xi + foot(kb, s_meas[:, kb], ux, uy)[0], yi + foot(kb, s_meas[:, kb], ux, uy)[1], ellipse_k * sig_hi) ** 2
                                         for kb, (ux, uy) in enumerate(dirs)], axis=1)
                else:
                    s_terr_b = np.repeat((stats.hstd(xi, yi, ellipse_k * sig_hi) ** 2)[:, None], Kb, axis=1)
                R_b = (1.0 + 0.0015 * np.maximum(s_meas, 0)) ** 2
                if oracle_R and judge == "tolerance_mb":
                    R_b = R_b * mult[idx, None] ** 2
                if tol_noise_floor and judge == "tolerance_mb":
                    R_gate_b, R_upd_b = _floor_split(R_b, np.maximum(R_b, s_hat[idx, None] ** 2), tol_floor_mode)
                else:
                    R_gate_b = R_upd_b = R_b
                zapp = np.zeros_like(s_meas)
                for kb, (ux, uy) in enumerate(dirs):
                    fxk, fyk = foot(kb, s_meas[:, kb], ux, uy)
                    zapp[:, kb] = mapq(xi + fxk, yi + fyk, idx) + s_meas[:, kb] * (ct if dy is None else CZE[:, kb])
                var_z = (np.sqrt(R_gate_b) * (ct if dy is None else CZE)) ** 2 + s_terr_b + world.map_sigma ** 2
                use_cons = (judge == "pitfal_mb") or mb_consensus
                cons_ok = _consensus_ok(zapp, var_z) if use_cons else np.ones(s_meas.shape, dtype=bool)
                acc_any = np.zeros(n, dtype=bool)
                flag_any = np.zeros(n, dtype=bool)
                nu_abs = np.zeros(n)
                n_acc = np.zeros(n)
                joint = joint_update or solsep
                map2 = world.map_sigma ** 2
                if joint:
                    nuJ = np.zeros((idx.size, Kb)); HJ = np.zeros((idx.size, Kb, 9)); RJ = np.zeros((idx.size, Kb))
                    okJ = np.zeros((idx.size, Kb), dtype=bool)
                    jlist = []
                z_acc = np.zeros(idx.size)

                def book(kb, ok, nu_k, lb, present):
                    res["valid_total"][idx] += (~lb & present)
                    res["fault_total"][idx] += (lb & present)
                    res["valid_rej"][idx] += (~ok & ~lb & present)
                    res["fault_acc"][idx] += (ok & lb)
                    acc_any[idx] |= ok
                    flag_any[idx] |= (~ok & present)
                    nu_abs[idx] += np.where(ok, np.abs(nu_k), 0.0)
                    n_acc[idx] += ok

                for kb, (ux, uy) in enumerate(dirs):
                    xe_i, ye_i, ze_i = nav.x[idx, 0], nav.x[idx, 1], nav.x[idx, 2]
                    s_p = s_meas[:, kb].copy()
                    ctk = ct if dy is None else CZE[:, kb]
                    for _ in range(3):      # predicted slant range from the map at the predicted footprint
                        fxp, fyp = foot(kb, s_p, ux, uy)
                        s_p = np.clip((ze_i - mapq(xe_i + fxp, ye_i + fyp, idx)) / ctk, 1.0, 1e5)
                    fxp, fyp = foot(kb, s_p, ux, uy)
                    gxk, gyk = mapg(xe_i + fxp, ye_i + fyp, idx)
                    nu_k = s_meas[:, kb] - s_p
                    Dk = np.maximum(ct + st * (gxk * ux + gyk * uy), 0.1) if dy is None else np.maximum(CZE[:, kb] + gxk * DXE[:, kb] + gyk * DYE[:, kb], 0.1)
                    Hk = np.zeros((n, 9))
                    Hk[idx, 0] = -gxk / Dk
                    Hk[idx, 1] = -gyk / Dk
                    Hk[idx, 2] = 1.0 / Dk
                    HPHk = np.einsum("ni,nij,nj->n", Hk[idx], nav.P[idx], Hk[idx])
                    if judge == "pitfal_mb":
                        Rk = R_b[:, kb] * np.where(flag_timer[idx] > 0, 10.0, 1.0)
                        gate_ok = nu_k * nu_k / (HPHk + Rk) <= CHI2_99
                        chi_g = nu_k * nu_k / (HPHk + Rk)
                    elif selector is not None or sel_collect is not None:
                        # learned (or, when collecting training rows, floor-in-both) choice between the tight and the noise-floor gate
                        R_fl = np.maximum(R_b[:, kb], s_hat[idx] ** 2)
                        extra = s_terr_b[:, kb] + map2
                        S_t = HPHk + R_b[:, kb] + extra
                        S_f = HPHk + R_fl + extra
                        chi_t, chi_f = nu_k * nu_k / S_t, nu_k * nu_k / S_f
                        Xs = _sel_features(chi_t, chi_f, s_terr_b[:, kb], s_hat[idx] / np.sqrt(R_b[:, kb]), ema_z[idx], sig_hi, s_p)
                        use_f = selector.predict_proba(Xs)[:, 1] >= 0.5 if selector is not None else np.ones(idx.size, dtype=bool)
                        chi_g = np.where(use_f, chi_f, chi_t)
                        Rk = np.where(use_f, R_fl, R_b[:, kb]) + extra
                        gate_ok = chi_g <= gate_chi2
                    else:
                        Rk = R_upd_b[:, kb] + s_terr_b[:, kb] + map2
                        chi_g = nu_k * nu_k / (HPHk + (R_gate_b[:, kb] + s_terr_b[:, kb] + map2))
                        gate_ok = chi_g <= gate_chi2
                    if robust_t > 0 and judge == "tolerance_mb":
                        Rk = Rk / _t_weight(chi_g, robust_t)
                        gate_ok = np.ones_like(gate_ok)
                    present = np.ones(idx.size, dtype=bool)
                    lb = lbl_b[:, kb]
                    if scen.fault_type == "beam_dropout":      # the beam returns nothing while its burst lasts
                        present = ~mbd.burst[idx, tt, kb]
                        lb = lb & present
                    ok = gate_ok & cons_ok[:, kb] & present
                    if sel_collect is not None:
                        ct_ok, cf_ok = (chi_t <= gate_chi2) == ~lb, (chi_f <= gate_chi2) == ~lb
                        dsel = (ct_ok != cf_ok) & present
                        if dsel.any():
                            sel_collect.append((Xs[dsel], cf_ok[dsel].astype(int)))
                    if chi_collect is not None:
                        chi_collect.append(chi_g[~lb & present])
                    z_acc += np.sqrt(chi_g) * present
                    if joint:
                        nuJ[:, kb] = nu_k
                        HJ[:, kb, :] = Hk[idx]
                        RJ[:, kb] = np.maximum(Rk - map2, 1e-6)
                        okJ[:, kb] = ok
                        jlist.append((kb, nu_k, lb, present))
                    else:
                        m = np.zeros(n, dtype=bool)
                        m[idx] = ok
                        nu_full = np.zeros(n)
                        nu_full[idx] = nu_k
                        R_full = np.ones(n)
                        R_full[idx] = Rk
                        _scalar_update(nav.x, nav.P, Hk, nu_full, R_full, m)
                        book(kb, ok, nu_k, lb, present)
                if joint:
                    flagged_ss = _solution_separation(nav.x[idx], nav.P[idx], nuJ, HJ, RJ, map2, okJ) if solsep else np.zeros_like(okJ)
                    okF = okJ & ~flagged_ss
                    xn, Pn = _joint_update(nav.x[idx], nav.P[idx], nuJ, HJ, RJ, map2, okF)
                    nav.x[idx], nav.P[idx] = xn, Pn
                    for kb, nu_k, lb, present in jlist:
                        book(kb, okF[:, kb], nu_k, lb, present)
                if selector is not None or sel_collect is not None:
                    ema_z[idx] = 0.9 * ema_z[idx] + 0.1 * (z_acc / Kb)
                if judge == "pitfal_mb":
                    flag_timer = np.where(flag_any, 40, np.maximum(flag_timer - 1, 0))
                elif tol_noise_floor:
                    upd_mb = n_acc > 0
                    mean_nu = nu_abs / np.maximum(n_acc, 1)
                    s_hat = np.where(upd_mb, 0.97 * s_hat + 0.03 * np.minimum(1.25 * mean_nu, 6.0 * s_hat + 1.0), s_hat)
            avail = np.zeros(n, dtype=bool)      # the single-beam path below sees no reading
        if fault_label_noise_aware:      # true noise level (nominal sigma x scenario multiplier), as in sim/ml_labels.py
            fault_lbl = np.abs(r_meas - r_true) > 5.0 * (sig_nom * mult) + 1.0
        else:
            fault_lbl = np.abs(r_meas - r_true) > 5.0 * (1.0 + 0.0015 * np.maximum(r_true, 0)) + 1.0
        # judge prediction surface
        if delay_est:      # unstamped readings: estimate the delay as the lag that best matches the reading history to the predicted ranges
            r_mh[:, tt] = np.where(avail, r_meas, np.nan)
            pred_hist[:, tt] = x_est[:, 2] - mapq(x_est[:, 0], x_est[:, 1], allidx)
            if tt >= DE_W + DE_MAX and tt % 4 == 0:
                ts = tt - np.arange(DE_W)
                A = r_mh[:, ts]
                best = np.full(n, np.inf)
                bl = est_lag.copy()
                for d_ in range(DE_MAX + 1):
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", RuntimeWarning)
                        e_ = np.nanmedian(np.abs(A - pred_hist[:, ts - d_]), axis=1)
                    better = np.isfinite(e_) & (e_ < best)
                    best = np.where(better, e_, best)
                    bl = np.where(better, d_, bl)
                est_lag = bl
            lag_hi = alive & (agl_true > 200.0)
            lag_sum += np.where(lag_hi, est_lag, 0.0)
            lag_n += lag_hi
        if use_ts or delay_est:   # time-stamped readings: compare with the prediction at the instant the reading was taken
            dsec = (draws.delay_steps if use_ts else est_lag) * DT
            xe = x_est[:, 0] - x_est[:, 3] * dsec
            ye = x_est[:, 1] - x_est[:, 4] * dsec
            ze = x_est[:, 2] - x_est[:, 5] * dsec
        else:
            xe, ye, ze = x_est[:, 0], x_est[:, 1], x_est[:, 2]
        if use_gest:
            hp = g_est.copy(); gx = np.zeros(n); gy = np.zeros(n)
        elif use_map and not missing:
            hp = mapq(xe, ye, allidx)
            gx, gy = mapg(xe, ye, allidx)
            if dy is not None:      # 6-DOF: predict the range along the ESTIMATED beam direction (footprint away from the nadir point)
                De1 = -dy.R_est()[:, :, 2]
                dxe, dye, cze = De1[:, 0], De1[:, 1], np.maximum(-De1[:, 2], 0.2)
                s_p1 = np.maximum(ze - hp, 1.0) / cze
                for _ in range(3):
                    s_p1 = np.clip((ze - mapq(xe + s_p1 * dxe, ye + s_p1 * dye, allidx)) / cze, 1.0, 1e5)
                gxf, gyf = mapg(xe + s_p1 * dxe, ye + s_p1 * dye, allidx)
                D1 = np.maximum(cze + gxf * dxe + gyf * dye, 0.1)
                hp = ze - s_p1 * cze
                gx, gy, hz = cze * gxf / D1, cze * gyf / D1, cze / D1
        else:
            hp = coarse.height(xe, ye)
            gx, gy = coarse.grad(xe, ye, step=400.0)
        H = np.zeros((n, 9)); H[:, 0] = -gx; H[:, 1] = -gy; H[:, 2] = 1.0 if dy is None or not (use_map and not missing) else hz
        r_pred = ze - hp
        nu = r_meas - r_pred
        R = (1.0 + 0.0015 * np.maximum(r_meas, 0)) ** 2
        Rg = np.maximum(R, s_hat ** 2) if v2 else R      # v2: noise level learned from accepted readings
        PHt = np.einsum("nij,nj->ni", nav.P, H)
        HPHt = np.einsum("ni,ni->n", H, PHt)
        S0 = HPHt + Rg
        sig_h = np.sqrt(np.maximum(nav.P[:, 0, 0], nav.P[:, 1, 1]))
        sig_z = np.sqrt(nav.P[:, 2, 2])
        accept = np.zeros(n, dtype=bool)
        R_use = R.copy()
        vo_mask = np.zeros(n, dtype=bool)        # ml2 diagnostic: rows whose update is vertical-only
        nu_use = nu.copy()
        decided = np.ones(n, dtype=bool)     # False while a reading is held in probation (counted later)
        gate_chi = nu * nu / S0
        flagged = avail & (gate_chi > CHI2_99 * wide_gate)
        rad = ellipse_k * sig_h
        if judge == "fixed":
            accept = avail & ~flagged
        elif judge == "pitfal":
            infl = np.where(flag_timer > 0, 10.0, 1.0)
            Rp = R * infl
            S = HPHt + Rp
            fl = avail & (nu * nu / S > CHI2_99)
            accept = avail & ~fl
            R_use = Rp
            flag_timer = np.where(fl, 40, np.maximum(flag_timer - 1, 0))
        elif judge == "tolerance":
            s_terr = stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2
            s_map = world.map_sigma ** 2
            R_t = R * mult ** 2 if oracle_R else R      # oracle: the true noise level (upper bound, not deployable)
            if tol_noise_floor:      # adaptive noise level: never trust the reading more than the running noise estimate
                floor2 = sig_diff ** 2 if tol_floor_source == "diff" else s_hat ** 2
                R_gate, R_upd = _floor_split(R_t, np.maximum(R_t, floor2), tol_floor_mode)
                S_tol = (S0 - R) + R_gate + s_terr + s_map
                R_use = R_upd + s_terr + s_map
            else:
                S_tol = (HPHt + R_t + s_terr + s_map) if oracle_R else (S0 + s_terr + s_map)
                R_use = R_t + s_terr + s_map
            chi_tol = nu * nu / S_tol
            accept = avail & (chi_tol <= gate_chi2)
            if imm:      # IMM-style: noise-level modes plus a fault mode, mixed by their posterior probability (one shared filter state)
                M2 = IMM_MULT ** 2
                base = HPHt + s_terr + s_map
                var_m = base[:, None] + R_t[:, None] * M2[None, :]
                lik = np.exp(-0.5 * nu[:, None] ** 2 / var_m) / np.sqrt(2.0 * np.pi * var_m)
                mu_pred = (1.0 - IMM_EPS) * imm_mu + IMM_EPS / len(IMM_MULT)
                num_m = (1.0 - IMM_PF) * mu_pred * lik
                num_f = IMM_PF / (2.0 * IMM_RANGE)
                p_f = num_f / np.maximum(num_m.sum(axis=1) + num_f, 1e-300)
                post = num_m / np.maximum(num_m.sum(axis=1, keepdims=True), 1e-300)
                accept = avail & (p_f < 0.5)
                R_use = (post * R_t[:, None] * M2[None, :]).sum(axis=1) + s_terr + s_map
                imm_mu = np.where((avail & accept)[:, None], post, imm_mu)
            if cusum:    # also reject while the CUSUM of normalised innovations is in alarm (slow drifts)
                zc = np.minimum(np.abs(nu) / np.sqrt(S_tol), 6.0)
                cs = np.where(avail, np.minimum(np.maximum(cs + zc - CUSUM_K, 0.0), 2.0 * CUSUM_H), cs)
                accept = accept & (cs <= CUSUM_H)
            if robust_t > 0:   # Student-t: no hard gate, heavy-tailed weight on every reading
                accept = avail.copy()
                R_use = R_use / _t_weight(chi_tol, robust_t)
            if chi_collect is not None:
                chi_collect.append(chi_tol[avail & ~fault_lbl])
        elif judge == "vbakf":
            # VB-AKF noise estimate (Sarkka & Nummenmaa 2009, Algorithm 1) for the scalar altimeter, in units of the nominal variance R
            s_terr = stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2
            s_map = world.map_sigma ** 2
            R_pred = np.maximum(1.0, vb_b / vb_a) * R
            S_tol = HPHt + R_pred + s_terr + s_map
            accept = avail & (nu * nu / S_tol <= CHI2_99)
            a_new = VBAKF_RHO * vb_a + 0.5
            b_pred = VBAKF_RHO * vb_b
            b_it = b_pred.copy()
            for _ in range(VBAKF_ITER):
                Rv = np.maximum(1.0, b_it / a_new) * R + s_terr + s_map
                Sv = HPHt + Rv
                b_it = b_pred + 0.5 * ((nu * Rv / Sv) ** 2 + HPHt * Rv / Sv) / R
            R_use = np.maximum(1.0, b_it / a_new) * R + s_terr + s_map
            vb_upd = avail & accept
            vb_a = np.where(vb_upd, a_new, vb_a)
            vb_b = np.where(vb_upd, b_it, vb_b)
            s_hat = np.sqrt(np.maximum(1.0, vb_b / vb_a) * R)
        elif judge in ("wait", "second", "ml", "ml2") or is_trust:
            if is_trust:
                s_terr = stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2
                S_tol = S0 + s_terr + world.map_sigma ** 2
                # step 1: physical possibility (lowest and highest ground within the uncertainty region)
                if not missing and opts["phys"]:
                    hmin = stats.hmin(x_est[:, 0], x_est[:, 1], rad + 30.0)
                    hmax = stats.hmax(x_est[:, 0], x_est[:, 1], rad + 30.0)
                    rmin = x_est[:, 2] - 3 * sig_z - hmax - 10.0
                    rmax = x_est[:, 2] + 3 * sig_z - hmin + 10.0
                    impossible = avail & ((r_meas < rmin) | (r_meas > rmax))
                else:
                    impossible = np.zeros(n, dtype=bool)
                gate_k = CHI2_99 if not missing else 10.83      # cautious mode: wider gate
                surprising = avail & ~impossible & (nu * nu / S_tol > gate_k)
                normal = avail & ~impossible & ~surprising
                R_normal = Rg + (s_terr + world.map_sigma ** 2) * 0.5
                accept = normal
                R_use = np.where(normal, R_normal, R)
                # impossible readings are rejected immediately (counted as decided rejections)
            else:
                surprising = flagged
                impossible = np.zeros(n, dtype=bool)
                normal = avail & ~flagged
                accept = normal
                if terrain_R:        # unflagged readings get the terrain + map variance, as tolerance / trust do
                    R_use = np.where(normal, R + (stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2 + world.map_sigma ** 2) * 0.5, R_use)
            if judge == "second":
                # second opinion: IMU/camera consistency. Accept a surprise only if the camera is trustworthy
                # (and the IMU shows no fall matching the jump); otherwise treat it as a fault.
                imu_rate = x_est[:, 5]
                alt_rate = np.where(np.isnan(last_valid_r), imu_rate, (r_meas - last_valid_r) / DT)
                step_jump = np.abs(alt_rate - imu_rate) > 20.0
                cam_trust = lit_cam_prev_ok
                acc2 = surprising & step_jump & cam_trust
                accept = accept | acc2
                R_use = np.where(acc2, R + stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2 + 9.0, R_use)
                surprising = np.zeros(n, dtype=bool)
            if judge == "ml":
                if ml2_terrain_R:      # diagnostic switch (default off), same as for ml2: terrain+map variance on unflagged readings
                    R_use = np.where(normal, R + (stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2 + world.map_sigma ** 2) * 0.5, R_use)
                if np.any(surprising):
                    feats = _features(nu, S0, R, stats, x_est, rad, agl_true=r_meas, nu_hist=nu_hist)
                    isfault = np.zeros(n, dtype=bool)
                    si = np.nonzero(surprising)[0]
                    if ml_model is not None:
                        isfault[si] = ml_model.predict(feats[si]).astype(bool)
                    acc2 = surprising & ~isfault
                    accept = accept | acc2
                    R_use = np.where(acc2, R + stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2 + 9.0, R_use)
                surprising = np.zeros(n, dtype=bool)
            if judge == "ml2":
                if ml2_terrain_R:
                    R_use = np.where(normal, R + (stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2 + world.map_sigma ** 2) * 0.5, R_use)
                if ml2_noise_model is not None and ml2_noise_normal and normal.any():
                    # exploratory: also apply the error-size model to UNFLAGGED readings (the model was trained on flagged rows only)
                    nm = ml2_noise_model["model"] if isinstance(ml2_noise_model, dict) else ml2_noise_model
                    ni = np.nonzero(normal)[0]
                    fa = MF.features_v3(nu, S0, R, stats, x_est, rad, r_meas, nu_hist, z_buf)
                    s_n = np.sqrt(R[ni]) * np.expm1(np.clip(nm.predict(fa[ni]), 0.0, 7.0)) * ml2_noise_scale
                    R_use[ni] = np.maximum(R_use[ni], s_n ** 2)
                if ml2_rule_gate and np.any(surprising):
                    # EXPERIMENTAL non-ML replacement for the classifier: tolerance-style gate whose noise level adapts (s_hat)
                    s_terr2 = stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2
                    S_ad = (S0 - R) + np.maximum(R, s_hat ** 2) + s_terr2 + world.map_sigma ** 2
                    acc2 = surprising & (nu * nu / S_ad <= CHI2_99)
                    R_use = np.where(acc2, R + s_terr2 + 9.0, R_use)
                    accept = accept | acc2
                    vo_mask = acc2.copy()
                elif np.any(surprising):
                    si = np.nonzero(surprising)[0]
                    mdl = ml_model["model"] if isinstance(ml_model, dict) else ml_model
                    feats = MF.features_v3(nu, S0, R, stats, x_est, rad, r_meas, nu_hist, z_buf)
                    p_fault = np.ones(n)
                    if mdl is not None:
                        p_fault[si] = mdl.predict_proba(feats[si])[:, 1]
                    r_terr = R + stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2 + 9.0
                    if ml2_noise_model is not None:
                        # predicted error size -> variance floor (models/err_reg_v3.pkl; s = sigma_nominal * expm1(t_hat) * scale)
                        nm = ml2_noise_model["model"] if isinstance(ml2_noise_model, dict) else ml2_noise_model
                        t_hat = np.clip(nm.predict(feats[si]), 0.0, 7.0)
                        s_pred = np.sqrt(R[si]) * np.expm1(t_hat) * ml2_noise_scale
                        r_terr = r_terr.copy()
                        r_terr[si] = np.maximum(r_terr[si], s_pred ** 2)
                    if ml2_mode == "hard":
                        acc2 = surprising & (p_fault <= ml2_threshold)
                        R_use = np.where(acc2, r_terr, R_use)
                    else:   # soft: keep the reading but trust it less the more likely it is a fault
                        acc2 = surprising
                        R_use = np.where(acc2, r_terr / np.maximum(1.0 - p_fault, 0.01) ** 2, R_use)
                    accept = accept | acc2
                    vo_mask = acc2.copy()
                if ml2_noise_heuristic:   # non-ML control: running innovation-size estimate (trust v2's rule) instead of the learned error model
                    R_use = np.where(accept, np.maximum(R_use, s_hat ** 2), R_use)
                surprising = np.zeros(n, dtype=bool)
            # --- probation for the remaining surprising readings
            if judge == "wait" or (is_trust and opts["prob"]):
                in_prob = prob.n > 0
                start = surprising & ~in_prob
                prob.n[start] = 0
                feed = (surprising | in_prob) & avail
                idxf = np.nonzero(feed)[0]
                if idxf.size:
                    slot = prob.n[idxf]
                    prob.buf[idxf, slot] = nu[idxf]
                    prob.Rbuf[idxf, slot] = Rg[idxf]
                    prob.fault[idxf, slot] = fault_lbl[idxf]
                    prob.n[idxf] = slot + 1
                decided = ~feed
                done = prob.n >= K_prob
                if done.any():
                    di = np.nonzero(done)[0]
                    mean = prob.buf[di].mean(axis=1)
                    std = prob.buf[di].std(axis=1)
                    sig = np.sqrt(prob.Rbuf[di].mean(axis=1))
                    consistent = std <= sigma_probation * sig + 1e-6
                    # counted at resolution time
                    nvalid = (~prob.fault[di]).sum(axis=1)
                    nfault = prob.fault[di].sum(axis=1)
                    acc_runs = di[consistent]
                    rej_runs = di[~consistent]
                    res["valid_total"][di] += nvalid
                    res["fault_total"][di] += nfault
                    res["valid_rej"][rej_runs] += nvalid[~consistent]
                    res["fault_acc"][acc_runs] += nfault[consistent]
                    # accept: single update with the mean innovation, then reset
                    if acc_runs.size:
                        m = np.zeros(n, dtype=bool); m[acc_runs] = True
                        nu_use = nu.copy(); nu_use[acc_runs] = mean[consistent]
                        Rr = Rg + stats.hstd(x_est[:, 0], x_est[:, 1], rad) ** 2 * 0.5
                        _scalar_update(nav.x, nav.P, H, nu_use, Rr, m)
                        if v2:
                            s_hat[acc_runs] = np.maximum(s_hat[acc_runs], std[consistent])
                        if use_gest:
                            g_est[acc_runs] = nav.x[acc_runs, 2] - (r_pred[acc_runs] + mean[consistent])
                            r_f[acc_runs] = r_pred[acc_runs] + mean[consistent]
                    prob.n[done] = 0
        # ---------------- bookkeeping + ordinary update ----------------
        direct = avail & decided
        res["valid_total"] += (direct & ~fault_lbl)
        res["fault_total"] += (direct & fault_lbl)
        rej = direct & ~accept
        res["valid_rej"] += (rej & ~fault_lbl)
        res["fault_acc"] += (direct & accept & fault_lbl)
        if ml2_vertical_only and judge == "ml2":
            Hv = H.copy(); Hv[:, 0] = 0.0; Hv[:, 1] = 0.0
            _scalar_update(nav.x, nav.P, H, nu_use, R_use, direct & accept & ~vo_mask)
            _scalar_update(nav.x, nav.P, Hv, nu_use, R_use, direct & accept & vo_mask)
        else:
            _scalar_update(nav.x, nav.P, H, nu_use, R_use, direct & accept)
        upd = direct & accept
        if alt2:      # second, dissimilar altimeter (ASSUMED): 3x noise, independent faults, no dropout; plain tolerance gate
            a2 = draws.alt2(scen)
            sig2 = ALT2_MULT * sig_nom * mult
            r2 = r_true + a2.g[:, tt] * sig2 + np.where(a2.burst[:, tt], a2.bias[:, tt], 0.0)
            av2 = alive & (agl_true < 20000.0)
            hp2 = mapq(nav.x[:, 0], nav.x[:, 1], allidx)
            gx2, gy2 = mapg(nav.x[:, 0], nav.x[:, 1], allidx)
            H2 = np.zeros((n, 9)); H2[:, 0] = -gx2; H2[:, 1] = -gy2; H2[:, 2] = 1.0
            nu2 = r2 - (nav.x[:, 2] - hp2)
            HPH2 = np.einsum("ni,nij,nj->n", H2, nav.P, H2)
            R2 = (ALT2_MULT * (1.0 + 0.0015 * np.maximum(r2, 0)) * mult) ** 2
            st2 = stats.hstd(nav.x[:, 0], nav.x[:, 1], rad) ** 2 + world.map_sigma ** 2
            ok2 = av2 & (nu2 * nu2 / (HPH2 + R2 + st2) <= gate_chi2)
            _scalar_update(nav.x, nav.P, H2, nu2, R2 + st2, ok2)
        if map_search:
            rej_ema = np.where(direct, 0.95 * rej_ema + 0.05 * (~accept), rej_ema)
            r_mh[:, tt] = np.where(avail, r_meas, np.nan)
            x_hist[:, tt], y_hist[:, tt], z_hist[:, tt] = x_est[:, 0], x_est[:, 1], x_est[:, 2]
            if tt >= MS_W * MS_STEP + 20 and tt % MS_EVERY == 0:
                trig = np.nonzero(alive & (rej_ema > 0.5))[0]
                if trig.size:
                    ts = tt - MS_STEP * np.arange(MS_W)
                    rm, xs_, ys_, zs_ = r_mh[trig][:, ts], x_hist[trig][:, ts], y_hist[trig][:, ts], z_hist[trig][:, ts]

                    def score(hx, hy):
                        hh = np.empty(xs_.shape)
                        bid = draws.map_bank[trig]
                        for b_ in np.unique(bid):
                            mm = bid == b_
                            hh[mm] = banks[b_].height(xs_[mm] - shift[trig[mm], 0][:, None] + (scen.wrong_offset_m if wrong else 0.0) - hx[mm][:, None],
                                                      ys_[mm] - shift[trig[mm], 1][:, None] - hy[mm][:, None])
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", RuntimeWarning)
                            dres = rm - (zs_ - hh)
                            return np.nanmedian(np.abs(dres - np.nanmedian(dres, axis=1)[:, None]), axis=1)    # altitude bias removed

                    cur = score(est_off[trig, 0], est_off[trig, 1])
                    best = np.full(trig.size, np.inf)
                    bx, by = np.zeros(trig.size), np.zeros(trig.size)
                    grid = [(hx_, hy_) for hx_ in np.arange(-MS_SPAN, MS_SPAN + 1.0, 500.0) for hy_ in np.arange(-MS_SPAN, MS_SPAN + 1.0, 500.0)]
                    gsc = np.full((len(grid), trig.size), np.inf)
                    for gi, (hx_, hy_) in enumerate(grid):
                        sc_ = score(np.full(trig.size, hx_), np.full(trig.size, hy_))
                        gsc[gi] = np.where(np.isfinite(sc_), sc_, np.inf)
                        bt = gsc[gi] < best
                        best = np.where(bt, gsc[gi], best); bx = np.where(bt, hx_, bx); by = np.where(bt, hy_, by)
                    gxy = np.array(grid)
                    far = np.hypot(gxy[:, 0][:, None] - bx[None, :], gxy[:, 1][:, None] - by[None, :]) > 750.0
                    second = np.where(far, gsc, np.inf).min(axis=0)      # best hypothesis away from the winner: the winner must stand out
                    cx, cy = bx.copy(), by.copy()
                    for dx_ in np.arange(-375.0, 376.0, 125.0):
                        for dy_ in np.arange(-375.0, 376.0, 125.0):
                            sc_ = score(bx + dx_, by + dy_)
                            bt = np.isfinite(sc_) & (sc_ < best)
                            best = np.where(bt, sc_, best); cx = np.where(bt, bx + dx_, cx); cy = np.where(bt, by + dy_, cy)
                    track_m = np.hypot(xs_[:, 0] - xs_[:, -1], ys_[:, 0] - ys_[:, -1])          # the window must cover enough ground to identify an offset
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", RuntimeWarning)
                        sig_w = np.nanmedian(1.0 + 0.0015 * np.maximum(rm, 0.0), axis=1)
                    adopt = (np.isfinite(best) & np.isfinite(cur) & (best < 0.5 * cur) & (best < 3.0 * sig_w + 3.0) & (best < 0.6 * second)
                             & (track_m > 600.0))
                    if adopt.any():
                        est_off[trig[adopt], 0], est_off[trig[adopt], 1] = cx[adopt], cy[adopt]
                        rej_ema[trig[adopt]] = 0.0
        if v2 or (judge == "ml2" and ml2_noise_heuristic) or (judge == "tolerance" and tol_noise_floor):
            s_hat = np.where(upd, 0.97 * s_hat + 0.03 * np.minimum(np.abs(nu) * 1.25, 6.0 * s_hat + 1.0), s_hat)
        if tol_floor_source == "diff":      # robust second-difference noise level of the range sequence (no map involved)
            rbuf = np.concatenate([rbuf[:, 1:], np.where(avail, r_meas, np.nan)[:, None]], axis=1)
            dbuf[:, tt % DIFF_WINDOW] = np.abs(rbuf[:, 2] - 2.0 * rbuf[:, 1] + rbuf[:, 0])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)      # all-NaN rows (no data yet) give NaN
                med = np.nanmedian(dbuf, axis=1)
            sig_diff = np.where(np.isfinite(med), 1.4826 * med / np.sqrt(6.0), 0.0)
        res["s_hat_max"] = np.maximum(res["s_hat_max"], s_hat if tol_floor_source != "diff" else sig_diff)
        if use_gest:
            e_ab = r_meas - r_f
            g_est = np.where(upd, nav.x[:, 2] - r_meas, g_est)
            r_f = np.where(upd, r_f + 0.5 * e_ab, r_f)
            rate_f = np.where(upd, rate_f + 0.05 * e_ab / DT, rate_f)
        if collect is not None and judge == "pitfal":
            fl = avail & (gate_chi > CHI2_99)
            if fl.any():
                fi = np.nonzero(fl)[0]
                feats = _features(nu, S0, R, stats, x_est, ellipse_k * sig_h, agl_true=r_meas, nu_hist=nu_hist)
                collect.append((feats[fi], fault_lbl[fi]))
        nu_hist = np.concatenate([nu_hist[:, 1:], (nu / np.sqrt(S0))[:, None]], axis=1)
        if judge == "ml2":
            z_buf = MF.push_history(z_buf, flagged, nu / np.sqrt(S0))
        last_valid_r = np.where(direct & accept, r_meas, last_valid_r)
        # ---------------- camera ----------------
        if tt % cam_period == 0:
            sel = alive & (agl_true < 12000.0)
            r_foot = np.clip(agl_true * 0.36, 60, 3840)
            lit_true = world.true_lit.litfrac(p[:, 0], p[:, 1], r_foot)
            agl_for = np.maximum(agl_true, 0)
            sig_n = 20.0 + 0.004 * agl_for
            bad = (1.0 - lit_true)
            sig_a = sig_n * (1.0 + scen.cam_sig_gain * bad ** 2)
            if scen.cam_model == "empirical":
                cm = _cam_model()
                pos = np.searchsorted(cm["lit"], lit_true)
                kk = 15
                idx = np.clip(pos + np.floor((draws.cam_u[:, cam_i] - 0.5) * 2 * kk).astype(int), 0, len(cm["lit"]) - 1)
                meas = p[:, 0:2] + shift + np.stack([cm["rex"][idx], -cm["rez"][idx]], axis=1) * agl_for[:, None]
            else:
                idx = None
                meas = p[:, 0:2] + shift + scen.cam_bias_gain * draws.cam_bias * (bad ** 2)[:, None] + draws.cam_g[:, cam_i, :] * sig_a[:, None]
            Rc = sig_n ** 2
            if cam_soft and scen.cam_model == "empirical":
                Rc = np.maximum(Rc, (cm["sigrel"][idx] * agl_for) ** 2)
            use = sel.copy()
            wgt = np.ones(n)
            if cam_use_conf and scen.cam_model == "empirical":
                use &= cm["peak"][idx] >= 0.5          # matcher confidence gate (fixed a priori)
            if cam_use_aware:
                lit_pred = stats.litfrac(x_est[:, 0], x_est[:, 1], np.clip(np.maximum(x_est[:, 2] - hp, 0) * 0.36, 60, 3840))
                if missing:     # no map: lit fraction unknown, use the camera as a cautious cross-check
                    lit_pred = np.ones(n)
                use &= lit_pred >= 0.25
                wgt = np.where(lit_pred >= 0.25, np.clip(lit_pred, 0.25, 1.0) ** 2, 0.0)
                if missing:
                    wgt = np.where(use, 0.5, 0.0)
                Rc = Rc / np.maximum(wgt, 1e-3)
                if judge == "second":
                    pass
            for ax in (0, 1):
                Hc = np.zeros((n, 9)); Hc[:, ax] = 1.0
                _scalar_update(nav.x, nav.P, Hc, meas[:, ax] - nav.x[:, ax], Rc, use)
            lit_cam_prev_ok = ((meas - nav.x[:, 0:2]) ** 2).sum(axis=1) < 9.0 * (Rc * 2 + 400.0)
            wgt_used = wgt if cam_use_aware else np.ones(n)
            last_cam_w = np.where(use, wgt_used, 0.0)
            shadow = sel & (lit_true < 0.3)
            res["cam_w_sum"] += np.where(shadow, np.where(use, wgt_used, 0.0), 0.0)
            res["cam_w_n"] += shadow
            cam_i += 1
        # ---------------- live scan (extension) ----------------
        if scan and judge in ("trust_scan", "trust2_scan") and tt % scan_period == 0 and scen.scan_ok:
            cell = np.maximum(8.0, 0.0185 * np.maximum(agl_true, 0))
            sel = alive & (agl_true > 80.0) & (agl_true < 2500.0)
            rough = world.true_lit.hstd(p[:, 0], p[:, 1], 150.0)
            sel &= rough > 1.5
            sig_s = np.maximum(4.0, 0.8 * cell)
            meas = p[:, 0:2] + shift + draws.scan_g[:, scan_i, :] * sig_s[:, None]
            # three-way check: scan fix vs estimate; distrust a scan that disagrees wildly with a confident estimate
            dpos = np.hypot(meas[:, 0] - nav.x[:, 0], meas[:, 1] - nav.x[:, 1])
            sig_pos = np.sqrt(np.maximum(nav.P[:, 0, 0], nav.P[:, 1, 1]) + sig_s ** 2)
            ok_scan = sel & (dpos < 4.0 * sig_pos + 50.0)
            for ax in (0, 1):
                Hc = np.zeros((n, 9)); Hc[:, ax] = 1.0
                _scalar_update(nav.x, nav.P, Hc, meas[:, ax] - nav.x[:, ax], sig_s ** 2, ok_scan)
            scan_i += 1
        # ---------------- metrics ----------------
        res["alt_sq"] += np.where(alive, (agl_b - agl_true) ** 2, 0.0)
        res["alt_n"] += alive
        res["z_sq"] += np.where(alive, (nav.x[:, 2] - p[:, 2]) ** 2, 0.0)
        e3 = nav.x[:, 0:3] - p
        res["nees_sum"] += np.where(alive, np.einsum("ni,ni->n", e3, np.linalg.solve(nav.P[:, 0:3, 0:3] + 1e-9 * np.eye(3), e3[:, :, None])[:, :, 0]), 0.0)
        if rec is not None and (alive[record_idx] or contact[record_idx]):
            i = record_idx
            rec["t"].append(t + DT)
            rec["x"].append(p[i, 0]); rec["y"].append(p[i, 1]); rec["z"].append(p[i, 2])
            rec["ex"].append(nav.x[i, 0]); rec["ey"].append(nav.x[i, 1]); rec["ez"].append(nav.x[i, 2])
            rec["agl_true"].append(agl_true[i]); rec["agl_est"].append(nav.x[i, 2] - hp[i])
            rec["gate"].append(3.0 * np.sqrt(S0[i])); rec["acc"].append(float(direct[i] & accept[i]))
            rec["r"].append(r_meas[i]); rec["fault"].append(float(fault_lbl[i])); rec["fuel"].append(fuel[i])
            rec["tgt_x"].append(target[i, 0]); rec["tgt_y"].append(target[i, 1])
            rec["cam_w"].append(float(last_cam_w[i])); rec["prob"].append(float(prob.n[i] > 0)); rec["s_hat"].append(float(sig_diff[i] if tol_floor_source == "diff" else s_hat[i]))
    # runs still alive at the end: timeout
    left = alive
    res["outcome"][left] = "timeout"
    res["fuel_left"][left] = fuel[left]
    res["t_end"][left] = T * DT
    res["rec"] = rec
    res["est_lag"] = lag_sum / np.maximum(lag_n, 1.0)    # round 5: delay estimate averaged over the descent above 200 m (steps) and map-offset-search output (m)
    res["est_off_x"], res["est_off_y"] = est_off[:, 0].copy(), est_off[:, 1].copy()
    if dy is not None:
        res["tilt_max"] = dy.tilt_max.copy()
        res["att_err_rms_deg"] = np.sqrt(dy.att_sq / np.maximum(dy.att_n, 1.0))
        res["rcs_fuel"] = dy.rcs_used.copy()
    return res


def _features(nu, S0, R, stats, x_est, rad, agl_true, nu_hist):
    sd = np.sqrt(S0)
    return np.stack([
        nu / sd, nu, stats.hstd(x_est[:, 0], x_est[:, 1], rad), stats.hmax(x_est[:, 0], x_est[:, 1], rad) - stats.hmin(x_est[:, 0], x_est[:, 1], rad),
        np.abs(nu) / np.sqrt(R), np.abs(nu_hist).mean(axis=1), agl_true / 1000.0, rad], axis=1)


def _find_divert(world, track):
    """Nearest flat spot ~2 km from the target (for the mid-descent divert test)."""
    from scipy.ndimage import maximum_filter
    z = world.dem_grid.z
    px = world.px
    gy, gx = np.gradient(z, px)
    sl = maximum_filter(np.degrees(np.arctan(np.hypot(gx, gy))), size=7)
    tx, ty = track["target"]
    yy, xx = np.mgrid[0:z.shape[0], 0:z.shape[1]]
    d = np.hypot(xx * px - tx, yy * px - ty)
    ok = (sl < 5.0) & (d > 1800) & (d < 3200)
    if not ok.any():
        return (tx + 1500.0, ty)
    i = np.argmin(np.where(ok, d, 1e9))
    iy, ix = divmod(i, z.shape[1])
    return (ix * px, iy * px)


def summarize(res):
    n = len(res["success"])
    out = {}
    out["n"] = n
    out["success_pct"] = 100.0 * res["success"].mean()
    k = int(res["success"].sum())
    p = k / n
    z = 1.96
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    out["success_lo"] = 100 * (centre - half)
    out["success_hi"] = 100 * (centre + half)
    nz = np.maximum(res["alt_n"], 1)
    out["alt_rms_m"] = float(np.sqrt(np.mean(res["alt_sq"] / nz)))
    out["z_rms_m"] = float(np.sqrt(np.mean(res["z_sq"] / nz)))
    vt = res["valid_total"].sum()
    out["false_rej_pct"] = float(100 * res["valid_rej"].sum() / max(vt, 1))
    ft = res["fault_total"].sum()
    out["missed_fault_pct"] = float(100 * res["fault_acc"].sum() / max(ft, 1)) if ft > 0 else float("nan")
    cw = res["cam_w_n"].sum()
    out["cam_weight_in_shadow"] = float(res["cam_w_sum"].sum() / cw) if cw > 0 else float("nan")
    landed = res["outcome"] == "landed"
    out["fuel_left_kg"] = float(np.mean(res["fuel_left"]))
    out["fuel_left_landed_kg"] = float(np.mean(res["fuel_left"][landed])) if landed.any() else float("nan")
    out["touchdown_miss_m_median"] = float(np.median(res["miss_m"][res["t_end"] > 0]))
    for o in ("landed", "crash", "rough", "timeout"):
        out[f"outcome_{o}"] = int((res["outcome"] == o).sum())
    return out
