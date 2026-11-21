# Descent GNC chain and command/authority chain of modern lunar landers (2013-2025)

Research date: 2026-10-29. Builds on `D:\newprj\research_notes\Lunar TRN literature verification\lunar_mission_outcomes.md` (root causes); this file focuses on **sensor chain, filter, guidance phases/mode transitions, onboard-vs-ground authority, FDIR, the point where a sensor-rejection decision sits, touchdown/cutoff, and what ground did during descent**.

Claim labels:
- **VERIFIED-PRIMARY**: read this session in an official/primary document (agency/company release, NASA TM, conference abstract by the operator's own engineers, peer-reviewed or arXiv technical paper).
- **SECONDARY**: read this session in reporting/aggregators that attribute the claim to an official source; primary text not read.
- **UNVERIFIED**: researcher's prior knowledge or a weak single source; not confirmed this session. Do not cite without checking.

Method limits (read before using): the web tools hit a session limit partway through. Not read this session: Chinese CE-3/CE-5 GNC full texts (Springer/SPJ returned 403/login redirect), ISRO primary documents, ispace M1 technical detail beyond the 26 May 2023 release, IM's own IM-1/IM-2 reports, AAS 25-310 (IM-1 powered-descent reconstruction). Those items are marked UNVERIFIED or listed as gaps.

---

## Q1. ispace HAKUTO-R Mission 1: where the altitude-rejection logic sat, why ground could not intervene, the timeline, and stated changes

### Takeaway
The rejection decision sat **inside the onboard navigation software, at the measurement-acceptance step**: the software compared the sensor's measured altitude with its own pre-set/estimated altitude, judged the gap "larger than expected" as a sensor fault, and stopped admitting the altitude data, so the vehicle flew on inertial propagation. The estimate reached zero while the lander was ~5 km up. The guidance then finished its terminal deceleration (under 1 m/s, vertical) at ~5 km altitude and kept descending slowly until propellant ran out, after which it free-fell. No published source says ground tried to intervene or could have. The descent was an autonomous sequence, and ground telemetry showed the vehicle's *believed* state. ispace's published fix is generic: put the findings into the software design and widen the pre-landing simulations to represent the lunar terrain.

### Cited Findings
- VERIFIED-PRIMARY: Timeline (JST, 26 Apr 2023). Descent began at **00:40** from ~100 km. Operations went as expected until about **01:43**, the scheduled landing time. The lander "completed the full planned deceleration" and reached under 1 m/s in a vertical attitude at **~5 km** altitude. After 01:43 it kept descending at low speed until propellant was exhausted, controlled descent ended, and it is believed to have free-fallen. Communications were never re-established, so Milestones 9 and 10 were not achieved. — [ispace release, 26 May 2023](https://www.ispace-inc.com/2023/05/26/ispace-announces-results-of-the-hakuto-r-mission-1-lunar-landing/)
- VERIFIED-PRIMARY: Mechanism. Measured altitude rose sharply as the lander crossed a ~**3 km** high cliff (crater rim). The gap between measured and **pre-set estimated altitude** was larger than expected. The software judged the sensor reading abnormal and **rejected** the altitude data. The filter was meant as a safeguard against sensor/hardware faults that could destabilize the lander. The release calls this the most likely cause. — [ispace release, 26 May 2023](https://www.ispace-inc.com/2023/05/26/ispace-announces-results-of-the-hakuto-r-mission-1-lunar-landing/)
- VERIFIED-PRIMARY: The landing site was changed **after the CDR completed in February 2021**. This affected the V&V plan, and prior simulations "did not adequately include the lunar terrain along the navigation route". — [ispace release](https://www.ispace-inc.com/2023/05/26/ispace-announces-results-of-the-hakuto-r-mission-1-lunar-landing/)
- VERIFIED-PRIMARY: Corrective actions as published: incorporate the findings into the software design, and upgrade and expand the scope of landing-sequence simulations to better represent the lunar environment. Hardware unchanged for M2 (same Series 1 lander). The release gives no specific software fixes, thresholds, or changes to ground procedures. — [ispace release](https://www.ispace-inc.com/2023/05/26/ispace-announces-results-of-the-hakuto-r-mission-1-lunar-landing/)
- VERIFIED-PRIMARY: Flight data were analysed by operations specialists at the Mission Control Center in Nihonbashi, Tokyo. The release says nothing about ground commanding during descent. — [ispace release](https://www.ispace-inc.com/2023/05/26/ispace-announces-results-of-the-hakuto-r-mission-1-lunar-landing/)
- SECONDARY: The sensor was the laser rangefinder, and the software (developed by Draper to ispace requirements) was not programmed to expect the rim jump and treated the instrument as malfunctioning. — [SpaceNews](https://spacenews.com/software-problem-blamed-for-ispace-lunar-lander-crash/)
- SECONDARY: Mission control saw the lander vertical on final approach. Engineers noticed the estimated propellant reaching its lower threshold just before descent speed rose rapidly, then no touchdown data and loss of signal. — [Gulf News](https://gulfnews.com/uae/science/uaes-rashid-rover-what-led-to-unsuccessful-landing-1.95356448)
- SECONDARY: ispace later said the M1 software fixes performed correctly on M2. M2's cause was LRF hardware, and ispace's 24 June 2025 analysis says "the issue was not related to the landing guidance control software". — [ispace M2 cause analysis](https://www.ispace-inc.com/2025/06/24/ispace-releases-technical-cause-analysis-for-hakuto-r-mission-2/) (VERIFIED-PRIMARY for the quote); [SpacePolicyOnline](https://spacepolicyonline.com/news/hardware-failure-doomed-ispaces-mission-2/)
- Conflict: MoonCoverage says the engine "cut off early" at several km altitude. ispace's primary release says it kept descending slowly until propellant exhaustion. **Use ispace.** — [MoonCoverage](https://mooncoverage.com/missions/hakuto-r-m1/)

### Inferences
- **Chain position:** sensor → measurement-validity gate (innovation/jump test against the predicted altitude) → navigation filter → guidance (terminal-descent law that targets the estimated surface) → control. The fault entered at the **gate**, which works as an onboard FDIR decision embedded in navigation. After rejection, nothing higher in the chain (guidance, a mode manager, or ground) had independent altitude truth to overrule it.
- **Why ground could not save it (inference; no source states this):** (1) The sequence was autonomous, and once it was running there is no published evidence of a ground "override altitude" or "re-admit sensor" command path. (2) Ground saw the *estimated* altitude, which looked like a landing, so the anomaly showed only indirectly as a long low-speed descent and propellant reaching its low threshold. (3) A slow descent from ~5 km at under 1 m/s holds for minutes, not hours, while the propellant margin drains. Any re-plan would need diagnosis, a command, and a burn within that margin.
- Free-fall from ~5 km in lunar gravity (1.62 m/s²) gives roughly 127 m/s at impact, before counting any residual velocity (inference, simple kinematics).
- The "pre-set estimated altitude" wording means the gate's reference was partly a stored profile or prediction that was never re-derived for the post-CDR route. The fault-protection threshold was terrain-dependent but was validated on the wrong terrain.

### Gaps
- Time spent between rejection and 01:43, the true altitude when rejection occurred, gate threshold values, and whether the gate latched permanently or could re-admit data: not published in material read.
- Whether ground had any commandable abort or override in the terminal sequence: no source found.
- ispace's detailed post-M1 requirement changes (for example terrain-aware gating, or a DEM along the new route in simulation): UNVERIFIED. Only the generic statement is primary.

---

## Q2. ispace HAKUTO-R Mission 2 (RESILIENCE): place of the LRF fault in the chain

### Takeaway
On M2 the fault entered at the **sensor itself** (availability/latency), not at the gate. Valid LRF measurements arrived too late for the guidance to decelerate. The vehicle's navigation and guidance logic was exonerated.

### Cited Findings
- VERIFIED-PRIMARY: "the acquisition of valid measurements from the LRF was delayed", so the lander could not slow to the required speed, and a hard landing was highly likely. The lander was nearly vertical in the final phase. — [ispace, 24 Jun 2025](https://www.ispace-inc.com/2025/06/24/ispace-releases-technical-cause-analysis-for-hakuto-r-mission-2/)
- VERIFIED-PRIMARY: Two candidate causes. (1) Installation-direction error, or abnormal attitude during descent: ruled out. (2) "deterioration in the performance of the LRF during flight or the performance itself was lower than expected": judged highly likely. Software, propulsion, and power were ruled out. — [ispace, 24 Jun 2025](https://www.ispace-inc.com/2025/06/24/ispace-releases-technical-cause-analysis-for-hakuto-r-mission-2/)
- VERIFIED-PRIMARY: Actions: re-select landing sensors including LRFs and expand testing, set up an external review task force, expand JAXA collaboration, and budget up to ~¥1.5 bn across M3/M4. — [ispace, 24 Jun 2025](https://www.ispace-inc.com/2025/06/24/ispace-releases-technical-cause-analysis-for-hakuto-r-mission-2/)
- SECONDARY: Nominal profile: terminal descent from 1 km to 10 m (120 km/h down to 2 km/h), then terminal landing from 10 m to 0. — [Spaceflight Now](https://spaceflightnow.com/2025/06/06/ispaces-resilience-lander-crash-lands-on-the-moon/)
- UNVERIFIED: last-telemetry altitude and speed (often quoted as ~190 m and ~40 m/s); not found in primary text this session.

### Inferences
- M2 was a "time-to-first-valid" failure. Guidance needed LRF data before a gate altitude, and when the data had not arrived, no fallback mode (such as an earlier or more conservative braking profile, or an alternate sensor) existed. M1 and M2 together show both ends of single-modality fragility: over-rejection of good data (M1) and a good gate waiting for data that came too late (M2).

### Gaps
- Whether M2 software had an explicit "no valid LRF by altitude X" response: not published.

---

## Q3. Intuitive Machines IM-1 Odysseus: who decided to switch to NDL, how the patch was uplinked, why it failed, touchdown and tip-over

### Takeaway
The GN&C chain was IMU + optical feature-tracking TRN + laser altimeter feeding a Kalman filter initialized from DSN orbit determination. NASA's NDL was planned only as a secondary velocity input. Before descent initiation the laser altimeter was found non-operational. Ground (IM's flight team, using an added orbit and a ~2 h delay) modified the flight software to ingest NDL range and velocity, but the modification failed and **no NDL data reached the filter**. The lander landed on IMU + optical alone. It made first ground contact at **7.8 m/s** with a large flight-path angle (~45-49° below horizontal, i.e. substantial horizontal velocity), broke a leg, and tipped. The failure entered the chain twice: a **configuration step before launch** (the altimeter safety enable), and a **ground-side software integration step in lunar orbit** (the patch that never made NDL data usable by the filter).

### Cited Findings
- VERIFIED-PRIMARY: GN&C: IMU, optical feature-tracking TRN instrument, and laser altimeter → Kalman filter initialized from DSN OD. NDL velocity was intended as a *secondary* filter input. Filter output provides the navigation state to guidance and control. — NASA/TM-20250010290 (local text `D:\newprj\out\literature\20261029_trn_review\NDL_IM1_TM_20250010290.txt`; [NTRS](https://ntrs.nasa.gov/citations/20250010290))
- VERIFIED-PRIMARY: "A discovery was made prior to descent initiation that the laser altimeter was not operational… the filter would rely on an IMU and optical feature tracking alone. An effort was made to modify the flight software to enable processing of the NDL range and velocity measurements; however, the attempt proved to be unsuccessful and the vehicle conducted its landing without the use of any NDL data." The introduction says "software issues prevented the navigation filter from ingesting the data". — [NASA/TM-20250010290](https://ntrs.nasa.gov/citations/20250010290)
- VERIFIED-PRIMARY: Timeline. 20×200 km lunar orbit on 21 Feb 2024 at 14:35:51 UTC. Descent orbit insertion on 22 Feb at 05:49:29 UTC. Powered landing sequence initiated at **23:10:32 UTC**. Landed near Malapert-A at −80.1276°, 1.4367°E, at 23:23:00 UTC per ref [24]. NDL data ran "until touchdown at 23:23:45.0" with no dropouts. **Internal inconsistency:** 23:23:00 and 23:23:45 are both given as landing/touchdown; possibly first contact vs. final rest, or rounding in ref [24]. — [NASA/TM-20250010290](https://ntrs.nasa.gov/citations/20250010290)
- VERIFIED-PRIMARY: Velocity at first ground contact 7.79 m/s (NDL-only) and 7.80 m/s (IMU/NDL). Flight-path angle at first contact −44.46° ground-relative and −48.99° NED-relative. Pitch 76.83° relative to local terrain and 85.42° relative to NED. Reconstructed AGL at the start of the IMU segment was 1921.2 m. — [NASA/TM-20250010290](https://ntrs.nasa.gov/citations/20250010290)
- SECONDARY: The landing was delayed ~2 h, adding an extra orbit, to put the patch in place. The patch let the lander use NDL in place of the failed laser rangefinders. The rangefinders failed because a physical safety switch had not been flipped. — [Payload Space](https://payloadspace.com/im-1-is-sideways-but-weve-all-been-there/); [Space.com](https://www.space.com/intuitive-machines-odysseus-private-moon-landing-success)
- SECONDARY: Altemus said the EagleCam payload was shut off so the NDL could be connected to the lander's navigation system for descent. — [Spectrum News 13](https://mynews13.com/fl/orlando/space/2024/02/23/eaglecam-not-deployed-for-lunar-landing-due-to-odysseus-navigation-issue)
- SECONDARY (three accounts of *why* the patch failed, mutually consistent with the TM):
  - NYT via Pittsburgh Post-Gazette: engineers rewrote guidance software shortly before landing but "overlooked one spot" that needed updating, and the computer ignored the altitude data. — [Pittsburgh Post-Gazette (PressReader)](https://www.pressreader.com/usa/pittsburgh-post-gazette/20240305/281767044180636)
  - Altemus to Ars Technica's Berger (relayed): the NDL collected data but the flight computer could not process it in real time. — [Neowin](https://www.neowin.net/news/odysseus-was-data-blind-prior-moon-landing-survived-11-crises-and-got-lost-for-a-few-hours/) (fetch 403; relayed via search snippet)
  - AZMTH: Crain said on 28 Feb 2024 that a missed data flag meant the NDL data never processed. — [AZMTH](https://azmth.space/moon/missions/im-1-odysseus)
- Conflict: early reporting said "on-the-fly software patch saved" the landing ([Bloomberg](https://www.bloomberg.com/news/articles/2024-02-23/on-the-fly-software-patch-saved-intuitive-machines-lunr-moon-landing)). The NASA TM says no NDL data were used. **NASA TM is authoritative.**
- SECONDARY: after touchdown, several minutes passed before controllers reacquired a signal. — [search summary of Reuters-derived coverage; see AmericaSpace](https://www.americaspace.com/2024/02/26/im-1-struggles-with-communications-after-tipping-over/)
- UNVERIFIED: the decision-maker structure (IM Nova Control flight director plus IM GNC team, with NASA Langley's NDL team supplying interface/data-format support), the exact uplink time, and whether the patch was tested on a ground simulator before uplink.

### Inferences
- **Decomposed contact velocity (inference computed from TM values, assuming flight-path angle = velocity direction below local horizontal):** with |V| = 7.80 m/s at −48.99° NED, vertical ≈ 5.9 m/s and horizontal ≈ 5.1 m/s. Using the ground-relative −44.46°, both components are ≈ 5.5 m/s. Either way, horizontal velocity at contact was several m/s, consistent with a leg catching and the vehicle tipping. This also explains the rest attitude without invoking an attitude-control fault, since the NED pitch at contact was ~85° (near upright).
- **Authority chain:** the altimeter-out discovery and the NDL decision were **ground** decisions made in lunar orbit. The descent was then fully autonomous on whatever filter configuration had been uploaded. Ground effectively owned "which sensors the filter trusts" pre-descent, and the vehicle owned everything after PDI. The patch failure means the ground-side trust change was never verified end-to-end: the filter's acceptance flag/path (data-valid flag, per secondary) blocked a good sensor. This is an "(A) rejecting a good sensor" failure that happened in ground software engineering, not in onboard FDIR logic.
- Without an altimeter, the vertical channel and the terrain-relative horizontal velocity near touchdown came from optical feature tracking plus IMU, a weak observability case near the surface over polar terrain.

### Gaps
- IM's official IM-1 report and Stewart et al. AAS 25-310 (powered-descent reconstruction) were not read. They would confirm the nav-filter internals and the touchdown/cutoff logic.
- Touchdown detection and engine-cutoff logic on Nova-C: no source found.

---

## Q4. Intuitive Machines IM-2 Athena: the altimeter problem's place in the chain

### Takeaway
On IM-2 the altimeter was operating but its returns were noisy and distorted in final descent. Per IM's account this was a bad-data acceptance or degradation problem at the **sensor/measurement** level, compounded by optical-navigation (crater-matching) degradation from polar lighting and from an orbital-altitude reference map. No primary IM document was read. All IM-2 claims are SECONDARY (CEO statements).

### Cited Findings
- SECONDARY: Three factors. (1) Laser altimeter "signal noise and distortion" in the final phase of descent prevented accurate altitude readings. (2) Low-angle sunlight and long shadows challenged the landing system. (3) The optical navigation crater reference used LRO images from ~100 km, which "could not accurately account for how craters appear at lower altitudes with south pole lighting conditions". — [Space.com](https://www.space.com/astronomy/moon/heres-why-the-private-athena-lunar-lander-toppled-over-on-the-moon); [Spaceflight Now](https://spaceflightnow.com/2025/05/14/intuitive-machines-ceo-points-to-issues-that-prevented-upright-touchdown-during-im-2-moon-landing/)
- SECONDARY: IM-3 fixes: altimeters with different operating principles under more stringent testing, lighting-independent velocity sensing, an extended crater database, and IM-2 imagery used to train ML. — [Space.com](https://www.space.com/astronomy/moon/heres-why-the-private-athena-lunar-lander-toppled-over-on-the-moon)
- UNVERIFIED: whether NDL flew on IM-2, the altitude band of the altimeter noise, and whether the filter flagged the data or ingested it.

### Inferences
- In the chain, IM-2's failure entered at sensor and measurement quality, and both absolute-position aids degraded at once (range and optical). Unlike ispace M1, the problem was likely **insufficient rejection** (or rejection with no alternative), not over-rejection. Because the IM-3 fix is "different operating principles", IM itself sees the root issue as lack of dissimilar redundancy, not gate tuning.

### Gaps
- No IM technical report found on how the filter handled the noisy altimeter or what onboard FDIR did.

---

## Q5. JAXA SLIM: image-matching navigation phases, obstacle detection at ~50 m, and onboard handling of the engine anomaly

### Takeaway
SLIM's navigation corrected IMU propagation with crater-based image matching during descent. At the second hover point (HV2, ~50 m) it ran two obstacle detections and **set the safe landing zone autonomously**. Just before the obstacle-avoidance maneuver, one of two main engines lost thrust. **The onboard software autonomously identified the anomaly and continued the descent on the remaining engine**, holding horizontal position as well as it could while drifting east. It touched down at ≤1.4 m/s vertical (within design), but lateral velocity and attitude were out of range, and it came to rest inverted ~55 m east of target. Ground's role after touchdown was a commanded shutdown to save battery.

### Cited Findings
- VERIFIED-PRIMARY: Landing at 00:20 JST on 20 Jan 2024, with communication established. Because the solar cells could not generate power at the landing attitude, ground sent a command shutting the spacecraft down at **02:57 JST**. Touchdown ~55 m east of target. — [JAXA press release, 25 Jan 2024](https://global.jaxa.jp/press/2024/01/20240125-1_e.html)
- VERIFIED-PRIMARY: Positional accuracy before the obstacle-avoidance maneuver (~50 m altitude) was "approximately 10m or less, possibly about 3 - 4m". At HV2 two obstacle detections took place (about 3-4 m and about 10 m accuracy), and SLIM **autonomously set a safe landing zone** from the HV2 obstacle detection. The main engine was "highly likely" already affected during the second detection. — [JAXA, 25 Jan 2024](https://global.jaxa.jp/press/2024/01/20240125-1_e.html)
- VERIFIED-PRIMARY: "at an altitude of 50m just prior to the start of the obstacle avoidance maneuver, the thrust from one of the two main engines was most likely lost". The onboard software "autonomously identifies the anomaly", continued descent with the other engine while controlling horizontal position as much as possible, and drifted east. LEV-1/LEV-2 separated just before touchdown. — [JAXA, 25 Jan 2024](https://global.jaxa.jp/press/2024/01/20240125-1_e.html); [SpaceNews](https://spacenews.com/japans-slim-achieved-pinpoint-moon-landing-with-just-one-working-engine/)
- VERIFIED-PRIMARY: Contact velocity "approximately 1.4 m/s or less", within design. Lateral velocity and attitude were outside design, likely causing the unplanned final attitude. — [JAXA, 25 Jan 2024](https://global.jaxa.jp/press/2024/01/20240125-1_e.html)
- SECONDARY: a camera image showed a nozzle lying on the surface, and JAXA attributed the loss to an undisclosed "external factor". — [SpacePolicyOnline](https://spacepolicyonline.com/news/jaxas-slim-literally-lost-an-engine-and-nasas-lro-spots-slim-on-the-surface/)
- UNVERIFIED: full phase list (powered descent from ~15 km, vertical descent, HV1 hover with image matching, HV2 at ~50 m with obstacle detection by navigation camera, then planned "two-step" touchdown with the main leg first, then tipping onto the rear legs) and the sensor list (navigation cameras, landing radar, IMU). From prior knowledge; the JAXA page read does not detail them.

### Inferences
- SLIM is the clearest published example of **onboard propulsion FDIR with autonomous continuation**. The vehicle did not abort or wait for ground; it reconfigured to one engine and prioritized vertical velocity over lateral position. Under a single-engine thrust and torque budget it kept vertical touchdown speed in spec but not lateral speed or attitude. Navigation integrity was intact: nav saw the drift, and control lacked authority to correct it.
- The obstacle-detection decision (safe-zone selection) was onboard at HV2. Ground played no role in hazard selection.

### Gaps
- JAXA/ISAS technical papers on SLIM's navigation filter, image-matching FDIR (match-rejection logic), and the touchdown detection/cutoff mechanism were not read this session.

---

## Q6. CNSA Chang'e-3/4/5: autonomous hazard-avoidance hover, phases, touchdown sensing and cutoff

### Takeaway
Chang'e-3 established the template that CE-4/5/6 inherited: fully autonomous powered descent of ~700 s and ~1.7 km/s ΔV, in a phase sequence of braking, pitch adjustment, **approach** (optical camera, coarse hazard detection of large obstacles), **hover at ~100 m** (laser 3D imaging, fine hazard detection of rocks/pits), **obstacle avoidance** (lateral translation), and **slow descent**. The descent is autonomous by design because it is short and high-ΔV. Engine cutoff close to the surface followed by a short free drop is reported in prior knowledge but **not verified this session**.

### Cited Findings
- SECONDARY (relaying Sun, Jia & Zhang, Sci China Tech Sci 2013): powered descent "will not be a long period of time (appr. 700 s), with a larger ∆V (1.7 km/s), so the implementation of guidance, navigation & control depends on autonomous navigation". — [Sci China Tech Sci 2013, doi:10.1007/s11431-013-5377-0](https://link.springer.com/article/10.1007/s11431-013-5377-0) (full text not reached: login redirect)
- SECONDARY: CE-3 profile: braking, pitch-up, approach, hovering, hazard avoidance, slow-rate descent. CE-5's descent trajectory "is derived from Chang'E-3 lander". — [Guidance Navigation and Control for Chang'E-5 Powered Descent, Space: Science & Technology 2021](https://spj.science.org/doi/10.34133/2021/9823609) (403; content via search extraction); [ResearchGate CE-3 guidance assessment](https://www.researchgate.net/publication/284345092_Guidance_Summary_and_Assessment_of_the_Chang'e-3_Powered_Descent_and_Landing)
- SECONDARY: Relay obstacle avoidance ("coarse-to-fine"): it starts at the approach stage, using optical camera images to detect large obstacles. During hover the laser 3D imaging sensor collects 3D terrain data to detect small hazards (>20 cm). — [eoPortal Chang'e-3](https://www.eoportal.org/satellite-missions/chang-e-3)
- SECONDARY: A 2D grey-image-based hazard detection scheme failed first-round ground testing, forcing the HDA redesign (which added 3D laser imaging) and delaying CE-3 to end-2013. — [eoPortal Chang'e-3](https://www.eoportal.org/satellite-missions/chang-e-3)
- VERIFIED-PRIMARY (prior notes): CE-4 hovered ~13 s at ~99 m, then shifted ~12 m to avoid a 25 m crater. CE-3/4 sensors were laser ranging, microwave ranging/velocimetry, optical imaging, and laser 3D imaging. — [Nature Communications 2019 (PDF mirror)](https://dcmpx.remotevs.com/com/nature/www/SL/articles/s41467-019-12278-3.pdf)
- SECONDARY: CE-3 hover reported as ~20 s at 100 m; variable-thrust engine 1,500-7,500 N; ~12 min descent. Conflict: a 100 s hover figure also circulates, probably the pre-flight allowance. — [Universe Today](https://www.universetoday.com/107369/stunning-change-3-lunar-landing-video-gives-astronauts-eye-view-of-descent-touchdown/amp/)
- SECONDARY (bibliographic only): primary GNC source is Yu P., Zhao Y., Li J., Zhang X., Wang D., "Guidance navigation and control for Chang'E-3 powered descent", Scientia Sinica Technologica 44(4):377-384, 2014. Zhang Honghua (BICE/CAST) is co-author of the CE-3 autonomous hazard-avoidance control paper. — [ScienceGate record](https://next.sciencegate.app/document/10.1360/092014-43); [ResearchGate: Autonomous hazard avoidance control for Chang'E-3 soft landing](https://www.researchgate.net/publication/273225575_Autonomous_hazard_avoidance_control_for_Chang'E-3_soft_landing)
- SECONDARY: "engine shutdown at touchdown" landing-stability studies exist for Chinese landers (BUAA). — [BUAA journal abstract](https://bhxb.buaa.edu.cn/CN/abstract/abstract14368.shtml)
- UNVERIFIED (prior knowledge): CE-3 cut off the engine at ~4 m altitude and dropped to the surface, with cutoff triggered by a dedicated shutdown sensor (often described as a gamma-ray shutdown sensor). The navigation filter is IMU propagation corrected by ranging/velocimeter measurements, with measurement-validity checks. Ground role: uplinks the descent start time/parameters, then monitors only.

### Inferences
- The Chang'e architecture pairs **dissimilar** absolute sensors (laser *and* microwave range/velocity) with an **active, lighting-independent** 3D imager at the hover point. That makes the hazard decision robust to lighting, and the range channel robust to a single-modality anomaly like ispace M1's.
- The hover is an explicit **decision gate** with a defined state (near-zero velocity at ~100 m) in which sensing time is bought with propellant. That is a useful pattern for a simulated study: a "verify-then-commit" mode transition.

### Gaps
- The CE-3/CE-5 GNC full texts (filter type, measurement rejection rules, mode-transition triggers, cutoff sensor) were not accessible this session.

---

## Q7. ISRO Chandrayaan-3 (and Chandrayaan-2): ALS, sensors, phases, redundancy, and the Chandrayaan-2 failure timeline

### Takeaway
Ground **commanded the start** of the Automatic Landing Sequence (ALS). ISRO posted that it was "all set to initiate" the ALS, awaiting the lander's arrival at the designated point around 17:44 IST. After that, the onboard computer ran the powered descent autonomously: rough braking (30 → 7.4 km), a ~10 s attitude hold for absolute-sensor updates to the INS, fine braking to ~800 m (1.3 km above mean surface) with a 12 s hover, vertical descent to 150 m, a second hover of up to 22 s for hazard-camera site selection, retargeting to a safe site at 60 m, then descent at −1 m/s and constant-velocity touchdown at 18:04 IST. ISRO's "failure-based design" used dissimilar altimeters and velocimeters. Chandrayaan-2's committee findings were never published. Public statements cite thrust dispersion larger than simulated and "three cumulative errors".

### Cited Findings
- SECONDARY (quoting ISRO's X post, 23 Aug 2023): "All set to initiate the Automatic Landing Sequence (ALS). Awaiting the arrival of the Lander Module (LM) at the designated point, around 17:44 Hrs." Upon receiving the ALS command, the LM activates the throttleable engines for powered descent, and operators at MOX verify the command sequence. The link was between the lander and MOX-ISTRAC, Bengaluru. Landing at 18:04 IST. — [Deccan Herald](https://www.deccanherald.com/science/space/chandrayaan-3-moon-touchdown-all-set-for-automatic-landing-sequence-says-isro-2657519); [Business Today](https://www.businesstoday.in/latest/trends/story/chandrayaan-3-landing-update-isro-says-it-is-all-set-to-initiate-the-automatic-landing-sequence-395234-2023-08-23)
- VERIFIED-PRIMARY (technical preprint, arXiv 2605.29412): Phases. Rough braking 30 km → 7.4 km, removing most of ~1.68 km/s with four 800 N engines. Attitude hold ~10 s for sensor operations, after which navigation is corrected with absolute sensor measurements. Fine braking to 800 m above the site (1.3 km from mean surface) at near-zero velocity. Two engines shut off, a 12 s hover, then vertical descent to 150 m. Second hover up to 22 s at 150 m, where the hazard camera identifies a safe site. Move to the hazard-free site at 60 m with zero velocity, descend to 10 m at a commanded −1 m/s, then constant velocity to touchdown at 69.373560°S, 32.319750°E. Guidance in fine braking is a closed-loop cubic-polynomial acceleration law recomputed each cycle. — [arXiv 2605.29412 (Real-Time Retargeting Using Controllability Boundary for Chandrayaan-3)](https://arxiv.org/html/2605.29412)
- SECONDARY: Attitude hold at ~50° from vertical so the altimeters point to nadir, ending with sensor updates to the INS. — [Swarajya](https://swarajyamag.com/science/explained-how-chandrayaan-3-lander-will-navigate-through-its-final-descent-to-the-moons-surface)
- SECONDARY: The lander decides onboard whether to land vertically or translate up to ~150 m laterally to avoid hazards. In flight it moved to an adjacent safer area. — [Republic World](https://www.republicworld.com/science/space/15-minutes-of-terror-chandrayaan-3-landing-process-explained-articleshow)
- SECONDARY (prior notes): sensors were Ka-band altimeter, laser altimeter, LDV, LHVC, LPDC, and hazard detection camera. The landing zone was enlarged to 4 km × 2.4 km. "Failure-based design" assumed sensor, engine, and algorithm failures. The LDV was not needed because descent was nominal. — [Aviation Week](https://aviationweek.com/space/indias-chandrayaan-3-will-attempt-soft-lunar-landing); [Business Today](https://www.businesstoday.in/amp/latest/in-focus/story/indias-moon-mission-how-chandrayaan-3-is-better-than-chandrayaan-2-key-differences-explained-389556-2023-07-13); [Science Chronicle](https://sciencechronicle.in/2025/05/03/what-helped-vikram-lander-to-soft-land-on-the-moon/)
- SECONDARY (Chandrayaan-2): Sivan said thrust "dispersion level… was more than what we had assumed during the pre-flight simulations", that three cumulative errors caused the failure, and that the mission would have succeeded had any one of them been absent. The Failure Analysis Committee reportedly concluded a software glitch. The report was not made public. — [India Today via PressReader](https://www.pressreader.com/india/india-today/20190923/282565904845630); [The Wire](https://thewire.in/space/chandrayaan-2-anniversary-vikram-lander-pragyan-rover-isro-k-sivan-ohrc-narrative-failure); [inkl](https://www.inkl.com/news/large-speed-spike-may-have-led-to-vikram-crashing-says-isro-chairman)
- UNVERIFIED (prior knowledge): ISRO uploaded the ALS ~2 h before landing. Chandrayaan-2 Vikram had five 800 N engines (four plus a central one, which Chandrayaan-3 removed). Vikram's deviation began near ~2.1 km altitude after the "camera coasting"/fine-braking transition, when higher thrust plus guidance rate/attitude limits drove it off trajectory. Somanath said Vikram would land "even if all sensors fail… provided propulsion works". Dual or redundant computers and an onboard landing-site-safety algorithm. None of this was confirmed this session.

### Inferences
- **Authority split:** ground owns the go/no-go and the start epoch of ALS (plus, pre-ALS, the choice to land on the planned date or slip, which ISRO had said was possible). Once ALS starts, all phase transitions, sensor fusion, hazard detection, and retargeting are onboard. This is the same split as Blue Ghost (ground commands DOI; vehicle runs descent).
- The 10 s attitude hold is an explicit **sensor-trust re-initialization point**: an open-loop interval where absolute sensors are brought in and the INS is reset before closed-loop fine braking. A simulation can mirror this with a "gate" where sensor admission is decided under stable geometry.
- The enlarged landing zone and the controllability-boundary retargeting turn "sensor disagreement → large estimate correction" from a crash risk into a retarget. That reduces the cost of trusting a late, large correction, the case that killed ispace M1.

### Gaps
- No ISRO primary document on the navigation filter, sensor voting/rejection logic, or touchdown detection/cutoff was read. ISRO's Chandrayaan-2 FAC report is not public.

---

## Q8. Firefly Blue Ghost M1: autonomy and sensor chain

### Takeaway
Ground commanded Descent Orbit Insertion. In the descent orbit the vehicle engaged its **vision navigation system** (two navigation cameras, Space-ng software matching live imagery against rendered terrain) and autonomously flew powered descent with **D'Souza guidance**, using the main engine plus eight Spectre thrusters. The main engine disengaged over the site, and the final descent was on thrusters only. Two hazard-avoidance maneuvers were **autonomously commanded by the vision nav system**. Touchdown was sensed by footpad sensors (3 of 4 triggered), and upright status was verified from IMU data.

### Cited Findings
- VERIFIED-PRIMARY (Firefly engineers' LPSC 2026 abstract): "operators commanded Blue Ghost to perform Descent Orbit Insertion". "Once in its Descent Orbit, Blue Ghost engaged its vision navigation system to determine its location and attitude and began Powered Descent. Utilizing D'Souza guidance, the vehicle autonomously used both its main engine and eight Spectre thrusters…" "Once over the landing site, the main engine disengaged, and the remainder of descent was performed with Spectre thrusters only." "two hazard avoidance maneuvers were autonomously commanded by the vision navigation system." "Ground contact was sensed by three of the four footpad sensors, and successful soft and upright landing was verified using IMU data." LRO imagery verified touchdown "58 meters from the targeted landing ellipse". ~60 anomalies were dispositioned over the mission. — [Tackett, Marlin & Coogan, LPSC 2026 abstract 1958](https://www.hou.usra.edu/meetings/lpsc2026/pdf/1958.pdf)
- SECONDARY: vision-based TRN and hazard avoidance during the final hour identified craters, slopes, and rocks, and two vision-nav cameras chose the safest site. — [Firefly mission page](https://fireflyspace.com/missions/blue-ghost-mission-1/)
- SECONDARY: Space-ng software determined position and attitude by comparing two navigation cameras' imagery with terrain simulated in real time. Firefly acquired Space-ng in June 2026. — [Tech Times](https://www.techtimes.com/articles/319197/20260627/firefly-aerospace-brings-moon-landing-ai-navigation-in-house-after-blue-ghost-success.htm); [PR Newswire (Space-ng)](https://www.prnewswire.com/news-releases/space-ng-demonstrates-astrovision-and-lunar-optical-navigation-at-the-40th-space-symposium-302421087.html)
- Conflict: prior notes cite "within 100 m" of target (press). The primary abstract says 58 m "from the targeted landing ellipse". **Use the primary.**
- UNVERIFIED: altimeter/velocimeter hardware (laser or radar), star trackers, and the hazard sensing modality (passive stereo/photogrammetry vs active). The primary text does not list them.

### Inferences
- In Firefly's own account, the vision nav system holds **hazard-avoidance command authority** (it "commanded" the maneuvers), so TRN/HDA sits above guidance in the decision chain for the final target. The cutoff/contact chain uses dedicated footpad contact sensors with 3-of-4 sensing reported, which suggests a k-of-n vote (inference; voting logic not published).

### Gaps
- No Firefly paper on filter type, sensor-rejection logic, or cutoff logic (whether engine/thruster cutoff is on footpad contact, on altitude, or both).

---

## Lessons for a simulated sensor-trust study

### Takeaway
In every case the decisive trust decision was **onboard and pre-committed**: ground can configure trust before the autonomous sequence (IM-1 patch, ISRO ALS go, Firefly DOI) but cannot arbitrate during terminal descent. A simulated study should therefore model the trust decision as an onboard gate with a defined position in the chain, include configuration/ground-edit errors as a failure class, and score outcomes by touchdown state (vertical *and* lateral velocity, attitude), not just estimate error.

### Cited Findings
- Each lesson rests on findings above:
  - ispace M1: gate rejects good data at a rim [ispace 2023](https://www.ispace-inc.com/2023/05/26/ispace-announces-results-of-the-hakuto-r-mission-1-lunar-landing/).
  - ispace M2: late valid data [ispace 2025](https://www.ispace-inc.com/2025/06/24/ispace-releases-technical-cause-analysis-for-hakuto-r-mission-2/).
  - IM-1: good sensor blocked by a ground-made software path [NASA TM-20250010290](https://ntrs.nasa.gov/citations/20250010290).
  - SLIM: autonomous propulsion FDIR, with lateral/attitude out of spec [JAXA](https://global.jaxa.jp/press/2024/01/20240125-1_e.html).
  - Blue Ghost: autonomous HDA, footpad contact [LPSC 2026](https://www.hou.usra.edu/meetings/lpsc2026/pdf/1958.pdf).
  - Chandrayaan-3: ground-started ALS, attitude-hold sensor update, hover-gated retargeting [arXiv 2605.29412](https://arxiv.org/html/2605.29412).

### Inferences
1. **Put the rejection decision at an explicit chain node and log it.** Model sensor → validity gate → filter → guidance → control, and record each gate decision (accept/reject, innovation, threshold) with the *true* error. ispace M1 shows the gate itself can be the failure point.
2. **Make gates map-aware and test them on the route actually flown.** Compare measured range with DEM-predicted range along the current trajectory rather than with a pre-set altitude profile. Re-run validation whenever the site or route changes (ispace's post-CDR site change).
3. **Model both trust errors and their asymmetric costs:** false rejection (M1, IM-1's blocked NDL) and false acceptance or degraded acceptance (IM-2). Report them separately; a single accuracy metric hides the direction.
4. **Add an availability/latency failure class:** "no valid measurement by gate altitude h". Specify the fallback (conservative braking, hover-and-wait, retarget) and measure the propellant it costs (ispace M2).
5. **Add a configuration/integration failure class:** a sensor physically fine but disabled, or admitted through a mis-specified interface (IM-1's safety enable and failed patch; Luna-25's accelerometer in the prior notes). Inject "sensor present, data never reaches filter" faults and test whether the integrity monitor *notices the absence*.
6. **Include dissimilar redundancy as an experimental factor:** single LRF vs LRF + radar (Chandrayaan-3, Chang'e) vs LRF + vision velocimetry. Every 2023-2025 commercial failure involved a single altitude modality.
7. **Model hover/attitude-hold "verify-then-commit" gates** (Chang'e ~100 m hover, Chandrayaan-3 10 s hold and 150 m hover, SLIM HV2 at 50 m) as mode transitions where trust is re-evaluated under benign geometry, and price their propellant cost.
8. **Model ground authority realistically:** ground sets the configuration and the sequence start before PDI and has no in-loop authority during terminal descent. Do not let a simulated "operator" fix in-descent trust errors unless the study is explicitly about that counterfactual.
9. **Score touchdown by the full state:** vertical speed, horizontal speed, attitude/rate, and slope. IM-1 (7.8 m/s at ~45-49° flight-path angle) and SLIM (vertical in spec, lateral out) show that lateral velocity and attitude decided the outcome. Include touchdown detection (contact-sensor k-of-n, as on Blue Ghost) and cutoff timing.
10. **Separate nav integrity from control authority when attributing outcomes** (SLIM: correct nav, insufficient control after engine loss).

### Gaps
- Without the primary GNC texts (CE-3/5, ISRO, IM AAS 25-310, SLIM papers), the study cannot copy real gate thresholds, filter tuning, or cutoff logic. Parameters must be stated as assumptions.
