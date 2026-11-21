"""Tests of the multi-beam sensor and consensus check in sim/engine.py (round-3 extension).

Run: python -m unittest tests.test_multibeam   (the integration tests build one procedural world, about 1 minute)
"""
import dataclasses
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim"))
import engine  # noqa: E402

CT, ST = np.cos(np.deg2rad(engine.BEAM_CANT_DEG)), np.sin(np.deg2rad(engine.BEAM_CANT_DEG))


class SlantRangeTests(unittest.TestCase):
    def test_flat_ground(self):
        h = lambda x, y: np.zeros_like(x)               # noqa: E731
        z = np.array([100.0, 1000.0, 8000.0])
        s = engine._slant_range(h, np.zeros(3), np.zeros(3), z, 1.0, 0.0, CT, ST)
        np.testing.assert_allclose(s, z / CT, rtol=2e-4)

    def test_sloped_plane_matches_closed_form(self):
        h = lambda x, y: 0.3 * x                         # noqa: E731
        z = np.array([1000.0, 3000.0])
        for ux, expect in ((1.0, lambda zz: zz / (CT + 0.3 * ST)), (-1.0, lambda zz: zz / (CT - 0.3 * ST))):
            s = engine._slant_range(h, np.zeros(2), np.zeros(2), z, ux, 0.0, CT, ST)
            np.testing.assert_allclose(s, expect(z), rtol=2e-4)

    def test_cliff_shortens_the_beam_on_the_high_side(self):
        h = lambda x, y: np.where(x > 100.0, 800.0, 0.0)  # noqa: E731  a wall 800 m high, 100 m east of the lander
        z = np.array([1000.0])
        up = engine._slant_range(h, np.zeros(1), np.zeros(1), z, 1.0, 0.0, CT, ST)[0]
        down = engine._slant_range(h, np.zeros(1), np.zeros(1), z, -1.0, 0.0, CT, ST)[0]
        self.assertLess(up, down)
        self.assertAlmostEqual(down, 1000.0 / CT, delta=2.0)


class ConsensusTests(unittest.TestCase):
    var = np.full((1, 3), 4.0)

    def test_consistent_beams_all_kept(self):
        ok = engine._consensus_ok(np.array([[500.0, 500.5, 499.7]]), self.var)
        self.assertTrue(ok.all())

    def test_single_outlier_is_the_only_one_flagged(self):
        ok = engine._consensus_ok(np.array([[500.0, 800.0, 499.7]]), self.var)
        self.assertEqual(ok.tolist(), [[True, False, True]])

    def test_two_beams_cannot_vote(self):
        ok = engine._consensus_ok(np.array([[500.0, 900.0]]), np.full((1, 2), 4.0))
        self.assertTrue(ok.all())

    def test_larger_variance_widens_the_tolerance(self):
        z = np.array([[500.0, 512.0, 500.0]])
        self.assertFalse(engine._consensus_ok(z, np.full((1, 3), 4.0))[0, 1])
        self.assertTrue(engine._consensus_ok(z, np.full((1, 3), 400.0))[0, 1])


class DrawsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pipeline as P
        cls.world, cls.track = P.get_world(("proc", 11))
        cls.P = P

    def test_beam_draws_do_not_change_legacy_draws(self):
        scen = engine.SCENARIOS["cliff_fault"]
        a = engine.Draws(self.world, scen, 8, 5)
        b = engine.Draws(self.world, scen, 8, 5)
        b.mb(3, scen)
        self.assertTrue(np.array_equal(a.alt_g, b.alt_g))
        self.assertTrue(np.array_equal(a.burst, b.burst))

    def test_beam_draws_are_reproducible_and_independent_per_beam(self):
        scen = engine.SCENARIOS["cliff_fault"]
        a = engine.Draws(self.world, scen, 8, 5).mb(3, scen)
        b = engine.Draws(self.world, scen, 8, 5).mb(3, scen)
        self.assertTrue(np.array_equal(a.g, b.g))
        self.assertFalse(np.array_equal(a.g[:, :, 0], a.g[:, :, 1]))

    def test_unsupported_settings_are_refused(self):
        tr, w = self.track, self.world
        d = engine.Draws(w, engine.SCENARIOS["cliff"], 4, 1)
        with self.assertRaises(ValueError):
            engine.simulate(w, tr, engine.SCENARIOS["cliff"], "pitfal_mb", d, beams=0)
        dd = engine.Draws(w, engine.SCENARIOS["delayed"], 4, 1)
        with self.assertRaises(ValueError):
            engine.simulate(w, tr, engine.SCENARIOS["delayed"], "pitfal_mb", dd, beams=3)


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pipeline as P
        cls.world, cls.track = P.get_world(("proc", 11))
        cls.kw = dict(P.tuned())
        cls.kw["cam_policy"] = "conf"

    def run_one(self, judge, scen_name="cliff_fault", n=12, **extra):
        scen = engine.SCENARIOS[scen_name]
        d = engine.Draws(self.world, scen, n, 3)
        kw = dict(self.kw)
        kw.update(extra)
        return engine.simulate(self.world, self.track, scen, judge, d, beams=3, **kw)

    def test_mb_judges_run_and_count_readings(self):
        for judge, extra in (("pitfal_mb", {}), ("tolerance_mb", {}), ("tolerance_mb", dict(tol_noise_floor=True, mb_consensus=True))):
            r = self.run_one(judge, **extra)
            self.assertEqual(len(r["success"]), 12)
            self.assertGreater((r["valid_total"] + r["fault_total"]).sum(), 0)
            self.assertTrue(np.isfinite(r["miss_m"]).all())

    def test_consensus_does_not_change_a_clean_run_much(self):
        quiet = dataclasses.replace(engine.SCENARIOS["cliff"], burst_rate=0.0)
        engine.SCENARIOS["_quiet"] = quiet
        try:
            a = self.run_one("tolerance_mb", "_quiet")
            b = self.run_one("tolerance_mb", "_quiet", mb_consensus=True)
        finally:
            del engine.SCENARIOS["_quiet"]
        self.assertGreaterEqual(b["success"].sum(), a["success"].sum() - 2)

    def test_legacy_judges_ignore_beams(self):
        scen = engine.SCENARIOS["cliff_fault"]
        a = engine.simulate(self.world, self.track, scen, "pitfal", engine.Draws(self.world, scen, 8, 3), **self.kw)
        b = engine.simulate(self.world, self.track, scen, "pitfal", engine.Draws(self.world, scen, 8, 3), beams=3, mb_consensus=True, **self.kw)
        for k in ("success", "miss_m", "impact_vz", "fuel_left"):
            self.assertTrue(np.array_equal(a[k], b[k]), k)


if __name__ == "__main__":
    unittest.main()
