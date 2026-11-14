"""Train/serve consistency checks for the 'ml2' judge. Run: python sim/check_ml2.py   (about 1-2 minutes)

(a) History features: the engine computes them step by step from a ring buffer (ml_features.history_features). Training
    computed them offline over whole sequences (ml_labels.persistence). They must agree row for row.
(b) Base features: ml_features.base_features (used in flight) must equal the features the model was trained on
    (ml_eval.features_v2 on top of engine._features) on REAL filter states from a short simulation.
Exit code 0 = all good. A mismatch would silently feed the model wrong inputs, so run this after touching any feature code.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import ml_features as MF  # noqa: E402
import ml_labels as L  # noqa: E402  (also patches engine._features to the offline version; restored below)
import ml_eval as E  # noqa: E402


def check_history():
    rng = np.random.default_rng(0)
    n, T = 60, 400
    flagged = rng.random((n, T)) < 0.18
    z = rng.standard_normal((n, T)) * 4.0
    # offline: build the row table exactly as ml_labels does
    rr, tt = np.nonzero(flagged)
    X = np.zeros((len(rr), L.N2 + 8), dtype=np.float32)
    X[:, 0] = z[rr, tt]; X[:, L.N2] = rr; X[:, L.N2 + 1] = tt
    off = L.persistence(X)
    # online: ring buffer, step by step
    buf = np.full((n, MF.WINDOW), np.nan)
    on = np.zeros_like(off)
    k = 0
    lookup = {}
    for t in range(T):
        h = MF.history_features(z[:, t], buf)
        for i in np.nonzero(flagged[:, t])[0]:
            lookup[(i, t)] = h[i]
        buf = MF.push_history(buf, flagged[:, t], z[:, t])
    for j in range(len(rr)):
        on[j] = lookup[(rr[j], tt[j])]
    err = np.abs(on - off).max()
    print(f"(a) history features: {len(rr)} rows, max abs difference online vs offline = {err:.2e}")
    assert err < 1e-4, "history features differ between flight and training"


def check_base():
    import world as W
    w = W.procedural(11, 2.0, 270.0); tr = W.track_for(w)
    seen = []
    saved = engine._features                    # ml_labels patched it at import; restored in the finally block

    def both(nu, S0, R, stats, x_est, rad, agl_true, nu_hist):
        off = E.features_v2(nu, S0, R, stats, x_est, rad, agl_true, nu_hist)       # what the model was trained on
        on = MF.base_features(nu, S0, R, stats, x_est, rad, agl_true, nu_hist)     # what flight code computes
        seen.append(np.abs(off - on).max())
        return off
    engine._features = both
    try:
        sc = engine.SCENARIOS["cliff_fault"]
        d = engine.Draws(w, sc, 12, 3)
        col = []
        engine.simulate(w, tr, sc, "pitfal", d, collect=col, K_prob=10, sigma_probation=4.0)
    finally:
        engine._features = saved
    print(f"(b) base features: {len(seen)} calls on real filter states, max abs difference = {max(seen):.2e}")
    assert len(seen) > 0 and max(seen) < 1e-3, "base features differ between flight and training"


if __name__ == "__main__":
    check_history()
    check_base()
    print("ALL CHECKS PASSED")
