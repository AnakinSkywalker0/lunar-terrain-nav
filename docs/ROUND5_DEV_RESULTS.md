# Round 5 development comparison (21 Nov 2026) - exploratory

Source: `docs/LANTERN_Architecture_and_Build_Plan.docx`, Section 4. Every technique is a default-off switch in `sim/engine.py` (bit-identical when off, `tests/test_round5_switches.py`), run on the nine development cells
(procedural 11-13 and Site01 at seed 7, 11-12 at seed 202, 14-16 at seed 101), 100 descents per cell, confidence-gated camera, noise-aware fault label. Untuned constants, no tuning budget given to any arm.
Data: `out/round5/dev_single.csv`, `dev_multi.csv`; summaries `summary_means.csv`, `summary_paired.csv` (`python sim/round5_analyze.py`).
Training / calibration (selector, conformal limits) used NEW worlds 27-32 only (`sim/round5_train.py`). Worlds 41-50, 17-20 and Site04 were not touched. Simulation only; nothing here is a pre-registered result.
**Selection warning:** about ten candidates were compared on nine cells, so the best looking one is optimistic (winner's curse). Only a fresh pre-registered run can confirm any of this.

## Single-beam altimeter (mean landing success %, 9 cells)
| Rule | Cliff+faults | x8 noise | x16 noise | Delayed, no stamps | Dropout | Stuck-at | Drift | 2 km wrong map |
|---|---|---|---|---|---|---|---|---|
| PITFAL-style (baseline) | 84 | 70 | 40 | 0 | 54 | 80 | 78 | 4 |
| A: tolerance + noise floor (round 3) | 92 | 87 | 82 | 4 | 70 | 90 | 94 | 17 |
| A3 IMM-style noise modes | **97** | **93** | **94** | 5 | **74** | 92 | **97** | 9 |
| B2 Student-t (4 dof) + floor | 94 | **94** | 93 | 3 | 70 | 64 | 95 | 19 |
| B3 CUSUM + floor | 85 | 64 | 57 | 4 | 69 | 83 | 92 | 31 |
| B1 conformal gate limit (92) | 74 | 90 | 88 | 3 | 68 | 27 | 94 | 14 |
| A4 delay estimation (no stamps) | - | - | - | **54** | - | - | - | - |
| A5 map-offset search | 90 | 84 | - | - | - | - | - | 23 |
| B4 soft camera weighting + floor | **100** | **100** | - | - | - | - | - | - |
| B8 second altimeter + floor (assumed) | 93 | 86 | 83 | 83* | **89** | 91 | 92 | 4 |
| Oracle noise (not flyable) | 89 | 92 | 91 | 1 | 66 | 87 | 75 | 4 |
\* B8's second altimeter is modelled as not delayed, so 83% is an artefact of that assumption, not a result. Scale-factor and shadow rows are in `summary_means.csv` (shadow: floor 87, IMM 93, Student-t+floor 94, soft camera 100).

Paired difference to rule A (bootstrap over cells, `summary_paired.csv`): IMM-style +4 (cliff), +6 (x8), +11 (x16), -8 (2 km map); Student-t+floor +1, +7, +10; soft camera +8 (cliff), +13 (x8, shadow); delay estimation +50 (delayed, no stamps).

## Three-beam altimeter (mean landing success %, independent faults)
| Rule | Cliff+faults | x4 | x8 | x16 | One beam drops out | 2 km wrong map |
|---|---|---|---|---|---|---|
| PITFAL-style multi-beam (baseline) | 92 | 96 | 98 | 69 | 94 | 4 |
| A: floor in gate and update + footprint terrain | 85 | 79 | 88 | 98 | 85 | 6 |
| B: floor in update only + footprint terrain | 97 | **98** | **98** | 76 | **98** | 10 |
| A1 joint three-beam update | 83 | 79 | 87 | 98 | 83 | 6 |
| A2 learned gate selector | 85 | 79 | 88 | 98 | 85 | 5 |
| B1 conformal gate limit (19.5) | 82 | 79 | 86 | 98 | 82 | 9 |
| B2 Student-t (4 dof) + floor | **99** | 92 | 96 | **99** | 91 | 6 |
| B7 solution separation | 83 | 79 | 87 | 98 | 83 | 6 |
| Oracle noise (not flyable) | 93 | 78 | 82 | 96 | 94 | 5 |
Averaged over the noise and fault conditions (without the 2 km map), mean / worst cell: Student-t+floor 94 / 87, B 93 / 76, PITFAL-style 90 / 69, A 87 / 79. Common-mode faults give the same picture (`summary_means.csv`).

## What each technique did
* **Worked (exploratory):** delay estimation without time stamps (4% to 54%; mean lag error 1.4 steps; true stamps give 90%); soft camera weighting (cliff 92 to 100, x8 87 to 100, shadow 87 to 100); IMM-style noise modes and Student-t weighting at high noise with one beam (+10 to +11 at x16); Student-t weighting with three beams, the best mean and best worst case of the nine rules (+5 to +14 over rule A at low and middle noise).
* **Partly:** Student-t on the collapsing world 12 (x4): 61-63% against 7% for rule A, 93% for rule B and 81-84% for PITFAL-style, so it avoids most but not all of the collapse. Map-offset search found the 2 km offset in about a third of the descents (32%) and adopted a wrong offset in others; 2 km map success 17 to 23%, still failing. Stuck-at faults hurt Student-t (64%) because it has no hard gate.
* **No gain:** joint three-beam update (-0.4 to -2); learned gate selector (99.9% accurate on held-back training worlds but the floor gate was right on 99% of disagreement rows, so it behaves like always-floor); conformal limits (single beam -18 at cliff, stuck-at 27%: a 92 limit lets faults in); solution separation (identical to the joint update in every cell: it never fired once the floor gate had screened the beams).
* **Harmful:** CUSUM (38% of valid readings rejected; -23 at x8 and -25 at x16 with one beam).
* **Second altimeter (assumed model):** dropout 70 to 89; no help elsewhere; its dissimilar-hardware assumptions decide the result.
* **Consistency (NEES, 3 dof, ideal about 3):** every rule is overconfident; Student-t+floor with three beams 370 vs PITFAL-style 5793; single beam A 144, IMM-style 478.
* **Missed-fault percentages are not comparable** for Student-t (it has no accept/reject decision, so every faulty reading counts as accepted).

## Not done
B5 (point-mass filter) and B6 (learned gain, KalmanNet): each a week or more; the plan's own note says an earlier learned noise model did not beat the running estimate. Time to detect, protection levels, per-pixel map error and the 2 km map in the three-beam search were not built. A5 and the solution-separation exclusion are first versions (single-fault only).

## Consequences
1. One rule does not win everywhere; the earlier round-4 finding stands. Student-t weighting is the first candidate that is near the top in nearly every cell, and it is the natural pre-registered candidate for a fresh set of worlds (41-50) and a new real site, with rule B, rule A and PITFAL-style multi-beam as comparators.
2. Delay estimation and soft camera weighting are cheap single-purpose additions worth their own pre-registered rules.
3. No candidate solves the 2 km wrong map; say so in the report.
