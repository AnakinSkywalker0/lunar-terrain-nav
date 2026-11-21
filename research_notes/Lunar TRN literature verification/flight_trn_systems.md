# Flight-proven and flight-tested TRN / landing-sensor systems (NASA/JPL): verified technical account

Compiled 2026-10-29. Labels: **[VF]** = VERIFIED-FULLTEXT (I read the PDF or slide text myself); **[AO]** = ABSTRACT-ONLY (NTRS/journal abstract read, full text not obtained); **[WEB]** = official NASA/JPL/USGS web page read through a fetch tool (primary, but a summary, not an archival paper); **[SEC]** = SECONDARY/UNVERIFIED (news, aggregator, or search-snippet text only).
Local copies of the PDFs, with SHA-256 hashes and download status, are in `D:\newprj\out\literature\20261029_trn_review\provenance.csv`. Two downloads are only partial: the Roback/Amzajerdian lidar paper (abstract plus first pages) and the COBALT open-loop paper (extended abstract). One is damaged: the M2020 Site Safety paper, which I did not read.

## Q1. Mars 2020 Lander Vision System (LVS) + Safe Target Selection (STS)

### Takeaway
LVS matched descent-camera images to an onboard map. It ran a coarse FFT-correlation batch stage and then a fine spatial-correlation EKF stage. It was built and verified to put map-relative position error under 40 m (99th percentile) within 10 s, starting from a 3.2 km initial error. In flight, the landing came out about 5 m from the STS-selected target, against a 60 m requirement. Pre-landing prediction was 33 m; post-landing reconstruction was 8.53 m or better. This is **one flight (n=1)**. The detailed in-flight LVS error numbers are in papers I could only get as abstracts. Map-tie error was largely avoided by design: the hazard/safe-target map was co-registered to the LVS map, so the whole system works in map frame.

