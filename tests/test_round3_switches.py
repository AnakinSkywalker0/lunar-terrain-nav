"""Invariants of the round-3 candidate switches in sim/engine.py (slow: builds one procedural world, about 1 minute).

Run: python -m unittest tests.test_round3_switches
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim"))
import engine  # noqa: E402
import pipeline as P  # noqa: E402

N, SEED = 24, 3


def run(world, track, scen, judge, **extra):
    kw = dict(P.tuned())
    kw["cam_policy"] = "conf"
    kw.update(extra)
    return engine.simulate(world, track, scen, judge, engine.Draws(world, scen, N, SEED), **kw)


def same(a, b, keys=("success", "miss_m", "impact_vz", "impact_vh", "fuel_left", "alt_sq")):
    return all(np.array_equal(a[k], b[k]) for k in keys)


class Round3SwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w, cls.tr = P.get_world(("proc", 11))
        cls.scen = engine.SCENARIOS["shadow_noisy"]

    def test_defaults_are_off(self):
        a = run(self.w, self.tr, self.scen, "tolerance")
        b = run(self.w, self.tr, self.scen, "tolerance", tol_noise_floor=False, terrain_R=False, fault_label_noise_aware=False)
        self.assertTrue(same(a, b))
        self.assertTrue(np.array_equal(a["valid_total"], b["valid_total"]))

    def test_label_switch_changes_bookkeeping_only(self):
        old = run(self.w, self.tr, self.scen, "pitfal")
        new = run(self.w, self.tr, self.scen, "pitfal", fault_label_noise_aware=True)
        self.assertTrue(same(old, new), "the label must not change any decision or outcome")
        # with x8 noise the nominal-sigma label calls many valid readings faults; the true-noise label calls fewer
        self.assertGreater(new["valid_total"].sum(), old["valid_total"].sum())
        self.assertLess(new["fault_total"].sum(), old["fault_total"].sum())
        self.assertEqual((new["valid_total"] + new["fault_total"]).sum(), (old["valid_total"] + old["fault_total"]).sum())

    def test_switches_ignored_by_other_judges(self):
        a = run(self.w, self.tr, self.scen, "pitfal")
        b = run(self.w, self.tr, self.scen, "pitfal", tol_noise_floor=True, terrain_R=True)
        self.assertTrue(same(a, b))

    def test_tol_noise_floor_changes_tolerance_judge(self):
        a = run(self.w, self.tr, self.scen, "tolerance")
        b = run(self.w, self.tr, self.scen, "tolerance", tol_noise_floor=True)
        self.assertFalse(same(a, b))

    def test_terrain_R_changes_wait_but_not_tolerance(self):
        self.assertFalse(same(run(self.w, self.tr, self.scen, "wait"), run(self.w, self.tr, self.scen, "wait", terrain_R=True)))
        self.assertTrue(same(run(self.w, self.tr, self.scen, "tolerance"), run(self.w, self.tr, self.scen, "tolerance", terrain_R=True)))


if __name__ == "__main__":
    unittest.main()
