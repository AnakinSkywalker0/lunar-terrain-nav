# Round 3 results: noise floor, terrain variance and noise-aware label (20 Nov 2026)

Pre-registration: [PREREG_ROUND3.md](PREREG_ROUND3.md), frozen at git tag `prereg-round3` (commit `e63c7a6`) before this run. Site04 was run once with
`python sim/round3_site04.py --allow-site04` (500 descents per cell, seed 20261201, confidence-gated camera for every judge, time stamps for every judge in the
delayed condition). Data: `out/round3/site04.csv`; logs: `out/round3/logs/`. Simulation only.

## What was tested
Three default-off switches in `sim/engine.py`: `tol_noise_floor` (the tolerance judge uses trust v2's running noise estimate), `terrain_R` (terrain and map
variance on unflagged readings for `wait`, `second`, `ml`) and `fault_label_noise_aware` (bookkeeping only). They came from the ml-eval study (merged into `main`
as PR #1 and #2) and were screened on the tuning worlds, then checked on fresh procedural worlds 14-16 (`out/round3/candidates_tune.csv`, `fresh.csv`; rules R1
and R2 written in `sim/round3_fresh.py` before that run and both met).

## Verdicts on the pre-registered rules (Site04)
All five were met.
* **Q1 met.** The noise floor beats plain tolerance by +17.0, +33.0 and +48.0 points at x4, x8 and x16 noise (rule: at least +10 each).
* **Q2 met.** It is above PITFAL-style by +29.0 at x8, +52.2 at x16 and +14.2 in cliff + faults at nominal noise.
* **Q3 met, a weak test.** It is +2.4 above trust v2 in cliff + faults (rule: no more than 3 below) and +5.6 above at x8. A 2.4-point gap is within noise.
* **Q4 met.** `wait + terrain_R` gains +13.0 (nominal) and +22.0 (x8); `ml + terrain_R` gains +14.2 and +8.6 (rule: at least +5 each).
* **Q5 met.** Trust v2's missed-fault rate in shadow + noisy x8 is 6.6% with the noise-aware label (rule: below 10%). With the old label it is far higher.

## Landing success (%), Site04, 500 descents per cell (95% intervals about plus or minus 2 to 4 points)
| Condition | pitfal | trust2 | tolerance | tolerance + noise floor | wait | wait + terrain_R | ml | ml + terrain_R | second | second + terrain_R |
|---|---|---|---|---|---|---|---|---|---|---|
| cliff + faults (nominal noise) | 83.4 | 95.2 | 97.0 | 97.6 | 83.0 | 96.0 | 76.0 | 90.2 | 9.0 | 11.0 |
| x2 below 6000 m | 81.8 | 96.2 | 91.2 | 96.0 | 75.8 | 92.4 | 61.0 | 73.4 | 36.2 | 42.6 |
| x4 below 6000 m | 84.8 | 94.6 | 78.0 | 95.0 | 62.2 | 92.0 | 28.6 | 28.4 | 25.4 | 34.6 |
| x8 below 6000 m (TRAINING) | 65.6 | 89.0 | 61.6 | 94.6 | 33.4 | 55.4 | 24.2 | 32.8 | 17.4 | 29.4 |
| x16 below 6000 m | 38.6 | 57.2 | 42.8 | 90.8 | 18.0 | 35.2 | 18.0 | 22.6 | 11.2 | 16.6 |
| x8 below 2500 m | 76.6 | 96.2 | 88.2 | 97.2 | 53.8 | 73.0 | 45.0 | 48.4 | 30.0 | 36.0 |
| delayed altimeter (time-stamped for every judge) | 70.8 | 86.8 | 96.0 | 96.4 | 77.8 | 94.0 | 72.2 | 92.2 | 63.4 | 82.8 |
| altimeter dropout (exploratory) | 33.6 | 37.4 | 44.6 | 49.6 | 29.2 | 37.2 | 25.2 | 32.2 | 25.6 | 34.2 |

## Effect of the fault label on the bookkeeping columns (success is identical either way)
| Condition | Judge | False rejection % (old label) | False rejection % (noise-aware) | Missed fault % (old label) | Missed fault % (noise-aware) |
|---|---|---|---|---|---|
| cliff + faults (nominal noise) | pitfal | 0.5 | 0.5 | 7.7 | 7.7 |
| cliff + faults (nominal noise) | tolerance | 0.2 | 0.2 | 7.2 | 7.2 |
| cliff + faults (nominal noise) | tolerance + noise floor | 0.2 | 0.2 | 10.5 | 10.5 |
| cliff + faults (nominal noise) | trust2 | 1.7 | 1.7 | 6.1 | 6.1 |
| x8 below 6000 m (TRAINING) | pitfal | 3.9 | 20.6 | 32.8 | 7.8 |
| x8 below 6000 m (TRAINING) | tolerance | 5.8 | 19.4 | 40.9 | 8.1 |
| x8 below 6000 m (TRAINING) | tolerance + noise floor | 0.1 | 4.2 | 74.5 | 9.8 |
| x8 below 6000 m (TRAINING) | trust2 | 3.7 | 13.7 | 52.6 | 6.6 |

## What did not improve, and limits
* `second` (second opinion) is still poor; `ml` still fails at x4, and `ml + terrain_R` gains nothing there (28.4 against 28.6). Neither is a rule.
* The noise-floor judge lets through more faults than the others in the table: missed faults are 10.5% in cliff + faults and 9.8% at x8 (trust v2: 6.1% and 6.6%). It trades some fault rejection for far fewer false rejections.
* Altimeter dropout (exploratory) stays low for every judge (49.6% for the best).
* Not tested: a shifted or wrong map, and delayed readings without time stamps, for the new switches.
* One run on one real site in simulation; the constants were not tuned; the earlier tuning and fresh-world numbers were seen before the freeze (disclosed in the pre-registration). Site04 cannot be rerun under the pre-registration.
* The noise-aware label changes only false-rejection and missed-fault columns; round-1 and round-2 tables keep the old label, which overstates missed faults and understates false rejections at high noise.
