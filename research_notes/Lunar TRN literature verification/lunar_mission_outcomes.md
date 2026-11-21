# Lunar landing missions 2013-2026: descent navigation sensors, outcomes, official causes, and sensor-trust lessons

Research date: 2026-10-29. Claim labels:
- **VERIFIED-PRIMARY**: read this session in an official/primary document (agency or company release, NASA/JAXA technical report, peer-reviewed paper).
- **SECONDARY**: read this session in reputable reporting (SpacePolicyOnline, SpaceNews, Spaceflight Now, Space.com, etc.) that attributes the claim to an official briefing or document, but the primary text itself was not read.
- **UNVERIFIED**: from the researcher's prior knowledge, or single weak source; not confirmed this session. Do not cite without checking.

Method note: ispace's own PDFs (ispace-inc.com, 2022.ispace-inc.com) returned HTTP 403 / DNS failure this session, so ispace findings are SECONDARY via reporting that quotes the releases. The NASA TM on IM-1 NDL was retrieved and read in full (VERIFIED-PRIMARY).

Sensor-trust failure-mode taxonomy used below: **(A) rejecting a good sensor**, **(B) trusting a bad sensor / bad data not detected**, **(C) map/terrain-model mismatch**, **(D) lighting**, **(E) single-point failure / no dissimilar redundancy**, **(F) sensor never available (configuration/integration error)**.

---

## ispace HAKUTO-R Mission 1 (landing attempt 25 April 2023, Atlas crater): official root cause

### Takeaway
The lander's onboard software rejected *valid* laser rangefinder (LRF) data as faulty when the measured altitude jumped as the lander crossed the rim of Atlas crater; the navigation altitude estimate drifted to ~zero while the lander was really ~5 km up, and it hovered/descended slowly until propellant ran out and it fell. ispace attributes this to software requirements, a late landing-site change, and simulations that did not adequately model the terrain on the new route. This is the canonical case of **failure mode (A) rejecting a good sensor**, driven by **(C) terrain-model mismatch** in the fault-detection logic, with **(E) no dissimilar altitude source** to arbitrate.

