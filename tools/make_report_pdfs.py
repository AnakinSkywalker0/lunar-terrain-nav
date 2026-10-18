"""Builds docs/Project_Description.pdf and docs/Progress_Report.pdf (reportlab). Run: python tools/make_report_pdfs.py"""
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
os.makedirs(DOCS, exist_ok=True)
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=18, spaceAfter=8, textColor=colors.HexColor("#1f3d2b"))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1f3d2b"))
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9.6, leading=13)
SM = ParagraphStyle("SM", parent=B, fontSize=8.2, leading=10.5, textColor=colors.HexColor("#444444"))
BUL = ParagraphStyle("BUL", parent=B, leftIndent=12, bulletIndent=2)


def para(t, s=B): return Paragraph(t, s)
def bullets(items): return [Paragraph(i, BUL, bulletText="•") for i in items]


def table(rows, widths, head=True):
    t = Table([[Paragraph(str(c), SM) for c in r] for r in rows], colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bbbbbb")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if head: st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3efe7")))
    t.setStyle(TableStyle(st))
    return t


def img(path, width_mm):
    from PIL import Image as PI
    p = os.path.join(ROOT, path)
    w, h = PI.open(p).size
    return Image(p, width=width_mm * mm, height=width_mm * mm * h / w)


def build(name, story, title):
    def footer(c, d):
        c.saveState(); c.setFont("Helvetica", 7.5); c.setFillColor(colors.grey)
        c.drawString(18 * mm, 10 * mm, f"{title} - Sensor Trust for Lunar South Pole Landing (LANTERN)")
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}"); c.restoreState()
    SimpleDocTemplate(os.path.join(DOCS, name), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                      title=title, author="LANTERN project").build(story, onFirstPage=footer, onLaterPages=footer)


