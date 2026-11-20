# LANTERN full project log

Sensor Trust for Lunar South Pole Landing. Complete chronological record of what was done, decided, found, got wrong and fixed.
Written 19 Oct 2026. Short versions: `PROGRESS.md` (status), `Progress_Report.pdf` (results), `Paper_Draft.pdf`, `PREREG.md`.

## 0. Starting point (before 18 Oct)

* Five plan documents in `deliverables/`: literature review, research gap, objective and problem definition, proposed methodology, paper summaries.
  They define the problem (HAKUTO-R 2023 rejected valid altimeter readings at a crater rim; IM-2 2025 trusted a camera in shadow),
  the four-step trust rule, objectives O1-O7, hypotheses H1-H4, metrics and the fair-testing rules.
* NASA PGDA Product 78 Site04 elevation and slope GeoTIFFs in `data/` (5 m/pixel, 3200 x 3200, -2848 m to +1805 m). Rendered by `tools/render_site.py` (`out/site04/`).
* A Unity 6 project `LANTERN/` already existed: Site04 scene built from the DEM, a rigid-body lander (`LanderController`), HUD, follow camera,
  and the LUMEN live-scan module (lidar raycasts, height patch, patch matcher, position correction).

## 1. Unity connection and smoke test (18 Oct)

* Checked the Unity MCP connection: project `D:/newprj/LANTERN`, scene `Site04.unity`, scripts as above. Connected.
* **Smoke test failed first**: entering Play mode left the game loop frozen at frame 2. Cause: the Unity editor window reported itself inactive
  (`isApplicationActive` false). Fix: `Application.runInBackground = true`. Later made automatic in `DescentAutopilot.Start`.
* After the fix the lander free-falls with throttle 0 (at t = 16.6 s: 276 m above ground, -26.9 m/s, fuel 800 kg). Console clean.

## 2. Landing site selection (18 Oct)

* The supplied slope file `Site04_final_adj_5mpp_slp.tif` is **truncated** (30.5 MB instead of 41 MB); the missing part loads as 0 degrees, which fakes flat areas.
  `tools/render_site.py` already handles this by deriving slope from the DEM; the same was done here.
* Tile centre: 33 degrees, 35 degrees maximum over 45 m. Only 0.4% of the tile has a 45 m maximum slope under 5 degrees.
* Chosen site: Unity (x 6198, z 8512), 1.88 km from the centre, elevation 1729.5 m, mean slope 1.1 deg, 45 m-window maximum 2.8 deg.
  The Unity terrain height there equals the DEM (1729.5 m). Lander start moved there (scene saved, `Site04SceneBuilder.cs` updated).

## 3. HUD, shadows and autopilot (18 Oct)

* HUD text was white on sunlit near-white terrain and too small. Added a dark backing box, then scaled the font to 3% of screen height with a box sized to the text.
  Verified on a 1920 x 1080 game-view screenshot (`out/hud_check.png`).
* Low-Sun cast shadows verified with camera captures (shadow edges visible; shadowed side black because ambient light is 0).
* `DescentAutopilot.cs`: free-fall coast, speed-profile braking, upright hold. First run from 500 m touched down at **2.07 m/s** (over the 2 m/s target);
  retuned (final-descent rate 0.5 m/s, derating 0.5, velocity gain 4): **0.50 m/s**, 0 m/s horizontal, 0.0 deg tilt.

## 4. 102.5 km start and time warp (18 Oct)

* User asked for a start 100-105 km above the surface. Lander moved to 102.5 km above the flat spot, dropped from rest.
  Autopilot gained time warp (8x high up, 1x below 4 km, physics step unchanged) and checkpoint logging.
* Full run: free fall about 190 s to 312 m/s at 70 km, then about 0.69 throttle to touchdown. Touchdown t = 583-587 s, 0.50 m/s vertical,
  0 m/s horizontal, 0.0 deg tilt, **251 kg fuel left** (549 kg used), exactly on target.
* Caveat: a real descent from 100 km altitude starts with about 1.7 km/s horizontal speed. The autopilot does not handle that (vertical drop only).

## 5. LUMEN diagnosis and fix (18 Oct)

* Found dead zones: invalid at 1252 m, at 25 m and at touchdown. Cause (from code): lidar beam spacing grows with altitude (about 14 m at 1250 m) while the
  patch cell was fixed at 8 m, so cells never got 2 points; and below about 80 m the scan footprint is too small (the map itself is 7.8 m/pixel).
* Fix: patch cell scales with beam spacing (`adaptiveCell`, `cellPerBeamSpacing` 1.6). Result: first fix at 2463 m;
  error 47 m at 2205 m (41 m cell), 14.5 m at 921 m, 4 m at 155 m (8 m cell). Over 108 logged fixes: median 8.9 m, max 48.7 m, injected error (+60, -40) m,
  shift reported (-64, 32) m, confidence 1.00. No fix below about 80 m (physical limit, left as is).

## 6. Data logging (18 Oct)

* `TelemetryLogger.cs`: one CSV per Play session in `out/runs/` plus `runs_summary.csv`, flushed per row.
* Bug found: the first run's summary recorded start altitude 0 (the logger read the autopilot's altitude before the autopilot had computed it). Fixed afterwards
  (logger now computes altitude itself); not re-verified in a later Unity run.

## 7. First documents and git (18 Oct)

