from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ss = getSampleStyleSheet()
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=10, leading=14, spaceAfter=5)
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=16, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#1a3a5c"))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#1a3a5c"))
T = ParagraphStyle("T", parent=ss["Title"], fontSize=22, spaceAfter=6)
C = ParagraphStyle("C", parent=B, fontSize=8.5, leading=11)
S = []


def h1(t): S.append(Paragraph(t, H1))
def h2(t): S.append(Paragraph(t, H2))
def p(t): S.append(Paragraph(t, B))
def bl(items):
    for i in items:
        S.append(Paragraph("&bull; " + i, ParagraphStyle("bl", parent=B, leftIndent=14, firstLineIndent=-9, spaceAfter=2)))
    S.append(Spacer(1, 4))


def tbl(rows, widths):
    data = [[Paragraph(str(c), C) for c in r] for r in rows]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde6f0")), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    S.append(t); S.append(Spacer(1, 8))


S.append(Paragraph("LANTERN: Project Status and Handoff Report", T))
p("<b>Prepared 20 November 2026, updated 21 November 2026 (round 6 added; everything is now pushed)</b> for external review. Team: Abhishek Mishra (240365), Rishabh Kumar (240605), Neil Jain (240553), Khushi (240511). "
  "Mentor: Dr. Sukhandeep Kaur. BML Munjal University, Project-I, August to December 2026. Repository: AnakinSkywalker0 (GitHub), local copy D:\\newprj.")
p("<b>Everything here is simulation only.</b> No real flight data has been used. Claims are about which navigation ideas work in a simulated South Pole landing, not about real mission safety.")

h1("1. The problem in one paragraph")
p("A lunar lander without GPS navigates by combining an inertial estimate with sensor readings (a laser altimeter, a terrain map, a camera). "
  "At each moment it must decide <i>which readings to trust</i>. Trust a bad reading and the estimate is wrong; reject a good reading and the lander flies blind. "
  "Two real landers failed this way: one rejected a correct height reading at a crater edge, and one trusted noisy readings. "
  "LANTERN is a simulation study of how the navigation filter should make that trust decision, using real NASA terrain near the lunar South Pole (sites Site04 and Site01 from NASA PGDA data) and a fast test bench that can fly thousands of landings so that decision rules can be compared fairly and repeated exactly.")

h1("2. Where the project stands (headline)")
bl(["A working simulator (Python test bench plus a Unity testbed) with an extended Kalman filter and swappable <b>judges</b>: fixed gate, PITFAL-style (our single-beam reimplementation of NASA's fault-detection idea), tolerance, wait-and-see, second-opinion, ML judges, and trust v1/v2.",
    "Three rounds of pre-registered evaluation. Round 3 was run <b>once</b> on the held-out Site04 and <b>all five pre-registered rules (Q1 to Q5) were met</b>.",
    "Main finding: letting the tolerance gate follow the altimeter's current noise level (a 'noise floor') kept landing success at about 95% at eight times normal noise, against 61.6% for plain tolerance, 65.6% for the PITFAL-style baseline and 89.0% for our trust v2. No machine learning is needed.",
    "Learned (ML) judges did not beat these simple rules; an earlier claim that a shadow-aware camera is the big win disappeared under fair comparison. Two earlier results were corrected and recorded.",
    "A multi-beam altimeter extension, a round-4 development study and a round-5 comparison of eleven build-plan techniques (exploratory) were done; the best candidates were then frozen (tag prereg-round5) and run once on worlds 41-50: five of seven rules met (Student-t and delay estimation replicated; Student-t did not beat the full floor at low noise). No rule wins everywhere; the world-12 collapse is not caused by the floor misreading map error (an oracle collapses too). The round-4 held-out test was frozen (tag prereg-round4, commit 36e2942) and run once on worlds 17-20: candidate B FAILED rules R1 and R2, R3 and R4 were met. Round 6 (exploratory, 6-DOF lander dynamics) kept the ranking of the rules with a working attitude loop; see 6e. Everything was pushed on 21 Nov 2026 (commit 722aa7b)."])

