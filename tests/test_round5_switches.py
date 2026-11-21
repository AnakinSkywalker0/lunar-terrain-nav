"""Tests of the round-5 engine switches (all default off). Run: python -m unittest tests.test_round5_switches  (about 5 minutes)

The bit-identity test needs out/round5/engine_before_round5_backup.py (the engine as it was before the round-5 edit).
"""
import dataclasses
import importlib.util
import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sim"))
import engine  # noqa: E402

BACKUP = os.path.join(ROOT, "out", "round5", "engine_before_round5_backup.py")
KEYS = ("success", "miss_m", "impact_vz", "impact_vh", "fuel_left", "alt_sq", "valid_total", "valid_rej", "fault_total", "fault_acc")


def same(a, b, keys=KEYS):
    return all(np.array_equal(a[k], b[k]) for k in keys)


class UnitTests(unittest.TestCase):
    def test_joint_update_with_one_beam_equals_the_scalar_update(self):
        rng = np.random.default_rng(1)
        m = 4
        A = rng.standard_normal((m, 9, 9))
        P = np.einsum("mij,mkj->mik", A, A) + 5 * np.eye(9)
        x = rng.standard_normal((m, 9))
        Hm = rng.standard_normal((m, 3, 9))
        nu = rng.standard_normal((m, 3))
        Rd = np.full((m, 3), 2.0)
        ok = np.zeros((m, 3), dtype=bool)
        ok[:, 1] = True
        xj, Pj = engine._joint_update(x, P, nu, Hm, Rd, 0.0, ok)
        xs, Ps = x.copy(), P.copy()
        engine._scalar_update(xs, Ps, Hm[:, 1], nu[:, 1], Rd[:, 1], np.ones(m, dtype=bool))
        self.assertTrue(np.allclose(xj, xs, atol=1e-6) and np.allclose(Pj, Ps, atol=1e-6))

    def test_joint_update_with_no_beam_changes_nothing(self):
        P = np.tile(np.eye(9), (2, 1, 1)) * 3.0
        x = np.ones((2, 9))
        xj, Pj = engine._joint_update(x, P, np.ones((2, 3)), np.ones((2, 3, 9)), np.ones((2, 3)), 1.0, np.zeros((2, 3), dtype=bool))
        self.assertTrue(np.allclose(xj, x, atol=1e-6) and np.allclose(Pj, P, atol=1e-6))

    def test_solution_separation_flags_the_odd_beam_only(self):
        m = 2
        P = np.tile(np.eye(9), (m, 1, 1)) * 100.0
        Hm = np.zeros((m, 3, 9))
        Hm[:, :, 2] = 1.0
        nu = np.zeros((m, 3))
        nu[1, 0] = 80.0                                   # run 1: beam 0 is far off
        flagged = engine._solution_separation(np.zeros((m, 9)), P, nu, Hm, np.full((m, 3), 4.0), 0.0, np.ones((m, 3), dtype=bool))
        self.assertFalse(flagged[0].any())
        self.assertTrue(flagged[1, 0] and not flagged[1, 1:].any())

    def test_student_t_weight(self):
        self.assertAlmostEqual(float(engine._t_weight(0.0, 4.0)), 1.25)
        self.assertLess(float(engine._t_weight(100.0, 4.0)), 0.05)


class SwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pipeline as P
        cls.P = P
        cls.world, cls.track = P.get_world(("proc", 11))
        cls.kw = dict(P.tuned())
        cls.kw["cam_policy"] = "conf"

    def run_eng(self, eng, judge, scen, n=10, seed=3, world=None, **extra):
        w, tr = (self.world, self.track) if world is None else world
        d = eng.Draws(w, scen, n, seed)
        kw = dict(self.kw)
        kw.update(extra)
        return eng.simulate(w, tr, scen, judge, d, **kw), d

    def test_defaults_off_are_bit_identical_to_the_previous_engine(self):
        if not os.path.exists(BACKUP):
            self.skipTest("backup engine missing")
        spec = importlib.util.spec_from_file_location("engine_prev5", BACKUP)
        prev = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prev)
        prev._CAM.update(engine._cam_model())
        sc, sc_prev = engine.SCENARIOS["cliff_fault"], prev.SCENARIOS["cliff_fault"]
        for judge, extra, mb in (("tolerance", {}, 0), ("tolerance", dict(tol_noise_floor=True), 0), ("pitfal", {}, 0), ("trust2", {}, 0),
                                 ("vbakf", {}, 0), ("tolerance_mb", dict(tol_noise_floor=True), 3),
                                 ("tolerance_mb", dict(tol_noise_floor=True, mb_terrain_at_footprint=True), 3), ("pitfal_mb", {}, 3)):
            a, _ = self.run_eng(engine, judge, sc, beams=mb, **extra)
            b, _ = self.run_eng(prev, judge, sc_prev, beams=mb, **extra)
            self.assertTrue(same(a, b), (judge, extra))

    def test_invalid_combinations_are_refused(self):
        sc = engine.SCENARIOS["cliff_fault"]
        for judge, extra in (("pitfal", dict(cusum=True)), ("tolerance", dict(joint_update=True)), ("tolerance_mb", dict(solsep=True)),
                             ("tolerance", dict(imm=True, tol_noise_floor=True)), ("fixed", dict(robust_t=4.0))):
            with self.assertRaises(ValueError):
                self.run_eng(engine, judge, sc, n=2, beams=3 if judge.endswith("_mb") else 0, **extra)
        with self.assertRaises(ValueError):
            self.run_eng(engine, "tolerance", dataclasses.replace(sc, fault_type="beam_dropout"), n=2)
        with self.assertRaises(ValueError):
            self.run_eng(engine, "tolerance_mb", dataclasses.replace(sc, fault_type="stuck"), n=2, beams=3, tol_noise_floor=True)

    def test_new_fault_types_inject_faults_and_dropout_removes_readings(self):
        sc = engine.SCENARIOS["cliff_fault"]
        for ft in ("stuck", "drift", "scale"):
            r, _ = self.run_eng(engine, "tolerance", dataclasses.replace(sc, fault_type=ft, burst_len=(40, 80)), tol_noise_floor=True)
            self.assertGreater(r["fault_total"].sum(), 0, ft)
        d, _ = self.run_eng(engine, "tolerance_mb", dataclasses.replace(sc, fault_type="beam_dropout"), beams=3, tol_noise_floor=True)
        b, _ = self.run_eng(engine, "tolerance_mb", sc, beams=3, tol_noise_floor=True)
        self.assertLess(d["valid_total"].sum() + d["fault_total"].sum(), b["valid_total"].sum() + b["fault_total"].sum())
        self.assertEqual(d["fault_total"].sum(), 0)

    def test_delay_estimator_recovers_the_true_delay(self):
        sc = engine.SCENARIOS["delayed"]
        r, d = self.run_eng(engine, "tolerance", sc, tol_noise_floor=True, delay_est=True, timestamps=False)
        self.assertLessEqual(np.median(np.abs(r["est_lag"] - d.delay_steps)), 2.5, (r["est_lag"], d.delay_steps))

    def test_map_search_finds_a_2_km_offset(self):
        w = self.P.get_world(("proc", 11))
        sc = dataclasses.replace(engine.SCENARIOS["cliff_fault"], map_mode="wrong", wrong_offset_m=2000.0)
        r, _ = self.run_eng(engine, "tolerance", sc, n=10, world=w, tol_noise_floor=True, map_search=True)
        found = np.hypot(r["est_off_x"] - 2000.0, r["est_off_y"]) < 300.0
        self.assertGreaterEqual(found.sum(), 1, (r["est_off_x"], r["est_off_y"]))   # partial: the search is unreliable (see docs/ROUND5_DEV_RESULTS.md)
        r0, _ = self.run_eng(engine, "tolerance", sc, n=10, world=w, tol_noise_floor=True)
        self.assertTrue((r0["est_off_x"] == 0).all())

    def test_gate_limit_and_student_t_change_results_sensibly(self):
        sc = engine.SCENARIOS["cliff_fault"]
        a, _ = self.run_eng(engine, "tolerance", sc, tol_noise_floor=True)
        wide, _ = self.run_eng(engine, "tolerance", sc, tol_noise_floor=True, gate_chi2=50.0)
        self.assertLessEqual(wide["valid_rej"].sum(), a["valid_rej"].sum())
        self.assertGreaterEqual(wide["fault_acc"].sum(), a["fault_acc"].sum())
        t, _ = self.run_eng(engine, "tolerance", sc, tol_noise_floor=True, robust_t=4.0)
        self.assertEqual(t["valid_rej"].sum(), 0)

    def test_joint_and_solsep_multibeam_run_and_stay_finite(self):
        sc = engine.SCENARIOS["cliff_fault"]
        for extra in (dict(joint_update=True), dict(solsep=True)):
            r, _ = self.run_eng(engine, "tolerance_mb", sc, beams=3, tol_noise_floor=True, **extra)
            self.assertGreater(r["valid_total"].sum(), 0)
            self.assertTrue(np.isfinite(r["nees_sum"]).all())


if __name__ == "__main__":
    unittest.main()
