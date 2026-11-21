# Round 4 held-out results (20 Nov 2026)

Run once from the frozen commit `36e2942` (tag `prereg-round4`): procedural worlds 17-20, seed 20261215, 200 descents per cell, three-beam altimeter (assumed geometry), independent and common-mode beam faults. Data: `out/round4/heldout.csv`, log `out/round4/logs/heldout_run.log`. Simulation only. No rerun and no rule change after seeing the results.

## Verdicts (mean over worlds 17-20; difference in points)
| Rule | Verdict | Values |
|---|---|---|
| R1 B not worse than pitfal_mb by more than 3 at cliff, x4, x8 | **NOT met** | cliff +4.5 / +3.5, x4 +2.5 / +4.0, **x8 -5.1 / -4.8** (independent / common) |
| R2 B at least 3 above pitfal_mb at x16 | **NOT met** | **-3.1 / -5.6** |
| R3 A not worse than pitfal_mb by more than 3 at cliff, x4 | **MET** | +2.9 / +4.0, +3.6 / +6.4 (no world-12-like collapse occurred) |
| R4 single-beam floor not worse than plain tolerance with 100 m map offset | **MET** | +12.5 (68.2% vs 55.8%) |

## Mean landing success (%), independent / common faults
| Condition | pitfal_mb | B (update only) | A (both) | tolerance_mb | floor both, nadir terrain* | oracle* |
|---|---|---|---|---|---|---|
| cliff + faults | 73.6 / 73.1 | 78.1 / 76.6 | 76.5 / 77.1 | 79.9 / 76.2 | 80.4 / 80.1 | 79.9 / 76.2 |
| x4 | 78.8 / 76.1 | 81.2 / 80.1 | 82.4 / 82.5 | 77.8 / 78.6 | 84.5 / 84.9 | 83.4 / 84.4 |
| x8 | 79.2 / 79.6 | 74.1 / 74.9 | 84.6 / 82.5 | 60.2 / 60.2 | 84.8 / 82.4 | 85.1 / 84.9 |
| x16 | 63.5 / 63.1 | 60.4 / 57.5 | 80.2 / 79.8 | 38.1 / 36.6 | 80.5 / 81.4 | 83.1 / 81.5 |
\* reference rows, not hypotheses (oracle is not deployable).

## Reading
* The pre-registered candidate B **failed**: the high-noise gain seen in development (76% vs 69% at x16) did not replicate (about 59% vs 63%), and B was 5 points below pitfal_mb at x8. Development gains on nine cells were not a reliable guide.
* The collapse feared for the floor in both places (A) did **not** appear on worlds 17-20; A was 3 to 6 points above pitfal_mb at low noise and 17 points above at x16. This is unplanned for x8/x16 and exploratory only. Whether world-12-like terrain exists elsewhere is unknown.
* World 20 is the hard world: pitfal_mb scored 26-37% there at low noise while the tolerance-based rules scored 44-78%; world 19 is near 100% for all rules. Per-world spread is large; differences of a few points per cell are within noise.
* Single beam with a 100 m map offset: the floor was 12.5 points better than plain tolerance (68.2% vs 55.8%), consistent with development.
* Not tested: 2 km wrong map, delayed readings without time stamps, real terrain other than Site01/Site04, real sensor data. The three-beam geometry and the PITFAL-style consensus are our assumptions/interpretation.
