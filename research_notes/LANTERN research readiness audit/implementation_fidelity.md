# LANTERN implementation correctness and simulation fidelity

Audit date: 2026-10-25. Scope: the current working tree in `D:\newprj`, including untracked project-authored Unity scripts. This is a source audit, not a certification, flight qualification, or independent reproduction of the reported experiment results. **Bottom line: the newer Unity code is a genuine, narrowly scoped closed-loop horizontal terrain-matching testbed; it is not yet a validated lunar landing/navigation simulator.** The older Python benchmark has concrete covariance, delayed-measurement initialization, and endpoint-recording defects. The original Unity flight demo, Python benchmark, newer Unity experiments, and their replay scenes must be kept distinct.

Evidence labels used below:
- **Demonstrated bug:** directly established by source logic; where noted, also reproduced with a tiny read-only Python check.
- **Model approximation / scope limitation:** an intentional or evident simplification, not necessarily incorrect within its declared experiment.
- **Unverified concern:** a specific source-grounded question requiring a test; not presented as an observed failure.
- Priorities are this audit's engineering recommendations: **P0** before relying on the affected scientific claim; **P1** before a broader NASA-relevant research-readiness claim; **P2** maintenance/presentation correctness.

## 1. What source was covered, and what actually runs?

### Takeaway

All **27 project-authored C# files under `LANTERN/Assets`** were read completely: 15 runtime scripts and 12 Editor scripts. The four requested Python core files and both Python camera scripts were also read completely. No Unity experiment batch, build, training job, or renderer was executed; application files were not modified. Three tiny Python checks were run against `sim/engine.py` using an in-memory flat-world fixture, with bytecode writing disabled.

### Cited Findings

#### Complete C# source inventory

Paths below are relative to `LANTERN/Assets/`; each linked file was read through its final line. Counts exclude `.meta`, scenes, prefabs and binary assets.

| Source | Lines | Role / coverage |
|---|---:|---|
| [Scripts/LanderController.cs](../../LANTERN/Assets/Scripts/LanderController.cs) | 69 | Original demo rigidbody thrust, fuel and torque |
| [Scripts/DescentAutopilot.cs](../../LANTERN/Assets/Scripts/DescentAutopilot.cs) | 112 | Original demo truth-state guidance, contact and time warp |
| [Scripts/FollowCamera.cs](../../LANTERN/Assets/Scripts/FollowCamera.cs) | 17 | Visual follow camera only |
| [Scripts/LanderHud.cs](../../LANTERN/Assets/Scripts/LanderHud.cs) | 48 | Truth-state display and matcher diagnostics |
| [Scripts/TelemetryLogger.cs](../../LANTERN/Assets/Scripts/TelemetryLogger.cs) | 107 | Demo telemetry and summary semantics |
| [Scripts/ReplayPlayer.cs](../../LANTERN/Assets/Scripts/ReplayPlayer.cs) | 174 | Playback of Python-generated CSV, not a live estimator |
| [Scripts/Lumen/LidarScanner.cs](../../LANTERN/Assets/Scripts/Lumen/LidarScanner.cs) | 72 | Original demo terrain-only ray scanner |
| [Scripts/Lumen/HeightPatch.cs](../../LANTERN/Assets/Scripts/Lumen/HeightPatch.cs) | 72 | Binned heights, spread, cell-confidence helper |
| [Scripts/Lumen/PatchMatcher.cs](../../LANTERN/Assets/Scripts/Lumen/PatchMatcher.cs) | 85 | Original grid-patch matcher |
| [Scripts/Lumen/LumenModule.cs](../../LANTERN/Assets/Scripts/Lumen/LumenModule.cs) | 68 | Fixed injected-error scan demonstration |
| [Scripts/Experiments/TerrainNavigationCore.cs](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs) | 111 | New map, raw-point matcher, state integration, guidance |
| [Scripts/Experiments/TerrainTouchdownRecorder.cs](../../LANTERN/Assets/Scripts/Experiments/TerrainTouchdownRecorder.cs) | 18 | Terrain collision callback; evaluation-only |
| [Scripts/Experiments/TerrainExperimentReplay.cs](../../LANTERN/Assets/Scripts/Experiments/TerrainExperimentReplay.cs) | 165 | New experiment CSV/map playback and presentation |
| [Scripts/Experiments/PortableScanTrust.cs](../../LANTERN/Assets/Scripts/Experiments/PortableScanTrust.cs) | 94 | Frozen classifier/rule inference, observable feature boundary |
| [Scripts/Experiments/ScanUtilityPolicy.cs](../../LANTERN/Assets/Scripts/Experiments/ScanUtilityPolicy.cs) | 71 | Frozen gain-regression inference and bounded corrections |
| [Editor/Site04SceneBuilder.cs](../../LANTERN/Assets/Editor/Site04SceneBuilder.cs) | 147 | Original terrain/flight-scene construction, obsolete self-test |
| [Editor/ReplaySceneBuilder.cs](../../LANTERN/Assets/Editor/ReplaySceneBuilder.cs) | 27 | Python replay scene; deactivates original vehicle and HUD |
| [Editor/CameraSurvey.cs](../../LANTERN/Assets/Editor/CameraSurvey.cs) | 77 | Offline rendered image-pair acquisition |
| [Editor/ShortDescentExperiment.cs](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs) | 352 | Original and expanded new Unity experiment runners |
| [Editor/ScanTrustExperiment.cs](../../LANTERN/Assets/Editor/ScanTrustExperiment.cs) | 345 | Four-arm closed-loop scan-veto runner |
| [Editor/ScanUtilityRunner.cs](../../LANTERN/Assets/Editor/ScanUtilityRunner.cs) | 396 | Collection/development/evaluation runner and label interfaces |
| [Editor/ScanUtilityTransferRunner.cs](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs) | 407 | Site01 terrain ingestion and transfer runner |
| [Editor/ScanTrustVerification.cs](../../LANTERN/Assets/Editor/ScanTrustVerification.cs) | 44 | C# inference-fixture consumer and guards |
| [Editor/ScanUtilityVerification.cs](../../LANTERN/Assets/Editor/ScanUtilityVerification.cs) | 42 | C# inference-fixture consumer and guards |
| [Editor/TerrainExperimentCommand.cs](../../LANTERN/Assets/Editor/TerrainExperimentCommand.cs) | 60 | Explicit Editor job dispatcher and Play-mode transition |
| [Editor/TerrainExperimentView.cs](../../LANTERN/Assets/Editor/TerrainExperimentView.cs) | 92 | Constructs v1 recorded-experiment viewer |
| [Editor/LanderArtPreview.cs](../../LANTERN/Assets/Editor/LanderArtPreview.cs) | 146 | Visual-only FBX import, material setup and studio rendering |

#### Other inspected source and configuration

