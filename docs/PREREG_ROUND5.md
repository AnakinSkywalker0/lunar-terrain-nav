# Round 5 pre-registration (21 Nov 2026) - DRAFT, NOT FROZEN, NOT RUN

**Status:** drafted by the build session after the owner asked for it. It becomes binding only when the owner reads it, edits it if needed, commits it together with `sim/engine.py`, `sim/round5_heldout.py`, `sim/round5_dev.py`, `sim/round5_train.py`, and tags that commit `prereg-round5`. Nothing has been committed, tagged or run on the reserved worlds.
Freeze and run (owner, from a clean tree):
```
git add docs/PREREG_ROUND5.md sim/engine.py sim/round5_heldout.py sim/round5_dev.py sim/round5_train.py tests/test_round5_switches.py tests/test_round5_heldout_guards.py
git commit -m "Freeze round-5 pre-registration"
git tag prereg-round5
python sim/round5_heldout.py --allow-heldout
```
Simulation only. "PITFAL-style" is our reimplementation; the three-beam, 22.5 degree geometry and the second-sensor and camera-error models are assumptions. Constants are untuned (as in rounds 3 and 4).

## What is tested
Procedural worlds **41-50** (ten worlds; never used for training, tuning, development or any earlier round; a search of sim/, tools/ and tests/ on 21 Nov 2026 found no use). Seed 20261221, 200 descents per cell, confidence-gated camera (except where stated), noise-aware fault label.
* **Three beams** (independent AND common-mode beam faults): cliff + faults at nominal noise, x4, x8, x16 noise below 6000 m. Rules: **PITFAL-style multi-beam** (baseline, `pitfal_mb`), **A** = floor in gate and update + footprint terrain, **B** = floor in the update only + footprint terrain, **S** = Student-t weighting (4 dof) + floor in both + footprint terrain (the candidate).
* **Single beam:** cliff + faults, x8, x16, delayed readings without time stamps, 100 m map offset, 2 km map offset. Rules: PITFAL-style, **A1s** = tolerance + noise floor (round-3 rule), **St** = Student-t (4 dof) + floor, **De** = tolerance + floor + delay estimation (no time stamps), **Cs** = tolerance + floor + soft camera weighting (cliff and x8 only), and the IMM-style noise-mode rule as a reference row (not a hypothesis).
Definitions are the entries with those names in `sim/round5_dev.py`, frozen with it.

## Disclosure (everything seen before these rules)
`docs/ROUND5_DEV_RESULTS.md`: nine development cells (procedural 11-16, Site01), 100 descents each, about ten candidates compared; the winners are therefore optimistic. Student-t (three beams) averaged 94% (worst cell 87%) against 90% (69%) for PITFAL-style multi-beam and 93% (76%) for B; on world 12 at x4 it reached 61-63%, B 93%, A 7%, PITFAL-style 81-84%. Delay estimation: 4% to 54% (true stamps 90%). Soft camera: cliff 92 to 100, x8 87 to 100. Student-t with one beam: x16 93 against 82. Failures seen: Student-t with stuck-at faults (64%), conformal gate limits, CUSUM; every rule fails with the 2 km wrong map (at most 31%). Round-4 held-out worlds 17-20 and Site04 are used and are not part of this test.

## Decision rules (scored on the mean over worlds 41-50; three-beam rules must hold in BOTH independent and common-mode faults)
* **S1 (safe at low and middle noise):** S is no more than 3 points below PITFAL-style multi-beam at cliff + faults, x4 and x8.
* **S2 (high-noise value):** S is at least 3 points above PITFAL-style multi-beam at x16.
* **S3 (better than the floor at low noise):** S is at least 3 points above A at cliff + faults, x4 and x8.
* **S4 (no collapse):** S scores at least 50% in every world at cliff + faults and x4 (independent faults). A failure is reported as a failure; world-12-like terrain is not guaranteed to occur.
* **S5 (delay estimation):** De is at least 20 points above A1s for delayed readings without time stamps.
* **S6 (soft camera):** Cs is at least 3 points above A1s at cliff + faults and at x8 (single beam).
* **S7 (single-beam Student-t):** St is at least 3 points above A1s at x16.
Everything not listed is exploratory and labelled so, including B versus S, the IMM-style row, and every comparison of any pair not named above.

## Known weaknesses to report whatever the outcome (not hypotheses)
Stuck-at faults (Student-t has no hard gate), a 2 km wrong map, the missed-fault percentage not being comparable for Student-t (no accept/reject decision), overconfident estimates (NEES), the assumed three-beam geometry, no real sensor data, no new real site (a PGDA download was not requested), second altimeter and map-offset search not tested.

## Reporting
Per-world tables with Wilson intervals (`out/round5/heldout.csv`), a verdict per rule (met / failed) with the values, everything that did not improve, and what was not tested. Held-out set run once; no rerun and no post-hoc rule changes. Differences of a few points per cell are within noise; the world is the unit of evidence (ten worlds).
