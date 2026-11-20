# Round 4 pre-registration (20 Nov 2026) - READY TO FREEZE, NOT YET FROZEN

**Status:** the owner chose candidate B and reserved procedural seeds 17-20 (20 Nov 2026, in chat). This file becomes binding only when the owner commits it together with
`sim/engine.py`, `sim/round4_heldout.py`, `sim/round4_dev.py` and tags that commit `prereg-round4`. The build session has NOT committed, tagged or run the held-out set.
Freeze and run (owner, from a clean tree):
```
git add docs/PREREG_ROUND4.md sim/engine.py sim/round4_heldout.py sim/round4_dev.py tests/test_round4_heldout_guards.py tests/test_round4_switches.py
git commit -m "Freeze round-4 pre-registration"
git tag prereg-round4
python sim/round4_heldout.py --allow-heldout
```
Simulation only. PITFAL-style is our interpretation of a method with no released code; the 3-beam, 22.5 degree geometry is assumed.

## What is tested
Procedural worlds **17, 18, 19, 20** (never used for training, tuning, development or any earlier round; a search of sim/, tools/, tests/, the docs and result files on 20 Nov 2026 found no use).
Seed 20261215, 200 descents per cell, confidence-gated camera, noise-aware fault label. Multi-beam (3 beams): independent AND common-mode beam faults; conditions cliff + faults
(nominal noise), x4, x8, x16 below 6000 m. Single beam: cliff + faults with a 100 m altimeter map offset.
Candidates (all existing default-off switches in the frozen `sim/engine.py`): **B** = multi-beam tolerance, noise floor in the update variance only, terrain variance at the beam footprint;
**A** = floor in both gate and update, terrain variance at the beam footprint. Baseline: `pitfal_mb`. Reference rows (not hypotheses): plain `tolerance_mb`, floor in both with nadir terrain, oracle noise (not deployable).
Single beam: `tolerance` and `tolerance` + floor in both. Constants are untuned (as in round 3).

## Disclosure (everything seen before these rules)
`docs/ROUND4_DEV_RESULTS.md`: worlds 11-16 and Site01 were used in development (14-16 also in round 3). Candidate B scored 97 / 98 / 98 / 76% (cliff / x4 / x8 / x16) against 92 / 96 / 98 / 69% for
`pitfal_mb` on the 9 development cells. Candidate A collapses on development world 12 (6% at x4). The oracle also collapses there. The single-beam 100 m offset gave 65% (floor) against 56% (plain).
Site04 was not used.

## Decision rules (scored on the mean over worlds 17-20, separately for independent and common-mode faults; every listed difference must hold in both modes)
* **R1 (safe at low and middle noise):** B is no more than 3 points below `pitfal_mb` at cliff + faults, x4 and x8.
* **R2 (high-noise value):** B is at least 3 points above `pitfal_mb` at x16.
* **R3 (collapse check):** A is no more than 3 points below `pitfal_mb` at cliff + faults and x4. Expected to fail if world-12-like terrain occurs in the held-out set; a failure is reported as a failure.
* **R4 (no harm from a map shift):** single-beam floor in both places is no more than 3 points below plain `tolerance` with a 100 m altimeter map offset.

## Reporting
Per-world tables with Wilson intervals (`out/round4/heldout.csv`), a verdict per rule (met / failed), everything that did not improve, and what was not tested (2 km wrong map, delayed readings without time stamps,
real terrain other than Site01/Site04, real sensor data). Held-out set run once; no rerun and no post-hoc rule changes. Differences of a few points per cell are within noise.
