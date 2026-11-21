# LANTERN methodology and claims audit against lunar TRN / landing-navigation practice

Audit date: 29 October 2026. Workspace `D:\newprj` (read-only; no files other than this note were changed, nothing was run except text extraction of downloaded public PDFs into the session scratchpad). Builds on `research_notes/LANTERN research readiness audit/` (25 Oct), which covered implementation fidelity (I01–I16) and claims (F01–F22) **without external literature research**. This note does not repeat those findings except where a literature comparison changes or sharpens them.

Evidence labels:
- **REPO** — read directly in the repository (path:line, current working tree).
- **VERIFIED-FULLTEXT** — I read the full text (or the full relevant section) of the source.
- **ABSTRACT-ONLY** — I read only an abstract, record page, or institutional summary.
- **UNVERIFIED** — from search-engine snippets, prior repo notes, or my background knowledge; not confirmed against the source.
- **COMPUTED** — my own arithmetic from repo constants; not a measured result.

Note on line numbers: `ScanUtilityPolicy.cs` line numbers below are file-relative.

---

## 1. What does LANTERN actually implement (lidar, matcher, perturbations, dynamics/guidance, initial errors, success)?

### Takeaway
The Unity experiments implement a deliberately minimal map-relative position-fix loop: a synthetic 24×24 ray "lidar", an exhaustive 2-D translation search with a mean-removed squared-residual cost and an ad-hoc peak-to-mean confidence, a **hard state overwrite** (no Kalman filter, no covariance), near-perfect inertial propagation with perfectly known velocity, and a PD position-tracking guidance law with no terminal velocity-nulling phase. Map errors are a single Gaussian bump (8–20 m amplitude) or a pure 36–47 m translation of the prior. Success is first contact with miss <10 m, |vz| <2 m/s, |vh| <1 m/s.

### Cited Findings

**Lidar simulation (REPO)**
- 24 × 24 = 576 rays per scan in a square grid spanning ±20° about nadir in two axes (Euler pitch/roll interpolation), cast from the true body position, max range 3000 m — `LANTERN/Assets/Editor/ShortDescentExperiment.cs:246-257`; identical in `LANTERN/Assets/Editor/ScanUtilityRunner.cs:272-283`.
- Per-ray noise: Gaussian range error with σ = 0.05 m + 0.001 × range; 2 % independent dropout — `ShortDescentExperiment.cs:252-254`.
- Returned points are `direction × noisy range` in a frame with **perfect attitude** (body rotation frozen, `ShortDescentExperiment.cs:228`); no beam divergence/footprint averaging, no incidence-angle effects, no pointing or lever-arm error, no motion distortion within a scan (scan is instantaneous). Environment file states "3-DOF PhysX; ideal attitude" — `ShortDescentExperiment.cs:97`.
- Scans every 3 s, only when measured AGL > 80 m — `ShortDescentExperiment.cs:307-311`, `ScanUtilityRunner.cs:351-356`.
- COMPUTED: footprint width = 2·h·tan 20° ≈ 364 m at 500 m, 1092 m at 1500 m, 1456 m at 2000 m; adjacent-ray ground spacing ≈ 16 m at 500 m and ≈ 63 m at 2000 m. Range σ ≈ 0.55 m at 500 m and ≈ 2.05 m at 2000 m.
- Map/truth grids: 2.4 km crop sampled on a 301 × 301 grid (8 m spacing) from the Unity terrain (itself a 2049-sample resample of the 5 m PGDA DEM over 16 km, ~7.8 m), then truth resampled to a 513 × 513 TerrainCollider — `ShortDescentExperiment.cs:15-16,173-202`; `docs/PROJECT_EXPLAINED_AND_REFOCUSED.md:64-66`. Truth and prior share the same 8 m-grid ancestry, so "aligned" is an identical-map case (prior audit I12).

**Matcher (REPO, `LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs`)**
- Points are placed at the *estimated* position and compared against bilinear samples of the prior map; ~144 points used via deterministic stride — `:37-45`.
- Cost = variance of vertical residuals (mean squared residual minus squared mean), i.e. a mean-removed MSD that is insensitive to a constant height offset — `:46-48`.
- Search: exhaustive coarse grid ±128 m at 16 m steps (17 × 17 = 289 cells), then two 7 × 7 refinements at 4 m and 1 m steps around the best cell; translation only (no rotation, scale, or vertical solve), 1 m final resolution, no sub-cell interpolation — `:55-74`.
- Boundary flag is evaluated **only on the coarse result** (|shift| ≥ 128 on either axis) — `:64`.
- Confidence = clamp(1 − (best+0.01)/(mean cost of coarse cells >32 m from the best + 0.01)) — a peak-to-mean ratio, not a second-peak ratio, curvature/Hessian covariance, or calibrated probability — `:75-79`.
- Acceptance: not boundary AND RMS ≤ 8 m AND confidence ≥ 0.35 — `:80`.
- Self-checks exercise only a flat map, an empty scan, out-of-map, and one synthetic sinusoid with a known (−60, +40) offset — `ShortDescentExperiment.cs:144-166`.

