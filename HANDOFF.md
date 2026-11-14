# Handoff: new ML judge on branch `ml-eval` (14 Nov 2026)

**For:** the person who owns the simulator (`sim/engine.py`).  **From:** the ML-side contributor, with Claude's help.
**Status:** the first version of this work was merged into `main` through PR #1 (14 Nov, by the ML-side contributor, no review). Everything in the UPDATE section below is only on branch `ml-eval` (ahead of `main`, merges cleanly). Please review before relying on any of it. All of it is simulation only; Site04 has not been touched.

## In five lines
1. We re-examined the random-forest "fault vs terrain" classifier (the `ml` judge) and found its **training label was wrong** in the noisy-altimeter scenario, its inputs were thin, and its quoted accuracy is a best-case world.
2. We built a corrected version: new label, 22 features (map consistency, vertical speed, 10 s history of flagged readings), a small model (`models/fault_clf_v3.pkl`, 0.5 MB).
3. We added a new judge **`ml2`** to `sim/engine.py` (additive; all existing judges are bit-identical, see step 2 below).
4. In flight the new classifier ALONE did not help, but the investigation found what does (see UPDATE): the terrain-variance fix, an adaptive measurement-noise estimate, and the classifier's accept/reject decision. The resulting `ml2` structure beats PITFAL by about 15 landing-success points on average on worlds it was never tuned on and is level with or ahead of trust v2 under noise. **A simple non-ML noise rule matches our learned noise model**, so the learning part of the noise model is not what helps.
5. Site04 has NOT been touched. A round-3 pre-registration is needed before Site04 is run again (step 6).

## UPDATE (second session): what actually helps, with the controls that changed the picture
`ml2` (hard mode + terrain-variance fix, `ml2_terrain_R`) with a measurement-noise floor for accepted readings. Three ways of setting that floor were compared:
none; the **learned error-size model** (`models/err_reg_v3.pkl`: predicts `log1p(|error| / nominal sigma)`, median |error|/prediction 0.95-1.02 on an unseen world; floor `(nominal sigma * expm1(pred))^2`,
for flagged readings, and with `ml2_noise_normal=True` also unflagged ones); and a **non-ML control**, `ml2_noise_heuristic=True`: the running innovation-size estimate `s_hat` that trust v2 already uses (floor `s_hat^2`).
Landing success %, 100 descents per world, confidence-gated camera, tuning worlds only. Noise conditions are `shadow_noisy` variants (x2/x4/x8/x16 below 6000 m AGL, x8 below 2500 m); x8 below 6000 m is the only noise level the models were trained on.

### A. Tuning worlds (procedural 11-13 + Site01), seed 7 (`out/ml2/noise_normal.csv`, `control_noise.csv`)
| Condition | PITFAL | trust v2 | non-ML control | learned, flagged only | learned, flagged + unflagged |
|---|---|---|---|---|---|
| cliff + faults (nominal noise) | 89.2 | 96.0 | 93.2 | 93.5 | 95.0 |
| x2 | 87.2 | 92.0 | 93.0 | 88.2 | 94.0 |
| x4 | 88.2 | 88.8 | 90.5 | 73.0 | 92.0 |
| x8 (training level) | 77.0 | 78.0 | 91.0 | 69.8 | 84.0 |
| x16 | 45.2 | 62.8 | 89.0 | 63.5 | 87.2 |
| x8 below 2500 m | 87.5 | 91.2 | 89.5 | 87.5 | 90.5 |

### B. Fresh worlds, `sim/ml2_fresh.py` (`out/ml2/fresh.csv`): procedural worlds 14-16 (never used for training or tuning), seed 101, plus the four tuning worlds with a new seed 202; 7 world runs pooled
| Condition | PITFAL | trust v2 | non-ML control | learned, flagged + unflagged |
|---|---|---|---|---|
| cliff + faults | 83.3 | 91.6 | 88.9 | 93.4 |
| x2 | 81.6 | 90.4 | 90.6 | 93.0 |
| x4 | 83.0 | 84.3 | 87.7 | 91.7 |
| x8 | 70.1 | 81.0 | 89.0 | 78.9 |
| x16 | 40.0 | 63.6 | 85.1 | 83.9 |
| x8 below 2500 m | 78.7 | 88.9 | 88.4 | 89.6 |