# =============================================================== PROJECT DESCRIPTION
def description():
    s = [para("Sensor Trust for Lunar South Pole Landing", H1),
         para("Project description - LANTERN simulation testbed", H2),
         para("A lunar lander's navigation filter should trust each sensor according to the terrain and lighting ahead, "
              "so that a real cliff is not mistaken for a broken sensor and a blinded camera is not believed. The project "
              "tests this by landing a simulated lander on real NASA South Pole terrain."), Spacer(1, 4),
         para("1. The problem", H2),
         para("During powered descent a lander fuses a laser altimeter, an optical camera and an IMU. With a fixed outlier gate and fixed "
              "sensor weights the filter cannot tell a real terrain discontinuity, or a shadowed featureless scene, from a sensor fault. "
              "It then either rejects valid altimeter data at crater rims (the HAKUTO-R M1 failure, April 2023) or keeps trusting a camera "
              "that cannot see in shadow (a contributor to IM-2, March 2025). The question is how to adjust, ahead of time and along the planned "
              "trajectory, how much the filter trusts each sensor, using known terrain and illumination."),
         para("2. Proposed solution: context-aware sensor trust layer", H2),
         para("For every altimeter reading the trust layer asks four questions in order:"),
         ] + bullets([
        "<b>Is it physically possible?</b> Find the lowest and highest ground on the map within the area where the lander might be. A reading that fits nowhere on the map is a fault and is rejected.",
        "<b>Probation.</b> A surprising but possible reading is neither believed nor rejected at once. For 2-3 s the lander watches the next readings; if they agree with each other and follow the map's shape they are accepted and the height is reset, otherwise they are rejected.",
        "<b>Camera and shadow.</b> The map and Sun position say whether the ground is lit. In darkness the camera is not used; in partial light it is used with less weight.",
        "<b>No map coverage.</b> Outside the map the standard fixed rule is used with probation, in a more cautious mode."]) + [
         para("The trust layer adds map-driven terms to the standard chi-square gate: the variance of DEM heights inside the position-uncertainty ellipse, and the "
              "LOLA height error from the PGDA error map. Seven ways of judging a surprising reading are compared on identical descents: fixed rule (baseline), "
              "PITFAL-style, map tolerance, wait-and-see, second opinion, ML classifier and the full four-step rule."),
         para("3. Data", H2),
         para("NASA PGDA Product 78 (Barker et al.), Site04 Shackleton rim: a 16 x 16 km tile at 5 m/pixel (3200 x 3200), spanning -2848 m to +1805 m (4.65 km of relief), slopes up to about 70 degrees. "
              "Along one track across the rim the ground falls 4.5 km over about 9 km. With the Sun 2 degrees above the south-east horizon at least 51% of the tile is in cast shadow, and another 46% cannot be classified "
              "from this tile alone because terrain up to about 130 km away can cast shadows. The slope GeoTIFF supplied in <i>data/</i> is truncated, so slope is derived from the elevation file. Site01 is not present in this repository."),
         img("out/site04/01_elevation_slope.png", 170), para("Figure 1. Site04 elevation (left) and slope (right).", SM),
         para("4. System architecture", H2),
         table([["Layer", "What it does", "Where"],
                ["Terrain", "PGDA DEM converted to a Unity heightmap (2049 px, 16 km); procedural crater worlds for tuning and training", "LANTERN/Assets/Terrain, tools/make_heightmap.py, sim/world.py"],
                ["Lighting", "Directional Sun at 1.5-3 degrees with cast shadows; shadow rasters from the DEM", "Site04SceneBuilder.cs, tools/render_site.py"],
                ["Physics (Unity)", "Rigid-body lander, lunar gravity 1.62 m/s2, throttleable engine, fuel with Isp 300 s, legs", "LanderController.cs"],
                ["Guidance (Unity)", "Descent autopilot: free-fall coast, speed-profile braking, upright hold; optional time warp", "DescentAutopilot.cs"],
                ["Live scan (LUMEN)", "64x64 lidar raycasts, height patch, match to stored map, position correction with confidence; patch cell grows with altitude", "Assets/Scripts/Lumen/"],
                ["Data logging", "One CSV per run plus a one-line summary per run", "TelemetryLogger.cs -> out/runs/"],
                ["Fast test bench (Python)", "Batched simulator for hundreds of seeded descents: sensors, faults, EKF, judges, scenarios", "sim/engine.py, sim/world.py, sim/pipeline.py"],
                ["Replay (Unity)", "Side-by-side replay of recorded landings with a ghost at each filter's estimate", "ReplayPlayer.cs, ReplaySceneBuilder.cs"]],
               [28, 92, 54]),
         para("5. Objectives and experiments", H2),
         table([["#", "Objective (from the project plan)", "Status"],
                ["O1", "Hazard (cliff) and blind-spot (shadow) maps for Site04 and Site01", "Done inside the test bench: cliff (terrain-height spread) and shadow (lit-fraction) statistics from the DEM and Sun position"],
                ["O2", "Trust layer producing gate width and measurement noise, with fault-vs-terrain check", "Done and evaluated: sim/engine.py (500 runs per scenario)"],
                ["O3", "Reproduce baseline failures (cliff, shadow, delay, dropout)", "Done: cliff failure reproduced (fixed rule fails 99.6% of runs); shadow, delay and dropout scenarios run"],
                ["O4", "Compare baseline, PITFAL-style and trust layer over ~500 Monte Carlo runs per scenario", "Done: 500 runs per cell, 11 judges and ablations, 95% intervals"],
                ["O5", "Release Unity project, code, scenarios and a side-by-side replay", "Done: Site04Replay scene plays a recorded descent with all three filters side by side"],
                ["O6", "Site-change robustness (unseen site, divert, wrong or missing map)", "Done: unseen site, mid-descent divert, shifted map, missing map"],
                ["O7", "Live 3D scan extension with three-way check", "Done: LUMEN in Unity; scan fix and three-way check in the test bench"]],
               [10, 100, 64]),
         para("Metrics: landing success (upright within speed and tilt limits), altitude error (RMS), false rejection of valid altimeter readings, missed injected faults, "
              "camera weight in shadow, fuel left at touchdown, and success on an unseen site compared with the tuned site. Landing success here means: vertical speed at most 2 m/s, horizontal speed at most 1.5 m/s, ground slope at most 10 degrees, fuel remaining."),
         para("6. Fair-testing rules (fixed before any experiment)", H2),
         ] + bullets([
        "The onboard map differs from the simulated Moon (unmapped craters and roughness, small registration shifts, height noise).",
        "Count both mistakes: real terrain wrongly rejected and faults wrongly believed.",
        "Include faults exactly at cliffs and faults together with cliffs.",
        "Tune and train on procedural terrain only; test on Site04, never used for tuning.",
        "About 500 runs per scenario with fixed seeds, reporting success with 95% intervals.",
        "Every method sees the same descents, noise and faults (common random numbers).",
        "The hundreds of landings run in the fast Python bench; Unity replays selected landings."]) + [
         para("7. Scope and assumptions", H2),
         para("In scope: powered descent to touchdown with a laser altimeter, optical camera and IMU, on real DEMs plus procedural terrain. Out of scope: orbit and deorbit, flight hardware, certification, boulder avoidance, engine failures, "
              "sensors that never switch on, plume dust (planned later extension). Assumptions: the planned trajectory is known before descent; the DEM's stated height error bounds map error."),
         para("8. Known limits stated up front", H2),
         ] + bullets([
        "A fault that is a constant offset lasting longer than the probation window looks like terrain and passes probation.",
        "Delayed altimeter readings carry a steady offset; probation is expected to help only partly.",
        "A dead altimeter (IM-1) is not solved by trust logic.",
        "The simulated camera model and the 'real Moon' roughness are simplified stand-ins."])
    build("Project_Description.pdf", s, "Project Description")


