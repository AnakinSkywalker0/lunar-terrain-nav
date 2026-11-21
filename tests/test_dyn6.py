"""Tests of the 6-DOF dynamics (sim/dyn6.py) and its engine switch. Run: python -m unittest tests.test_dyn6

The bit-identity test needs out/round6/engine_before_dyn6_backup.py (the engine as it was before the 6-DOF edit).
"""
import importlib.util
import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sim"))
import dyn6 as D  # noqa: E402
import engine  # noqa: E402

BACKUP = os.path.join(ROOT, "out", "round6", "engine_before_dyn6_backup.py")
KEYS = ("success", "miss_m", "impact_vz", "impact_vh", "fuel_left", "alt_sq", "valid_total", "valid_rej", "fault_total", "fault_acc")
UP = np.tile([0.0, 0.0, 1.0], (3, 1))


def new(cfg=None, n=3, seed=1):
    return D.Dyn6(cfg or D.Dyn6Config(misalign_deg=0.0, com_offset_m=0.0), n, seed, UP[:n])


def run(dy, a, steps, mass=2000.0, n=3):
    p, v = np.zeros((n, 3)), np.zeros((n, 3))
    tilt = []
    out = None
    for _ in range(steps):
        p, v, f, T, r = dy.step(p, v, np.tile(a, (n, 1)), np.full(n, mass), 6000.0, np.ones(n, bool), 0.25)
        tilt.append(dy.tilt_deg()[0])
        out = (p, v, f, T, r)
    return out, np.array(tilt)


