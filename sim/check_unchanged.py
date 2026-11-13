"""Regression check: do the EXISTING judges still behave exactly as before the ml2 edit to sim/engine.py?

  python sim/check_unchanged.py            full check, about 10 minutes (7 judges x 2 scenarios, 30 descents each)
  python sim/check_unchanged.py --quick    pitfal + tolerance on one scenario, about 1-2 minutes

The reference tests/ref_old_judges.npz was produced with the UNMODIFIED engine (commit 08458d2, the state of main) on
procedural world 11, seed 3, tuned K_prob=10, sigma_probation=4.0, camera policy 'conf'.
Exit 0 = identical. Tiny differences can appear with a different numpy/scipy build; large differences mean a real change.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import world as W  # noqa: E402

REF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "ref_old_judges.npz")


def main():
    quick = "--quick" in sys.argv
    ref = np.load(REF)
    w = W.procedural(11, 2.0, 270.0); tr = W.track_for(w)
    scens = ["cliff_fault"] if quick else ["cliff_fault", "delayed"]
    judges = ["pitfal", "tolerance"] if quick else ["fixed", "pitfal", "tolerance", "wait", "second", "ml", "trust2"]
    bad = 0
    for scen in scens:
        sc = engine.SCENARIOS[scen]
        for j in judges:
            d = engine.Draws(w, sc, 30, 3)
            r = engine.simulate(w, tr, sc, j, d, K_prob=10, sigma_probation=4.0, cam_policy="conf")
            same = (np.array_equal(r["success"], ref[f"{scen}_{j}_success"]) and
                    np.allclose(r["miss_m"], ref[f"{scen}_{j}_miss"], atol=1e-6) and
                    np.allclose(r["impact_vz"], ref[f"{scen}_{j}_vz"], atol=1e-6))
            print(f"  {scen:12s} {j:10s} landed {int(r['success'].sum()):2d}/30  {'identical' if same else 'DIFFERENT'}", flush=True)
            bad += not same
    print("UNCHANGED: all judges identical to the reference" if bad == 0 else f"CHANGED: {bad} judge/scenario pairs differ")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
