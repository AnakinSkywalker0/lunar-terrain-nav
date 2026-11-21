# Flight TRN evidence narrows LANTERN's defensible claim

**What LANTERN gets right:** it treats terrain-relative navigation (TRN) as map-relative and studies how a terrain fix should be trusted. That is how real systems work, and it is where recent landings have failed. **What does not hold up:** several of its headline results come from the experiment design, not from the policies tested. Mars 2020's Lander Vision System (LVS), ALHAT/Morpheus and SPLICE all estimate position *in the frame of their onboard map*. They put map-tie error in a separate budget and support their flight claims with one to a few flights plus Monte Carlo and field tests. The lunar landings of 2023–2025 failed mostly in the *altitude channel*, and the matcher was rarely the cause. HAKUTO-R M1 rejected a good rangefinder. IM-1 flew with its laser altimeter disabled and could not ingest a working Doppler lidar. IM-2 accepted a noisy altimeter under low-Sun lighting. Most 2023–2026 learned-TRN and lidar-to-DEM papers are simulations in which the "truth" and the onboard map come from the same product. None of the papers verified here estimates a horizontal map-tie offset, and NASA's TRN fault detector (PITFAL) publishes no detection statistics. Against this background, LANTERN's shifted-map 0/N result is guaranteed by construction. Its 36–47 m shifts and 8–20 m bumps are gross stress cases, roughly 200–400× and 16–65× the errors Barker et al. report for the PGDA DEMs LANTERN uses. Its 10 m miss criterion is 5–10× stricter than NASA's 100 m (Artemis III) and 50 m (Artemis IV+) requirements. The defensible contribution is narrower than "lunar sensor trust": a closed-loop study of how TRN correction gating affects touchdown velocity, tested against realistic, product-derived map errors and classical baselines, with fault-detection statistics that the NASA work does not report.

*Synthesis date: 29 October 2026. Inputs: five research notes in `research_notes/Lunar TRN literature verification/`, the 25 October readiness audit and its notes, and `docs/RESEARCH_NOVELTY_REVIEW.md` and `docs/MAP_EFFICIENCY_RECHECK.md`. Where these disagree, the 29 October notes win.*

**Evidence labels used throughout.** **[VF]** means the researchers read the full text, or the full relevant section, themselves. **[VF-slides]** means presentation slides were read in full. **[AO]** means only an abstract, NTRS record or indexer metadata was read. **[WEB]** means an official agency web page was read (a primary source, but a summary). **[SEC]** means reputable secondary reporting that attributes the claim to an official source. **[UNV]** means a search snippet, an aggregator, or a source that could not be located. **[REPO]** means read in this repository. **[LOCAL]** means measured from local data files. **[COMP]** means arithmetic done in the notes or here, not a measured result.

## Flight TRN systems navigate in map frame on very small flight samples

### Mars 2020 LVS shows map-relative design working, on one landing

LVS is the only flight-proven map-relative localization system in this review, and it is classical rather than learned. It worked in two stages:

- **Coarse stage.** FFT correlation of 15 landmarks across 3 images (128×128 templates) fed a batch estimator.
- **Fine stage.** Spatial correlation of up to 150 landmarks per image fed an EKF propagated by the IMU, with outlier rejection inside each stage.

