# Pre-registration for evaluation round 3 (FROZEN at git tag `prereg-round3`, 20 Nov 2026)

Status: frozen 20 Nov 2026 by committing this file with the engine, runner and tests and tagging that commit `prereg-round3`. Nothing here had been run on Site04 at the time of the freeze. Round 1 stays at tag `round1`, round 2 at tag `prereg-round2`.

## Why round 3
Round 2 (`PREREG.md`) found that the map in the filter does most of the work and that the plain map-tolerance gate collapses with a noisy altimeter (48.2% at x8 on the tuning worlds). The ml-eval study and the 20 Nov engine work (`fault_label_noise_aware`, `terrain_R`, `tol_noise_floor` in `sim/engine.py`, all default off) found three changes that carry most of the gain without machine learning. Round 3 tests them once on the held-out site.

## What changed since round 2 (and what was already seen)
1. **Candidate judge:** the tolerance gate with a running noise floor, `judge="tolerance"`, `tol_noise_floor=True` (trust v2's innovation-size estimate `s_hat` in the gate and in the measurement variance). Constants are those already in the engine (gate 6.635, `s_hat` update 0.97/0.03); no new tuning.
2. **Terrain variance on unflagged readings:** `terrain_R=True` for the `wait` and `ml` judges.
3. **Scoring:** false rejection and missed faults use the noise-aware ground-truth label (`fault_label_noise_aware=True`). The old label is also reported for continuity. Landing success does not depend on the label (checked: identical in every tuning cell).

Seen before this draft (disclosure):
* Tuning worlds (procedural 11-13, Site01), seed 7, 100 descents: all candidate results (`out/round3/candidates_tune.csv`, `label_effect_tune.csv`).
* Fresh procedural worlds 14-16 (seed 101) and the tuning worlds re-seeded (202): all candidate results (`out/round3/fresh.csv`). Decision rules R1 and R2 were written in `sim/round3_fresh.py` before that run and both were met.
* Round-2 Site04 results for PITFAL-style, tolerance, wait, trust v1/v2 (`out/mc/`). No Site04 number exists for any round-3 switch.
* The ml-eval tables (reproduced 19-20 Nov); ml2 itself is not a round-3 candidate.

## Frozen settings (proposed; owner to confirm)
* Judges: `pitfal`, `trust2`, `tolerance`, `tolerance + noise floor` (candidate), `wait`, `wait + terrain_R`, `ml`, `ml + terrain_R` (old random forest, `out/mc/ml_model.pkl`). Every judge gets the confidence-gated camera.
* Site: Site04 only, run once. No tuning on Site04. Tuning and fresh worlds are already used up for this decision.
* Conditions (as in the ml-eval study): cliff + faults at nominal noise; shadow + noisy altimeter at x2, x4, x8 and x16 noise; x8 below 2500 m; plus delayed altimeter with time stamps for every judge (so the comparison is fair) and altimeter dropout as an exploratory condition.
* n = 500 runs per cell, seed 20261201 (new; round 2 used 20260101), 95% Wilson intervals.
* Success: vertical speed <= 2 m/s, horizontal <= 1.5 m/s, slope <= 10 degrees, fuel > 0 (as in round 2).
* Code freeze: the commit tagged `prereg-round3` must contain `sim/engine.py`, the Site04 runner and this file. The runner must refuse to run without `--allow-site04` and without that tag (to be written before the freeze; none exists yet).

## Primary hypotheses and decision rules (Site04, all judges with the same camera)
* **Q1** The candidate beats plain tolerance by at least 10 points of landing success at each of x4, x8 and x16.
* **Q2** The candidate is at or above PITFAL-style at x8 and x16 and no more than 3 points below it in cliff + faults at nominal noise.
* **Q3** The candidate is no more than 3 points below trust v2 in cliff + faults at nominal noise and at or above trust v2 at x8 (the fresh-world margin was +4.0, so this is a weak test and is stated as such).
* **Q4** `wait + terrain_R` and `ml + terrain_R` each beat their plain judge by at least 5 points at nominal noise and at x8.
* **Q5** (scoring) With the noise-aware label, trust v2's missed-fault rate in shadow + noisy is below 10% (tuning worlds: 1.0%; old label: 42.5%). If it is not, the label change is not the explanation and this is reported as unexplained.
Everything not listed is exploratory and labelled so, including the delayed and dropout conditions, the shifted-map and no-map checks, and comparisons of any pair not named above.

## Known weaknesses to report whatever the outcome (not hypotheses)
* A map shifted by 2 km and a noisy altimeter in good light were the round-2 failures of trust v2; the candidate has not been tested against a wrong map. Report it as untested, not as solved.
* Delayed readings without time stamps fail for every judge.
* Simulation only; point-mass lander; one real unseen site; rule constants untuned; differences of about 4 points per cell are within noise.

## Procedure
1. Owner resolves the open decisions below and edits this file.
2. Write the Site04 runner with the two refusals above; run `lantern-verify` checks (`check_unchanged.py` full, unit tests, `tests/test_round3_switches.py`).
3. Commit, tag `prereg-round3`, run Site04 once. No re-runs after seeing results; report failures.
4. Report each Q1-Q5 as met, failed or mixed, with the intervals.

## Decisions (owner accepted the proposals on 20 Nov 2026; the document is still NOT frozen)
* [x] Judge list, conditions, n = 500 and seed 20261201 as proposed above.
* [x] The candidate's constants stay untuned (no tuning pass).
* [x] The noise-aware label stays behind the `fault_label_noise_aware` switch (earlier tags keep reproducing).
* [x] The three switches are not made defaults now; revisit only after the round-3 result.
* [x] A shifted-map condition is not in the primary set; it stays exploratory (see Known weaknesses).

Done: the Site04 runner `sim/round3_site04.py` exists with its refusals (flag, tag, HEAD == tag, clean frozen files, no re-run) and computes the Q1-Q5 verdicts; `tests/test_round3_site04_guards.py` checks the refusals and the verdict logic without running Site04. Still needed before the freeze: the full `check_unchanged.py` and the unit tests, then the owner commits and tags `prereg-round3`. Nothing has been committed or tagged.