h1("3. GitHub branches, tags and history")
tbl([["Ref", "Commit", "Status / meaning"],
     ["main (local and origin/main)", "722aa7b", "Current (21 Nov). Adds rounds 3-6 work: round-4/5 pre-registrations and results, 6-DOF dynamics, college report, handoff, docs/PROJECT_SUMMARY_2026-11-21.md. Pushed together with tags prereg-round4 and prereg-round5. Raw per-descent dumps (about 1.3 GB), *.raw, downloaded paper PDFs and local config files are left out of git."],
     ["origin/ml-eval", "9df6032", "Rishabh's branch. Already merged into main via PR #1 and PR #2 (merge 0f9d8df). Contains HANDOFF.md-style documentation of his ML evaluation."],
     ["tag round1", "-", "Frozen settings of the first evaluation round."],
     ["tag prereg-round2", "ca61ea6", "Frozen before the round-2 Site04 run."],
     ["tag prereg-round3", "e63c7a6", "Frozen before the round-3 Site04 run. The Site04 runner refuses to start unless this tag is the current commit and code is unchanged, and refuses a second run."]],
    [4.2, 2.0, 10.8])
p("<b>Commit history (17 commits, 9 by Abhishek, 8 by Rishabh):</b>")
tbl([["Date", "Author", "Commit", "What"],
     ["2026-10-18", "Abhishek", "60c99fe", "LANTERN Unity testbed, Python test bench, docs"],
     ["2026-10-19", "Abhishek", "ba22256, 6bbda5c", "Full Monte Carlo, controlled comparisons, replay scene, progress log"],
     ["2026-10-19", "Abhishek", "e406319, ca61ea6, b4c2a2c", "Round 2: camera survey, trust layer v2, pre-registration, freeze, Site04 results, paper draft"],
     ["2026-10-19", "Abhishek", "5853a84", "Full chronological project log (markdown and PDF)"],
     ["2026-11-13", "Rishabh", "08458d2", "Leave-one-world-out evaluation of the fault-or-terrain classifier"],
     ["2026-11-14", "Rishabh", "2c4c2a7, 05dc94c", "Corrected-label ml2 judge, evaluation tooling, diagnostics, handoff (PR #1)"],
     ["2026-11-14", "Rishabh", "ccb643f, 0d77ffc", "Learned measurement-noise model for ml2; handoff status correction"],
     ["2026-11-14", "Rishabh", "0f25f69, 9df6032, 0f9d8df", "Non-ML control, fresh-worlds test, classifier ablation, non-ML rule gate, decision points (PR #2)"],
     ["2026-11-20", "Abhishek", "e63c7a6", "Round-3 freeze: noise floor, terrain variance, noise-aware label switches"],
     ["2026-11-20", "Abhishek", "5b26430", "Round-3 Site04 result, ml-eval reproduction, project documents"]],
    [2.2, 2.0, 4.3, 8.5])
p("<b>Superseded note (written 20 Nov, before the 21 Nov push; all of this is now committed in 722aa7b except the exclusions above):</b> multi-beam sensor and round-4 switches in sim/engine.py (a backup of the pre-round-4 engine and a patch of the multi-beam code are in out/round4/), sim/round3_multibeam*.py, sim/round4_*.py, tests/test_multibeam.py and tests/test_round4_*.py, docs/ROUND4_DEV_RESULTS.md, docs/PREREG_ROUND4.md, docs/WORLD12_DIAGNOSIS.md, docs/NEXT_DIRECTION_REVIEW_AND_BUILD.md, out/round3/multibeam_*.csv, out/round4/, the college report build in report/, and project skills in .claude/skills/. Uncommitted since: round-5 switches in sim/engine.py (backup in out/round5/), sim/round5_*.py, tests/test_round5_switches.py, docs/ROUND5_DEV_RESULTS.md, out/round5/. The round-5 freeze is committed locally too (f742d08, tag prereg-round5). Committed locally on main: the round-4 freeze (36e2942, tag prereg-round4: engine, runner, dev script, pre-registration, tests). The owner asked for the push on 21 Nov and it was done.")