**Estimator and correction (REPO)**
- `NavigationEstimate.Predict` integrates measured acceleration; `ObserveAltitude` overwrites estimated height with map(estimated x,z) + measured range; `Correct` **adds the accepted horizontal correction directly to position**; velocity is never corrected — `TerrainNavigationCore.cs:86-96`.
- "IMU": acceleration = finite difference of true PhysX velocity plus white noise σ = 0.002 m/s² per 0.05 s step, no bias, no scale factor, no attitude error — `ShortDescentExperiment.cs:300-302`.
- Initial velocity estimate equals truth exactly — `ShortDescentExperiment.cs:232-233`; `ScanUtilityRunner.cs:257-258`. Hence the injected horizontal error is effectively a constant offset that does not grow (prior audit I07).
- Altimeter: nadir ray with σ = 0.1 m — `ShortDescentExperiment.cs:303-305`.
- Learned / rule gain: the utility arm scales the proposed correction by g ∈ [0,1]; `utility_hybrid` uses g = 1 if prediction ≥ 0.75 else prediction, and both hybrid and "bounded" cap the applied magnitude at max(5 m, 0.5·AGL) — `LANTERN/Assets/Scripts/Experiments/ScanUtilityPolicy.cs:57-69`; applied via `ScanUtilityRunner.cs:299-306`.
- Utility features: RMS normalised by expected range noise, confidence, |correction|, AGL, distance between current correction and the residual of the previous one ("consistency"), has-previous flag — `ScanUtilityPolicy.cs:34-39`.
- Training label = clip(−(e·d)/|d|², 0, 1), the least-squares fraction of correction d that minimises true horizontal error e — `ScanUtilityRunner.cs:308-310`; protocol form `docs/SCAN_TRUST_PROTOCOL_V2.md:44-52` (algebraically identical).
- Model: 32-tree `RandomForestRegressor`, max_depth 8, min_samples_leaf 12, area/case weighting — `tools/train_scan_utility.py:38-39`. Validation gain MAE 0.213 vs 0.221 for always-full-gain — `docs/SCAN_UTILITY_RESULTS.md:109-111`.

**Dynamics and guidance (REPO)**
- 3-DOF point mass (rotation frozen), dry 1200 kg + 800 kg fuel, Isp 300 s, gravity 1.62 m/s², thrust magnitude clamp 6000 N, Δt = 0.05 s — `ShortDescentExperiment.cs:15,226-234,315-320`; `TerrainNavigationCore.cs:108`.
- Vertical: velocity profile v_y = −min(30, 0.5 + √(0.9·(AGL−0.5))) tracked with gain 0.8 — `TerrainNavigationCore.cs:103-104`.
- Horizontal: commanded acceleration = −0.04·x̂ − 0.5·v̂ (estimated position/velocity toward the origin), clamped to a_y·tan 10° — `TerrainNavigationCore.cs:105-107`. There is no terminal phase that freezes the position target or nulls horizontal velocity independent of position.
- Initial true state: zero horizontal velocity, v_y = −10 m/s, altitudes 500/1000/2000 m (v1), 500/2000 m (expanded), 500/1500 m (utility final/transfer); true start offset (−12, +16) m in final/transfer — `ShortDescentExperiment.cs:18,119,231-232`; `ScanUtilityRunner.cs:145,152,256-257`.

**Initial errors (REPO)**
- v1/expanded: (60, −40), (−80, 50), (100, 80) m → 72, 94, 128 m — `ShortDescentExperiment.cs:33`. COMPUTED: the 128 m case sits at the edge of the ±128 m search box.
- Utility final/transfer: magnitudes 35/70/95 m at 23/157/281° — `docs/SCAN_TRUST_PROTOCOL_V2.md:80-82`; training draws 5–140 m over the full circle — `:19-20`.
- Errors are injected constants, not draws from a navigation covariance or a propagated orbit-determination/IMU error model.

**Perturbations (REPO)**
- "Changed terrain": an additive Gaussian bump added to the truth only. v1: +12 m, σ 60 m at (120, 60) m — `ShortDescentExperiment.cs:181`. Utility variants: amplitudes 8/20/12/16 m, σ 50/100/75/65 m, centres 86–159 m from the target — `ScanUtilityRunner.cs:200-205`; protocol `docs/SCAN_TRUST_PROTOCOL_V2.md:31-33,61-64,83-84`.
- "Shifted map": the prior is the same DEM sampled at an offset s. v1 s = (40, −24) m (46.6 m); training (30, −20) 36.1 m and (−25, 35) 43.0 m; development (−28, 36) 45.6 m; final/transfer (22, −31) 38.0 m — `ShortDescentExperiment.cs:182-183`; `ScanUtilityRunner.cs:206-208`.
- No rotation, scale, skew, smoothing, low-frequency warp, rock/crater omissions, resolution mismatch, or illumination effects are modelled.

**Success (REPO)**
- `success = touchdown && vz < 2 && vh < 1 && miss < 10`, miss measured from the **true-frame origin** — `ShortDescentExperiment.cs:331-332`; `ScanUtilityRunner.cs:375-376`. Expanded/utility runs use PhysX contact velocity; v1 used an 8 cm proximity stop — `ShortDescentExperiment.cs:322-325`.

### Inferences
- The "estimator" is a deterministic reset loop, so the learned g plays the role of a scalar, isotropic Kalman gain K = P/(P+R) with P and R never represented. This matters for literature comparison (section 3).
- Because velocity is known perfectly and never corrected, every touchdown horizontal speed in these runs is a *guidance response* to position steps, not a velocity-knowledge error (section 5).
- The lidar noise model (0.1 % of range) is coarse but not obviously optimistic. The main optimism is perfect attitude, perfect velocity, no IMU bias, identical-grid truth/map, and instantaneous scans.