Cell by cell (42 cells): learned minus PITFAL +15.6 on average (positive in 35); learned minus trust v2 +5.1 (positive in 27); **learned minus non-ML control +0.1 (positive in 20)**. The fresh worlds are harder for every judge (PITFAL cliff + faults 77.0 on worlds 14-16 vs about 88 on the tuning worlds).

### C. Is the classifier needed? `sim/ml2_ablate.py` (`out/ml2/ablate.csv`): non-ML structure with the classifier's decision replaced by a constant; tuning worlds, seed 7
| Condition | full control (classifier at 0.5) | accept ALL flagged readings | reject ALL flagged readings |
|---|---|---|---|
| cliff + faults | 93.2 | 34.0 | 94.0 |
| x2 | 93.0 | 47.5 | 93.2 |
| x4 | 90.5 | 64.0 | 68.8 |
| x8 | 91.0 | 75.2 | 44.5 |
| x16 | 89.0 | 80.0 | 36.5 |
| x8 below 2500 m | 89.5 | 70.5 | 82.0 |

### What this means
1. The gain is not an artefact of the four tuning worlds or one seed: on fresh worlds the `ml2` structure still beats PITFAL by a wide margin and is level with or ahead of trust v2 in most cells.
2. **The learned noise model does not beat a simple running noise estimate** (A, B). The learned version is ahead at nominal and low noise (about +4 to +5 points at cliff, x2, x4 in both groups of worlds), the running estimate is ahead at high noise (x8: +10 on fresh worlds, and the learned model is worse than the control at the very noise level it was trained on). They look complementary; a combined floor (the larger of the two) is untested.
3. **The classifier does real work inside this structure** (C): accept-all collapses with faults (34%), reject-all collapses with high noise (44.5% at x8, 36.5% at x16), only the classifier version stays at 89-93% everywhere. At nominal/low noise "reject all" is as good, which fits your finding that the map in the filter does most of the work. We have NOT shown a non-ML gate cannot do the classifier's job; a gate that adapts to the noise level is untested.
4. **What probably transfers to your judges regardless of ML:** (i) terrain+map variance on unflagged readings (the `ml` / `wait` / `second` branch used the bare altimeter noise; adding it lifted the OLD `ml` judge from 78.5 to 90.2 in cliff + faults), (ii) a running innovation-size noise floor like trust v2's `s_hat` (lifts `ml2` from about 47 to 91 at x8 on the tuning worlds).
5. Not run on Site04. Fresh worlds are procedural; Site01 is the only real terrain, with fresh draws only. Differences of about 4 points per cell are within noise. Several variants were compared on the tuning worlds before the fresh test.

Scripts: `ml2_noise_normal.py` (6-condition grid), `ml2_control_noise.py` (non-ML control), `ml2_fresh.py` (fresh worlds), `ml2_ablate.py` (classifier ablation), plus the earlier `ml2_x4.py`, `ml2_noise_levels.py`, `ml2_noise.py` (thresholds, unseen noise levels, the x4 investigation: other thresholds and soft mode did not help; the terrain-variance fix is essential, x4 drops from 73% to 56% without it).

