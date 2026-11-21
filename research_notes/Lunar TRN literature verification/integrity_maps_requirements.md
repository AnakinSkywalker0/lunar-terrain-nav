# Navigation integrity, lunar south-pole map accuracy, lighting, and landing requirements (verification notes, 2026-10-29)

Labels: **VERIFIED-PRIMARY** = read in the primary document (full text or official product page). **ABSTRACT-ONLY** = read only from an abstract, NTRS record or search snippet of a primary source. **UNVERIFIED** = secondary or aggregator source, or background knowledge not confirmed this session. **LOCAL-DATA** = measured read-only from files in D:\newprj\data.

## (a) How integrity / fault detection is done or proposed for TRN and lunar navigation

### Takeaway
The only TRN-specific integrity method verified here, NASA SPLICE's PITFAL (Adams et al., SciTech 2025), is a simple per-beam chi-square consensus test on four NDL apparent altitudes. It uses a 1-DOF, 99% gate (6.635) and inflates the noise of flagged measurements instead of rejecting them. It is fault detection and down-weighting, not RAIM/ARAIM with protection levels, and the paper reports no detection or false-alarm statistics. Lunar PNT integrity (LunaNet/LANS) is still being defined, and I found no published TRN protection-level requirement.

### Cited Findings
**PITFAL paper: full text read (VERIFIED-PRIMARY).** Adams, Ward, Smith, Pedrotty, Mendeck, "Topographic Slant Range Modeling and Fault Detection for Precision Planetary Landing," AIAA SciTech 2025 (Orlando, 6–10 Jan 2025), NTRS 20240014100. Record: [NTRS](https://ntrs.nasa.gov/citations/20240014100); PDF: [NTRS PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)
- PITFAL stands for "probabilistic inspection of topographic filter altitude likelihood." It is designed for multi-beam slant-range sensors such as the Navigation Doppler Lidar (NDL). It performs "a consensus check on the set of apparent altitudes computed for each individual beam." — VERIFIED-PRIMARY [NTRS PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)
- **Method.** Apparent altitude per beam: a_i = ρ_i cos θ_i, where ρ_i is the topographic range solution and θ_i is the beam incidence angle from nadir. Fault vector: ã = S·a, where S = (1/m)[(m−1) on the diagonal, −1 off the diagonal] and m ≥ 3; the paper uses 4 beams. The method is rooted in the redundant-IMU FDI work of Zanetti et al. (2014) and Sturza (1988, "Navigation System Integrity Monitoring Using Redundant Measurements"). Covariance: A = S·diag(σ²_alt)·Sᵀ, where σ²_alt is "the altitude variance of the underlying DEM" (stated as a design choice). Test: a value is an inlier if ã_i²/A_ii < χ_limit, with χ_limit = 6.635 (1 DOF, 99%). A flagged measurement has its noise variance inflated "such that the estimate would no longer fail the Mahalanobis distance check." It is not discarded. — VERIFIED-PRIMARY [same PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)
- **Purpose.** PITFAL flags cases where the pose estimate puts a beam intersection on "topographically distinct" terrain, such as a crater or ridge. These cases would otherwise drive over-convergent updates and wrong bias estimates. In the paper's example run, beam 4 is flagged while crossing a crater and a ridge (Fig. 17). — VERIFIED-PRIMARY [same PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)
- **Measurement model.** The site-relative topographic slant-range model avoids surface-normal approximation. Range is computed from the estimated landing site plus the DEM-origin offset plus the DEM intersection point, so ∂ρ/∂r_slr = −k and ∂ρ/∂r_ls = +k. Beam–DEM intersection uses a coarse ray trace against the DEM extents, then an expanding-radius fine cell search. If the beam misses the DEM, the model can fall back to the ellipsoid. — VERIFIED-PRIMARY [same PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)
- **Simulation setup (SPLICE).**
  - Closed-loop lunar lander simulation built on NASA Trick and JSC JEOD. Truth gravity is LP150Q degree/order 8 plus Earth and Sun third-body effects. The filter uses spherical gravity and no COG migration, which is deliberate unmodeled error.
  - Guidance: Apollo-style powered descent guidance, then dual-quaternion guidance after PDI.
  - Target site: lat −89.9°, lon 0°, approached from a N→S polar orbit.
  - Start: approach-phase transition, about 6 min before landing. End: **terminal descent at 30 m AGL.** The simulation does not model touchdown.
  - Initial 1σ uncertainties: 30 m position, 3 m/s velocity, 0.5° attitude; landing-site uncertainty 1 m.
  - Sensors: IMU, TRN camera (1 Hz until camera GSD exceeds map GSD), NDL (20 Hz, processed at 5 Hz, valid 30 m–5 km) and Goddard HDL (map acquired from MET+350 s; divert after 4 s of processing). NDL range noise variance is 2% of range; LOS Doppler noise is 0.1 m/s.
  - Reference map: a **10 km × 10 km patch of the PGDA "NPA" 5 m/px LOLA DEM** (product 78), cited at a median RMS elevation error of 0.3–0.5 m.
  - **1000 Monte Carlo runs.** — VERIFIED-PRIMARY [same PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)
- **Results (qualitative only).**
  - Absolute plot values are omitted "for export control considerations." Relative errors are shown normalized by unpublished project KPPs.
  - With the topographic model, the filter is consistent: errors stay inside ±3σ. Terminal-descent landing-site-relative position and velocity errors fall inside the KPP circles.
  - With the ellipsoidal model, states diverge outside 3σ once NDL processing starts, because NDL bias states are misestimated.
  - **No PITFAL detection rate, false-alarm rate or missed-detection statistics are reported.** The abstract mentions "terrestrial and lunar" simulations, but only lunar results are shown. — VERIFIED-PRIMARY [same PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)
- **Stated landing goal.** The SPLICE navigation system supports "a precision landing maneuver ... within 50 meters of the intended landing site." The total GN&C error budget at terminal descent must not exceed 50 m. — VERIFIED-PRIMARY [same PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)

**Other TRN fault-detection and active-TRN work**
- NASA JSC's Active TRN (CIF project, D. Adams, 9 Apr 2025) uses RANSAC and "geometric invariant logic" for outlier rejection in lidar-DEM keypoint matching. Reported mean keypoint localization error is 0.07 m (high-gradient) and 0.28 m (ZMGM). Reported pose error is 0.027 m / 0.03° and 0.257 m / 0.07°, against goals of <1 m and <1°. Tests used synthetic and SPLICE-sim DEMs plus Aeva lidar hardware-in-the-loop in the JSC SENSS lab. — VERIFIED-PRIMARY (slides) [NTRS 20250003778](https://ntrs.nasa.gov/api/citations/20250003778/downloads/JSC_CIF_ATRN_Overview.pdf)
- A Stanford ARL paper, "A Robust Framework for Failure Detection and Recovery for Terrain-Relative Navigation," exists. Its content was not read. — UNVERIFIED (title only) [Stanford ARL](https://web.stanford.edu/group/arl/publications/robust-framework-failure-detection-and-recovery-terrain-relative-navigation)

**Lunar PNT integrity (LunaNet/LANS)**
- One source gives the LANS requirement as 40 m (95%) position and 10 mm/s (95%) velocity. — UNVERIFIED (search summary; primary LNIS document not read) [UNOOSA ICG Lunar PNT Jun 2024](https://www.unoosa.org/documents/pdf/icg/2024/WG-B_Lunar_PNT_Jun24/LunarPNT_Jun24_01_01.pdf)
- A Cislunar 2026 workshop deck on integrity monitoring for LCNS users reportedly concludes that filtered approaches combined with LunaNet or lunar ranging could meet lander integrity bounds, while GNSS adds little because of geometry. — UNVERIFIED (search snippet) [IOAG Cislunar 2026](https://ioag.org/Cislunar2026/Thursday/06a%20Lunar%20PNT%20UserTest%20Equipment%20&%20Technology%20%E2%80%93%20Part%201/1625%20CLPNT_Integrity_monitoring_strategies_for_LCNS_users.pdf)
- LANS providers must meet a common signal structure and Signal-in-Space Error requirements. — ABSTRACT-ONLY [NASA LunaNet/LCRNS slides, Mar 2025](https://ntrs.nasa.gov/api/citations/20250002120/downloads/LunaNet%20%20and%20NASA%20LCRNS%20-MGAconf%205Mar2025.pdf)

### Inferences
- PITFAL is a **local consistency check on redundant ranges**: chi-square with 1 DOF per beam on a mean-removed vector. It is not a RAIM/ARAIM protection-level computation. It bounds no position error and produces no HPL/VPL. A simulation study that uses "chi-square innovation gating" as integrity monitoring sits at roughly the PITFAL level of sophistication. Calling it "integrity" in the aviation (ARAIM) sense would overstate it.
- PITFAL sets σ_alt from the DEM's altitude variance. A natural analogue for this project is the PGDA `toterr` layer, a per-pixel RMS Z error of about 0.37 m median at Site01.
- PITFAL publishes no detection-performance numbers. A study that reports missed-detection and false-alarm rates against injected map faults would add something the NASA paper does not provide.
- SPLICE's simulation ends at 30 m AGL. Touchdown-velocity success criteria are therefore outside what this NASA work validates.

### Gaps
- I found no published RAIM/ARAIM protection-level formulation applied specifically to lunar TRN. LunaNet integrity parameters (LNIS v5) were not read.
- ESA/NASA lander FDIR documents (for example, PILOT for the Argonaut/ESA lunar lander, or Astrobotic or IM FDIR papers) were not retrieved in this session.
- The Stanford TRN failure-recovery paper was not read.

## (b) How accurate the onboard maps actually are (LOLA / PGDA DEMs, horizontal shifts, toterr)

### Takeaway
PGDA's 5 m/px south-pole site DEMs (Barker et al. 2021, PSS 203:105119) have adjusted LOLA track geolocation of about 10–20 cm horizontally and about 2–4 cm vertically. Typical per-pixel RMS height uncertainty is 0.30–0.50 m. `toterr` is the per-pixel **vertical (Z) RMS error** across 100 Monte Carlo "clones," combining orbital and interpolation error. It contains no horizontal error. Realistic horizontal misregistration for these LOLA products is decimeters to a few meters, not kilometers.

### Cited Findings
- **Product page (PGDA 78).** "High-Resolution LOLA Topography for Lunar South Pole Sites" (M. K. Barker). 5 m/px GeoTIFFs in south polar stereographic X/Y metres, MOON_ME frame of DE421. Files are named `SiteNN_final_adj_5mpp_<suffix>.tif`:
  - `_surf`: surface-interpolated height Z (m)
  - `_ldec`: LOLA spot count per pixel
  - `_slp`: slope (deg)
  - `_toterr`: "Total Z uncertainty in meters (formally, the RMS error)"
  - `_slperr`: slope uncertainty
  - 100 clone files
  - `final_adj.xyzi`: "final point clouds after track adjustments and cleaning"

  Sites include Site01 "Connecting ridge," Site04 "Shackleton rim," Site06/07/11/20/23/42, NPA–NPD, DM1/DM2, LM1–LM8 and others. — VERIFIED-PRIMARY [PGDA product 78](https://pgda.gsfc.nasa.gov/products/78); [README](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/README)
- The README also states that X/Y follow the GMT "pixel-registered" convention, and it cites Barker et al. 2021, PSS 203, 105119, [doi:10.1016/j.pss.2020.105119](https://doi.org/10.1016/j.pss.2020.105119). — VERIFIED-PRIMARY [README](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/README)
- **Barker et al. 2021, full text read (VERIFIED-PRIMARY).** Source: [NTRS PDF](https://ntrs.nasa.gov/api/citations/20205009660/downloads/Mike%20Barker_%20Paper_%20Improved%20Lola.pdf)
  - The original paper covers 4 sites (1, 4, 7, 11) in 16 × 16 km regions. Site 4 also contains Site 8 of Mazarico et al. (2011). Data run through Sep 2013.
  - LOLA geometry from 50 km altitude: 12 m cross-track and 57 m along-track spacing, 5 m spots. LOLA range precision of about 10 cm "sets an absolute floor" on the vertical geolocation of any single return.
  - Iteratively co-adjusting tracks reduced orbital geolocation errors "by over a factor of 10." After 5 iterations, uncertainty is under about 12–14 cm horizontally and about 2 cm vertically for about 68% of tracks. Formal covariance gives about 10–20 cm horizontally and about 2–4 cm vertically. The authors state that this geolocation uncertainty "applies to total absolute position" and is distinct from surface-height uncertainty.
  - The MOON_ME/DE421 frame orientation "has an overall uncertainty of a few meters" relative to the principal-axis frame.
  - About 90% of 5 m pixels are interpolated. The height error map is "dominated as a whole by interpolation error."
  - Uncertainty comes from 100 clones built on fractal terrain. Each clone has synthetic tracks perturbed by each track's error covariance plus 10 cm range noise, then is re-gridded and interpolated. The RMS over the 100 clones per pixel is the total Z error.
  - Site 1 statistics: median RMS Z error 0.37 m (MAD 0.15 m); about 1% of pixels exceed 1 m; about 0.025% exceed 2 m; maximum 5.65 m. Median slope error is 1.90°, about 1% of pixels exceed 4°, and the maximum is 21°.
  - Height errors propagate into horizon elevation and predicted illumination.
- **LRO orbit accuracy before adjustment.** Mazarico et al. reported LRO positions better than about 20 m (2012), against a 50 m mission requirement. Post-GRAIL gravity improved radio-only reconstruction to under about 10 m. Separately, the FDF operational requirement is 500 m total and 18 m radial RMS. — ABSTRACT-ONLY / search summaries [Mazarico et al. "Status after seven years" (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6417890); [Slojkowski ISSFD 2014](https://www.issfd.org/ISSFD_2014/ISSFD24_Paper_S5-4_slojkowski.pdf)
- **Newer product.** Barker et al. 2023, PSJ 4:183 ("A New View of the Lunar South Pole from LOLA"), offers 10–240 m/px products to 60°S with `ADJ_ERR` height-error layers and PSR maps. Data DOI: 10.60903/gsfcpgda-lola-spole. The page gives no numeric accuracy. — VERIFIED-PRIMARY (product page) [PGDA product 90](https://pgda.gsfc.nasa.gov/products/90); [doi:10.3847/PSJ/acf3e1](https://doi.org/10.3847/PSJ/acf3e1)
- **Map accuracy limits navigation.** Restrepo et al. (SciTech 2022), "Building Lunar Maps for TRN and Hazard Detection," makes the point that position estimates can only be as accurate as the reference map. — ABSTRACT-ONLY [doi:10.2514/6.2022-0356](https://doi.org/10.2514/6.2022-0356); [LuNaMaps NTRS](https://ntrs.nasa.gov/api/citations/20210024816/downloads/LuNaMaps_Scitech2022_Nov19.pdf)
- **Image-based polar maps.** LRO NAC images at the pole have roughly half the nominal 0.5 m/px resolution because of low sun. LuNaMaps sums images, giving about 2× coarser resolution than nominal. — ABSTRACT-ONLY (search snippet) [LuNaMaps NTRS](https://ntrs.nasa.gov/api/citations/20210024816/downloads/LuNaMaps_Scitech2022_Nov19.pdf)

**Local data check (LOCAL-DATA, read-only, tifffile/numpy)**
- `Site01_final_adj_5mpp_surf.tif` and `_toterr.tif`:
  - 3200 × 3200 px, float32, 5.0 m pixel scale, so 16 × 16 km.
  - Upper-left tie point X = −19000, Y = −4000 m, giving X ∈ [−19000, −3000] and Y ∈ [−20000, −4000].
  - NaN nodata, no NaNs present. The GeoTIFF GeoKeys hold an "unnamed ellipse / unknown datum," so the CRS is not fully embedded. Frame and projection come from the README.
  - Surf heights range from −523 m to 1959 m.
- **Site01 `toterr`:** min 0.062 m, median 0.372 m, mean 0.405 m, p95 0.731 m, p99 0.991 m, max 5.583 m. 23.6% of pixels exceed 0.5 m, 0.95% exceed 1 m, 0.03% exceed 2 m. This matches Barker et al. 2021 Fig. 12 for Site 1 (median 0.37 m, about 1% above 1 m, about 0.025% above 2 m). Barker reports a maximum of 5.65 m against 5.58 m locally, a small difference of unknown cause (possibly a product version or extent difference).
- `Site04_final_adj_5mpp_surf.tif`: 3200 × 3200, 5 m, tie point X = −9000, Y = 1000. Heights range from −2848 to 1805 m; Site04 includes the Shackleton interior.
- **`Site04_final_adj_5mpp_slp.tif` is truncated or corrupt.** File size is 30,509,336 bytes, but its strip table ends at 40,980,772 bytes. tifffile fails with "failed to read 40960000 bytes, got 30488564." Any slope statistics or slope-based landing-site masks from this file are suspect. It should be re-downloaded from PGDA product 78.

### Inferences
- `toterr` is a **vertical-only** (Z) per-pixel 1σ-like RMS uncertainty. It is not a horizontal registration error. A simulation map-error model that uses `toterr` to scale vertical noise is consistent with the product. Using it to justify horizontal map shifts is not.
- Per Barker 2021, realistic horizontal registration error for these LOLA site DEMs is on the order of **0.1–0.2 m** for track geolocation, plus **a few meters** of frame-orientation uncertainty relative to the principal-axis frame. Unadjusted LOLA products or LRO orbits alone would be about 10–20 m (inference from the Mazarico figures). A simulated horizontal map shift of a few meters to about 20 m is realistic-to-conservative for LOLA-derived maps. **A km-scale shift is not realistic** for these products. It would only represent a gross fault such as a wrong tile or datum, or a mis-specified landing site.
- Because about 90% of pixels are interpolated, errors are spatially correlated at scales of LOLA track gaps (tens of meters). Independent per-pixel white noise scaled by `toterr` would understate correlated error. A clone-based or correlated-field error model is closer to the product's own definition.

### Gaps
- LROC NAC DTM accuracy was not verified this session. Background knowledge (Henriksen et al. 2017, Icarus) suggests NAC DTMs at about 2–5 m/px with meter-level vertical precision, controlled to LOLA. — UNVERIFIED
- I found no peer-reviewed absolute (inertial or ME-frame) horizontal accuracy statement for Barker 2023 polar mosaics.
- Exact LOLA RDR geodetic accuracy wording (Mazarico et al. 2012, 2018) was not read in full.

## (c) South-pole lighting and its effect on camera TRN

### Takeaway
At the south pole the Sun and Earth rise only about 2–7° above the horizon. Shadows are long and change constantly, and PSRs get no direct sunlight. NASA's own presentations state that passive camera TRN is impractical for permanently shadowed or poorly mapped regions, which motivates active lidar TRN. I found no published quantitative failure rate for camera TRN in shadow.

### Cited Findings
- NASA HLS overview (A. Dwyer Cianciolo, LaRC, Aug 2024; reused by L. Ortiz, Oct 2025): at the south pole the "Sun and Earth only rise above the horizon ~2 to 7 deg," the "Sun casts long shadows," and the terminator "is not smooth." Artemis III requirements include surface lighting and approach lighting. — VERIFIED-PRIMARY [NTRS 20250009323](https://ntrs.nasa.gov/api/citations/20250009323/downloads/ArtemisOverview2025IntSPAPPSChallenge.pdf?attachment=true)
- NASA JSC ATRN (Adams, Apr 2025): "Passive (camera-based) approaches are impractical for permanently shadowed or poorly mapped regions." Active 3D mapping sensors are needed. Map-based 3D feature methods face "Non-uniqueness in the presence of homogonous terrain" and feature-extraction failure where topographic contrast is low. — VERIFIED-PRIMARY [NTRS 20250003778](https://ntrs.nasa.gov/api/citations/20250003778/downloads/JSC_CIF_ATRN_Overview.pdf)
- Barker et al. 2021: "laser altimeters are not hindered by shadows." This is why LOLA maps are the polar topographic reference. — VERIFIED-PRIMARY [NTRS PDF](https://ntrs.nasa.gov/api/citations/20205009660/downloads/Mike%20Barker_%20Paper_%20Improved%20Lola.pdf)
- The SPLICE camera TRN runs only until camera GSD exceeds reference-map GSD. Lidar (NDL and HDL) carries the final approach. — VERIFIED-PRIMARY [PITFAL PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)
- ShadowCam on KPLO/Danuri: designed for more than 200× the sensitivity of the LROC NAC, about 1.7 m/px, and saturates on sunlit terrain. — UNVERIFIED-secondary (mission site and factsheet seen only via search) [ShadowCam about](https://www.shadowcam.asu.edu/about); [factsheet](https://www.shadowcam.asu.edu/assets/shadowcam_factsheet-18b6acd8e4c34699dc380c7bbe9b64111ff572963ae16cc6381ddbd20b200b73.pdf)
- Polar visual field: lunar obliquity about 1.54° gives solar elevations "often <<10°," with "dim lights and long, dynamic shadows." — ABSTRACT-ONLY [arXiv 2506.22956](https://arxiv.org/html/2506.22956v1)
- SLIM-related work notes that crater-based navigation may not find enough craters at the pole, where solar altitude is low. — UNVERIFIED (search summary) [J-STAGE JSPRS 60(1)](https://www.jstage.jst.go.jp/browse/jsprs/60/1/_contents/-char/ja)

### Inferences
- A simulation that uses camera TRN at the south pole should vary sun azimuth and elevation (about 0–7°) and include shadow-induced matching failures. Otherwise it may overstate camera TRN availability. A lidar or DEM-correlation TRN study matches NASA's stated direction (ATRN, SPLICE) more closely.
- Height errors in the map (`toterr`) change predicted shadow edges (Barker 2021). This matters for any image-rendering-based TRN reference.

### Gaps
- No quantitative study of camera-TRN match-failure rate versus sun elevation was retrieved.
- ShadowCam-based TRN map products and their accuracy were not found.

## (d) Real precision-landing and touchdown requirements; is "miss <10 m, vertical <2 m/s, horizontal <1 m/s" realistic?

### Takeaway
- **Accuracy.** Artemis III HLS must land within 100 m of a target. From Artemis IV, the requirement is 50 m under any lighting. SPLICE also designs to a 50 m GN&C budget. The demonstrated south-pole state of the art is about 250 m (IM-2), and SLIM achieved about 10 m navigation accuracy at an equatorial site. A <10 m miss is therefore **about 5–10× stricter** than current NASA requirements.
- **Velocity.** Apollo LM limits were Vv ≤ 10 ft/s (3.05 m/s) and Vh ≤ 4 ft/s (1.22 m/s) for Vv ≤ 7 ft/s, tapering at higher Vv. A <2 m/s vertical and <1 m/s horizontal criterion is inside the LM envelope, so it is **moderately conservative** by Apollo standards. However, IM-1 tipped over at about 2.7 m/s vertical and about 0.9 m/s lateral against a ~0.9 m/s planned vertical. For small CLPS-class landers the horizontal criterion is therefore **lax**.

### Cited Findings
**Landing accuracy requirements**
- "Key Artemis III Landing Requirements":
  1. Land within 6° latitude of the pole.
  2. Surface slope for landing (100 m) <10°.
  3. EVA slope (2 km) <20°.
  4. Direct-with-Earth communications.
  5. Surface and approach lighting.
  6. "Land within 100 m of a target." The slide also shows "Human Landing Accuracy Requirements 100 m x 100 m."

  — VERIFIED-PRIMARY (NASA presentation, not a requirements document) [NTRS 20250009323](https://ntrs.nasa.gov/api/citations/20250009323/downloads/ArtemisOverview2025IntSPAPPSChallenge.pdf?attachment=true)
- "Beginning with Artemis 4, HLS has a requirement to land within 50m of targeted landing site under any lighting condition." The slide lists the state of the art as: Mars 7–8 km (Perseverance); Moon equatorial <60 m (SLIM); Moon south pole 250 m (IM-2). — VERIFIED-PRIMARY (NASA JSC slides) [NTRS 20250003778](https://ntrs.nasa.gov/api/citations/20250003778/downloads/JSC_CIF_ATRN_Overview.pdf)
- Wueller et al. (JGR Planets 2026) cite "100 m (3σ)" accuracy and an 8° slope limit for site analyses. — ABSTRACT-ONLY [doi:10.1029/2025JE009434](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2025JE009434). The 3σ qualifier did not appear in the NASA slides I read, so the statistical definition of "within 100 m" is unconfirmed.
- SPLICE goal: landing within 50 m of the intended site, with the total GN&C budget at terminal descent ≤50 m. — VERIFIED-PRIMARY [PITFAL PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)
- JAXA SLIM accuracy depends on definition. JAXA evaluated navigation accuracy at "~10 m or better" from images at about 50 m altitude. The final touchdown was about 55 m from the target after an engine anomaly and hazard avoidance, and the project manager estimated 3–4 m. — UNVERIFIED-secondary / ABSTRACT-ONLY (JAXA briefing seen only via search) [JAXA briefing 2024-12-26](https://www.isas.jaxa.jp/en/topics/files/SLIM-press-briefing-20241226.pdf); [Space.com](https://space.com/japan-slim-moon-precise-landing)
- CLPS: no task-order landing-accuracy requirement was found. CLPS deliveries are provider missions, and requirements sit in each task order's RFTOP. — VERIFIED-PRIMARY for program structure [NASA CLPS](https://www.nasa.gov/reference/commercial-lunar-payload-services/). No specific number was found.

**Touchdown velocity limits**
- **Apollo LM (NASA TN D-6850, Rogers, Apollo Experience Report: LM Landing Gear Subsystem; full text read, OCR):**
  - The initial envelope was 10 ft/s vertical and 5 ft/s horizontal. It was reduced to 4 ft/s horizontal, then further reduced to "for Vv ≤ 7 ft/sec, Vh = 4 ft/sec; and, for 7 ≤ Vv ≤ 10 ft/sec," with Vh tapering linearly. The OCR of the taper formula is garbled; it appears to reach 0 at 10 ft/s, which should be checked against Fig. 10.
  - Final touchdown specification: tilt ≤ 6° from local vertical and angular rate < 2 deg/s.
  - Design surface: mean slope ≤ 6° and effective slope ≤ 12°. P(stable landing on ≤12° slope) = 0.998.
  - The envelope was accepted if P(touchdown within envelope) > 0.9974, "the 3σ probability for a single, normally distributed random variable."
  - Apollo 11 touched down with about 2.1 ft/s and 1.7 ft/s horizontal components and negligible vertical-axis (Z) motion.

  — VERIFIED-PRIMARY [TN D-6850 (ALSJ)](https://apollojournals.org/alsj//tnD6850LMLandingGearSubsytem.pdf)
- Conversion: 10 ft/s = 3.05 m/s; 7 ft/s = 2.13 m/s; 4 ft/s = 1.22 m/s. This is arithmetic, not a sourced figure.
- **IM-1 Odysseus (Feb 2024).** IM briefings, as reported in the press, said the planned touchdown was about 2 mph vertical with no horizontal motion. The actual was about 6 mph vertical and 2 mph horizontal, roughly 2.7 m/s and 0.9 m/s. The legs were "loaded beyond their rating," the lander was on about a 12° slope, caught a foot, and tipped. The cause was laser rangefinders disabled by a safety switch that was not flipped. — UNVERIFIED-secondary (press via search; no IM primary document read) [SpaceNews](https://spacenews.com/?p=349475); [Space.com](https://www.space.com/intuitive-machines-odysseus-moon-lander-tipped-over); [TechCrunch](https://techcrunch.com/2024/02/23/quick-thinking-and-a-stroke-of-luck-averted-a-moon-lander-disaster-for-intuitive-machines)
- HLS slope limit for landing is <10° over 100 m. — VERIFIED-PRIMARY [NTRS 20250009323](https://ntrs.nasa.gov/api/citations/20250009323/downloads/ArtemisOverview2025IntSPAPPSChallenge.pdf?attachment=true). No HLS touchdown velocity numbers were found in public sources.

**V&V and Monte Carlo practice**
- NASA-STD-7009B ("Standard for Models and Simulations") was approved 5 Mar 2024 and supersedes 7009A w/Change 1. It defines a Credibility Assessment Scale that assesses M&S results and process rigor against key factors; 8 factors in the original version. — ABSTRACT-ONLY [standards.nasa.gov](https://standards.nasa.gov/node/263); [7009B PDF](https://standards.nasa.gov/sites/default/files/standards/NASA/B/1/NASA-STD-7009B-Final-3-5-2024.pdf) (not read in full)
- Run counts seen in practice:
  - SPLICE/PITFAL validation: 1000 MC runs. — VERIFIED-PRIMARY [PITFAL PDF](https://ntrs.nasa.gov/api/citations/20240014100/downloads/Topo_Slant_Range_%20Modeling_SciTech25.pdf)
  - X-33: 1000 runs; Genesis: 2000 dispersed entry states. — ABSTRACT-ONLY (search snippets of NTRS docs) [NTRS 20000010426](https://ntrs.nasa.gov/citations/20000010426)
  - The LM touchdown envelope criterion was P > 0.9974 (3σ). — VERIFIED-PRIMARY [TN D-6850](https://apollojournals.org/alsj//tnD6850LMLandingGearSubsytem.pdf)

### Inferences
- **Miss < 10 m.** This is strict: 10× tighter than Artemis III (100 m), 5× tighter than Artemis IV and SPLICE (50 m), and about 25× tighter than demonstrated south-pole performance (IM-2, about 250 m). It matches SLIM's best-case navigation accuracy at a well-lit equatorial site. A simulation that achieves <10 m should note that the result is far beyond requirements. If it fails at 10 m, it can still pass at 50 or 100 m, so results should be reported at all three thresholds.
- **Vertical < 2 m/s.** This sits inside the LM limit (3.05 m/s) and just below the LM's 7 ft/s (2.13 m/s) knee. It is reasonable to moderately conservative for a crewed-class gear. It is about 2× IM-1's planned value (about 0.9 m/s), and IM-1's about 2.7 m/s overloaded its legs. For small CLPS-class landers, 2 m/s may be near or above gear limits (inference; no IM spec found).
- **Horizontal < 1 m/s.** This is slightly inside the LM's 1.22 m/s. IM-1 tipped at about 0.9 m/s lateral on a 12° slope, with zero planned. For tall, narrow commercial landers this criterion is **lax**; ≤0.5 m/s or a tip-over check against slope would be more defensible (inference).
- A pass/fail criterion should be stated as a probability, for example ≥99.73% of MC runs within limits, following the LM 0.9974 precedent. A single-run or mean criterion is weaker. The run count should support the claimed probability: about 1000+ runs to say anything near 3σ (inference consistent with SPLICE's 1000).
- Slope matters as much as velocity. HLS uses <10° at 100 m, and the LM was designed for ≤12° effective slope. The truncated Site04 slope file (see b) directly affects any slope-based touchdown evaluation.

### Gaps
- No primary HLS requirements document (for example, the HLS-RQMT/SRD) or OIG report text giving the statistical definition of "within 100 m" was read. No public HLS touchdown-velocity numbers were found.
- No CLPS task-order landing-accuracy or touchdown-velocity requirement was found. No IM Nova-C or ispace published gear limits were found; the IM-1 figures are press-reported (mph) only.
- No IM-2 accuracy primary source was read; the 250 m figure comes from NASA JSC slides.
- The NASA-STD-7009B full text and any NASA EDL Monte Carlo run-count guidance (for example, a NASA GN&C or EDL handbook) were not read. Background knowledge says 7009 does not mandate run counts (UNVERIFIED).
