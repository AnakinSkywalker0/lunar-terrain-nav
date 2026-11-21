"""Six-degree-of-freedom rigid-body lander dynamics for the batched engine (round 6; exploratory, default off).

The 3-DOF engine applies the commanded acceleration vector instantly.  Here the vehicle has ONE main engine fixed along the body +z axis:
thrust acts only along that axis, so a horizontal acceleration needs a tilt, and a tilt needs reaction-control torque, which is limited.
Modelled: throttle lag, attitude (quaternion) and body rate, a PD+I attitude controller with a torque limit, inertia that follows the mass,
thrust misalignment and centre-of-mass offset (disturbance torque), a gyro and star-tracker attitude estimate, strapdown rotation of the
accelerometer into the world frame with the ESTIMATED attitude, body-fixed altimeter beams, reaction-control propellant.
NOT modelled: fuel slosh, structural flex, engine start-up/shut-down transients, plume effects, landing-gear crush, yaw coupling to the guidance.

Every number below is ASSUMED (typical of a small lunar lander of this mass; none is taken from a real vehicle) unless stated otherwise.
Random numbers come from a separate generator seeded from the Draws seed, so all judges see the same vehicle imperfections (common random numbers).
"""
from dataclasses import dataclass

import numpy as np

G = 1.62          # lunar gravity (m/s^2); same as engine.G (not imported to keep this module self-contained)
G0 = 9.80665


@dataclass(frozen=True)
class Dyn6Config:
    sub: int = 5                       # integration substeps per engine step (0.25 s / 5 = 0.05 s)
    tau_thr: float = 0.3               # throttle first-order lag (s)
    tmin_frac: float = 0.0             # deepest throttle as a share of maximum thrust (0 = may idle; real engines have a floor)
    torque_max: float = 800.0          # reaction-control torque limit per body axis (N m)
    gyr2: tuple = (1.3, 1.3, 1.1)      # (radius of gyration)^2 about body x, y, z (m^2): inertia = mass * gyr2
    wn: float = 1.0                    # attitude loop natural frequency (rad/s)
    zeta: float = 0.9                  # attitude loop damping
    ki: float = 0.15                   # integral gain (1/s) on the tilt error (cancels the steady disturbance torque)
    misalign_deg: float = 0.15         # thrust-vector misalignment, 1 sigma per axis (deg)
    com_offset_m: float = 0.02         # centre-of-mass lateral offset, 1 sigma per axis (m)
    thr_arm_m: float = 1.5             # distance of the engine below the centre of mass (m)
    gyro_bias_dps: float = 0.005       # gyro constant bias, 1 sigma (deg/s)
    gyro_noise_rps: float = 0.0005     # gyro noise per engine step, 1 sigma (rad/s)
    st_period_s: float = 2.0           # star-tracker update period (s)
    st_sigma_deg: float = 0.02         # star-tracker attitude error, 1 sigma per axis (deg)
    st_gain: float = 0.5               # share of the tracker-minus-gyro difference applied at each update
    rcs_arm_m: float = 1.5             # reaction-control thruster lever arm (m)
    rcs_isp: float = 220.0             # reaction-control specific impulse (s)
    tilt_land_max_deg: float = 12.0    # touchdown tilt from vertical above which the vehicle is counted as tipping over
    rate_land_max_dps: float = 5.0     # touchdown body rate above which the landing is counted as rough
    hold_acc: float = 0.05             # below this commanded acceleration (m/s^2) the previous thrust direction is held
    tilt_cmd_max_deg: float = 35.0     # guidance may not command a thrust direction further than this from vertical


# ---- quaternion helpers; q = [w, x, y, z], body-to-world, shape (n, 4) ----
def qmul(a, b):
    w1, x1, y1, z1 = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    w2, x2, y2, z2 = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    return np.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], axis=1)


def qconj(q):
    return q * np.array([1.0, -1.0, -1.0, -1.0])


def qnorm(q):
    return q / np.linalg.norm(q, axis=1, keepdims=True)


def rotvec_to_q(v):
    """Quaternion of the rotation vector v (n, 3), exact for any size."""
    a = np.linalg.norm(v, axis=1)
    half = 0.5 * a
    k = np.where(a > 1e-9, np.sin(half) / np.maximum(a, 1e-12), 0.5)
    return np.concatenate([np.cos(half)[:, None], v * k[:, None]], axis=1)


def q_to_rotvec(q):
    q = np.where(q[:, :1] < 0, -q, q)
    s = np.linalg.norm(q[:, 1:], axis=1)
    ang = 2.0 * np.arctan2(s, q[:, 0])
    return q[:, 1:] * (ang / np.maximum(s, 1e-12))[:, None]


