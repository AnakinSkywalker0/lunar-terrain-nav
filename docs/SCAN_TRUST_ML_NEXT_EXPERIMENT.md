# LANTERN: learned scan trust, preparation and next experiment

Latest follow-up: [completed utility-based v2 experiment](SCAN_UTILITY_RESULTS.md).

22 October 2026. Historical preparation note: training was disabled at this step.
The user subsequently authorized training. The completed model, Unity integration
and648-descent evaluation are documented in [SCAN_TRUST_RESULTS.md](SCAN_TRUST_RESULTS.md).
The preparation facts below describe the earlier state and remain unchanged.

The next question is whether a learned trust decision can reject misleading
scan-to-map corrections while keeping the accurate corrections that already help
the lander. Converting the existing elevation raster into a 3D surface remains
geometric: the height of each raster cell is already supplied. This experiment
does not train a model to invent missing lunar terrain.

## What was audited

`sim/pipeline.py:stage_ml` previously trained a random forest for the Python
altimeter experiment. The saved model has 120 trees, eight inputs and 857,764
nodes; its pickle is 80,395,833 bytes. SHA-256:
`a5802244483e6a91e1ace1d97d8e9ab6a84a8ffccd19ac643af5b6093290faee`.
It was loaded for inspection only. No fit or training stage was invoked.

Its fault label is an altimeter measurement whose absolute error exceeds
`5*(1 + 0.0015*max(true_range,0)) + 1` metres. This is not a label for a
scan matching the wrong location. Its eight inputs, in the order in
`sim/engine.py:_features`, are:

1. Signed altimeter innovation / predicted innovation standard deviation.
2. Signed altimeter innovation in metres.
3. Map height standard deviation inside the estimated uncertainty footprint.
4. Map height range inside that footprint.
5. Absolute innovation / assumed measurement standard deviation.
6. Mean absolute normalized innovation over the preceding four samples.
7. Measured range / 1000 (the argument is named `agl_true`, but receives `r_meas`).
8. Estimated horizontal uncertainty-footprint radius in metres.

The latest Unity experiment has no equivalent covariance-based filter inputs.
Passing matcher confidence into an arbitrary slot would change the model's
meaning. The saved altimeter classifier must not be relabelled as scan trust.
The older engine already uses this classifier with `judge="ml"`; the current
Unity scan-matching experiment does not.

The archived 89.54% accuracy and 0.9665 AUC describe a procedural held-out world
before a final refit. The pipeline subsequently refits on all procedural training
worlds, including that held-out world. Those scores are not independent test
scores for the final saved pickle, and do not establish scan or landing benefit.

## Completed now

`tools/prepare_scan_trust_data.py` reads the completed expanded Unity batch,
without running Unity or training anything. Output:
`out/scan_trust/20261022_preparation_v1/`.

It exports **10,530 valid proposed corrections**, of which **4,881** would leave
more than 10 m of horizontal position error. These are correlated observations
from 810 cases, not 10,530 independent missions. Of 9,196 geometrically accepted
proposals, 3,547 exceed 10 m error. These counts include stationary cases and both
descent arms; they are not the ON-only counts in the previous landing report.

Files separate model inputs, simulation-only labels and grouping information:

- `features.csv`: point count, fit RMS, heuristic confidence, correction x/z,
  correction magnitude. No truth, map condition or run identifier is an input.
- `labels.csv`: bad match = proposed absolute horizontal error **>10 m**;
  separately, whether the proposal reduces error by **>1 m**. A correction can
  help and still leave an unacceptable absolute error. Invalid proposals would
  be excluded, rather than labelled safe. None in this batch were invalid.
- `groups.csv`: all observations from an area stay in the same split, including
  stationary scans, OFF/ON pairs, conditions, offsets and noise seeds.
- `shadow_decisions.csv`: inference-gate decisions with **no learned model**.
- `manifest.json`, `baseline_audit.json`, `REPORT.md`: counts, hashes, provenance,
  grouped development assignments and baseline failures. Code is snapshotted.

The development assignments are original/area01/area02 for training (6,318 rows),
area03 for validation (2,106), and area04 for retrospective testing (2,106).
**All five areas and their results have already been inspected.** This split is
useful for development, but is not an untouched final test. Nearby terrain crops
also share one DEM. A later evaluation needs fresh terrain, spatial separation,
new initial errors, independent map errors and multiple noise seeds. V1's
original-area records must never be added to a different split.

`sim/scan_trust.py` supplies an inference-only Python gate with a strict task and
feature schema. A compatible future model can veto an otherwise accepted
correction; it cannot promote a geometrically rejected correction. Nonfinite
scores and inference failures reject the correction. No model preserves the
original geometric gate, explicitly labelled `geometric_only_no_model`.
This Python boundary is **not yet connected to live Unity guidance**.

Eight contract tests pass using score stubs, not trained models. The no-model
gate reproduced acceptance on every archived scan. This verifies the interface
and baseline preservation, not ML accuracy or improved landings.

Reproduce without training:

```powershell
python -m unittest discover -s tests -p test_scan_trust.py -v
python tools/prepare_scan_trust_data.py --output out/scan_trust/my_new_preparation
```

The output folder must not already exist. Historical simulation outputs and the
saved ML model are read only throughout preparation.

## Experiment to run after training is explicitly authorized

Hypothesis: a learned veto reduces accepted bad corrections compared with the
frozen geometric gate, while retaining enough good corrections to improve
target accuracy and avoid excessive sideways touchdown speed.

1. Fix the split and feature schema before fitting. Establish a simple residual
   and confidence gate baseline with the same tuning budget. Try a small
   classifier before considering a larger model. Fit preprocessing on training
   data only, with area/trajectory weighting so long descents do not dominate.
2. Choose thresholds using validation only. Measure bad corrections accepted,
   good corrections rejected, precision/recall, calibration and inference cost,
   by terrain area, altitude, initial error and map condition. Do not treat the
   matcher's existing confidence as a calibrated probability.
3. Freeze and version the chosen model, schema and threshold. Export inference
   for Unity and compare its scores against Python on identical feature vectors.
4. Run live, paired closed-loop descents: matching OFF, geometric matching ON,
   and geometric matching plus learned veto. Share initial states and sensor
   random streams; reset navigation and controller state between runs. A veto
   changes the trajectory, so archived-row replay alone cannot predict landings.
5. Evaluate on fresh terrain and new map/error patterns. Report target miss,
   navigation error, contact rate, vertical/horizontal impact speeds and fuel,
   including failures. Use paired mission-level differences; do not compute
   confidence intervals by pretending individual scans are independent trials.

A globally translated onboard map can fit measured terrain very well while
giving the wrong absolute coordinates. Local fit features alone cannot uniquely
resolve this ambiguity. Independent registration evidence, such as an anchored
landmark or independent absolute navigation reference, is needed to diagnose it.
Temporal consistency and correction limits may help other failures, but are not
proof against a coherent global translation. Simulation truth is used only for
training labels and evaluation, never as an onboard input.

The immediate result is a reproducible foundation for a sensor-trust experiment.
There is no newly trained model, deployed Unity ML policy or measured ML landing
improvement from this preparation step.