* Project description and progress PDFs built with reportlab (`tools/make_report_pdfs.py`); pages rendered and checked.
* Git initialised in `D:/newprj`; `.gitignore` excludes Unity `Library/Temp/Logs/UserSettings`, the large GeoTIFFs and caches. Private repo
  `AnakinSkywalker0/lantern-sensor-trust` created and pushed (user chose private, exclude large files).

## 8. Reading the plan and scoping the full study (18-19 Oct)

* The user said "complete everything". Reading `4_Proposed_Methodology.pdf`: the plan requires a **fast Python test bench for the 500-run Monte Carlo**
  (rule 7), Unity only replays selected landings; scope is powered descent from about 15 km; tune on Site01 plus procedural terrain, test on Site04.
* Decisions and disclosures made at the time: the Python bench starts at 15 km (the Unity demo stays at 102.5 km); Site01 missing so tuning uses procedural terrain only;
  HAKUTO-R altitude record unavailable; guidance and sensor settings were chosen while looking at Site04 runs (disclosed in every report since).

## 9. Python test bench (18-19 Oct)

* `sim/world.py`: Site04 and procedural crater worlds (10 m), truth surface with unmapped craters and roughness, onboard map banks (3 m height noise, registration shift),
  coarse reference surface (4 km Gaussian), shadow rasters at 20 m (cached), region statistics (min/max/std, lit fraction at several radii), track selection
  (about 10 km from high ground across the rim to a flat floor: start 15 km above the rim, target on the crater floor).
  Site04 coarse reference reads -1482 m at the target against a true -2755 m (this offset is the HAKUTO-R mechanism).
* `sim/engine.py`: batched simulator (500 runs in lock-step), truth physics (1.62 m/s2, 2000 kg, 6000 N, Isp 300 s), IMU with bias, altimeter with fault bursts,
  delay and dropout, camera and live-scan fixes, a 9-state EKF, guidance on the estimate (speed profile with a 15 m constant-rate final), and seven judges:
  fixed, PITFAL-style, map tolerance, wait-and-see, second opinion, ML classifier, trust (four-step). Ablations of the trust rule.
* Smoke tests found and fixed: guidance had no constant final descent (touchdown 2-3 m/s); with the Sun from the south-east the track never entered shadow,
  so the default Sun was set to the west (az 270) for the IM-2 scenario.

## 10. Round 1: pipeline, results and the mistake in it (19 Oct)

* `sim/pipeline.py`: stages ml, tune, main, sweeps, replay (parallel). First launch with 20 workers ran out of memory (15.7 GB machine, 5-6 GB free);
  cut to 6 workers and one cached world per worker. At the user's request ("do not train anything right now") all Python processes were stopped; no model existed;
  training was resumed only after the user said "execute them all".
* ML classifier (round 1): 77.7% held-out accuracy, AUC 0.85. Tuning on procedural worlds chose probation 8 samples, 4 sigma.
* Round-1 results (Site04, 500 runs): fixed 0.4%, PITFAL-style 49%, trust layer 89% (cliff); the "controlled" check giving every judge the same shadow-aware camera showed
  the map-tolerance gate at 93% against the four-step rule's 89%; with a mildly damaged camera PITFAL-style reached 94-100%. Everything in `out/mc_round1/`, tag `round1`.
* **The mistake**: round 1's camera-in-shadow damage curve was my assumption, and the comparison gave the trust layer a shadow-aware camera while the other judges fed every
  camera fix to the filter. Round 2 corrected this (section 14).
* Replay export: found a recording bug (the filter kept integrating free-fall after touchdown, so the estimate drifted km below ground in the replay); fixed to stop recording at contact.
* Unity replay scene: `ReplayPlayer.cs` and `ReplaySceneBuilder.cs` (builds `Site04Replay.unity`). Verified by play and screenshots: the fixed-gate lander hovers 1372 m up believing it is
  62 m below the surface while the other two land.
* Documents and push: progress report with conclusions (6 pages), `PROGRESS.md`, README; pushed. The user asked for conclusions in plain language; they were given.

## 11. Round 2: why and what changed (19 Oct)

* User: "do it all". Next-step list: (1) justify the camera model, (2) redesign probation and add timestamps, (3) fix the no-map fallback, (4) get more data, (5) write the paper.

### 11.1 Site01 data (user approved the download)
* Asked before downloading (filename, source, size). Approved: `Site01_final_adj_5mpp_surf.tif` and `..._toterr.tif` (40,980,810 bytes each) from
  pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/ into `data/` (not in git). Checked: 3200 x 3200, no gaps; relief -523 to 1959 m; NASA total error 0.06-5.6 m.
  The error map sets the map-noise level for Site01.

### 11.2 Camera survey in Unity
* `sim/cam_survey_plan.py` picks 300 positions on Site04 stratified by lit fraction (60 per bin). `CameraSurvey.cs` renders paired nadir images: live (true Sun,
  displaced by an unknown offset) and reference (onboard prediction, Sun 0.05-0.25 deg higher, +-1 deg azimuth).
* First pass showed dark scenes with mean 21/255, from the skybox leaking into shadows. Fixed by switching reflections and ambient intensity off during the survey,
  then re-rendered; dark scenes became flat (texture std 0.8).
