"""Tests of the round-4 engine switches (all default off). Run: python -m unittest tests.test_round4_switches  (about 2-3 minutes)

The bit-identity test needs out/round4/engine_before_round4_backup.py (the engine as it was before the round-4 edit, multi-beam included).
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

BACKUP = os.path.join(ROOT, "out", "round4", "engine_before_round4_backup.py")
KEYS = ("success", "miss_m", "impact_vz", "impact_vh", "fuel_left", "alt_sq", "valid_total", "valid_rej", "fault_total", "fault_acc")


def same(a, b, keys=KEYS):
    return all(np.array_equal(a[k], b[k]) for k in keys)


class Round4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pipeline as P
        cls.world, cls.track = P.get_world(("proc", 11))
        cls.kw = dict(P.tuned())
        cls.kw["cam_policy"] = "conf"

    def run_eng(self, eng, judge, scen, n=10, seed=3, **extra):
        d = eng.Draws(self.world, scen, n, seed)
        kw = dict(self.kw)
        kw.update(extra)
        return eng.simulate(self.world, self.track, scen, judge, d, **kw)

    def test_defaults_off_are_bit_identical_to_the_previous_engine(self):
        if not os.path.exists(BACKUP):
            self.skipTest("backup engine missing")
        spec = importlib.util.spec_from_file_location("engine_prev", BACKUP)
        prev = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prev)
        prev._CAM.update(engine._cam_model())      # the backup sits in another folder, so give it the camera model directly
        sc = engine.SCENARIOS["cliff_fault"]
        sc_prev = prev.SCENARIOS["cliff_fault"]
        for judge, extra, mb in (("tolerance", {}, 0), ("tolerance", dict(tol_noise_floor=True), 0), ("pitfal", {}, 0), ("trust2", {}, 0),
                                 ("tolerance_mb", dict(tol_noise_floor=True), 3), ("pitfal_mb", {}, 3)):
            a = self.run_eng(engine, judge, sc, beams=mb, **extra)
            b = self.run_eng(prev, judge, sc_prev, beams=mb, **extra)
            self.assertTrue(same(a, b), (judge, extra))

    def test_floor_mode_both_equals_the_round3_floor(self):
        sc = engine.SCENARIOS["cliff_fault"]
        a = self.run_eng(engine, "tolerance", sc, tol_noise_floor=True)
        b = self.run_eng(engine, "tolerance", sc, tol_noise_floor=True, tol_floor_mode="both")
        self.assertTrue(same(a, b))
        c = self.run_eng(engine, "tolerance", sc, tol_noise_floor=True, tol_floor_mode="variance")
        self.assertFalse(same(a, c))

    def test_oracle_equals_plain_tolerance_at_nominal_noise(self):
        sc = engine.SCENARIOS["cliff_fault"]
        a = self.run_eng(engine, "tolerance", sc)
        b = self.run_eng(engine, "tolerance", sc, oracle_R=True)
        self.assertTrue(same(a, b))

    def test_wrong_offset_default_and_zero(self):
        base = engine.SCENARIOS["cliff_fault"]
        d = engine.Draws(self.world, base, 10, 3)

        def run(scen):
            return engine.simulate(self.world, self.track, scen, "tolerance", d, **self.kw)
        wrong_default = dataclasses.replace(base, map_mode="wrong")
        wrong_explicit = dataclasses.replace(base, map_mode="wrong", wrong_offset_m=2000.0)
        wrong_zero = dataclasses.replace(base, map_mode="wrong", wrong_offset_m=0.0)
        self.assertTrue(same(run(wrong_default), run(wrong_explicit)))
        self.assertTrue(same(run(wrong_zero), run(base)))
        self.assertFalse(same(run(wrong_explicit), run(base)))

    def test_footprint_terrain_equals_nadir_for_vertical_beams(self):
        sc = engine.SCENARIOS["cliff_fault"]
        old = engine.BEAM_CANT_DEG
        engine.BEAM_CANT_DEG = 0.0
        try:
            a = self.run_eng(engine, "tolerance_mb", sc, beams=3)
            b = self.run_eng(engine, "tolerance_mb", sc, beams=3, mb_terrain_at_footprint=True)
        finally:
            engine.BEAM_CANT_DEG = old
        self.assertTrue(same(a, b))

    def test_invalid_combinations_are_refused(self):
        sc = engine.SCENARIOS["cliff_fault"]
        d = engine.Draws(self.world, sc, 4, 1)
        for extra in (dict(tol_floor_mode="nope"), dict(tol_noise_floor=True, oracle_R=True), dict(ar1_phi=1.0),
                      dict(tol_floor_source="diff")):
            with self.assertRaises(ValueError):
                engine.simulate(self.world, self.track, sc, "tolerance", d, **extra)

    def noisy_trace(self, judge, **extra):
        sc = dataclasses.replace(engine.SCENARIOS["cliff"], burst_rate=0.0, noise_mult_below_agl=4.0, noise_mult_agl=1e9)
        d = engine.Draws(self.world, sc, 6, 5)
        kw = dict(self.kw)
        kw.update(extra)
        r = engine.simulate(self.world, self.track, sc, judge, d, record_idx=0, **kw)
        rec = r["rec"]
        agl = np.array(rec["agl_true"])
        true_sd = 4.0 * (1.0 + 0.0015 * agl)
        est = np.array(rec["s_hat"])
        late = (agl < 8000) & (agl > 300)
        return np.median(est[late] / true_sd[late])

    def test_vbakf_tracks_a_constant_noise_multiplier(self):
        ratio = self.noisy_trace("vbakf")
        self.assertTrue(0.8 <= ratio <= 1.2, ratio)

    def test_diff_estimator_recovers_white_noise_and_underestimates_correlated_noise(self):
        white = self.noisy_trace("tolerance", tol_noise_floor=True, tol_floor_source="diff")
        corr = self.noisy_trace("tolerance", tol_noise_floor=True, tol_floor_source="diff", ar1_phi=0.9)
        self.assertTrue(0.75 <= white <= 1.25, white)
        self.assertTrue(0.15 <= corr <= 0.40, corr)       # theory: sqrt((6 - 8*0.9 + 2*0.81) / 6) = 0.26


if __name__ == "__main__":
    unittest.main()