def q_to_matrix(q):
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((len(q), 3, 3))
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - w * z); R[:, 0, 2] = 2 * (x * z + w * y)
    R[:, 1, 0] = 2 * (x * y + w * z); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - w * x)
    R[:, 2, 0] = 2 * (x * z - w * y); R[:, 2, 1] = 2 * (y * z + w * x); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def q_from_z_axis(d):
    """Attitude whose body +z axis points along the unit vector d (minimal rotation from world +z; no yaw)."""
    cross = np.stack([-d[:, 1], d[:, 0], np.zeros(len(d))], axis=1)
    q = np.concatenate([(1.0 + d[:, 2])[:, None], cross], axis=1)
    q[np.linalg.norm(q, axis=1) < 1e-9] = [0.0, 1.0, 0.0, 0.0]
    return qnorm(q)


def command_from_accel(a_cmd, cfg):
    """Guidance acceleration vector -> (unit thrust direction, thrust acceleration magnitude), with the thrust direction kept inside a cone of
    cfg.tilt_cmd_max_deg around vertical. Inside the cone the thrust equals |a_cmd|; outside it the vertical acceleration the guidance asked
    for is kept and the rest of the horizontal part is dropped."""
    ahm = np.hypot(a_cmd[:, 0], a_cmd[:, 1])
    az = a_cmd[:, 2]
    tilt_c = np.arctan2(ahm, np.maximum(az, 0.0))               # commanded angle from vertical (0 to 90 deg)
    cap = np.deg2rad(cfg.tilt_cmd_max_deg)
    tc = np.minimum(tilt_c, cap)
    hdir = a_cmd[:, :2] / np.maximum(ahm, 1e-9)[:, None]
    zd = np.concatenate([np.sin(tc)[:, None] * hdir, np.cos(tc)[:, None]], axis=1)
    amag = np.where(tilt_c > cap, np.maximum(az, 0.0) / np.cos(cap), np.hypot(ahm, az))
    return zd, amag