* `sim/cam_survey_match.py`: ZNCC landmark matcher with sensor noise (read noise 2 DN, shot noise). Two reference variants: direct-light-only (primary) and scattered-light (optimistic).
  Primary result: median error 401 m and 88% of fixes off by more than 100 m when the footprint is under 5% lit; 7.6 m (20% off by >100 m) at 5-25%; 2.4 / 1.3 / 0.8 m above 25%.
  The matcher confidence (correlation peak) was a perfect failure detector: 0 of 226 fixes with peak >= 0.5 were off by more than 100 m.
* **Second correction**: the first round-2 smoke test showed PITFAL-style at 0%, because it fed every fix to the filter. That is a strawman (a real matcher reports confidence).
  Camera policies were added: naive, confidence gate, Sun-geometry prediction, both. Every judge now gets the confidence gate by default.

### 11.3 Trust layer v2
* Noise level learned online from accepted readings (fixes noisy-but-valid readings); time-stamped readings compensated for delay (assumes the message carries its acquisition time);
  no-map fallback that tracks ground height under the lander.
* The no-map fallback took three attempts, debugged on a procedural world only: (a) ground height reset on every accepted reading left vertical speed unobservable
  (AGL estimate good, vertical speed off by 1.4 m/s, touchdown 2.8 m/s); (b) a terrain-relative altitude filter for the whole descent flew into the crater wall; (c) final approach
  only on the terrain-relative filter below 200 m: 98% on the tuning world.
* ML classifier retrained with the new camera: 89.5% held-out accuracy, AUC 0.97 (procedural worlds only).

### 11.4 Pre-registration and freeze
* `PREREG.md` written before the Site04 run: changes since round 1, frozen settings, primary hypotheses P1-P6 with decision rules, procedure.
  **Disclosure** in it: a 100-run Site04 smoke test of the new engine was inspected before writing it (trust v2 looked ahead; no-map still 0% at that time).
* Tuned on procedural worlds + Site01 only (grid K 8/10/12, sigma 2.5/3/4): chosen K = 10, sigma = 4 (87% mean success there). Committed, tagged `prereg-round2`, pushed.

### 11.5 The Site04 evaluation (run once)
* 500 runs per cell, 9 judges + 2 ablations, 5 scenarios, confidence-gated camera for everyone; camera policy comparison; sweeps; replay.
* Pre-registered outcome: P1 met (+14.8 / +11.8 / +24.0 points over PITFAL-style), P2 mixed, P3 met in cliff cases and failed in shadow + noisy (52% vs 33% fooled),
  P4 supported (Sun-geometry prediction 5-11 points worse than the confidence gate in three of four cases), P5 met, P6 met only via time stamps.
* Exploratory (added after the main run, labelled as such): giving the other judges the same time stamps: tolerance gate 97.6%, wait-and-see 79%, trust v1 79.6%,
  PITFAL-style 74.2%; trust v2 without time stamps 0%. Only change to the code after the freeze tag: a `timestamps` option in `sim/engine.py`; default behaviour identical.

## 12. Headline numbers

### Round 1 (kept for comparison; tag `round1`; unfair camera baseline), landing success %, Site04, 500 runs
| Scenario | Fixed | PITFAL | Trust v1 |
|---|---|---|---|
| Cliff | 0.4 | 49.0 | 89.2 |
| Cliff + faults | 0.0 | 45.6 | 84.6 |
| Shadow + noisy | 0.0 | 27.0 | 55.0 |
| Delayed | 0.0 | 1.2 | 0.2 |
| Dropout | 0.0 | 7.8 | 44.4 |

### Round 2 (pre-registered; confidence-gated camera for every judge), landing success %, Site04, 500 runs
| Scenario | Fixed | PITFAL | Map tol. | Wait | 2nd op. | ML | Trust v1 | Trust v2 | v2 + scan |
|---|---|---|---|---|---|---|---|---|---|
| Cliff | 0.2 | 82.0 | 97.2 | 79.6 | 56.6 | 75.8 | 94.6 | 96.8 | 100.0 |
| Cliff + faults | 0.0 | 85.6 | 97.6 | 80.2 | 8.6 | 76.0 | 94.8 | 97.4 | 99.8 |
| Shadow + noisy | 0.0 | 64.0 | 61.6 | 28.6 | 15.6 | 23.8 | 53.4 | 88.0 | 59.2 |
| Delayed (v2 time-stamped) | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 | 0.4 | 0.0 | 83.0 | 95.8 |
| Dropout | 0.0 | 34.8 | 41.6 | 29.0 | 26.2 | 24.2 | 31.4 | 37.0 | 61.4 |

### Round 2 sweeps and robustness (300 runs; sun sweep 200)
| Test | PITFAL | Trust v2 |
|---|---|---|
| Position error 5 / 50 / 200 / 400 m (cliff) | 81 / 83 / 76 / 61 | 97 / 98 / 95 / 96 |
| Divert | 74.3 | 91.3 |
| No map | 2.7 | 90.7 |
| Map shifted 2 km | 35.0 | 1.3 |
| Site01 vs Site04, cliff | 100 vs 81.7 | 100 vs 98.0 |
| Sun from the east (well lit), shadow + noisy | 99.5 | 39 |
| Sun from south / west, el 1.5-3 deg | 62-70 | 81-90 |

## 13. Conclusions

