# Round 5 held-out results (21 Nov 2026)

Run once from the frozen commit `f742d08` (tag `prereg-round5`): procedural worlds 41-50, seed 20261221, 200 descents per cell, three beams (assumed geometry) with independent and common-mode faults, plus the single-beam rules. Data: `out/round5/heldout.csv`, log `out/round5/logs/heldout_run.log`. Simulation only. No rerun and no rule change after seeing the results.

## Verdicts (mean over worlds 41-50; difference in points)
| Rule | Verdict | Values (independent / common) |
|---|---|---|
| S1 Student-t not more than 3 below PITFAL-style multi-beam at cliff, x4, x8 | **MET** | cliff -1.3 / +4.5, x4 +1.6 / +1.9, x8 -0.3 / +1.1 |
| S2 Student-t at least 3 above it at x16 | **MET** | +18.8 / +20.7 |
| S3 Student-t at least 3 above the full floor (A) at cliff, x4, x8 | **NOT met** | -4.3 / -1.9, -2.6 / -3.0, -2.7 / -1.8 (Student-t is slightly below A) |
| S4 Student-t at least 50% in every world at cliff and x4 | **MET** | lowest world 56% (worlds 41 and 44 are the hard ones) |
| S5 Delay estimation at least 20 points above the floor rule with no stamps | **MET** | +49.3 (50.8% against 1.5%) |
| S6 Soft camera at least 3 points above the hard cut at cliff and x8 | **NOT met** | cliff +2.8 (just short), x8 +9.3 |
| S7 One-beam Student-t at least 3 above the floor at x16 | **MET** | +8.8 (86.0% against 77.3%) |

## Mean landing success (%), three beams, independent faults (common-mode faults give the same picture)
| Condition | PITFAL-style multi-beam | A: floor both | B: floor update only | S: Student-t + floor |
|---|---|---|---|---|
| cliff + faults | 89.0 | 92.0 | 91.2 | 87.7 |
| x4 | 89.8 | 94.0 | 91.2 | 91.4 |
| x8 | 89.6 | 92.0 | 88.1 | 89.3 |
| x16 | 68.6 | 88.4 | 71.4 | 87.4 |

## Mean landing success (%), single beam
| Condition | PITFAL-style | Floor (A1s) | Student-t + floor | IMM-style (reference) | Delay est. | Soft camera |
|---|---|---|---|---|---|---|
| cliff | 78.8 | 88.6 | 87.7 | 90.9 | - | 91.5 |
| x8 | 66.9 | 81.7 | 86.5 | 87.4 | - | 91.0 |
| x16 | 34.6 | 77.3 | 86.0 | 85.7 | - | - |
| delayed, no stamps | 0.2 | 1.5 | 0.8 | 1.6 | 50.8 | - |
| 100 m map offset | 56.2 | 63.2 | 75.4 | 66.4 | - | - |
| 2 km map offset | 1.4 | 4.0 | 3.6 | 5.4 | - | - |

## Reading
* **Replicated:** Student-t weighting matches the PITFAL-style rule at low and middle noise and beats it by about 19-21 points at x16; one-beam Student-t beats the floor at x16 by 9 points; delay estimation without time stamps lifts landing from about 1.5% to 51% (true stamps gave 90% in development); soft camera weighting helps (+9 points at x8, +2.8 at cliff, just under the 3-point margin).
* **Did not replicate:** the development edge of Student-t over the full floor at low noise. On these worlds the full floor (A) was 2 to 4 points better than Student-t at cliff, x4 and x8, and the two were level at x16. The development numbers were optimistic, as the disclosure warned.
* **Unplanned observation (exploratory, not a hypothesis):** the full floor in both places (A) was the best three-beam rule on average here (92 / 94 / 92 / 88) and did not collapse on any of these worlds; the floor in the update only (B) lost 17 points at x16. Worlds 41, 44 and 47 are the hard ones for every rule (56-76% for Student-t at cliff and x4).
* **Still open:** the 2 km wrong map (at most 5%), delayed readings without time stamps beyond what delay estimation recovers (51% against 90% with true stamps), stuck-at faults for Student-t (development finding; not retested here), estimate overconfidence (NEES).
* **Not tested:** a new real site, real sensor data, the second altimeter, the map-offset search.
