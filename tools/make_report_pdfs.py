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
def bullets(items): return [Paragraph(i, BUL, bulletText="â€¢") for i in items]


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
    s = [para("Progress Report and Results", H1),
         para("Sensor Trust for Lunar South Pole Landing - LANTERN testbed, 19 October 2026", SM), Spacer(1, 4),
         para("Conclusion in plain words", H2),
         para("<b>1.</b> A navigation filter with a fixed rule fails on real Site04 terrain exactly like HAKUTO-R: it rejects 99% of valid altimeter readings and the lander crashes (about 500 of 500 runs). "
              "<b>2.</b> Simply putting the terrain map into the filter fixes most of that. "
              "<b>3.</b> The biggest further gain comes from not believing the camera when the ground below is in shadow: with it, landing success is 89% instead of about 49%. "
              "<b>4.</b> The specific four-step altimeter rule (physical-possibility check plus probation) did <b>not</b> beat a simpler map-tolerance gate once every method was given the same camera handling (89% versus 93%), and it performs worse when the altimeter is noisy but the scene is well lit (61% versus 99%). "
              "<b>5.</b> The camera result depends on how badly my simulated camera is hurt by shadow; if shadow hurts it only mildly, the PITFAL-style filter does as well or better. "
              "<b>6.</b> Delayed altimeter readings defeat every method, and the trust layer's no-map fallback failed. "
              "So the honest message is: shadow-aware sensor weighting matters a lot, the four-step altimeter rule adds little beyond a simple tolerance gate, and the evidence is simulation-only."),
         para("1. Verified in Unity", H2),
         table([["Item", "Result"],
                ["Descent", "From 102.5 km above a flat spot at Site04 (Unity 6198, 8512; 2.8 deg maximum slope over 45 m): touchdown at t = 583-587 s, 0.50 m/s vertical, 0 m/s horizontal, 0.0 deg tilt, 251 kg fuel left, exactly on target"],
                ["Live scan (LUMEN)", "Fix from 2463 m down. Error 47 m at 2205 m (41 m cell), 14.5 m at 921 m, 4 m at 155 m (8 m cell); median 8.9 m over 108 fixes. No fix below about 80 m or above about 2.5 km"],
                ["HUD, logging, shadows", "HUD text scales with screen height; every run writes CSV to out/runs/; low-Sun cast shadows render"],
                ["Replay scene", "Site04Replay plays one recorded descent with the three filters side by side (true lander solid, filter estimate as a ghost, live altitude error and gate)"]],
               [34, 140]),
         Spacer(1, 3), img("out/plots/unity_descent.png", 105), para("Figure 2. Logged Unity descent from 102.5 km.", SM),
         img("out/replay_final.png", 150),
         para("Figure 3. Unity replay of one descent (cliff plus faults). The fixed-gate lander (red) hovers 1372 m above ground believing it is 62 m below the surface; the PITFAL-style (yellow) and trust-layer (green) landers have landed.", SM),
         PageBreak(),
         para("2. Monte Carlo results (Python test bench, Site04, never used for tuning)", H2),
         para("500 seeded runs per cell. Every method sees the same descents, noise and faults. The ML classifier and the probation settings were trained or tuned on procedural crater worlds only (classifier: 77.7% accuracy, AUC 0.85 on a held-out world; probation window 8 samples, 4 sigma). Sun 2 degrees above the horizon from the west, so the descent enters shadow."),
         table([["Scenario", "Fixed", "PITFAL-style", "Map tol.", "Wait&see", "2nd opinion", "ML", "Trust 4-step", "Trust + scan"],
                ["Cliff (HAKUTO-R)", "0.4", "49.0", "45.6", "53.0", "46.2", "48.8", "89.2", "100.0"],
                ["Cliff + faults", "0.0", "45.6", "40.4", "53.6", "32.8", "46.0", "84.6", "100.0"],
                ["Shadow + noisy altimeter (IM-2)", "0.0", "27.0", "18.0", "33.2", "33.8", "25.0", "55.0", "64.2"],
                ["Delayed altimeter (ispace M2)", "0.0", "1.2", "4.0", "35.6", "18.4", "23.8", "0.2", "2.2"],
                ["Altimeter dropout (IM-1)", "0.0", "7.8", "9.0", "7.4", "7.6", "8.6", "44.4", "55.8"]],
               [38, 14, 20, 16, 18, 20, 12, 20, 20]),
         para("Table 1. Landing success (%). 95% intervals are about +/-4 points (cliff row: trust 86-92, PITFAL 45-53). Judges other than the trust layer used the camera whether or not the ground was lit.", SM),
         img("out/plots/01_success_by_scenario.png", 170),
         para("3. Controlled checks that change the interpretation", H2),
         para("Table 1 compares the trust layer, which includes shadow-aware camera handling, with judges that lack it. To separate the two ideas, every judge was re-run with the same shadow-aware camera (500 runs):"),
         table([["Scenario", "Map tol.", "Trust 4-step", "PITFAL-style", "Wait&see", "ML", "2nd opinion"],
                ["Cliff", "93.0", "89.2", "72.8", "68.0", "64.4", "33.6"],
                ["Cliff + faults", "90.6", "84.6", "73.2", "68.8", "57.8", "1.0"],
                ["Shadow + noisy altimeter", "60.0", "55.0", "52.8", "22.8", "14.4", "5.8"]],
               [44, 22, 26, 26, 22, 18, 24]),
         para("Table 2. Landing success (%) with identical camera handling. The simple map-tolerance gate matches or beats the four-step rule.", SM),
         img("out/plots/06_altimeter_logic_only.png", 170),
         para("Ablations (cliff scenario): removing the camera step drops the trust layer from 89% to 47%; removing probation leaves it at 89%; removing the physical-possibility check leaves it at 88%. In the shadow-plus-noise scenario probation helps (55% versus 38% without), while the physical check hurts (63% without it)."),
         img("out/plots/07_camera_damage_sensitivity.png", 110),
         para("Figure 4. Sensitivity to the camera model. If shadow only mildly degrades the camera, PITFAL-style reaches 94-100% and the trust layer's advantage disappears; the trust layer is flat at 88% because it ignores the camera in the dark."),
         para("In a well-lit run (Sun from the east) every map-based judge except the second-opinion one lands at least 98.7% in the cliff scenarios, so the trust layer is not harmful there. With a noisy altimeter in good light, though, PITFAL-style lands 99% and the trust layer only 61%, because probation compares readings to the nominal noise level and rejects noisy but valid ones."),
         PageBreak(),
         para("4. Sweeps and robustness (300 runs each unless noted)", H2),
         table([["Test", "PITFAL-style", "Trust layer", "Reading"],
                ["Initial position error 5 m / 50 m / 200 m / 400 m (cliff)", "48 / 48 / 49 / 45", "94 / 92 / 81 / 73", "Trust layer gap is largest when position is well known, the opposite of hypothesis H3; the gap is driven by shadow handling"],
                ["Mid-descent divert", "54.3", "72.7", "Works without re-planning; one test, not tuned"],
                ["Map shifted by 2 km", "17.7", "26.0", "Both fail; false rejections 70% and 90%"],
                ["No map", "6.7", "0.0", "The trust layer's cautious fallback does not work (fixed rule: 0)"],
                ["Unseen site vs tuned site (shadow + noise)", "29.3 vs 35.3", "51.7 vs 41.7", "No drop on the unseen site; the procedural world is simply harder"],
                ["Sun azimuth 90 degrees (well lit), shadow + noise", "99.0", "58.0", "Trust layer worse in good light with noisy altimeter"],
                ["Sun azimuth 180 / 270 degrees, elevation 1.5-3 degrees", "28 to 31", "55.0", "Identical for all three elevations: the lander is in shadow throughout"]],
               [58, 24, 24, 68]),
         img("out/plots/03_when_does_it_help.png", 100), img("out/plots/04_lighting_sweep.png", 120),
         para("5. Hypotheses against the plan", H2),
         table([["#", "Expectation", "Outcome"],
                ["H1", "Four-step rule rejects far fewer real cliff readings than the fixed rule without being fooled noticeably more (at most 1 extra fooled run in 100)", "Versus the fixed rule: yes (99% false rejection down to 0.2%). Versus PITFAL-style: false rejection 8.3% down to 0.2%, but missed faults rise from 7.3% to 10.7%, which breaks the stated threshold"],
                ["H2", "Shadow-aware camera trust reduces error in dark areas", "Supported in this model (89% versus 47-49%), but depends on how badly shadow hurts the camera; see Figure 4"],
                ["H3", "When position is already well known, the NASA-style method does as well as ours", "Not supported here; confounded by the shadow effect"],
                ["H4", "The rule still works on a site it was never tuned on", "Supported: 51.7% on Site04 versus 41.7% on the tuned world, with the trust layer ahead of PITFAL on both"]],
               [10, 76, 88]),
         para("6. Limits and honest caveats", H2),
         ] + bullets([
        "Everything is simulation. The shadowed-camera model, the unmapped-terrain roughness and the fault models are my assumptions, and the headline result is sensitive to the camera model (Figure 4).",
        "Guidance, sensor models and the first judge designs were chosen while looking at Site04 smoke runs. Only the probation settings and the ML model were tuned strictly on procedural worlds; the controlled comparisons in section 3 were added after the main run because the first table confounded two ideas.",
        "Site01 is not available, so the tuned site is procedural terrain only. The HAKUTO-R altitude debriefing curve was not available, so no replay of the real data was done.",
        "The Python bench starts at 15 km as the plan specifies; the Unity demonstration starts at 102.5 km from rest at the user's request, which ignores the real orbital speed.",
        "Delayed readings, dead altimeters and a missing map are not solved, as the plan stated for the first two.",
        "The ML classifier is moderate and was no better than PITFAL-style in the tests."]) + [
         para("7. Is it publishable?", H2),
         para("As a negative-and-mixed result, possibly at a workshop: a controlled study on real Site04 terrain showing that (a) a fixed rule reproduces the HAKUTO-R failure, (b) putting the map in the filter fixes most of it, (c) shadow-aware camera weighting gives the largest further gain but depends on the camera model, and (d) a four-step rule with probation adds little over a map-tolerance gate. "
              "To be stronger it would need a better-justified camera model, real image-based navigation, Site01 and a second real site, and a redesign of probation for noisy but valid readings. The data, code and seeds are in the repository."),
         para("8. Next steps", H2),
         ] + bullets([
        "<b>Justify the camera model first</b> (it decides whether the headline holds): render camera images in Unity under low Sun, measure how a simple landmark matcher degrades with lit fraction, replace the assumed shadow-damage curve, and re-run the sensitivity test.",
        "Redesign probation to learn the noise level from the data, add a time-stamp check for delayed readings, tune on procedural worlds, then run Site04 once with settings frozen beforehand.",
        "Fix the no-map fallback (currently 0%) and re-run the shifted-map and missing-map tests.",
        "Obtain Site01 and PGDA Product 104 for a second real site, and the published HAKUTO-R altitude record for a real-data replay.",
        "Write the workshop-style paper after the first three steps; add per-sensor trust bars and live gate width to the Unity HUD."]) + [
         para("9. Repository map", H2),
         table([["Path", "Contents"],
                ["LANTERN/", "Unity 6 project: Site04 and Site04Replay scenes, lander, autopilot, LUMEN, HUD, logger, replay"],
                ["sim/", "Python test bench and pipeline (world.py, engine.py, pipeline.py, plots.py)"],
                ["out/mc/", "Monte Carlo results: main_results.csv/.md, controlled.csv, sweeps, tuning, ML report; per-run CSVs"],
                ["out/plots/, out/replay/", "Result figures; replay data for Unity"],
                ["docs/", "This report and the project description"],
                ["data/", "NASA PGDA GeoTIFFs (not in git; see README)"]],
               [34, 140])]
    build("Progress_Report.pdf", s, "Progress Report")


if __name__ == "__main__":
    description()
    progress()
    print("wrote", os.listdir(DOCS))
