"""Tests of the round-5 held-out runner's refusals, plan and verdict logic. Never runs the held-out set."""
import os
import sys
import types
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim"))
import round5_heldout as R  # noqa: E402
import round5_dev as D  # noqa: E402


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

    def test_reserved_worlds_and_registry_names(self):
        self.assertEqual(R.SEEDS, tuple(range(41, 51)))
        self.assertFalse(set(R.SEEDS) & {11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32})
        for name in (R.PB, R.A, R.B, R.S):
            self.assertIn(name, D.MULTI)
        for name in R.SINGLE_PLAN:
            self.assertIn(name, D.SINGLE)
        for c in R.SINGLE_CONDS:
            self.assertIn(c, D.SINGLE_CONDS)


def frame(s_over=0.0, worst=95.0, de=60.0, cs=100.0, st=95.0):
    rows = []
    for md in ("independent", "common"):
        for c in R.CONDS:
            base = 60.0 if c == "x16" else 90.0
            for cfg, v in ((R.PB, base), (R.A, 99.0 if c == "x16" else 80.0), (R.B, base), (R.S, base + s_over + (5 if c == "x16" else 0))):
                for w in (41, 42):
                    val = worst if (cfg == R.S and c in ("cliff", "x4") and w == 41 and md == "independent") else v
                    rows.append(dict(part="multi", fault_mode=md, condition=c, config=cfg, world=w, success_pct=val))
    for c, vals in (("cliff", {R.SA: 90.0, R.CS: cs}), ("x8", {R.SA: 80.0, R.CS: cs}), ("x16", {R.SA: 70.0, R.ST: st}), ("delayed_nots", {R.SA: 4.0, R.DE: de})):
        for cfg, v in vals.items():
            rows.append(dict(part="single", fault_mode="single", condition=c, config=cfg, world=41, success_pct=v))
    return pd.DataFrame(rows)


class VerdictTests(unittest.TestCase):
    def test_all_met_when_the_candidate_is_clearly_better(self):
        df = frame(s_over=10.0)
        v = R.verdicts(df)
        self.assertTrue(all(ok for ok, _ in v.values()), v)

    def test_s1_fails_when_far_below_the_baseline_at_low_noise(self):
        df = frame(s_over=-10.0)
        self.assertFalse(R.verdicts(df)["S1"][0])

    def test_s3_fails_without_a_margin_over_the_floor(self):
        df = frame(s_over=0.0)
        df.loc[(df.config == R.A) & df.condition.isin(["cliff", "x4", "x8"]), "success_pct"] = 90.0      # the floor is level with S at low noise
        self.assertFalse(R.verdicts(df)["S3"][0])

    def test_s4_reports_a_collapsing_world(self):
        self.assertFalse(R.verdicts(frame(s_over=10.0, worst=20.0))["S4"][0])

    def test_single_beam_rules(self):
        v = R.verdicts(frame(s_over=10.0, de=20.0, cs=91.0, st=71.0))
        self.assertFalse(v["S5"][0])
        self.assertFalse(v["S6"][0])
        self.assertFalse(v["S7"][0])


if __name__ == "__main__":
    unittest.main()
