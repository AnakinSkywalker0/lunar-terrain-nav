# Round 6: 6-DOF lander dynamics (21 Nov 2026) — exploratory, development worlds only

Code: `sim/dyn6.py` (rigid body, one body-fixed engine), switch `dyn6=` in `sim/engine.py` (default off, bit-identical when off; test `tests/test_dyn6.py`).
Study: `sim/round6_dyn6.py` → `out/round6/dyn6_dev.csv`; analysis `sim/round6_analyze.py` → `dyn6_means.csv`, `dyn6_paired.csv`.
Worlds: development set only (procedural 11-16, Site01); never Site04, never 17-20 or 41-50. n = 60 descents per cell, 9 worlds, 3 noise conditions.
Nothing here is pre-registered. Every vehicle number is ASSUMED (see the top of `sim/dyn6.py`). Not modelled: fuel slosh, flex, engine transients, plume, gear crush.

## What the model adds over the point mass
Thrust only along the body axis (sideways acceleration needs a tilt), throttle lag 0.3 s, torque-limited attitude control (800 N m), inertia that follows the mass,
thrust misalignment and centre-of-mass offset, gyro + star-tracker attitude estimate, accelerometer rotated with the ESTIMATED attitude, body-fixed altimeter beams
(the filter predicts the range along the estimated beam direction), reaction-control propellant. Touchdown also needs tilt ≤ 12° and body rate ≤ 5°/s.
Guidance is unchanged, except that the commanded thrust direction is kept within 35° of vertical.

## Result 1: with the default vehicle the ranking of the rules holds
Mean landing success (%), mean over 9 development worlds:

| | 3-DOF | 6-DOF default |
|---|---|---|
| single beam, x16: PITFAL-style / floor A / Student-t | 44 / 82 / 93 | 34 / 76 / 75 |
| three beams, x16: PITFAL-style / floor A / Student-t | 73 / 98 / 99 | 69 / 100 / 100 |
| three beams, cliff: PITFAL-style / floor A / Student-t | 92 / 86 / 99 | 100 / 100 / 100 |

* Three beams, x16: floor A and Student-t are +30 points above the PITFAL-style rule (95 % interval 26 to 34), as in 3-DOF (+26).
* Single beam, x16: floor A +43 points over PITFAL-style (31 to 51); Student-t +42 (26 to 55).
* The low-noise edge of Student-t over floor A seen in 3-DOF (three beams, cliff +13.5) is gone in 6-DOF (-0.4). This agrees with the round-5 held-out result, where that edge did not replicate.
* Single-beam Student-t is NOT better than floor A under 6-DOF at x8 (75.7 vs 83.9) and cliff (76.3 vs 81.1), the opposite of 3-DOF. Single-beam landing is lower than in 3-DOF in 8 of 9 rule-and-noise cells, by up to 20 points (Student-t loses the most).
* Three-beam landing is higher in 6-DOF than in 3-DOF at low noise. My explanation (not tested): the old model applies noisy guidance commands instantly and fails mostly on touchdown sideways speed; the attitude and throttle lag smooth the commands. Do not read it as "6-DOF is easier".

## Result 2: the two stressed vehicles are not flyable with this guidance, so they say nothing about the rules
| variant | landing (all rules) | tilt at touchdown (median) | attitude error (deg RMS) | crashes |
|---|---|---|---|---|
| sluggish (torque 150 N m, throttle lag 1 s) | 3 to 11 % | 36° | 0.04 | 62 % |
| degraded (misalignment 0.5°, CoM 8 cm, gyro-only, gyro bias 0.05°/s) | 0 to 0.4 % | 25° | 7.4 | 88 % |

* Sluggish: the attitude loop is too slow for the guidance gains (tilt up to 83°); a vehicle like this would need slower guidance. Degraded: with no star tracker the attitude estimate drifts to about 7°, the rotated accelerometer then corrupts the navigation filter and the vehicle crashes whatever the altimeter rule is.
* The rule differences in these two variants are all within noise because everything fails. This is a result about guidance and attitude sensing, not about the altimeter rules.

## What this means
* The altimeter-rule conclusions (floor and Student-t far better than PITFAL-style at high noise; no reliable low-noise edge of Student-t) survive a 6-DOF vehicle with a working attitude loop and star tracker.
* The conclusions say nothing about vehicles whose attitude control or attitude sensing is poor: there the whole descent fails first. A real design would need guidance tuned to the vehicle and an attitude estimator the navigation filter accounts for (the filter's process noise does not include attitude error).
* Single-beam rules are sensitive to the dynamics model; three-beam rules much less.
* Limits: simulation only, development worlds only, assumed vehicle numbers, tilt cap and touchdown limits are my choices, one set of guidance gains, 60 descents per cell. `sim/engine.py` now differs from the commit tagged `prereg-round5` (default-off switch only; the round-5 held-out result is unaffected and its runner refuses a re-run).