### Cited Findings
- SECONDARY: The onboard software discarded valid LRF data after the lander passed over the rim of Atlas crater; it was not programmed to expect that change and treated the instrument as malfunctioning; the filter that rejects abrupt altitude jumps (meant to protect against sensor faults) rejected the rim-crossing readings — [SpaceNews (LRO crash site article)](https://spacenews.com/?p=159890); [Interesting Engineering](https://interestingengineering.com/science/japans-lander-confused-by-a-crater-on-the-moon)
- SECONDARY (quoting ispace 26 May 2023 release): the lander was later determined to be at approximately **5 km** altitude when its estimate indicated it had landed; it continued slow deceleration and ran out of propellant, then free-fell — [ispace release PDF, 26 May 2023](https://ispace-inc.com/wp-content/uploads/2023/05/EN_ispace_release_20230506_Final-Results.pdf) (403 this session; content relayed via search snippet and [EEVblog repost of the release](https://www.eevblog.com/forum/chat/japans-ispace-reveals-hakuto-r-mission-1-lunar-landing-crash-results/msg4884809/))
- Number conflict: SpaceNews describes the *measured altitude jump* at the rim as about **3 km**; other outlets describe a ~**5 km** difference between estimated and true altitude. These are two different quantities (rim-step in the LRF reading vs. accumulated estimate error at "touchdown") and both can be true — [SpaceNews](https://spacenews.com/?p=159890); [Interesting Engineering](https://interestingengineering.com/science/japans-lander-confused-by-a-crater-on-the-moon)
- SECONDARY: Official cause framed as software; prior landing-sequence simulations did not adequately incorporate the lunar environment along the navigation route — [Interesting Engineering](https://interestingengineering.com/science/japans-lander-confused-by-a-crater-on-the-moon); [ispace release PDF](https://ispace-inc.com/wp-content/uploads/2023/05/EN_ispace_release_20230506_Final-Results.pdf)
- SECONDARY: The decision to target Atlas crater was made after the lander's critical design review, months before the Dec 2022 launch; ispace (CTO Ryo Ujiie) accepted responsibility, tying the failure to requirements ispace levied on the software (developed by Draper) — [SpaceNews](https://spacenews.com/?p=159890)
- SECONDARY: ispace later said the software fixes made after Mission 1 were successful on Mission 2 (Mission 2 crash cause was hardware, not the M1 software logic) — [SpacePolicyOnline, June 2025](https://spacepolicyonline.com/news/hardware-failure-doomed-ispaces-mission-2/)
- UNVERIFIED: the landing-site change date (often cited as February 2021) and the specific software change list (relaxed/terrain-aware LRF rejection thresholds; expanded simulation with site-specific DEMs).

### Inferences
- The innovation-gating / jump-rejection logic was implicitly "trained" on terrain profiles of the *original* site; a site change without re-deriving gating thresholds against the new route's DEM converted a fault-protection feature into the failure mechanism. Sensor-integrity monitors must be validated against the map they will actually fly over.
- With a single altitude-sensing modality (LRF) and IMU propagation, the system had no independent witness to decide whether the jump was a sensor fault or terrain; a DEM-predicted range profile (map-aided consistency check) or a dissimilar altimeter could have arbitrated.

### Gaps
- Exact text of ispace's 26 May 2023 release and any detailed technical paper (none found) — fetch blocked (403).
- Exact timeline altitudes (true altitude at rim crossing, time spent hovering) not confirmed this session.

---

## ispace Mission 2 "RESILIENCE" (crash 6 June 2025 JST, Mare Frigoris): LRF degradation

### Takeaway
ispace's 24 June 2025 technical cause analysis attributes the hard landing to a **hardware anomaly in the laser rangefinder**: valid LRF measurements were acquired late, so the lander could not decelerate in time. ispace narrowed the anomaly to several candidate causes, set up an external review, budgeted ~¥1.5 bn to make landing sensors more robust, and sought JAXA technical advice. The LRF was a new supplier's unit flying for the first time and there was again no dissimilar altitude sensor — failure modes **(B)/(F) a degraded sensor that did not deliver in time** plus **(E) single-point failure**.

### Cited Findings
- SECONDARY (quoting ispace 24 June 2025 release): analysis identifies an anomaly in the LRF that resulted in the hard landing and narrows down the most likely causes — [ispace M2 Technical Cause Analysis press release PDF](https://2022.ispace-inc.com/wp-content/uploads/2025/06/20250624-M2-Tech-Cause-Analysis-Press_Release.pdf) (DNS failure this session); [SpacePolicyOnline](https://spacepolicyonline.com/news/hardware-failure-doomed-ispaces-mission-2/)
- SECONDARY: June 6 briefing cited nearly vertical attitude in final phase, **delayed acquisition of valid LRF measurements**, and resulting inability to decelerate sufficiently — [Spaceflight Now](https://spaceflightnow.com/2025/06/06/ispaces-resilience-lander-crash-lands-on-the-moon/); [Payload Space](https://payloadspace.com/ispace-blames-faulty-hardware-for-failed-lunar-landing/)
- SECONDARY: ispace narrowed the fault to four possible factors (shown only in a graphic in its materials); will set up a third-party review; will seek JAXA technical advice for the next two missions; estimates ~¥1.5 bn (~$10M) to make landing-system sensors more robust and allow additional testing; no schedule delays expected — [SpacePolicyOnline](https://spacepolicyonline.com/news/hardware-failure-doomed-ispaces-mission-2/)
- SECONDARY: NASA LRO located the crash site at 60.44°N, 4.6°W, very close to the target; ispace CTO said this validated the GNC system — [SpacePolicyOnline](https://spacepolicyonline.com/news/hardware-failure-doomed-ispaces-mission-2/)
- SECONDARY: The Mission 1 LRF supplier stopped manufacturing, so the M2 LRF was a different unit flying for the first time; the lander had no visual/other sensor to determine distance to the surface — [Payload Space](https://payloadspace.com/ispace-blames-faulty-hardware-for-failed-lunar-landing/) (as summarized in search results; also [Japan Times](https://www.japantimes.co.jp/article/627733))
- SECONDARY: Mission 3 (Apex 1.0 lander, Draper-led CLPS CP-12 to Schrödinger basin) slipped from 2026 to 2027 — [SpacePolicyOnline](https://spacepolicyonline.com/news/hardware-failure-doomed-ispaces-mission-2/)
- UNVERIFIED: the four candidate factors (recalled as including LRF performance degradation due to environment/physical-condition change); final-telemetry altitude/velocity figures (recalled as roughly ~190 m altitude at ~40 m/s); outcome of the third-party review.

### Inferences
- M1 and M2 bracket the trust problem: M1 rejected a *good* LRF; M2 had a *late/degraded* LRF and nothing to fall back on. Both share the root architectural issue — a single active altitude modality with no dissimilar cross-check (radar, Doppler lidar, or vision-based altimetry/velocimetry).
- "Delayed acquisition" is an availability/latency failure, not a wrong-value failure: integrity design must include "time-to-first-valid" requirements and a fallback trajectory/guidance mode when a sensor has not locked by a gate altitude.

### Gaps
- Primary PDF text (four hypotheses, telemetry figures) not retrieved this session.
- No report found on outcome of the third-party review as of Oct 2026.

---

## Intuitive Machines IM-1 Odysseus (22 Feb 2024, near Malapert A): LRF safety enable, NDL, tilted landing

### Takeaway
Hours before descent the team discovered the lander's laser altimeter(s) were not operational (a physical safety-enable had not been switched on before launch). An in-flight software patch to ingest NASA's Navigation Doppler Lidar (NDL) **did not succeed**: per NASA's November 2025 technical memorandum, the vehicle landed **without using any NDL data**, relying on IMU + optical feature tracking only. NDL itself worked well (ranges >20 km vs 5 km expected; reconstruction agreement ~5 m / 0.5 m/s). Reconstructed speed at first ground contact was **~7.8 m/s** (total Moon-relative velocity), and the lander broke a leg and came to rest tilted. Failure modes: **(F) sensor never available (configuration error)**, **(E) no working dissimilar altimeter**, and **(A)-like integration failure — a good sensor whose data the filter could not accept**.

### Cited Findings
- VERIFIED-PRIMARY: Odysseus GN&C: IMU, optical feature-tracking instrument for TRN, and a laser altimeter feeding a Kalman filter initialized from DSN orbit determination; NDL velocity was intended as a secondary filter input — [NASA/TM-20250010290, Karlgaard et al., "Navigation Doppler Lidar Performance Assessment and Trajectory Reconstruction of the Intuitive Machines IM-1 Lunar Landing," Nov 2025](https://ntrs.nasa.gov/citations/20250010290)
- VERIFIED-PRIMARY: "A discovery was made prior to descent initiation that the laser altimeter was not operational and could not provide data to the navigation filter. Thus, the filter would rely on an IMU and optical feature tracking alone." An attempt to modify flight software to process NDL range/velocity "proved to be unsuccessful and the vehicle conducted its landing without the use of any NDL data" — [NASA/TM-20250010290](https://ntrs.nasa.gov/citations/20250010290)
- VERIFIED-PRIMARY: NDL Beam A (near-nadir) measured ranges >20 km vs expected 5 km; all three beams gave range and velocity from 23:18:20.6 UTC to touchdown at 23:23:45.0 UTC "with no dropouts or outliers" — [NASA/TM-20250010290](https://ntrs.nasa.gov/citations/20250010290)
- VERIFIED-PRIMARY: IMU+NDL Unscented Kalman Filter reconstruction agrees with measurements to ~5 m and 0.5 m/s; velocity at first ground contact **7.79 m/s (NDL-only) / 7.80 m/s (IMU/NDL)**; pitch relative to local terrain at first contact 76.83°, relative to NED 85.42° — [NASA/TM-20250010290](https://ntrs.nasa.gov/citations/20250010290)
- VERIFIED-PRIMARY: Landed near Malapert A at −80.1276°, 1.4367°E; powered descent began 23:10:32 UTC 22 Feb 2024; detailed powered-flight reconstruction in Stewart et al., "IM-1 Powered Descent Reconstruction," AAS 25-310 (Jan 2025) — [NASA/TM-20250010290](https://ntrs.nasa.gov/citations/20250010290) (AAS 25-310 itself not read)
- VERIFIED-PRIMARY (reference, not read): Hines et al., "Demonstration of Navigation Doppler Lidar Capabilities Onboard the First Commercial Lunar Lander," AIAA 2025-1115 — cited in [NASA/TM-20250010290](https://ntrs.nasa.gov/citations/20250010290); also [AAS NDL Karlgaard slides](https://ntrs.nasa.gov/citations/20250008015)
- SECONDARY: The lasers were not working because a physical safety switch was not flipped before launch; CEO said it could not be flipped in flight — [SpaceQ](https://spaceq.ca/simple-error-could-have-resulted-in-intuitive-machines-mission-failure/); [TechCrunch](https://techcrunch.com/2024/02/23/quick-thinking-and-a-stroke-of-luck-averted-a-moon-lander-disaster-for-intuitive-machines)
- SECONDARY: Planned touchdown ~1 m/s vertical with no lateral motion; came in faster and with lateral motion; a footpad likely caught, a leg (or two) broke, lander tipped — [New Atlas](https://newatlas.com/space/odysseus-broke-leg-landing); [CBS News](https://www.cbsnews.com/news/moon-lander-tipped-over-on-its-side-during-touchdown)
- Conflict: Early press (Feb 2024) widely reported that the NDL "saved" the mission / was used for landing ([BGR](https://bgr.com/science/how-a-nasa-payload-saved-the-first-u-s-moon-lander-since-apollo)); the NASA TM (Nov 2025) states no NDL data were used. A secondary report attributes the failure to a missing "data valid" flag in the patch — UNVERIFIED (not in the TM text read). **Use the NASA TM as authoritative.**
- UNVERIFIED: vertical/horizontal decomposition of the 7.8 m/s (press figures of ~3x planned descent rate and ~2 m/s lateral are from blogs/analyst estimates, e.g. [Behind the Black](https://behindtheblack.com/behind-the-black/points-of-information/odysseus-tip-over-likely-caused-because-it-landed-without-good-elevation-data)); landing distance from target (~1.5 km often cited).

### Inferences
- IM-1 is the clearest case that a *good* dissimilar sensor is worthless if the integrity architecture cannot admit it: the NDL was onboard, functioning, and accurate, but not integrated as a validated input path. Sensor trust must be designed (and tested end-to-end) before flight, including enable/arming states verified in the final flight configuration.
- Optical feature tracking + IMU without an altimeter left vertical channel weakly observable near touchdown; the 7.8 m/s contact speed is consistent with that (inference).

### Gaps
- IM's own final IM-1 report / AAS 25-310 text not read; official vertical vs horizontal touchdown velocity not confirmed.

---

## Intuitive Machines IM-2 Athena (6 March 2025, Mons Mouton region, south pole): tipped in crater

### Takeaway
Per CEO Steve Altemus (May 2025 earnings/briefing), three issues combined: (1) **laser altimeter interference/noise** that corrupted altitude readings in final descent, (2) **low-sun south-polar lighting** with long shadows degrading the optical landing system, and (3) **crater-matching tuned to LRO imagery taken from ~100 km**, which did not reflect how craters look at low altitude under polar lighting. Athena landed in a ~20 m crater and on its side. IM-3 changes: redundant *dissimilar* altimeters with more rigorous testing, a lighting-independent velocity sensor, expanded onboard crater database, IM-2 imagery for training. Failure modes: **(B) trusting corrupted altimetry**, **(D) lighting**, **(C) map/appearance mismatch**, **(E) no dissimilar altimeter**.

### Cited Findings
- SECONDARY (CEO statements, May 2025): laser altimeter interference during descent — signal noise and distortion prevented accurate altitude readings — [Spaceflight Now, 14 May 2025](https://spaceflightnow.com/2025/05/14/intuitive-machines-ceo-points-to-issues-that-prevented-upright-touchdown-during-im-2-moon-landing/); [SpacePolicyOnline](https://spacepolicyonline.com/news/im-2s-imperfect-landing-due-to-altimeter-interference-south-pole-lighting-conditions/)
- SECONDARY: south-pole low-angle lighting / long shadows challenged landing-system precision — [Space.com](https://www.space.com/astronomy/moon/heres-why-the-private-athena-lunar-lander-toppled-over-on-the-moon); [SpacePolicyOnline](https://spacepolicyonline.com/news/im-2s-imperfect-landing-due-to-altimeter-interference-south-pole-lighting-conditions/)
- SECONDARY: optical navigation relied on LRO images from ~100 km that did not account for crater appearance at lower altitude under south-pole lighting — [Spaceflight Now](https://spaceflightnow.com/2025/05/14/intuitive-machines-ceo-points-to-issues-that-prevented-upright-touchdown-during-im-2-moon-landing/)
- SECONDARY: IM-3 corrective actions: redundant and dissimilar altimeters tested more rigorously, lighting-independent velocity sensor, expanded onboard crater database, IM-2 imagery used to train algorithms — [Spaceflight Now](https://spaceflightnow.com/2025/05/14/intuitive-machines-ceo-points-to-issues-that-prevented-upright-touchdown-during-im-2-moon-landing/)
- SECONDARY: landed faster than intended and on its side in a ~20 m (65 ft) crater; could not recharge; mission declared over 7 March 2025 — [Astronomy](https://www.astronomy.com/space-exploration/intuitive-machines-im-2-moon-lander-is-lying-dead-in-a-crater/); [CBS News](https://www.cbsnews.com/amp/news/athena-moon-lander-tips-over-intuitive-machines-mission)
- UNVERIFIED: altimeter interference cause (thermal/vibration theory mentioned by one outlet as a company theory only); landing ~250 m from target; whether NDL flew on IM-2.

### Inferences
- IM-2 shows that even with a working altimeter, a noisy/corrupted range channel accepted by the filter (B) plus a TRN appearance model mismatched to altitude and sun angle (C+D) can compound. The explicit IM-3 call for a *lighting-independent velocity sensor* (likely Doppler lidar/radar — inference) is direct evidence that industry now treats lighting as a sensor-trust axis.
- "Map mismatch" here is an *appearance* mismatch (orbital imagery vs low-altitude view, sun angle), not a DEM elevation error — useful distinction for integrity modeling.

### Gaps
- No public IM final report on IM-2 found; specifics of altimeter noise (which sensor, altitude band) unconfirmed.

---

## Firefly Blue Ghost Mission 1 (2 March 2025, Mare Crisium near Mons Latreille): success

### Takeaway
Blue Ghost landed upright within ~100 m of its target using vision-based terrain-relative navigation and autonomous hazard detection/avoidance (craters, slopes, rocks), with final velocity ~1 m/s. No quantitative TRN error budget was found. Positive case: benign mare terrain and favorable lighting, with the full TRN+HDA chain working.

### Cited Findings
- SECONDARY: landed within 100 m of expected landing zone near Mons Latreille in Mare Crisium — [Sky & Telescope](https://skyandtelescope.org/astronomy-blogs/astronomy-space-david-dickinson/blue-ghost-lands-on-the-moon/); [ScienceAlert](https://www.sciencealert.com/blue-ghost-makes-history-with-perfect-moon-landing-amazing-photos)
- SECONDARY: vision-based TRN in final hour; identified craters, slopes, rocks before selecting the final hazard-free target; executed hazard-avoidance maneuvers; final velocity ~1 m/s — [Sky & Telescope](https://skyandtelescope.org/astronomy-blogs/astronomy-space-david-dickinson/blue-ghost-lands-on-the-moon/); [Kuwait Times (wire)](https://kuwaittimes.com/article/25024/technology/private-us-company-aces-lunar-landing-on-first-mission/)
- UNVERIFIED: specific sensor suite (cameras, laser/radar altimeter vendor); NASA LuGRE GNSS payload operation on the surface (payload, not lander nav).

### Inferences
- Blue Ghost and the failures differ in environment (mid-latitude mare, high sun) as much as in hardware; it does not by itself show the architecture would survive polar lighting.

### Gaps
- No Firefly technical paper on GNC/TRN accuracy found; landing accuracy figure is end-to-end, not a TRN error.

---

## JAXA SLIM (19-20 January 2024, near Shioli crater): image-based crater-matching navigation

### Takeaway
SLIM demonstrated "pinpoint" landing using vision-based (crater-matching) navigation that corrects IMU propagation. JAXA's evaluation puts navigation accuracy at about **10 m or better**, with image-matching position estimates at ~50 m altitude of **3.4 m and 10.2 m** (two sequences). One of two main engines lost its nozzle at ~50 m altitude, causing eastward drift and a touchdown ~55-60 m east of target, and the vehicle came to rest inverted (solar panels facing west). Positive case for map-matching TRN; the failure was propulsion, not navigation.

### Cited Findings
- VERIFIED-PRIMARY (JAXA documents, per search extraction): accuracy evaluated at around 10 m or better from comparison of Chandrayaan-2 and SLIM high-resolution images; image-matching at ~50 m altitude: HV2#1 3.4 m, HV2#2 10.2 m — [JAXA SLIM press briefing, 26 Dec 2024](https://www.isas.jaxa.jp/en/topics/files/SLIM-press-briefing-20241226.pdf); [JAXA doc02 20241226](https://www.jaxa.jp/projects/files/youtube/slim/jaxa_doc02_20241226.pdf)
- VERIFIED-PRIMARY (per search extraction): spacecraft drifted eastward during descent and soft-landed ~60 m east of the target site — [JAXA doc01, 25 Jan 2024](https://global.jaxa.jp/press/2024/01/file/jaxa_doc01_20240125_e.pdf)
- SECONDARY: one engine nozzle detached (visible in navigation camera imagery on the surface); thrust loss; ~55 m offset — [SpacePolicyOnline](https://spacepolicyonline.com/news/jaxas-slim-literally-lost-an-engine-and-nasas-lro-spots-slim-on-the-surface); [Space.com](https://space.com/japan-slim-moon-precise-landing)
- SECONDARY (JST): image-based navigation compares descent camera images with terrain maps, craters as landmarks — [JST Science Japan](https://sj.jst.go.jp/stories/2025/s0318-01p.html)
- UNVERIFIED: the "3-4 m before obstacle avoidance" figure as phrased in the assignment — the 3.4 m figure exists for one 50 m image-matching sequence, but the second sequence gave 10.2 m; do not report "3-4 m" as the landing accuracy. Engine-nozzle root cause: JAXA cited a shock/external factor (possibly related to propellant tank/pressure) — not confirmed this session.

### Inferences
- SLIM shows crater-matching TRN can deliver ~10 m-class accuracy in favorable lighting with a good map; it is a reference point for what TRN can achieve when map and appearance match.
- Its failure (propulsion) still produced lateral drift that nav correctly *measured* but control could not counter — separate nav integrity from control authority when attributing outcomes.

### Gaps
- Peer-reviewed SLIM navigation papers (e.g., Trans. JSASS) not retrieved this session.

---

## China Chang'e-3/4/5/6: hovering hazard avoidance with optical camera and 3D laser imaging

### Takeaway
Chang'e landers use a two-stage hazard avoidance: coarse optical-image hazard detection at higher altitude, then a **hover at ~100 m** where a **laser 3D imaging sensor** maps the site for fine obstacle avoidance, with laser ranging and microwave velocimetry plus IMU. All four landed successfully (CE-3 2013, CE-4 2019, CE-5 2020, CE-6 2024). Published accuracy figures for landing were not found this session.

### Cited Findings
- VERIFIED-PRIMARY: Chang'e-4 hovered ~13 s at ~99 m, then shifted ~12 m to avoid a 25 m crater; CE-3 and CE-4 used laser ranging, microwave velocimetry, optical imaging, and laser imaging sensors — [Nature Communications 2019 (CE-4 descent trajectory paper, PDF mirror)](https://dcmpx.remotevs.com/com/nature/www/SL/articles/s41467-019-12278-3.pdf)
- VERIFIED-PRIMARY: CE-3 obstacle-avoidance lidar calibration paper: errors in intrinsic parameters can produce a false obstacle ~1.4 m tall, which could cause poor site selection — [MDPI Sensors 2022, 22(19):7366](https://www.mdpi.com/1424-8220/22/19/7366) ([PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9570552/))
- SECONDARY (institutional): CE-4 3D imaging lidar could identify rocks/craters >15 cm from the 100 m hover point — [Tongji University](https://www.tongji.edu.cn/eng1/info/1008/3558.htm); laser 3D imaging sensor produced point cloud for obstacle recognition and safe-site selection — [SITP CAS](https://english.sitp.cas.cn/Research/rp/201905/t20190513_209559.html)
- SECONDARY: Chinese-language CE-3 GNC papers (Scientia Sinica Technologica 2014; Journal of Deep Space Exploration 2014) cited as primary sources on hazard avoidance control and autonomous navigation — reference list in [Springer, Astrodynamics (Tianwen-1 GNC)](https://link.springer.com/10.1007/s42064-021-0118-9) (not read)
- UNVERIFIED: CE-5/CE-6 sensor-level details beyond inheritance of the CE-3/4 architecture.

### Inferences
- The hover-and-image step gives an explicit, active-sensor (lighting-independent) hazard map at close range — a design pattern that would have mitigated IM-2's lighting/appearance mismatch. The 1.4 m false-obstacle calibration result shows active sensors have their own integrity mode (calibration bias → false hazards → "rejecting good sites").

### Gaps
- Published landing-accuracy numbers for Chang'e-3 to -6 not found.

---

## ISRO Chandrayaan-3 Vikram (23 August 2023) and Chandrayaan-2 Vikram (6-7 Sept 2019)

### Takeaway
Chandrayaan-3 flew a deliberately redundant, dissimilar sensor suite: Ka-band altimeter, laser altimeter, laser Doppler velocimeter (LDV), Lander Horizontal Velocity Camera (LHVC), Lander Position Detection Camera (LPDC), plus hazard detection camera. ISRO's chairman described a shift from "success-based" to "failure-based" design (assuming sensor, engine, and algorithm failures), a much larger landing zone (4 km × 2.4 km vs 500 m × 500 m), and extra propellant. ISRO has not published an official Chandrayaan-2 failure report.

### Cited Findings
- SECONDARY: sensors: Ka-band altimeter, LDV, LPDC, laser altimeter, LHVC — [Aviation Week](https://aviationweek.com/space/indias-chandrayaan-3-will-attempt-soft-lunar-landing); [Jatan Mehta](https://jatan.space/chandrayaan-3-makes-historic-touchdown/)
- SECONDARY: Ka-band altimeter's wider footprint tolerates abrupt terrain changes better than laser altimeters, which can give anomalous heights over crater rims/mountainous terrain — [Jatan Mehta](https://jatan.space/chandrayaan-3-makes-historic-touchdown/)
- SECONDARY: ISRO chairman said the LDV was not needed because descent was nominal — [Science Chronicle](https://sciencechronicle.in/2025/05/03/what-helped-vikram-lander-to-soft-land-on-the-moon/)
- SECONDARY: "failure-based design" (sensor, engine, algorithm failure considered); landing zone enlarged to 4 km × 2.4 km; extra propellant for alternate site — [Business Today](https://www.businesstoday.in/amp/latest/in-focus/story/indias-moon-mission-how-chandrayaan-3-is-better-than-chandrayaan-2-key-differences-explained-389556-2023-07-13)
- SECONDARY: Chandrayaan-2 reported cause: cumulative errors (failure analysis committee, as reported by The Hindu); thrust higher than expected during camera-coasting phase and guidance/software issues — [spacetoday.net summary](https://spacetoday.net/getarticle.php3?id=427662); [Business Today](https://www.businesstoday.in/amp/latest/in-focus/story/indias-moon-mission-how-chandrayaan-3-is-better-than-chandrayaan-2-key-differences-explained-389556-2023-07-13)
- UNVERIFIED: official ISRO Chandrayaan-2 FAC report text (not public as far as found).

### Inferences
- Chandrayaan-3 is the clearest positive example of dissimilar altimetry (Ka-band radar + laser) chosen specifically to handle the crater-rim effect that defeated ispace M1.

### Gaps
- ISRO primary publications on Chandrayaan-3 GNC/sensor performance not retrieved; Chandrayaan-2 official report not public.

---

## Luna-25 (Russia, crash 19 August 2023) and Beresheet (Israel, crash 11 April 2019)

### Takeaway
Luna-25 was **not a descent-navigation-sensor failure**: it crashed during a pre-descent orbit-lowering burn when the engine ran 127 s instead of 84 s. The Roscosmos commission's most likely cause was abnormal operation of the onboard control complex — failure to switch on the accelerometer unit in the BIUS-L angular-velocity measurement device — so the burn cutoff logic lacked the acceleration data it needed. Beresheet (2019) is commonly attributed to an IMU fault followed by a commanded reset that cascaded into main-engine shutdown (UNVERIFIED this session).

### Cited Findings
- SECONDARY (Roscosmos head Borisov, Aug 2023): engine operated 127 s instead of planned 84 s; main cause of crash — [CNN](https://amp.cnn.com/cnn/2023/08/21/world/russia-luna-25-crash-cause-engine-issue-scn); [RFE/RL](https://www.rferl.org/amp/russia-moon-spacecraft-crash-propulsion-malfunction/32557559.html)
- SECONDARY (Roscosmos statement, 3 Oct 2023): most likely cause "abnormal functioning of the on-board control complex, associated with the failure to turn on the accelerometer unit in the BIUS-L device (angular velocity measurement unit)" — [GlobalSecurity/Sputnik](https://www.globalsecurity.org/space/library/news/2023/space-231003-sputnik01.htm); [SpaceNews](https://spacenews.com/?p=192647)
- UNVERIFIED: rumor blaming BKU thrust-controller mishandling — no confirmation found ([Universe Today](https://universetoday.com/162856/russias-luna-25-lander-crashed-into-the-moon) reports it only as rumor).
- UNVERIFIED: Beresheet — one IMU failed during descent; ground-commanded reset of the IMU triggered a chain that shut down the main engine; it lost altitude and impacted. No source retrieved this session.

### Inferences
- Luna-25 is still sensor-integrity relevant: an inertial sensor that was *never enabled* was effectively trusted by a cutoff logic that did not check its own input validity (failure modes F + B) — same class as IM-1's disabled laser.

### Gaps
- Full Roscosmos commission report not public/found; Beresheet official SpaceIL/IAI findings not retrieved.

---

## 2026 missions (status as of late October 2026)

### Takeaway
No new lunar landing occurred in 2026 up to ~26 Oct 2026. Blue Moon MK1, IM-3 and Blue Ghost 2 slipped to 2027; Chang'e-7 was postponed from its 2026 window (CMSA, 23 Aug 2026) with no reason given; Astrobotic Griffin-1 completed environmental testing (JPL, 13 Oct 2026) and targets a November 2026 launch; ispace M3 is planned for 2027.

### Cited Findings
- SECONDARY: Blue Moon MK1 "Endurance" grounded after a New Glenn pad explosion, not expected before early 2027; IM-3 and Blue Ghost 2 slipped to 2027; Griffin-1 the only US robotic lander still planning a 2026 launch — [The Space Review, art. 5344](https://www.thespacereview.com/article/5344/1)
- SECONDARY (tertiary aggregator, verify): Griffin-1 finished environmental tests at JPL 13 Oct 2026, launch listed November 2026 — [Wikipedia: Griffin Mission One](https://en.wikipedia.org/wiki/Griffin_Mission_One)
- SECONDARY (tertiary aggregator, verify): CMSA said 23 Aug 2026 that Chang'e-7 could not proceed in its 2026 window; no reason/new date; Wikipedia infobox and body conflict (2027 vs indefinite) — [Wikipedia: Chang'e 7](https://en.wikipedia.org/wiki/Chang%27e_7)
- SECONDARY: ispace Mission 3 slipped to 2027 — [SpacePolicyOnline](https://spacepolicyonline.com/news/hardware-failure-doomed-ispaces-mission-2/)

### Inferences
- No 2026 landing data exist to test the post-2025 corrective actions (IM-3 dissimilar altimeters, ispace sensor robustness, Blue Moon TRN).

### Gaps
- Primary CMSA statement on Chang'e-7 and Astrobotic statement on Griffin-1 schedule not read; events after ~26 Oct 2026 not covered.

---

## Cross-mission synthesis for sensor-trust design (inferences, built on findings above)

| Mission | Outcome | Dominant trust failure mode | Official vs speculative |
|---|---|---|---|
| ispace M1 (2023) | Crash (fuel exhaustion at ~5 km true altitude) | (A) good LRF rejected at crater rim; (C) gating not validated on new-site terrain; (E) | Official (ispace) — SECONDARY |
| ispace M2 (2025) | Crash | (B/F) LRF hardware anomaly, delayed valid data; (E) | Official (ispace) — SECONDARY |
| IM-1 (2024) | Landed tilted, ~7.8 m/s contact | (F) laser altimeter not enabled; good NDL not admitted to filter; (E) | NDL facts VERIFIED-PRIMARY (NASA TM) |
| IM-2 (2025) | Landed on side in crater | (B) noisy altimeter; (D) polar lighting; (C) crater appearance mismatch | CEO statements — SECONDARY |
| Blue Ghost M1 (2025) | Success, <100 m | — | SECONDARY |
| SLIM (2024) | Landed inverted; nav ~10 m | Nav OK; propulsion failure | JAXA — VERIFIED-PRIMARY (via doc extraction) |
| Chang'e-3/4/5/6 | Success | — (active 3D lidar hover HDA) | Papers — VERIFIED-PRIMARY |
| Chandrayaan-3 (2023) | Success | — (dissimilar Ka-band + laser altimetry) | SECONDARY |
| Luna-25 (2023) | Crash in orbit burn | (F/B) accelerometer not enabled in BIUS-L; not descent nav | Roscosmos — SECONDARY |

- Every commercial failure 2023-2025 involved the altitude channel and a lack of a *working, admitted, dissimilar* altitude/velocity source; every success either had dissimilar active sensing (Chandrayaan-3, Chang'e) or benign terrain/lighting with working TRN (Blue Ghost, SLIM).
- Both directions of trust error occurred: over-rejection (ispace M1) and under-detection/acceptance of bad data (IM-2). An integrity design needs a map-aware consistency test (DEM-predicted range vs measured) rather than a fixed jump threshold.
- Configuration/enable errors (IM-1 laser, Luna-25 accelerometer) are a distinct failure class: the sensor is fine but absent; integrity monitors must detect "no valid data by gate X" and trigger a defined fallback.
