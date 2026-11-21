"""Diagnostic test (changes no results): the multi-beam terrain variance is taken under the vehicle, not where the canted beams land.
Run: python -m unittest tests.test_round4_audit
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim"))
import engine  # noqa: E402


class FootprintAuditTests(unittest.TestCase):
    def test_footprint_terrain_spread_differs_from_nadir_at_altitude(self):
        import pipeline as P
        w, tr = P.get_world(("proc", 12))
        sx, sy = tr["start"]
        tx, ty = tr["target"]
        f = np.linspace(0.0, 1.0, 100)
        x, y = sx + f * (tx - sx), sy + f * (ty - sy)
        rad = np.full_like(x, 200.0)
        agl = 3000.0
        off = agl * np.tan(np.deg2rad(engine.BEAM_CANT_DEG))
        self.assertAlmostEqual(off, 1242.6, delta=1.0)
        nad = w.stats.hstd(x, y, rad) ** 2
        fp = np.mean([w.stats.hstd(x + off * np.cos(a), y + off * np.sin(a), rad) ** 2 for a in (0.0, 2.094, 4.189)], axis=0)
        self.assertGreater(np.median(fp) / np.median(nad), 1.5)     # descriptive fact, see out/round4/footprint_audit.csv


if __name__ == "__main__":
    unittest.main()
