"""Batched lunar-descent simulator: truth physics, sensors with faults, EKF with pluggable altimeter judges.

All state arrays have a leading run axis N so hundreds of descents run in lock-step with numpy.
Every judge sees identical truth-independent noise (common random numbers), see Draws.
"""
from dataclasses import dataclass, field
import numpy as np

G = 1.62
G0 = 9.80665
CHI2_99 = 6.635          # 1-dof 99 % gate
DT = 0.25


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
    return _CAM


class Draws:
    """Pre-drawn random numbers shared by all judges (same descents, noise and faults for everyone)."""

    def __init__(self, world, scen, n, seed, t_max=None):
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
             record_idx=None, sigma_probation=3.0, K_prob=10, ellipse_k=2.0, wide_gate=1.0, cam_policy=None, timestamps=None):
    """Run all N descents for one judge. Returns a dict of per-run result arrays (+ optional recorded traces)."""
    veh = veh or Vehicle()
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
                                    "cam_w_sum", "cam_w_n", "z_final_true_agl"]}
    res["success"] = np.zeros(n, dtype=bool)
    res["outcome"] = np.array(["flying"] * n, dtype=object)
    rec = None
    if record_idx is not None:
        rec = {k: [] for k in ["t", "x", "y", "z", "ex", "ey", "ez", "agl_true", "agl_est", "gate", "acc", "r", "fault", "fuel", "tgt_x", "tgt_y", "cam_w", "prob", "s_hat"]}
    r_hist = np.zeros((n, T), dtype=np.float32)
    last_valid_r = np.full(n, np.nan)
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
    ml_feat_all = []

    def mapq(x, y, idx):
        """Onboard map height at estimated map-frame position (registration shift applied)."""
        out = np.empty(len(idx), dtype=np.float64)
        bank_ids = draws.map_bank[idx]
        for b in np.unique(bank_ids):
            m = bank_ids == b
            g = banks[b]
            out[m] = g.height(x[m] - shift[idx[m], 0] + (2000.0 if wrong else 0.0), y[m] - shift[idx[m], 1])
        return out

    def mapg(x, y, idx):
        gx = np.empty(len(idx)); gy = np.empty(len(idx))
        bank_ids = draws.map_bank[idx]
        for b in np.unique(bank_ids):
            m = bank_ids == b
            gxm, gym = banks[b].grad(x[m] - shift[idx[m], 0] + (2000.0 if wrong else 0.0), y[m] - shift[idx[m], 1], step=40.0)
            gx[m], gy[m] = gxm, gym
        return gx, gy

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
        am = np.linalg.norm(a_cmd, axis=1)
        burn = mass * am / (veh.isp * G0) * DT
        fuel = np.maximum(0.0, fuel - burn * alive)
        acc = a_cmd + np.array([0, 0, -G])
        p_new = p + v * DT + 0.5 * acc * DT * DT
        v_new = v + acc * DT
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
            res["success"][ci] = ok
            res["outcome"][ci] = np.where(ok, "landed", np.where(res["impact_vz"][ci] > 2.0, "crash", "rough"))
            touched[ci] = True
            alive[ci] = False
        p = np.where(alive[:, None], p_new, p)
        v = np.where(alive[:, None], v_new, v)
        # ---------------- IMU + EKF predict ----------------
        a_meas = a_cmd + draws.bias_true + 0.003 * draws.imu_g[:, k, :]
        nav.predict(a_meas)
        x_est = nav.x
        tt = k + 1
        # ---------------- altimeter ----------------
        ht = truth.height(p[:, 0], p[:, 1])
        agl_true = p[:, 2] - ht
        r_true = agl_true
        r_hist[:, tt] = r_true
        d_idx = np.maximum(tt - draws.delay_steps, 0)
        r_src = r_hist[allidx, d_idx]
        sig_nom = 1.0 + 0.0015 * np.maximum(r_src, 0)
        mult = np.ones(n)
        if scen.noise_mult_agl > 0:
            mult = np.where(agl_true < scen.noise_mult_agl, scen.noise_mult_below_agl, 1.0)
        r_meas = r_src + draws.alt_g[:, tt] * sig_nom * mult
        burst = draws.burst[:, tt]
        r_meas = r_meas + np.where(burst, draws.burst_bias[:, tt], 0.0)
        avail = alive & (agl_true < 20000.0)
        if scen.dropout_agl > 0:
            avail &= agl_true > scen.dropout_agl
        fault_lbl = np.abs(r_meas - r_true) > 5.0 * (1.0 + 0.0015 * np.maximum(r_true, 0)) + 1.0
        # judge prediction surface
        if use_ts:   # time-stamped readings: compare with the prediction at the instant the reading was taken
            dsec = draws.delay_steps * DT
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
        else:
            hp = coarse.height(xe, ye)
            gx, gy = coarse.grad(xe, ye, step=400.0)
        H = np.zeros((n, 9)); H[:, 0] = -gx; H[:, 1] = -gy; H[:, 2] = 1.0
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
            S_tol = S0 + s_terr + s_map
            accept = avail & (nu * nu / S_tol <= CHI2_99)
            R_use = R + s_terr + s_map
        elif judge in ("wait", "second", "ml") or is_trust:
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
        _scalar_update(nav.x, nav.P, H, nu_use, R_use, direct & accept)
        upd = direct & accept
        if v2:
            s_hat = np.where(upd, 0.97 * s_hat + 0.03 * np.minimum(np.abs(nu) * 1.25, 6.0 * s_hat + 1.0), s_hat)
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
        if rec is not None and (alive[record_idx] or contact[record_idx]):
            i = record_idx
            rec["t"].append(t + DT)
            rec["x"].append(p[i, 0]); rec["y"].append(p[i, 1]); rec["z"].append(p[i, 2])
            rec["ex"].append(nav.x[i, 0]); rec["ey"].append(nav.x[i, 1]); rec["ez"].append(nav.x[i, 2])
            rec["agl_true"].append(agl_true[i]); rec["agl_est"].append(nav.x[i, 2] - hp[i])
            rec["gate"].append(3.0 * np.sqrt(S0[i])); rec["acc"].append(float(direct[i] & accept[i]))
            rec["r"].append(r_meas[i]); rec["fault"].append(float(fault_lbl[i])); rec["fuel"].append(fuel[i])
            rec["tgt_x"].append(target[i, 0]); rec["tgt_y"].append(target[i, 1])
            rec["cam_w"].append(float(last_cam_w[i])); rec["prob"].append(float(prob.n[i] > 0)); rec["s_hat"].append(float(s_hat[i]))
    # runs still alive at the end: timeout
    left = alive
    res["outcome"][left] = "timeout"
    res["fuel_left"][left] = fuel[left]
    res["t_end"][left] = T * DT
    res["rec"] = rec
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