h1("4. Rishabh's work (branch ml-eval)")
p("Rishabh's branch asked: <i>can machine learning decide fault versus terrain better than simple rules?</i> It added 52 files (about 3,200 lines): the ML evaluation tools (ml_eval.py, ml_features.py, ml_labels.py, ml_train.py, ml_faults.py), the ml2 experiments (ml2_*.py), checks that old judges are unchanged (check_unchanged.py, tests/ref_old_judges.npz), and result tables under out/ml_eval, out/ml_eval_v2, out/ml_faults, out/ml_labels and out/ml2.")
bl(["<b>Leave-one-world-out evaluation</b> of the fault-or-terrain classifier: tested whether a classifier trained on some terrains generalises to an unseen one.",
    "<b>Corrected labels (ml2):</b> found that the simulator's ground-truth fault label used the nominal noise, so at high noise it mislabelled normal readings as faults. His corrected-label judge became the basis for the 'noise-aware label' switch.",
    "<b>Learned noise model:</b> an ML model of measurement noise; tested at several noise levels.",
    "<b>Controls:</b> a non-ML control, a fresh-worlds test and a classifier ablation. These showed that most of the ML gain came from the noise-aware structure, and a non-ML rule gate reached about 86.5% where the ML judge reached its best, so ML's value was largely replaceable by a simple rule.",
    "<b>Two engine findings</b> that became round 3: (i) readings that pass the gate should still carry terrain and map variance; (ii) a running innovation-size noise estimate should floor the tolerance gate.",
    "On 20 Nov the handoff steps were run and reproduced <b>row for row</b> (output in out/ml2_repro_2026-11-20)."])

h1("5. Round 3 (pre-registered, run once on Site04)")
p("<b>What was tested:</b> three default-off switches in sim/engine.py: <b>tol_noise_floor</b> (tolerance judge follows the running noise estimate), <b>terrain_R</b> (terrain and map variance on unflagged readings for wait, second, ML) and <b>fault_label_noise_aware</b> (bookkeeping only). They were screened on tuning worlds, checked on three fresh procedural worlds (14 to 16), then frozen and tagged and run once on Site04 with 500 descents per cell, seed 20261201.")
tbl([["Rule", "Statement", "Outcome"],
     ["Q1", "Noise floor beats plain tolerance by at least 10 points at x4, x8, x16", "Met: +17.0, +33.0, +48.0"],
     ["Q2", "At or above PITFAL-style at x8 and x16; at most 3 below in cliff + faults", "Met: +29.0, +52.2, +14.2"],
     ["Q3", "At most 3 below trust v2 in cliff + faults; at or above at x8 (weak test)", "Met: +2.4 and +5.6 (2.4 is within noise)"],
     ["Q4", "Terrain variance lifts wait and ML by at least 5 points at nominal noise and x8", "Met: wait +13.0/+22.0; ML +14.2/+8.6"],
     ["Q5", "Trust v2 misses fewer than 10% of faults at x8 with the noise-aware label", "Met: 6.6% (52.6% under old label)"]],
    [1.2, 10.3, 5.5])
tbl([["Landing success % (Site04)", "PITFAL", "Trust v2", "Tolerance", "Tol + floor", "Wait+terr", "ML+terr"],
     ["Cliff + faults", "83.4", "95.2", "97.0", "97.6", "96.0", "90.2"],
     ["x2 noise", "81.8", "96.2", "91.2", "96.0", "92.4", "73.4"],
     ["x4 noise", "84.8", "94.6", "78.0", "95.0", "92.0", "28.4"],
     ["x8 noise", "65.6", "89.0", "61.6", "94.6", "55.4", "32.8"],
     ["x16 noise", "38.6", "57.2", "42.8", "90.8", "35.2", "22.6"],
     ["Delayed (time-stamped)", "70.8", "86.8", "96.0", "96.4", "94.0", "92.2"],
     ["Dropout (exploratory)", "33.6", "37.4", "44.6", "49.6", "37.2", "32.2"]],
    [4.4, 2.0, 2.0, 2.2, 2.2, 2.2, 2.0])
p("<b>Not improved:</b> second-opinion judge stays weak; ML still fails at x4; altimeter dropout stays low for every judge; the noise-floor judge lets more faults through than trust v2 (9.8% vs 6.6% at x8); a wrong map and delayed readings without time stamps were not tested with the new switches. 95% intervals are about plus or minus 2 to 4 points.")

