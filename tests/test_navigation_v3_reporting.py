import unittest

import numpy as np
import pandas as pd

from tools.summarize_navigation_v3 import booleans, score


class LandingScoringTests(unittest.TestCase):
    def test_strict_distance_and_speed_limits_and_contact(self):
        result = score(np.array([True, True, True, True, False]),
                       np.array([9.9, 10, 0, 0, 0]), np.array([1.9, 0, 2, 0, 0]),
                       np.array([.9, 0, 0, 1, 0]), 10)
        np.testing.assert_array_equal(result, [True, False, False, False, False])

    def test_negative_zero_and_nonfinite_values(self):
        result = score(np.ones(4, dtype=bool), np.array([0, -1, np.nan, 1]),
                       np.array([0, 0, 0, np.inf]), np.zeros(4), 10)
        np.testing.assert_array_equal(result, [True, False, False, False])

    def test_false_strings_are_not_truthy_and_unknowns_fail(self):
        self.assertEqual(booleans(pd.Series(["True", "False"])).tolist(), [True, False])
        with self.assertRaises(ValueError):
            booleans(pd.Series(["False", "maybe"]))


if __name__ == "__main__":
    unittest.main()
