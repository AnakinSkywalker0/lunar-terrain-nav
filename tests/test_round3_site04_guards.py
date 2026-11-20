"""Tests of the Site04 runner's refusals and of the pre-registered verdict logic. Never runs Site04 and never calls the runner."""
import os
import sys
import types
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim"))
import round3_site04 as R  # noqa: E402


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
    def test_refuses_without_tag(self):
        self.assertIn("does not exist", R.check_frozen(fake_git(tag=None), csv_exists=False))

    def test_refuses_off_the_tagged_commit(self):
        self.assertIn("not the commit", R.check_frozen(fake_git(tag="aaa", head="bbb"), csv_exists=False))

    def test_refuses_dirty_frozen_files(self):
        self.assertIn("uncommitted", R.check_frozen(fake_git(tag="aaa", head="aaa", dirty=True), csv_exists=False))

    def test_refuses_rerun(self):
        self.assertIn("forbids re-running", R.check_frozen(fake_git(tag="aaa", head="aaa"), csv_exists=True))

    def test_allows_clean_first_run(self):
        self.assertIsNone(R.check_frozen(fake_git(tag="aaa", head="aaa"), csv_exists=False))


def frame(values):
    rows = []
    for (cond, cfg), v in values.items():
        rows.append(dict(condition=cond, config=cfg, label="aware", success_pct=v, missed_fault_pct=5.0))
    return pd.DataFrame(rows)


class VerdictTests(unittest.TestCase):
    base = {}
    for c in (R.CL, R.X4, R.X8, R.X16):
        base.update({(c, "tolerance"): 50.0, (c, "tolerance + noise floor"): 90.0, (c, "pitfal"): 70.0, (c, "trust2"): 85.0,
                     (c, "wait"): 60.0, (c, "wait + terrain_R"): 70.0, (c, "ml"): 50.0, (c, "ml + terrain_R"): 60.0})

    def test_all_met(self):
        v = R.verdicts(frame(self.base))
        self.assertTrue(all(ok for ok, _ in v.values()), v)

    def test_q1_fails_when_gain_small(self):
        b = dict(self.base)
        b[(R.X8, "tolerance + noise floor")] = 55.0
        self.assertFalse(R.verdicts(frame(b))["Q1"][0])

    def test_q2_fails_when_below_pitfal_at_x16(self):
        b = dict(self.base)
        b[(R.X16, "tolerance + noise floor")] = 60.0
        self.assertFalse(R.verdicts(frame(b))["Q2"][0])

    def test_q4_fails_when_terrain_gain_small(self):
        b = dict(self.base)
        b[(R.X8, "ml + terrain_R")] = 52.0
        self.assertFalse(R.verdicts(frame(b))["Q4"][0])

    def test_q5_uses_missed_fault_rate(self):
        df = frame(self.base)
        df.loc[(df.condition == R.SHADOW_NOISY) & (df.config == "trust2"), "missed_fault_pct"] = 42.0
        self.assertFalse(R.verdicts(df)["Q5"][0])


if __name__ == "__main__":
    unittest.main()
