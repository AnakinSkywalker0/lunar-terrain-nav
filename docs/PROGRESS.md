# LANTERN progress log

Project: Sensor Trust for Lunar South Pole Landing (context-aware sensor trust layer, tested on NASA PGDA Site04).
Last updated: 19 Oct 2026. Full write-up with figures: `Progress_Report.pdf`. Plan: `../deliverables/`.

## Milestones

| Date | Milestone | Evidence |
|---|---|---|
| 16 Oct | Site04 DEM rendered; plan documents written; Unity Site04 scene, lander physics and LUMEN live scan built | `deliverables/`, `out/site04/`, `LANTERN/` |
| 18 Oct | Unity connection verified; Play mode stall diagnosed (editor inactive) and fixed with `runInBackground` | Unity console, frame counters |
| 18 Oct | Landing site chosen from DEM-derived slope (supplied slope file is truncated): Unity (6198, 8512), 2.8 deg max slope over 45 m | `Site04SceneBuilder.cs` |
| 18 Oct | Descent autopilot; start moved to 102.5 km; time warp; touchdown 0.50 m/s, 0 m/s horizontal, 251 kg fuel left | `out/runs/`, `out/plots/unity_descent.png` |
| 18 Oct | LUMEN fixed for altitude (patch cell scales with beam spacing): fix from 2463 m down, 4 m error at 155 m | `LumenModule.cs`, run CSV |
| 18 Oct | HUD text scaled to screen; per-run telemetry CSV logger | `LanderHud.cs`, `TelemetryLogger.cs` |
| 18 Oct | Project description and progress PDFs; private GitHub repo created | `docs/`, repo |
| 18-19 Oct | Python test bench: worlds, batched EKF, 7 judges + 3 ablations, 5 scenarios, pipeline | `sim/` |
| 19 Oct | ML classifier (77.7% acc, AUC 0.85) and probation tuning on procedural worlds only | `out/mc/ml_report.json`, `tuning_procedural.csv` |
| 19 Oct | 500-run Site04 Monte Carlo, sweeps, controlled same-camera comparison, camera-damage sensitivity | `out/mc/` |
| 19 Oct | Unity replay scene (`Site04Replay`) showing fixed / PITFAL-style / trust filters side by side | `LANTERN/Assets/Scenes/`, `out/replay_final.png` |
| 19 Oct | Results report with conclusions and caveats | `docs/Progress_Report.pdf` |

## Status against the plan objectives

| # | Objective | Status |
|---|---|---|
| O1 | Hazard and blind-spot maps | Done inside the test bench (terrain-height spread, lit fraction). Site04 only; Site01 data missing |
| O2 | Trust layer and fault-vs-terrain check | Done; evaluated |
| O3 | Reproduce baseline failures | Done: cliff, shadow, delay, dropout. HAKUTO-R failure reproduced |
| O4 | Monte Carlo comparison (~500 runs per scenario) | Done: 500 runs per cell, 95% intervals |
| O5 | Reproducible release and side-by-side replay | Done (repo, seeds, replay scene). No in-flight trust-bar HUD yet |
| O6 | Site-change robustness | Done: unseen site, divert, shifted map, missing map. Missing-map fallback fails |
| O7 | Live 3D scan extension | Done: LUMEN in Unity; three-way check in the bench |

## Headline results (Site04, 500 runs, Sun from the west)

* Fixed rule: 0.4% success (reproduces HAKUTO-R). Map in the filter (PITFAL-style): 49%.
* Trust layer: 89% (cliff), 85% (cliff + faults), 55% (shadow + noisy altimeter).
* With identical camera handling the simple map-tolerance gate scores 93%: the four-step rule's advantage is the shadow-aware camera, not the altimeter logic.
* Trust layer worse than PITFAL-style with a noisy altimeter in good light (61% vs 99%).
* Delayed readings: every method fails. No-map fallback: 0%.
* The shadow-camera advantage disappears if shadow only mildly hurts the camera model.

## Round 2 (19 Oct 2026, complete)

