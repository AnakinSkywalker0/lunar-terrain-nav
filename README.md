# LANTERN: Sensor Trust for Lunar South Pole Landing

A lander's navigation filter should trust each sensor according to the terrain and lighting ahead, so a real
cliff is not mistaken for a sensor fault and a blinded camera is not believed. This repository holds the Unity
testbed, a fast Python test bench and the project documents.

**Update 20 Nov 2026:** round 3 on Site04 (run once after the freeze `prereg-round3`) met all five pre-registered rules. A tolerance gate with a running noise
floor holds up under a noisy altimeter without machine learning; terrain variance helps the `wait` and `ml` judges; a noise-aware fault label corrects the old
missed-fault and false-rejection columns. Simulation only; untested: wrong map, delayed readings without time stamps. See
[docs/ROUND3_RESULTS.md](docs/ROUND3_RESULTS.md) and [docs/PREREG_ROUND3.md](docs/PREREG_ROUND3.md).

**Update 8 Nov 2026 (read first):** a literature check and re-analysis show that some results below depend on how the tests were
scored and built. Scored in the map's own frame, the "shifted-map 0/N" outcome becomes about 70% success; 3-8 m map-tie errors are harmless
in this simulator; speed violations come from wrong matches under unmodelled relief. In a new 12-area headless study (21,888 descents) a
classical Kalman chi-square gate beat both plain matching and the learned policy. Simulation only; not yet a finished paper. See
[docs/EXPLAINER_FOR_MENTOR.md](docs/EXPLAINER_FOR_MENTOR.md), [docs/GUIDANCE_ABLATION_RESULTS.md](docs/GUIDANCE_ABLATION_RESULTS.md) and
[docs/HANDOFF_2026-11-08.md](docs/HANDOFF_2026-11-08.md). Statements below that call the shifted-map case "unsolved" are superseded.

Latest implementation (4 Nov): [uncertainty-aware Unity navigation v3](docs/NAVIGATION_V3.md).
Adds timestamped sensor fusion, map-height uncertainty, terminal braking and
optional bounded ML advice. Live scene: `Assets/Scenes/NavigationV3.unity`.
Unity execution is paused at the user's request; final code-only changes await
Unity verification. Earlier v3 checks and the 324-case engineering evaluation
are recorded in the linked note, including remaining failures.

Earlier measured work (22 Oct): [frozen-model Site01 transfer](docs/SCAN_UTILITY_TRANSFER_RESULTS.md).
Completed 810 descents across three terrain areas without retraining. Utility ML
and geometric matching both achieved 54/162 target successes. Mean miss improved
45.99 m to 43.60 m, but speed violations increased 39 to 47. The prewritten
transfer criterion failed: the earlier speed benefit did not generalize to
this batch. All accurate-map cases succeeded; changed terrain and shifted maps
failed the original absolute-frame 10 m criterion. Global map registration is a
separate observability issue. Data, failures and verification records are retained.

Previous measured work (22 Oct): [utility-based scan trust v2](docs/SCAN_UTILITY_RESULTS.md).
Collected 7,680 diverse proposals, selected the policy on 672 development descents,
then ran 270 reserved-area descents. Updated ML and geometric matching both
achieved 24/54 target successes; updated ML reduced mean miss 34.64 m to 28.92 m and
speed violations 12 to 7. The previous ML veto achieved 0/54 on the same cases.
This is a narrow single-area Site04 result; shifted-map absolute-target failures
do not by themselves establish a weakness of the correction policy.

[Current project explanation and research significance](docs/PROJECT_EXPLAINED_AND_REFOCUSED.md):
substantial engineering and early applied-research evidence, with unchanged target
success versus geometric matching. Includes a mentor summary, remaining gaps and
the next independent validation goals. Earlier PDFs predate these latest tests.

Previous measured ML work (22 Oct): [learned scan trust v1](docs/SCAN_TRUST_RESULTS.md).
Trained a small scan-specific model, verified Python/Unity inference parity and
ran 648 fresh four-arm descents. Geometric matching achieved 90/162 target
successes; ML achieved 18/162. The learned veto removed most wrong updates but
rejected useful corrections and worsened landings. This negative result and all
data are retained; the original geometric experiment remains available.

Previous measured work (22 Oct): [expanded five-area tests](docs/TERRAIN_MATCHING_EXPANDED_RESULTS.md).
540 descents and 270 stationary scans with the same frozen matcher: accurate-map
mean target miss 93.94 m OFF / 0.49 m ON, with 90/90 target successes ON.
Changed terrain achieved 3/90 successes and shifted maps 0/90; some wrong
corrections caused excessive sideways speed. No training was run.

Initial experiment (21 Oct): [short-descent terrain matching](docs/TERRAIN_MATCHING_RESULTS.md).
The new Unity experiment connects estimated-state guidance to scan matching and
compares 54 descents from 500-2000 m. With an aligned map, mean target miss was
70.31 m with correction OFF and 0.42 m ON. Changed terrain and shifted maps
exposed confident wrong corrections. The scene `TerrainMatchingExperiment`
replays the recorded results with condition, altitude, seed and ON/OFF controls.
No ML training is required for this experiment.

* `docs/Project_Description.pdf`, `docs/Progress_Report.pdf` - what the project is and where it stands (read the progress report first: it separates verified results from work that is built but not yet run).
* `LANTERN/` - Unity 6 (6000.3) project. Scene `Assets/Scenes/Site04.unity`; menu `SensorTrust > Build Site04 Scene` rebuilds it, `SensorTrust > Build Replay Scene` builds the replay scene.
* `sim/` - Python test bench (`world.py`, `engine.py`, `pipeline.py`, `plots.py`). Needs numpy, scipy, pandas, scikit-learn, matplotlib, Pillow.
* `tools/` - heightmap and rendering scripts, `make_report_pdfs.py`.
* `deliverables/` - the project plan PDFs.
* `out/` - plots, telemetry runs, figures. Caches and trained models are not tracked.

## Data (not in git)
Download NASA PGDA Product 78 Site04 (5 m/pixel) `Site04_final_adj_5mpp_surf.tif` and `..._slp.tif` into `data/`.
The slope file supplied during development was truncated; the code derives slope from the elevation file.
The Unity heightmap in `LANTERN/Assets/Terrain/` is generated from it by `tools/make_heightmap.py`.

## Status (19 Oct 2026, round 2 complete)
* Unity: descent from 102.5 km to a 0.50 m/s touchdown, live scan, CSV logging, replay scene with trust bars, camera survey tool.
* Python: round-2 Monte Carlo on Site04 (500 runs per cell) with a measured camera model; design pre-registered in `docs/PREREG.md` (tag `prereg-round2`); round 1 kept at tag `round1`.
* Complete chronological record of everything done, found and corrected: `docs/FULL_LOG.md` (PDF: `docs/Full_Project_Log.pdf`).
* Read `docs/Progress_Report.pdf` (results and caveats) and `docs/Paper_Draft.pdf`. Log: `docs/PROGRESS.md`.
* Headline: the map in the filter does most of the work; a plain map-tolerance gate matches the four-step trust rule in cliff cases; camera fixes must be gated by matcher confidence; delayed readings need time stamps. Simulation only.