h1("6. Multi-beam consensus extension (today, tuning/fresh worlds only)")
p("Motivation: the real NASA PITFAL method uses multi-beam Navigation Doppler Lidar with a consensus check across beams, whereas ours is single-beam. We added a 3-beam slant-range sensor (beams canted 22.5 degrees, <b>assumed geometry</b>), with independent noise per beam, two fault modes (one beam at a time, or all beams at once), and two judges: PITFAL multi-beam and tolerance multi-beam (optionally with noise floor and consensus). 13 new unit tests pass; legacy results are unchanged when beams are off.")
p("Rules written before the fresh-world run (worlds 14 to 16, 100 descents each):")
tbl([["Rule", "Statement", "Result"],
     ["M1", "Consensus helps by at least 3 points against independent beam faults (cliff + faults)", "<b>Not confirmed</b>: change under 1 point"],
     ["M2", "Floor + consensus within 3 points of PITFAL multi-beam at cliff, x4, x8, x16", "<b>Confirmed</b>; far ahead at x16 (about 99% vs 66%)"],
     ["M3", "Common-mode faults: floor within 3 points of PITFAL multi-beam", "<b>Confirmed</b>"]],
    [1.2, 9.6, 6.2])
bl(["With three beams even the PITFAL-style judge reaches about 98% at x8 (against about 59% single beam): much of the earlier gap was the sensor, not the judging rule.",
    "<b>World 12 (updated, round-4 development study):</b> on the tuning worlds the noise-floor version collapses on procedural world 12 (6% at x4 noise). Our first explanation, that the floor mistakes a wrong map for sensor noise, is <b>not supported</b>: a gate that knows the true noise level (oracle, not flyable) collapses on the same terrain. Any gate widened to the right noise size lets harmful readings in there; the tight gate acts as a terrain-consistency filter. Static terrain statistics do not single world 12 out. Floor in the update only is safe (98-100%) but gives up most of the high-noise gain.",
    "Caveats: assumed beam geometry; my own interpretation of PITFAL's consensus check; 3 readings per step is a sensor advantage over single beam; independent beam noise favours averaging; no Site04 run was made on this extension."])

h1("6b. Round-4 development study (exploratory, 20 Nov 2026)")
p("Built from the owner's review plan (docs/NEXT_DIRECTION_REVIEW_AND_BUILD.md). New default-off switches in sim/engine.py: where the floor enters (gate, update, both), true-noise oracle, terrain variance at each beam's footprint, AR(1) correlated noise, a map-independent second-difference noise estimator, a VB-AKF judge, a configurable wrong-map offset. Checked: 26 unit tests pass and the old judges are bit-identical (check_unchanged: UNCHANGED). Grid: 9 world/seed cells, 100 descents each (tuning worlds, fresh 14-16, Site01; Site04 untouched).")
tbl([["Three beams, success %", "Cliff", "x4", "x8", "x16"],
     ["PITFAL-style multi-beam", "92", "96", "98", "69"], ["Floor in gate and update", "85", "78", "91", "99"],
     ["Floor in update only + footprint terrain", "97", "98", "98", "76"], ["True-noise oracle (not flyable)", "93", "78", "82", "96"]],
    [7.0, 2.5, 2.5, 2.5, 2.5])
bl(["Single beam: the floor in both places is close to the oracle (93/87/82 at x4/x8/x16 against 94/92/91) and a 100 m map offset does not make it worse (65% against 56% plain tolerance). A 2 km wrong map and delayed readings without time stamps defeat every rule.",
    "The map-independent second-difference noise estimate matches the floor with white noise but falls to about 28% with strongly correlated noise (phi 0.9) against about 50% for the floor: it works only for near-white noise.",
    "Terrain spread where the canted beams land is 4-15 times the spread under the vehicle at 3000 m height in every procedural world, so nadir terrain variance is a poor stand-in at altitude.",
    "Held-out result (run once, frozen commit 36e2942, worlds 17-20, n=200, docs/ROUND4_RESULTS.md): R1 NOT met (B 5 points below pitfal_mb at x8), R2 NOT met (B 3 to 6 below at x16), R3 MET (floor in both places did not collapse; 3-6 points above pitfal_mb at low noise), R4 MET (single-beam floor 68.2% vs plain tolerance 55.8% with a 100 m map offset). Means at x16 (independent): pitfal_mb 63.5, B 60.4, A 80.2, tolerance 38.1, oracle 83.1. The development gain of B did not replicate. A's high-noise advantage was not pre-registered (exploratory). World 20 is hard for pitfal_mb (26-37% at low noise); world 19 is near 100% for all."])

