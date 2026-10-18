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
                ["O1", "Hazard (cliff) and blind-spot (shadow) maps for Site04 and Site01", "Partly: DEM slope/shadow rasters exist; trust maps are computed inside the test bench"],
                ["O2", "Trust layer producing gate width and measurement noise, with fault-vs-terrain check", "Implemented in sim/engine.py; not yet evaluated at scale"],
                ["O3", "Reproduce baseline failures (cliff, shadow, delay, dropout)", "Scenarios implemented; early small runs reproduce the cliff failure"],
                ["O4", "Compare baseline, PITFAL-style and trust layer over ~500 Monte Carlo runs per scenario", "Pipeline written; not run"],
                ["O5", "Release Unity project, code, scenarios and a side-by-side replay", "Replay player written; not built into a scene or run"],
                ["O6", "Site-change robustness (unseen site, divert, wrong or missing map)", "Implemented as sweeps; not run"],
                ["O7", "Live 3D scan extension with three-way check", "LUMEN works in Unity; scan fix and check modelled in the test bench"]],
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
    s = [para("Progress Report", H1),
         para("Sensor Trust for Lunar South Pole Landing - state of the LANTERN testbed on 18 October 2026", SM), Spacer(1, 4),
         para("Summary", H2),
         para("The Unity side is working and verified: a lander descends from 102.5 km above a flat spot on the Site04 crater floor and touches down at 0.50 m/s under autopilot, with a live-scan position fix (LUMEN) and per-run data logging. "
              "A fast Python test bench for the 500-run comparison is written and was smoke-tested on 40-100 runs, but <b>the full Monte Carlo evaluation, the ML classifier, the tuning, the sweeps and the Unity replay have not been run</b>. "
              "No result in this report from the Python bench should be quoted as a finding."),
         para("1. Verified in Unity", H2),
         table([["Item", "Result", "How it was checked"],
                ["Unity connection and Play mode", "Works. Play did not advance while the editor window was inactive; Application.runInBackground fixes it and is now set by the autopilot", "Frame counter and Time.time sampled in Play"],
                ["Landing site", "Unity (6198, 8512), 1.88 km from the tile centre, 1729.5 m elevation, mean slope 1.1 deg, 45 m-window maximum 2.8 deg. The tile centre itself is 33 deg", "Slope derived from the DEM (the supplied slope file is truncated); Unity terrain height at the point equals the DEM"],
                ["Shadows", "Low-Sun cast shadows render across the terrain", "Camera captures"],
                ["Autopilot, 500 m start", "First run touched down at 2.07 m/s (over target); after retuning, 0.50 m/s", "Console and sampled state"],
                ["Autopilot, 102.5 km start", "Touchdown at t = 583-587 s, 0.50 m/s vertical, 0 m/s horizontal, 0.0 deg tilt, 251 kg fuel left (549 kg used), exactly on the target. Coast about 190 s to 312 m/s, then about 0.69 throttle to touchdown", "Two full runs and the logged CSV"],
                ["LUMEN live scan", "Shift opposed the injected error (+60, -40) m: (-64, 32) m at 390 m and 272 m altitude, confidence 1.00. After the altitude-scaled cell fix it gets a fix from 2463 m down; error 47 m at 2205 m (41 m cell), 14.5 m at 921 m, 4 m at 155 m (8 m cell). Valid in 9% of logged rows; median error 8.9 m; max 48.7 m", "Logged run CSV (108 valid fixes)"],
                ["HUD", "Text now scales to 3% of screen height with a dark backing box and is readable at 1920x1080", "Game-view screenshot (out/hud_check.png)"],
                ["Data logging", "TelemetryLogger writes per-run CSV and runs_summary.csv; flushed per row. The first run's summary line recorded a start altitude of 0 (logging bug, fixed afterwards, fix not re-verified)", "Files in out/runs/"]],
               [34, 96, 44]),
         Spacer(1, 4), img("out/plots/unity_descent.png", 120),
         para("Figure 2. Logged Unity descent from 102.5 km: altitude, descent rate with throttle, and LUMEN position error.", SM),
         img("out/unity_landed_view.png", 130), para("Figure 3. Lander on the Site04 crater-floor landing spot (Unity camera capture).", SM),
         para("2. Built but not run at scale", H2),
         para("<b>Python test bench (sim/).</b> world.py (Site04 and procedural crater worlds, onboard map with registration shift and noise, unmapped craters, coarse reference surface, shadow and lighting statistics), "
              "engine.py (batched truth physics, IMU, altimeter, camera and live-scan sensors, fault bursts, delay, dropout, a 9-state EKF, guidance on the estimate, seven judges plus three ablations), "
              "pipeline.py (parallel ML, tuning, main, sweeps and replay stages) and plots.py. Scenarios: cliff crossing (HAKUTO-R), cliff with frequent faults, shadow with noisy altimeter (IM-2), delayed readings (ispace M2), altimeter dropout (IM-1)."),
         para("<b>Unity replay.</b> ReplayPlayer.cs and ReplaySceneBuilder.cs compile without errors; the replay scene has not been built because no replay data has been exported yet."),
         para("<b>Smoke test only (40-100 runs, Site04, Sun from the west, not tuned, not a result).</b> The fixed-gate baseline rejected about 99% of valid readings and crashed in nearly every run, which matches the HAKUTO-R failure mechanism. "
              "The trust layer landed more often than the PITFAL-style filter in the cliff and shadow scenarios, but scored 0% on delayed readings and about half on dropout. "
              "These early numbers came from a model whose guidance and sensor settings were chosen while looking at Site04 runs, so they need the tuning-on-procedural-only procedure before any claim."),
         para("3. Not done", H2),
         ] + bullets([
        "The 500-run Monte Carlo on Site04, ablation table, lighting sweep, position-uncertainty sweep, wrong/missing-map and divert tests.",
        "ML classifier training (a run was started and stopped at the user's request; no model was produced) and tuning on procedural worlds.",
        "Site01 tuning data (the tile is not in the repository); the HAKUTO-R altitude-curve replay (debriefing data not available).",
        "Building and running the Unity replay scene; the in-flight HUD showing true vs estimated altitude, gate width and per-sensor trust bars.",
        "LUMEN has no fix below roughly 80 m (footprint smaller than the 40 cells needed) and none above about 2.5 km (by design); only partly investigated."]) + [
         para("4. Deviations and caveats", H2),
         ] + bullets([
        "The plan scopes powered descent from about 15 km; the Unity demonstration starts at 102.5 km at the user's request, from rest, falling straight down. A real descent from 100 km altitude starts with about 1.7 km/s of horizontal speed, which the autopilot does not handle. The Python bench starts at 15 km.",
        "Several Unity checks (HUD, camera) rely on one screenshot each; the camera capture tool did not appear to follow the lander during Play.",
        "The simulated 'real Moon' differs from the onboard map only by synthetic craters, noise and shifts, not by real unmapped terrain."]) + [
         para("5. Next steps", H2),
         ] + bullets([
        "Run ML training and tuning on procedural worlds, then the Site04 evaluation with fixed seeds.",
        "Export a replay where the baseline crashes and the trust layer lands; build and capture the Unity replay scene.",
        "Write up results with confidence intervals and the stated limits."]) + [
         para("6. Repository map", H2),
         table([["Path", "Contents"],
                ["LANTERN/", "Unity 6 project (scene Site04, scripts, editor builders)"],
                ["sim/", "Python test bench and experiment pipeline"],
                ["tools/", "Heightmap and rendering scripts, PDF generator"],
                ["deliverables/", "Project plan PDFs (literature review, gap, objectives, methodology, summaries)"],
                ["docs/", "This project description and progress report"],
                ["out/", "Plots, telemetry runs, figures (large caches excluded from git)"],
                ["data/", "NASA PGDA GeoTIFFs (excluded from git; see README)"]],
               [34, 140])]
    build("Progress_Report.pdf", s, "Progress Report")


if __name__ == "__main__":
    description()
    progress()
    print("wrote", os.listdir(DOCS))