# =============================================================== PROGRESS REPORT
def progress():
    s = [para("Progress Report and Results (round 2)", H1),
         para("Sensor Trust for Lunar South Pole Landing - LANTERN testbed, 19 October 2026. Design and hypotheses were fixed in docs/PREREG.md (git tag prereg-round2) before the Site04 run.", SM), Spacer(1, 4),
         para("Conclusions in plain words", H2),
         ] + bullets([
        "<b>The HAKUTO-R failure is real and reproducible.</b> A filter with a fixed rule and a coarse terrain reference rejects 99% of good altimeter readings on Site04 and the lander is lost in 499 of 500 runs.",
        "<b>The big fix is simply putting the terrain map into the filter.</b> Success goes from 0.2% to 82% (PITFAL-style) and to 97% with a plain map-tolerance gate that allows bigger surprises where the map is bumpy.",
        "<b>The four-step rule's own ingredients add little in the cliff cases.</b> Trust v2 (97%) matches the plain tolerance gate (97%); probation changes nothing (95.0% without it, 94.6% with it, v1).",
        "<b>Where trust v2 clearly wins:</b> a noisy altimeter in shadow (88% vs 64%), no map at all (91% vs 3%) and a mid-descent divert (91% vs 74%). The price: it is fooled by faults more often in the noisy case (52% vs 33%).",
        "<b>Where it fails badly:</b> a noisy altimeter in good light (39% vs 99.5% for PITFAL-style) and a map shifted by 2 km (1% vs 35%). Its physical-possibility check rejects readings that do not fit the map.",
        "<b>The camera lesson:</b> a navigation camera must never be used without its matcher's confidence (every fix used: 0.4-3% success). Predicting darkness from the Sun and terrain adds nothing over the matcher's own confidence (it is slightly worse).",
        "<b>Delayed readings:</b> the 83% for trust v2 comes entirely from time-stamping the readings. With the same time stamps the plain tolerance gate scores 97.6% and PITFAL-style 74%; without time stamps trust v2 scores 0%.",
        "<b>Round 1's headline (shadow-aware camera is the big win) did not survive a fair camera baseline.</b> That is the main scientific outcome of this round."]) + [
         para("1. Verified in Unity", H2),
         table([["Item", "Result"],
                ["Descent", "From 102.5 km to a flat Site04 spot: touchdown at t = 583-587 s, 0.50 m/s vertical, 0 m/s horizontal, 0.0 deg tilt, 251 kg fuel left, exactly on target"],
                ["Live scan (LUMEN)", "Fix from 2463 m down (patch cell grows with altitude). Error 47 m at 2205 m, 14.5 m at 921 m, 4 m at 155 m; median 8.9 m over 108 fixes. No fix below ~80 m"],
                ["Replay scene", "Site04Replay plays a recorded descent with the three filters side by side, with true lander, estimate ghost, altitude error, gate, camera trust bar and learned noise level"]],
               [34, 140]),
         Spacer(1, 3), img("out/replay_round2.png", 150),
         para("Figure 1. Unity replay of one descent (cliff + faults, run 7): the fixed-gate lander (red) hovers 1268 m up believing it is 75 m below the surface; the PITFAL-style (yellow) and trust v2 (green) landers have landed.", SM),
         PageBreak(),
         para("2. Camera reliability measured in Unity", H2),
         para("300 paired nadir images on Site04 (true Sun vs a prediction from the map with 0.05-0.25 deg Sun-elevation error and +-1 deg azimuth error; reflections off so shadows are dark; read noise 2 DN plus shot noise), matched with a normalised-cross-correlation landmark matcher. The onboard prediction uses direct light only."),
         table([["Lit fraction of footprint", "Median error (m)", "Fixes off by >100 m", "Matcher confidence (median peak)"],
                ["0 - 5%", "401", "88%", "0.00"], ["5 - 25%", "7.6", "20%", "0.86"], ["25 - 50%", "2.4", "0%", "0.98"],
                ["50 - 80%", "1.3", "0%", "0.97"], ["80 - 100%", "0.8", "0%", "0.92"]], [48, 36, 40, 50]),
         para("Table 1. Camera fix error by lit fraction. Among the 226 fixes with confidence >= 0.5, none was off by more than 100 m, so the matcher's own confidence is a reliable failure detector. This replaced round 1's hand-made damage curve. Caveat: the survey uses one renderer, one matcher and one site.", SM),
         para("3. Site04 Monte Carlo (round 2, run once after the freeze)", H2),
         para("500 seeded runs per cell, every judge uses the same confidence-gated camera. Probation window 10 samples and 4 sigma were tuned on procedural worlds and Site01 only (87% mean success there). The ML classifier was retrained on procedural worlds (held-out accuracy 89.5%, AUC 0.97). Sun 2 degrees above the horizon from the west."),
         table([["Scenario", "Fixed", "PITFAL", "Map tol.", "Wait", "2nd op.", "ML", "Trust v1", "Trust v2", "v2+scan"],
                ["Cliff (HAKUTO-R)", "0.2", "82.0", "97.2", "79.6", "56.6", "75.8", "94.6", "96.8", "100.0"],
                ["Cliff + faults", "0.0", "85.6", "97.6", "80.2", "8.6", "76.0", "94.8", "97.4", "99.8"],
                ["Shadow + noisy altimeter (IM-2)", "0.0", "64.0", "61.6", "28.6", "15.6", "23.8", "53.4", "88.0", "59.2"],
                ["Delayed altimeter (ispace M2)", "0.0", "0.0", "0.0", "0.2", "0.0", "0.4", "0.0", "83.0*", "95.8*"],
                ["Altimeter dropout (IM-1)", "0.0", "34.8", "41.6", "29.0", "26.2", "24.2", "31.4", "37.0", "61.4"]],
               [40, 11, 14, 14, 11, 13, 10, 15, 15, 15]),
         para("Table 2. Landing success (%). 95% intervals about +-2 to 4 points. * Trust v2 uses time-stamped readings, the other judges do not (see the exploratory control).", SM),
         img("out/plots/01_success_by_scenario.png", 170),
         PageBreak(),
         para("4. Pre-registered hypotheses", H2),
         table([["#", "Hypothesis (docs/PREREG.md)", "Outcome"],
                ["P1", "Trust v2 beats PITFAL-style by >= 10 points in cliff, cliff + faults, shadow + noisy", "Met: +14.8, +11.8, +24.0"],
                ["P2", "Lower false rejection than PITFAL-style in those scenarios", "Mixed: lower in cliff (0.2 vs 0.8) and shadow + noisy (3.8 vs 4.3); higher in cliff + faults (1.7 vs 0.6)"],
                ["P3", "Fooled by faults at most 1 point more often", "Met in cliff scenarios (4.9 vs 7.1, 6.1 vs 7.9); failed in shadow + noisy (52.4 vs 32.5)"],
                ["P4", "Sun-geometry camera prediction improves on the matcher confidence gate by <= 5 points", "Supported: prediction is 5-11 points worse than the confidence gate in three of four cases and 2 points better in the fourth (trust v2, shadow + noisy)"],
                ["P5", "Gap to PITFAL-style on unseen Site04 at least the tuning-site gap minus 10 points", "Met: Site04 98.0 vs 81.7 (cliff); Site01 100 vs 100"],
                ["P6", "Trust v2 lands >= 50% with delayed readings", "Met numerically (83.0%), but only because of time stamps (exploratory control)"]],
               [10, 84, 80]),
         img("out/plots/06_camera_policies.png", 120),
         para("Figure 2. Camera policies (500 runs). Using every fix without a confidence check fails almost every landing; the matcher's own confidence is enough.", SM),
         para("5. Exploratory control (not pre-registered)", H2),
         para("Does trust v2's delayed-reading result come from its trust logic or from time stamps? Every other judge was re-run with the same time stamps (500 runs): PITFAL-style 74.2%, wait-and-see 79.0%, trust v1 79.6%, trust v2 83.0%, <b>plain map-tolerance gate 97.6%</b>; trust v2 without time stamps 0.0%. The time stamps, not the trust rule, solve this scenario."),
         img("out/plots/07_timestamps_exploratory.png", 100),
         PageBreak(),
         para("6. Sweeps and robustness (300 runs; sun sweep 200)", H2),
         table([["Test", "PITFAL-style", "Trust v2", "Reading"],
                ["Initial position error 5 / 50 / 200 / 400 m (cliff)", "81 / 83 / 76 / 61", "97 / 98 / 95 / 96", "Gap grows with position uncertainty, as the plan expected"],
                ["Mid-descent divert", "74.3", "91.3", "Works without re-planning"],
                ["No map", "2.7", "90.7", "Fallback works; the baseline uses a coarse reference, so this shows the fallback design matters"],
                ["Map shifted by 2 km", "35.0", "1.3", "Trust v2 rejects readings that do not match the wrong map (90% false rejection)"],
                ["Site01 (tuned on) vs Site04 (unseen), cliff", "100 vs 81.7", "100 vs 98.0", "No drop on the unseen, harder site"],
                ["Delayed readings, Site01 vs Site04", "0 vs 0", "98 vs 85", "With time stamps"],
                ["Sun from the east (well lit), shadow + noisy", "99.5", "39", "Trust v2 collapses in good light with a noisy altimeter"],
                ["Sun from the south / west, elevation 1.5-3 deg", "62-70", "81-90", "Trust v2 ahead when the lander is in shadow"]],
               [58, 28, 24, 64]),
         img("out/plots/03_when_does_it_help.png", 95), img("out/plots/04_lighting_sweep.png", 115),
         para("Live scan (extension): trust v2 + scan lifts cliff to 100%, delayed to 95.8% and dropout to 61.4%, but hurts shadow + noisy (59% with 203 of 500 runs timing out in a hover).", SM),
         para("7. Limits and honest caveats", H2),
         ] + bullets([
        "Simulation only. The camera model comes from one renderer, one matcher and one site; shadowed scenes in the renderer are very dark but not physically exact.",
        "Disclosure: guidance, sensor settings and round-1 judge designs were chosen while looking at Site04 runs. Round 2 redid the camera model from measurements and fixed the settings in docs/PREREG.md, but a 100-run Site04 smoke test of the new code was seen before that document was written (recorded in it). The exploratory time-stamp control was added after the main run.",
        "Trust v2 assumes time-stamped altimeter readings and a map registered to within the position uncertainty; it fails when the map is wrong (1% with a 2 km shift).",
        "The no-map comparison is against a coarse-reference baseline; a terrain-relative baseline would be a fairer opponent.",
        "Site01 was used for tuning, so Site04 is the only unseen real site. The real HAKUTO-R altitude record was not available.",
        "The Python bench starts at 15 km as planned; the Unity demo starts at 102.5 km from rest and ignores orbital speed."]) + [
         para("8. Is it publishable, and what next?", H2),
         para("Yes as a controlled-comparison workshop paper (draft: docs/Paper_Draft.pdf): a measured camera model, a pre-registered design, and honest negative findings. The practical recommendation that falls out is a map-tolerance gate, a confidence-gated camera and time-stamped readings; the four-step rule is not needed for the cliff cases. "
              "Next: repair the two weaknesses found (physical check should scale with the noise level; wrong-map detection), add a terrain-relative no-map baseline, survey the camera on a second site and with a second matcher, and replay the real HAKUTO-R altitude record when it is obtained."),
         para("9. Repository map", H2),
         table([["Path", "Contents"],
                ["LANTERN/", "Unity 6 project: Site04 and Site04Replay scenes, lander, autopilot, LUMEN, HUD, logger, replay, camera survey"],
                ["sim/", "Python test bench and pipeline (world, engine, pipeline, plots, camera survey scripts)"],
                ["out/mc/", "Round-2 results: main_results.csv, camera_policies.csv, sweeps_*.csv, exploratory_timestamps.csv, tuning.csv, ML report"],
                ["out/mc_round1/, out/plots_round1/", "Round-1 results (kept for comparison; git tag round1)"],
                ["out/camera_survey/", "Survey positions, matcher results, empirical camera model (images not in git)"],
                ["docs/", "PREREG.md, PROGRESS.md, this report, the project description, the paper draft"]],
               [44, 130])]
    build("Progress_Report.pdf", s, "Progress Report")