h1("6c. Round-5 development comparison (exploratory, 21 Nov 2026)")
p("Built from docs/LANTERN_Architecture_and_Build_Plan.docx. Eleven techniques were added to sim/engine.py as default-off switches (bit-identical when off, tests/test_round5_switches.py, 11 tests; check_unchanged --quick UNCHANGED): A1 joint three-beam update, A2 learned gate selector (trained on new worlds 27-32), A3 IMM-style noise modes (one filter state), A4 delay estimation without time stamps, A5 map-offset search (first version), B1 conformal gate limits, B2 Student-t weighting, B3 CUSUM, B4 soft camera weighting, B7 solution separation (single-fault), B8 second altimeter (assumed model); plus stuck-at, drift, scale-factor and beam-dropout faults and NEES. B5 (point-mass filter) and B6 (KalmanNet) were NOT built. Compared on the nine development cells, 100 descents each, untuned constants (docs/ROUND5_DEV_RESULTS.md, out/round5/).")
tbl([["Single beam, success %", "Cliff", "x8", "x16", "Delayed, no stamps", "Dropout", "Stuck", "Drift", "2 km map"],
     ["PITFAL-style", "84", "70", "40", "0", "54", "80", "78", "4"], ["Noise floor (round 3)", "92", "87", "82", "4", "70", "90", "94", "17"],
     ["IMM-style noise modes", "97", "93", "94", "5", "74", "92", "97", "9"], ["Student-t + floor", "94", "94", "93", "3", "70", "64", "95", "19"],
     ["Delay estimation", "-", "-", "-", "54", "-", "-", "-", "-"], ["Soft camera weighting", "100", "100", "-", "-", "-", "-", "-", "-"]],
    [4.0, 1.2, 1.2, 1.2, 2.0, 1.5, 1.3, 1.2, 1.6])
tbl([["Three beams, success %", "Cliff", "x4", "x8", "x16", "Beam out", "2 km map"],
     ["PITFAL-style multi-beam", "92", "96", "98", "69", "94", "4"], ["Floor in gate and update", "85", "79", "88", "98", "85", "6"],
     ["Floor in update only", "97", "98", "98", "76", "98", "10"], ["Student-t + floor", "99", "92", "96", "99", "91", "6"],
     ["Joint update / selector / solution separation / conformal", "83-85", "79", "86-88", "98", "82-85", "5-9"]],
    [6.0, 1.5, 1.5, 1.5, 1.5, 1.8, 1.8])
bl(["Clearest gains (exploratory): delay estimation (4% to 54%), soft camera weighting (cliff 92 to 100), Student-t and IMM-style at high noise with one beam (+10 to +11 at x16), Student-t with three beams (best mean 94 and best worst case 87 over noise/fault conditions; on the collapsing world 12 at x4 it reaches 61-63% against 7% for the full floor).",
    "No gain: joint update, learned selector (99.9% accurate on held-back worlds but the floor gate was right on 99% of disagreement rows), conformal limits (let faults in: stuck-at 27%), solution separation (identical to the joint update: never fired). Harmful: CUSUM (38% valid readings rejected). No rule handles the 2 km wrong map (at most 31%); map-offset search found it in about a third of descents.",
    "Caveats: about ten candidates compared on nine cells (winner's curse); B8's second altimeter is modelled as undelayed so its delayed-reading 83% is an artefact; missed-fault percentages are not comparable for Student-t (no accept/reject); every rule is overconfident (NEES far above its ideal); nothing was run on held-out worlds 41-50, worlds 17-20 or Site04."])