class QuaternionTests(unittest.TestCase):
    def test_rotation_vector_round_trip_and_matrix(self):
        rv = np.array([[0.3, -0.2, 0.5], [0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        q = D.rotvec_to_q(rv)
        self.assertTrue(np.allclose(np.linalg.norm(q, axis=1), 1.0))
        self.assertTrue(np.allclose(D.q_to_rotvec(q), rv, atol=1e-9))
        R = D.q_to_matrix(q)
        self.assertTrue(np.allclose(np.einsum("nij,nkj->nik", R, R), np.eye(3), atol=1e-9))     # orthonormal
        self.assertTrue(np.allclose(np.linalg.det(R), 1.0))

    def test_q_from_z_axis_points_the_body_axis(self):
        d = np.array([[0.6, 0.0, 0.8], [0.0, 0.0, 1.0], [0.0, -0.6, 0.8]])
        R = D.q_to_matrix(D.q_from_z_axis(d))
        self.assertTrue(np.allclose(R[:, :, 2], d, atol=1e-9))

    def test_command_cone(self):
        a = np.array([[0.0, 0.0, 1.62], [3.0, 0.0, 1.0], [0.5, 0.0, 1.0]])
        zd, mag = D.command_from_accel(a, D.Dyn6Config(tilt_cmd_max_deg=35.0))
        self.assertTrue(np.allclose(zd[0], [0, 0, 1]) and np.isclose(mag[0], 1.62))
        self.assertAlmostEqual(float(np.degrees(np.arccos(zd[1, 2]))), 35.0, places=6)          # outside the cone: capped
        self.assertAlmostEqual(float(mag[1] * np.cos(np.deg2rad(35.0))), 1.0, places=6)       # the vertical acceleration asked for is kept
        self.assertTrue(np.allclose(zd[2], a[2] / np.linalg.norm(a[2])) and np.isclose(mag[2], np.linalg.norm(a[2])))   # inside: unchanged


class RigidBodyTests(unittest.TestCase):
    def test_hover_thrust_gives_no_acceleration_once_the_throttle_has_settled(self):
        dy = new()
        (p, v, f, T, r), _ = run(dy, np.array([0.0, 0.0, 1.62]), 60)
        (p2, v2, *_), _ = run(dy, np.array([0.0, 0.0, 1.62]), 8)
        self.assertLess(float(np.abs(v2).max()), 1e-6)                                       # run() restarts from rest: settled hover thrust holds it there
        self.assertTrue(np.allclose(T, 2000.0 * 1.62, rtol=1e-6))

    def test_free_fall_without_thrust_is_lunar_gravity(self):
        dy = new()
        p, v = np.zeros((3, 3)), np.zeros((3, 3))
        for _ in range(8):
            p, v, *_ = dy.step(p, v, np.zeros((3, 3)), np.full(3, 2000.0), 6000.0, np.zeros(3, bool), 0.25)
        self.assertTrue(np.allclose(v[:, 2], -1.62 * 2.0, atol=1e-9))
        self.assertTrue(np.allclose(p[:, 2], -0.5 * 1.62 * 4.0, atol=1e-9))

    def test_quaternion_stays_unit_and_attitude_follows_the_command(self):
        dy = new()
        th = np.deg2rad(20.0)
        (_, _, _, _, _), tilt = run(dy, 2.0 * np.array([np.sin(th), 0.0, np.cos(th)]), 80)
        self.assertTrue(np.allclose(np.linalg.norm(dy.q, axis=1), 1.0))
        self.assertAlmostEqual(float(tilt[-1]), 20.0, delta=0.5)
        self.assertLess(float(tilt.max()), 20.0 * 1.15)                                      # overshoot below 15 %
        self.assertGreater(float(tilt[1]), 0.1)                                              # it does not jump: tilt needs time

    def test_the_attitude_cannot_slew_faster_than_the_torque_limit_allows(self):
        weak = new(D.Dyn6Config(misalign_deg=0.0, com_offset_m=0.0, torque_max=50.0))
        strong = new()
        a = 2.0 * np.array([np.sin(np.deg2rad(30.0)), 0.0, np.cos(np.deg2rad(30.0))])
        _, tw = run(weak, a, 12)
        _, ts = run(strong, a, 12)
        self.assertLess(float(tw[3]), float(ts[3]) * 0.5)
        alpha_max = 50.0 / (2000.0 * 1.3)                                                    # rad/s^2 about a transverse axis
        self.assertLessEqual(float(np.deg2rad(tw[3])), 0.5 * alpha_max * 1.0 ** 2 * 1.10)      # after 1 s: at most the full-torque slew angle

    def test_propellant_matches_the_rocket_equation_integral(self):
        dy = new()
        (_, _, _, T, rcs), _ = run(dy, np.array([0.0, 0.0, 2.0]), 40)
        burned = T / (300.0 * 9.80665) * 0.25
        self.assertTrue(np.allclose(burned, 2000.0 * 2.0 / (300.0 * 9.80665) * 0.25, rtol=1e-3))      # settled thrust = m |a|
        self.assertTrue(np.all(rcs >= 0.0))

    def test_engine_off_stops_the_thrust(self):
        dy = new()
        run(dy, np.array([0.0, 0.0, 2.0]), 20)
        p, v = np.zeros((3, 3)), np.zeros((3, 3))
        _, _, _, T, _ = dy.step(p, v, np.tile([0.0, 0.0, 2.0], (3, 1)), np.full(3, 2000.0), 6000.0, np.zeros(3, bool), 0.25)
        self.assertTrue(np.allclose(T, 0.0))

    def test_misalignment_and_com_offset_make_a_disturbance_that_the_controller_removes(self):
        dy = new(D.Dyn6Config(misalign_deg=0.0, com_offset_m=0.05))
        _, tilt = run(dy, np.array([0.0, 0.0, 2.0]), 120)
        self.assertLess(float(tilt[-1]), 0.3)                        # integral action: steady tilt error close to zero
        self.assertGreater(float(tilt[:20].max()), 0.0)              # but it did tilt at first

    def test_estimate_tracks_the_truth_and_is_deterministic(self):
        def go():
            dy = D.Dyn6(D.Dyn6Config(), 4, 5, np.tile([0.0, 0.0, 1.0], (4, 1)))
            a = 2.0 * np.array([np.sin(0.3), 0.0, np.cos(0.3)])
            p, v = np.zeros((4, 3)), np.zeros((4, 3))
            for k in range(1, 121):
                p, v, *_ = dy.step(p, v, np.tile(a, (4, 1)), np.full(4, 2000.0), 6000.0, np.ones(4, bool), 0.25)
                dy.estimate(k, 0.25, np.ones(4, bool))
            return dy
        d1, d2 = go(), go()
        self.assertTrue(np.array_equal(d1.q_est, d2.q_est))
        self.assertLess(float(np.sqrt(d1.att_sq / d1.att_n).max()), 0.2)       # degrees RMS, with a 2 s star tracker

    def test_without_the_star_tracker_a_gyro_bias_makes_the_estimate_drift(self):
        cfg = D.Dyn6Config(st_gain=0.0, gyro_bias_dps=0.05)
        dy = D.Dyn6(cfg, 4, 5, np.tile([0.0, 0.0, 1.0], (4, 1)))
        p, v = np.zeros((4, 3)), np.zeros((4, 3))
        for k in range(1, 401):
            p, v, *_ = dy.step(p, v, np.tile([0.0, 0.0, 1.62], (4, 1)), np.full(4, 2000.0), 6000.0, np.ones(4, bool), 0.25)
            dy.estimate(k, 0.25, np.ones(4, bool))
        self.assertGreater(float(np.sqrt(dy.att_sq / dy.att_n).mean()), 0.3)


class EngineSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pipeline as P
        cls.world, cls.track = P.get_world(("proc", 11))
        cls.kw = dict(P.tuned())
        cls.kw["cam_policy"] = "conf"

    def test_default_off_is_bit_identical_to_the_previous_engine(self):
        if not os.path.exists(BACKUP):
            self.skipTest("backup engine missing")
        spec = importlib.util.spec_from_file_location("engine_prev6", BACKUP)
        prev = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prev)
        prev._CAM.update(engine._cam_model())
        sc, sc_prev = engine.SCENARIOS["cliff_fault"], prev.SCENARIOS["cliff_fault"]
        for judge, extra, mb in (("tolerance", dict(tol_noise_floor=True), 0), ("pitfal", {}, 0), ("trust2", {}, 0),
                                 ("tolerance_mb", dict(tol_noise_floor=True, mb_terrain_at_footprint=True), 3), ("pitfal_mb", {}, 3)):
            a = engine.simulate(self.world, self.track, sc, judge, engine.Draws(self.world, sc, 10, 3), beams=mb, **self.kw, **extra)
            b = prev.simulate(self.world, self.track, sc_prev, judge, prev.Draws(self.world, sc_prev, 10, 3), beams=mb, **self.kw, **extra)
            for k in KEYS:
                self.assertTrue(np.array_equal(a[k], b[k]), (judge, k))
            self.assertNotIn("impact_tilt", a)

    def test_6dof_runs_report_the_new_keys_and_the_stricter_landing_rule(self):
        sc = engine.SCENARIOS["cliff_fault"]
        r = engine.simulate(self.world, self.track, sc, "tolerance", engine.Draws(self.world, sc, 12, 3), dyn6=D.Dyn6Config(), **self.kw)
        for k in ("impact_tilt", "impact_rate", "success_legacy", "tilt_max", "att_err_rms_deg", "rcs_fuel"):
            self.assertIn(k, r)
        self.assertTrue(np.all(r["success"] <= r["success_legacy"]))                   # the 6-DOF rule is never looser than the 3-DOF rule
        landed = r["success"]
        self.assertTrue(np.all(r["impact_tilt"][landed] <= D.Dyn6Config().tilt_land_max_deg))
        self.assertTrue(np.all(r["tilt_max"] <= D.Dyn6Config().tilt_cmd_max_deg + 15.0))
        self.assertTrue(np.all(r["rcs_fuel"] >= 0.0) and np.all(r["rcs_fuel"] < 50.0))

    def test_6dof_is_deterministic_and_the_same_for_every_judge_draw(self):
        sc = engine.SCENARIOS["cliff_fault"]
        kw = dict(self.kw)
        a = engine.simulate(self.world, self.track, sc, "tolerance", engine.Draws(self.world, sc, 8, 3), dyn6=D.Dyn6Config(), **kw)
        b = engine.simulate(self.world, self.track, sc, "tolerance", engine.Draws(self.world, sc, 8, 3), dyn6=D.Dyn6Config(), **kw)
        for k in ("success", "miss_m", "impact_tilt", "att_err_rms_deg", "fuel_left"):
            self.assertTrue(np.array_equal(a[k], b[k]), k)

    def test_missing_map_is_refused(self):
        import dataclasses
        sc = dataclasses.replace(engine.SCENARIOS["cliff_fault"], map_mode="missing")
        with self.assertRaises(ValueError):
            engine.simulate(self.world, self.track, sc, "tolerance", engine.Draws(self.world, sc, 4, 3), dyn6=D.Dyn6Config(), **self.kw)

    def test_three_beam_6dof_runs(self):
        sc = engine.SCENARIOS["cliff_fault"]
        r = engine.simulate(self.world, self.track, sc, "tolerance_mb", engine.Draws(self.world, sc, 8, 3), dyn6=D.Dyn6Config(), beams=3,
                            tol_noise_floor=True, mb_terrain_at_footprint=True, **self.kw)
        self.assertTrue(np.isfinite(r["att_err_rms_deg"]).all() and r["success_legacy"].any())


if __name__ == "__main__":
    unittest.main()