1. The HAKUTO-R failure is reproducible: a fixed gate with a coarse reference fails 99.8% of landings.
2. The map in the filter does most of the work (82%), and a plain map-tolerance gate reaches 97%.
3. The four-step rule matches but does not beat that gate in cliff cases; probation adds nothing there.
4. Trust v2 wins with a noisy altimeter in shadow, with no map and on a divert; it fails with a noisy altimeter in good light and with a shifted map, and is fooled by more faults in the noisy case.
5. Camera fixes must be gated by matcher confidence (ungated: 0.4-3%); Sun-geometry prediction adds nothing over it.
6. Delayed readings are solved by time stamps, not by the trust logic.
7. Round 1's shadow-aware-camera headline did not survive a fair baseline.
8. Publishable as a controlled-comparison workshop paper with honest negative findings; not a breakthrough. Simulation only.

## 14. Errors, corrections and disclosures (all of them)

| What | When found | What was done |
|---|---|---|
| Play mode frozen (editor inactive) | 18 Oct | `runInBackground`, later automatic |
| Truncated slope file read as flat | 18 Oct | slope derived from the DEM |
| HUD unreadable on bright terrain | 18 Oct | dark box, font scaled to screen |
| Autopilot touched down at 2.07 m/s | 18 Oct | retuned to 0.50 m/s |
| LUMEN blind above ~500 m | 18 Oct | patch cell scales with altitude |
| Logger recorded start altitude 0 | 18 Oct | fixed; not re-verified in Unity |
| 20-worker pool ran out of memory | 19 Oct | 6 workers, one world per worker |
| Replay recorder kept integrating after touchdown | 19 Oct | stops at contact |
| Round-1 camera model assumed and unfair baseline | 19 Oct (round 2) | replaced by measured model and confidence-gated camera; round 1 kept and labelled |
| Skybox light leaked into survey shadows | 19 Oct | reflections and ambient off, re-rendered |
| No-map fallback unobservable vertical speed | 19 Oct | terrain-relative altimeter filter on final approach |
| Design looked at Site04 smoke runs before pre-registration | 19 Oct | disclosed in `PREREG.md` and every report |
| Time-stamp control added after the main run | 19 Oct | labelled exploratory; only a default-off code option changed after the freeze tag |
| `sim/engine.py` differs from the `prereg-round2` tag | 19 Oct | disclosed; default behaviour identical |
| PDF bullets rendered as mojibake | 19 Oct | fixed in the generator; all PDFs re-checked |
| Two statements in the report slightly off (camera prediction "within noise"; scan "up to 20 points") | 19 Oct | corrected before commit |

## 15. Open items

* Repair trust v2's two weaknesses: scale the physical check with the noise level; detect a wrong map.
* Terrain-relative no-map baseline for a fair comparison.
* Repeat the camera survey on Site01 and with a second matcher; add a scattered-light prediction case.
* Real HAKUTO-R altitude record (not available). Site01 only used for tuning, so Site04 is the only unseen real site.
* Optional: PGDA Product 104 as a second high-detail site; an orbital-speed start for the Unity demo; an outside read-through before submission.

## 16. Where everything is

| Path | What |
|---|---|
| `LANTERN/Assets/Scripts/` | `LanderController`, `DescentAutopilot`, `LanderHud`, `TelemetryLogger`, `FollowCamera`, `ReplayPlayer`, `Lumen/` |
| `LANTERN/Assets/Editor/` | `Site04SceneBuilder`, `ReplaySceneBuilder`, `CameraSurvey` |
| `LANTERN/Assets/Scenes/` | `Site04.unity`, `Site04Replay.unity` |
| `sim/` | `world.py`, `engine.py`, `pipeline.py`, `plots.py`, `cam_survey_plan.py`, `cam_survey_match.py`, `smoke.py`, `quicktest.py`, `dbg_nomap.py` |
| `tools/` | `render_site.py`, `make_heightmap.py`, `make_report_pdfs.py` |
| `docs/` | `PREREG.md`, `PROGRESS.md`, `FULL_LOG.md` (+ PDF), `Progress_Report.pdf`, `Paper_Draft.pdf`, `Project_Description.pdf` |
| `out/mc/` | round-2 results (main_results.csv/.md, camera_policies, sweeps, exploratory_timestamps, tuning, ML report, per-run CSVs) |
| `out/mc_round1/`, `out/plots_round1/` | round-1 results (tag `round1`) |
| `out/camera_survey/` | survey positions, matcher results, empirical camera model (images not in git) |
| `out/runs/` | Unity telemetry CSVs and run summaries |
| `out/plots/`, `out/replay/` | figures and replay data; `out/replay_round2.png` Unity replay capture |
| `data/` | NASA GeoTIFFs (not in git) |

Git tags: `round1` (6bbda5c), `prereg-round2` (ca61ea6). Reproduce round 2: `python sim/pipeline.py ml tune` then `main policies sweeps explore replay`, `python sim/plots.py`, `python tools/make_report_pdfs.py`.

## 17. Short-descent terrain matching and lander art (21 Oct)

The user's original emphasis was clarified: turn the stored elevation map into
a terrain surface and test whether live scans help navigation. The old long
Unity descent and Python sensor-trust bench did not directly establish that.
An editable Blender lander concept and a separate Unity art preview were built.

The new short-descent experiment connects scan-derived position corrections to
an estimator consumed by horizontal guidance. The matcher/guidance code has no
access to physical truth. Independent terrain/map grids allow aligned, changed
relief and coordinate-shift cases. Both comparison arms receive the same sensor
models and map, with paired seeds; only applying the correction differs.