### Gaps
- I did not find verified flight-lidar specifications (e.g., ALHAT flash lidar array size, range precision) to benchmark the 576-ray pattern and noise model; flagged UNVERIFIED.

---

## 2. How do these elements compare with published TRN practice, and is the shifted-map failure an inherent observability limit?

### Takeaway
Published systems define their accuracy **relative to the onboard map**, and they treat map-tie/registration error as a separate budget item. Map-relative matching cannot remove a coherent map translation without an independent absolute reference. LANTERN's 0/18, 0/54 and 0/90 shifted-map outcomes are therefore **predetermined by construction**: with |s| = 38–47 m and a 10 m absolute-miss criterion, no map-relative method can succeed. They are not evidence about any policy. LANTERN's shift magnitudes are also roughly 5× the *pre-adjustment* LRO orbit errors and more than 100× the post-adjustment geolocation uncertainty Barker et al. report for the PGDA south-pole DEMs that LANTERN itself uses. They are stress values, not realistic LOLA-registration errors.

### Cited Findings

**Mars 2020 LVS / TRN (map-relative by design)**
- The LVS estimated the lander position *relative to a map* by matching descent-image landmarks to the map and fusing with IMU; Safe Target Selection used that estimate to choose a safe target, and the final error between targeted and actual landing location was 5 m against a 60 m requirement — [Zheng et al., "Mars 2020 Lander Vision System Flight Performance", NTRS 20230006986](https://ntrs.nasa.gov/citations/20230006986) — ABSTRACT-ONLY.
- JPL: "LVS achieves a position error <40 m relative to the map"; 12 and 6 m/pixel maps for coarse and fine localization; coarse mode matches 15 landmarks across 3 images with 128×128 templates in 1024×1024 windows; fine mode matches up to 150 landmarks with 15×15 templates in 100×100 windows; touchdown within 5 m of the LVS-targeted point; success also depended on low errors in the onboard safe-targets map — [JPL Robotics, Mars 2020 TRN](https://robotics.jpl.nasa.gov/what-we-do/flight-projects/mars-2020-rover/terrain-relative-navigation) — ABSTRACT-ONLY (institutional page read in full).
- Pre-TRN inertial position error "as large as 3.2 km"; 40 m (3σ) demonstrated in helicopter field tests — search-snippet attribution to NTRS/JPL records (e.g. [NTRS 20160009627](https://ntrs.nasa.gov/citations/20160009627)) — UNVERIFIED.
- The Mars 2020 map budget reportedly included map absolute position, attitude and distortion items, with co-registration bounded at <15 m (3σ) between elevation maps — search snippet of [Cheng, IPPW 2018](https://colorado.edu/event/ippw2018/mro-ctx-imagery-for-mars2020-cheng-jpl) (page returned 404 when fetched) — UNVERIFIED.

**Relative vs inertial errors in lunar descent analysis**
- In a linear-covariance analysis of NRHO-to-surface descent, relative navigation error drops from ~20 m to ~2 m at the hazard-detection scan "although the inertial navigation errors remain largely unchanged"; footprint dispersions improve from 18.96 m to 3.34 m (3σ) with HDA plus divert. The paper notes that Monte Carlo studies use "hundreds or thousands of runs" — [Woffinden, "Evaluating Lunar Descent and Landing Performance from a NRHO Using Linear Covariance Resetting Techniques", AAS 22-xxx, NTRS 20210026438](https://ntrs.nasa.gov/api/citations/20210026438/downloads/EvalLunarDescentResetting.pdf) — VERIFIED-FULLTEXT (relevant sections).

**ALHAT practice**
- ALHAT ALDAC-2 (6-DOF POST2 Monte Carlo, dispersing thrust, Isp, mass properties, sensor errors and navigated initial state). TRN measurements run from 15 km to 5 km altitude; velocimeter updates begin at 2 km; HRN builds onboard DEMs during the approach (~500 m trigger) and "aligns them using digital correlation of elevations"; vertical descent begins ~30 m above the surface. Requirements: global 3σ < 90 m and local 3σ < 3 m. Global was met; local was not met even with HRN — [Davis, Striepe, Maddock, Johnson, Paschall, "POST2 End-to-End Descent and Landing Simulation for ALHAT Design Analysis Cycle 2", NTRS 20100025998](https://ntrs.nasa.gov/api/citations/20100025998/downloads/20100025998.pdf) — VERIFIED-FULLTEXT (4-page paper).
- A lidar-TRN analysis paper reportedly found no matching degradation for initial position uncertainty up to 1.6 km — search snippet of [CORE record "Analysis and Testing of a LIDAR-Based Approach to TRN for Precise Lunar Landing"](https://core.ac.uk/works/24786392) (403 on fetch) — UNVERIFIED.
- The ALHAT TRN accuracy requirement is landing within 100 m of a predetermined location; TRN needs a prior reference map — [NTRS 20090018401 (Overview of TRN approaches for precise lunar landing)](https://ntrs.nasa.gov/citations/20090018401) — ABSTRACT-ONLY via search summary (authorship not confirmed on the record).

**Map accuracy limits TRN, and published map-error models are richer than LANTERN's**
- "The accuracy achievable using TRN is limited by the accuracy of the reference Digital Elevation Map." LuNaMaps deforms lunar DEMs with local height/albedo changes and with global deformations: scale, smoothing, skew, **shift**, rotation, and low-frequency noise. It notes that photoclinometry tends to produce global rather than per-pixel errors — [Gnam, Restrepo, Liounis (GSFC), "DEM Parametric Error Analysis Using Corresponding NAC Images", SIW 2022, NTRS 20220008667](https://ntrs.nasa.gov/api/citations/20220008667/downloads/lunamaps_siw22_abstract.pdf) — VERIFIED-FULLTEXT (extended abstract).

**Realism of LANTERN's shift and relief magnitudes (PGDA Product 78 / LOLA)**
- LRO orbit-reconstruction errors are ~7/7/0.5 m (along/cross/radial). After iterative self-consistent track adjustment, final geolocation uncertainty is "less than ~12–14 cm horizontally and ~2 cm vertically for most (~68%) of the tracks" (abstract: ~10–20 cm horizontal, ~2–4 cm vertical per 16×16 km region). The authors state that this "applies to total absolute position". LDEM surface-height uncertainty is typically 0.30–0.50 m RMS and slope uncertainty 1.5–2.5°. Most 5 m pixels are interpolated. Imagery-derived models "are not as well controlled geodetically" — [Barker et al., "Improved LOLA elevation maps for south pole landing sites: Error estimates and their impact on illumination conditions", Planet. Space Sci. 2021, doi:10.1016/j.pss.2020.105119, NTRS 20205009660](https://ntrs.nasa.gov/citations/20205009660) — VERIFIED-FULLTEXT.
- COMPUTED: LANTERN shifts of 36–47 m are ≈5–7× the pre-adjustment orbit error and ≈200–400× the reported post-adjustment geolocation uncertainty. LANTERN bumps of 8–20 m amplitude are ≈16–65× the 0.3–0.5 m height RMS.
- Data used: `README.md:56` (PGDA Product 78 Site04 5 m/pixel) — REPO; product page [PGDA 78](https://pgda.gsfc.nasa.gov/products/78) — not fetched.

**Bayesian / filter-based TRN for comparison**
- The point-mass filter gives an approximate Bayesian solution for terrain navigation; EKF-type local approximations fail with an unstructured nonlinear map; reported Monte Carlo performance reaches the Cramér–Rao bound — [Bergman, Ljung, Gustafsson, "Terrain navigation using Bayesian statistics", IEEE Control Systems Mag. 19(3):33–40, 1999](https://rt.isy.liu.se/research/reports/Ph.D.Thesis/PhD579.pdf) — ABSTRACT-ONLY via search summaries.
- Choe & Park, "Point-Mass Filtering With Boundary Flow and Its Application to TRN", IEEE TAES 2021; Choe, Song, Park, "Lightweight Marginalized Particle Filtering With Enhanced Consistency for TRN", IEEE TAES 58(3) 2022 — [dblp](https://dblp.dagstuhl.de/rec/journals/taes/ChoeSP22.html) — bibliographic only (UNVERIFIED content).
- Choe et al., "LiDAR-Inertial-Based Absolute Positioning With Sparse DEM for Accurate Lunar Landing", IEEE TAES 60(3):3482–3495, 2024: ensemble Kalman filter with a fractal terrain model and two-step filtering to handle lidar/DEM resolution mismatch; ~10 m (1σ) with a 60 m-resolution map — [record](https://www.bohrium.com/paper-details/lidar-inertial-based-absolute-positioning-with-sparse-dem-for-accurate-lunar-landing/977543077256232982-2511) — ABSTRACT-ONLY.
- PITFAL (Adams et al., SciTech 2025): multi-beam slant-range statistical consensus for fault detection of apparent altitudes in SPLICE simulations — [NTRS 20240014100](https://ntrs.nasa.gov/citations/20240014100) — ABSTRACT-ONLY (per prior audit `external_citation_verification.md:8`). It addresses range-beam fault rejection, not horizontal scan-gain scheduling.

**LANTERN's own observability statements (REPO)**
- "Global map translation remains unobservable from local shape alone" — `docs/SCAN_TRUST_PROTOCOL_V2.md:9-11`; "Local shape alone cannot uniquely resolve a global map translation" — `docs/PROJECT_EXPLAINED_AND_REFOCUSED.md:180-181`; formal derivation (corrected error = −s) — prior audit `implementation_fidelity.md:178-184` (I10).

### Inferences
- **Observability (derivation, COMPUTED from code).** Prior(x) = DEM(x + s), truth(x) = DEM(x). A correct shape match yields estimate q = p − s. Guidance drives q → 0, so the true touchdown is at s and the absolute miss equals |s| (38.0 m in final/transfer). Success requires miss < 10 m, so **every** shifted-map case must fail unless no correction is accepted *and* the initial error happens to be < 10 m. None of the initial errors is < 10 m. The 0/N results are a tautology of the design.
- **The target-frame choice is the real issue.** In Mars 2020 practice the target is chosen *in the map* (STS) and accuracy is reported map-relative. Under that convention, LANTERN's shifted-map lander touches down on the terrain point the map designates as the target. It is a *map-relative success* and an *absolute-frame miss*. LANTERN should report both metrics. An absolute miss matters only when the target is fixed by an independent frame (a surface asset, a beacon, a site chosen from a differently registered product).
- I found no single paper sentence stating literally that "map-relative TRN cannot detect a global map offset". The support is structural. The flight literature specifies accuracy relative to the map (JPL/Zheng et al.) and keeps relative and inertial error separate (Woffinden: relative error falls 20 → 2 m while inertial error is unchanged). Map-tie/co-registration appears as a separate budget item (UNVERIFIED snippet). Pair these with the derivation above rather than citing a "proof" from the literature.
- **Altitude regime and error magnitudes differ from flight practice.** ALHAT TRN runs at 15–5 km with km-scale prior uncertainty (Mars 2020 ~3.2 km, UNVERIFIED). LANTERN starts at 0.5–2 km with 35–140 m errors and a ±128 m window. LANTERN is closer to an ALHAT HRN-like terminal regime, but against an orbital prior DEM rather than an onboard-built map.
- **Matcher.** Exhaustive translation search with a mean-removed MSD cost is a reasonable, classic correlation-TRN design. Published systems additionally carry covariance and fuse the result in a filter (ALHAT navigation filter; Choe EnKF), or keep a multimodal posterior (PMF/PF), rather than overwriting the state. LANTERN's confidence is uncalibrated, and the boundary test only covers the coarse stage (prior audit I11).
- **Map-error realism.** At Barker-scale errors (sub-metre heights, decimetre geolocation), the accurate-map case is the realistic one for PGDA-quality south-pole sites, but LANTERN's accurate-map case is optimistic for a different reason (identical grids). The bump and shift cases are gross-error stress tests and should be labelled that way, ideally with a magnitude sweep spanning Barker-realistic to gross values and LuNaMaps-style deformation families.

### Gaps
- Exact Mars 2020 map-tie / co-registration numbers (snippet only); full text of Johnson & Montgomery 2008 and of the lidar-TRN 1.6 km sensitivity study were not accessible (403/404).
- No verified published value for typical horizontal registration error between LRO-NAC-derived DEMs/orthophotos and LOLA at the south pole; Barker only states that imagery products are less well controlled.

---

## 3. Is learning a scalar correction gain with a random forest similar to published approaches?

### Takeaway
Yes. It is a narrow, supervised, per-scan instance of well-established ideas: learned Kalman gain (KalmanNet), learned measurement-noise covariance (AI-IMU), innovation-based adaptive estimation (Mohamed & Schwarz), and learned TRN-match uncertainty (Acharya et al., RA-L 2025, the closest TRN-specific analogue). Michaelson et al. (TAES 2024) also combine TRN with measurement rejection and online measurement covariance. LANTERN's distinguishing features are that it learns an oracle gain label rather than a covariance or an end-to-end filter, and that it evaluates policies by full closed-loop landing outcome. That supports a modest applied finding, not a method-novelty claim.

### Cited Findings
- KalmanNet keeps the Kalman-filter structure but replaces the gain computation with a compact RNN. Training is supervised, and the loss is computed on the state estimate rather than on true gains — [Revach et al., "KalmanNet: Neural Network Aided Kalman Filtering for Partially Known Dynamics", IEEE TSP 70:1532ff, 2022, arXiv:2107.10043](https://arxiv.org/abs/2107.10043) — ABSTRACT-ONLY. Unsupervised variant: [arXiv:2110.09005](https://www.arxiv.org/pdf/2110.09005) — ABSTRACT-ONLY.
- AI-IMU: deep networks dynamically adapt the Kalman filter's measurement-noise covariances from raw IMU signals; hand-tuned adaptation rules are application-specific — [Brossard, Barrau, Bonnabel, "AI-IMU Dead-Reckoning", IEEE T-IV 5(4):585–595, 2020, arXiv:1904.06064](https://arxiv.org/abs/1904.06064) — ABSTRACT-ONLY.
- Innovation-based adaptive estimation (IAE) and multiple-model adaptive estimation (MMAE). An ML-based adaptive Kalman filter choosing filter weights and gain factors outperformed a conventional KF when adapting Q, R or both — [Mohamed & Schwarz, "Adaptive Kalman Filtering for INS/GPS", J. Geodesy 73:193–203, 1999, doi:10.1007/s001900050236](https://link.springer.com/doi/10.1007/s001900050236) — ABSTRACT-ONLY.
- Deep models of non-Gaussian aleatoric uncertainty (parametric, discretised, generative) evaluated on real **terrain-relative navigation** data; TRN systems typically treat per-match uncertainty as homogeneous Gaussian and discard high-uncertainty matches. Uncertainty is conditioned on the matching similarity surface (search snippet) — [Acharya et al., IEEE RA-L 10(1):660–667, 2025, arXiv:2405.20513](https://arxiv.org/abs/2405.20513) — ABSTRACT-ONLY.
- Michaelson, Wang, Zanetti, "Terrain-Relative Navigation with Neuro-Inspired Elevation Encoding", IEEE TAES 60(3):3368–3378, 2024 — includes measurement rejection and online measurement covariance — repo-reported in `docs/MAP_EFFICIENCY_RECHECK.md:28-35` — UNVERIFIED by me.
- A 2011 lunar soft-landing navigation paper fuses a Sage–Husa noise-statistics estimator with an iterated KF — [BIT record](https://pure.bit.edu.cn/en/publications/3d-terrain-feature-matching-based-navigation-for-lunar-soft-landi/) — UNVERIFIED (snippet).
- LANTERN: label = oracle least-squares gain from truth (`ScanUtilityRunner.cs:308-310`); direction-free diagnostics as features (`ScanUtilityPolicy.cs:34-39`); offline MAE barely better than always-1 (0.213 vs 0.221, `docs/SCAN_UTILITY_RESULTS.md:109-110`); policy selected by development landings (`docs/SCAN_TRUST_PROTOCOL_V2.md:73-76`); the project itself disclaims method novelty (`docs/PROJECT_EXPLAINED_AND_REFOCUSED.md:159`) — REPO.

### Inferences
- Mapping to the literature: g ≈ scalar Kalman gain. Predicting g from fit RMS, confidence and AGL is functionally a learned R (as in AI-IMU and Acharya et al.), and the "consistency" feature is an innovation-consistency proxy (as in IAE). KalmanNet differs in training end-to-end on state error; LANTERN trains on a per-scan oracle label and only selects among three gain mappings on landing outcomes.
- Missing baselines needed for a publishable comparison: (i) a real KF/EKF with matcher-derived covariance (e.g. from the cost-surface curvature) and χ² innovation gating; (ii) an IAE-style adaptive R; (iii) a PMF/PF that keeps the multimodal hypothesis. Each needs a tuning budget matched to the learned policy's. The current "bounded" rule is only a magnitude clamp.
- The label optimises instantaneous position error, not landing outcome. KalmanNet-style end-to-end or outcome-weighted training is the published direction that addresses exactly LANTERN's observed mismatch (lower miss but more speed violations).

### Gaps
- I did not find a published lunar-TRN paper that uses a tree ensemble to schedule a scalar correction gain. That is absence of evidence from a limited search (~6 queries), not proof of novelty.

---

## 4. Are LANTERN's evaluation statistics adequate compared with EDL Monte Carlo practice?

### Takeaway
No, not for anything beyond descriptive within-batch comparisons. The final utility test has one terrain area (Site04) and the transfer test three (Site01), with seeds changing only sensor noise. Outcomes are dominated by the map condition: aligned ≈ 100 %, shifted 0 % by construction. The success endpoint therefore discriminates between arms only through the changed-terrain cells. EDL practice uses thousands of dispersed end-to-end runs and 3σ or 99 % requirements. LANTERN's runtime (~0.37 s per descent) makes that scale cheap.

### Cited Findings
- InSight's flight-reference campaign used 8001 Monte Carlo cases, 99 %-tile landing-ellipse limits and a safe-landing probability > 95 % — [NTRS 20200002909](https://ntrs.nasa.gov/api/citations/20200002909/downloads/20200002909.pdf) — UNVERIFIED (snippet; PDF not opened).
- MSL EDL simulation collects outputs "over thousands of individual instantiations" — [Way et al., NTRS 20130011617](https://ntrs.nasa.gov/api/citations/20130011617/downloads/20130011617.pdf) — UNVERIFIED (snippet). MER sites were assessed within the central 99 % of landing dispersions — [Adler, MER talk](https://marsoweb.nas.nasa.gov/landingsites/mer2003/doc/pasadena_01/talks/Adler-MER.pdf) — UNVERIFIED (snippet).
- Woffinden: Monte Carlo sample statistics of "hundreds or thousands of runs" are used to compute GN&C dispersion and navigation-error covariances; linear covariance analysis is the complementary tool — [NTRS 20210026438](https://ntrs.nasa.gov/api/citations/20210026438/downloads/EvalLunarDescentResetting.pdf) — VERIFIED-FULLTEXT.
- ALHAT ALDAC-2 states requirements as 3σ (90 m global, 3 m local) over dispersed vehicle, sensor and initial-state parameters — [NTRS 20100025998](https://ntrs.nasa.gov/api/citations/20100025998/downloads/20100025998.pdf) — VERIFIED-FULLTEXT.
- LANTERN final Site04: 54 paired configurations per arm = 1 area × 2 altitudes × 3 conditions × 3 errors × 3 seeds; successes 24/54 for geometric, bounded and utility alike; by condition 18/18 aligned, 6/18 changed, 0/18 shifted — `docs/SCAN_UTILITY_RESULTS.md:27-51`. Transfer: 54/162 for both arms, equal to all 54 aligned cases; 0/54 changed and 0/54 shifted — `docs/SCAN_UTILITY_TRANSFER_RESULTS.md:28-34,43-47`. Expanded geometric: 90/90 aligned, 3/90 changed (all one area/altitude/seed), 0/90 shifted — `docs/TERRAIN_MATCHING_EXPANDED_RESULTS.md:16-20,34-36` — REPO.
- No significance test or population confidence claim was planned — `docs/SCAN_UTILITY_TRANSFER_PROTOCOL.md:57-63` — REPO. Wall time 298 s for 810 descents — `docs/SCAN_UTILITY_TRANSFER_RESULTS.md:84` — REPO.

### Inferences
- COMPUTED (exact/rule-of-three): 0/54 bounds the true rate at ≤ ~5.4 % (95 %), and 54/54 or 90/90 give lower bounds of ~94.6 % and ~96.7 %. Demonstrating a 99 % success probability at 99 % confidence with zero failures needs n ≥ ln(0.01)/ln(0.99) ≈ 459 independent trials. LANTERN's independent unit is the terrain area (1 or 3), not the descent.
- Seeds add only sensor-noise variation. Paired-configuration counts (41/7/6; 105/39/18) are correlated within area, so a cluster bootstrap by area or a mixed-effects model is needed, plus McNemar tests on paired success and paired Wilcoxon or bootstrap CIs on miss.
- Because aligned and shifted cells are saturated by design, the success endpoint has almost no power to separate arms. Report the changed-terrain stratum separately, and add continuous endpoints with CIs (miss, |vh| distribution, the P(|vh|>1) exceedance curve).
- At ~0.37 s per descent, 10,000 dispersed runs (random error direction and magnitude from a covariance, altitude, bump parameters, shift, many PGDA sites) take about an hour. Scale is not the constraint; independent terrain and realistic dispersion models are.

### Gaps
- The InSight 8001-case and MSL "thousands" figures were not confirmed in full text.

---

## 5. Why might horizontal-speed violations rise under changed terrain, and is that a known phenomenon?

### Takeaway
In LANTERN the mechanism is almost certainly guidance-side. A wrong (or right) position step is fed straight into a PD position-tracking law with no terminal velocity-nulling phase, and the ~19 s from the last scan (80 m AGL) to contact is only about two slow time constants of the horizontal loop. The literature recognises the general problem: Apollo-era analyses flagged guidance "overreacting" to navigation updates and recommended filtering or re-weighting the updates. Flight landers use a terminal vertical-descent phase driven by velocity sensing. I found no modern paper that isolates "step position correction → touchdown lateral velocity" as such, so this is partly inference.

### Cited Findings
- REPO facts: `Correct` changes position only (`TerrainNavigationCore.cs:94-95`); horizontal command −0.04·x̂ − 0.5·v̂ clamped to a_y·tan 10° (`:105-107`); scans stop below 80 m AGL (`ShortDescentExperiment.cs:310`); no terminal phase exists. All utility speed violations occurred under changed terrain (Site04 7/7 at 500 m; Site01 47/47 split 23 at 500 m, 24 at 1500 m) — `docs/SCAN_UTILITY_RESULTS.md:53-58`; `docs/SCAN_UTILITY_TRANSFER_RESULTS.md:49-52`. Expanded: 69/90 changed-terrain ON contacts > 1 m/s, max 6.83 m/s; 0 in aligned — `docs/TERRAIN_MATCHING_EXPANDED_RESULTS.md:26-30`. In the transfer, utility's changed-terrain mean miss (75.19 m) exceeded OFF (64.45 m) — `docs/SCAN_UTILITY_TRANSFER_RESULTS.md:43-52`.
- Apollo: terrain elevation departing from the landing-site reference could cause navigation error and make guidance overreact to altitude updates near high gate; the suggested remedies were on the navigation side (filter the radar data or readjust the radar weighting functions) — search summary of 1970 NASA reports on LM landing-radar updates ([NTRS 19700025264](https://ntrs.nasa.gov/api/citations/19700025264/downloads/19700025264.pdf), [NTRS 19700026474](https://ntrs.nasa.gov/api/citations/19700026474/downloads/19700026474.pdf)) — UNVERIFIED. The 19700025264 record page is titled "False high gate targeting for LM powered descent" (McSwain & Moore, MSC-68-EG-07) and gives no abstract, so I could not confirm which report contains the quoted statement. Weighting factors were derived from Kalman/Battin least-squares estimation and gated by altitude bands — UNVERIFIED (snippets).
- ALHAT: vertical descent starts ~30 m above the surface; velocimeter (Doppler lidar) updates begin at 2 km; altimeter and velocimeter are deactivated during HRN "to also help keep the spacecraft position knowledge consistent" — [Davis et al., NTRS 20100025998](https://ntrs.nasa.gov/api/citations/20100025998/downloads/20100025998.pdf) — VERIFIED-FULLTEXT.
- Navigation/trajectory resets alter trajectory dispersions, footprint and propellant, and are modelled explicitly (state and covariance reset; replanning after an HDA divert) — [Woffinden, NTRS 20210026438](https://ntrs.nasa.gov/api/citations/20210026438/downloads/EvalLunarDescentResetting.pdf) — VERIFIED-FULLTEXT.

### Inferences
- COMPUTED (linear, unsaturated): the horizontal loop ẍ = −0.04x − 0.5ẋ has poles at −0.1 and −0.4 s⁻¹ (ζ ≈ 1.25, slow time constant 10 s). For a position step Δ, peak lateral speed ≈ 0.063·Δ at t ≈ 4.6 s, and the residual speed after 19 s ≈ 0.02·Δ. The tilt clamp (≈0.29 m/s² near hover) slows the build-up but also slows the velocity nulling.
- COMPUTED: descent from 80 m AGL on the profile v = √(0.9h) takes ≈ 19 s. A single late step of ≳50 m therefore leaves ≳1 m/s at contact. In changed terrain the matcher can propose successive inconsistent corrections every 3 s; these re-excite the loop and plausibly explain multi-m/s contacts. This is consistent with the observed pattern but not causally isolated.
- Why utility can *increase* violations while lowering mean miss: partial gains spread one large step into several smaller steps over successive scans. That moves the last effective step closer to touchdown. The label also rewards position error only, with time-to-go entering only through AGL. Both are hypotheses consistent with prior audit F06 and need an ablation.
- Standard mitigations to test, as guidance/estimation baselines rather than ML: blend the correction in over a time constant (an "update fading" analogue of Apollo re-weighting); freeze the target and stop position updates below an altitude/time-to-go gate; add a terminal phase that nulls horizontal velocity independent of position; make the lateral gain time-to-go aware (e.g. ZEM/ZEV-type guidance; UNVERIFIED as a specific citation); propagate covariance so the KF gain is naturally small for low-information scans.

### Gaps
- No verified modern source quantifying touchdown lateral-velocity transients caused by TRN position resets; the Apollo statement is snippet-level.

---

## 6. Which concrete research contributions are defensible, and which claims should LANTERN not make?

### Takeaway
The defensible path is an *outcome-based evaluation methodology plus mechanism study* of TRN correction gating in closed loop, not a new estimator. Specifically: (a) show that per-scan rejection metrics mispredict landing outcomes; (b) explain and mitigate correction-induced lateral-velocity transients; (c) separate map-relative from absolute accuracy, with a formal observability statement; (d) benchmark the learned gain against KF/χ²/IAE/PMF baselines under realistic, literature-grounded map-error models and Monte Carlo statistics.

### Cited Findings
- LANTERN already documents: the v1 veto's negative result (18/162 vs 90/162) — `docs/PROJECT_EXPLAINED_AND_REFOCUSED.md:119-123`; a failed pre-written transfer criterion — `docs/SCAN_UTILITY_TRANSFER_RESULTS.md:10-15`; no novelty claim — `docs/PROJECT_EXPLAINED_AND_REFOCUSED.md:159-160`; frozen protocols and hashes — `docs/SCAN_TRUST_PROTOCOL_V2.md:1-5,95-98` — REPO.
- Literature anchors are in sections 2–5: map-relative accuracy (JPL/Zheng et al.), relative vs inertial error (Woffinden), map-error families (LuNaMaps), DEM error magnitudes (Barker et al.), learned gain and covariance (KalmanNet, AI-IMU, Acharya et al.), adaptive KF (Mohamed & Schwarz), Bayesian TRN (Bergman et al.; Choe & Park), and Monte Carlo/3σ practice (ALHAT, Woffinden).

### Inferences
**Contributions LANTERN could pursue (feasible with existing code):**
1. **Closed-loop vs per-scan metric mismatch.** Quantify, with CIs over many areas, how per-scan "wrong-accept" rates and offline gain MAE correlate (or fail to correlate) with landing outcomes. Existing v1/v2 data are development evidence. Frame it against KalmanNet's end-to-end training argument.
2. **Mechanism and mitigation of correction-induced lateral speed.** Derive the step-response bound (section 5), predict |vh| at contact from (Δ, time-to-go), verify in simulation, then test guidance-side mitigations (blending, terminal gate, velocity-nulling phase) against the learned gain on a newly reserved test. This is cheap, falsifiable and literature-connected (Apollo re-weighting; ALHAT vertical descent).
3. **Map-relative vs absolute evaluation.** Report both metrics and state the observability limit formally. Add an independent-reference arm (e.g. absolute position prior with covariance from orbit determination, or a surveyed landmark/beacon) and show what it resolves. Sweep shift magnitude from Barker-realistic (≤1 m) to gross values (≥40 m).
4. **Literature-grounded baselines.** Replace the overwrite with a KF whose R comes from the cost-surface curvature, plus χ² gating; add IAE-style adaptive R and a PMF. Tune all with budgets matched to the learned policy's. Only then compare the RF gain.
5. **Realistic map-error and dispersion models.** Use LuNaMaps deformation families (scale, rotation, skew, smoothing, low-frequency noise), Barker height/slope uncertainty, resolution mismatch (e.g. map coarser than truth, as in Choe et al. 2024), and error vectors drawn from a covariance. Run thousands of dispersed cases across all PGDA sites, with the area as the statistical unit.
6. **Fidelity upgrades before any mission-relevance claim:** IMU bias, attitude error and its coupling into the scan geometry, uncertain velocity, finite scan time, and higher-altitude/larger-error regimes (km-scale, 15–5 km as in ALHAT TRN).

**Claims LANTERN should not make:**
- That shifted-map 0/N outcomes show a method weakness or are "unsolved" by the policies. They are guaranteed by the absolute-frame metric and |s| > 10 m. Under the map-relative convention used in flight (Mars 2020), those landings hit the map-designated point.
- That 36–47 m shifts or 8–20 m bumps represent realistic PGDA/LOLA south-pole map errors. Per Barker et al. they are gross-error stress cases.
- Any method novelty for "learned trust/gain" (close analogues: KalmanNet, AI-IMU, IAE, Acharya et al. 2025, Michaelson et al. 2024).
- Improved landing success, safety, or statistical significance: successes are identical across arms (24/54; 54/162), the transfer criterion failed, and there are 1–3 areas.
- Generalisation across lunar sites, flight-lidar realism, or full-descent validity (ideal attitude, perfect velocity, 0.5–2 km starts, ±128 m window).
- That the RF output is a calibrated probability or a covariance.
- Mission-requirement comparisons (e.g. "meets 40 m" or "3σ"). LANTERN neither computes 3σ statistics nor uses mission-like dispersions.

### Gaps
- Whether any published lunar-TRN study already reports closed-loop touchdown-velocity consequences of TRN gating; not found in this limited search, so it needs a targeted check (AIAA GNC/SciTech 2018–2026, JGCD, JSR) before claiming it as a gap.