def paper():
    s = [para("When should a lunar lander believe its altimeter?", H1),
         para("A controlled comparison of sensor-trust rules on real South Pole terrain (draft, 19 October 2026)", SM), Spacer(1, 4),
         para("Abstract", H2),
         para("Two recent lunar landers were lost partly because their navigation filters misjudged a sensor: a valid altimeter reading at a crater edge was rejected as a fault, and a camera was trusted in shadow. We build a seeded descent simulator on NASA PGDA Site04 (Shackleton rim), measure a landmark-matching camera's reliability in a Unity renderer instead of assuming it, and compare seven ways of judging a surprising altimeter reading over 500 landings per scenario, with a pre-registered design and a held-out site. "
              "A fixed-gate filter with a coarse reference reproduces the HAKUTO-R failure (0.2% landing success). Putting the terrain map in the filter recovers most of it (82%), and a plain map-tolerance gate reaches 97%. A four-step trust rule with probation matches but does not beat that gate in cliff scenarios, wins with a noisy altimeter in shadow (88% vs 64%) and with no map (91% vs 3%), and fails when the altimeter is noisy in good light (39% vs 99%) or the map is shifted (1% vs 35%). "
              "Camera fixes must be gated by the matcher's own confidence (ungated: under 3% success); predicting darkness from Sun and terrain adds nothing. Delayed readings are solved by time stamps, not by trust logic. We report limits and the points where an earlier, unfairly designed comparison had overstated the benefit."),
         para("1. Introduction", H2),
         para("Powered descent navigation fuses a laser altimeter, a camera and an IMU. A fixed chi-square gate cannot tell a real terrain discontinuity from a sensor fault. HAKUTO-R M1 (April 2023) rejected altimeter readings after crossing a crater rim; IM-2 (March 2025) kept trusting a camera that could not see in shadow. PITFAL-style filters put a terrain map into the prediction (Adams et al., 2025). We ask which additional judging rule, if any, is worth having once the map is in the filter and the camera is handled honestly."),
         para("2. Method", H2),
         para("<b>Terrain.</b> PGDA Product 78 (Barker et al., 2021): Site04 (unseen test) and Site01 (tuning, with NASA's total-error map) at 5 m/pixel, resampled to 10 m; procedural crater worlds for tuning and classifier training. The simulated Moon contains unmapped craters and roughness absent from the onboard map, plus a registration shift (fair-testing rule 1). "
              "<b>Vehicle and guidance.</b> Point-mass lander, lunar gravity, throttleable engine with fuel; guidance flies a speed profile on the estimated terrain-relative altitude. Success: vertical speed <= 2 m/s, horizontal <= 1.5 m/s, slope <= 10 degrees, fuel left. "
              "<b>Sensors.</b> IMU with bias and noise; laser altimeter with range-dependent noise and fault bursts; camera position fixes drawn from a Unity survey (300 image pairs, normalised cross-correlation matcher, direct-light-only prediction); optional live lidar scan. "
              "<b>Judges.</b> Fixed gate with coarse reference; PITFAL-style (map in prediction, noise inflation after a flag); map tolerance (gate widened by local terrain variance and map error); wait-and-see (probation); second opinion; random-forest classifier (trained on procedural worlds only); and the four-step trust rule (physical possibility, probation, camera, no-map fallback) in two versions. "
              "<b>Scenarios.</b> Cliff crossing, cliff with frequent faults, shadow with a noisy altimeter, delayed readings, altimeter dropout. All judges see identical noise and faults. "
              "<b>Protocol.</b> Hypotheses and settings were fixed in a pre-registration committed before the Site04 run; tuning used procedural worlds and Site01 only; 500 runs per cell with 95% intervals; an exploratory control was added afterwards and is labelled."),
         para("3. Results", H2),
         table([["Scenario", "Fixed", "PITFAL", "Map tol.", "Trust v1", "Trust v2"],
                ["Cliff (HAKUTO-R)", "0.2", "82.0", "97.2", "94.6", "96.8"], ["Cliff + faults", "0.0", "85.6", "97.6", "94.8", "97.4"],
                ["Shadow + noisy altimeter", "0.0", "64.0", "61.6", "53.4", "88.0"], ["Delayed readings (v2 time-stamped)", "0.0", "0.0", "0.0", "0.0", "83.0"],
                ["Altimeter dropout", "0.0", "34.8", "41.6", "31.4", "37.0"]], [56, 16, 18, 20, 20, 20]),
         para("Table 1. Landing success (%), Site04, 500 runs per cell, confidence-gated camera for every judge.", SM),
         img("out/plots/01_success_by_scenario.png", 165),
         para("<b>Camera.</b> The matcher is accurate (median 0.8-2.4 m) once a quarter of the footprint is lit and fails in the dark (88% of fixes off by more than 100 m); its confidence flags every failure in our survey (0 of 226 accepted fixes off by >100 m). Using every fix: 0.4-3% success. Sun-geometry prediction instead of confidence: 5-11 points worse in three of four cases. "
              "<b>Delays.</b> With time stamps PITFAL-style reaches 74%, the tolerance gate 97.6% and trust v2 83%; without them trust v2 reaches 0%. "
              "<b>Robustness.</b> No map: 91% vs 3%; divert: 91% vs 74%; position uncertainty 400 m: 96% vs 61%; unseen Site04 98% vs 82% (Site01: both 100%). Failures: noisy altimeter in good light 39% vs 99.5%; map shifted by 2 km 1% vs 35%. Live scan adds up to 24 points in three scenarios and removes 29 in the shadow + noisy one."),
         para("4. Discussion", H2),
         para("The map in the filter does most of the work; a plain tolerance gate does the rest in cliff cases. The four-step rule's distinctive parts (physical-possibility check, probation) add little there and introduce brittleness: the check rejects valid noisy readings when position is well known and any reading when the map is wrong. Its learned noise level is what helps with a noisy altimeter, at the cost of accepting more faulty readings. "
              "For camera handling the practical lesson is to trust the matcher's confidence. An earlier version of this study compared a shadow-aware camera rule with judges that used every fix, and reported a large benefit; with a measured camera and a fair baseline that benefit disappeared."),
         para("5. Limitations", H2),
         ] + bullets([
        "One simulator, one renderer and matcher, one unseen real site; no hardware, no real image-based navigation, no real HAKUTO-R altitude record.",
        "Settings were first explored while looking at Site04 runs; the pre-registration limits this but does not erase it (disclosed in the registration).",
        "Trust v2 assumes time-stamped readings and a registered map.",
        "The no-map baseline uses a coarse reference rather than a terrain-relative filter."]) + [
         para("6. Conclusion", H2),
         para("For this class of descent, a map-tolerance gate with a confidence-gated camera and time-stamped altimeter readings is about as good as the four-step trust rule in the cliff cases. The trust rule is worth keeping only for its noise-learning, no-map fallback and divert behaviour, and it needs a physical check that scales with measurement noise and a way to detect a wrong map."),
         para("References", H2),
         para("Adams et al. (2025), AIAA SciTech, NTRS 20240014100 (PITFAL). Barker et al. (2021), Planetary and Space Science 203 (LOLA 5 m DEMs). Bertone et al., Planetary Science Journal, doi:10.3847/PSJ/ae5b70. Karlgaard et al. (2025), NTRS 20250010290. ispace HAKUTO-R Mission 1 debriefing (2023). "
              "Code, data products, seeds and the pre-registration: github.com/AnakinSkywalker0/lantern-sensor-trust (private).", SM)]
    build("Paper_Draft.pdf", s, "Paper Draft")


