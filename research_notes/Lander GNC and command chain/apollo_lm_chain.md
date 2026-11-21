# Apollo LM Descent GNC Data Chain and Chain of Authority

Research date: 2026-10-29. The run stopped early because the session limit was hit after about 17 tool calls. Some planned fetches did not complete: Klumpp R-695, GSOP R-567 Section 5, LUNAR_LANDING_GUIDANCE_EQUATIONS.agc, THE_LUNAR_LANDING.agc, the AGS experience report, and the radar report TN D-6849. The ibiblio.org and UNT webarchive hosts failed with "certificate rejected". Items that depend on those fetches are labelled UNVERIFIED or listed under Gaps.

Labels:
- VERIFIED-FULLTEXT: read from the full primary or near-primary text in this session, through a WebFetch extraction by a small model. Paraphrase risk remains.
- ABSTRACT-ONLY: only a search snippet or abstract was seen.
- SECONDARY: a reputable secondary account such as journalism or a biography.
- UNVERIFIED: background knowledge that was not checked in this session.

Primary pages actually read:
- Don Eyles, "Tales from the Lunar Module Guidance Computer" — https://www.doneyles.com/LM/Tales.html
- Peter Adler, "Apollo 11 Program Alarms" (ALSJ) — https://www.apollojournals.org/alsj/a11/a11.1201-pa.html
- ALSJ Apollo 11 "The First Lunar Landing" (transcript and commentary) — https://www.apollojournals.org/alsj/a11/a11.landing.html
- ALSJ Apollo 14 landing (transcript and commentary) — https://www.apollojournals.org/alsj/a14/a14.landing.html
- Luminary 099 (Apollo 11 LGC flight software) SERVICER.agc source — https://raw.githubusercontent.com/chrislgarry/Apollo-11/master/Luminary099/SERVICER.agc

## Q1. PGNCS sensor-to-navigation chain: IMU, 2-s servicer, landing radar incorporation, V57/N68, DELTA-H, ground "go"

### Takeaway
The LGC's SERVICER propagated the state vector from IMU accelerometer (PIPA) data on a nominal 2-s READACCS cycle. Landing-radar altitude and velocity were blended in through a reasonableness test and a weight that shrank linearly with altitude and speed. The data entered navigation only after the crew keyed V57. The crew compared the DELTA-H display with the ground before doing so; the computer automated the blending, and the crew and ground held the gate.