h1("6d. Round-5 held-out result (21 Nov 2026, run once, frozen commit f742d08, tag prereg-round5)")
p("Worlds 41-50 (procedural, never used before), seed 20261221, 200 descents per cell, three beams (assumed geometry) with independent and common-mode faults plus single-beam rules; docs/PREREG_ROUND5.md, docs/ROUND5_RESULTS.md, out/round5/heldout.csv. <b>Five of seven rules met.</b>")
tbl([["Rule", "Verdict", "Values"],
     ["S1 Student-t within 3 points of PITFAL-style multi-beam at cliff, x4, x8", "MET", "-1.3 to +4.5"],
     ["S2 Student-t at least 3 above it at x16", "MET", "+18.8 / +20.7"],
     ["S3 Student-t at least 3 above the full floor at cliff, x4, x8", "NOT met", "-1.8 to -4.3 (slightly below)"],
     ["S4 Student-t at least 50% in every world at cliff, x4", "MET", "lowest world 56%"],
     ["S5 Delay estimation +20 points with no time stamps", "MET", "+49.3 (51% vs 1.5%)"],
     ["S6 Soft camera +3 points at cliff and x8", "NOT met", "cliff +2.8 (just short), x8 +9.3"],
     ["S7 One-beam Student-t +3 at x16", "MET", "+8.8"]],
    [8.0, 1.8, 6.0])
tbl([["Three beams, independent faults, success %", "Cliff", "x4", "x8", "x16"],
     ["PITFAL-style multi-beam", "89", "90", "90", "69"], ["Floor in gate and update (A)", "92", "94", "92", "88"],
     ["Floor in update only (B)", "91", "91", "88", "71"], ["Student-t + floor (S)", "88", "91", "89", "87"]],
    [7.0, 2.0, 2.0, 2.0, 2.0])
bl(["The development edge of Student-t over the full floor at low noise did not replicate; unplanned (exploratory) observation: the full floor in both places was the best three-beam rule here and did not collapse on any world; worlds 41, 44, 47 are hard for every rule.",
    "Still open: 2 km wrong map (at most 5%), unstamped delays (51% with estimation vs 90% with true stamps), stuck-at faults for Student-t (development finding), overconfident estimates. Not tested: new real site, real sensor data.",
    "Worlds 41-50 are now used; any further confirmatory test needs fresh worlds and a new pre-registration."])

h1("6e. Round 6: 6-DOF lander dynamics (exploratory, 21 Nov 2026)")
p("Code: sim/dyn6.py and switch <i>dyn6=</i> in sim/engine.py (default off, bit-identical when off; tests/test_dyn6.py, 17 tests); study sim/round6_dyn6.py; results docs/ROUND6_DYN6_RESULTS.md, out/round6/. Nine development worlds, 60 descents per cell; never Site04 or reserved worlds; not pre-registered. <b>All vehicle numbers are assumed.</b> Model: one body-fixed engine (thrust along body z, throttle lag 0.3 s), torque-limited attitude control (800 N m), thrust misalignment 0.15 deg and CoM offset 2 cm, delta-angle gyro plus star tracker, accelerometer rotated with the estimated attitude, body-fixed beams, RCS propellant, thrust tilt capped at 35 deg, touchdown also needs tilt up to 12 deg and rate up to 5 deg/s. Not modelled: slosh, flex, engine transients, plume, gear crush; filter process noise excludes attitude error.")
tbl([["Success %, x16 noise", "Single beam 3-DOF", "6-DOF", "Three beams 3-DOF", "6-DOF"],
     ["PITFAL-style", "44", "34", "73", "69"], ["Floor in gate and update (A)", "82", "76", "98", "100"], ["Student-t + floor", "93", "75", "99", "100"]],
    [5.0, 3.0, 2.0, 3.2, 2.0])
bl(["The rule ranking holds with a working attitude loop: three beams at x16, floor and Student-t about +30 over PITFAL-style (95% interval 26 to 34); one beam, floor +43.",
    "Student-t's low-noise edge over the floor disappears (+13.5 to -0.4, three beams, cliff), matching the round-5 held-out result; single-beam Student-t falls below the floor at x8 and cliff.",
    "Single-beam landing is lower than 3-DOF in 8 of 9 cells (up to 20 points); three-beam landing is higher at low noise (untested explanation: actuator lag smooths noisy commands). This does not mean 6-DOF is easier.",
    "A sluggish vehicle (3-11%) and a degraded one (0-0.4%) fail with every rule; these say nothing about the altimeter rules, only that guidance and attitude sensing fail first. Needed next: vehicle-tuned guidance and attitude error in the filter.",
    "Real flight data: raw descent telemetry of modern landers is not public (web search, nothing downloaded); candidates are ISRO PRADAN science data, Morpheus/ALHAT papers on NASA NTRS and Apollo guidance code."])