The first editor-only physics-scene initialization failed before producing
measurements. It was corrected to enter Play mode and manually advance a local
PhysX scene. Known-offset/sign, ambiguous-flat-map, empty-scan and out-of-bounds
checks passed, followed by one stationary scan and a paired 500 m smoke descent.
No algorithm tuning was performed after inspecting these results.

Protocol v1 then completed 27 stationary scans and 54 descents: 500/1000/2000 m,
three environments, three seeds, correction OFF/ON. All descents reached contact
below 2 m/s vertically. With an aligned map the mean target miss was 70.31 m OFF
and 0.42 m ON (target successes 0/9 and 9/9). Changed relief produced 55.30 m
mean miss ON; a shifted map produced 45.43 m ON. Both mismatch conditions failed
the <10 m target criterion in all nine ON runs. Shape-fit confidence could remain
very high for incorrect corrections. Those negative outcomes are retained.

The full evidence is in `out/terrain_matching/20261021_181450_v1/`, including
source snapshots/hashes, protocol, independent map grids, scan diagnostics,
per-run trajectories, sparse point clouds, report and plots. See
`TERRAIN_MATCHING_RESULTS.md` for the plain-language conclusion and limitations.
Python only summarized this experiment; no ML training ran.

`TerrainMatchingExperiment.unity` displays the stored map, scan points, true and
estimated positions and the new lander. It is explicitly a replay of the measured
Unity runs, with condition/altitude/seed/matching selectors. The original Site04
flight scene still uses the original true-state autopilot. The new experiment
uses simplified 3-DOF dynamics with ideal attitude response, not a validated
mission vehicle. Next work: map-consistency checks, influence limits for suspect
corrections, and tests across independent terrain sites.

## 18. Expanded surface-area tests (22 Oct)

The user requested more testing. The expanded protocol was written before the
new outcomes: five Site04 areas, 500/2000 m starts, three initial horizontal
errors crossed with three noise seeds, aligned/changed/shifted maps, OFF/ON.
Targets were selected from the generated heightmap by a deterministic local
slope and farthest-distance rule. Southeast quadrant candidates did not meet
the slope criterion; the full-tile selection rule and exact selected targets
were fixed before the expanded simulations. No matcher outcome selected sites.

The core matcher, navigation and guidance source is byte-identical to v1.
The harness now supports multiple areas and errors, caches terrain buffers,
and records actual PhysX contact/relative velocity for v2. The old proximity
stop is retained for v1. A six-case smoke check at the original area and area01
passed before the full batch. No thresholds or gains were tuned on the results.

Full batch: 270 stationary scans and 540 descents, complete in 281.9 seconds.
Accurate-map matching ON succeeded in 90/90 descents, 18/18 at each area; mean
target miss 0.49 m ON versus 93.94 m OFF. Changed terrain succeeded in 3/90
ON descents, mean miss 57.96 m; shifted maps succeeded in 0/90, mean miss
70.81 m. All 540 contacts were below 2 m/s vertically, but erroneous corrections
caused horizontal contact speeds up to 6.83 m/s. Matching improved terminal
target distance in 232 pairs, worsened it in 9 and left it tied in 29.

All 810 trajectory/cloud pairs, source snapshots/hashes, initial-pair sensor
equality and success labels were verified. Evidence:
`out/terrain_matching/20261021_183805_expanded_v2/` (UTC folder timestamp; local
date 22 Oct). The standalone result note is `TERRAIN_MATCHING_EXPANDED_RESULTS.md`.
Tables break results down by area, altitude and initial error; plots include
failure cases and confidence versus absolute error. No ML training was run.

The original v1 output and replay pointer remain available. Expanded data use
`latest_expanded.txt`. Five areas in the same DEM are not five independent lunar
datasets; ideal attitude response and synthetic sensor models remain limitations.

## 19. Scan-trust ML preparation (22 Oct; no training)

The user asked whether ML should decide sensor trust. Audited the existing
120-tree, eight-input altimeter classifier: its labels concern altimeter errors,
not wrong scan-to-map locations. Its old held-out metrics precede a final refit
on all procedural training worlds. It cannot be directly substituted into the
current Unity matcher. Loaded the saved model for inspection only.

Prepared 10,530 valid scan proposals from the completed expanded batch, with
4,881 labelled as leaving more than 10 m absolute horizontal error. Kept truth
labels separate from six runtime-observable features. Area-grouped splits keep
paired runs and correlated trajectories together; these are retrospective
development splits because all existing area results were already inspected.
Fresh terrain and error patterns are still required for final testing.

Added an inference-only Python scan-trust gate, with strict task/feature checks,
an optional learned veto and explicit geometric-only fallback. Eight contract
tests passed using stubs, and no-model acceptance matched all archived scans.
There is no live Unity ML connection or new landing result yet. No training ran,
no historical simulation output changed, and no trained model was overwritten.
Evidence and next protocol: `SCAN_TRUST_ML_NEXT_EXPERIMENT.md` and
`out/scan_trust/20261022_preparation_v1/`. A globally shifted map still requires
independent absolute registration evidence; a high local fit cannot prove it.

## 20. Authorized scan-specific training and live Unity evaluation (22 Oct)

The user explicitly said “DO IT” after the proposal to train, integrate and
compare paired descents. This authorized training for this new experiment;
the older altimeter classifier was not overwritten or retrained. Wrote the
scan-trust protocol and froze three fresh, nonoverlapping Site04 targets before
fitting or obtaining new outcomes. Reserved new error vectors, seeds, relief
perturbation and map-shift direction for the fresh closed-loop evaluation.

