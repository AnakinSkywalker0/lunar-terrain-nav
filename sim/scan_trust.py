"""Inference-only scan trust gate. No training, truth inputs or model loading.

This is a Python integration boundary, not a live Unity controller. The caller
must supply a separately validated scan-specific model and its metadata.
"""
from dataclasses import dataclass
import math

TASK = "scan_absolute_error_over_10m_v1"
FEATURES = ("points", "rms_m", "confidence", "dx", "dz", "correction_norm_m")


def features_from_match(match):
    """Only fields available from LocalScanMatcher before applying correction."""
    values = tuple(float(match[k]) for k in FEATURES[:-1])
    return values + (math.hypot(values[3], values[4]),)


@dataclass(frozen=True)
class TrustDecision:
    accept: bool
    reason: str
    bad_score: float | None = None


class ScanTrustGate:
    """Optional learned veto on top of the frozen geometric gate.

    No model: preserves geometric acceptance. With a model: both gates must
    accept. Scores are not called probabilities of correctness without separate
    calibration evidence. A model cannot promote a geometrically rejected scan.
    """

    def __init__(self, model=None, metadata=None):
        self.model = model
        self.threshold = None
        if model is None:
            if metadata is not None:
                raise ValueError("Metadata supplied without a model")
            return
        metadata = metadata or {}
        if metadata.get("task") != TASK or tuple(metadata.get("features", ())) != FEATURES:
            raise ValueError("Wrong task or feature schema; altimeter models are incompatible")
        if not metadata.get("model_id"):
            raise ValueError("A versioned model_id is required")
        if int(getattr(model, "n_features_in_", -1)) != len(FEATURES):
            raise ValueError("Model feature count differs from schema")
        if tuple(getattr(model, "classes_", ())) != (0, 1):
            raise ValueError("Class order must be [0=safe, 1=error>10m]")
        self.threshold = float(metadata["bad_score_threshold"])
        if not math.isfinite(self.threshold) or not 0 < self.threshold < 1:
            raise ValueError("Threshold must be finite and strictly between zero and one")

    def decide(self, features, *, valid, geometric_accept):
        if len(features) != len(FEATURES) or not all(math.isfinite(float(x)) for x in features):
            return TrustDecision(False, "invalid_features")
        if not valid or not geometric_accept:
            return TrustDecision(False, "geometric_reject")
        if self.model is None:
            return TrustDecision(True, "geometric_only_no_model")
        try:
            scores = self.model.predict_proba([features])
            if len(scores) != 1 or len(scores[0]) != 2:
                raise ValueError("Expected one binary score row")
            safe, bad = map(float, scores[0])
            if (not all(math.isfinite(x) and 0 <= x <= 1 for x in (safe, bad))
                    or abs(safe + bad - 1) > 1e-6):
                raise ValueError("Invalid binary scores")
        except Exception:
            return TrustDecision(False, "inference_failure")
        return TrustDecision(bad < self.threshold,
                             "learned_accept" if bad < self.threshold else "learned_veto", bad)