## What we found (details and tables: `out/ml_eval*/`, `out/ml_labels/`, `out/ml_faults/`)
| Finding | Evidence |
|---|---|
| The fault label at `engine.py:335` (`fault_lbl`) uses the *nominal* noise. In `shadow_noisy` (noise x8, `engine.py:328`) **63.7% of valid, fault-free readings are labelled "fault"** (only 12.2% of rows have an injected burst). | `out/ml_labels/label_audit.csv` |
| Same label in the delayed scenario: only 1.5% of rows are injected faults, 33.6% of the others are stale readings labelled "fault". | same file |
| The committed classifier score (AUC 0.967, 89.5%) is the best of 6 worlds; leave-one-world-out gives AUC 0.930 +/- 0.032, accuracy 0.857. 73% of its training rows come from the delayed scenario. | `out/ml_eval/` |
| With the corrected label, history + vertical-speed features raise the mean per-scenario AUC from 0.960 to 0.982 (delayed 0.903 to 0.954). The gain holds on fault shapes never seen in training (constant offset, small offset, drift, spike). | `out/ml_labels/arms.csv`, `out/ml_faults/summary.csv` |
| The original two terrain features carry no signal in the cliff scenarios (AUC ~0.5 alone). | `out/ml_labels` / ablation in the log |

## What is in the branch
| Path | What |
|---|---|
| `sim/engine.py` | **Edited (32 added, 3 changed lines).** New judge `ml2`, new keyword `ml2_mode="soft"|"hard"`, a 40-step history buffer. Read it with `git diff main..ml-eval -- sim/engine.py`. |
| `sim/ml_features.py` | The 22 flight features. Does not import the engine. |
| `models/fault_clf_v3.pkl` | Trained model (scikit-learn HistGradientBoosting). Trained with scikit-learn 1.9.1 / numpy 2.5.4 / Python 3.14. If it will not load on your versions, regenerate it with `python sim/ml_train.py` (needs the cached rows; about 15 min the first time). |
| `sim/ml_train.py`, `ml_eval.py`, `ml_labels.py`, `ml_faults.py` | Training and the offline experiments. |
| `sim/check_ml2.py` | Checks flight features == training features (history 5e-7, base features exact). |
| `sim/check_unchanged.py`, `tests/ref_old_judges.npz` | Proves the old judges still give identical results. |
| `sim/ml2_compare.py` | Runs `ml2` against the other judges on the **tuning worlds only**. |
| `sim/ml2_diagnose.py`, `sim/ml2_control.py` | The 2x2 diagnostic (vertical-only / terrain variance) and the control with the old random forest. The old forest `out/mc/ml_model.pkl` is untracked: regenerate with `python sim/pipeline.py ml` (about 9 min). |
| `sim/ml_train_noise.py`, `models/err_reg_v3.pkl` | Trains / holds the error-size model (560 KB). Regenerate with `python sim/ml_train_noise.py` (needs the cached rows, see `ml_train.py`). |
| `sim/ml2_control_noise.py`, `sim/ml2_fresh.py`, `sim/ml2_ablate.py` | Non-ML control, fresh-worlds test, classifier ablation (tables above). The engine switch `ml2_noise_heuristic` is the non-ML control. |
| `sim/ml2_noise_normal.py` (**key**), `sim/ml2_noise_levels.py`, `sim/ml2_x4.py`, `sim/ml2_noise.py` | The learned-noise experiments: the 6-condition confirmation grid, unseen noise levels, the x4 investigation, thresholds. |
| `out/ml_*/`, `out/ml2/` | Result tables and plots. |

How `ml2` decides: for every reading that fails the 99% gate it asks the model for the probability `p` that the reading is a fault.
`soft` (default): accept the reading but multiply its noise variance by `1/(1-p)^2` (so `p=0.9` means 100x less weight).
`hard`: reject if `p > 0.5`, otherwise accept with the same terrain-variance inflation the old `ml` judge used.