Round 1 compared the trust layer's shadow-aware camera with judges that fed every camera fix to the filter, using a hand-made
shadow-damage curve. That comparison was unfair, so round 2 redoes it on measured data. Round-1 results are kept in
`out/mc_round1/` and git tag `round1`. The design and hypotheses are fixed in `PREREG.md` before the round-2 Site04 run.

Done so far:
* **Site01 downloaded** (NASA PGDA, elevation + total-error map, not in git) and added as a real tuning site.
* **Camera survey in Unity** (`CameraSurvey.cs`, `sim/cam_survey_plan.py`, `sim/cam_survey_match.py`): 300 paired nadir images on Site04, a ZNCC landmark matcher,
  sensor noise, Sun-prediction error. Results (direct-light-only onboard prediction): median error 0.8-1.3 m when more than half the footprint is lit,
  4-8 m at 5-25% lit, but fully dark scenes fail (88% of fixes off by more than 100 m, matcher confidence about 0). The matcher's own confidence
  (correlation peak >= 0.5) never let through a fix off by more than 100 m (0 of 226).
  So a naive filter that ignores matcher confidence is a strawman; every judge now gets a confidence-gated camera.
* **Trust layer v2** (`trust2`): learns the noise level online, time-stamped altimeter readings (delay compensation), and a terrain-relative
  fallback for the no-map case (98% landing on a procedural tuning world in a smoke test; Site04 not yet run).
* **ML classifier retrained** with the new camera model: 89.5% accuracy, AUC 0.97 on a held-out procedural world (round 1: 77.7%, 0.85).
* **Replay HUD** now shows camera trust, altimeter state (used / rejected / on probation) and the learned noise level.
* Disclosure in `PREREG.md`: a 100-run Site04 smoke test of the new code was seen before the document was written.

Round-2 results (details in `Progress_Report.pdf`, draft paper in `Paper_Draft.pdf`):
* Tuned on procedural worlds + Site01 (probation 10 samples, 4 sigma), frozen at git tag `prereg-round2`, Site04 run once.
* Fixed gate 0.2% (HAKUTO-R reproduced); PITFAL-style 82%; plain map-tolerance gate 97%; trust v1 95%; trust v2 97% (cliff scenario).
* Trust v2 wins with a noisy altimeter in shadow (88% vs 64%), with no map (91% vs 3%) and on a divert (91% vs 74%); it fails with a noisy altimeter in good light (39% vs 99.5%) and with a map shifted 2 km (1% vs 35%).
* Camera: never use fixes without the matcher's confidence (0.4-3% success); Sun-geometry prediction adds nothing over confidence.
* Delayed readings: solved by time stamps (plain tolerance gate 97.6% with them), not by trust logic (exploratory control).
* Pre-registered hypotheses: P1 met, P2 mixed, P3 met in cliff cases and failed in shadow + noisy, P4 supported, P5 met, P6 met only via time stamps.

## Known issues

* Camera model is measured on one renderer, one matcher and one site (round 2); round 1's assumed model is retired.
* Trust v2's physical-possibility check rejects noisy valid readings when position is well known, and everything when the map is wrong.
* Guidance and sensor settings were first chosen while looking at Site04 smoke runs; round 2 pre-registered the rest (disclosure in `PREREG.md`).
* The real HAKUTO-R altitude record is not available; the no-map baseline uses a coarse reference.
* Unity: no LUMEN fix below ~80 m or above ~2.5 km; camera capture tool did not follow the lander in Play; the HUD shows no per-sensor trust bars yet.
* Python bench starts at 15 km (plan); the Unity demo starts at 102.5 km from rest and ignores orbital speed.

## Next steps

1. Repair the two weaknesses: make the physical check scale with the noise level; detect a wrong map (e.g. persistent disagreement between map and altimeter plus scan).
2. Add a terrain-relative no-map baseline so the no-map comparison is fair.
3. Repeat the camera survey on Site01 and with a second matcher; add a scattered-light prediction case.
4. Obtain the HAKUTO-R altitude record for a real-data replay; consider PGDA Product 104 for a second high-detail site.
5. Submit the paper draft after 1-3 (workshop-style controlled study), after a read-through by someone outside the project.
