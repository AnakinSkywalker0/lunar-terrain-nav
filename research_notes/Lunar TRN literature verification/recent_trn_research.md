# Recent (2023-2026) Terrain-Relative Navigation Research for Planetary/Lunar Landing: Learned Methods, Map Error, Ambiguity, and Measurement Trust

Notes compiled 2026-10-29. Each item is labelled VERIFIED-FULLTEXT (I read the paper's methods/results text), ABSTRACT-ONLY (abstract or publisher/indexer metadata only), or UNVERIFIED (search snippet, aggregator, or secondary press only). "NARROW-SIM" flags evidence that comes from a single synthetic scenario or a tiny trajectory set.

Evidence-strength scale used below: Flight > HIL/field test > scaled terrain rig > rendered imagery from real orbital maps > pure synthetic simulation.

## Q1. Learned TRN: crater detection/matching, learned feature matching against orbital imagery, learned pose regression, sim-to-real

### Takeaway
Learned crater-based TRN is active, but almost all of the 2023-2026 evidence comes from images rendered from LROC/LOLA products, not flight imagery. Headline errors run from tens to hundreds of metres from orbit or high altitude. Papers rarely compare against a shared baseline on a shared test set. The only flight-proven map-relative localization system (Mars 2020 LVS) is classical, not learned. Learned matchers such as Geo-LoFTR and LightGlue-class methods help with illumination change, but no controlled cross-method lunar benchmark exists.

### Cited Findings
**Candan & Servadio (Iowa State), "Deep Learning-Based Lunar Crater Terrain Relative Navigation", arXiv 2606.14776 (2026). VERIFIED-FULLTEXT (HTML). NARROW-SIM.**
- **Method:** U-Net++ (ResNet50 encoder) outputs crater rim and centre masks. Detections are matched to projected catalog craters by nearest neighbour (τ = 3 px). The filter is a 6-state EKF with two-body gravity, an auxiliary altitude measurement (1 m σ) and residual gating — [arXiv HTML](https://arxiv.org/html/2606.14776v1)
- **Data and setting:** Training patches are rendered from the LROC WAC global mosaic and labelled with the Robbins 2019, Head 2010 and Barlow 2012 catalogs. Testing is pure simulation: synthetic orthographic frames along a 100 km orbit, with no real images, no IMU model and no dynamic illumination — [arXiv HTML](https://arxiv.org/html/2606.14776v1)
- **Numbers:** Pixel characterisation over 6,500 images gave 80,293 matches at a 2.0 px threshold, mean radial error 0.8163 px. Navigation: a 5 km initial offset is reduced to "a few hundred meters"; in another section the error floor is about 50-100 m from a 1 km initial σ, with velocity error near 2.5 m/s. Detection precision and recall are not reported — [arXiv HTML](https://arxiv.org/html/2606.14776v1)
- **Internal inconsistencies:** The Monte Carlo count is given as 50 in one place and N = 500 in figure captions. The association method is described three ways (Hungarian, linear assignment, "quadrant spread"). The conclusion says "without radar altimeter", yet the filter uses an altitude measurement. LunaNet is cited as the baseline (~1.4 px), but there is no head-to-head run — [arXiv HTML](https://arxiv.org/html/2606.14776v1)

**McLeod, Chng, Rodda, Chin, "AI-Enabled Crater-Based Navigation for Lunar Mapping" (STELLA), arXiv 2509.20748 (Sep 2025). ABSTRACT-ONLY.**
- **Method:** Mask R-CNN crater detector, descriptor-less crater identification, a robust perspective-n-crater pose solver, and batch orbit determination — [arXiv](https://arxiv.org/abs/2509.20748)
- **Data:** New dataset CRESENT-365, 15,283 images rendered from high-resolution DEMs with SPICE Sun geometry, emulating a year-long mapping mission; CRESENT+ is also used — [arXiv](https://arxiv.org/abs/2509.20748)
- **Claim:** "metre-level position accuracy and sub-degree attitude accuracy on average". This is a mapping-orbit setting, not landing; no baselines are named in the abstract — [arXiv](https://arxiv.org/abs/2509.20748)

**Andolfo, Genova et al., "Neural Network-Aided Optical Navigation for Precise Lunar Descent Operations", Aerospace 12(3):195 (Feb 2025). ABSTRACT-ONLY (via OpenAlex; MDPI returned 403).**
- **Method and data:** NN crater detection matched to an onboard landmark database. Detection is tested on synthetic images from a custom Blender pipeline under varied illumination — [OpenAlex record](https://api.openalex.org/works/doi:10.3390/aerospace12030195); DOI [10.3390/aerospace12030195](https://doi.org/10.3390/aerospace12030195)
- **Claim:** In simulations based on JAXA SLIM, final position errors are consistent with 3σ < 100 m horizontal at altitudes down to about 10 km — [OpenAlex record](https://api.openalex.org/works/doi:10.3390/aerospace12030195)

**Song, Aouf, Rondao, Honvault, Mansilla, "Explainable Convolutional Networks for Crater Detection and Lunar Landing Navigation", arXiv 2408.13587 (Aug 2024). ABSTRACT-ONLY.**
- **Method:** Attention-YOLOv3 crater detection plus an Attention-Darknet53-LSTM that estimates pose end-to-end from image sequences — [arXiv](https://arxiv.org/abs/2408.13587)
- **Claim:** The abstract reports only "competitive performance". It gives no numbers, dataset or baselines — [arXiv](https://arxiv.org/abs/2408.13587)

**Luo et al., "Learning to Anchor Visual Odometry: KAN-Based Pose Regression for Planetary Landing" (KANLoc), arXiv 2602.06968 (comments say accepted to RA-L). ABSTRACT-ONLY.**
- **Method:** A Kolmogorov-Arnold Network regresses image features to map coordinates. The resulting sparse global anchors are fused into bundle adjustment — [arXiv](https://arxiv.org/abs/2602.06968)
- **Claim:** Average translation error falls 32% and rotation error 45% relative to unnamed "strong baselines", at ≥15 FPS. The abstract says it uses "synthetic and real lunar landing datasets" but does not name them — [arXiv](https://arxiv.org/abs/2602.06968)

**Pisanti, Hewitt, Brockers, Georgakis (JPL-associated authors), "Geometry-aided Vision-based Localization of Future Mars Helicopters in Challenging Illumination Conditions" (Geo-LoFTR), arXiv 2502.09795 (v3 Apr 2026). ABSTRACT-ONLY.**
- **Method:** A LoFTR-style transformer matcher that uses DEM geometry to register onboard images to ortho maps. It is the closest published analogue to learned image-to-DEM registration — [arXiv](https://arxiv.org/abs/2502.09795)
- **Setting:** Images are rendered from real orbital maps across a simulated Martian day; "real Mars imagery" is also mentioned. No numbers appear in the abstract — [arXiv](https://arxiv.org/abs/2502.09795)

**La et al., "LROC-PANGU-GAN: Closing the Simulation Gap in Learning Crater Segmentation", ASTRA 2023, arXiv 2310.02781. ABSTRACT-ONLY.**
- **Method:** A CycleGAN translates PANGU renders toward the LROC image style. Adding the translated images to training improved crater segmentation on real LROC test images. The abstract gives no figures — [arXiv](https://arxiv.org/abs/2310.02781)

**Seminal baselines (pre-2023, cited for context only).**
- **LunaNet (Downes, Steiner, How, AIAA SciTech 2020):** CNN crater detection matched to known craters for landing TRN — [AIAA ARC](https://arc.aiaa.org/doi/abs/10.2514/6.2020-1838); [arXiv 2007.07702](https://arxiv.org/pdf/2007.07702). ABSTRACT-ONLY.
- **Christian, Derksen, Watkins, "Lunar Crater Identification in Digital Images", J. Astronaut. Sci. 2021:** Projective invariants exist for conics on a nondegenerate quadric such as a sphere or ellipsoid, but not for conics on an arbitrary body — [Springer DOI 10.1007/s40295-021-00287-8](https://link.springer.com/10.1007/s40295-021-00287-8); [author PDF](https://hderksen.sites.northeastern.edu/files/2023/08/Lunar.pdf). ABSTRACT-ONLY. I found no 2023-2026 Christian JSR crater paper.
- **LunarNav (arXiv 2301.01350):** Crater-based localization for rovers, not landers. It uses particle-filter matching weighted by crater IoU — [arXiv](https://arxiv.org/html/2301.01350). ABSTRACT-ONLY.

**Benchmarks and surveys.**
- A 2026 survey (Aerospace 13(10):929) says LightGlue and XFeat show value in specific lunar conditions but do not establish uniform superiority across terrain and lighting. It also says a controlled cross-descriptor lunar benchmark is missing — [DOI 10.3390/aerospace13100929](https://doi.org/10.3390/aerospace13100929). UNVERIFIED (search snippet).
- arXiv 2610.30774 (2026) benchmarks 11 classical and learned detector-matcher combinations on synthetic, testbed and terrestrial-analogue data — [arXiv](https://arxiv.org/abs/2610.30774). UNVERIFIED (title/snippet only).
- A Chinese Journal of Aeronautics 2026 paper describes a two-stage offline-online polar-landing framework using masked NCC landmark matching. This is classical, not learned — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1000936126000865). UNVERIFIED (snippet only).

**Flight reference point (classical).**
- **Mars 2020 LVS:** The requirement was to land within 60 m of target. Post-landing imagery puts Perseverance about 5 m from the targeted location — [NTRS 20230007014](https://ntrs.nasa.gov/citations/20230007014). UNVERIFIED (search snippet of the NTRS record).
- **Cheng, Ansar, Johnson (Earth and Space Science, 2021):** The LVS executed TRN "flawlessly" against an onboard map built from CTX/HiRISE products — [DOAJ](https://doaj.org/article/16ac3ff5095c4aebad1328eafc29cc57); [JPL TRN page](https://robotics.jpl.nasa.gov/what-we-do/flight-projects/mars-2020-rover/terrain-relative-navigation). UNVERIFIED (snippet).

### Inferences
- Learned crater TRN is consistently evaluated on renders built from the same LROC/LOLA products used for the catalog or map. This makes the "map" and the "truth" share error, so it is systematically optimistic about map-tie error (inference).
- The evidence is weak on comparability. No two of the 2024-2026 learned lunar papers above share a test set or report against the same baseline (inference from abstracts and full text).
- The only flight-validated map-relative localization (Mars 2020 LVS) is classical feature/template matching. A learned method would need to beat that class of baseline to claim progress.

### Gaps
- I could not retrieve full text for STELLA, Andolfo 2025, KANLoc, Geo-LoFTR or LROC-PANGU-GAN, so their sample sizes and baselines are unverified.
- I found no 2023-2026 learned lunar TRN paper evaluated on real descent imagery: not SLIM, Chang'e, IM-1/IM-2 or Blue Ghost data.
- I did not verify whether JAXA SLIM published flight TRN performance numbers.

## Q2. Lidar-to-DEM registration under map uncertainty (Choe & Park; sliding grid; NeuroGrid)

### Takeaway
Choe & Park (TAES 2024) is the closest published work to "lidar TRN against a sparse/coarse DEM". It handles the resolution mismatch with an EnKF plus a fractal terrain model, and reports about 10 m (1σ) with a 60 m map, from simulation plus a scaled-down experiment. I could not find the ION ITM 2022 Choe et al. paper the brief cites. Neither Şanlan et al. (sliding grid) nor Michaelson/Wang/Zanetti (NeuroGrid) model map error at all. Both generate measurements from the same DEM used onboard. In NeuroGrid, the "measurement rejection" and "online covariance" are hand-crafted heuristics, not learned.

### Cited Findings
**Choe & Park, "LiDAR-Inertial-Based Absolute Positioning With Sparse DEM for Accurate Lunar Landing", IEEE TAES 60(3):3482-3495, 2024, DOI 10.1109/TAES.2024.3363678. ABSTRACT-ONLY (OpenAlex/indexer).**
- **Metadata:** Authors are Yeongkwon Choe (Kangwon National Univ.) and Chan Gook Park (Seoul National Univ.); published 8 Feb 2024 — [OpenAlex](https://api.openalex.org/works/doi:10.1109/TAES.2024.3363678)
- **Problem and method:** During approach, the onboard lidar resolves fine terrain detail while orbital maps are sparse, which makes absolute matching ambiguous. The authors use an EnKF to handle the ambiguity, a fractal terrain model for unresolved sub-grid detail, and a two-step filtering framework — [OpenAlex](https://api.openalex.org/works/doi:10.1109/TAES.2024.3363678); [Bohrium abstract mirror](https://www.bohrium.com/paper-details/lidar-inertial-based-absolute-positioning-with-sparse-dem-for-accurate-lunar-landing/977543077256232982-2511)
- **Result:** About 10 m (1σ) absolute position error using a 60 m resolution map, from "numerical simulations and a scaled-down experiment". I could not see the experiment's scale, terrain source, run count or baselines — [OpenAlex](https://api.openalex.org/works/doi:10.1109/TAES.2024.3363678)
- **"Map uncertainty" framing:** The abstract treats map uncertainty as a resolution/sparsity mismatch, modelled by fractal terrain. I saw no evidence that it treats map georeferencing bias. UNVERIFIED either way without full text.

**Choe et al., ION ITM 2022.** I found no record of this paper in four separate searches (web, OpenAlex, dblp-adjacent results). UNVERIFIED and possibly mis-cited. Related verified-metadata Choe TRN papers:
- Choe & Park, "Point-Mass Filtering With Boundary Flow and Its Application to Terrain Referenced Navigation", IEEE TAES 57(6):3600-3613, 2021 — [dblp](https://dblp.dagstuhl.de/pid/267/6509.html). ABSTRACT-ONLY.
- Choe, Song, Park, "Lightweight Marginalized Particle Filtering With Enhanced Consistency for Terrain Referenced Navigation", IEEE TAES 58(3):2493-2504, 2022 — [dblp](https://dblp.dagstuhl.de/pid/267/6509.html). ABSTRACT-ONLY.
- Choe, Jung, Park, "Ensemble Kalman Filter Based LiDAR Odometry for Skewed Point Clouds Using Scan Slicing", ICRA 2022. This is odometry, not TRN — [dblp](https://dblp.dagstuhl.de/pid/267/6509.html).

**Şanlan, Erol, Abu-Khalaf, Koyuncu, "Terrain-Aided Navigation Without Raycasting: A Sliding Grid Approach for Point Cloud Processing", arXiv 2510.06470 (v1 Oct 2025, v2 Oct 2026). VERIFIED-FULLTEXT (HTML). NARROW-SIM.**
- **Method:** A marginalized particle filter (500 particles) on INS error states. The sliding-grid measurement model replaces ray-casting with an orthogonal DEM lookup — [arXiv HTML](https://arxiv.org/html/2510.06470)
- **Setting:** Simulation only, over a Bosphorus-strait DTED DEM. Measured point clouds are emulated by ray-casting the same DEM, so there is no map error. There are four scenarios (high and low altitude, 30° and 60° bank), with no Monte Carlo count stated. This is an aircraft setting, not lunar — [arXiv HTML](https://arxiv.org/html/2510.06470)
- **RMSE x/y/z:**

  | Scenario | Raycasting (m) | Sliding grid (m) |
  |---|---|---|
  | High altitude | 2.45 / 1.91 / 0.15 | 2.44 / 2.73 / 0.21 |
  | Low altitude | 8.96 / 11.44 / 4.47 | 25.12 / 17.77 / 5.99 |

  At low altitude the sliding grid is about 2-3x worse horizontally. "Orders of magnitude faster" appears only in a figure, with no timings in the text — [arXiv HTML](https://arxiv.org/html/2510.06470)
- **Stated weakness:** Prolonged occlusion "would likely cause" the filter to diverge — [arXiv HTML](https://arxiv.org/html/2510.06470)

**Michaelson, Wang, Zanetti, "Terrain-Relative Navigation with Neuro-Inspired Elevation Encoding".**
- **Venues:** PLANS 2023, pp. 851-857, DOI 10.1109/PLANS53410.2023.10139925; VERIFIED-FULLTEXT via the [UT NEAR lab PDF](https://sites.utexas.edu/near/files/2023/06/Terrain_Relative_Navigation_with_Neuro_Inspired_Elevation_Encoding.pdf). Journal version in IEEE TAES 60(3):3368-3378, 2024, DOI 10.1109/TAES.2024.3362760; ABSTRACT-ONLY via a [library catalog record](https://ersearch2.cvtisr.sk/vufind/SummonRecord/FETCH-LOGICAL-c316t-890b76e9c8defb5f828153da340a0966a04fc67a18fa104c40258b6325d6453c3). The journal abstract matches the PLANS abstract; I could not see its results.
- **Method:** NeuroGrid (grid-cell-inspired phase encoding of elevation contours) produces a global (x, y) "winner-take-all" position fix from lidar elevations, which feeds an EKF — [NEAR PDF](https://sites.utexas.edu/near/files/2023/06/Terrain_Relative_Navigation_with_Neuro_Inspired_Elevation_Encoding.pdf)
- **Measurement rejection (hand-set rule):** A grid's phase-candidate sum is accepted only if max(S) − mean(S) > P/10, where P is the number of elevation points — [NEAR PDF](https://sites.utexas.edu/near/files/2023/06/Terrain_Relative_Navigation_with_Neuro_Inspired_Elevation_Encoding.pdf)
- **Online covariance (heuristic):** Step down from the argmax of the grid-sum image until the value drops below c·max. Then σ = n·pixel size and R = σ²I — [NEAR PDF](https://sites.utexas.edu/near/files/2023/06/Terrain_Relative_Navigation_with_Neuro_Inspired_Elevation_Encoding.pdf)
- **Setting (NARROW-SIM, not lunar):** A simulated circular flight (radius 100 m, altitude 350 m, 60 s per lap) over a 400 × 400 m UT Austin campus DEM at 0.25 m/px. There are 50 Monte Carlo runs, P = 150 points per scan, and the same DEM is used for both measurements and map — [NEAR PDF](https://sites.utexas.edu/near/files/2023/06/Terrain_Relative_Navigation_with_Neuro_Inspired_Elevation_Encoding.pdf)
- **Mean position RMSE:** 1.438 m with rejection off; 0.788 / 0.681 / 0.680 / 0.718 m with rejection on at c = 0.995 / 0.999 / 0.9995 / 0.9999. On average 24.4 of 50 grids were rejected. The filter is reported as consistent and slightly conservative. The memory saving over storing the DEM is only about 30% (3.5 MB vs 5.1 MB) — [NEAR PDF](https://sites.utexas.edu/near/files/2023/06/Terrain_Relative_Navigation_with_Neuro_Inspired_Elevation_Encoding.pdf)

**Agency lidar context.** The NASA "Terrain Sensing Lidar" (MSS 2025) document exists — [NTRS PDF](https://ntrs.nasa.gov/api/citations/20250002825/downloads/MSS%202025_Terrain%20Sensing%20Lidar.pdf). UNVERIFIED (not read).

### Inferences
- None of the three verified lidar/DEM papers tests a map with a georeferencing offset or production-style DEM error. NeuroGrid and the sliding grid both use the same DEM for truth and map. So "robust to map error" claims cannot be supported by this literature, and a study that injects map-tie bias would be testing something genuinely untested (inference).
- NeuroGrid's peak-sharpness covariance and peak-contrast rejection are the closest prior art to a confidence-weighted TRN fix. They are fixed heuristics, not learned.

### Gaps
- I did not see the Choe & Park 2024 full text: scaled experiment details, Monte Carlo counts and baselines are unknown.
- I could not locate the Choe et al. ION ITM 2022 paper.
- I did not see the NeuroGrid TAES 2024 results; they may include longer trajectories.
- I did not read any recent ICP/NDT lunar lidar TRN papers (2023-2026) in full.

## Q3. Ambiguity and multimodal localization: PMF, particle filters, TERCOM/SITAN lineage

### Takeaway
The TAN community treats terrain ambiguity with global (grid/point-mass or particle) Bayesian filters rather than gated EKFs. Recent work, mainly from Matoušek/Duník (UWB) and Zanetti (UT Austin), makes point-mass filters tractable in higher dimensions, with open code and a real TAN dataset. On that real dataset, grid filters and a bootstrap PF reach about 14-15 m while a UKF fails at about 291 m. This is direct evidence that unimodal filters break on ambiguous terrain.

### Cited Findings
**Matoušek, Krejčí, Duník, Zanetti, "Tensor Decompositions for Online Grid-Based Terrain-Aided Navigation", arXiv 2601.07728 (under review, FUSION 2026). VERIFIED-FULLTEXT (UT NEAR manuscript PDF).**
- **Method:** A Lagrangian grid-based filter with CPD tensor decomposition that scales linearly with state dimension. Evaluation uses the public repo's real TAN dataset — [NEAR manuscript](https://sites.utexas.edu/near/wp-content/uploads/sites/6030/2026/05/manuscript.pdf); [arXiv](https://arxiv.org/html/2601.07728); code at github.com/pesslovany/Matlab-LagrangianPMF
- **Table I (position RMSE, velocity RMSE, time per step on a MacBook Air M1):**

  | Filter | Position (m) | Velocity (m/s) | Time per step (s) |
  |---|---|---|---|
  | LGbF | 15.23 | 0.76 | 3.88 |
  | SpectLGbF | 17.00 | 0.84 | 0.97 |
  | Bootstrap PF | 14.76 | 0.82 | 0.68 |
  | UKF | 290.97 | 4.78 | 0.0008 |
  | LGbF-CPD (proposed) | 14.13 | 0.80 | 0.06 |

  — [NEAR manuscript](https://sites.utexas.edu/near/wp-content/uploads/sites/6030/2026/05/manuscript.pdf)
- **Caveats:** A Rao-Blackwellised PF was excluded as "unstable" for this setup. The authors also warn of stability issues and negative weights under other rank settings — [NEAR manuscript](https://sites.utexas.edu/near/wp-content/uploads/sites/6030/2026/05/manuscript.pdf)

**Other grid and particle filter work.**
- **Efficient PMF (FUSION 2023):** Matoušek, Duník, Brandner, "Design of Efficient Point-Mass Filter with Application in Terrain Aided Navigation", arXiv 2303.05100. It claims a ">99.9%" time-complexity reduction "without compromising accuracy", with MATLAB code — [arXiv](https://arxiv.org/abs/2303.05100). ABSTRACT-ONLY.
- **Tutorial (2025):** Matoušek, Duník, Straka, "Lagrangian Grid-Based Filters With Application to Terrain-Aided Navigation", IEEE Signal Processing Magazine column. It claims deterministic results with improved resilience to initialisation error and measurement outliers versus PFs — [UWB repository](https://dspace.zcu.cz/items/0b9ab541-1d83-41a0-88eb-1a5023b77530/full). ABSTRACT-ONLY.
- **Dense-plus-sparse grid (ICASSP 2020, baseline-defining):** Duník, Straka, Matoušek, "Conditional Density Driven Grid Design in Point-Mass Filter" — [ZCU](https://dspace5.zcu.cz/handle/11025/42245?locale=en). ABSTRACT-ONLY.
- **Choe & Park TAES 2021 (PMF with boundary flow) and TAES 2022 (marginalized PF for TRN):** See Q2 — [dblp](https://dblp.dagstuhl.de/pid/267/6509.html). ABSTRACT-ONLY.
- **Contours-seeking PF (2026):** "Contours-Seeking Proposal Density Particle Filter and Resilient Terrain-Referenced Navigation", arXiv 2608.15489. The snippet says it treats INS drift as unknown bias and notes that multimodal radar-altimeter measurements destabilise estimation — [arXiv PDF](https://arxiv.org/pdf/2608.15489). UNVERIFIED.
- **Sliding grid (2025):** Şanlan et al. use a marginalized PF (see Q2) — [arXiv HTML](https://arxiv.org/html/2510.06470). VERIFIED-FULLTEXT.

### Inferences
- In the TAN literature, ambiguity is handled by global multimodal filters (PMF, PF, filter banks). Learned trust or gating layers on top of a unimodal EKF are not the standard. Any proposal that gates TRN fixes in an EKF should benchmark against a PMF or PF on the same ambiguous terrain (inference).
- The UWB/UT real-data TAN repo is a reusable public baseline (inference from the paper's description).

### Gaps
- I did not retrieve primary TERCOM/SITAN sources. SITAN versus batch (TERCOM-style) processing is only mentioned in the NeuroGrid PDF's background section — [NEAR PDF](https://sites.utexas.edu/near/files/2023/06/Terrain_Relative_Navigation_with_Neuro_Inspired_Elevation_Encoding.pdf).
- I found no lunar-specific multi-hypothesis tracking (MHT) TRN paper for 2023-2026.

## Q4. Map error and map bias estimation (DEM georeferencing offset, map tie, stochastic/uncertainty-aware DEMs)

### Takeaway
Estimating a DEM bias jointly with vehicle state is established in underwater TAN, through tidal-depth or altitude bias states added to PMF/RBPF filters. I found no 2023-2026 lunar landing paper that estimates a horizontal DEM georeferencing (map-tie) offset jointly with the state. Sheppard/Reale/Skinner (arXiv 2512.12058) is about terrain-height uncertainty for hazard/safety. It does not estimate georeferencing bias and is not used in navigation.

### Cited Findings
**Sheppard, Reale, Skinner, "A Stochastic Approach to Terrain Maps for Safe Lunar Landing", arXiv 2512.12058 (Dec 2025; abstract says accepted to IEEE Aerospace 2026). VERIFIED-FULLTEXT (v1 HTML).**
- **Method:** A two-stage GP. A noise GP (RBF kernel) is fitted to log height-error variance from Ames Stereo Pipeline shape-from-shading uncertainty, then frozen. It sets per-point heteroscedastic noise in a terrain GP (RQ kernel). There are exact and SVGP variants (1024 inducing points) — [arXiv HTML](https://arxiv.org/html/2512.12058v1)
- **Data:** The abstract says "LRO DEM confidence maps", but the paper's actual noise source is the ASP SfS error map. Inputs are LROC NAC stereo DEMs at about 1.3 m/px (NAC IDs M104318871, M104311715) and LuNaSynth synthetic data; 961 ASP tiles and 500 LuNaSynth tiles. LOLA appears only as a possible prior — [arXiv HTML](https://arxiv.org/html/2512.12058v1)
- **Baselines:** Tomita (exact GP), Hayner (exact GP), Torroba (SVGP). Metrics are RMSE, NLPD and AUSE, with no variance across runs and no significance tests — [arXiv HTML](https://arxiv.org/html/2512.12058v1)
- **NAC results (RMSE / NLPD / AUSE):** Ours-Exact 0.0976 / -2.642 / 0.0395 vs Tomita 0.0999 / -2.301 / 0.0410. Ours-Variational 0.1472 / -2.217 / 0.0652 is worse than the exact baselines. The large LuNaSynth gains (RMSE 0.0009 vs 0.024) come on synthetic data whose noise model matches the method's assumption — [arXiv HTML](https://arxiv.org/html/2512.12058v1)
- **Scope:** No georeferencing or map-registration bias estimation and no use in TRN. Hazard detection and trajectory optimisation are listed as future work — [arXiv HTML](https://arxiv.org/html/2512.12058v1)
- **Conflicting claim:** An aggregator summary attributes a "32% improvement in obstacle identification confidence in south-polar regions" to this paper — [newx.sg](https://www.newx.sg/paper/detail/2d2f3b76-f824-11f0-b84c-00163e10baa7). I did not see this number in the v1 HTML I read. UNVERIFIED; it may come from a later version or the IEEE Aerospace text.

**Related stochastic mapping.** Real-time stochastic terrain mapping for safe landing, arXiv 2409.09309 — [arXiv HTML](https://arxiv.org/html/2409.09309v2). UNVERIFIED (title only; likely the Hayner et al. GP baseline above).

**Joint bias estimation in TAN (underwater/aircraft).**
- **Tidal depth bias:** A marginalized point-mass filter estimates tidal depth bias as a Kalman state alongside a 2D PMF for horizontal position (J. Sensors, 2019) — [catalog record](https://vufind-test.katalog.k.utb.cz/SummonRecord/FETCH-LOGICAL-c427t-d95d1b7e048915969c97accc690c0b04510ef25bbd8cdba905ae85e2c6e4bd0b3). ABSTRACT-ONLY.
- **Altitude bias in an RBPF:** Altitude bias corrupts particle likelihoods, so a 1D KF compensates (Sensors 18(9):2886, 2018) — [MDPI PDF](https://res.mdpi.com/d_attachment/sensors/sensors-18-02886/article_deploy/sensors-18-02886-v2.pdf). ABSTRACT-ONLY.
- **Filter bank:** A bank of filters weighted by residuals recovers an altitude bias without a 3D grid search (ACC 2015, DOI 10.1109/ACC.2015.7171002) — [record](https://manuscript.isc.ac/Inventory/49/728209.htm). ABSTRACT-ONLY.
- **Thesis:** Bias estimation for terrain-aided tracking (McMaster PhD, 2022) — [thesis PDF](https://macsphere.mcmaster.ca/bitstream/11375/27799/2/schonborn_david_082022_phd.pdf). ABSTRACT-ONLY.

**Agency map products.** Mars 2020 TRN used dedicated USGS orthorectified CTX mosaics and DTMs built for onboard maps — [USGS](https://www.usgs.gov/data/mars-2020-terrain-relative-navigation-context-camera-orthorectified-image-mosaic); [USGS Astrogeology](https://astrogeology.usgs.gov/search/map/mars_2020_terrain_relative_navigation_ctx_dtm_mosaic). ABSTRACT-ONLY. Cheng/Ansar/Johnson 2021 describe validating the LVS map on 18 Feb 2021 — [DOAJ](https://doaj.org/article/16ac3ff5095c4aebad1328eafc29cc57). UNVERIFIED (snippet).

### Inferences
- The underwater TAN technique (bias state plus PMF/RBPF) is the closest template for estimating a lunar DEM vertical bias. For a horizontal map-tie offset, the bias is unobservable from a single fix and must be separated through vehicle dynamics or multiple fixes. I found no lunar paper that analyses this (inference).
- The Sheppard et al. uncertainty maps could plausibly feed a TRN measurement covariance, but that has not been published (inference).

### Gaps
- I could not access a primary source quantifying LOLA/LROC georeferencing (map-tie) errors at south-pole sites.
- I did not verify NASA's LuNaMaps or other agency uncertainty-aware lunar DEM work.

## Q5. Learned or adaptive measurement gating/trust (learned gain, learned covariance, learned outlier rejection); flight anomalies relevant to gating

### Takeaway
Learning the Kalman gain (KalmanNet and its many variants) and learning measurement noise covariance from data (DNN-adaptive KFs) are well published. "Learning a correction gain" is therefore not novel by itself. I found no published work that learns a trust/gain for TRN fixes specifically, or a learned TRN innovation gate. The ispace HAKUTO-R M1 crash (2023) is a flight-data case in which a fixed residual-rejection filter rejected valid altitude measurements over unexpected terrain. That is direct motivation for terrain-aware trust logic.

### Cited Findings
**Learned Kalman gain.**
- **KalmanNet:** Revach, Shlezinger, Ni, Lopez Escoriza, van Sloun, Eldar, IEEE Transactions on Signal Processing, 2022 (arXiv 2107.10043). It embeds an RNN "in the flow of the KF" and claims to outperform classical filters under mismatch and non-linearity — [arXiv](https://arxiv.org/abs/2107.10043). ABSTRACT-ONLY.
- **Variants:** Split-KalmanNet learns prior and innovation covariances separately and forms the gain with the known measurement Jacobian. Unsupervised KalmanNet matches supervised performance without ground-truth labels — [EmergentMind topic summary](https://www.emergentmind.com/topics/kalmannet); [arXiv 2110.09005](https://www.arxiv.org/pdf/2110.09005); [EUSIPCO 2022](https://eurasip.org/Proceedings/Eusipco/Eusipco2022/pdfs/0001571.pdf). UNVERIFIED (snippet level).
- **Recent extensions:** AM-KNet (Apr 2026) adds sensor-specific modules and an NLL-supervised covariance branch on error and innovation — [arXiv 2604.02441](https://arxiv.org/html/2604.02441v1). Unscented KalmanNet (2026) targets calibrated posterior uncertainty — [arXiv 2608.04201](https://arxiv.org/pdf/2608.04201). Both UNVERIFIED (snippet).

**Learned noise covariance.**
- **Or & Klein (2022):** A DNN sets the process-noise covariance from IMU data inside an EKF — [arXiv 2207.12082](https://arxiv.org/pdf/2207.12082). ABSTRACT-ONLY.
- **ANPMN-UKF (2026):** Networks predict process and GNSS measurement noise for a UGV, trained on simulated data only — [arXiv 2603.11649](https://arxiv.org/html/2603.11649v1). UNVERIFIED (snippet).
- **DualAttNet (IEEE JSEN):** An attention network scores measurement confidence and maps it to measurement noise R for pedestrian INS — [BIT record](https://pure.bit.edu.cn/zh/publications/a-dualattnet-based-deep-adaptive-kalman-filter-in-inertial-naviga/). UNVERIFIED (snippet).
- **Non-learned baselines:** Chi-square innovation gating combined with GA-tuned R — [Soft Computing Journal](https://scj.kashanu.ac.ir/article_115169_en.html); variational robust noise adaptation (PolyU thesis 2025) — [PolyU](https://theses.lib.polyu.edu.hk/handle/200/13926?mode=full). UNVERIFIED.

**Hand-crafted TRN trust (closest to a TRN-specific gate).** NeuroGrid's peak-contrast rejection and peak-width covariance — see Q2 — [NEAR PDF](https://sites.utexas.edu/near/files/2023/06/Terrain_Relative_Navigation_with_Neuro_Inspired_Elevation_Encoding.pdf). VERIFIED-FULLTEXT.

**ispace HAKUTO-R Mission 1 (Apr 2023; findings released 26 May 2023), flight anomaly.**
- **Root cause:** A filter "designed to reject an altitude measurement having a large gap from the lander's estimation" (a hardware-fault safeguard) rejected valid altimeter data after the lander passed over a crater rim. The estimate drifted; the lander exhausted propellant and free-fell — [Engadget](https://www.engadget.com/japans-ispace-says-hakuto-r-crashed-because-it-got-confused-by-a-crater-rim-113115803.html); [Universe Today](https://universetoday.com/161661/hakuto-rs-software-got-confused-at-the-last-minute-causing-it-to-crash-into-the-moon); [SpacePolicyOnline](https://spacepolicyonline.com/?p=62380). UNVERIFIED (secondary press; the ispace primary release URL returned 404).
- **Contributing factors:** Pre-flight simulations did not adequately include the terrain on the route, and the landing site changed after CDR — [SpacePolicyOnline](https://spacepolicyonline.com/?p=62380). UNVERIFIED.
- **Source conflict on altitudes:** Some reports cite about 3 km (crater-rim height or sensor jump) and others about 5 km (the lander's altitude when the error became critical) — [Gizmodo](https://gizmodo.com/why-japan-private-lunar-lander-crashed-moon-1850479198). UNVERIFIED.

**Intuitive Machines IM-1 Odysseus (Feb 2024).** The laser rangefinders were unusable because a safety switch was not disarmed before launch. A patch to use NASA's Navigation Doppler Lidar failed because a software data flag was not set, so the lander landed on IMU plus optical navigation and tipped over at about 3 m/s with lateral motion — [The Space Review](https://thespacereview.com/article/4765/1); [New Atlas](https://newatlas.com/space/odysseus-broke-leg-landing). UNVERIFIED (press).

### Inferences
- The literature already contains learned gains (KalmanNet family) and learned R (DNN-adaptive KFs). A novelty claim for a random-forest "utility gain" on TRN fixes would have to rest on being TRN-specific: map-error-aware, terrain-feature conditioned, and evaluated against PMF/PF and chi-square gating baselines. It cannot rest on "learning a gain" (inference).
- HAKUTO-R shows that a fixed innovation gate can fail catastrophically over terrain that is real but absent from the simulation. This argues for terrain-conditioned trust and for evaluating gates on out-of-distribution terrain (inference).

### Gaps
- I found no 2023-2026 paper on learned innovation gating or learned outlier rejection specifically for TRN or TAN.
- I did not read KalmanNet's full text, so its experiment sizes are unverified here.
- The ispace primary release was not retrieved (404).

## Q6. Hazard detection and avoidance (HDA) relevant to the lunar south pole

### Takeaway
South-pole HDA work in 2024-2026 is mostly agency and industry sensor development with helicopter or VTVL field tests (NASA Goddard SPLICE HD lidar, Astrobotic HD Lidar on Xodiac), plus simulation frameworks built from DEMs. Peer-reviewed quantitative south-pole HDA performance from flight is scarce.

### Cited Findings
- **NASA Goddard SPLICE (SciTech 2026 paper):** Covers lidar motion compensation for hazard scanning and divert-site selection in a south-pole landing concept of operations. The HD lidar was helicopter-tested over several days in March 2025 — [NTRS PDF](https://ntrs.nasa.gov/api/citations/20250010237/downloads/MAIN_SPLICE_MotionComp_SciTech_2026.pdf). UNVERIFIED (snippet; not read).
- **Astrobotic HD Lidar:** An engineering model flew on a Xodiac vehicle on 11 Nov 2024 and produced terrain hazard maps from point clouds in flight. NASA's Flight Opportunities page frames it as going to the Moon — [NASA](https://www.nasa.gov/stmd-flight-opportunities/transitions-of-flight-tested-technologies/hazard-detection-lidar-system-goes-to-the-moon/). UNVERIFIED (snippet).
- **Lunar surface navigation survey (AAS GNC 2025, NASA):** [NTRS PDF](https://ntrs.nasa.gov/api/citations/20250000720/downloads/Lunar_Surface_Nav_Survey_AAS_GNC_011825.pdf). UNVERIFIED (not read).
- **Unreal Engine south-pole HDA framework:** Ostrogovich et al., MetroAeroSpace 2025 — [IRIS UNINA](https://iris.unina.it/handle/11588/1028216). UNVERIFIED.
- **Uncertainty-aware maps for safe landing:** Sheppard et al. 2025 (see Q4) is framed for south-pole hazard and site selection but does not yet run HDA — [arXiv HTML](https://arxiv.org/html/2512.12058v1). VERIFIED-FULLTEXT.
- **Rover lidar field test:** Two Ouster lidars used for mapping and hazard detection under simulated south-pole lighting. This is a rover, not a lander — [arXiv 2601.03371](https://arxiv.org/pdf/2601.03371). UNVERIFIED.
- **Pre-window reference:** The ESA Lunar Lander phase B1 HDA (NGC Aerospace, IAC 2013) used lidar for slope and roughness and a camera for shadow and texture — [IAF](https://iafastro.directory/iac/archive/browse/IAC-13/A3/P/18356/). UNVERIFIED.

### Inferences
- South-pole HDA evidence is at the field-test tier for sensors and the simulation tier for algorithms. Low Sun angles and long shadows make camera-only HDA and TRN especially exposed to sim-to-real gaps (inference consistent with the shadow emphasis in the sources above).

### Gaps
- I did not read the SPLICE, Astrobotic or Ostrogovich full texts, so their quantitative hazard-detection metrics (detection rates, safe-site success) are not captured.
- I did not verify any 2024-2026 commercial lunar landing flight's HDA performance (IM-2, Blue Ghost M1, ispace M2).
