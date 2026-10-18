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

## Status
Unity descent from 102.5 km to a 0.50 m/s touchdown works, with a live-scan position fix and CSV logging.
The 500-run Monte Carlo, ML classifier, tuning and sweeps in `sim/pipeline.py` have **not** been run yet.