### Cited Findings
**Architecture and hardware**
- TRN = LVS (map-relative position) + STS (picks a safe, reachable target from an onboard Safe Targets Map). The target is handed to the heritage MSL powered-descent GNC. The TRN interface was designed to "do no harm" to MSL EDL, and the vehicle "can still land without TRN". **[VF slides]** [Johnson, LSIC workshop slides, 2021-03-02](https://lsic.jhuapl.edu/uploadedDocs/presentations/764-1.09_Johnson_20210302_LuNaMaps_LVS_v0.pdf); [STS reconstruction abstract, NTRS 20230005646](https://ntrs.nasa.gov/citations/20230005646) **[AO]**
- LCAM (built by Malin Space Science Systems): 1024×1024 pixels, global shutter, 90°×90° FOV, 100 ms latency, 200 µs exposure. Vision Compute Element: RAD750 plus a Computer Vision Accelerator Card (Virtex-5 FPGA, "up to 7000 MIPS image processing"), with maps in flash memory. Inputs were Honeywell MIMUs (DIMU-A/B). **[VF slides]** [Johnson 2021 slides](https://lsic.jhuapl.edu/uploadedDocs/presentations/764-1.09_Johnson_20210302_LuNaMaps_LVS_v0.pdf)
- Operating envelope as stated on the slides:
  - Lighting: sun elevation 25–55°, sun azimuth 240–310°.
  - Attitude and rates: off-nadir < 45°, angular rates < 50°/s.
  - Velocity: horizontal < 70 m/s, vertical 60–115 m/s.
  - Terrain: slope < 15°, relief < 150 m, "appearance entropy > 4".
  - Timeline: start "as high as 4200 m", operate until 2000 m or backshell separation.
  - **[VF slides]** [Johnson 2021 slides](https://lsic.jhuapl.edu/uploadedDocs/presentations/764-1.09_Johnson_20210302_LuNaMaps_LVS_v0.pdf)
- Performance spec on the slides: remove an initial position error of 3.2 km. Reach "40m 99%tile at 6 seconds (95% of time)" and "40m 99%tile at 10 seconds (99% of time)". **[VF slides]** [Johnson 2021 slides](https://lsic.jhuapl.edu/uploadedDocs/presentations/764-1.09_Johnson_20210302_LuNaMaps_LVS_v0.pdf)

**Two-stage matching**
- **Coarse mode.** Images arrive at about 1 Hz and IMU data at 200 Hz.
  - An interest operator runs over 64×64 windows.
  - 5 landmarks per image are warped by homography/RDC and correlated as 128×128 templates by FFT against a normalized map.
  - Sub-pixel peak fitting, then "coarse outlier rejection", then a **batch estimator**.
  - This repeats 3 times (3 images × 5 landmarks = 15 landmarks).
  - **[VF slides]** [Johnson 2021 slides](https://lsic.jhuapl.edu/uploadedDocs/presentations/764-1.09_Johnson_20210302_LuNaMaps_LVS_v0.pdf)
- **Fine mode.** 150 windows per image, spatial correlation of 21×21 windows, sub-pixel peaks, "fine outlier rejection", then an **EKF** with IMU propagation. LVS state is output at 8 Hz. **[VF slides]** (same source)
- The JPL Robotics page describes it differently:
  - Coarse: 15 landmarks over 3 images, 128×128 templates in 1024×1024 map windows, frequency-domain correlation.
  - Fine: up to 150 landmarks per image, **15×15** templates in 100×100 windows.
  - Maps: "12 and 6 m/pixel" for coarse and fine, "processed" from HiRISE (~30 cm/pixel).
  - **[WEB]** [JPL Robotics TRN page](https://www-robotics.jpl.nasa.gov/what-we-do/flight-projects/mars-2020-rover/terrain-relative-navigation/)
  - Discrepancy 1: the template size is 15×15 on the web page but 21×21 on the CDR-era slides.
  - Discrepancy 2: the map source is HiRISE on the web page but CTX in USGS/Cheng (next bullets).

**Map products and map tie**
- The LVS onboard map is a **CTX** orthomosaic of about 6 m/pixel (20 m version also produced) with a 20 m CTX DTM. It was built from 3 CTX stereo pairs. The DTMs were aligned to each other (translation only) and then to the HRSC Level 5 DTM; the control net is listed as MOLA. CTX orthoimages show "an average horizontal displacement of 9.6 meters" between one another. The CTX map was the "truth" dataset TRN used. **[WEB]** [USGS Astropedia, M2020 TRN CTX orthomosaic](https://astrogeology.usgs.gov/search/map/mars_2020_terrain_relative_navigation_context_camera_orthorectified_image_mosaic) (dataset DOI 10.5066/P9GV1ND3)
- The hazard basemap is a HiRISE orthomosaic at 25 cm with 1 m DTMs.
  - It was **registered to the CTX LVS map**, not independently to the Mars frame.
  - "94.1% of matched features have displacements <6 meters". The authors call this conservative against a 99% requirement.
  - A HiRISE–CTX **scale distortion** was corrected with a single 2D affine transform (translation, rotation, scale).
  - The hazard map flew onboard for TRN.
  - **[WEB]** [USGS Astropedia, M2020 TRN HiRISE orthomosaic](https://astrogeology.usgs.gov/search/map/Mars/Mars2020/JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first)
- Cheng, Ansar, Johnson et al. (2021, *Earth and Space Science*, doi:10.1029/2020EA001560): the LVS map was made from MRO/CTX. The local hazard map is "registered to the LVS reference map so that the safe target selection (STS) system can select a safe and reachable landing site". The final error is estimated at about 5 m. **[SEC: search-snippet text only; Wiley page returned 403]** [ADS record](https://ui.adsabs.harvard.edu/abs/2021E&SS....801560C/abstract)
- A JPL presentation (as quoted in the search tool's summary) checked the "LVS appearance map to HiRISE: error < 3m". **[SEC]** (no URL confirmed)

**Error budget and in-flight result**
- The 60 m landing requirement was split into three parts:
  - **Targeting error:** LVS localization, LVS-to-NavFilter synchronization, LVS reference-map errors and STS.
  - **Knowledge error:** growth after synchronization.
  - **Control error.**
  - **[AO]** [Chen, Casoliva, Montgomery et al., "Assessment of M2020 Terrain Relative Landing Accuracy: Flight Performance vs Predicts", NTRS 20230007014](https://ntrs.nasa.gov/citations/20230007014)
- Predictions versus result: pre-landing best estimate 33 m; post-landing analysis "8.53m or better"; post-landing imagery put the rover 5 m from target. **[AO]** (same)
- The flight-performance paper reports a touchdown error to target of 5 m, "an order of magnitude less than the 60m touchdown error requirement". It also covers final pre-launch tests and checkout during cruise. **[AO]** [Montgomery/Johnson et al., "Mars 2020 LVS Flight Performance", AIAA SciTech 2022, NTRS 20230006986](https://ntrs.nasa.gov/citations/20230006986)
- The JPL page says LVS "achieves a position error <40 m relative to the map". It argues the very low touchdown error implies low local map distortion, accurate sensor alignment and sharp correlation peaks. **[WEB]** [JPL Robotics](https://www-robotics.jpl.nasa.gov/what-we-do/flight-projects/mars-2020-rover/terrain-relative-navigation/)
- The 2023 JGCD paper (Johnson, Cheng, Trawny, Montgomery +5; doi:10.2514/1.G006780) covers the map-relative localization implementation. A search snippet says "postflight analysis indicated that all required systems worked much better than predicted". **[SEC — AIAA returned 403; aggregator only]** [Bohrium listing](https://www.bohrium.com/paper-details/implementation-of-a-map-relative-localization-system-for-planetary-landing/838367174396477441-4102)

**Safe Target Selection**
- STS chose "the safe landing target within a reachable region from the on-board Safe Targets Map". **[AO]** [NTRS 20230005646](https://ntrs.nasa.gov/citations/20230005646)
- The divert was constrained by a minimum distance (to reduce recontact risk with the parachute and backshell) and a maximum distance. **[SEC: search snippet of NTRS 20200002978; the PDF download was damaged]** [EDL Simulation Results for M2020 Landing Site Safety Assessment](https://ntrs.nasa.gov/api/citations/20200002978/downloads/20200002978.pdf)
- "With TRN, the overall probability of success is predicted to be approximately 99% for all of the candidates." This is a **simulation** result. **[AO]** (same paper; abstract via NTRS API)

**Navigation filter**
- The M2020 NavFilter is based on Curiosity's, with modifications. It integrates DIMU data and uses the Terminal Descent Sensor (radar) for surface-relative corrections. It supplies dynamic state to entry guidance, LVS and powered-descent guidance. **[AO]** [Casoliva et al., "The Mars 2020 Perseverance Navigation Filter", NTRS 20230005661](https://ntrs.nasa.gov/citations/20230005661)

**Test evidence (what was demonstrated where)**
- **2014 helicopter field test** of the LVS prototype over Mars-analog terrain at representative altitudes. It ran in real time "without human intervention or tuning" and gave "estimates accurate to 40m (3 sigma) in 10 seconds". **[AO]** [Johnson et al., "Real-time TRN Test Results from a Relevant Environment for Mars Landing", AIAA GNC Jan 2015, NTRS 20160009627](https://ntrs.nasa.gov/citations/20160009627)
  - **Note:** this paper is a *helicopter* test, not the Xombie rocket flights. Search summaries conflate the two.
- **Dec 2014 Masten Xombie (ADAPT):** LVS plus G-FOLD as a standalone payload, with "two successful free flight demonstrations". **[AO]** [Trawny et al., AIAA SPACE 2015, NTRS 20170008233](https://ntrs.nasa.gov/citations/20170008233)
  - Flight details: Dec 4 and Dec 9, 2014; 325 m max altitude; divert began at about 190 m; landed about 300 m from the launch pad. **[SEC]** [spaceref/news](https://spaceref.com/?p=12871); [JPL news](https://www.jpl.nasa.gov/news/nasa-flight-program-tests-mars-lander-vision-system/)
  - **n=2 flights**, low altitude compared with Mars LVS start (4200 m).
- **2016 algorithm robustness work:** bland terrain, map/image appearance differences, initial state errors, vertical motion. Tested on MSL flight imagery, a simulation and multi-altitude field data. **[AO]** [Johnson et al., SciTech 2016, NTRS 20170008287](https://ntrs.nasa.gov/citations/20170008287)
- **2017 COBALT on Masten Xodiac:** LVS plus NDL, open loop. **[AO, title only]** [NTRS 20210006132](https://ntrs.nasa.gov/citations/20210006132)
  - The COBALT filter agreed with the Xodiac GPS/IMU to within about 5 m and 0.5 m/s. **[VF, as cited in NASA TM-20250010290 §1]** [NDL IM-1 TM](https://ntrs.nasa.gov/api/citations/20250010290/downloads/NASA%20TM%2020250010290.pdf)
- **May 2019 M2020 LVS field test:** "over 600 independent real-time runs on engineering model LVS hardware and software" met the 40 m requirement "over a wide operational envelope". Off-nominal and fault-recovery cases were included. **[AO]** [Johnson et al., "The Mars 2020 LVS Field Test", NTRS 20220000862](https://ntrs.nasa.gov/citations/20220000862)
- **V&V approach:** a "trifecta" of Monte Carlo simulation with high-fidelity models and FSW, field tests with EM hardware ("real surface and illumination, representative dynamics", used for model validation), and HWIL testbeds with flight/EM hardware. **[VF slides]** [Johnson 2021](https://lsic.jhuapl.edu/uploadedDocs/presentations/764-1.09_Johnson_20210302_LuNaMaps_LVS_v0.pdf). NASA Science says Monte Carlo runs were made "thousands of times". **[WEB]** [NASA Science TRN highlight](https://science.nasa.gov/science-research/science-enabling-technology/technology-highlights/terrain-relative-navigation-landing-between-the-hazards/)

### Inferences
- The brief's wording "Masten Xodiac 2014/2019" does not match the sources:
  - 2014 was **Xombie** (ADAPT, 2 flights).
  - The 2019 LVS validation was a **field test with 600+ runs**. The slides list Pursuit Aviation on the field-test team, which suggests an aircraft or helicopter campaign; this is not verified.
  - The Sept 2019 Xodiac flight was **SPLICE/Draper TRN**, not LVS.
- The 5 m result comes from one landing. It shows the error budget held in that case; it does not give a statistical estimate of accuracy. The statistical evidence is the 600+ field-test runs plus Monte Carlo runs.
- The system is map-relative end to end: the LVS estimate and the hazard map share the CTX map frame. A rigid global offset of the CTX map relative to the true Mars frame therefore mostly cancels for hazard avoidance. What matters is the **relative** co-registration (HiRISE↔CTX, <6 m for 94.1% of features) and local distortion.

### Gaps
- I could not get full text of: the SciTech 2022 LVS flight paper (NTRS has no PDF; ResearchGate and AIAA returned 403), the JGCD 2023 paper, the Chen 2021 error-budget paper, the STS reconstruction, the NavFilter paper, or the 2019 field-test paper. Missing as a result:
  - in-flight landmark counts and inlier rates
  - LVS first-fix time and altitude
  - the per-term error-budget allocations
  - the exact outlier-rejection algorithm
  - how the LVS solution was handed to the NavFilter (the "synchronization" term)
- The LVS map-tie numbers (CTX map against the MOLA/HRSC absolute frame) are not quantified in what I read, apart from the 9.6 m average CTX-to-CTX displacement.

## Q2. ALHAT and the Morpheus 2014 free flights

### Takeaway
ALHAT flew a flash-lidar Hazard Detection System (in-flight DEM, safe-site ranking, hazard-relative navigation), a Navigation Doppler Lidar and a laser altimeter on Morpheus over the KSC hazard field. The ALHAT-driven flights were FF10–FF14 (Apr–May 2014) and FF15 (Dec 2014). Hazard detection and safe-site selection worked. HRN was the weak point: only 1–2 of 8–10 measurement opportunities succeeded per flight, and the filter diverged on FF13/FF14. A timing feedback bug was found as the root cause and fixed for FF15, which processed 7 HRN measurements. This is a small-n terrestrial demonstration (about 250 m altitude, 400 m downrange), not a lunar-relevant TRN test. Global TRN was not flown on Morpheus.

### Cited Findings
- ALHAT Level-0 requirements:
  - **Global precision:** map-based target with 1σ < 30 m and no hazard-avoidance maneuver.
  - **Local precision:** selected safe site with 1σ < 3 m.
  - **Hazard detection:** hazards ≥30 cm and slopes ≥5°.
  - **Lighting:** any lighting condition, which is why all ALHAT sensors were active lidars.
  - **[VF]** [Epp et al., AIAA SPACE 2014, NTRS 20140010334](https://ntrs.nasa.gov/api/citations/20140010334/downloads/20140010334.pdf)
- Hazard-detection-phase trajectory: about 98 s total flight, with **14.1 s** allotted to the HDS to build the DEM, rank the top 5 safe sites and return them. Test objectives included "DEM … generated within six seconds" and "DEM map-tie error is less than one meter". The top site had to be within 2 m of the pad centre (a Morpheus-imposed threshold). **[VF]** (Epp 2014)
- HRN outcome: "Only one or two HRN measurements (out of 8 to 10 opportunities)" per closed-loop flight. Images were lost to dust pre-triggering or failed the "correlation threshold", or the feature "exceeded the correlation radius". HRN "tended to drive the ALHAT navigation solution away from the VTB navigation solution". HRN was "the only ALHAT technique that was not fully verified". **[VF]** (Epp 2014)
- Despite this, the same paper claims TRN, HDA and HRN are all at "TRL6 or higher" pending resolution of the issues. TRN itself had been demonstrated earlier, on a 2009 fixed-wing aircraft campaign (FT3) with passive cameras and the flash lidar/altimeter, not on Morpheus. **[VF]** (Epp 2014)
- **Flight log:** FF10 (3/2014, DL polarity issue), FF11 (4/2014), FF12 (4/2014, "Lost HRN target track"), FF13 (5/2014), FF14 (5/2014, night) and FF15 (12/2014, "Successful ALHAT test"). FF10–12 were open loop with VTB nav flying; FF13–15 were closed loop on ALHAT nav. **[VF]** [Crain et al., AIAA SciTech 2016, NTRS 20170009198](https://ntrs.nasa.gov/api/citations/20170009198/downloads/20170009198.pdf)
  - Internal inconsistency: Table 8 dates FF15 to 12/2014 and the text says "Flight testing completed with Free Flight 15 on December 15, [2014]", but another passage says "FF15 was executed in late 2015".
- **FF13/FF14 divergence:** HRN processing diverged and the AFM down-moded to VTB nav (at about MET 67 s on FF13 and about MET 90 s on FF14). Root cause: "the HDS processor was steering the laser camera to a pre-updated Kalman filter state". The bookkeeping error between the gimbal-steering loop and the KF correction was "not discovered in simulation because the modeled HDS software did not have an actual processor delay". FF15 processed "a record 7 HRN vector measurements … displaying convergent behavior". **[VF]** (Crain 2016)
- **Landing accuracy** (Table 9, ALHAT closed loop; my parse of a garbled table): FF15 nav-vs-measured error was about 0.74 m East and 0.32 m North; FF13 and FF14 were about 0.02/0.20 m and 0.09/0.19 m. The abstract says "landing within 2 meters of the VTB GPS-based navigation solution at the safe landing site target". **[VF]** (Crain 2016; the per-flight values are my reading of the extracted layout)
- **Sensor specs (lidar paper):**
  - Flash lidar: "identifying a 30 cm hazard from a slant range of 1 km with its 8 cm range precision at 1 sigma"; HRN updates down to 250 m slant range.
  - NDL: velocity accuracy 0.2 cm/s and range accuracy 17 cm, from 2,200 m maximum range down to a few metres.
  - Laser altimeter: 5 cm accuracy from 30 km down to 1 m.
  - **[VF, abstract/first pages]** [Roback, Pierrottet, Amzajerdian et al., SciTech 2015, NTRS 20160005928](https://ntrs.nasa.gov/api/citations/20160005928/downloads/20160005928.pdf)
- **Demonstrated in flight versus claimed:** 30 cm hazards were detected only "from the maximum slant range of 450 m which Morpheus could provide", not 1 km. Failure modes:
  - Flash-lidar range noise from plume-heated air.
  - **Dust pre-triggering** during HRN.
  - NDL signal degradation from heated air.
  - The laser altimeter flew with a "degraded transmitter laser".
  - **[VF]** (Roback 2015)
- NDL open-loop velocities agreed with Morpheus navigation "to within 5 cm/s". The NASA TM counts **six** NDL flights in 2014: 3 open loop, then 3 closed loop. **[VF]** [NASA TM-20250010290 §1](https://ntrs.nasa.gov/api/citations/20250010290/downloads/NASA%20TM%2020250010290.pdf)
- HDS abstract: "five successful free flights" at the SLF hazard field, "first autonomous landing of a NASA rocket-powered vehicle in hazardous terrain". **[AO]** [Trawny et al., SciTech 2015, NTRS 20160009637](https://ntrs.nasa.gov/citations/20160009637)

### Inferences
- Counts of ALHAT flights differ by source: 5 (Trawny, Epp: FF10–14), 6 (NDL TM, including FF15) and 3 closed loop (FF13–15). Any "flight-proven" claim rests on about 3 closed-loop flights, and only one (FF15) had working HRN.
- The safety architecture (a GPS-based VTB string as hot backup) means the closed-loop ALHAT flights never exercised unrecoverable failures.

### Gaps
- The Trawny HDS full text (DEM resolution, timing actually achieved, safe-site truth comparison) was not available as a PDF on NTRS.
- The Crain Fig. 2 "map-tie error" values for the lunar descent profile are not legible in the extracted text.

## Q3. SPLICE: components, flight tests 2019–2026, status

### Takeaway
SPLICE flew TRN (a COTS camera with Draper algorithms), NDL and a Descent and Landing Computer (DLC) surrogate open loop on two New Shepard flights (2020 and Aug 2021). The NDL produced no usable data on either flight (anomalies; helium environment). Published TRN/nav results are post-flight playback against the launch vehicle's GPS navigation, presented as plots only. The integrated closed-loop Xogdor flight planned for 2025 does not appear in NASA's Aug 2026 SPLICE page. Instead, that page lists Mar 2025 helicopter tests of HDL/DLC/HDS, Aug 2026 drone tests of DQG/ATRN, and a **September 2026 closeout** milestone. I could not confirm that the closeout happened. NDL technology reached the Moon on IM-1 (Feb 2024), but the lander's filter never ingested its data.

### Cited Findings
- **Goals (FY23 annual review):**
  - Landing precision within 50 m.
  - DQG trajectory solutions within 3 s.
  - HDL: "1 MP digital elevation map of 100x100m area at 1.5cm (1σ) elevation precision" within 2 s.
  - Hazard-detection software: 1 MP DEM processed in 2 s.
  - Navigation: "onboard position accuracy of 3m (3σ) relative to a safe site within the DEM".
  - TRL/SRL 6.
  - Final flight planned on "Xogdor SPLICE Flight Test" (Astrobotic Tipping Point, "Suborbital Testing 2025").
  - Partners: Psionic PS-NDL, Astrobotic A-TRN, Draper TRN/GN&C, GSFC HDL.
  - **[VF slides]** [Mendeck & May, FY23 SPLICE APR, NTRS 20230011737](https://ntrs.nasa.gov/api/citations/20230011737/downloads/SPLICE_FY23%20GCD%20APR.pdf)
- **New Shepard navigation filter:**
  - Discretized EKF in UDU form; ECI translational states.
  - **41 states** (10 dynamic + 31 parameter, including NDL beam biases, camera-to-IMU misalignment, and camera focal-length and principal-point biases) and 40 error states.
  - Split into a high-rate IMU propagation app and a low-rate update app.
  - The update app performs "fault detection and residual editing checks for accepting/rejecting NDL and TRN sensor measurements", plus measurement underweighting.
  - **[VF]** [Fritz et al., AIAA SciTech 2022, NTRS 20210023718](https://ntrs.nasa.gov/api/citations/20210023718/downloads/AIAA_SciTech2022_TP2_NAVDQG.pdf)
- **TRN measurement model:** pixel locations of features matched to an onboard database. Four features were processed at a time, from a 1440×1080 COTS monochrome camera. Hardware: DLC EDU on a Xilinx UltraScale+ MPSoC, with FPGA time-stamping of sensor data. **[VF]** (Fritz 2022)
- **Flight outcome (the analysed flight):**
  - NDL anomalies appeared about 2 h before launch. The NDL "was therefore rejected by the navigation algorithm via its built-in fault protection logic", so only IMU and TRN were active. The ~7 min flight was **open loop**, and DQG solved every 5 s.
  - Post-flight, a **simulated** NDL (4.5 km max slant range) was injected in playback.
  - "Truth" was the launch vehicle's GPS-aided navigation; no best-estimate trajectory was available.
  - TRN accuracy degrades with altitude because of map and image resolution.
  - Near landing, residuals grew from dynamics plus "foreign object debris on the lens".
  - **No numeric error table is given (figures only).**
  - **[VF]** (Fritz 2022)
- The earlier SPLICE TRN flight on Masten Xodiac reached 500 m with a Multi-State Constraint Kalman Filter (IMU + barometer + TRN), open loop. **[VF, as described in Fritz 2022 §I, citing Fritz et al. SciTech 2020]**
- **Second New Shepard flight (August 2021):** "more than 4,000 images" over about 7 min. Navigation "met performance targets" using IMU and TRN. The Doppler lidar had a "pre-launch anomaly" and a review board was formed. NASA called this "initial post-flight analysis". **[WEB]** [NASA Langley, 2021-11-29](https://www.nasa.gov/centers-and-facilities/langley/nasa-matures-lunar-landing-tech-through-suborbital-flights/)
- NDL on New Shepard: "two flights in 2020 and 2021 … adversely affected by the helium environment … performance could not be evaluated". Earlier China Lake sled tests showed tracking ">200 m/s and at ranges up to 4 km". **[VF]** [NASA TM-20250010290](https://ntrs.nasa.gov/api/citations/20250010290/downloads/NASA%20TM%2020250010290.pdf)
- **Official SPLICE page (last updated Aug 25, 2026):**
  - NDL activates at about 10 km; HDL at about 500 m.
  - Events listed: Sept 2019 Draper TRN on Xodiac; June 2019 NDL sled at about 250 m/s; **March 2025** helicopter tests of HDL, DLC and HDS at the KSC hazard field; **Aug 2026** closed-loop drone tests of DQG and ATRN at Voyager's Lunar Surface Proving Grounds (Mojave); "September 2026: SPLICE project closeout".
  - Outcomes are not stated for most events. Infusion is described only as "will be considered" for Artemis and Mars sample return.
  - **[WEB]** [NASA SPLICE page](https://www.nasa.gov/safe-and-precise-landing-integrated-capabilities-evolution-splice/)
- **Active TRN (JSC CIF):** a 3D keypoint pipeline; claims keypoint errors under 10 cm and pose errors under 10 cm and 0.05°. A C++ library was expected Oct 2025, with evaluation planned on GSFC HDL helicopter DEMs. This is a presentation and reads as pre-flight. **[AO]** [NTRS 20250003778](https://ntrs.nasa.gov/citations/20250003778)
- **NDL on IM-1 (CLPS, Feb 22, 2024):**
  - Sensor: FMCW, 3 beams, up to 218 m/s line-of-sight, ranges 5 km to 2 m, 20 Hz.
  - Calibration 1σ: range ≈ 1.2×10⁻⁴·R + 0.16 m; velocity ≈ 1.11×10⁻⁶ (scaled term) + 1.4×10⁻³ m/s.
  - In flight, beam A ranged ">20 km, in excess of the expected 5 km".
  - The lander's laser altimeter was found non-operational. A flight-software patch to ingest NDL "proved to be unsuccessful", so the landing used IMU plus optical feature tracking only.
  - Post-flight reconstruction agreed with NDL to about 5 m and 0.5 m/s.
  - **[VF]** [NASA TM-20250010290, Nov 2025](https://ntrs.nasa.gov/api/citations/20250010290/downloads/NASA%20TM%2020250010290.pdf)
- **Astrobotic's own HD lidar** (not SPLICE HDL) for Griffin Mission One: 15 cm hazards, slopes >10°, scans while hovering at 100 m. It flew on Xodiac Nov 2024 and in an integrated HD + GNC test in March 2026. **[WEB]** [NASA Flight Opportunities transition page](https://www.nasa.gov/stmd-flight-opportunities/transitions-of-flight-tested-technologies/hazard-detection-lidar-system-goes-to-the-moon/)

### Inferences
- The Fritz paper's flight is very likely the Aug 2021 flight (NS-17): pre-launch NDL anomaly, ~7 min, 1440×1080 camera, submitted for SciTech 2022. The paper does not name the flight number.
- Measured against its own goals (3 m 3σ safe-site navigation, 1.5 cm HDL DEMs, integrated closed-loop suborbital flight), SPLICE's public flight evidence is thin: open-loop TRN+IMU only, no in-flight NDL data, and the HDL tested only on helicopter. Transfer to CLPS and HLS is shown for NDL (IM-1, as data only) and is not documented for SPLICE HDL or TRN in the sources I read.

### Gaps
- No source confirms whether the 2025 Xogdor flight happened, the outcomes of the 2025 helicopter and 2026 drone tests, or that the Sept 2026 closeout occurred.
- No documented SPLICE-to-HLS transfer agreement was found.

## Q4. Active (lidar-to-DEM) vs passive (camera-to-image) TRN under map misregistration

### Takeaway
None of the flown systems detects a global offset between its map and the true planet frame. Each estimates position *in map frame*. Flight programs handle this by design:
- M2020 co-registered the hazard map to the LVS map and budgeted reference-map error inside "targeting error".
- ALHAT accepted that the in-flight DEM inherits navigation error (its "map tie") and then used HRN to hold DEM-relative accuracy.
Active versus passive changes lighting robustness and what is matched (geometry versus appearance), not the map-tie problem.

### Cited Findings
- ALHAT: the DEM is centred on the ILP. "Knowledge error in the ALHAT Nav estimate of ILP-relative HDS pose causes a map tie error between the DEM and the pre-mission desired mapping region. This is a known phenomenon and is not a problem in the architecture… HRN measurements are used after HD to minimize the additional growth of DEM-relative errors." The terrestrial test, however, compared against GPS truth, which is why a 2 m allowance was needed. FF10 and FF14 safe sites fell outside it. **[VF]** [Epp 2014](https://ntrs.nasa.gov/api/citations/20140010334/downloads/20140010334.pdf)
- ALHAT's reason for active sensors was the "any lighting conditions" requirement. The same authors expect most future robotic TRN to be passive optical. **[VF]** (Epp 2014)
- M2020: the 60 m budget includes "errors associated with the LVS Reference Map and Safe Target Selection" within targeting error. **[AO]** [Chen et al., NTRS 20230007014](https://ntrs.nasa.gov/citations/20230007014)
- The hazard map was registered relative to the LVS map (HiRISE↔CTX affine fit; 94.1% of features <6 m). The CTX map itself was aligned to HRSC/MOLA. **[WEB]** [USGS HiRISE](https://astrogeology.usgs.gov/search/map/Mars/Mars2020/JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first); [USGS CTX](https://astrogeology.usgs.gov/search/map/mars_2020_terrain_relative_navigation_context_camera_orthorectified_image_mosaic)
- SPLICE New Shepard: TRN measurement accuracy falls with altitude "due to the resolution of the onboard maps and imagery". **[VF]** [Fritz 2022](https://ntrs.nasa.gov/api/citations/20210023718/downloads/AIAA_SciTech2022_TP2_NAVDQG.pdf)

### Inferences
- A **rigid global shift** of the onboard map is not observable by either TRN type. It only harms the mission if the target or hazard knowledge sits in a different frame from the TRN map. Building every product in a single map frame (M2020) makes the shift cancel for hazard avoidance.
- **Relative** distortions between maps (scale, local warps) and between map and terrain do propagate. Scale distortion was found and corrected in M2020.
- In-flight hazard-relative navigation (HRN, or an onboard DEM such as SPLICE HDL) is immune to orbital-map tie for the final approach, because it builds its own local map. It inherits nav error at DEM-formation time, though.

### Gaps
- I found no flown-system paper giving a numeric budget for an absolute map-to-inertial tie (for example, CTX vs MOLA uncertainty for M2020, or a lunar LOLA tie for SPLICE).

## Q5. Trust and rejection logic for TRN fixes

### Takeaway
What is documented is generic:
- M2020 LVS: separate coarse- and fine-stage outlier rejection, a batch estimator before EKF handover, hard operational-envelope gates, and a "can still land without TRN" fallback.
- SPLICE: EKF residual editing and fault detection that rejected a failed NDL in flight.
- Morpheus: correlation threshold and radius tests for HRN, and an independent-navigation corridor switch.
None of the sources I could read give the statistical thresholds.

### Cited Findings
- LVS pipeline: "coarse outlier rejection" before the batch estimator; "fine outlier rejection" before the EKF; flight figures label inlier and outlier matches. **[VF slides]** [Johnson 2021](https://lsic.jhuapl.edu/uploadedDocs/presentations/764-1.09_Johnson_20210302_LuNaMaps_LVS_v0.pdf)
- LVS envelope gates (sun angles, rates, velocities, terrain entropy and relief) are listed in Q1. **[VF slides]**
- SPLICE update steps: "perform measurement underweighting… compute the measurement residual, perform residual editing". The fault protection rejected the invalid NDL output in flight. **[VF]** [Fritz 2022](https://ntrs.nasa.gov/api/citations/20210023718/downloads/AIAA_SciTech2022_TP2_NAVDQG.pdf)
- ALHAT HRN validity: images that "did not meet the correlation threshold… or exceeded the correlation radius" produced no measurement. The search window required the predicted feature to be within about 2 m. **[VF]** [Epp 2014](https://ntrs.nasa.gov/api/citations/20140010334/downloads/20140010334.pdf); [Crain 2016](https://ntrs.nasa.gov/api/citations/20170009198/downloads/20170009198.pdf)
- Morpheus AFM: if ALHAT nav drifts outside a corridor around the GPS-aided VTB nav, it switches to VTB. After FF13, DL velocimetry was processed only when all three beams were available. **[VF]** (Epp 2014; Crain 2016)

### Inferences
- An independent, trusted reference string (GPS on Morpheus) is a test-range integrity mechanism with no analogue on the Moon or Mars. Flight-like integrity would have to rely on internal consistency (outlier rejection, residual gating, envelope gates) plus a fallback to an inertial or radar-only path, as M2020's "do no harm" design did.

### Gaps
- No access to the LVS outlier-rejection method (RANSAC versus residual consensus), chi-square gate values, or LVS-to-NavFilter acceptance logic. These are likely in the JGCD 2023 paper and the SciTech 2022 flight-performance paper.

## Q6. Navigation filter architectures and latency handling

### Takeaway
All three programs used IMU-propagated Kalman filters with explicit handling of delayed measurements:
- **Morpheus/ALHAT:** dual-state inertial estimator; ring buffer for 2 s-late HRN measurements.
- **SPLICE:** UDU EKF that propagates to measurement time and back.
- **M2020 LVS:** its own batch→EKF estimator synchronized to the MSL-heritage NavFilter.
Timing bugs, not sensing, caused the most serious ALHAT in-flight failure.

### Cited Findings
- **ALHAT (Morpheus):**
  - "Dual-state inertial estimator Kalman filter" running at 5 Hz with a 200 ms measurement-validity window.
  - HRN arrived "up to 2 seconds after the laser camera image", so a "ring buffer storing additional state and covariance data" was added.
  - SIGI IMU low-pass filtering caused up to 120 ms delay, reduced to 20 ms with a firmware update.
  - GPS poll-response caused up to 200 ms delay, never fixed.
  - Attitude error over 0.1° would prevent a successful HRN test, so a GIDE optical alignment was done before launch.
  - **[VF]** [Crain 2016](https://ntrs.nasa.gov/api/citations/20170009198/downloads/20170009198.pdf)
- **SPLICE:** "For each measurement, the state estimate, error state and covariance are propagated to the time of the measurements… then propagated back to the time corresponding to the latest IMU time in the buffer." Covariance propagation uses modified Gram-Schmidt plus Agee-Turner rank-one updates. **[VF]** [Fritz 2022](https://ntrs.nasa.gov/api/citations/20210023718/downloads/AIAA_SciTech2022_TP2_NAVDQG.pdf)
- **M2020 LVS:** images at about 1 Hz, IMU at 200 Hz, a time-ordered data sequencer, LVS state at 8 Hz, LCAM latency 100 ms. **[VF slides]** [Johnson 2021](https://lsic.jhuapl.edu/uploadedDocs/presentations/764-1.09_Johnson_20210302_LuNaMaps_LVS_v0.pdf). The NavFilter is Curiosity-derived (DIMU + TDS). **[AO]** [NTRS 20230005661](https://ntrs.nasa.gov/citations/20230005661)

### Inferences
- The FF13/FF14 HRN divergence came from a closed loop between the navigation estimate and sensor pointing that ran on stale state. It slipped through simulation because the simulated processor delay was synthetic. Any TRN design that steers or crops using the nav state needs latency-faithful HWIL testing.

### Gaps
- I did not obtain how the M2020 LVS↔NavFilter "synchronization" works (one-time position reset versus continuous update), or its error-budget term.