## Steps for you (in this order)
Assume a Python 3 environment with numpy, scipy, pandas, scikit-learn, matplotlib, Pillow, and the NASA files in `data/`.
1. **Read the engine diff** (about 15 minutes): `git fetch && git diff main..origin/ml-eval -- sim/engine.py`. Tell us if you want any of it done differently.
2. **Check nothing else changed:** `python sim/check_unchanged.py` (10 min; `--quick` for 2 min) should end with `UNCHANGED`. Then `python sim/check_ml2.py` should end with `ALL CHECKS PASSED`.
3. **Reproduce the key results first** (each 8-35 min, 4 workers, one at a time on a 16 GB machine): `python sim/ml2_noise_normal.py` (table A), `python sim/ml2_control_noise.py` (non-ML control), `python sim/ml2_fresh.py` (table B), `python sim/ml2_ablate.py` (table C). Then, if you like, the older comparison: `python sim/ml2_compare.py --n 100` (about 15 min), then `--n 500` for paper-size numbers. Uses 4 workers; on a 16 GB machine do not go above 6. Output: `out/ml2/compare_tune.csv`.
4. **Judge the result.** Do you reproduce the table above? If yes, we need your view on the suspected causes (in particular the horizontal-position hypothesis, which you know best) before spending more time on the model. The questions are in the next section.
5. **Fix the simulator's own label** (`fault_lbl`, `engine.py:335`) so it compares with the actual noise level, as `sim/ml_labels.py` does. This changes the "false rejection" and "missed fault" columns in your tables, so decide how to report it. We did not edit it.
6. **If ml2 helps: write a round-3 pre-registration** (new file, like `docs/PREREG.md`) *before* any Site04 run: the judges, `ml2_mode`, the model file, and the decision rules. Then freeze, tag, and run Site04 once.

