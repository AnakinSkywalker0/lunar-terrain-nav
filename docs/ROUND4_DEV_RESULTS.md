# Round 4 development results (20 Nov 2026) - EXPLORATORY, tuning and fresh worlds only

Not pre-registered. Site04 not touched. Simulation only; PITFAL-style and the beam geometry (3 beams, 22.5 deg, assumed) are our interpretations.
Plan: `docs/NEXT_DIRECTION_REVIEW_AND_BUILD.md` Part C. Code: new default-off switches in `sim/engine.py`, plus `sim/round4_dev.py`, `sim/round4_ar1.py`,
`sim/round4_terrain_audit.py`. Data: `out/round4/dev_single.csv` (891 rows), `dev_multi.csv` (720), `dev_ar1.csv` (378), `terrain_stats.csv`,
`footprint_audit.csv`. 100 descents per cell, 9 world/seed cells (procedural 11-13 and Site01 at seed 7, 11 and 12 again at seed 202, fresh 14-16 at seed 101).

Checks run: `tests.test_round4_switches` (8), `tests.test_round4_audit` (1), `tests.test_round3_switches`, `tests.test_multibeam` (26 tests together, all OK);
`sim/check_unchanged.py` full and quick: UNCHANGED. The VB-AKF equations were read from the author PDF. Differences: the noise scale is kept in units of the nominal
variance, the estimate is floored at the nominal variance, the fixed point is in closed form, 3 iterations.

## 1. The earlier world-12 explanation is not supported
Multi-beam, independent faults, procedural world 12, success %: plain tolerance 97-100; floor in both 43-48 (cliff) and 6 (x4); floor in gate only 36-38 and 0-5;
floor in update only 98-100; **oracle noise (the true noise level, not deployable) 97-99 at nominal noise and 7 at x4.**
The oracle collapses where the floor collapses, so the floor is not "mistaking mismatch for noise". Any gate widened to the right noise size lets harmful readings in
on that world at x4, while the tight gate acts as a terrain-consistency filter there. Static terrain statistics do not single world 12 out (it has the lowest median slope
of the tuning worlds; `terrain_stats.csv`). Terrain spread where the canted beams land is 4-15 times the spread under the vehicle at 3000 m height in every procedural world
(`footprint_audit.csv`), so the nadir terrain variance is a poor stand-in at altitude.

## 2. Multi-beam, mean success % over the 9 cells (independent faults; common-mode faults are within a few points of these)
| Arm | cliff | x4 | x8 | x16 |
|---|---|---|---|---|
| pitfal_mb | 92 | 96 | 98 | 69 |
| tolerance_mb | 93 | 98 | 73 | 45 |
| + floor (both) | 85 | 78 | 91 | 99 |
| + floor (both) + footprint terrain | 85 | 79 | 88 | 98 |
| + floor (update only) | 98 | 99 | 79 | 61 |
| + floor (update only) + footprint terrain | 97 | 98 | 98 | 76 |
| + floor (gate only) | 75 | 67 | 70 | 60 |
| + oracle noise (not deployable) | 93 | 78 | 82 | 96 |

Fresh worlds 14-16 only: floor (both) + footprint terrain 99 / 100 / 100 / 100; pitfal_mb 99 / 100 / 98 / 66; update-only + footprint 99 / 100 / 99 / 76.
Reading: no arm wins everywhere. Floor in both gives the high-noise gain but collapses on world 12. Floor in the update only plus footprint terrain is safest at low and
middle noise and beats pitfal_mb at x16 by about 7 points, but gives up most of the x16 gain. A 2 km wrong map: every arm 0-12%.

## 3. Single beam, mean success % over the 9 cells
| Arm | cliff | x4 | x8 | x16 | wrong 100 m | delayed + stamps | dropout |
|---|---|---|---|---|---|---|---|
| tolerance | 89 | 69 | 45 | 39 | 56 | 86 | 66 |
| floor (both) | 92 | 93 | 87 | 82 | 65 | 90 | 70 |
| floor (update only) | 93 | 88 | 68 | 53 | 56 | 91 | 71 |
| floor (gate only) | 89 | 71 | 47 | 28 | 55 | 84 | 65 |
| oracle noise | 89 | 94 | 92 | 91 | 56 | 86 | 66 |
| second-difference floor (both) | 93 | 93 | 92 | 92 | 65 | 87 | 68 |
| VB-AKF | 92 | 89 | 79 | 71 | 61 | 89 | 69 |
| pitfal | 84 | 84 | 70 | 40 | 61 | 70 | 54 |
| trust2 | 92 | 86 | 79 | 62 | 62 | 84 | 63 |

Single beam: the floor in both places is close to the oracle, does not make a 100 m map error worse (65 against 56 for plain tolerance), and does not help a 2 km error
(about 17% at best). Delayed readings without time stamps: every arm 0-4%.

## 4. Correlated altimeter noise (AR(1), same variance), single beam, success %
| Arm | x4 phi 0.5 | x4 phi 0.9 | x8 phi 0.5 | x8 phi 0.9 | x16 phi 0.5 | x16 phi 0.9 |
|---|---|---|---|---|---|---|
| floor (both), innovation | 83 | 48 | 81 | 51 | 79 | 52 |
| second-difference floor | 79 | 28 | 82 | 26 | 85 | 30 |
| oracle noise | 86 | 48 | 87 | 55 | 89 | 60 |
| VB-AKF | 79 | 41 | 72 | 43 | 63 | 39 |
| trust2 | 82 | 47 | 74 | 49 | 56 | 39 |

The map-independent second-difference estimator matches the innovation floor with white noise but fails with strongly correlated noise (phi 0.9), as theory predicts
(variance underestimated about 14 times). It works only when the noise is close to white, so Direction 2 as specified is not supported.

## 5. Not done
Direction 3 (new real sites, clone-DEM map errors, per-cause error rates) needs a PGDA download: file, source, size and terms first. The 100 m shift was tested only as
an altimeter map offset. Per-world tables are in the CSVs. At n = 100 a cell has a 95% interval of roughly 3-10 points.