### Cited Findings
- SERVICER: Eyles calls SERVICER the lowest-priority but longest job in the descent. When it overran, unfinished SERVICER instances piled up (this is the mechanism behind 1201/1202, see Q4). VERIFIED-FULLTEXT — [Eyles, Tales](https://www.doneyles.com/LM/Tales.html)
- 2-s cycle: the SERVICER source contains "WAIT TWO SECONDS FOR READACCS" (PREREAD). PIPA reads are done "TRYING TO BE VERY CAREFUL SO THAT WILL BE RESTARTABLE", and restarts re-enter at REREADAC. The fetched excerpt did not explicitly state a steady 2-s repeat period, though the 2-s guidance/navigation cycle is the widely documented design. The PREREAD wait is VERIFIED-FULLTEXT; the steady 2-s period is UNVERIFIED in this session — [Luminary099 SERVICER.agc](https://raw.githubusercontent.com/chrislgarry/Apollo-11/master/Luminary099/SERVICER.agc)
- Navigation propagation: MUNRVG is "a special average G integration routine" for thrusting flight near "an assumed spherical moon". It runs in stable-member (IMU platform) coordinates and produces HCALC (computed altitude) and HDOTDISP. VERIFIED-FULLTEXT — [SERVICER.agc](https://raw.githubusercontent.com/chrislgarry/Apollo-11/master/Luminary099/SERVICER.agc)
- Radar sampling: LRHJOB takes one altitude measurement in about 95 ms. LRVJOB takes five velocity samples in about 500 ms. VERIFIED-FULLTEXT — [SERVICER.agc](https://raw.githubusercontent.com/chrislgarry/Apollo-11/master/Luminary099/SERVICER.agc)
- DELTA-H is radar altitude minus HCALC. Before high gate the reasonableness test is skipped ("DO NOT PERFORM DATA REASONABLENESS TEST ... UNTIL AFTER HIGATE"). After high gate an update is rejected if |DELTAH| > 50 ft + HCALC/8 (comment "50 FT NOM"); a rejection branches to HFAIL. VERIFIED-FULLTEXT — [SERVICER.agc](https://raw.githubusercontent.com/chrislgarry/Apollo-11/master/Luminary099/SERVICER.agc)
- Altitude weighting is WH·(1 − H/HMAX), using LRWH and LRHMAX. No update is made above HMAX, so the weight falls linearly to zero at HMAX and rises toward WH near the surface. The weighted correction is applied to the state vector (GNUR/GNURVST). VERIFIED-FULLTEXT — [SERVICER.agc](https://raw.githubusercontent.com/chrislgarry/Apollo-11/master/Luminary099/SERVICER.agc). The LUM147 memo snippet also describes W as "the zero-altitude value of the altitude weighting function" stored as an erasable padload, with the position update scaled by W(1 − HCALC/HMAX). ABSTRACT-ONLY — [LUM147](https://ibiblio.org/apollo/Documents/LUM147_text.pdf)
- Velocity update: a velocity sample is rejected if |DV| > 7.5 ft/s + |VM|/8. Weights LRWVZ, LRWVFZ, LRWVFF and LRVMAX scale with how close the speed is to LRVMAX. LRMCTR/LRSCTR count failures and drive the VEL fail light ("IF M-S > 3, THEN TWO OR MORE OF THE LAST FOUR V READINGS WERE BAD"). VXINH inhibits the X-axis update when a Z-component error may come from lobe lock-up. VERIFIED-FULLTEXT — [SERVICER.agc](https://raw.githubusercontent.com/chrislgarry/Apollo-11/master/Luminary099/SERVICER.agc)
- Data-good handling: after bad data, the code waits before trusting the radar again ("JUST GOOD -- MUST WAIT 4 SECONDS", STILBADH/STILBADV). A bad return caused by a range-scale change is ignored (RNGSCBIT). VERIFIED-FULLTEXT — [SERVICER.agc](https://raw.githubusercontent.com/chrislgarry/Apollo-11/master/Luminary099/SERVICER.agc)
- Inhibit and permit flags: LRBYBIT ("LR BYPASS SET -- BYPASS ALL LR READING"), NOLRRBIT ("LR READ INHIBITED"), LRINHBIT ("UPDATE INHIBITED -- TEST VELOCITY ANYWAY"), and NOLRREAD (cleared to "ENABLE LR READING"). The radar is read and tested even while updates are inhibited, which is what lets the crew watch DELTA-H before accepting. At high gate, HIGATASK sets flags and queues HIGATJOB to move the antenna to its second position. VERIFIED-FULLTEXT — [SERVICER.agc](https://raw.githubusercontent.com/chrislgarry/Apollo-11/master/Luminary099/SERVICER.agc)
- Eyles: radar data could not enter navigation without crew and ground approval. Aldrin monitored DELTAH on Verb 16 Noun 68; it started near −2900 ft and later fell to about 900 ft. Verb 57 allowed navigation to incorporate the data. VERIFIED-FULLTEXT — [Eyles, Tales](https://www.doneyles.com/LM/Tales.html)
- Apollo 11 timeline: landing radar "good lock-on" at 102:38:04 MET, and Aldrin reported "Delta-H ... minus 2,900 feet" at 102:38:11. VERIFIED-FULLTEXT — [ALSJ A11 landing](https://www.apollojournals.org/alsj/a11/a11.landing.html)
- Apollo 14: Mitchell asked to accept the radar data, Houston agreed (108:09:27–33), and the updates converged at once. Kranz put the pre-update computed-altitude error at almost 4,000 ft. VERIFIED-FULLTEXT — [ALSJ A14 landing](https://www.apollojournals.org/alsj/a14/a14.landing.html)
- A later GSOP revision lists "Two-Segment LR Altitude and Velocity Weighting Functions" as a change. A Kriegsman et al. memo recommends two- or three-segment altitude weighting for braking and approach. ABSTRACT-ONLY — [R-567 Rev10 Sec5](https://www.ibiblio.org/apollo/Documents/R-567-Rev10-Section5.pdf); [Memo Kriegsman et al. 1970-02-18](https://ibiblio.org/apollo/Documents/Memo-KriegsmanEtAl700218_text.pdf)
- Eyles: a terrain model was added to the landing radar routines for Apollo 15, 16 and 17. VERIFIED-FULLTEXT — [Eyles, Tales](https://www.doneyles.com/LM/Tales.html)
- Eyles describes "IMU bob": pitch maneuvers swung the IMU, which biased the accelerometer-derived altitude-rate estimate. VERIFIED-FULLTEXT — [Eyles, Tales](https://www.doneyles.com/LM/Tales.html)

### Inferences
- The gating had three layers. (1) The computer read the radar and ran its own data-good and reasonableness tests continuously. (2) The crew saw the innovation (DELTA-H on N68) and keyed V57 to enable updates. (3) The ground compared telemetry and voiced concurrence. After acceptance, each update was a fixed-gain partial correction (gain < 1, decreasing with altitude and speed), not a Kalman filter. This is an inference from the WH(1 − H/HMAX) form.
- The reasonableness band (50 ft + H/8) is relative: wide at altitude, tight near the ground. It is checked only after high gate, so a large initial DELTA-H such as Apollo 11's −2900 ft could still be accepted during braking.

### Gaps
- Numerical padload values of LRWH, LRHMAX, LRWVZ and LRVMAX for each mission (in GSOP R-567 Sec 5 or the LUMINARY memos; fetch failed with a certificate error).
- The altitude at which velocity updates began, and any altitude-band permission logic. One NASA document snippet suggested 15–25 kft bands, but its OCR was garbled; UNVERIFIED.
- Landing radar hardware details from TN D-6849 (fetch failed): the three-beam Doppler velocity plus altimeter beam (four beams in total), frequencies and accuracies. Background knowledge only, UNVERIFIED — [TN D-6849 NTRS record](https://ntrs.nasa.gov/citations/19720016521)
- Which display noun the crew normally used for DELTA-H: Eyles says N68; other procedures reference N63. Not resolved.

## Q2. Descent programs P63/P64/P66, throttle, RCS DAP, LPD, contact light and engine stop

### Takeaway
P63 (braking) ran from ignition, starting at 10% throttle and going to full thrust at about +26 s. Guidance switched to P64 (approach/visibility) at high gate, where the crew could redesignate the target with the hand controller against the LPD reticle. Armstrong took semi-manual control in P66 (rate of descent), adjusting the descent rate in 1 ft/s steps. The crew, not the computer, commanded engine stop at or after contact light.

### Cited Findings
- Apollo 11 P63: ignition at about 102:33:05 MET (ALSJ commentary gives PDI at 102:33:07 and the transcript "Ignition" at 102:33:11) at 10% throttle; full throttle (9,870 lb) at +26 s. VERIFIED-FULLTEXT — [Eyles](https://www.doneyles.com/LM/Tales.html); [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)
- Planned throttle-down: Duke called "6 plus 25. Throttle down", and the crew reported it "on time" at about 102:39:34. VERIFIED-FULLTEXT — [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)
- High gate at 102:41:32 MET, at 7,400 ft and 125 ft/s sink rate. P64 began there and allowed redesignation through the LPD angle. ALSJ gives P64 at 102:41:35 and an LPD reading of 47 degrees at 102:42:32. VERIFIED-FULLTEXT — [Eyles](https://www.doneyles.com/LM/Tales.html); [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)
- Armstrong switched from AUTO to ATT HOLD at 102:43:08 (about 650 ft) and entered P66 at 102:43:20 (about 430 ft). Each flick of the ROD switch changed the commanded descent rate by 1 ft/s. VERIFIED-FULLTEXT — [Eyles](https://www.doneyles.com/LM/Tales.html)
- Throttle lag: the ICD specified 0.3 s; Eyles compensated for 0.2 s, and Apollo 11 and 12 flew that way. The actual DPS lag was about 0.075 s, a mismatch found by Klumpp and confirmed by a Bellcomm (Sorensen) report. Eyles argues that the "correct" 0.3 s would have made throttling unstable and invites review of that claim. VERIFIED-FULLTEXT (Eyles' own account and opinion) — [Eyles](https://www.doneyles.com/LM/Tales.html)
- Fuel: the low-level quantity light latched at 102:44:31 (about 5.6% remaining, per Fjeld's ALSJ note). The ground called "60 seconds" at 102:45:02 and "30 seconds" at 102:45:31 (time to the Bingo call). Armstrong's debrief: "We were hitting our abort limit." VERIFIED-FULLTEXT — [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)
- Touchdown and cutoff: each footpad probe was 67 in (1.73 m) long. Aldrin called "Contact Light" at 102:45:40, and the Mission Report gives touchdown at 102:45:39.9 with about 1.7 ft/s down and 2.1 ft/s left. Armstrong said "Shutdown" at 102:45:43 and Aldrin "Engine Stop" at 102:45:44. Armstrong had meant to shut down on contact light but did not; the engine ran until touchdown. VERIFIED-FULLTEXT — [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)
- The post-landing checklist was "ACA out of Detent ... Mode Control, both Auto. Descent Engine Command Override, Off. Engine Arm, Off. 413 is in" (102:45:45–47). The stick was moved because the DAP was in Attitude Hold and firing jets, and doing so reset the reference attitude. "413 is in" set AGS address 413 to tell the AGS the LM had landed, so the AGS saved gyro attitude for a surface abort. VERIFIED-FULLTEXT — [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)
- Fjeld (ALSJ) notes that an engine cutoff above about 10 ft would have produced a touchdown harder than the gear was designed for. Armstrong later said in an interview that he could have fallen from perhaps 40 ft in lunar gravity. These views conflict; Fjeld is an analyst, Armstrong is giving opinion. VERIFIED-FULLTEXT — [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)

### Inferences
- Touchdown detection was human-in-the-loop. The probes lit a light, and the crew pressed the engine stop button. There is no evidence in the sources read that the LGC cut the engine automatically on contact.

### Gaps
- Klumpp R-695 details (fetch failed): the quadratic-in-time acceleration law (target jerk), the 2-s guidance period, the throttle-recovery logic, the ~10–60% throttleable band versus the fixed full-throttle position, and the LPD increments per hand-controller click. Background knowledge only, UNVERIFIED. Abstract only: descent over about 17° of central angle and about 15 km of altitude in about 11 min — [NTRS 19740044219](https://ntrs.nasa.gov/citations/19740044219); report at [ALSJ PDF](https://www.nasa.gov/wp-content/uploads/static/history/alsj/ApolloDescentGuidnce.pdf), which returned HTTP 404 this session.
- P68 (landing confirmation) behavior and the RCS DAP structure (rates, jet-select logic) were not verified.
- Official touchdown envelope limits (vertical, horizontal, attitude) were not verified; no source read.

## Q3. AGS as independent backup; abort / abort-stage logic

### Takeaway
Only partial verification. During descent, an ABORT (DPS) or ABORT STAGE (APS) discrete forced the PGNCS into P70/P71. The AGS was a separate backup that kept its own attitude reference and was told about touchdown by the crew (address 413).

### Cited Findings
- With the abort bit set during P63, the computer would drop into P70, the abort on the descent engine. VERIFIED-FULLTEXT — [ALSJ A14](https://www.apollojournals.org/alsj/a14/a14.landing.html)
- The AGS kept its own gyro attitude, which the crew told it to save on landing (address 413) for a surface abort. On Apollo 14, the abort-masking procedure had to be reversed only "if an abort on AGS was needed". VERIFIED-FULLTEXT — [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html); [ALSJ A14](https://www.apollojournals.org/alsj/a14/a14.landing.html)
- Mitchell said that at 10,000 ft there was an "automatic" (meaning mandatory) abort without landing radar. Shepard later said he would have continued without it. This shows a mission rule could be pre-empted, at least in the commander's stated intent. VERIFIED-FULLTEXT — [ALSJ A14](https://www.apollojournals.org/alsj/a14/a14.landing.html)

### Gaps
- AGS hardware (strapdown inertial unit, its own computer) and accuracy, and which crew switch selected AGS versus PGNCS guidance, were not verified. The Apollo Experience Report on the AGS was not fetched.

## Q4. Apollo 11 1201/1202 alarms and Apollo 14 abort-switch workaround

### Takeaway
On Apollo 11, the rendezvous-radar CDU interface fed spurious counter increments that stole about 13–15% of LGC time. SERVICER overran, Executive slots filled, and BAILOUT restarts flushed stale jobs while the restart protection kept guidance running. MIT-tested restart behavior was the basis for the MOCR "go". On Apollo 14, a failing ABORT switch was masked by keying data into erasable memory to fool the abort monitor.

### Cited Findings
- 1202 meant no free core sets and 1201 meant no free VAC areas, both raised through BAILOUT. Eyles says the Executive had 8 core sets × 12 registers and 5 VAC areas × 43. Adler says 7 core sets × 12 and 5 VAC × 44. The sources conflict by one, probably over counting conventions. VERIFIED-FULLTEXT — [Eyles](https://www.doneyles.com/LM/Tales.html); [Adler/ALSJ](https://www.apollojournals.org/alsj/a11/a11.1201-pa.html)
- Cause: the RR was in SLEW or AUTO, not LGC. Its CDU counters ran at up to 6,400 pulses/s per angle, each costing an 11.7 µs memory cycle, for roughly 13–15% of computer time (Grumman later measured a maximum of 13.36%). The trigger was an 800 Hz phase mismatch between the ATCA and the LGC power supplies, which was documented but never corrected. VERIFIED-FULLTEXT — [Eyles](https://www.doneyles.com/LM/Tales.html)
- Margin: duty-cycle margin was over 15% in braking, about 13% after radar acquisition, and 10% or less with V16 N68 displayed. The crew's DELTA-H monitoring display therefore consumed some of the margin. VERIFIED-FULLTEXT — [Eyles](https://www.doneyles.com/LM/Tales.html)
- Restart design: restart protection used registered waypoints so a job could resume without double-applying changes. Restarts were triggered by power transients, a watchdog-detected endless loop, or a fixed-memory parity failure. Restarts flushed the stacked SERVICER stubs, which is why the display reverted to N63 after the P63 alarms. Adler says DSKY updating and descent-engine steering continued, and the erroneous radar jobs were not restarted. VERIFIED-FULLTEXT — [Eyles](https://www.doneyles.com/LM/Tales.html); [Adler](https://www.apollojournals.org/alsj/a11/a11.1201-pa.html)
- Decision chain: Steve Bales (GUIDO) made the go calls, supported by Jack Garman (NASA) and Russ Larson (MIT). Flight director Gene Kranz concurred, and CapCom Charlie Duke relayed to the crew. Adler says the go rested on MIT having "extensively tested the restart capability". VERIFIED-FULLTEXT — [Eyles](https://www.doneyles.com/LM/Tales.html); [Adler](https://www.apollojournals.org/alsj/a11/a11.1201-pa.html)
- Alarm timeline: 1202 at 102:38:26–30; "We're Go on that alarm" at 102:38:53, about 25 s later. 1201 at 102:42:19; "We're Go. Same type" at 102:42:25, about 6 s later. "You're Go for landing" came at 102:42:08. VERIFIED-FULLTEXT — [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)
- Apollo 14 abort-switch problem:
  - The abort bit kept showing set, starting at about 104:29:57, and tapping the panel cleared it. A loose solder ball was suspected.
  - The first idea was V25 N07 to reset LETABORT, keyed right after ignition. The exposure during manual entry was judged unacceptable.
  - The adopted fix, read up by CapCom Haise at 107:33:49, was V21 N01 ENTER 1010 ENTER 107 ENTER. It wrote a P70/P71-like code into MODREG so the abort monitor believed an abort was already in progress.
  - After ignition (PDI at 108:02:29), Shepard manually advanced the throttle at about +27.3 s, roughly 1.25 s late. Mitchell then keyed the ZOOMFLAG set (V25 N07; 101; 200; 1), the LETABORT reset (V25 N07; 105; 400; 0), and P63 restored to MODREG (V21 N01; 1010; 77) "so the landing radar weighting would be correct".
  - VERIFIED-FULLTEXT — [ALSJ A14](https://www.apollojournals.org/alsj/a14/a14.landing.html)
- Eyles' account: he wrote the abort-monitor code, the fix fooled it into thinking an abort was in progress, and the procedure was 61 keystrokes. VERIFIED-FULLTEXT — [Eyles](https://www.doneyles.com/LM/Tales.html). Secondary accounts give other counts (a "26-command sequence", "a few dozen keystrokes") and say the fix was finished about 10 min before it was needed. SECONDARY — [Astronomy](https://www.astronomy.com/observing/hacking-apollo-14-how-an-mit-computer-scientist-saved-a-lunar-landing/); [IEEE Spectrum](https://spectrum.ieee.org/amp/don-eyles-space-hacker-2650277249)
- Apollo 14 landing radar problem: the radar's scale switching at a slant range of about 63,000 ft (about 36,500 ft altitude) prevented lock-on. Mitchell expected lock by about 30,000 ft. Houston told the crew to cycle the LR circuit breaker (108:08:42–52), and the radar locked at about 18,000 ft. Shepard said the ground's call "saved the day". VERIFIED-FULLTEXT — [ALSJ A14](https://www.apollojournals.org/alsj/a14/a14.landing.html)

### Inferences
- The restart design is the key enabler. The software degraded gracefully by shedding stale work and keeping guidance and steering running, which turned the decision from "is the computer failing?" into "is the alarm rate low enough?". The ground could judge that using pre-tested knowledge.

### Gaps
- The exact alarm-rate rule Garman and Bales applied was not verified in this session.

## Q5. Mission Control's role: polls, uplinks, light-time, reserved decisions

### Takeaway
The ground ran go/no-go polls ("Go for powered descent", "Go for landing", "Stay for T1"), monitored telemetry, made the alarm and radar-acceptance calls, and supplied fixes. The crew executed the fixes, flew the final phase manually, and kept control of engine stop and the last-moment abort action.

### Cited Findings
- "Go for powered descent" was given at 102:28:08, about 5 min before PDI, relayed via Collins because of comm dropouts. "You're Go for landing" came at 102:42:08 after a White Team poll. "Eagle, you are Stay for T1" came at 102:47:06–12. VERIFIED-FULLTEXT — [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)
- Comm was intermittent during the descent ("We've got data dropout" at 102:37:35, with repeated high-gain antenna losses). VERIFIED-FULLTEXT — [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)
- Apollo 14: the ground and MIT diagnosed the faults and wrote the procedures, CapCom read them up, Mitchell keyed them and Shepard flew. Houston told the crew to cycle the radar breaker and concurred with radar acceptance. VERIFIED-FULLTEXT — [ALSJ A14](https://www.apollojournals.org/alsj/a14/a14.landing.html)

### Gaps
- The one-way light time of about 1.28–1.3 s (about 2.6 s round trip plus processing) is background, UNVERIFIED in this session.
- State-vector and REFSMMAT uplinks before PDI, and the formal division of mission-rule authority (flight director as final ground authority, commander onboard), were UNVERIFIED.

## Q6. Touchdown envelope and cutoff

### Takeaway
Touchdown was sensed by 67-inch footpad probes lighting "Contact Light", and the crew commanded engine stop manually. Apollo 11 touched down at about 1.7 ft/s vertical and 2.1 ft/s lateral.

### Cited Findings
- Touchdown facts are in Q2. VERIFIED-FULLTEXT — [ALSJ A11](https://www.apollojournals.org/alsj/a11/a11.landing.html)

### Gaps
- Design touchdown limits (commonly cited as about 10 ft/s vertical, about 4 ft/s horizontal, and attitude/rate limits) are UNVERIFIED. No source was read.

## Lessons for a simulated sensor-trust study

These are inferences built on the verified findings above.

- **Layered acceptance.** The computer always read the radar, applied a data-good check and a relative reasonableness check (|DELTA-H| < 50 ft + H/8, and |DV| < 7.5 ft/s + |V|/8), and counted failures (two or more bad in the last four lights the fail light). Entry into navigation was still gated by a human permit (V57) after a crew and ground look at the innovation. A simulation could model: auto-validity check, then shown innovation, then an explicit accept, then a fixed-gain update.
- **Smoothing, not snapping.** Accepted measurements were blended with a gain W(1 − H/HMAX), so the trust given to the radar grew as altitude fell. Velocity used a similar speed-scaled gain. Even a large initial bias (about 2,900 ft on Apollo 11, about 4,000 ft on Apollo 14) was absorbed over several 2-s cycles, which avoids steps in the guidance command. A trust study should use a scheduled gain rather than a binary replace.
- **Hold-off after recovery.** After bad data the code waited about 4 s of good data before trusting the radar again (hysteresis), and ignored glitches it knew were caused by range-scale changes. Persistence requirements belong in any trust filter.
- **Innovation visibility.** The crew was shown DELTA-H (N68), the residual, not just a "good" flag. Displaying the residual lets the human judge trust. The cost is real: N68 display ate CPU margin on Apollo 11.
- **Ground as an independent cross-check, with latency.** The ground voted go/no-go on alarms (about 6–25 s decision latency observed) and on radar acceptance, but did not directly command the vehicle. It advised, and the crew executed. Model the ground as a delayed advisory channel with veto-by-voice.
- **Graceful degradation.** Restart protection shed stale jobs and kept steering running, so an overload became a monitored-alarm condition rather than a failure. Trust logic should define safe fallback behavior when its own compute budget is exceeded.
- **Final authority stays local.** Touchdown sensing (contact light) and engine cutoff were crew actions. The commander also took semi-manual control (P66) when the automated target was unsuitable.
