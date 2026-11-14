# Handoff: new ML judge on branch `ml-eval` (14 Nov 2026)

**For:** the person who owns the simulator (`sim/engine.py`).  **From:** the ML-side contributor, with Claude's help.
**Status:** nothing here is merged into `main`. Please review first. All of it is simulation only.

## In five lines
1. We re-examined the random-forest "fault vs terrain" classifier (the `ml` judge) and found its **training label was wrong** in the noisy-altimeter scenario, its inputs were thin, and its quoted accuracy is a best-case world.
2. We built a corrected version: new label, 22 features (map consistency, vertical speed, 10 s history of flagged readings), a small model (`models/fault_clf_v3.pkl`, 0.5 MB).
3. We added a new judge **`ml2`** to `sim/engine.py` (additive; all existing judges are bit-identical, see step 2 below).
4. Offline it is clearly better, **but in flight (tuning worlds, 400 descents per cell) it did NOT beat the simpler judges, and not even the old random forest once both get the same engine fix** (see "First flight result"). The useful finding is a handicap in how the engine feeds the ML judges: fixing it lifts the OLD `ml` judge to PITFAL level (90.2% vs 89.2%, cliff + faults). Treat `ml2` as an unsuccessful first attempt plus a corrected evaluation, not as an improvement.
5. Site04 has NOT been touched. A round-3 pre-registration is needed before Site04 is run again (step 6).

## UPDATE (second session): a learned measurement-noise model is the first ML result that works in flight
The weakness of every ML judge was **over-trusting noisy readings**. We trained a second small model (`models/err_reg_v3.pkl`) that predicts the size of each reading's error
(target `log1p(|error| / nominal sigma)`, same 22 features; on an unseen world its median |error|/prediction is 0.95-1.02 in every scenario). `ml2` uses it to set the measurement
variance: `variance >= (nominal sigma * expm1(prediction))^2`, for accepted flagged readings and, with `ml2_noise_normal=True`, for readings that passed the gate as well.
Landing success %, mean of the 4 tuning worlds (procedural 11-13 + Site01), 100 descents each, seed 7, `ml2_hard + terrain_R` (`sim/ml2_noise_normal.py`, `out/ml2/noise_normal.csv`):

| Condition | PITFAL | trust v2 | ml2, noise model on flagged only | **ml2, noise model on flagged + unflagged** |
|---|---|---|---|---|
| cliff + faults (nominal noise) | 89.2 | 96.0 | 93.5 | **95.0** |
| x2 below 6000 m | 87.2 | 92.0 | 88.2 | **94.0** |
| x4 below 6000 m | 88.2 | 88.8 | 73.0 | **92.0** |
| x8 below 6000 m (the only noise level the models were trained on) | 77.0 | 78.0 | 69.8 | **84.0** |
| x16 below 6000 m | 45.2 | 62.8 | 63.5 | **87.2** |
| x8 below 2500 m only | 87.5 | 91.2 | 87.5 | **90.5** |

Also tried and **not** helpful: reject thresholds 0.2 / 0.3 / 0.7, soft mode (`out/ml2/x4.csv`, `noise.csv`); without the terrain-variance fix the x4 result drops from 73% to 56%.

**Why this is promising but NOT yet a result (please read):**
* Found and confirmed on the **same four tuning worlds and the same seed**; the variant `ml2_noise_normal` was chosen after looking at tuning-world numbers, and 7+ variants were compared. The confirmation covers more noise levels, not new worlds or seeds. Expect some optimism.
* The error model was trained on **flagged readings only**; applying it to unflagged ones is outside its training data. It works empirically; we do not yet understand why.
* The noise is always a multiple of the nominal noise in this simulator; the models never saw other noise shapes.
* **Missing control:** a simple non-ML adaptive noise estimate (running innovation variance, Mehra-style) may do just as well. Until that is tested, this is not evidence that *learning* helps. Learned adaptive noise is close to known adaptive filtering; the defensible claim is "a learned, terrain-aware noise estimate", not a new principle.
* Not run on Site04; needs frozen settings and a round-3 pre-registration first. Per world there is spread (e.g. world 13 at x2: 80 vs trust v2 83).
* `sim/ml2_x4.py`, `ml2_noise_levels.py`, `ml2_noise.py` hold the intermediate experiments (`out/ml2/*.csv`).

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
| `sim/ml2_noise_normal.py` (**key**), `sim/ml2_noise_levels.py`, `sim/ml2_x4.py`, `sim/ml2_noise.py` | The learned-noise experiments: the 6-condition confirmation grid, unseen noise levels, the x4 investigation, thresholds. |
| `out/ml_*/`, `out/ml2/` | Result tables and plots. |

How `ml2` decides: for every reading that fails the 99% gate it asks the model for the probability `p` that the reading is a fault.
`soft` (default): accept the reading but multiply its noise variance by `1/(1-p)^2` (so `p=0.9` means 100x less weight).
`hard`: reject if `p > 0.5`, otherwise accept with the same terrain-variance inflation the old `ml` judge used.

## Steps for you (in this order)
Assume a Python 3 environment with numpy, scipy, pandas, scikit-learn, matplotlib, Pillow, and the NASA files in `data/`.
1. **Read the engine diff** (about 15 minutes): `git fetch && git diff main..origin/ml-eval -- sim/engine.py`. Tell us if you want any of it done differently.
2. **Check nothing else changed:** `python sim/check_unchanged.py` (10 min; `--quick` for 2 min) should end with `UNCHANGED`. Then `python sim/check_ml2.py` should end with `ALL CHECKS PASSED`.
3. **Reproduce the key result first:** `python sim/ml2_noise_normal.py` (about 15-20 min, 4 workers) should give the table in the UPDATE section. Then, if you like, the older comparison: `python sim/ml2_compare.py --n 100` (about 15 min), then `--n 500` for paper-size numbers. Uses 4 workers; on a 16 GB machine do not go above 6. Output: `out/ml2/compare_tune.csv`.
4. **Judge the result.** Do you reproduce the table above? If yes, we need your view on the suspected causes (in particular the horizontal-position hypothesis, which you know best) before spending more time on the model. The questions are in the next section.
5. **Fix the simulator's own label** (`fault_lbl`, `engine.py:335`) so it compares with the actual noise level, as `sim/ml_labels.py` does. This changes the "false rejection" and "missed fault" columns in your tables, so decide how to report it. We did not edit it.
6. **If ml2 helps: write a round-3 pre-registration** (new file, like `docs/PREREG.md`) *before* any Site04 run: the judges, `ml2_mode`, the model file, and the decision rules. Then freeze, tag, and run Site04 once.

## Questions we need you to answer
* Is the `engine.py` edit acceptable as written? Prefer a different hook?
* Do you know a real altimeter failure shape we have not simulated? **"Stuck at last value" is not covered** (it needs the true range at run time).
* Should the delayed scenario treat a stale reading as a fault? Today it is labelled one; trust v2 instead compensates using time stamps.
* Do you want `ml2` in the paper as a new judge, or as an improved version of the `ml` judge?

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
