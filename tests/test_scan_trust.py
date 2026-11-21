"""Contract tests using a score stub, not a trained model."""
import unittest
from sim.scan_trust import FEATURES, TASK, ScanTrustGate, features_from_match


class ScoreStub:
    n_features_in_ = len(FEATURES)
    classes_ = (0, 1)

    def __init__(self, score):
        self.score = score
        self.calls = []

    def predict_proba(self, rows):
        self.calls.append(rows)
        return [[1 - self.score, self.score]]


class ScanTrustTests(unittest.TestCase):
    def setUp(self):
        self.x = features_from_match(dict(points=560, rms_m=1, confidence=.9, dx=-60, dz=40,
                                         proposed_error_m=9999, condition="truth_only"))
        self.metadata = dict(task=TASK, features=list(FEATURES), model_id="test_stub_only",
                             bad_score_threshold=.25)

    def test_only_runtime_features(self):
        self.assertEqual(self.x[:5], (560., 1., .9, -60., 40.))
        self.assertAlmostEqual(self.x[-1], (60**2 + 40**2)**.5)

    def test_no_model_preserves_gate(self):
        gate = ScanTrustGate()
        for valid in (False, True):
            for accepted in (False, True):
                self.assertEqual(gate.decide(self.x, valid=valid, geometric_accept=accepted).accept,
                                 valid and accepted)

    def test_learned_veto_and_accept(self):
        for score, accept in ((.1, True), (.25, False), (.8, False)):
            stub = ScoreStub(score)
            gate = ScanTrustGate(stub, self.metadata)
            self.assertEqual(gate.decide(self.x, valid=True, geometric_accept=True).accept, accept)
            self.assertEqual(stub.calls, [[self.x]])

    def test_geometric_reject_cannot_be_promoted(self):
        stub = ScoreStub(0)
        self.assertFalse(ScanTrustGate(stub, self.metadata).decide(
            self.x, valid=True, geometric_accept=False).accept)
        self.assertEqual(stub.calls, [])

    def test_altimeter_task_and_schema_rejected(self):
        for metadata in ({**self.metadata, "task": "altimeter_fault"},
                         {**self.metadata, "features": ["truth_error"]}):
            with self.assertRaises(ValueError):
                ScanTrustGate(ScoreStub(.1), metadata)

    def test_feature_count_and_classes_rejected(self):
        for field, value in (("n_features_in_", 8), ("classes_", (1, 0))):
            stub = ScoreStub(.1)
            setattr(stub, field, value)
            with self.assertRaises(ValueError):
                ScanTrustGate(stub, self.metadata)

    def test_nonfinite_scores_fail_closed(self):
        for score in (float("nan"), float("inf"), -1, 2):
            result = ScanTrustGate(ScoreStub(score), self.metadata).decide(
                self.x, valid=True, geometric_accept=True)
            self.assertFalse(result.accept)
            self.assertEqual(result.reason, "inference_failure")

    def test_nonfinite_features_fail_closed(self):
        self.assertFalse(ScanTrustGate().decide(self.x[:-1] + (float("nan"),),
                                              valid=True, geometric_accept=True).accept)


if __name__ == "__main__":
    unittest.main()