- Complete: [sim/world.py, 252 lines](../../sim/world.py), [sim/engine.py, 634](../../sim/engine.py), [sim/pipeline.py, 272](../../sim/pipeline.py), [sim/plots.py, 112](../../sim/plots.py), [sim/cam_survey_plan.py, 31](../../sim/cam_survey_plan.py), [sim/cam_survey_match.py, 97](../../sim/cam_survey_match.py), [tools/make_heightmap.py, 25](../../tools/make_heightmap.py), [tools/render_site.py, 135](../../tools/render_site.py), [tools/build_lander_art.py, 262](../../tools/build_lander_art.py), and [art/lander/README.md, 31](../../art/lander/README.md).
- Complete configuration reads: [Packages/manifest.json](../../LANTERN/Packages/manifest.json), [Packages/packages-lock.json](../../LANTERN/Packages/packages-lock.json), [ProjectVersion.txt](../../LANTERN/ProjectSettings/ProjectVersion.txt), [DynamicsManager.asset](../../LANTERN/ProjectSettings/DynamicsManager.asset), [TimeManager.asset](../../LANTERN/ProjectSettings/TimeManager.asset), [EditorBuildSettings.asset](../../LANTERN/ProjectSettings/EditorBuildSettings.asset), [GraphicsSettings.asset](../../LANTERN/ProjectSettings/GraphicsSettings.asset), [TagManager.asset](../../LANTERN/ProjectSettings/TagManager.asset). Targeted reads/searches: quality/shadow/platform settings in [QualitySettings.asset](../../LANTERN/ProjectSettings/QualitySettings.asset), color-space/backend/API settings in [ProjectSettings.asset](../../LANTERN/ProjectSettings/ProjectSettings.asset).
- Scene coverage was **targeted, not a full serialization audit**. Verified original scene components, enabled state, references, vehicle initial pose/parameters and terrain identity in [Site04.unity:480–646](../../LANTERN/Assets/Scenes/Site04.unity#L480-L646); GUIDs cross-checked against `LumenModule.cs.meta` and `DescentAutopilot.cs.meta`. Verified replay source path and class in [TerrainMatchingExperiment.unity:507–576](../../LANTERN/Assets/Scenes/TerrainMatchingExperiment.unity#L507-L576). Other scene associations were checked through their complete builder/player source rather than reading every mesh/line-renderer record.
- Terrain metadata: [site04_height.json](../../LANTERN/Assets/Terrain/site04_height.json), [site01_height.json](../../LANTERN/Assets/Experiments/ScanUtilityTransfer/site01_height.json). Directory inventories confirmed TIFF files, RAW files, Unity TerrainData assets, Blender source, FBX and visual prefab presence. Binary content, hashes, raster validity and complete prefab geometry were **not independently verified** here.

#### Exclusions and coordination boundary

- Excluded all generated `LANTERN/Library`, package caches, Temp/Obj/build caches and Python `__pycache__`; excluded vendor/package implementation source. Package declarations were inspected, not audited internally. Source references to `Library/*.validation.json` were read as code; generated validation reports themselves were not used as proof of passing tests.
- The other agent owns `sim/scan_trust.py`, `sim/scan_utility.py`, training/evaluation tools, tests and raw result statistics. Those implementations and result tables were not analyzed here. The C# inference/runtime/verification consumers are explicitly within this assignment; label and feature interfaces were inspected to assess truth access. `pipeline.py` was inspected because it is explicitly assigned, including which algorithms run and which replay is exported, without redoing model evaluation or raw statistical analysis.
- `sim/dbg_nomap.py`, `quicktest.py`, `smoke.py` and the standalone test suite were not audited. Unrelated project settings (audio, multiplayer, 2D physics, VFX, etc.) were inventoried but not substantively reviewed. No `graphify-out/graph.json` or repository `AGENTS.md` was found in the initial searches; direct source inspection was used.
- Initial `git status --short` showed numerous existing modified/untracked sources and outputs. This audit describes the working tree, not a verified immutable release or the exact source of every historical result. A broad search unexpectedly returned adjacent notes/tools; those incidental excerpts were not used to establish this audit's findings.

#### Architecture and data flow: four distinct execution paths

**A. Older Python benchmark — principally vertical altitude/sensor-trust research, but with 3D translational dynamics.** `world.py` builds a DEM-derived truth raster with extra craters/noise, map-error banks, a coarse reference, shadows and regional statistics. `engine.py` runs vectorized point-mass descents at 0.25 s, a nine-state position/velocity/accelerometer-bias EKF, faulty/delayed altimetry, empirical or assumed camera position fixes, and optional synthetic scan fixes. Guidance uses the estimate; translation is integrated analytically over each constant-acceleration step. The initial trajectory has 100 m/s horizontal speed and −140 m/s vertical speed, starting at 15 km by default; this is not the newer 500–2000 m Unity experiment. [world.py:175–203,206–239](../../sim/world.py#L175-L239); [engine.py:112–134,178–187,246–315](../../sim/engine.py#L112-L315).

`pipeline.py` orchestrates that engine, then exports selected trajectories; `plots.py` consumes its CSV results. `stage_replay()` deliberately prefers a case where trust2 succeeds and fixed/PITFAL-style fail. That is a selected explanatory visualization, not a representative random sample. `ReplayPlayer` reads/interpolates CSV, moves meshes and draws HUD/trails. It does not execute the Python algorithm or rerun physics. [pipeline.py:73–92,242–262](../../sim/pipeline.py#L242-L262); [plots.py:17–19,92–104](../../sim/plots.py#L92-L104); [ReplayPlayer.cs:37–64,93–140](../../LANTERN/Assets/Scripts/ReplayPlayer.cs#L37-L140).

**B. Original Unity `Site04` flight demo.** Scene builder creates a primitive rigidbody lander over the full Site04 terrain, from 102.5 km AGL at rest. `LanderController` applies body thrust and finite fuel. `DescentAutopilot` controls it from true Rigidbody velocity, true transform attitude and terrain-sampled true AGL. `LumenModule` separately scans the terrain and reports correction for a fixed injected offset; the autopilot does not use that correction. HUD/logger display this demonstration. This path cannot establish that scan correction improves landings. [Site04SceneBuilder.cs:68–99,103–130](../../LANTERN/Assets/Editor/Site04SceneBuilder.cs#L68-L130); [DescentAutopilot.cs:50–97](../../LANTERN/Assets/Scripts/DescentAutopilot.cs#L50-L97); [LumenModule.cs:23–65](../../LANTERN/Assets/Scripts/Lumen/LumenModule.cs#L23-L65).

**C. New Unity closed-loop horizontal experiments.** Editor command → Play-mode dispatcher → isolated `LocalPhysicsMode.Physics3D` scene → 2.4 km local DEM crop and independent truth/map arrays → frozen-rotation sphere vehicle → noisy ray ranges and acceleration increments → `NavigationEstimate` → raw-point `LocalScanMatcher` → optional observable-only veto/gain → corrected estimate → `EstimateGuidance` → thrust/PhysX → contact and logs. The original demo's `LanderController`, `DescentAutopilot`, `LidarScanner`, `HeightPatch`, `PatchMatcher` and `LumenModule` are not the physics/navigation implementation used by these runners. [TerrainExperimentCommand.cs:14–29](../../LANTERN/Assets/Editor/TerrainExperimentCommand.cs#L14-L29); [ShortDescentExperiment.cs:136–140,168–257,295–334](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L168-L334); [TerrainNavigationCore.cs](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs).

All four runners use `Dt=.05`, a 24×24 angular ray grid, a scan clock increment of 3 s, no correction at/below measured 80 m AGL, ideal attitude, initial exact velocity, and 1200 kg dry + 800 kg initial propellant. Their differences are sites, perturbations, gate/gain arms and endpoint variants. ShortDescent v1 terminates by 0.08 m proximity; expanded and learned runners use the terrain collision recorder. Utility collection is stationary and takes two scans with time labels 3 s apart; it does not advance physical motion between them. [ShortDescentExperiment.cs:15–19,217–257,295–334](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L217-L334); [ScanTrustExperiment.cs:204–266,288–326](../../LANTERN/Assets/Editor/ScanTrustExperiment.cs#L204-L326); [ScanUtilityRunner.cs:242–280,284–377](../../LANTERN/Assets/Editor/ScanUtilityRunner.cs#L242-L377); [ScanUtilityTransferRunner.cs:252–387](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs#L252-L387).

**D. New Unity replay/art presentation.** `TerrainMatchingExperiment.unity` is wired to `TerrainExperimentReplay`, with `runFolder=../../out/terrain_matching/20261021_181450_v1` and `runId=descent_aligned_500_11_on`. It replays logs from the initial geometric experiment. A visually realistic FBX can be attached to an enlarged marker, but has no role in experiment dynamics or optical sensing. [TerrainMatchingExperiment.unity:522–576](../../LANTERN/Assets/Scenes/TerrainMatchingExperiment.unity#L522-L576); [TerrainExperimentView.cs:49–74](../../LANTERN/Assets/Editor/TerrainExperimentView.cs#L49-L74); [TerrainExperimentReplay.cs:31–70,104–139](../../LANTERN/Assets/Scripts/Experiments/TerrainExperimentReplay.cs#L31-L139).

#### Coordinates and positive checks

- Python uses `(x east, y image-row, z elevation)`; Unity uses `(x, y elevation, z northward tile axis)`. The conversion is explicitly `(x,z,16000-y)` in Python replay, and the heightmap converter flips source rows. The camera model reverses the Unity-z error when returning Python-y errors. No unsupported sign-error allegation is warranted from these sources. [world.py:1–4](../../sim/world.py#L1-L4); [make_heightmap.py:18–23](../../tools/make_heightmap.py#L18-L23); [ReplayPlayer.cs:9–11,93](../../LANTERN/Assets/Scripts/ReplayPlayer.cs#L93); [cam_survey_plan.py:25–29](../../sim/cam_survey_plan.py#L25-L29); [engine.py:512](../../sim/engine.py#L512).
- New Unity experiments recenter horizontally at the selected crop and subtract center terrain height vertically; the target is local `(0,0)` in XZ. The transfer runner's `SourceMin=0` does **not** itself create a height error: the same constant is added to both sample and center and cancels. [ShortDescentExperiment.cs:173–185](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L173-L185); [ScanUtilityTransferRunner.cs:202–221](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs#L202-L221).
- New matcher/core guidance takes no Rigidbody, TerrainCollider or scene handle. Trust features are `[points,rms,confidence,dx,dz,norm]`; utility features are normalized RMS, confidence, correction norm, measured AGL, previous-correction consistency, and a history flag. True error and optimal gain are calculated for evaluation/labels, not passed into the inference call. This is a meaningful positive separation, though sensor adapters remain idealized. [TerrainNavigationCore.cs:7–109](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs#L7-L109); [PortableScanTrust.cs:64–92](../../LANTERN/Assets/Scripts/Experiments/PortableScanTrust.cs#L64-L92); [ScanUtilityPolicy.cs:34–68](../../LANTERN/Assets/Scripts/Experiments/ScanUtilityPolicy.cs#L34-L68); [ScanUtilityRunner.cs:293–315](../../LANTERN/Assets/Editor/ScanUtilityRunner.cs#L293-L315).
- The new sampler rejects out-of-grid bilinear cells, matcher rejects <80 returns, and geometric acceptance requires an interior coarse solution, RMS≤8 m and confidence≥0.35. Embedded self-checks cover a known offset/sign, empty scan, flat terrain and completely outside-map scan. They exist in source; this audit did not execute the Unity checks. [TerrainNavigationCore.cs:14–22,50–82](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs#L14-L82); [ShortDescentExperiment.cs:144–165](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L144-L165).
- Collision recorder filters for TerrainCollider, and new raycasts use the default-layer bit mask `1`, while the vehicle is put on layer 8. Thus the new experiment's rays do not accidentally hit its own sphere. The default collision matrix still permits terrain/body contact. [TerrainTouchdownRecorder.cs:11–15](../../LANTERN/Assets/Scripts/Experiments/TerrainTouchdownRecorder.cs#L11-L15); [ShortDescentExperiment.cs:224–230,253,304](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L224-L304); [DynamicsManager.asset:20](../../LANTERN/ProjectSettings/DynamicsManager.asset#L20).

### Inferences

- The proper scientific object for the latest work is correction gating/scaling under simplified 3-DOF translational closed-loop dynamics and synthetic DEM mismatch. It is not a six-degree-of-freedom lunar descent estimator, a camera-navigation experiment, or a combined operational implementation of every component appearing in the repository.
- Working-tree source supports the existence of a closed-loop causal path in the new runners. It does not by itself prove historical batches used exactly this source or establish effect sizes; that belongs to the coordinated reproducibility/statistical audit.

### Gaps

No independent Unity execution, engine backend validation, binary asset inspection, clean build, target-hardware timing, physical sensor calibration, full scene/prefab graph audit, or historical source-to-result hash match was performed. The project version and lockfile identify intended software, not a validated environment for every recorded run.

## 2. Which concrete correctness and fidelity findings affect the research claims?

### Takeaway

The most urgent source corrections affect the **older Python EKF/delay/replay path**. The most important limitations of the **new Unity path** are perfect attitude and initial velocity, an extremely benign acceleration model, no navigation covariance, instantaneous sensing/corrections, shared terrain ancestry, and an unobservable absolute map-registration offset. These limitations should not be conflated with direct leakage of evaluation truth into the new matcher/gates, which was not found.

### Cited Findings

#### I01 — P0: Python EKF transition Jacobian disagrees with its own state propagation

**Classification: demonstrated bug; tiny numerical reproduction passed.** Position propagation uses `p += v*DT + .5*(a_meas-bias-g)*DT²`, but `F` includes position–velocity and velocity–bias terms only. Therefore `F[p,b]` is zero where the actual derivative is `−.5*DT²*I`. At `DT=.25`, a finite difference against the actual `NavBatch.predict` returned **−0.03125**, while `F[0,6]` is **0.0**. [engine.py:119–134](../../sim/engine.py#L119-L134).

**Consequence:** propagated covariance and cross-covariances do not represent the stated nonlinear/linear state transition; downstream innovation gates and uncertainty-region calculations cannot be taken as EKF-consistent. This does not establish the numerical size or direction of changes in historical success rates.

**Related approximation:** `Q` is diagonal despite one accelerometer-noise draw driving both position and velocity within a step. Under that stated discrete-noise model there should be correlated position/velocity process noise. Bias-random-walk discretization also needs an explicit convention. The scalar covariance update uses subtraction and symmetrization, not Joseph form; loss of PSD is a numerical concern, **not an observed failure**. [engine.py:98–109,125–126,314–315](../../sim/engine.py#L98-L134).

**Fix:** derive `F` directly from the implemented transition and `Q=G_noise*Q_noise*G_noiseᵀ` from the sensor-noise definition; use a numerically robust update. **Acceptance:** finite-difference all 81 Jacobian entries; assert symmetry/PSD across long sequences; validate innovation/covariance calibration on a known linear truth model before using uncertainty in gates.

#### I02 — P0: Delayed altimeter emits initialized zero history as real data

**Classification: demonstrated bug; tiny execution reproduced it.** `r_hist` is allocated as zeros, only index `tt=k+1` is filled, and `d_idx=max(tt-delay_steps,0)` points to uninitialized slot zero during initial delay. `avail` does not require that a sample actually exists. With exact/noiseless measurements, 1 s delay and a 100 m starting altitude, two test steps produced **ranges `[0,0]` at times `[.25,.5]`**, while true AGL was approximately **`[65.043125,30.172524]`**. [engine.py:200,318–335](../../sim/engine.py#L318-L335).

**Consequence:** the delayed scenario adds a synthetic startup fault that is not a delayed real sensor return. That can affect early gating/probation and is not merely uncertainty about physical latency.

**Fix:** explicitly initialize a defined prehistory or withhold measurements until their acquisition timestamp exists. **Acceptance:** constant-height and descending fixtures must deliver the exact historical range only after the configured delay; no fabricated zeros; include nonintegral delays and the initial acquisition boundary.

#### I03 — P0: Timestamp compensation and covariance/Jacobian are inconsistent

**Classification: demonstrated mathematical inconsistency plus an explicitly approximate time model.** For timestamp-enabled operation, the predicted historical position is current position minus current velocity times delay. Yet measurement `H` still contains only position derivatives `[-gx,-gy,1]`. For that very prediction, velocity derivatives must be `[gx*d,gy*d,-d]`; they are zero in code. Acceleration during the delay is also omitted, and the update is applied directly to the current covariance/state rather than a stored past state followed by repropagation. [engine.py:337–359,481](../../sim/engine.py#L337-L359).

Delay knowledge comes directly from `draws.delay_steps`; no timestamp transport error, jitter or clock uncertainty is modeled. This can be a valid assumption of perfect timestamps, but it is a stronger sensor-interface assumption than merely enabling a trust rule. Defaults give timestamp compensation to trust2 and not other judges; the source contains an exploratory equal-timestamp comparison. [engine.py:158–159,338](../../sim/engine.py#L158-L159); [pipeline.py:229–239](../../sim/pipeline.py#L229-L239).

**Fix:** use timestamped measurement objects and a buffered out-of-sequence update/repropagation, or derive a consistent current-state observation model and Jacobian with declared approximations. **Acceptance:** finite-difference the delayed observation Jacobian; compare against a known delayed linear estimator; use identical timestamp access across algorithm arms when attributing a trust-logic effect.

#### I04 — P0 for no-map/wrong-map claims: Python map ablations leave accurate-map-derived information accessible

**Classification: demonstrated interface/configuration inconsistency.** `mapq`/`mapg` apply per-run registration shifts and add 2 km when `map_mode='wrong'`. In contrast, `stats` is always computed from unshifted `map_banks[0]`; physical terrain bounds, roughness variances and predicted illumination use it at unshifted estimated coordinates. In missing-map mode, the physical-bounds check is disabled, but `s_terr`, ordinary trust variance and probation variance still use those high-resolution map statistics. [world.py:181–192](../../sim/world.py#L181-L192); [engine.py:172–177,215–232,379–403,466,522–529](../../sim/engine.py#L379-L403).

Camera fixes also remain available in missing-map mode; the missing flag changes weighting, not whether map-matched fixes exist. This is not necessarily an error if an independent position-fix product is intentionally retained, but the code does not represent complete deprivation of high-resolution map-derived navigation information. [engine.py:498–535](../../sim/engine.py#L498-L535).

**Fix:** one explicit map/reference interface must supply mean, gradients, uncertainty statistics and lighting in the same datum/registration/bank. Define which products remain available in each ablation. **Acceptance:** a missing-map stub that throws on every forbidden high-resolution access; a translated-map fixture in which all map queries transform together; explicitly test camera/reference availability.

#### I05 — P0 for interpreting scan evidence: Python “live scan” is a synthetic truth-centered position fix

**Classification: model approximation / misleading cross-system equivalence, not an implementation of a matcher.** The Python extension selects eligibility using true AGL and true-terrain roughness, then constructs `meas = true_position_xy + map_shift + Gaussian_noise*sig_s`. There are no raycasts, acquired point clouds, map searches or ambiguity decisions from actual matching in this branch. [engine.py:542–557](../../sim/engine.py#L542-L557). Plot labels call this “live scan.” [plots.py:17–19](../../sim/plots.py#L17-L19).

**Consequence:** these results can assess the effect of an assumed auxiliary fix model; they do not validate LUMEN or `LocalScanMatcher`. Truth access here is normal for a synthetic sensor generator, but the truth-roughness eligibility supplies optimistic observability information unavailable as that exact value to a real instrument.

**Fix:** label it a synthetic scan-fix surrogate, or replace/calibrate it with independent point-cloud/matcher outcomes including false matches. **Acceptance:** verify the sensor output contract, failure/ambiguity rates and errors on reserved actual matcher runs; separately track surrogate and measured-matcher evidence.

#### I06 — P0 for original-demo navigation claims: original Unity flight is truth-guided and LUMEN does not close the loop

**Classification: demonstrated architectural fact / scope limitation.** `EstimatedPosition` is literally `transform.position + positionErrorM`; gating and adaptive cell size use true transform position and the map terrain. Scanner returns true-world-frame noisy ray hits; the module simply adds injected translation. `Last` is published but never applied to navigation by this class. The autopilot uses `rb.linearVelocity`, `transform.up`, angular velocity and terrain-sampled true AGL. [LumenModule.cs:36–65](../../LANTERN/Assets/Scripts/Lumen/LumenModule.cs#L36-L65); [LidarScanner.cs:44–66](../../LANTERN/Assets/Scripts/Lumen/LidarScanner.cs#L44-L66); [DescentAutopilot.cs:53–95](../../LANTERN/Assets/Scripts/DescentAutopilot.cs#L53-L95).

**Fix:** describe this as a flight/scan visualization and injected-offset recovery demo; use the newer isolated experiment for closed-loop correction claims. If extending the demo, replace truth-state guidance with the same tested sensor/estimate interfaces. **Acceptance:** perturb or disable matching while holding sensors fixed; a claimed closed-loop demo must change its estimate/control path through actual updates, never a fresh truth-plus-offset property.

#### I07 — P1: New Unity estimator is dead reckoning with overwrite updates, not a navigation filter with uncertainty

**Classification: model approximation.** `NavigationEstimate` holds only position/velocity; it integrates measured acceleration, overwrites vertical position with map-height-plus-range, and adds accepted horizontal correction at full or externally scaled gain. No covariance, bias state, attitude, innovation uncertainty, correction covariance, velocity correction, protection level or consistency statistic is present. [TerrainNavigationCore.cs:86–109](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs#L86-L109).

Runners initialize velocity exactly from truth and use `(true_velocity_now−previous_true_velocity)/Dt` plus independent 0.002 m/s² world-axis Gaussian noise as “measured acceleration.” This is a net inertial acceleration adapter, not a body-frame accelerometer specific-force model. A real gravity/attitude transformation is bypassed by the ideal attitude assumption; simply adding gravity again would be wrong for this adapter. [ShortDescentExperiment.cs:231–235,299–306](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L231-L306); [ScanUtilityTransferRunner.cs:266–271,353–360](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs#L266-L360).

**Consequence:** no evidence here for performance under gyro/attitude error, accelerometer bias instability, imperfect velocity initialization or filter inconsistency. “Confidence” from matching is not a covariance or probability of absolute safety.

**Fix:** retain and name the simplified state integrator for mechanism studies; for broader readiness add a defined IMU/sensor interface, uncertain initial state, bias/attitude dynamics and a consistent filter. **Acceptance:** zero-noise kinematic integration; known constant bias and attitude-error cases; state-error/covariance calibration and observability checks; exact input replay must yield identical estimates without truth access.

#### I08 — P1: Sensor and actuation fidelity is narrow, and wall time never delays a correction

**Classification: model approximation.** New lidar is an instantaneous 576-ray scan, ±20° about two axes, 3000 m limit, independent 2% dropout and range sigma `0.05+0.001*range`. The altimeter is a vertical ray, 4000 m range and 0.1 m white noise. Beam directions use world axes, consistent with frozen ideal attitude; there is no scanning motion, beam dwell, exposure, return intensity, reflectance-dependent detection, multipath, dust, boresight error, sensor lever arm or correlated range bias in the implemented adapter. [ShortDescentExperiment.cs:246–257,299–310](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L246-L310); [ScanUtilityTransferRunner.cs:282–292,353–365](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs#L282-L365).

All acquisition/matching/inference completes synchronously before the next force and `physics.Simulate(Dt)`. Match and trust milliseconds are logged but do not age the measurement or move the vehicle during computation. The 35 ms Editor loop budget checks only after `Step()` returns; it is not a worst-case per-scan or real-time execution deadline. Every arm performs matching; veto arms also compute gates even when not applied. [ShortDescentExperiment.cs:258–273,285–320](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L258-L320); [ScanTrustExperiment.cs:258–265,278–313](../../LANTERN/Assets/Editor/ScanTrustExperiment.cs#L258-L313); [ScanUtilityRunner.cs:298–306,320–364](../../LANTERN/Assets/Editor/ScanUtilityRunner.cs#L298-L364).

**Fix:** specify acquisition/completion timestamps and causal latency scheduling; distinguish matcher-only, end-to-end and wall throughput timings. Add fidelity features tied to the intended physical sensor rather than arbitrary realism knobs. **Acceptance:** inject a known latency and verify motion during it; report deadline misses and tail latency on identified hardware; repeat with scan motion/boresight/bias stress cases. No target-flight-computer timing claim is supported by the current code alone.

#### I09 — P1: New Unity altimeter failure retains a stale measurement without validity or age

**Classification: demonstrated failure-path bug; trigger frequency in existing runs unverified.** A failed down-ray simply leaves `measuredAgl` at its last value. That retained number is still passed to `ObserveAltitude`, used to enable/disable scans and used in thrust guidance. No range-valid flag or age accompanies it. [ShortDescentExperiment.cs:303–315](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L303-L315); [ScanUtilityTransferRunner.cs:357–369](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs#L357-L369).

**Fix:** timestamp and validate altitude measurements; on a miss explicitly skip the observation and invoke a defined degraded-guidance/failure policy. **Acceptance:** forced ray miss, out-of-range and out-of-map cases must not silently fuse old data as a new measurement; logs must record failure cause and measurement age. Existing nominal geometry may avoid this path; this audit does not claim it occurred in reported batches.

#### I10 — P0 for absolute-trust claims: map registration error is structurally unobservable from the same scan/map geometry

**Classification: demonstrated mathematical limitation of the observation model, not a coding sign bug.** The new cost is the variance of vertical residuals after subtracting their mean. The matcher estimates only horizontal translation and discards a constant height offset. The shifted prior is constructed as `prior(x,z)=source(x+sx,z+sz)−center`; truth is the same base surface at `(x,z)` in the map-shift case. [TerrainNavigationCore.cs:37–48,57–80](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs#L37-L80); [ShortDescentExperiment.cs:179–185](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L179-L185); [ScanUtilityTransferRunner.cs:208–221](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs#L208-L221).

Let the estimated horizontal position be `p+e` and the map shift be `s`. A correct shape alignment satisfies `e+correction+s=0`, so the corrected global estimate has error **`−s`**, even with perfect ranges and a distinctive terrain shape. Good RMS/confidence cannot distinguish this datum error from an actual vehicle displacement. Height-mean removal also prevents independent vertical translation recovery, and a planar surface provides no horizontal constraint once a constant height offset is removed.

**Fix:** distinguish map-relative localization from absolute target-frame localization. Model registration uncertainty; introduce an independent registration/position constraint or report unresolved absolute ambiguity. A learned veto based only on these diagnostics cannot generally create the missing information. **Acceptance:** noiseless translated-map analytic fixtures must return the predicted map-relative offset while flagging global-position uncertainty; flat and planar terrain must be recognized as unobservable, not merely assigned a large arbitrary correction.

#### I11 — P1: Confidence does not establish uniqueness; coarse boundary flag is frozen before refinement

**Classification: source-verified algorithm limitation; occurrence and impact on recorded terrain unverified.** Confidence compares best residual with the **mean** of distant coarse-grid costs, not the second-best separated minimum. Multiple equally good periodic matches can coexist with a high mean-away cost; this metric does not prove a unique match. The `boundary` boolean is calculated from the coarse winner before ±12 m then ±3 m refinement and is never recomputed. A coarse interior solution at 112 m can refine to 127 m without a revised boundary guard; an edge winner is rejected even if refinement comes inward. This may be an intentionally conservative coarse-edge policy rather than an implementation bug, but its semantics need to be explicit. [TerrainNavigationCore.cs:55–80](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs#L55-L80).

Important precision: an interior coarse winner cannot refine past 127 m under the present steps, so this is **not** a claim that an accepted solution exceeds ±128 m. Acceptance assesses the coarse boundary, not final solution proximity to the search boundary, and retains the coarse-edge rejection after refinement. [TerrainNavigationCore.cs:57–73](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs#L57-L73).

**Fix:** use separated-minimum ambiguity diagnostics/local observability, confidence calibrated for the defined use, and a documented final-edge margin; consider weighting residuals by range/incidence uncertainty. **Acceptance:** periodic terrain with two indistinguishable matches must remain ambiguous; planar/ridge geometry must expose unobservable directions; test true offsets just inside/outside each search edge and an edge coarse winner that refines inward.

#### I12 — P1: Shared DEM ancestry and deterministic perturbations limit “independent truth” claims

**Classification: model approximation.** New truth and stored map arrays are separate objects, and rays hit a separately resampled TerrainCollider rather than directly consulting the prior. That is good software separation. However, aligned truth/prior come from the **same source interpolation**; changed relief is one analytic Gaussian bump/depression and map shift is a fixed translation. Truth is constructed on 301×301 at 8 m, then interpolated to 513×513 over 2400 m for Unity terrain. The finer collider grid does not add independent surface information. [ShortDescentExperiment.cs:168–214](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L168-L214); [ScanUtilityRunner.cs:187–239](../../LANTERN/Assets/Editor/ScanUtilityRunner.cs#L187-L239).

The original full-tile heightmap is 2049 samples across 16 km, about 7.8125 m between vertices, derived from nominal 5 m raster samples. Footpads, rocks and submeter hazards shown in art are not resolved by this terrain construction. [site04_height.json](../../LANTERN/Assets/Terrain/site04_height.json); [make_heightmap.py:10–23](../../tools/make_heightmap.py#L10-L23).

**Fix:** describe independence as software/data-path separation, not independent measurement of the real surface. Add held-out terrain-error spectra/registration models and independently generated fine-scale truth justified for the mission. **Acceptance:** matcher robustness across independent map/truth resolutions and correlated errors, not only the same DEM plus a few analytic changes; demonstrate ray/map interpolation convergence separately from geographic generalization.

#### I13 — P1: Touchdown success is a restricted proxy; current truth physics cannot establish safe lander contact

**Classification: model approximation, plus endpoint timestamp bugs below.** New vehicle rotation is frozen, contact geometry is one 0.4 m sphere offset upward by 0.4 m, gravity is constant lunar gravity, and a world-force vector is applied instantaneously. Guidance limits tilt-equivalent lateral force to 10° and thrust magnitude to 6000 N. There is no attitude maneuver time, gimbal response, throttle slew/minimum, propellant slosh, engine transient, RCS propellant, gear crushing, tipping, rocks or payload clearance in the model. [ShortDescentExperiment.cs:224–232,315–320](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L224-L320); [TerrainNavigationCore.cs:101–108](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs#L101-L108).

New success is first terrain contact plus vertical speed<2 m/s, horizontal speed<1 m/s and target miss<10 m. It does not require fuel reserve, slope, tip-over stability or a settled condition. Python success differs: vertical≤2, horizontal≤1.5, sampled slope≤10°, fuel>0, but **no target-miss threshold**. Both are legitimate declared proxy endpoints; they are not the same mission success criterion. [ShortDescentExperiment.cs:329–333](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L329-L333); [TerrainTouchdownRecorder.cs:11–15](../../LANTERN/Assets/Scripts/Experiments/TerrainTouchdownRecorder.cs#L11-L15); [engine.py:295–310](../../sim/engine.py#L295-L310).

Fuel is clamped after applying a full step of thrust whenever it was positive at step start, in both new Unity and Python. Thus the final step can deliver more impulse than the remaining propellant supports; this is a finite-step model defect, not evidence it affects nominal outcomes. The original Unity manual throttle slew applies only to key input; automatic `Command()` sets throttle immediately. [ShortDescentExperiment.cs:315–320](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L315-L320); [engine.py:281,287–293](../../sim/engine.py#L281-L293); [LanderController.cs:31–38,41–50,63–66](../../LANTERN/Assets/Scripts/LanderController.cs#L31-L66).

**Fix:** publish endpoint definitions separately; fuel-limit final-step impulse; add fidelity only as required by the proposed research claim. **Acceptance:** analytic thrust/fuel exhaustion and gravity tests, timestep convergence, first-contact versus settled landing separation, and mission-linked limits for slope, reserve, attitude and clearance before claiming safe landing.

#### I14 — P1: Terminal records compare states from different times

**Python: demonstrated bug, reproduced.** Contact is detected using `p_new/v_new`, then `alive` is cleared; the following `np.where(alive,p_new,p)` retains old `p` for just-contacted runs. The trace nevertheless records it at `t+DT`. A flat-ground fixture starting 1 m high returned reported terminal AGL zero but recorded AGL/height **1 m at time 0.25 s**. [engine.py:294–322,562–571](../../sim/engine.py#L294-L322).

**New Unity: demonstrated time-alignment defect in terminal trace/error calculation.** Navigation predicts the previous physical interval at the start of `Step`; thrust and the next physical interval are then simulated. If contact/timeout happens, `elapsed` has advanced and `Trace()/Complete()` compare the new Rigidbody position against navigation that has not been advanced over that final interval. This affects terminal estimated-position error; it does not make true target miss or collision callback velocity an estimator output. [ShortDescentExperiment.cs:299–333](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L299-L333); [ScanUtilityTransferRunner.cs:353–387](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs#L353-L387).

**Related Python time alignment:** `alt_sq` compares pre-propagation guidance AGL `agl_b` against post-propagation `agl_true`; with perfect navigation a rapidly descending vehicle can still accumulate this apparent error. This is a source-level metric-definition defect, not a reanalysis of raw statistics. [engine.py:245–253,287–320,558–561](../../sim/engine.py#L558-L561).

**Fix:** make acquisition, truth, estimate and endpoint timestamps explicit; store new contact state (ideally interpolate contact time), and calculate errors at matched timestamps. **Acceptance:** perfect-navigation/noiseless fixtures have zero estimation error throughout including the final row; replay contact position agrees with reported collision geometry/time; convergence tests isolate integration error from state-time mismatch.

#### I15 — P1: Failure and provenance outputs can look complete after interruption

**Classification: demonstrated output semantics, not evidence that any published run was incomplete.** Runner `Finish(message)` writes its `latest` pointer for “Complete,” stopped, reload-interrupted and error outcomes; the latest pointer alone is therefore not completion proof. Summary stores touchdown/success and elapsed time but no explicit timeout/out-of-bounds/fuel-exhaustion failure category. [ShortDescentExperiment.cs:74–75,293,326–349](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L326-L349); [ScanUtilityTransferRunner.cs:338,380–404](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs#L380-L404).

Source snapshots are useful, but the Site04 runners' source lists do not capture the source TerrainData/RAW, complete ProjectSettings/Packages or every execution dependency. Transfer snapshots include its Site01 RAW and metadata, a useful improvement. [ShortDescentExperiment.cs:94–105](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L94-L105); [ScanUtilityRunner.cs:104–117](../../LANTERN/Assets/Editor/ScanUtilityRunner.cs#L104-L117); [ScanUtilityTransferRunner.cs:112–127](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs#L112-L127).

**Fix:** separate last-attempted and last-complete pointers; structured run status, expected/completed counts, per-case terminal reasons, and complete immutable dependency/config manifests. **Acceptance:** inject an interruption and an exception; neither may be mistaken for a complete batch, and every endpoint must carry its reason. Historical verification is delegated to the other agent.

#### I16 — P2: Concrete original-demo/presentation defects

- **Obsolete LUMEN self-test:** comments say scan from 500 m, but `LumenSelfTest()` calls `Build()`, which now places the lander at 102500 m AGL; scanner max range is 3000 m. It logs a result without assertions. This test cannot recover the intended ground patch at the configured initial height. **Fix/test:** explicitly position at the test AGL and fail on insufficient points, wrong sign/offset, invalid match or excessive residual. [Site04SceneBuilder.cs:73,133–144](../../LANTERN/Assets/Editor/Site04SceneBuilder.cs#L133-L144); [LidarScanner.cs:14,64](../../LANTERN/Assets/Scripts/Lumen/LidarScanner.cs#L14).
- **Demo “valid” is not acceptance:** original `PatchMatcher` sets valid whenever sufficient cells exist, with no confidence/RMS/boundary rejection. Its min/max search can return edge/ambiguous shifts that HUD/logger call valid. `HeightPatch.Confidence` is calculated by a helper but not used to weight matching. **Fix/test:** distinguish computed proposal from usable fix; flat/periodic/out-of-map fixtures should not imply navigation validity. [PatchMatcher.cs:37–46,69–81](../../LANTERN/Assets/Scripts/Lumen/PatchMatcher.cs#L37-L81); [HeightPatch.cs:56–63](../../LANTERN/Assets/Scripts/Lumen/HeightPatch.cs#L56-L63); [TelemetryLogger.cs:53–64](../../LANTERN/Assets/Scripts/TelemetryLogger.cs#L53-L64).
- **Old Python replay trail stops extending properly:** append increases count, writes last point, then truncates to 4000; once full, the newly appended point is removed instead of discarding the oldest. **Fix/test:** ring buffer or explicit oldest-point removal; after >4000 frames the newest displayed trail point must equal the current position. [ReplayPlayer.cs:136–140](../../LANTERN/Assets/Scripts/ReplayPlayer.cs#L136-L140).
- **New replay is v1-specific:** map lookup uses `map_<condition>.bin`, selectors construct `descent_<condition>_<altitude>_<seed>_<on/off>`, and Latest reads the original `latest.txt`. Expanded/utility files include site/variant/arm fields and map filenames. Current saved replay is correctly v1; it must not be presented as the viewer of transfer/ML batches without extending the schema. **Fix/test:** load a manifest rather than parse strings; open every supported run family and show its real arm/site/model metadata. [TerrainExperimentView.cs:13–27](../../LANTERN/Assets/Editor/TerrainExperimentView.cs#L13-L27); [TerrainExperimentReplay.cs:35–38,75,95–96](../../LANTERN/Assets/Scripts/Experiments/TerrainExperimentReplay.cs#L35-L96); [ScanUtilityTransferRunner.cs:67,222](../../LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs#L67).

### Inferences

- Source structure makes original-demo results, Python scan-surrogate results and new Unity closed-loop results noninterchangeable. A report should name the producing implementation and endpoint beside each claim.
- Perfect initial velocity and bias-free, ideal-frame acceleration make the new experiment primarily an initial-position/map-correction problem. This is appropriate for an isolated mechanism test; general navigation-recovery claims would require additional evidence.
- The shifted-map ambiguity is deeper than a threshold choice. Without an independent constraint, raising model complexity can only exploit correlations in the scenario distribution, not generally observe an absolute registration offset.

### Gaps

The effect of any identified bug on reported aggregate results remains unquantified. No current-run claim is made for the stale-altimeter path, matcher edge behavior, scalar covariance PSD loss, PhysX integration/callback subtleties, or cross-platform determinism. Those require targeted tests. In particular, the recorder uses `collision.relativeVelocity`; this audit did not verify its numerical agreement with pre-impact velocity for this exact Unity/PhysX backend.

## 3. What do terrain, rendering and configuration establish, and what are the readiness gates?

### Takeaway

The repository has traceable procedural art source and explicit terrain conversion code, but neither attractive renders nor NASA-sourced topography establish validated sensor physics. The next readiness step is a corrected, immutable and independently checkable **mechanism-study release**, with narrow claims and analytic acceptance fixtures, before increasing physical fidelity or claiming mission relevance beyond that scope.

### Cited Findings

#### Terrain provenance and coordinate fidelity

- The repository identifies its Site04 source as NASA PGDA Product 78, nominal 5 m/pixel, and names the input surface/slope GeoTIFFs. The converter loads pixels through Pillow, assumes a square raster at 5 m/pixel, resizes bilinearly to 2049², normalizes to unsigned 16-bit, flips rows and writes resolution/side/min/max/bad-pixel count. It does not parse or preserve full GeoTIFF CRS, projection, pixel-center convention, nodata tags, acquisition URI or source checksum. [README.md:55–58](../../README.md#L55-L58); [make_heightmap.py:9–24](../../tools/make_heightmap.py#L9-L24).
- Site04 metadata gives 16 km side, min −2847.877197265625 m, max 1805.0726318359375 m, bad count zero. Quantization step implied by this range is about **0.0710 m** before Unity internal representation; this is arithmetic from metadata, not measured end-to-end accuracy. Transfer Site01 metadata includes a source path, SHA-256 string, 5 m pixel scale and tiepoint, so its recorded provenance is stronger. Hash correctness was not recomputed here. [site04_height.json](../../LANTERN/Assets/Terrain/site04_height.json); [site01_height.json](../../LANTERN/Assets/Experiments/ScanUtilityTransfer/site01_height.json).
- Python `Grid.height` clips coordinates to the raster edge; `inside` uses one square extent `w*px` for both axes and is not invoked to terminate flight in `simulate`. Thus off-tile sampling does not itself produce invalid terrain. It is not evidence that the audited cases actually left the tile. [world.py:19–54](../../sim/world.py#L19-L54); [engine.py:287–322,572–578](../../sim/engine.py#L287-L322).
- Regional statistics are described as discs but are computed with square min/max/uniform filter windows at seven discrete radii, then nearest indexed lookup. Radii above 3840 m clamp to the largest available scale. This is a deliberate coarse geometric approximation, not an exact confidence ellipse or guaranteed bound for arbitrary uncertainty. [world.py:56–101](../../sim/world.py#L56-L101).
- `render_site.shadow_mask` explicitly computes an **unknown** horizon mask when the sun ray leaves the tile before clearing the tile maximum; `World._shadow` discards that unknown mask and uses only shadow/nonshadow. Consequently unknown pixels are counted as lit in `RegionStats`. This is a demonstrated information-loss path relevant to low-Sun reliability. [render_site.py:22–52](../../tools/render_site.py#L22-L52); [world.py:76–81,194–203](../../sim/world.py#L194-L203).
- Documentation records a truncated slope TIFF whose missing portion loaded as zero slope. `render_site.py` falls back to DEM-derived slope only on `OSError`, not on a successfully loaded but incomplete/zero-filled slope raster. The documentation's unconditional statement that the code derives slope is stronger than this conditional implementation. The current raster's integrity was not tested, and the new Unity runners derive geometry from heights rather than this slope TIFF. [FULL_LOG.md:24–28](../../docs/FULL_LOG.md#L24-L28); [README.md:55–58](../../README.md#L55-L58); [render_site.py:55–64](../../tools/render_site.py#L55-L64).

**Recommended fixes / acceptance:** preserve source URI/checksum/CRS/datum/nodata and exact resampling convention; round-trip corner, center and known landmark coordinates between source, Python and Unity; make out-of-map values invalid; retain unknown illumination separately; derive slope explicitly or validate supplied slope integrity. Compare plane/ramp and asymmetric landmark rasters across conversions to expose row flips, pixel-center offsets and scaling. A numeric georegistration error for this dataset remains unverified, so none is asserted here.

#### Camera survey: renderer-derived empirical surrogate, not validated lunar optics

- `CameraSurvey` creates a 40° nadir camera, 512² live image and 768² wider reference with matched nominal footprint scale. Both images render the **same current scene**; only camera position and Sun rotation change. No separate truth/prior terrain switch occurs, despite comments describing the reference as the onboard map. It depends on a scene object named `Sun`, does not pin the source scene/terrain hash and does not exclude unrelated visible objects through a sensor-specific culling mask. [CameraSurvey.cs:18–47,60–74](../../LANTERN/Assets/Editor/CameraSurvey.cs#L18-L74).
- Survey sample positions and lighting labels come from Python `World` truth (which includes synthetic unmapped features); the rendered Unity scene uses its own current terrain. Labels are evaluated at nominal locations, then the live camera is displaced by up to ±100 m. This is a source-visible mismatch between the survey's label geometry and the scene-image acquisition contract; its numerical importance has not been measured. [cam_survey_plan.py:7–29](../../sim/cam_survey_plan.py#L7-L29); [world.py:180–192](../../sim/world.py#L180-L192); [CameraSurvey.cs:39–47](../../LANTERN/Assets/Editor/CameraSurvey.cs#L39-L47).
- `cam_survey_match.py` converts PNG to grayscale, averages 2×2 pixels, adds Gaussian intensity noise with sigma `2 + .6*sqrt(DN)`, clips/rounds to 8-bit, and in primary mode replaces reference values below 40 with 20.4. ZNCC and a local parabola estimate translation; outputs become a table of normalized position errors/peaks versus lit fraction. These are explicit algorithmic assumptions, not an instrument-calibrated photon/electronics model. [cam_survey_match.py:16–24,40–75,85–97](../../sim/cam_survey_match.py#L40-L97).
- At runtime Python does not render images: it samples nearby entries in that empirical table by lit fraction and scales relative errors by current true AGL, including outside the survey's sampled 1500–5000 m band (camera eligible below 12000 m). The filter uses a nominal covariance curve, not the empirical distribution's conditional covariance. [cam_survey_plan.py:12](../../sim/cam_survey_plan.py#L12); [engine.py:498–535](../../sim/engine.py#L498-L535).
- Settings identify Built-in rendering (`m_CustomRenderPipeline=0`), serialized color space 0, non-linear light intensity setting, soft-shadow/cascade quality presets and Ultra 20 km shadow distance. The camera reads rendered RGB rather than a calibrated radiometric buffer. No source basis was found for a validated lunar BRDF, spectral response, exposure, PSF, stray-light or motion-blur claim. This is a gap in the implemented camera model, not an allegation that a particular mission requires all those effects at once. [GraphicsSettings.asset:40,63–64](../../LANTERN/ProjectSettings/GraphicsSettings.asset#L40); [ProjectSettings.asset:50](../../LANTERN/ProjectSettings/ProjectSettings.asset#L50); [QualitySettings.asset:274–290](../../LANTERN/ProjectSettings/QualitySettings.asset#L274-L290); [CameraSurvey.cs:33,65–74](../../LANTERN/Assets/Editor/CameraSurvey.cs#L65-L74).

**Recommended fixes / acceptance:** freeze scene, terrain/material/light/render settings and camera geometry per survey; make reference/truth terrain distinct when claiming map mismatch; retain unknown-horizon labels; test translation sign and image-footprint geometry with a planar asymmetric target; validate noise/exposure assumptions against the intended sensor and benchmark a reserved acquisition condition. Describe present evidence as “ZNCC behavior on this Unity rendering/noise pipeline,” not flight-camera reliability.

#### Art provenance is unusually clear, but purely illustrative

- `tools/build_lander_art.py` constructs geometry procedurally in Blender using primitive mesh operations, with explicit dimensions/materials; it exports selected mesh objects to FBX with Unity Y-up conversion and no animation. The source calls it original illustrative concept art and not flight-qualified hardware. The provided source and README support that stated provenance; this audit did not independently prove authorship or rebuild the binary assets. [build_lander_art.py:1–5,55–104,106–225](../../tools/build_lander_art.py#L106-L225); [art/lander/README.md:1–18](../../art/lander/README.md#L1-L18).
- The detailed body, legs, nozzle, tanks, optics and panels are visual geometry. Import disables colliders/cameras/lights/animation; the README explicitly says no collision shapes, controller, sensor extrinsics or mass properties are supplied. Unity material creation preserves portable color/metallic/roughness approximations, not Blender's procedural foil shader. [LanderArtPreview.cs:39–57,76–81](../../LANTERN/Assets/Editor/LanderArtPreview.cs#L39-L81); [art/lander/README.md:20–27](../../art/lander/README.md#L20-L27); [build_lander_art.py:43–53](../../tools/build_lander_art.py#L43-L53).
- Blender uses a Cycles studio stage with area lights and AgX; Unity preview uses studio directional fill and ambient illumination. Terrain replay uses a 55° demonstration light and ambient illumination, not the 2° camera-survey Sun. Screenshots across these paths cannot be pooled as evidence of low-Sun sensing. [build_lander_art.py:227–261](../../tools/build_lander_art.py#L227-L261); [LanderArtPreview.cs:82–110](../../LANTERN/Assets/Editor/LanderArtPreview.cs#L82-L110); [TerrainExperimentView.cs:63–64](../../LANTERN/Assets/Editor/TerrainExperimentView.cs#L63-L64).

**Acceptance:** keep “visual concept / enlarged markers / replay” labels; if art is attached to a physical vehicle, independently validate its transform/scale/extrinsics and collision/mass properties. The existing dimension guard checks imported height and an X-size upper bound; it is not engineering validation. [LanderArtPreview.cs:77–81](../../LANTERN/Assets/Editor/LanderArtPreview.cs#L77-L81); [TerrainExperimentReplay.cs:65–69,137–157](../../LANTERN/Assets/Scripts/Experiments/TerrainExperimentReplay.cs#L137-L157).

#### Unity version/configuration and computational reproducibility

- Project version is **6000.3.24f1**, revision `4e7b9b5b6244`. Package manifest includes AI Assistant `2.20.0-pre.2`, AI Inference `2.6.1` and Unity physics/terrain modules; lockfile resolves Burst/Collections and test framework dependencies. Presence of the AI Inference package does not establish it executes the scan models: the reviewed C# models use custom tree/logistic interpreters. [ProjectVersion.txt](../../LANTERN/ProjectSettings/ProjectVersion.txt); [manifest.json:3–4,19–23](../../LANTERN/Packages/manifest.json#L3-L23); [packages-lock.json:23–58,106–124](../../LANTERN/Packages/packages-lock.json#L23-L124); [PortableScanTrust.cs:66–87](../../LANTERN/Assets/Scripts/Experiments/PortableScanTrust.cs#L66-L87); [ScanUtilityPolicy.cs:40–55](../../LANTERN/Assets/Scripts/Experiments/ScanUtilityPolicy.cs#L40-L55).
- Project gravity is −1.62 m/s²; contact offset .01 m, solver iterations 6, velocity iterations 1, enhanced determinism disabled. The default timestep encoding corresponds to approximately .02 s, whereas new experiment runners explicitly simulate .05 s; these must not be confused. New bodies disable automatic gravity and apply their own lunar force, so gravity is not doubled in that path. [DynamicsManager.asset:7–14,35](../../LANTERN/ProjectSettings/DynamicsManager.asset#L7-L35); [TimeManager.asset:7–12](../../LANTERN/ProjectSettings/TimeManager.asset#L7-L12); [ShortDescentExperiment.cs:15,226,318–320](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L318-L320).
- Only `Assets/Scenes/Site04.unity` is enabled in build settings. Experimental orchestration is inside `Assets/Editor` and runs by Editor Play-mode callbacks; a normal player build of the currently enabled scene is not the experiment runner. [EditorBuildSettings.asset:7–10](../../LANTERN/ProjectSettings/EditorBuildSettings.asset#L7-L10); [TerrainExperimentCommand.cs:10–29](../../LANTERN/Assets/Editor/TerrainExperimentCommand.cs#L10-L29).
- Fixed seeds and explicitly consumed scan noise in both correction arms are good common-random-number engineering. They do not alone prove cross-platform PhysX determinism or identical sensor measurements after trajectories diverge; ray geometry necessarily changes. [ShortDescentExperiment.cs:234,251–254,307–312](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L307-L312); [DynamicsManager.asset:35](../../LANTERN/ProjectSettings/DynamicsManager.asset#L35).

**Acceptance:** freeze Unity revision, lockfile, physics/quality settings, source terrain and run configuration; compare repeated same-platform trajectories and declared cross-platform tolerances; perform timestep/solver convergence and terrain interpolation checks. Archive authoritative status and source manifests outside generated caches.

#### Read-only check record: exactly what was demonstrated

Executed from `D:\newprj` with `python -B -c`, importing `sim/engine.py` and NumPy; no file outputs and no Unity process. The fixture supplied zero-valued height/gradient/slope functions through `SimpleNamespace`, one run, `t_max=.25`, fixed gate, zero altimeter/IMU noise, zero initial errors and zero bursts. `Draws.T` includes its two extra slots, so the delay fixture logged two steps. No real terrain or historical result CSV was loaded.

Observed output:

```text
bias Jacobian: finite_difference= -0.03125 F= 0.0 expected= -0.03125
delay startup: logged_times= [0.25, 0.5]
  measured_ranges= [0.0, 0.0]
  true_agl= [65.043125, 30.172523905693]
contact: endpoint_agl= [0.0] recorded_agl= [1.0]
  recorded_height= [1.0] recorded_time= [0.25]
```

The essential reproduction (illustrative formatted equivalent of the executed inline command) is:

```python
import sys
sys.path.insert(0, 'sim')
import engine as e
import numpy as np
from types import SimpleNamespace as S
a = e.NavBatch(1, np.zeros((1,3)), np.zeros((1,3)), 1)
b = e.NavBatch(1, np.zeros((1,3)), np.zeros((1,3)), 1)
b.x[0,6] = 1e-5
a.predict(np.zeros((1,3))); b.predict(np.zeros((1,3)))
print((b.x[0,0]-a.x[0,0])/1e-5, a.F[0,6])
zero = lambda x,y: np.zeros_like(np.asarray(x, dtype=float))
grid = S(height=zero,
         grad=lambda x,y,step=None: (zero(x,y),zero(x,y)),
         slope_deg=lambda x,y,step=None: zero(x,y))
w = S(truth=grid, dem_grid=grid, map_banks=[grid], stats=None, coarse_ref=grid)
sc = e.Scenario('audit', burst_rate=0, delay_s=(1,1), t_max=.25)
d = e.Draws(w, sc, 1, 1)
d.alt_g[:]=0; d.pos0_err[:]=0; d.vel0_err[:]=0
d.bias_true[:]=0; d.imu_g[:]=0; d.burst[:]=False
r = e.simulate(w, dict(start=(0,0), target=(100,0), start_agl=100),
               sc, 'fixed', d, record_idx=0)
print(r['rec']['t'], r['rec']['r'], r['rec']['agl_true'])
d.delay_steps[:]=0
r = e.simulate(w, dict(start=(0,0), target=(100,0), start_agl=1),
               sc, 'fixed', d, record_idx=0)
print(r['z_final_true_agl'], r['rec']['agl_true'], r['rec']['z'], r['rec']['t'])
```

#### Ordered acceptance gates for a research-readiness release

1. **Correct the verified Python bugs before reusing affected benchmark claims:** transition/Jacobians, delayed startup, consistent delayed observation, contact recording and metric timestamps. Re-run analytic fixtures before any expensive benchmark rerun. Scope/impact on tables belongs to the coordinated results audit.
2. **Freeze the intended scientific system:** distinguish the new Unity correction experiment from the old Python benchmark/demo/replays; immutable source/config/data manifests and explicit complete-run state. Require a clean independent reproduction of the chosen mechanism experiment.
3. **Establish observable behavior:** exact translated/flat/planar/periodic terrain fixtures, uncertainty about absolute registration, valid/invalid/aged measurement semantics, and tests of estimator/guidance truth isolation.
4. **Establish numerical and physical limits:** timestep and interpolation convergence; correct fuel exhaustion; contact-speed validation; latency-aware correction; tested initial velocity/IMU bias/attitude assumptions appropriate to the claim.
5. **Tie any NASA-relevant extension to an actual intended use:** named vehicle/sensor/terrain-map requirements, sensor evidence, failure policy and target compute budget. Current hardcoded masses, thrust, Isp, speed/miss thresholds, Sun geometry and noise values are simulation parameters; the cited code does not document their derivation from a particular NASA mission requirement. [Vehicle parameters](../../sim/engine.py#L15-L20); [Unity guidance](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs#L101-L108); [Unity success](../../LANTERN/Assets/Editor/ShortDescentExperiment.cs#L329-L333).

### Inferences

- **Defensible now, subject to the separate result/source verification:** source-level proof that a simplified Unity state-estimate → match/gain → control → trajectory feedback experiment exists, with software-isolated truth evaluation and reproducible parameterization.
- **Not established by the inspected implementation:** flight-realistic lunar descent, robust absolute localization under unknown map registration, validated camera/lidar reliability, operational covariance/integrity guarantees, safe six-DOF touchdown or flight-processor real-time feasibility.
- A corrected narrow mechanism-study release is the most credible next deliverable. More visual realism would not address the principal correctness/observability issues identified above.

### Gaps

No formal NASA standard compliance or technology-readiness level is assigned. External mission literature/requirements are outside this implementation-only evidence base. Sensor calibration, actual target hardware, complete geographic datum provenance, binary raster integrity, real lunar illumination validation and independent repeated experiments remain open. Acceptance tests above are **recommendations**, not tests claimed to exist or pass in the repository.