## Questions we need you to answer
* Is the `engine.py` edit acceptable as written? Prefer a different hook?
* Do you know a real altimeter failure shape we have not simulated? **"Stuck at last value" is not covered** (it needs the true range at run time).
* Should the delayed scenario treat a stale reading as a fault? Today it is labelled one; trust v2 instead compensates using time stamps.
* Do you want `ml2` in the paper as a new judge, or as an improved version of the `ml` judge?
* Would you add a terrain-variance term and a running noise floor (trust v2's `s_hat`) to the `ml` / `wait` / `second` branch, or to the tolerance gate? Our results suggest those two changes, not learning, carry most of the gain.

## Rules
* **Do not run Site04** (`--allow-site04`) before step 6. It is the only unseen real site.
* Do not tune on Site04. Do not move or delete the git tags `round1` and `prereg-round2`.
* `models/fault_clf_v3.pkl` and `models/err_reg_v3.pkl` were trained on procedural worlds 21-26 only.

## Caveats (please keep them in the write-up)
* Offline AUC is not landing success. Nothing proves `ml2` lands more often until step 3 is done.
* The model was scored against a label we defined (error > 5 x true noise sigma + 1 m).
* Simulated faults are bursts only; the tests cover 5 shapes, not stuck values or real altimeter physics.
* One simulator, procedural training worlds, unvalidated against real flight data.
* The `ml_*` experiment scripts read the simulator's internals with a frame-inspection hack (`sys._getframe`) to get ground truth without editing `engine.py`. It is for analysis only; the flight path (`ml_features.py`) does not use it.

## First flight result (tuning worlds: procedural 11-13 + Site01, 100 descents each, seed 7, confidence-gated camera)
Landing success %, mean of the 4 worlds (about +-4 points at 50%; single worlds +-10). Source: `out/ml2/compare_tune.csv`.

| Judge | cliff + faults | shadow + noisy | delayed (no time stamps for ml/ml2) |
|---|---|---|---|
| PITFAL-style | 89.2 | 77.0 | 0.5 |
| map tolerance | 92.0 | 48.2 | 1.0 |
| wait and see | 88.8 | 40.0 | 2.0 |
| trust v2 | **96.0** | **78.0** | **87.2** (uses time stamps) |
| `ml` (old random forest) | 78.5 | 37.0 | 1.2 |
| `ml2_hard` (new) | 79.8 | 44.2 | 0.8 |
| `ml2_soft` (new) | 77.8 | 44.8 | 0.5 |

Reading it honestly: `ml2` is about 7-8 points better than the old `ml` in shadow + noisy, equal to it in cliff + faults, and **10-20 points below PITFAL, tolerance and trust v2** in both. It does nothing for delayed readings. (The `missed fault 100%` shown for `ml2_soft` is a bookkeeping artefact: soft mode accepts every flagged reading by design.)

### What we know and what we only suspect (diagnostic on world 11, cliff + faults, 100 descents)
* Known: the ML judges fail by **rough landings** (slope or horizontal speed), not by crashing: vertical speed at touchdown is about 0.6 m/s for every judge. Pitfal 86 landed / 14 rough; old `ml` 65 / 34 rough / 1 crash; `ml2_hard` 66 / 33 rough / 1 crash. The old and the new classifier behave alike, so the classifier's inputs are not the bottleneck.
* Known: altitude error is the same as PITFAL for the old `ml` (21.5 vs 21.6 m RMS) but 70 m for `ml2_hard` on this world, so `ml2_hard` has some large altitude errors that we have not explained.
* Suspected before testing (outcome of the tests in the list below): (1) accepted "terrain" readings at cliffs are also used for horizontal position through the map-gradient term, which is wrong at a jump, so they corrupt the position and the lander ends up on rough ground; PITFAL and the tolerance gate handle those readings differently. (2) The model was trained on filter states produced by the PITFAL run, not by its own decisions (train/deploy mismatch). (3) In `engine.py` the `ml`, `wait` and `second` judges use plain noise `R` for unflagged readings, whereas `tolerance` and `trust` add terrain variance; this is structural and may explain part of the gap.
* The suspicions were then tested (`sim/ml2_diagnose.py`, `sim/ml2_control.py`, `out/ml2/diagnose.csv`, `out/ml2/control.csv`; same worlds, same seed, `ml2_hard` reproduced 79.8 / 44.2 exactly):

| Landing success % (mean of 4 tuning worlds) | cliff + faults | shadow + noisy |
|---|---|---|
| PITFAL-style (reference) | 89.2 | 77.0 |
| old random forest `ml` | 78.5 | 37.0 |
| old `ml` **+ terrain variance on unflagged readings** | **90.2** | 48.5 |
| `ml2_hard` (new classifier) | 79.8 | 44.2 |
| `ml2_hard` + vertical-only update for accepted flagged readings | 75.5 | 37.8 |
| `ml2_hard` + terrain variance | 87.2 | 47.2 |
| `ml2_hard` + both | 85.5 | 49.0 |

  Conclusions: (1) the horizontal-position hypothesis is **refuted** (vertical-only made it worse and raised altitude RMS from 40 to 110 m); (2) the main cause of the weak `ml` judges is **in the engine, not the classifier**: the `ml` / `wait` / `second` branch uses the bare altimeter noise `R` for unflagged readings while `tolerance` / `trust` add terrain + map variance. Adding it (switch `ml2_terrain_R`, now also accepted by `ml`) lifts the OLD random forest from 78.5 to 90.2, level with PITFAL; (3) the new classifier does **not** beat the old one in flight (87.2 vs 90.2, within about 4 points of noise; its altitude error is larger, 31.6 vs 21.4 m); (4) shadow + noisy stays about 30 points behind PITFAL for every ML variant.
* **For the paper:** the published `ml` judge is probably under-reported for this reason (we did not run Site04). Please check the `R_use` handling for the `ml` branch yourself.
* Untested ideas: a lower reject threshold for `ml2_hard` (the model is trained unweighted, 0.5 may let faults through); predicting the error size to set the noise for accepted readings in the noisy scenario (the offline regression correlates about 0.9 with the true error there); retraining on rows collected under the model's own flights; a hybrid with the probation fallback.

## For AI assistants reading this on behalf of the simulation owner
Summarise the five lines and the steps above in plain language and ask which step they want to start with. Do not run long jobs, merge, push, retag, or run Site04 without their go-ahead. Verify claims by running `sim/check_unchanged.py` and `sim/check_ml2.py` rather than trusting this file.