def _inline(t):
    import re
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r'<font face="Courier" size="8">\1</font>', t)
    return t


def log_pdf():
    """Render docs/FULL_LOG.md (headings, bullets, numbered lists, tables, paragraphs) to docs/Full_Project_Log.pdf."""
    import re
    lines = open(os.path.join(DOCS, "FULL_LOG.md"), encoding="utf-8").read().split("\n")
    story = []
    i = 0
    para_buf = []

    def flush():
        if para_buf:
            story.append(para(_inline(" ".join(para_buf))))
            para_buf.clear()

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("# "):
            flush(); story.append(para(_inline(ln[2:]), H1))
        elif ln.startswith("## "):
            flush(); story.append(para(_inline(ln[3:]), H2))
        elif ln.startswith("### "):
            flush(); story.append(para("<b>" + _inline(ln[4:]) + "</b>", B))
        elif ln.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append([_inline(c) for c in cells])
                i += 1
            ncol = len(rows[0])
            story.append(table(rows, [174.0 / ncol] * ncol)); story.append(Spacer(1, 4))
            continue
        elif ln.startswith("* "):
            flush(); story.append(Paragraph(_inline(ln[2:]), BUL, bulletText="•"))
        elif re.match(r"^\d+\. ", ln):
            flush(); m = re.match(r"^(\d+)\. (.*)", ln); story.append(Paragraph(_inline(m.group(2)), BUL, bulletText=m.group(1) + "."))
        elif ln.startswith("  ") and story and para_buf == []:
            # continuation line of a bullet: append to the previous paragraph text
            story.append(para(_inline(ln.strip()), SM))
        elif ln.strip() == "":
            flush()
        else:
            para_buf.append(ln.strip())
        i += 1
    flush()
    build("Full_Project_Log.pdf", story, "Full Project Log")


if __name__ == "__main__":
    description()
    progress()
    paper()
    log_pdf()
    print("wrote", os.listdir(DOCS))