Trained logistic, full-feature random forest and residual-only random forest
on 5522 geometrically accepted historical proposals from three training areas.
Case/area weights balance the fit. Validation alone selected a 32-tree full
forest,depth 6,threshold 0.18. Additional forest seeds were sensitivity checks,
not a seed-selection opportunity. A 75-setting classical rule was also selected
on validation. The model is 1252 nodes and 43965 bytes as portable JSON.

Built a C# inference reader, strict task/feature checks and a separate four-arm
Unity harness. Unity scores and decisions matched Python on all 10530 inputs,
maximum score difference 3.33e-16. All eight Python contract tests passed; the
Python inference gate also matched all fixtures. The original geometric
navigation core is byte-identical to previous experiments.

The 12-case smoke passed. Full 648-descent batch completed in 137.7 seconds, with
all 648 physical contacts. Each arm has 162 paired cases: OFF 0 successes,
geometric 90,rule 45,ML 18. Mean target miss 96.24 m,23.00 m,49.96 m,84.70 m respectively.
Accurate-map geometric 54/54 versus ML 15/54; changed terrain 36/54 versus 3/54;
shifted map 0/54 for all arms. ML applied 1wrong correction of 28 updates versus
geometric 1077 of 2805, but rejecting useful corrections made navigation worse.
ML had 5vertical-speed and 25horizontal-speed violations; geometric had none.

The report generator initially lacked the join from scan IDs to condition
metadata; repaired the join and regenerated summaries from unchanged raw data.
No classifier, threshold, controller or simulation was changed after outcomes.
Verified all case files, paired initial inputs, policy routing, outcome labels,
source/model/protocol hashes and preservation of old pointers/model. The new
model remains an experimental option and has not been promoted as a solution.

Saved full evidence under `out/scan_trust/20261021_190929_closed_loop_v1/`, training
under `out/scan_trust/20261022_model_v1/`, and results in `SCAN_TRUST_RESULTS.md`.
The classifier's good rejection counts did not translate to good landings.
Next development needs broader error families, a correction-utility/uncertainty
objective and independent registration evidence for globally shifted maps.
New development must reserve a new final evaluation rather than tuning on this
batch and relabelling it as unseen. No independent lunar-dataset claim is made.

## 21. Diverse utility learning and mission-based selection (22 Oct)

The user authorized the proposed follow-up with “DO IT”. Wrote protocol v2 and
froze randomized collection draws, development errors and a new reserved area
before collecting/fitting. Only one eligible nonoverlapping crop remained after
excluding eight previous centres; the protocol allowed scaling, so final scope
was recorded as 270 descents before training. No v1 final-test scan rows were
used for v2 fitting or policy selection.

Collected 3840 stationary poses /7680 noisy scan proposals over five older areas,
varied angles/magnitudes, true positions, altitudes, raised/lowered relief and
map shifts. A gain target rewards useful local error reduction. Six observable
features omit signed correction direction and truth. Fit a 32-tree regressor on
4172 accepted training proposals, with 2732 accepted validation proposals and
three predetermined sensitivity seeds. The deployed seed remained 11.

An import problem initially omitted the new runner from Unity's assembly;
reimported it under ScanUtilityRunner.cs and repaired a missing magnitude helper
before any full data collection. Export verification then caught NumPy scalar
promotion rounding a double tree threshold. Repaired the reader, added a
regression test and repeated the same fixed fit. The failed export attempt is
retained separately. C# matched Python on 7680 fixtures, max difference 2.22e-16.
No dataset, model setting or held-out evaluation changed in these repairs.

After smoke checks, ran 672 development descents. Three utility policies all
achieved 32/96 target successes; the prewritten speed/miss criteria selected the
hybrid policy. Utility/geometric speed violations 19/32, mean miss 28.18/30.03 m.
The classical bounded rule had slightly lower development miss than utility;
that tradeoff is retained. Froze the choice before final-area outcomes. A Play
mode handoff initially reported Editor busy; completed the stop before retrying.

Final 270 descents completed in 50.7 seconds, with 54 configurations per arm:
OFF 0 successes,geometric 24,bounded 24,old ML 0,utility 24. Utility mean miss 28.92 m
versus geometric 34.64 m and bounded 32.67 m; speed violations 7 versus 12 for both
controls. Utility improved target distance in 41/54 pairs versus geometric,
worsened 7,tied 6. Accurate-map 18/18 for utility/geometric, changed terrain 6/18,
shifted map 0/18. Seven unsafe utility contacts remain, all changed terrain 500 m.
Maximum sideways impact 3.22 m/s utility versus 6.00 geometric. No flight-safety or
independent-site generalization claim follows from one protected Site04 area.

Verified raw labels, partial-correction geometry, paired initial inputs, policy
routing, outcome criteria, file completeness and frozen source/model/plan hashes.
All data, old failures and code snapshots retained. Results in
`SCAN_UTILITY_RESULTS.md`; evidence under `out/scan_utility/`. V2 recovered useful
updates and improved error/speed outcomes, without raising the target-success
rate above geometric matching. Independent terrain and registration evidence
remain the next research checks.

## 22. Project significance and current explanation (22 Oct)

