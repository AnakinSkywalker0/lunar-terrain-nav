# Pre-registration for evaluation round 2 (written before any round-2 Site04 run)

Date: 19 Oct 2026. Round 1 (see Progress_Report.pdf, git tag `round1`) used an assumed camera-in-shadow model and
compared the trust layer's shadow-aware camera against judges that fed every camera fix to the filter. That comparison
was unfair. Round 2 fixes the design below **before** looking at any Site04 number from the new code.

## What changed since round 1 (and why)
1. **Camera model is measured, not assumed.** `sim/cam_survey_match.py` renders 300 nadir image pairs in Unity
   (true Sun vs onboard prediction with 0.05-0.25 deg Sun-elevation and +-1 deg azimuth error, reflections off,
   read noise 2 DN + shot noise) and measures a ZNCC landmark matcher. Camera fixes in the simulator are drawn from
   those measurements by lit fraction. The onboard prediction uses direct light only (primary); a scattered-light
   prediction is the optimistic sensitivity case.
2. **Fair camera baseline.** The matcher reports a confidence (correlation peak). In the survey, fixes with peak >= 0.5
   were never wrong by more than 100 m (0 of 226). Every judge therefore gets the same **confidence-gated** camera
   (peak >= 0.5, fixed a priori). The trust layer's Sun-geometry prediction (step 3) is evaluated as a separate camera policy.
3. **Trust layer v2 (`trust2`)**: probation and the tolerance gate use a noise level learned online from accepted readings
   (fixes the round-1 failure with noisy-but-valid readings); readings are time-stamped, so delayed readings are compared
   with the prediction at the instant they were taken (assumption: the altimeter message carries its acquisition time);
   with no map the filter tracks the ground height under the lander from accepted readings instead of using a coarse reference.
4. Tuning worlds now include real **Site01** (downloaded from NASA PGDA) with NASA's total-error map for the map-noise level,
   plus procedural worlds. Site04 is never used for tuning.

## Disclosure
Before this document was written, a 100-run smoke test of the new engine on Site04 was inspected (pitfal, trust v1, trust v2 on cliff, shadow + noisy, delayed, and a no-map case). It showed trust v2 ahead of both on shadow + noisy and delayed, and the no-map fallback still at 0%. The design choices above were made for the reasons given, but that smoke test was seen; no further Site04 runs have been looked at. The no-map fallback is debugged on a procedural world only.

## Frozen settings
* Judges: fixed, PITFAL-style, map tolerance, wait-and-see, second opinion, ML classifier, trust v1, trust v2, trust v2 + live scan.
* Gate: chi-square 99% (6.635); probation window and consistency threshold chosen by grid on tuning worlds only
  (K in {8,10,12} samples, sigma in {2.5,3,4}); all else as in `sim/engine.py` at the commit tagged `prereg-round2`.
* Scenarios: cliff, cliff + faults, shadow + noisy altimeter, delayed altimeter, altimeter dropout. 500 runs each, seed 20260101.
* Landing success: vertical speed <= 2 m/s, horizontal <= 1.5 m/s, slope <= 10 deg, fuel > 0.

## Primary hypotheses and decision rules (all judges use the confidence-gated camera)
* **P1** Trust v2 beats PITFAL-style by at least 10 points of landing success in each of cliff, cliff + faults, shadow + noisy.
* **P2** Trust v2 has a lower false-rejection rate than PITFAL-style in those three scenarios.
* **P3** Trust v2 is fooled by faults no more than 1 percentage point more often than PITFAL-style (the plan's "1 extra fooled run in 100").
* **P4** (camera) Predicting the lit fraction from Sun and DEM ("aware") improves landing success over the matcher's own confidence by no more than 5 points; if so the shadow-prediction idea adds little beyond a confidence gate.
* **P5** Trust v2 minus PITFAL on the unseen Site04 is at least as large as on the tuning sites minus 10 points.
* **P6** With the time-stamp check, trust v2 lands at least 50% in the delayed-altimeter scenario.
Any result not listed here is exploratory and will be labelled so.

## Procedure
1. Retrain the ML classifier on procedural worlds only; tune K and sigma for trust v2 on procedural + Site01.
2. Freeze, tag, then run Site04 once. No re-runs after seeing results; failures are reported.