Its specification was to remove a 3.2 km initial error and reach **40 m at the 99th percentile within 10 s** ([Johnson, LSIC slides 2021](https://lsic.jhuapl.edu/uploadedDocs/presentations/764-1.09_Johnson_20210302_LuNaMaps_LVS_v0.pdf) [VF-slides]). The sources disagree on two details. The fine-stage template size is 21×21 on the CDR-era slides but 15×15 on JPL's page. The map source is HiRISE on JPL's page but CTX in USGS and Cheng et al. ([JPL Robotics](https://www-robotics.jpl.nasa.gov/what-we-do/flight-projects/mars-2020-rover/terrain-relative-navigation/) [WEB]).

The design point that matters for LANTERN is how the maps were tied together. The hazard map was **registered to the CTX LVS map, not independently to the Mars frame**, using a single affine fit (94.1% of matched features within 6 m) ([USGS HiRISE mosaic](https://astrogeology.usgs.gov/search/map/Mars/Mars2020/JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first) [WEB]). Reference-map error sat inside the "targeting error" term of the 60 m budget ([Chen et al., NTRS 20230007014](https://ntrs.nasa.gov/citations/20230007014) [AO]). A rigid global offset of the CTX map therefore largely cancels, because target and estimate share one frame.

In flight, Perseverance landed **about 5 m from the selected target against a 60 m requirement**. The pre-landing prediction was 33 m ([NTRS 20230007014](https://ntrs.nasa.gov/citations/20230007014) [AO]; [LVS flight performance, NTRS 20230006986](https://ntrs.nasa.gov/citations/20230006986) [AO]). That is **n = 1**. The statistical evidence behind it comes from elsewhere:

- more than 600 real-time field-test runs on engineering-model hardware ([NTRS 20220000862](https://ntrs.nasa.gov/citations/20220000862) [AO]);
- "thousands" of Monte Carlo runs ([NASA Science](https://science.nasa.gov/science-research/science-enabling-technology/technology-highlights/terrain-relative-navigation-landing-between-the-hazards/) [WEB]);
- two December 2014 Masten **Xombie** free flights ([Trawny et al., NTRS 20170008233](https://ntrs.nasa.gov/citations/20170008233) [AO]);
- a 2014 **helicopter** field test that gave 40 m (3σ) in 10 s ([Johnson et al., NTRS 20160009627](https://ntrs.nasa.gov/citations/20160009627) [AO]).

Search summaries often merge the helicopter test with the rocket flights. The **2017** COBALT flights and the **September 2019** SPLICE/Draper flight were the ones on Xodiac ([NTRS 20210006132](https://ntrs.nasa.gov/citations/20210006132) [AO, title only]; [NASA SPLICE](https://www.nasa.gov/safe-and-precise-landing-integrated-capabilities-evolution-splice/) [WEB]).

**Unresolved citation detail.** The notes attribute the LVS flight-performance paper (NTRS 20230006986) to "Zheng et al." in one place and to "Montgomery/Johnson et al." in another. Check the record before citing it.

### ALHAT/Morpheus showed hazard detection working, while hazard-relative navigation was the weak link

**What flew.** ALHAT flew a flash-lidar Hazard Detection System, a Navigation Doppler Lidar (NDL) and a laser altimeter on Morpheus over the KSC hazard field. Global TRN was demonstrated earlier on a 2009 fixed-wing aircraft campaign, not on Morpheus ([Epp et al., NTRS 20140010334](https://ntrs.nasa.gov/api/citations/20140010334/downloads/20140010334.pdf) [VF]).

**How few runs.** Only **three flights (FF13–FF15) were closed-loop** on ALHAT navigation, and only one of them had working hazard-relative navigation (HRN):

- On closed-loop flights, HRN produced only 1–2 usable measurements out of 8–10 opportunities.
- On FF13 and FF14, HRN diverged and the vehicle fell back to its GPS-aided navigation.
- The root cause was timing. The lidar gimbal was being steered using a Kalman-filter state from before the latest update. Simulation missed it because "the modeled HDS software did not have an actual processor delay".
- After the fix, FF15 processed 7 HRN measurements and converged ([Crain et al., NTRS 20170009198](https://ntrs.nasa.gov/api/citations/20170009198/downloads/20170009198.pdf) [VF]).

**Claimed versus demonstrated.** The flash lidar is specified to detect 30 cm hazards from 1 km. In flight they were detected only from the 450 m maximum slant range Morpheus could provide. Plume-heated air and dust pre-triggering degraded the sensors ([Roback et al., NTRS 20160005928](https://ntrs.nasa.gov/api/citations/20160005928/downloads/20160005928.pdf) [VF, first pages]).

**Simulation results.** In ALHAT's 6-DOF POST2 Monte Carlo (design analysis cycle 2), the global requirement of 3σ < 90 m was met. The local requirement of 3σ < 3 m was **not** met, even with HRN ([Davis et al., NTRS 20100025998](https://ntrs.nasa.gov/api/citations/20100025998/downloads/20100025998.pdf) [VF]).

### SPLICE and PITFAL: rich simulation, thin flight evidence

**New Shepard flights.** SPLICE flew open-loop on two New Shepard flights (2020 and 2021). On both, the NDL produced no usable data because of the helium environment ([NASA TM-20250010290](https://ntrs.nasa.gov/api/citations/20250010290/downloads/NASA%20TM%2020250010290.pdf) [VF]). The analysed flight's 41-state UDU EKF ran on IMU plus TRN only. "Truth" was the launch vehicle's GPS navigation, and the results are **figures without a numeric error table** ([Fritz et al., NTRS 20210023718](https://ntrs.nasa.gov/api/citations/20210023718/downloads/AIAA_SciTech2022_TP2_NAVDQG.pdf) [VF]).

**Later status.** NASA's August 2026 page lists March 2025 helicopter tests, August 2026 drone tests and a **September 2026 project closeout**. The notes could not confirm that the closeout happened, or that the planned 2025 integrated Xogdor flight took place ([NASA SPLICE](https://www.nasa.gov/safe-and-precise-landing-integrated-capabilities-evolution-splice/) [WEB]).

**PITFAL in full text.** PITFAL (Adams et al., SciTech 2025) is the only TRN-specific integrity method verified here. It is **a 1-DOF, 99% chi-square consensus test (limit 6.635) on four NDL apparent altitudes**. Per-beam σ is set from the DEM's altitude variance. A flagged beam has its noise inflated rather than being discarded.

Its validation is substantial:

- 1000 closed-loop Monte Carlo runs at lat −89.9°;
- a 10 × 10 km patch of the PGDA 5 m/px LOLA DEM;
- 30 m initial position σ;
- runs that **stop at 30 m AGL**.

The limits are just as important. Absolute errors are withheld for export control, and **no detection, false-alarm or missed-detection rates are reported** ([Adams et al., NTRS 20240014100](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf) [VF]). In aviation terms, PITFAL is fault detection with down-weighting. It is not RAIM/ARAIM: it computes no protection levels.

**NDL itself works.** On IM-1 it ranged beyond 20 km against an expected 5 km, with no dropouts. Post-flight reconstruction agreed to about 5 m and 0.5 m/s. But the lander's filter never used it (next section).

## Lunar landings since 2023 failed mostly in the altitude channel

The lunar record is the strongest real-world motivation for sensor-trust research. It also shows that the sharpest failures came from altitude-sensor architecture, not from map-matching accuracy. The notes classify each failure as rejecting a good sensor (A), trusting bad data (B), map or appearance mismatch (C), lighting (D), no dissimilar redundancy (E), or a sensor that was never available (F).

**HAKUTO-R M1 (April 2023)** is case A. A jump-rejection filter, meant to catch hardware faults, discarded valid laser-rangefinder data as the lander crossed the Atlas crater rim. The estimated altitude reached zero while the lander was still about 5 km up, and it fell after exhausting propellant. ispace tied this to a landing-site change after CDR and to simulations that did not model the new route's terrain ([SpaceNews](https://spacenews.com/?p=159890) [SEC]; [ispace release, 26 May 2023](https://ispace-inc.com/wp-content/uploads/2023/05/EN_ispace_release_20230506_Final-Results.pdf) [SEC; 403 when fetched]). The "3 km" and "5 km" figures in reporting are different quantities: the rim step in the reading, and the accumulated estimate error. Both can be true.

**ispace M2 (June 2025)** was a hardware anomaly in a first-flight rangefinder from a new supplier. Valid data arrived too late to decelerate, and there was no dissimilar altitude sensor ([SpacePolicyOnline](https://spacepolicyonline.com/news/hardware-failure-doomed-ispaces-mission-2/) [SEC]).

**IM-1 (February 2024)** is the case that most needs correcting in the project's documents. NASA's November 2025 technical memorandum states:

- The laser altimeter "was not operational and could not provide data to the navigation filter".
- A flight-software patch to ingest NDL data "proved to be unsuccessful".
- **The vehicle "conducted its landing without the use of any NDL data"**, using IMU plus optical feature tracking only.
- Contact velocity was **7.79–7.80 m/s** total, Moon-relative ([Karlgaard et al., NASA TM-20250010290](https://ntrs.nasa.gov/citations/20250010290) [VF]).

Early press claims that NDL "saved" the landing are contradicted by this TM. Press figures of about 2.7 m/s vertical and 0.9 m/s lateral ([SpaceNews](https://spacenews.com/?p=349475) [SEC]) do not obviously reconcile with the TM's 7.8 m/s total. The notes did not resolve the vertical/horizontal split, so treat it as **unresolved**.

**IM-2 (March 2025)** was, per the CEO's account, three things combined:

- laser-altimeter interference that corrupted altitude readings;
- low-Sun polar lighting with long shadows;
- crater matching tuned to LRO imagery taken from about 100 km.

Athena ended on its side in a ~20 m crater. IM-3 will add redundant, dissimilar altimeters and a velocity sensor that does not depend on lighting ([Spaceflight Now, 14 May 2025](https://spaceflightnow.com/2025/05/14/intuitive-machines-ceo-points-to-issues-that-prevented-upright-touchdown-during-im-2-moon-landing/) [SEC]).

**The successes look different.** Chandrayaan-3 flew dissimilar Ka-band and laser altimeters plus a laser Doppler velocimeter, under a design philosophy ISRO describes as "failure-based" ([Jatan Mehta](https://jatan.space/chandrayaan-3-makes-historic-touchdown/) [SEC]; [Business Today](https://www.businesstoday.in/amp/latest/in-focus/story/indias-moon-mission-how-chandrayaan-3-is-better-than-chandrayaan-2-key-differences-explained-389556-2023-07-13) [SEC]). Chang'e-4 hovered at about 99 m and used a 3D imaging lidar for fine hazard avoidance ([Nature Communications 2019](https://dcmpx.remotevs.com/com/nature/www/SL/articles/s41467-019-12278-3.pdf) [VF]). Blue Ghost M1 landed within about 100 m on benign mare terrain ([Sky & Telescope](https://skyandtelescope.org/astronomy-blogs/astronomy-space-david-dickinson/blue-ghost-lands-on-the-moon/) [SEC]).

**SLIM (January 2024)** is the best reference for what crater-matching TRN achieves when map and lighting cooperate. JAXA evaluated navigation accuracy at "~10 m or better", with image-matching estimates of **3.4 m and 10.2 m** in two sequences at about 50 m altitude. Touchdown was about 55–60 m east of target because an engine nozzle was lost: a propulsion failure, not a navigation failure ([JAXA briefing, 26 Dec 2024](https://www.isas.jaxa.jp/en/topics/files/SLIM-press-briefing-20241226.pdf); [JAXA doc01](https://global.jaxa.jp/press/2024/01/file/jaxa_doc01_20240125_e.pdf)). The two notes label this evidence differently: VERIFIED-PRIMARY via search extraction in one, ABSTRACT-ONLY in the other. Treat it as primary but not read directly. Do not quote "3–4 m" as SLIM's landing accuracy.

**Luna-25 (2023)** is not a descent-navigation case. It crashed during an orbit-lowering burn that ran 127 s instead of 84 s, after an accelerometer unit failed to switch on ([SpaceNews](https://spacenews.com/?p=192647) [SEC]). **No lunar landing had occurred in 2026 as of late October**, so the post-2025 fixes (IM-3's dissimilar altimeters, ispace's sensor work) have no flight data yet ([The Space Review](https://www.thespacereview.com/article/5344/1) [SEC]).

The pattern sharpens what "sensor trust" should mean. Trust failures ran in both directions: over-rejection on M1, under-detection on IM-2. "Sensor never available" (IM-1, Luna-25) is a separate class, which calls for a time-to-first-valid gate and a defined fallback. Every success had either dissimilar active sensing or benign terrain and lighting. LANTERN's current Unity experiments model none of these altitude-channel failures. Its legacy Python path did model a HAKUTO-R-style cliff, but under the defects listed in the readiness audit.

## 2023–2026 research is mostly simulation against the map it was built from

### Learned TRN: no shared benchmark and no real descent imagery

Learned crater TRN is active, but the evidence is weak for comparison. Candan & Servadio (arXiv 2606.14776) was read in full. It is pure synthetic simulation along a 100 km orbit, with no IMU model and no dynamic lighting. It reduces a 5 km offset to "a few hundred meters". It also contradicts itself: 50 vs 500 Monte Carlo runs, three different association methods, and a "no altimeter" claim while its filter uses an altitude measurement ([arXiv HTML](https://arxiv.org/html/2606.14776v1) [VF]).

The other learned papers were read at abstract level only, and none reports a shared baseline on a shared test set:

- STELLA: metre-level accuracy in a mapping orbit, not landing ([arXiv 2509.20748](https://arxiv.org/abs/2509.20748) [AO]).
- Andolfo et al.: 3σ < 100 m down to about 10 km altitude in SLIM-based simulation ([DOI 10.3390/aerospace12030195](https://doi.org/10.3390/aerospace12030195) [AO]).
- KANLoc: 32% lower translation error against unnamed baselines ([arXiv 2602.06968](https://arxiv.org/abs/2602.06968) [AO]).
- Geo-LoFTR: geometry-aided image-to-map matching for Mars helicopters ([arXiv 2502.09795](https://arxiv.org/abs/2502.09795) [AO]).

**The notes found no 2023–2026 learned lunar TRN paper evaluated on real descent imagery.** Because renders and catalogs come from the same LROC/LOLA products, these papers are systematically optimistic about map-tie error. That is an inference, but a structural one.

### Lidar-to-DEM registration never tests a mis-registered map

**Choe & Park (IEEE TAES 60(3), 2024)** is the closest published analogue to LANTERN: lidar plus inertial against a sparse DEM. It uses an EnKF, a fractal model of sub-grid terrain, and two-step filtering. It reports **about 10 m (1σ) with a 60 m map** from "numerical simulations and a scaled-down experiment" ([OpenAlex](https://api.openalex.org/works/doi:10.1109/TAES.2024.3363678) [AO]). Run counts, scale and baselines are unknown. Its "map uncertainty" appears to mean resolution mismatch, not georeferencing bias, but that is unverified without the full text.

Both lidar/DEM papers that were read in full generate their measurements **from the same DEM they navigate against**, so neither tests map error:

| Paper | Setting | Measurement rejection / covariance | Key results |
|---|---|---|---|
| Şanlan et al. sliding grid ([arXiv 2510.06470](https://arxiv.org/html/2510.06470) [VF]) | Aircraft over a Bosphorus DTED DEM, four scenarios | — | At low altitude, 2–3× worse horizontally than ray-casting (25.1/17.8 m vs 9.0/11.4 m RMSE) |
| Michaelson, Wang, Zanetti, NeuroGrid ([PLANS 2023 PDF](https://sites.utexas.edu/near/files/2023/06/Terrain_Relative_Navigation_with_Neuro_Inspired_Elevation_Encoding.pdf) [VF]; TAES 2024 version [AO]) | 400 m campus DEM, 50 Monte Carlo runs | Hand-set: peak contrast max(S) − mean(S) > P/10; σ from peak width | Mean RMSE 1.438 m without rejection; 0.68–0.79 m with it |

NeuroGrid's trust logic is the closest prior art to a confidence-weighted TRN fix, and it is fixed heuristics, not learning.

### Ambiguity: grid and particle filters win where unimodal filters fail

The terrain-aided navigation (TAN) community handles terrain ambiguity with global Bayesian filters. On a **real** TAN dataset, Matoušek, Krejčí, Duník & Zanetti report:

| Filter | Position RMSE (m) | Time per step (s) |
|---|---|---|
| Proposed tensor-decomposed grid filter | 14.13 | 0.06 |
| Bootstrap particle filter | 14.76 | 0.68 |
| UKF | **290.97** | — |

([NEAR manuscript](https://sites.utexas.edu/near/wp-content/uploads/sites/6030/2026/05/manuscript.pdf) [VF]; code at github.com/pesslovany/Matlab-LagrangianPMF.) This is direct evidence that unimodal filters break on ambiguous terrain. It also makes grid filters an available, reproducible baseline for any EKF-gating proposal. The notes found no lunar-specific multi-hypothesis TRN paper for 2023–2026.

### Map-error estimation: established underwater, absent for lunar map tie

Estimating a DEM bias jointly with vehicle state is established in underwater and aircraft TAN, for example tidal-depth or altitude bias states in point-mass and Rao-Blackwellized particle filters ([Sensors 18(9):2886](https://res.mdpi.com/d_attachment/sensors/sensors-18-02886/article_deploy/sensors-18-02886-v2.pdf) [AO]). **The notes found no 2023–2026 lunar landing paper that estimates a horizontal map-tie offset jointly with the state.**

Sheppard, Reale & Skinner (arXiv 2512.12058) model terrain-height uncertainty with a two-stage GP fitted to Ames Stereo Pipeline shape-from-shading error maps on NAC DEMs. On real NAC data the exact variant beats the Tomita baseline only narrowly (RMSE 0.0976 vs 0.0999). It does **no** georeferencing estimation and is not used in navigation ([arXiv HTML](https://arxiv.org/html/2512.12058v1) [VF]). An aggregator's "32% improvement" figure for this paper did not appear in the text that was read [UNV].

### Learned gains and covariances already exist, so learning a gain is not a contribution

Learning the Kalman gain (KalmanNet; [arXiv 2107.10043](https://arxiv.org/abs/2107.10043) [AO]) and learning noise covariances (AI-IMU; [arXiv 1904.06064](https://arxiv.org/abs/1904.06064) [AO]) are well published. Innovation-based adaptive estimation dates to at least Mohamed & Schwarz 1999 ([J. Geodesy](https://link.springer.com/doi/10.1007/s001900050236) [AO]). The closest TRN-specific analogue is Acharya et al., RA-L 2025. It learns non-Gaussian, per-match uncertainty from the matching similarity surface on **real TRN data** ([arXiv 2405.20513](https://arxiv.org/abs/2405.20513) [AO]). The notes found no paper that learns a gain or innovation gate specifically for TRN fixes. That is absence of evidence from a limited search, not proof of a gap.

## LANTERN beside five reference systems

| | **LANTERN (Unity v2)** | **Mars 2020 LVS** | **ALHAT / Morpheus** | **SPLICE / PITFAL** | **Choe & Park 2024** | **JAXA SLIM** |
|---|---|---|---|---|---|---|
| Sensors | 24×24 ray "lidar" ±20°, nadir altimeter, ideal attitude, acceleration = finite-differenced true velocity + noise [REPO] | 1024² LCAM camera + DIMU IMU; NavFilter adds radar [VF-slides] | Flash lidar, NDL, laser altimeter, IMU; GPS backup string [VF] | IMU, TRN camera, 4-beam NDL, HD lidar [VF] | Lidar + IMU [AO] | Descent camera (crater matching) + IMU [SEC/primary via extraction] |
| Estimator | Exhaustive 2-D translation search; **hard state overwrite**; RF-scheduled scalar gain; no covariance [REPO] | Coarse FFT correlation → batch estimator; fine correlation → EKF; outlier rejection in both stages [VF-slides] | Dual-state inertial KF at 5 Hz; HRN via ring buffer [VF] | 41-state UDU EKF with residual editing; PITFAL χ² consensus + noise inflation [VF] | Two-step EnKF + fractal terrain model [AO] | Image matching correcting IMU propagation [SEC] |
| Map | PGDA Site04/Site01 5 m DEM resampled to an 8 m grid; truth shares the same ancestry [REPO] | CTX ortho 6 m (12/6 m stages), 20 m DTM; hazard map registered to it [WEB] | DEM built in flight over the KSC hazard field (TRN not flown) [VF] | PGDA "NPA" 5 m LOLA DEM, 10×10 km patch [VF] | 60 m sparse DEM [AO] | Prebuilt crater/terrain maps [SEC] |
| Map-error model | One Gaussian bump (8–20 m) on truth, or rigid 36–47 m shift of the prior [REPO] | Budgeted as targeting error; HiRISE–CTX affine scale fix [AO/WEB] | Map tie accepted; DEM map-tie objective < 1 m [VF] | σ_alt from DEM altitude variance [VF] | Resolution mismatch (fractal sub-grid) [AO] | Not found |
| Test type | 3-DOF PhysX simulation, 0.5–2 km starts [REPO] | Monte Carlo + helicopter + 2 Xombie flights + field test + 1 Mars landing [AO/WEB] | POST2 Monte Carlo + 6 free flights (3 closed-loop) [VF] | Closed-loop Trick/JEOD simulation ending 30 m AGL; open-loop suborbital flights [VF] | Simulation + scaled-down experiment [AO] | 1 lunar landing |
| Sample size | 54 configs/arm on 1 crop (final); 162 configs/arm on 3 crops of one DEM (transfer); seeds vary noise only [REPO] | 600+ field runs; "thousands" MC; n=1 flight [AO/WEB] | ~3 closed-loop flights, 1 with working HRN [VF] | 1000 MC runs [VF] | Unknown | n=1 |
| Accuracy | Mean miss 28.9–46.0 m; success 24/54 and 54/162 for every correcting arm; 100% aligned, 0% shifted [REPO] | 40 m (99th pct) map-relative spec; **5 m** from target vs 60 m req [AO] | Within 2 m of GPS nav at pad; ALDAC-2 global 3σ<90 m met, local 3σ<3 m not met [VF] | Inside unpublished KPP circles; absolute values withheld; goal 50 m [VF] | ~10 m (1σ) [AO] | Nav ≈10 m or better; 3.4/10.2 m fixes; touchdown ~55–60 m off (engine) |

The table shows where LANTERN stands. It is the **only** entry whose map-error model includes a deliberate map perturbation. It is also the one with the least realistic sensing, the simplest estimator, and the fewest independent terrain units.

## What is consistent, and what is an artifact of the design

### Consistent with practice

LANTERN's exhaustive translation search with a mean-removed squared-residual cost is a reasonable, classic correlation-TRN design. Its 5 m PGDA LOLA DEMs are the same family of product PITFAL used ([NTRS 20240014100](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf) [VF]). Its own documents already state that "local shape alone cannot uniquely resolve a global map translation" (`docs/PROJECT_EXPLAINED_AND_REFOCUSED.md:180-181`) [REPO].

The project's honest record is a genuine strength. Few published papers report failed criteria this plainly. That record includes:

- a learned veto that cut success from 90/162 to 18/162;
- a pre-written transfer criterion that failed;
- frozen protocols.

### The shifted-map 0/N result is guaranteed by design

Map-relative navigation cannot observe a global map offset. Suppose the prior is DEM(x + s) and the truth is DEM(x). A perfect shape match drives the estimate to q = p − s. Guidance drives q → 0, so the vehicle touches down at true position s, and the **absolute miss equals |s|**: 38.0 m in the final and transfer tests [COMP, derived from `TerrainNavigationCore.cs`]. No injected initial error is below 10 m, and every shift is above 10 m. **The 0/18, 0/54 and 0/90 shifted-map outcomes are therefore a tautology of the metric. They are not evidence about any policy.** A stronger learner seeing the same evidence cannot change this.

Under the Mars 2020 convention, where the target is chosen in the map, these same landings are **map-relative successes**. The flight literature keeps relative and inertial error separate. Woffinden's linear-covariance analysis shows relative error falling from about 20 m to about 2 m at the hazard scan while "inertial navigation errors remain largely unchanged" ([NTRS 20210026438](https://ntrs.nasa.gov/api/citations/20210026438/downloads/EvalLunarDescentResetting.pdf) [VF]). No paper that was read states the unobservability in one sentence; the support is structural plus the derivation above.

### The map perturbations are gross stress cases, not LOLA-realistic errors

Barker et al. (2021) adjusted LOLA tracks for exactly these PGDA site DEMs. They report:

- horizontal geolocation uncertainty of about **10–20 cm** and vertical about 2–4 cm, which "applies to total absolute position";
- a MOON_ME frame-orientation uncertainty of "a few meters";
- per-pixel height RMS of about 0.30–0.50 m;
- that about 90% of the 5 m pixels are interpolated ([Barker et al., PSS 2021, NTRS PDF](https://ntrs.nasa.gov/api/citations/20205009660/downloads/Mike%20Barker_%20Paper_%20Improved%20Lola.pdf) [VF]).

The local check of `Site01_final_adj_5mpp_toterr.tif` agrees: median 0.372 m, p99 0.991 m, max 5.58 m [LOCAL]. `toterr` is a **vertical-only** error layer, so it cannot justify horizontal shifts.

Against those figures [COMP]:

| LANTERN perturbation | Compared with | Ratio |
|---|---|---|
| 36–47 m shifts | post-adjustment geolocation | about 200–400× |
| 36–47 m shifts | ~7 m pre-adjustment LRO orbit error | about 5–7× |
| 8–20 m bumps | 0.3–0.5 m height RMS | about 16–65× |

These are legitimate **gross-fault** cases (a wrong tile or datum, a mis-specified site), and should be labelled that way. Because interpolation errors are spatially correlated at LOLA track-gap scales, independent white noise scaled by `toterr` would *understate* realistic error. LuNaMaps already uses richer deformation families: scale, smoothing, skew, shift, rotation and low-frequency noise ([Gnam et al., NTRS 20220008667](https://ntrs.nasa.gov/api/citations/20220008667/downloads/lunamaps_siw22_abstract.pdf) [VF, extended abstract]).

The *aligned* case is optimistic for a different reason. Truth and map share the same 8 m grid, so it is an identical-map case rather than a realistic one.

### The success criterion is stricter than NASA on miss distance

LANTERN counts a landing as a success when contact occurs with miss < 10 m, |vz| < 2 m/s and |vh| < 1 m/s [REPO]. NASA's requirements are:

- **Artemis III:** land within **100 m** of a target ([NASA HLS overview, NTRS 20250009323](https://ntrs.nasa.gov/api/citations/20250009323/downloads/ArtemisOverview2025IntSPAPPSChallenge.pdf?attachment=true) [VF-slides; a presentation, not the requirements document; the statistical definition is unconfirmed]).
- **Artemis IV onward:** **50 m** under any lighting ([NASA JSC ATRN, NTRS 20250003778](https://ntrs.nasa.gov/api/citations/20250003778/downloads/JSC_CIF_ATRN_Overview.pdf) [VF-slides]).
- **SPLICE:** designs to a 50 m GN&C budget [VF].

The same JSC slide gives the demonstrated south-pole state of the art as **250 m (IM-2)**. LANTERN's 10 m is therefore 5–10× stricter than requirements.

This matters for interpretation. Under a 50 m or 100 m threshold, the shifted-map runs' 38 m miss would *pass* on distance [COMP]. Whether they pass overall depends on the velocity limits, which this synthesis did not recompute.

The velocity limits are moderate by Apollo standards. The LM allowed 3.05 m/s vertical and 1.22 m/s horizontal for Vv ≤ 2.13 m/s, and accepted the envelope at P > 0.9974 ([TN D-6850](https://apollojournals.org/alsj//tnD6850LMLandingGearSubsytem.pdf) [VF]). They may be lax for tall commercial landers, given IM-1's tip-over (velocity split unresolved, above).

**Recommendation:** report success at 10, 50 and 100 m with the velocity limits held fixed. Report map-relative and absolute miss separately. State pass/fail as a probability over Monte Carlo runs, not a count of runs.

### The statistics and dynamics cannot carry generalisation claims

LANTERN's independent unit is the terrain area: 1 crop in the final test and 3 crops of one DEM in transfer. Seeds vary only sensor noise. With zero failures, 0/54 bounds the true rate at ≤ about 5.4% (95%). Showing 99% success at 99% confidence needs **n ≥ 459 independent trials** [COMP].

Practice is far larger: PITFAL used 1000 Monte Carlo runs, Mars 2020 "thousands", and ALHAT stated its requirements as 3σ. At about 0.37 s per descent, 10,000 runs take roughly an hour, so compute is not the constraint. Independent terrain and realistic dispersions are.

The dynamics are also idealized:

- 3-DOF point mass with frozen rotation;
- perfect initial velocity;
- no IMU bias;
- instantaneous scans;
- start altitudes of 0.5–2 km with 35–140 m errors.

ALHAT's TRN regime, by contrast, ran from 15 km down to 5 km with km-scale prior uncertainty ([Davis et al.](https://ntrs.nasa.gov/api/citations/20100025998/downloads/20100025998.pdf) [VF]).

### The horizontal-speed violations look guidance-side, and the mechanism is testable

A position correction feeds straight into a PD law, a = −0.04·x̂ − 0.5·v̂, with no terminal velocity-nulling phase [REPO]. The notes' linear analysis [COMP] gives:

- poles at −0.1 and −0.4 s⁻¹;
- for a position step Δ, a peak lateral speed of about 0.063·Δ at about 4.6 s;
- about 0.02·Δ left after the ~19 s descent from the last scan at 80 m AGL.

So a single late step of ≳50 m leaves ≳1 m/s at contact. Successive inconsistent corrections under changed terrain plausibly re-excite the loop.

This fits the observed pattern: every utility speed violation occurred under changed terrain. It also offers one explanation for why partial gains can lower mean miss while raising violations: spreading a step over several scans moves the last effective step closer to touchdown. That explanation is a hypothesis, not yet isolated. Apollo-era analyses reportedly flagged guidance "overreacting" to navigation updates (NTRS 19700025264 [UNV, snippet]). ALHAT's ~30 m vertical-descent phase and its deactivation of the altimeter and velocimeter during HRN are the flight-practice analogues ([Davis et al.](https://ntrs.nasa.gov/api/citations/20100025998/downloads/20100025998.pdf) [VF]).

## Corrections to the project's own documents

| Document and claim | What the 29 Oct research found | Status / action |
|---|---|---|
| `docs/RESEARCH_NOVELTY_REVIEW.md:51-60`: Choe, Kim, Cha, Park, ION ITM 2022, pp. 545-553, DOI 10.33012/2022.18160, "publisher's abstract reviewed" | Four separate searches (web, OpenAlex, dblp-adjacent) found no record. Related Choe TRN papers in TAES 2021, 2022 and 2024 were confirmed bibliographically. | **Needs re-verification, not proven wrong.** Open `ion.org/publications/abstract.cfm?articleID=18160` and resolve the DOI before citing. Until then, cite Choe & Park TAES 2024 instead. |
| `deliverables/5_Research_Paper_Summaries.pdf`: "IM-1's own rangefinders never worked, so NASA's experimental NDL lidar became the main sensor"; `deliverables/1_Literature_Review.pdf`: "team patched in NASA's NDL" | NASA TM-20250010290 [VF]: the patch "proved to be unsuccessful", and the vehicle landed "without the use of any NDL data", on IMU + optical feature tracking. | **Correct both.** NDL's value on IM-1 is post-flight reconstruction (about 5 m / 0.5 m/s agreement), not landing navigation. |
| 2014 LVS test described as Xodiac (research brief and search summaries) | Johnson et al. 2015 (NTRS 20160009627) was a **helicopter** field test. Dec 2014 flights were **Xombie** (2 flights). Xodiac carried COBALT (2017) and SPLICE/Draper (Sept 2019). | Not found in `docs/*.md` or the text of the project PDFs. Correct it wherever it enters future writing. |
| Site04 slope file `Site04_final_adj_5mpp_slp.tif` | 30,509,336 bytes, while its strip table ends at 40,980,772; tifffile fails to read it [LOCAL]. | **Already noted** in `README.md:57`, `docs/PROGRESS.md:56` and `docs/FULL_LOG.md:24` (slope derived from the DEM). Re-download from PGDA 78 before using any official slope or slope-error layer. |
| `docs/Paper_Draft.pdf` and `deliverables/3_Objective_and_Problem_Definition.pdf`: IM-2 "kept trusting a camera that could not see in shadow" | CEO account [SEC] lists **laser-altimeter interference** first, then lighting, then crater-appearance mismatch. The project's own Literature Review table already lists all three. | Reword to include altimeter noise. Do not present IM-2 as a camera-trust failure alone. |
| `deliverables/1_Literature_Review.pdf:73`: "NASA field tests show lidar-based TRN delivering position estimates under 90 m (CORE record)" | The CORE record returned 403 [UNV]. The verified "90 m" figure is ALHAT's **simulation** requirement (global 3σ < 90 m, POST2 Monte Carlo) [VF]. That they are the same figure is an inference. | Needs re-verification. Do not describe it as a field-test result until the source is read. |
| `docs/RESEARCH_NOVELTY_REVIEW.md`: PITFAL "rejects inconsistent multibeam ranges"; Sheppard et al. use "LRO confidence information" | PITFAL **inflates noise** rather than rejecting [VF]. Sheppard's actual noise source is the ASP shape-from-shading error map [VF]. | Minor wording fixes. Also update the readiness audit's "abstract-only" PITFAL entry: full text is now read (1000 MC runs, ends at 30 m AGL, no detection statistics). |

## The defensible contribution is a closed-loop gating study, not a new estimator

LANTERN cannot claim learned trust as a method: KalmanNet, AI-IMU, adaptive estimation, Acharya et al. and NeuroGrid all overlap with it. It cannot claim robustness to map error either, because its shifted case is unobservable by design. What survives is an **outcome-based mechanism study**: when does accepting a TRN correction improve position but worsen the touchdown state, and which classical or learned scheduling fixes that? Run it under literature-grounded map errors, and report fault-detection statistics that PITFAL does not publish. The notes found no published lunar-TRN study that reports closed-loop touchdown-velocity consequences of TRN gating. That is a limited search, so a targeted check comes before any gap claim.

There is one concrete, cheap differentiator the literature lacks. Verified lidar/DEM papers test with **no map error at all** (NeuroGrid, sliding grid), and PGDA ships **100 Monte Carlo "clone" DEMs per site** ([PGDA product 78](https://pgda.gsfc.nasa.gov/products/78) [VF-primary page]). Drawing truth from one clone and navigating on the released mean map would give product-derived, spatially correlated vertical map error. No paper that was read has done this.

### Ranked next steps

| Rank | Step | Why it ranks here | Done when |
|---|---|---|---|
| 1 | Re-score existing runs: map-relative and absolute miss; success at 10/50/100 m; relabel shifted-map as a **negative control** | Days of work; removes the tautology and the over-strict headline | Every results table shows both frames and all three thresholds |
| 2 | Replace the map-error model: truth = PGDA clone, map = released DEM; shift sweep from 0.1 m to 47 m; add LuNaMaps families (scale, rotation, smoothing); break identical-grid truth/map | Grounds perturbations in Barker-realistic magnitudes; makes the aligned case honest | Results reported against error magnitude, labelled realistic vs gross |
| 3 | Add classical baselines with matched tuning budgets: KF with R from cost-surface curvature + χ² gating; tuned gain/rate schedule; grid filter or PF (public Matoušek code) | No learned-gain claim survives without them | Same observations, controller and budget for every arm |
| 4 | Isolate the lateral-speed mechanism: predict contact \|vh\| from (Δ, time-to-go), verify it, then test guidance-side fixes (blending, terminal gate, velocity-nulling phase) against the RF gain | Cheap, falsifiable, and tied to Apollo/ALHAT practice | Prediction vs simulation agreement; mitigation effect with CIs |
| 5 | Scale statistics: many PGDA product 78 sites with the area as the unit, dispersed initial errors, ≥ several hundred runs per cell, cluster bootstrap, McNemar on paired success | Turns descriptive counts into inference | Site-level CIs; ≥459 trials for any 99% claim |
| 6 | Report fault-detection performance (missed detection, false alarm) of the gate against injected map faults, compared with a PITFAL-style consensus approximation (labelled as an approximation) | Fills a gap the NASA paper leaves open | ROC or operating-point table per fault type and size |
| 7 | Fidelity upgrades: IMU bias, attitude error coupled into scan geometry, uncertain velocity, scan latency, larger km-scale errors from higher start altitude | Required before any mission-relevance statement; ALHAT's HRN failure was a latency bug | Each upgrade's effect reported separately |
| 8 | Targeted literature check: full texts of Choe & Park 2024, Acharya 2025, NeuroGrid TAES 2024, LVS JGCD 2023 (doi:10.2514/1.G006780); AIAA GNC/SciTech 2018–2026 and JGCD for closed-loop TRN-gating touchdown effects | Needed before claiming any gap | Gap claim cites a documented search |

### Claims LANTERN should not make

| Do not claim | Reason |
|---|---|
| Shifted-map 0/N shows a weakness of any policy, or that the problem is "unsolved" | Guaranteed by absolute-frame scoring with \|s\| > 10 m; these are map-relative successes |
| 36–47 m shifts or 8–20 m bumps are realistic south-pole map errors | Barker et al.: decimetre geolocation, 0.3–0.5 m height RMS |
| Method novelty for learned trust or a learned gain | KalmanNet, AI-IMU, adaptive estimation, Acharya et al. 2025, NeuroGrid |
| Improved landing success or safety | Identical successes across arms (24/54; 54/162); transfer criterion failed; speed violations rose 39 → 47 |
| Generalisation to "unseen lunar sites" | 1–3 crops, prior project exposure to both DEMs |
| "Integrity monitoring" in the aviation sense | No protection levels; even PITFAL is fault detection |
| That LANTERN meets, or fails, NASA requirements | No mission-like dispersions or 3σ statistics; criteria differ from Artemis definitions |
| Flight-lidar realism or full-descent validity | Ideal attitude, perfect velocity, instantaneous scans, 0.5–2 km starts, 3-DOF |
| That the RF output is a probability or a covariance | Regression on an oracle position-error label |
| That IM-1 landed on NDL, or that IM-2 was purely camera trust | Contradicted by NASA TM [VF] and the CEO account [SEC] |

## Conclusion

The literature shifts LANTERN's centre of gravity. Its most visible results (shifted-map failure, sub-10 m misses, learned gain) are either guaranteed by design, judged against a stricter bar than NASA's, or already published in general form. The flight record shows that the field's real exposure lies elsewhere:

- integration and timing (ALHAT's stale-state gimbal bug, IM-1's unadmitted NDL);
- altitude-channel trust in both directions (M1, IM-2);
- map and appearance mismatch rather than map tie.

LANTERN can speak credibly to only one of these: how accepting a terrain fix feeds through guidance into the touchdown state. That is a narrower question than the project began with. It is also one the verified literature has not answered with published numbers.

The practical consequence is that the next month of work should *re-score and re-perturb*, not add models. Re-scoring with both frames and 10/50/100 m thresholds, replacing hand-placed bumps and shifts with PGDA clone errors, and adding Kalman/χ²/grid-filter baselines will show whether any learned-gain advantage exists once the design artifacts are removed. A null result under those conditions is still a reportable, defensible finding. A positive one would be the first evidence LANTERN has that does not depend on how the test was built.