At the user's request, updated PROJECT_EXPLAINED_AND_REFOCUSED.md to describe
the completed geometric, learned-veto and utility-policy experiments. Replaced
outdated statements about unconnected guidance with an explicit distinction:
the original full-height Site04 demonstration uses true-state control; the
new experiments use corrected navigation estimates. Clarified that lifting
a DEM into a mesh is implemented geometry, not ML discovery of missing terrain.

Recorded the assessment as substantial engineering and meaningful early applied
research. Final v2 utility/geometric success is unchanged at 24/54, mean miss
is 28.92/34.64 m (16.5% lower), and speed violations are 7/12. Added a positive,
evidence-based mentor summary, contribution levels and future validation goals.
Novelty, statistical significance, independent-site generalization and physical
mission readiness remain unestablished. Multiple v2 components changed together;
matched ablations and baseline tuning are needed for causal attribution.

Linked this assessment from README, PROGRESS and SCAN_UTILITY_RESULTS. Preserved
the experiment snapshots and raw results; no new training or simulations were
started for this documentation update. Existing PDFs remain historical records.

## 23. Frozen-model transfer to Site01 (22 Oct)

The user requested further work. Prepared an evaluation of the existing
scan-utility model on Site01 without training or tuning. Wrote the transfer
protocol before outcomes, selected one smoke crop and three evaluation crops
using only terrain slope/distance, and froze the plan and runtime hashes.
Site01 appeared in older sensor studies, but not current scan-utility fitting
or policy selection. Georeferencing checks confirmed all four selected crops
lie outside the entire Site04 tile despite partial overlap between the tiles.

Created a separate terrain adapter from the archived utility runner. Sensor,
matcher, inference, navigation/control step and map-perturbation logic are
unchanged; source data and output paths differ. Existing model, policy and core
hashes match the archived final evaluation. Unity reopened during preparation;
the ready editor is 6000.3.24f1, matching the archived final-test environment.

The separate smoke area completed 15 descents and 150 scans. Initial independent
terrain verification assumed bilinear Unity sampling and failed by up to
0.274 m. A direct Unity height probe confirmed triangle interpolation; corrected
the Python verifier and allowed bounded height-quantization error. All integrity
checks then passed. No model, policy, simulation or raw outcome changed.
Saved the repair note with the smoke outputs. Started the planned 810 descents
across three areas and five arms; final outcome is recorded below when verified.

All 810 descents completed in 298.0 wall seconds. Near case 150, enabled
Application.runInBackground after finding it false following the editor restart;
this repaired inactive-window scheduling without changing the fixed physics step
or seeded sensor noise. The execution note is retained with the results.

Verified 810 unique cases and 13,011 unique scans, all paired arms, initial inputs,
outcome labels, gain routing, partial-update geometry, frozen model/core hashes,
terrain samples/perturbations and Python/C# inference on the new input records.
All trajectory/cloud pairs exist. Play mode stopped after completion.

Utility/geometric target successes both 54/162; mean miss 43.60/45.99 m (5.2%
lower for utility); speed violations 47/39 (worse for utility). Bounded achieved
54/162, 46.32 m, 39 violations. OFF and old ML each achieved 0/162. Accurate maps
gave 54/54 successes for geometric/utility; changed terrain and shifted maps
gave 0/54. All utility speed violations occurred with changed terrain. Area03
regressed from 3 to 14 violations, outweighing area01's improvement from 18 to15.
The frozen transfer criterion failed: the earlier error/speed tradeoff did not
generalize. No retuning followed. Report, per-area tables, chart and raw evidence
are saved under `out/scan_utility_transfer/20261022_091502_eval/`; project result
note: `SCAN_UTILITY_TRANSFER_RESULTS.md`. Updated README, overview, progress and
the earlier utility result with this qualification and next development goals.

## 24. Original idea and literature-based novelty assessment (22 Oct)

The user clarified the intended chain: lidar 3D observations matched to an
onboard 2.5D lunar map, then camera/altimeter trust decisions. Reviewed primary
sources: NASA/JPL ALHAT, Choe et al. ION 2022, a 2024 IEEE TAES publisher abstract,
Adams et al. SciTech 2025/PITFAL full paper, Sheppard et al. stochastic terrain
mapping preprint and an adjacent point-cloud navigation preprint. Recorded
which records were abstract-only and which full text was accessible.

The broad localization and terrain-informed range-rejection ideas have direct
precedents. Joint map/registration/sensor uncertainty with measured landing
benefit is a candidate research direction; this search does not establish its
novelty. Clarified that the current Unity ML selects correction gain, rather
than implementing the full proposed camera/altimeter integrity system.

Saved RESEARCH_NOVELTY_REVIEW.md with references, scoped claims, baseline and
ablation requirements, a pitch and checked conference information. IEEE SPACE
2027 lists a 31 January 2027 deadline; IEEE Aerospace 2027 regular submission
closed 2 October 2026. No new simulations, training or submissions in this review.

Follow-up question: whether a computationally lighter map would establish
novelty. Checked Schoppmann et al. IROS 2021 multiresolution planetary mapping,
Jin et al. adaptive-resolution GP mapping, and the already reviewed efficient
point-cloud measurement model. Added the distinction between routine map
reduction and a candidate navigation-aware resource/accuracy contribution,
including equal-budget baselines, runtime/RAM metrics and compression-induced
uncertainty. This remains a proposal, with no new code, training or experiments.

