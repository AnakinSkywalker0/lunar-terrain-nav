"""Tests of the round-4 held-out runner's refusals and verdict logic. Never runs the held-out set."""
import os
import sys
import types
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim"))
import round4_heldout as R  # noqa: E402


def fake_git(tag=None, head="aaa", dirty=False):
    def git(*args):
        if args[0] == "rev-parse" and "--verify" in args:
            return types.SimpleNamespace(returncode=0 if tag else 1, stdout=(tag or "") + "\n")
        if args[0] == "rev-parse":
            return types.SimpleNamespace(returncode=0, stdout=head + "\n")
        if args[0] == "diff":
            return types.SimpleNamespace(returncode=1 if dirty else 0, stdout="")
        raise AssertionError(args)
    return git


class GuardTests(unittest.TestCase):
    def test_refusals_and_clean_run(self):
        self.assertIn("does not exist", R.check_frozen(fake_git(tag=None), csv_exists=False))
        self.assertIn("not the commit", R.check_frozen(fake_git(tag="aaa", head="bbb"), csv_exists=False))
        self.assertIn("uncommitted", R.check_frozen(fake_git(tag="aaa", head="aaa", dirty=True), csv_exists=False))
        self.assertIn("forbids re-running", R.check_frozen(fake_git(tag="aaa", head="aaa"), csv_exists=True))
        self.assertIsNone(R.check_frozen(fake_git(tag="aaa", head="aaa"), csv_exists=False))

    def test_reserved_worlds_are_17_to_20_and_not_the_development_worlds(self):
        self.assertEqual(R.SEEDS, (17, 18, 19, 20))


def frame(b=None, a=None, pb=None, single=(70.0, 75.0)):
    rows = []
    for md in ("independent", "common"):
        for c in R.CONDS:
            for cfg, v in ((R.PB, 90.0 if c != "x16" else 60.0), (R.CA, 90.0 if c != "x16" else 99.0), (R.CB, 90.0 if c != "x16" else 70.0)):
                v = {R.PB: pb, R.CA: a, R.CB: b}.get(cfg) or v
                rows.append(dict(part="multi", fault_mode=md, condition=c, config=cfg, success_pct=v))
    rows += [dict(part="single", fault_mode="single", condition="wrong100", config=R.ST, success_pct=single[0]),
             dict(part="single", fault_mode="single", condition="wrong100", config=R.SF, success_pct=single[1])]
    return pd.DataFrame(rows)


class VerdictTests(unittest.TestCase):
    def test_all_met(self):
        self.assertTrue(all(ok for ok, _ in R.verdicts(frame()).values()))

    def test_r1_fails_when_b_is_far_below_at_low_noise(self):
        df = frame()
        df.loc[(df.config == R.CB) & (df.condition == "x4"), "success_pct"] = 70.0
        self.assertFalse(R.verdicts(df)["R1"][0])

    def test_r2_fails_without_a_margin_at_x16(self):
        df = frame()
        df.loc[(df.config == R.CB) & (df.condition == "x16"), "success_pct"] = 61.0
        self.assertFalse(R.verdicts(df)["R2"][0])

    def test_r3_reports_a_collapse(self):
        df = frame()
        df.loc[(df.config == R.CA) & (df.condition == "x4"), "success_pct"] = 6.0
        self.assertFalse(R.verdicts(df)["R3"][0])

    def test_r4_fails_when_the_floor_amplifies_the_map_error(self):
        self.assertFalse(R.verdicts(frame(single=(70.0, 60.0)))["R4"][0])


if __name__ == "__main__":
    unittest.main()