class Dyn6:
    """Batched 6-DOF state for n descents."""

    def __init__(self, cfg, n, seed, dir0):
        self.cfg, self.n = cfg, n
        rng = np.random.default_rng([int(seed), 6006])
        self.rng = rng
        self.q = q_from_z_axis(dir0)
        self.w = np.zeros((n, 3))
        self.thrust = np.zeros(n)
        self.ie = np.zeros((n, 2))
        self.zd = dir0.copy()
        self.mis = rng.standard_normal((n, 2)) * np.deg2rad(cfg.misalign_deg)
        self.com = rng.standard_normal((n, 2)) * cfg.com_offset_m
        self.gbias = rng.standard_normal((n, 3)) * np.deg2rad(cfg.gyro_bias_dps)
        self.q_est = qnorm(qmul(self.q, rotvec_to_q(rng.standard_normal((n, 3)) * np.deg2rad(cfg.st_sigma_deg))))
        self.kp, self.kd = cfg.wn ** 2, 2.0 * cfg.zeta * cfg.wn
        self.gyr2 = np.array(cfg.gyr2)
        self.att_sq = np.zeros(n)
        self.att_n = np.zeros(n)
        self.tilt_max = np.zeros(n)
        self.rcs_used = np.zeros(n)
        self.dq = np.tile([1.0, 0.0, 0.0, 0.0], (n, 1))         # rotation accumulated during the last engine step (what a delta-angle gyro integrates)

    # ---- truth: advance one engine step ----
    def step(self, p, v, a_cmd, mass, tmax, engine_on, dt):
        """Integrate the rigid body over dt with `sub` substeps. a_cmd: guidance acceleration vector (world, excluding gravity), the
        command for thrust magnitude (mass * |a_cmd|) and direction. Returns p_new, v_new, mean body specific force (n, 3),
        mean thrust (N) and reaction-control propellant used (kg)."""
        c = self.cfg
        h = dt / c.sub
        zd_new, amag = command_from_accel(a_cmd, c)
        hold = amag < c.hold_acc
        self.zd = np.where(hold[:, None], self.zd, zd_new)
        t_cmd = np.where(engine_on, np.clip(mass * amag, c.tmin_frac * tmax, tmax), 0.0)
        I = mass[:, None] * self.gyr2[None, :]
        lag = 1.0 - np.exp(-h / c.tau_thr)
        f_sum = np.zeros((len(p), 3))
        t_sum = np.zeros(len(p))
        rcs_kg = np.zeros(len(p))
        gvec = np.array([0.0, 0.0, -G])
        self.dq = np.tile([1.0, 0.0, 0.0, 0.0], (len(p), 1))
        for _ in range(c.sub):
            self.thrust = np.where(engine_on, self.thrust + (t_cmd - self.thrust) * lag, 0.0)
            R = q_to_matrix(self.q)
            zb = R[:, :, 2]
            e_w = np.cross(zb, self.zd)
            sn = np.linalg.norm(e_w, axis=1)
            ang = np.arctan2(sn, np.sum(zb * self.zd, axis=1))
            e_b = np.einsum("nji,nj->ni", R, e_w / np.maximum(sn, 1e-9)[:, None] * ang[:, None])
            near = (np.abs(e_b[:, :2]) < 0.1)                           # integrate only near the target (anti-windup during slews)
            self.ie = np.clip(self.ie + np.where(near, e_b[:, :2] * h, 0.0), -2.0, 2.0)
            # desired body rate: linear in the error near the target, a braking curve sqrt(2 alpha |e|) far from it (no overshoot when the torque saturates)
            a_lim = 0.7 * c.torque_max / I[:, :2]
            w_des = np.sign(e_b[:, :2]) * np.minimum(self.kp / self.kd * np.abs(e_b[:, :2]), np.sqrt(2.0 * a_lim * np.abs(e_b[:, :2])))
            wd = np.empty((len(p), 3))
            wd[:, :2] = self.kd * (w_des - self.w[:, :2]) + c.ki * self.kp * self.ie
            wd[:, 2] = -self.kd * self.w[:, 2]
            tau = np.clip(I * wd, -c.torque_max, c.torque_max)
            mis = np.concatenate([self.mis, np.ones((len(p), 1))], axis=1)
            Fb = self.thrust[:, None] * mis / np.linalg.norm(mis, axis=1, keepdims=True)         # thrust force in the body frame (N)
            r_thr = np.stack([self.com[:, 0], self.com[:, 1], np.full(len(p), -c.thr_arm_m)], axis=1)
            tau_d = np.cross(r_thr, Fb)
            wdot = (tau + tau_d - np.cross(self.w, I * self.w)) / I
            self.w = self.w + wdot * h
            step_q = rotvec_to_q(self.w * h)
            self.q = qnorm(qmul(self.q, step_q))
            self.dq = qmul(self.dq, step_q)
            Rn = q_to_matrix(self.q)
            f = Fb / mass[:, None]
            a = np.einsum("nij,nj->ni", Rn, f) + gvec
            p = p + v * h + 0.5 * a * h * h
            v = v + a * h
            f_sum += f
            t_sum += self.thrust
            rcs_kg += np.linalg.norm(tau, axis=1) / c.rcs_arm_m * h / (c.rcs_isp * G0)
        self.rcs_used += rcs_kg
        self.tilt_max = np.maximum(self.tilt_max, self.tilt_deg())
        return p, v, f_sum / c.sub, t_sum / c.sub, rcs_kg

    def tilt_deg(self):
        return np.degrees(np.arccos(np.clip(q_to_matrix(self.q)[:, 2, 2], -1.0, 1.0)))

    def rate_dps(self):
        return np.degrees(np.linalg.norm(self.w, axis=1))

    # ---- navigation side: attitude estimate ----
    def estimate(self, tt, dt, alive):
        """Gyro propagation every step, star-tracker correction every st_period_s; accumulates the attitude error."""
        c = self.cfg
        dtheta = q_to_rotvec(self.dq) + (self.gbias + self.rng.standard_normal((self.n, 3)) * c.gyro_noise_rps) * dt    # delta-angle gyro output
        self.q_est = qnorm(qmul(self.q_est, rotvec_to_q(dtheta)))
        meas_noise = self.rng.standard_normal((self.n, 3)) * np.deg2rad(c.st_sigma_deg)       # drawn every step: same stream for all judges
        if tt % max(int(round(c.st_period_s / dt)), 1) == 0:
            q_meas = qmul(self.q, rotvec_to_q(meas_noise))
            delta = q_to_rotvec(qmul(qconj(self.q_est), q_meas))
            self.q_est = qnorm(qmul(self.q_est, rotvec_to_q(c.st_gain * delta)))
        err = np.degrees(np.linalg.norm(q_to_rotvec(qmul(qconj(self.q_est), self.q)), axis=1))
        self.att_sq += np.where(alive, err * err, 0.0)
        self.att_n += alive

    def R_true(self):
        return q_to_matrix(self.q)

    def R_est(self):
        return q_to_matrix(self.q_est)

    def accel_world_meas(self, f_body, bias, noise):
        """Accelerometer output (specific force + bias + noise, body axes) rotated into the world frame with the ESTIMATED attitude."""
        return np.einsum("nij,nj->ni", self.R_est(), f_body + bias + noise)