Second novelty check requested by the user: found substantially closer prior
work, including Dymczyk et al. IROS 2015 localization-aware compression,
Michaelson et al. TAES 2024 compact terrain encoding with covariance/rejection,
Marcus et al. JGCD 2024 planar quadtree landing maps, and Adams et al. SciTech
2026 resource-optimized active TRN. Also inspected JPL's 2022 informative
topographic-landmark study. Downloaded the public NASA paper after the browser
size limit prevented full access. Saved MAP_EFFICIENCY_RECHECK.md and qualified
the earlier suggestion: keeping navigation-relevant information is not itself
a new contribution. No LANTERN map-efficiency method has yet been established
as novel. No new training or simulations.

## 25. Uncertainty-aware Unity navigation v3 (4 Nov 2026)

The user asked to implement the conventional navigation/landing pipeline with
optional ML. Found an existing v3 proposal, re-scoring tool and headless entry
in the workspace; preserved those and the archived experiment implementations.

Added a new ten-state EKF (position, velocity, accelerometer bias and shared
map-height bias), fixed-lag delayed observation replay, classical innovation
checks, terrain-curvature covariance proxy, bounded optional frozen-ML weighting,
terminal lateral braking and a vertical flare. The physics adapter has seeded
sensor noise/bias, initial velocity uncertainty, scan-attitude error and explicit
range/scan delivery delays. Added a live scene with controls and a shared batch
simulation engine, frozen inputs/source hashes and offline record verification.

Prepared one development crop and three reserved crops from Site01's surface and
vertical-error rasters, avoiding the prior transfer crops. Ground and prior grids
have different sampling. Ground error is a synthetic correlated proxy scaled by
`toterr` (0.36–0.43 m generated RMS), not a PGDA clone or independent lunar truth.

First smoke: `out/navigation_v3/20261104_041155_393_smoke/`. Revised development
smoke after adding common map-height uncertainty and vertical flare:
`20261104_041543_046_smoke/` (18 cases, 10,121 sensor receipts). Final live-scene
check/captures: `20261104_042147_760_visual/`. Corrected the screenshot inset
viewport during visual verification; no navigation outcome selected that change.

Reserved engineering run: `20261104_042217_834_evaluation/`, 324 cases and
315,724 sensor receipts; 318 contacts and six timeouts. New fusion with terminal
guidance had 45/108 10 m map-target successes, 83/108 at 50 m, and 21 excess-speed
contacts. The frozen ML arm had 37/108, 87/108, and 17 respectively. Thirteen
contract groups and offline artifact/pairing/scoring checks passed in that source
snapshot. Healthy-reading rejection remains substantial; this is an implemented
testbed, not a demonstrated robust landing solution or a paper novelty result.

The user then explicitly requested no further Unity execution. The last Unity
job had already completed; a process check found no running Unity editor. All
subsequent work stayed offline: observation-copy ownership for replay, an added
contract group, ML fallback HUD, completion-pointer checks, results analysis and
documentation. Current final C# edits have not been compiled/run in Unity.
Nineteen Python tests passed. Source snapshots retain exactly what the earlier
Unity jobs executed. See `NAVIGATION_V3.md` for the implementation, measured
limitations and commands reserved for a later authorized Unity session.

## 19-20 Nov 2026: ml-eval reproduction, engine switches, round 3 on Site04

* **Reproduction.** The ml-eval branch (Rishabh's `HANDOFF.md`) was checked out in a throwaway worktree. `check_unchanged.py --quick` and `check_ml2.py` passed;
  `ml2_noise_normal.py`, `ml2_control_noise.py`, `ml2_fresh.py`, `ml2_ablate.py`, `ml2_classifier_tests.py` and `ml2_compare.py --n 100` were rerun and matched the
  committed CSVs row for row (96, 24, 168, 48, 150 and 72 rows). Fixed seeds, so this shows determinism, not independent confirmation. Record and copies:
  `out/ml2_repro_2026-11-20/`. `ml2_classifier_tests.py` took 17.5 wall-clock hours against the 30-35 minute estimate; cause not investigated.
* **Branch state.** Local `main` was fast-forwarded from `5853a84` to `0f9d8df` (origin had merged ml-eval as PR #2); uncommitted files untouched.
* **Engine switches (default off).** `fault_label_noise_aware`, `terrain_R`, `tol_noise_floor` in `sim/engine.py`; `check_unchanged.py` (full), the 19 older tests,
  5 switch tests and 10 runner-guard tests pass.
* **Screening and confirmation.** Tuning worlds (`sim/round3_candidates.py`) then fresh worlds 14-16 (`sim/round3_fresh.py`, decision rules R1 and R2 written before the run, both met).
* **Freeze and run.** `docs/PREREG_ROUND3.md`, engine, scripts and tests committed as `e63c7a6`, tagged `prereg-round3`; `sim/round3_site04.py --allow-site04` run once.
  All of Q1-Q5 met. Results, tables and limits: `docs/ROUND3_RESULTS.md`. Not committed beyond the freeze commit: results files, this log and the other docs.
* **Report.** A project report draft for the course was built in `report/` (Word and PDF) from the repository documents; open fields are listed in the `lantern-report` skill.
* **Corrections to earlier statements.** The old fault label ignored the noise multiplier, so earlier missed-fault columns in noisy scenarios were overstated and false-rejection columns understated (Site04 round 3: trust v2 missed faults 52.6% old label against 6.6% noise-aware). Decisions and landing success were never affected.