h1("7. What we are aiming for")
bl(["<b>Deliver the Project-I report</b> and a clear, honest statement of which trust rules work and when.",
    "Decide whether to pre-register the full floor in both places against Student-t weighting and PITFAL-style on fresh worlds and a new real site (worlds 17-20, 41-50 and Site04 are used). Then consider a second real site (needs a PGDA download, not requested yet), delayed readings without time stamps and realistic map-error fields.",
    "The 2 km wrong map and delayed readings without time stamps remain unsolved for every rule tested.",
    "Longer term, move beyond simulation: public flight data is scarce. Candidates are NASA Langley / JAXA descent data outreach, Blue Ghost SCALPSS and Chang'e landing-camera datasets (none requested yet).",
    "Compared with the PITFAL paper: our reimplementation is single-beam and in simulation; the multi-beam extension narrows that gap but is unvalidated against real sensor data."])

h1("8. Deadlines and report status")
tbl([["Milestone", "Date", "Status"],
     ["First draft with supervisor", "20 Nov 2026", "Draft exists: report/LANTERN_Project_Report.docx and .pdf (54 pages, 11 figures, 26 tables, 29 references), follows the supplied front-page and body-format templates. Round 3, the round-4 and round-5 held-out results, the exploratory round-4 and round-5 studies and round 6 (6-DOF) are included."],
     ["Final draft + plagiarism report", "27 Nov 2026", "Plagiarism report not yet produced."],
     ["Printed, signed spiral report", "2 Dec 2026", "Needs supervisor signature."]],
    [4.5, 3.5, 9.0])
p("<b>Known blanks in the report:</b> Neil's and Khushi's contribution lines, mentor designation, supervisor signature, plagiarism report page. Abhishek's and Rishabh's contribution lines in Table 1.1 are inferred from git history and should be confirmed. The acknowledgement contains an AI-use statement; check the university's rules on this.")

h1("9. Evidence rules the project follows")
bl(["Decision rules are written before runs; Site04 (held-out) is run once after a tagged freeze; the runner enforces this.",
    "Selection is made on tuning worlds, confirmation on fresh worlds; exploratory results are labelled exploratory; earlier errors are corrected openly.",
    "Simulation only; differences of a few points per cell are within noise.",
    "Do not run anything on Site04, edit frozen settings, commit, push or move tags without the owner's explicit say-so."])

h1("10. Suggested review questions for the reviewer")
bl(["Is the noise-floor gate a sound idea, or is it hiding failures (more faults accepted: 9.8% vs 6.6%)?",
    "The oracle also collapses on world 12: is that a real property of multi-beam fusion on that terrain, or a defect in the beam model (assumed geometry, one-after-another fusion of beams that share position error)?",
    "Is the multi-beam geometry and consensus rule a fair stand-in for NASA's PITFAL? What would make the comparison fairer?",
    "Are the pre-registration and freeze procedures strong enough to support the claims in the report?",
    "What is the best plan for validating against real data?"])

h1("11. Contents of the attached zip")
bl(["01_this_report: this PDF.",
    "02_college_report: report/LANTERN_Project_Report.pdf and .docx (current draft, includes round 6).",
    "03_docs: project documents (round-3 to round-5 pre-registrations and results, round-6 6-DOF results, project summary, world-12 diagnosis, review plan, progress, full log, handoffs, protocols).",
    "04_code: sim/ and tests/ (including uncommitted multi-beam code), CLAUDE.md, README.md.",
    "05_results: out/round3, out/round4 (development grid, audits, engine backup and multi-beam patch) and out/ml2_repro_2026-11-20 result tables.",
    "06_git: branch, tag and commit listings."])

SimpleDocTemplate("D:/newprj/handoff/LANTERN_Handoff_Report.pdf", pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm,
                  title="LANTERN Project Status and Handoff Report").build(S)
print("ok")
