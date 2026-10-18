# LANTERN: Sensor Trust for Lunar South Pole Landing

A lander's navigation filter should trust each sensor according to the terrain and lighting ahead, so a real
cliff is not mistaken for a sensor fault and a blinded camera is not believed. This repository holds the Unity
testbed, a fast Python test bench and the project documents.

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

## Status (19 Oct 2026)
* Unity: descent from 102.5 km to a 0.50 m/s touchdown, live-scan position fix, CSV logging, and a replay scene (`SensorTrust > Build Replay Scene`).
* Progress log and next steps: `docs/PROGRESS.md`.
* Python: full Monte Carlo done (`python sim/pipeline.py ml tune main sweeps controlled replay`). Results in `out/mc/`, figures in `out/plots/`, write-up in `docs/Progress_Report.pdf`.
* Headline: a fixed-gate filter reproduces the HAKUTO-R failure; the biggest gain comes from shadow-aware camera weighting; the four-step altimeter rule adds little over a map-tolerance gate (and is worse with a noisy altimeter in good light). Simulation only; the camera model drives the result.
