"""Report text for the LANTERN project report. All numbers are taken from the repository documents named in the text."""
import os
from docbuild import Report
from refs import REFS

R = "D:/newprj/"
TITLE = "Sensor Trust and Terrain-Relative Navigation for Lunar South Pole Landing (LANTERN)"
STUDENTS = [("Abhishek Mishra", "240365"), ("Rishabh Kumar", "240605"), ("Neil Jain", "240553"), ("Khushi Vijay", "240511")]
BLANK = "____________"


def split_fig(path, split_x, strip_w, name):
    """Cut a 5-panel chart into a 3-panel and a 2-panel image (re-attaching the y axis) so the text stays readable."""
    import os
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    top = 48   # drop the chart's own title (the caption carries it)
    a = im.crop((0, top, split_x, h))
    b_body = im.crop((split_x, top, w, h))
    b = Image.new("RGB", (strip_w + b_body.size[0], h - top), "white")
    b.paste(im.crop((0, top, strip_w, h)), (0, 0))
    b.paste(b_body, (strip_w, 0))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
    pa, pb = os.path.join(out, name + "_a.png"), os.path.join(out, name + "_b.png")
    a.save(pa)
    b.save(pb)
    return [pa, pb]


def front(r, figs, tabs, pages):
    d = r.doc
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING

    def cp(text, size, space_after=10, bold=False):
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        p.paragraph_format.space_after = Pt(space_after)
        run = p.add_run(text)
        run.font.size = Pt(size)
        run.bold = bold
        return p

    # ---- title page (section 1, no page number) ----
    sec0 = d.sections[0]
    sec0.left_margin = sec0.right_margin = Cm(2.54)          # title page is centred on the page, as in the front-page template
    cp("A", 18, 12)
    cp("PROJECT-I REPORT", 22, 12)
    cp("on", 18, 12)
    cp(TITLE, 22, 10)
    cp("Submitted by:", 18, 6)
    for n, e in STUDENTS:
        cp(n, 18, 0)
        cp("(%s)" % (e if e else "Enrollment No."), 14, 4)
    cp("under mentorship of", 18, 6)
    cp("Dr. Sukhandeep Kaur", 22, 0)
    cp("(Professor)", 18, 8)
    lp = d.add_paragraph()
    lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    lp.paragraph_format.space_after = Pt(8)
    lp.add_run().add_picture(os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs", "bmu_logo.png"), width=Pt(250))
    cp("Department of Computer Science Engineering", 18, 0)
    cp("School of Engineering and Technology", 18, 0)
    cp("BML MUNJAL UNIVERSITY, GURUGRAM (INDIA)", 18, 0)
    fp = sec0.footer.paragraphs[0]                            # template shows its page number at bottom left
    fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fr = fp.add_run("1")
    fr.font.name = "Calibri"
    fr.font.size = Pt(11)

    # ---- front matter (section 2, roman numerals) ----
    sec1 = r.new_section(number=True, fmt="lowerRoman", start=2)
    sec1.left_margin, sec1.right_margin = Cm(3.5), Cm(1.5)
    d.add_paragraph("CANDIDATE'S DECLARATION", style="Front Heading").paragraph_format.page_break_before = False
    r.para("We hereby certify that the work on the project entitled, \"%s\", in partial fulfillment of requirements for the "
           "award of Degree of Bachelor of Technology in School of Engineering and Technology at BML Munjal University, "
           "having University Roll Nos. 240365, 240605, 240553 and 240511, is an authentic record of our own "
           "work carried out during a period from %s to %s under the supervision of Dr. Sukhandeep Kaur." % (TITLE, "August 2026", "December 2026"))
    for n, e in STUDENTS:
        r.para("%s (%s)" % (n, e if e else "Roll No. ____________"), align="left").paragraph_format.space_after = Pt(2)
    sh = d.add_paragraph("SUPERVISOR'S DECLARATION", style="Front Heading")
    sh.paragraph_format.page_break_before = False
    sh.paragraph_format.space_before = Pt(36)
    r.para("This is to certify that the above statement made by the candidates is correct to the best of my knowledge.")
    r.para("Faculty Supervisor Name: Dr. Sukhandeep Kaur", align="left")
    r.para("Signature: ______________________", align="left")

    d.add_paragraph("ACKNOWLEDGEMENT", style="Front Heading")
    r.para("We are grateful to Dr. Sukhandeep Kaur, BML Munjal University, Gurugram, for supervising this project and for "
           "guidance throughout the work. We thank the entire team at BML Munjal University and our friends who gave their time "
           "and help towards its completion.")
    r.para("We also acknowledge the public data and literature this work depends on: the NASA Planetary Geodesy Data Archive "
           "(PGDA) lunar South Pole elevation products by Barker et al. and the mission reports and papers cited in the References.")
    r.para("An AI coding assistant (Claude, Anthropic) was used during the project for writing and reviewing code, running "
           "experiments and drafting documents. Every number quoted in this report comes from result files stored in the project "
           "repository, and the limits of the evidence are stated in the text.")
    for n, e in STUDENTS:
        r.para(n, align="left").paragraph_format.space_after = Pt(0)

    d.add_paragraph("TABLE OF CONTENTS", style="Front Heading")
    r.toc()
    abstract(r)

    # ---- list of figures / tables / abbreviations (static; page numbers filled from the rendered PDF) ----
    d.add_paragraph("LIST OF FIGURES", style="Front Heading")
    _list_table(r, ["Figure No.", "Figure Description", "Page No."], figs, pages)
    d.add_paragraph("LIST OF TABLES", style="Front Heading")
    _list_table(r, ["Table No.", "Table Description", "Page No."], tabs, pages)
    d.add_paragraph("LIST OF ABBREVIATIONS", style="Front Heading")
    abbr = [
        ("AGL", "Above Ground Level"), ("AUC", "Area Under the ROC Curve"), ("DEM", "Digital Elevation Model"),
        ("DOF", "Degrees of Freedom"), ("EKF", "Extended Kalman Filter"), ("IMU", "Inertial Measurement Unit"),
        ("LOLA", "Lunar Orbiter Laser Altimeter"), ("LRO", "Lunar Reconnaissance Orbiter"), ("ML", "Machine Learning"),
        ("NDL", "Navigation Doppler Lidar"), ("PGDA", "Planetary Geodesy Data Archive (NASA GSFC)"),
        ("PITFAL", "Terrain-informed fault detection method of Adams et al. (2025); \"PITFAL-style\" is our reimplementation"),
        ("RMS", "Root Mean Square"), ("SPLICE", "Safe and Precise Landing - Integrated Capabilities Evolution (NASA)"),
        ("TRN", "Terrain-Relative Navigation"), ("ZNCC", "Zero-mean Normalised Cross-Correlation"),
        ("LUMEN", "Name of this project's live lidar-scan module in Unity"),
    ]
    _list_table(r, ["Abbreviation", "Full Form"], [(a, b) for a, b in abbr], {}, two=True)


def _list_table(r, header, items, pages, two=False):
    from docx.shared import Pt, Cm
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    d = r.doc
    t = d.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    t._tbl.tblPr.append(lay)
    widths = [3.0, 13.0] if two else [2.6, 11.4, 2.0]

    def put(cell, text, bold=False, w=None):
        p = cell.paragraphs[0]
        p.style = d.styles["Table Text"]
        r.runs(p, text, size=11, bold=bold)
        cell.width = Cm(w)

    for j, h in enumerate(header):
        put(t.rows[0].cells[j], h, True, widths[j])
    for it in items:
        cells = t.add_row().cells
        if two:
            put(cells[0], it[0], False, widths[0])
            put(cells[1], it[1], False, widths[1])
        else:
            lab, cap = it
            put(cells[0], lab.replace("Figure ", "").replace("Table ", ""), False, widths[0])
            put(cells[1], cap, False, widths[1])
            put(cells[2], str(pages.get(lab, "0")), False, widths[2])
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        cs.set(qn("w:val"), "true")
        trPr.append(cs)


def abstract(r):
    r.chapter(0, "Abstract")
    r.para("A lunar lander has no satellite navigation. It tracks its position from inertial sensors and corrects it with a laser "
           "altimeter, a camera and, in newer designs, a lidar scan matched against a stored elevation map. Two recent landers were "
           "lost partly because their filters misjudged a sensor: a valid altimeter reading at a crater edge was rejected as a fault "
           "(HAKUTO-R M1, 2023), and noisy range data and shadowed imagery were believed (IM-2, 2025) {ispace_m1, sp_im2}.")
    r.para("This project builds LANTERN, a Unity-based descent simulator on real NASA South Pole terrain (PGDA Site04 and Site01), "
           "with a fast Python test bench that runs thousands of seeded landings. The first study compared seven ways of judging a "
           "surprising altimeter reading over 500 landings per scenario on the unseen Site04, with a pre-registered design and a camera "
           "model measured in a renderer instead of assumed. A fixed gate reproduces the HAKUTO-R failure (0.2% landing success); putting the "
           "terrain map into the filter recovers 82%, and a plain map-tolerance gate reaches 97%. A four-step trust rule matches that gate "
           "in cliff cases, wins with a noisy altimeter in shadow (88% against 64%) and with no map (91% against 3%), and fails when the "
           "altimeter is noisy in good light or the map is shifted. Camera fixes must be gated by the matcher's own confidence.")
    r.para("Later Unity experiments on terrain-matching corrections, and a re-analysis on 12 terrain areas, showed that an earlier "
           "\"shifted map fails\" result was a scoring artefact, that speed violations come from wrong matches rather than late ones, and "
           "that a short classical Kalman chi-square gate beat a learned trust policy. A separate machine-learning study (a fault-or-terrain "
           "classifier with corrected labels and a learned measurement-noise model, tested leave-one-world-out and reproduced on Site04) found that "
           "its value lies mainly in a noise-aware structure that a non-ML rule gate nearly matches.")
    r.para("The final round, pre-registered and run once on Site04, tested three small engine changes (noise floor, terrain variance, noise-aware fault label) found in that work. Letting the tolerance gate follow "
           "the altimeter's current noise level raised landing success at eight times normal noise from 62% to 95%, against 66% for the PITFAL-style baseline (our single-beam reimplementation, not NASA's system) and "
           "89% for our trust rule; all five pre-registered rules were met, one of them (against our trust rule) only as a weak test within noise. The gain needs no machine learning. On the development worlds, delayed readings without time stamps and a 2 km wrong map defeated every rule in round 3 (round 5 later fixed the delay case). An exploratory study with an assumed three-beam altimeter found that no single rule wins everywhere: letting the gate follow the noise level helps most at high noise but collapsed on one procedural terrain, and a true-noise oracle collapsed there too, so the cause is the terrain, not the noise estimate. A second pre-registration, run once on four reserved worlds, was half met: the safer candidate (noise floor in the update only) failed two of its four rules, so its development gain did not replicate, while the noise floor in both places did not collapse and helped a single-beam altimeter with a 100 m map offset. A third, exploratory round tried the techniques of a build plan on the development worlds: Student-t weighting of readings, mixing of noise modes, delay estimation without time stamps and soft camera weighting helped in some cases, several others did not, and no rule solves a 2 km wrong map; the pre-registered test of the best candidates on ten reserved worlds met five of seven rules: Student-t weighting matched the PITFAL-style rule at low noise and beat it by about 20 points at high noise, delay estimation recovered unstamped readings (1.5% to 51%), but its development edge over the full noise floor at low noise did not replicate. A last, exploratory study replaced the point-mass lander by a six-degree-of-freedom model (one body-fixed engine, limited attitude torque, gyro and star-tracker attitude estimate, body-fixed beams): with a working attitude loop the ranking of the rules held, but vehicles with a slow attitude loop or poor attitude sensing failed with every rule. All vehicle numbers are assumed. All results are simulation only.")



def body(r):
    for k, v in REFS.items():
        r.refs[k] = v
    r.new_section(number=True, fmt="decimal", start=1)

    # ================= 1 INTRODUCTION =================
    r.chapter(1, "Introduction")
    r.h2("Background and motivation")
    r.para("Powered descent to the Moon must finish within tight limits: low vertical speed, low sideways speed and a small tilt at "
           "touchdown. The lander has no satellite navigation, so it integrates its inertial sensors and corrects the drifting estimate "
           "with ground-facing sensors: a laser altimeter, a camera that recognises landmarks, and increasingly a lidar scan compared "
           "with a stored height map (terrain-relative navigation, TRN). Each correction is useful only if the lander decides correctly "
           "whether to believe it.")
    r.para("The lunar South Pole makes that decision harder. The Sun stays 1.5 to 3 degrees above the horizon, so shadows are long and "
           "large parts of the ground are dark to a camera, and the terrain has steep crater rims with height changes of kilometres "
           "over short distances. Landing at the South Pole in varied lighting is the first of NASA's 40 FY26 technology focus "
           "areas (need statement 3.02) {nasa_stmd}.")
    r.h2("Motivating failures")
    r.para("Of the commercial lunar landings attempted between 2023 and 2025, four crashed or tipped over, and in each the altitude or "
           "terrain data used in terminal descent was wrong, missing or rejected {ispace_m1, newatlas_im1, sp_im2, sp_m2}. "
           "HAKUTO-R M1 is the clearest case for this work. Its altimeter reading jumped as it crossed a crater rim about 3 km high; the "
           "filter's outlier rule, a deliberate protection against hardware faults, rejected the correct reading as a sensor fault, and "
           "the lander believed it was at 0 km while still about 5 km up {ispace_m1}. IM-2 showed the opposite error: the rangefinder "
           "picked up noise even with its laser off, the software believed the lander was about 400 m up, and it touched down at 10 to 13 m/s "
           "{button}. In one case the software rejected a correct sensor and in the other it believed a faulty one; both are failures of judgement.")
    r.h2("Project overview")
    r.para("The project asks how a lander's navigation filter should decide which sensor readings and which terrain corrections to trust, and "
           "tests the answer by landing a simulated lander on real NASA terrain. Its main outputs are:")
    r.bullets([
        "**A testbed.** A Unity 6 project (Site04 and Site01 terrain, lander physics, descent autopilot, live scan module LUMEN, "
        "telemetry logging, a replay scene) and a Python test bench (world generator, batched Kalman filter, judges, scenarios, pipeline).",
        "**A controlled comparison of sensor-trust rules** on the unseen Site04, with pre-registration, 500 landings per cell and 95% intervals.",
        "**A camera reliability survey** measured with 300 rendered image pairs.",
        "**Terrain-matching and learned-trust experiments** in Unity, a re-analysis on 12 terrain areas, and a machine-learning evaluation "
        "of the fault-or-terrain classifier.",
        "**A pre-registered final round (round 3)** run once on Site04, showing that a simple noise-aware gate keeps landings safe under a noisy altimeter.",
        "**A complete record** of what was done, including corrections to earlier claims."])
    r.h2("Team and contributions")
    r.para("The project was carried out by the four candidates named on the title page. Contributions are recorded in the table below.")
    r.table(["Candidate", "Enrollment No.", "Contribution"],
            [["Abhishek Mishra", "240365", "Simulator owner: Unity testbed and Python bench (sim/engine.py), round-1 and round-2 studies, guidance ablation, project documents"],
             ["Rishabh Kumar", "240605", "Machine-learning evaluation: leave-one-world-out classifier test, corrected-label ml2 judge, learned noise model, fresh-world ablation and non-ML rule gate (branch ml-eval)"],
             ["Neil Jain", "240553", "Literature review and problem definition: recent landing-failure review, NASA priorities and descent-navigation architectures, the research gap and the reference list (Chapters 2 and 3)"],
             ["Khushi Vijay", "240511", "Data and reporting support: preparing the NASA PGDA terrain data, checking result tables and figures against the result files, and report formatting (Chapters 4 and 5)"]],
            [3.4, 2.8, 9.8], "Team members and contributions", align_num=False)
    r.h2("Organisation of the report")
    r.para("Chapter 2 reviews the literature and states the gap. Chapter 3 defines the problem, questions and objectives. Chapter 4 describes the "
           "data, testbed and each experiment. Chapter 5 reports results and discusses them, including claims that did not survive re-analysis. "
           "Chapter 6 concludes with limitations and future scope.")

    # ================= 2 LITERATURE REVIEW =================
    r.chapter(2, "Literature Review")
    r.h2("Mission evidence: navigation failures in terminal descent")
    r.para("Table 2.1 lists the landing attempts that matter for this work with the navigation cause as publicly reported. Every commercial failure "
           "involved altitude data that was rejected, missing, noisy or late.")
    r.table(["Mission", "Date", "Outcome", "Navigation cause (as reported)"],
            [["HAKUTO-R M1 (ispace)", "25 Apr 2023", "Crash, Atlas crater", "Altimeter reading jumped at a ~3 km crater-rim cliff; filter rejected it as a sensor fault; lander believed 0 km while ~5 km up {ispace_m1}"],
             ["IM-1 Odysseus (Intuitive Machines)", "22 Feb 2024", "Broke a leg, tipped over (about 80 deg S)", "Laser rangefinders unusable because a ground safety switch was not flipped; NASA's NDL experiment was patched in {newatlas_im1}"],
             ["IM-2 Athena (Intuitive Machines)", "~6 Mar 2025", "Landed on its side near the South Pole", "Altimeter noise and distortion, long low-Sun shadows, crater imagery that did not match at low altitude {sp_im2, button}"],
             ["ispace M2 RESILIENCE", "6 Jun 2025", "Crash, Mare Frigoris", "Laser rangefinder slow to give valid readings, so the lander could not decelerate in time {sp_m2}"],
             ["Chandrayaan-3 (ISRO)", "Aug 2023", "Soft landing", "Laser plus wide-footprint Ka-band microwave altimeter; wider footprint helped with abrupt altitude changes {mehta_ch3}"],
             ["SLIM (JAXA)", "Jan 2024", "Landed (pinpoint)", "Crater matching against a pre-built Kaguya map; all 14 image-matching fixes judged accurate {jaxa_slim}"]],
            [3.3, 2.0, 3.0, 7.7], "Recent lunar landing attempts and reported navigation causes", align_num=False)
    r.para("A qualitative review of 12 news reports on robotic landers found that leg stability was cited most often, with altimeter or "
           "rangefinder problems in 5 of 12 {freeman}. HAKUTO-R's site is in the northern hemisphere; the South Pole evidence comes from IM-1 and IM-2.")
    r.h2("NASA priorities and descent navigation architectures")
    r.para("NASA's FY26 shortfall prioritisation selects 40 need statements as focus areas; four match this project: 3.02 (land on South Pole "
           "sites in various illumination conditions with appropriate accuracy, listed first), 3.03 (stable touchdown on uneven or sloped terrain), "
           "24.03 (autonomous navigation) and 24.05 (lunar position, navigation and timing) {nasa_stmd}.")
    r.para("NASA's SPLICE project, started in FY2018, combines terrain-relative navigation, Navigation Doppler Lidar and a hazard-detection lidar "
           "and targets landing within 50 m of the intended site {splice}. The Nova-C hazard detection design must confirm a site free of hazards "
           "over 30 cm with slope below 10 degrees, running about 400 m above the target within 15 s {getchius}. NASA field tests of lidar-based "
           "TRN report position estimates under 90 m with less lighting sensitivity than camera TRN {nasa_lidar_trn}. Autonomous terrain mapping "
           "during descent is emerging, which motivates the live-scan extension in this project.")
    r.h2("Terrain and illumination data")
    r.para("Barker et al. produced 5 m per pixel elevation maps of South Pole landing sites from Lunar Orbiter Laser Altimeter (LOLA) data, "
           "with orbit errors cut by more than ten times and per-pixel height and slope uncertainty {barker}; they are released as PGDA Product 78 "
           "{pgda78}. Mazarico et al. computed polar illumination over an 18.6-year cycle from 240 m LOLA maps {mazarico}. Bertone et al. sharpen "
           "LOLA maps with Shape-from-Shading on LROC images over more than 4,500 square kilometres of Artemis III candidate regions (PGDA Product 104) "
           "{bertone}. Together these let a lander know before launch where cliffs and shadows lie, with an error estimate for every pixel.")
    r.h2("Measurement rejection and sensor degradation")
    r.para("A standard Kalman filter rejects a measurement when its normalised innovation exceeds a fixed chi-square threshold {barshalom}. "
           "The threshold assumes the terrain model is accurate between updates, which a kilometre-scale cliff breaks. Terrain-aided navigation "
           "(SITAN) linearises the DEM slope under the vehicle so an altimeter can correct position {hostetler}, but the linearisation fails at cliffs. "
           "Adaptive filtering re-estimates noise covariances from the data stream {mehra}; it reacts after the fact instead of using a map to "
           "anticipate change. For plume-dust degradation, the ARC-LIGHT team trained a small network to estimate dust thickness from camera images "
           "and corrected lidar distances with it, shutting the system off when its error grew too large {cushen}. The lesson is that sensor trust "
           "should change with the situation, not only with hardware health.")
    r.h2("Closest prior work")
    r.para("The building blocks are published and recent. The closest paper is the NASA and Draper work for SPLICE {adams}: a DEM-based "
           "slant-range altimeter model with a chi-square fault test at a fixed limit of 6.635 (99%, one degree of freedom), where a flagged beam's noise "
           "is inflated until it passes, evaluated with 1,000 Monte Carlo runs on a 10 km by 10 km patch of a PGDA South Pole DEM. This project "
           "reimplements that idea as the \"PITFAL-style\" judge; it is our reimplementation, not NASA's system.")
    r.table(["Work", "What it does", "Gap left open"],
            [["Adams et al., AIAA SciTech 2025 (PITFAL) {adams}", "DEM slant-range model; fixed 99% chi-square gate; noise inflated for flagged beams", "Fixed gate, reactive; needs multi-beam sensor; no lighting or camera trust"],
             ["Karlgaard et al., 2025 {karlgaard}", "Reconstructs IM-1's last 3 minutes with NDL, IMU, a lunar DEM and lidar ray-tracing; agreement within ~5 m and 0.5 m/s", "Post-flight and offline; shows a DEM-based altimeter model works on flight data"],
             ["Prakash and Raha, 2026 (preprint) {prakash}", "Detects EKF inconsistency on real lunar powered-descent telemetry earlier than standard alarms", "No terrain map or lighting; reactive"],
             ["Sheppard et al., 2026 {sheppard}", "Gaussian-process elevation maps from LRO DEMs with noise learned from DEM confidence", "For hazard detection and site selection, not filter trust"],
             ["Tomasicchio et al., ION GNSS+ 2024 {tomasicchio}", "Preliminary Mahalanobis check; altimeter noise fixed at 1% of height", "Fixed gate; no terrain or lighting"],
             ["Shoemaker et al., AIAA SciTech 2022 {shoemaker}", "TRN in autoNGC; images timed for a 20 to 40 degree Sun", "Lighting handled by planning only; the South Pole Sun (1.5 to 3 degrees) has no such window"],
             ["Cauligi et al., 2023 (ShadowNav) {cauligi}; Candan and Servadio, 2026 {candan}", "Crater-based localisation in shadow with added hardware; deep-learning crater TRN with fixed camera noise", "Hardware fix for rovers; camera noise does not change with lighting"]],
            [4.6, 6.0, 5.4], "Closest prior work and the gap each leaves open", align_num=False)
    r.para("Cowan et al. fuse optical flow with a laser rangefinder for small landers over South Pole terrain {cowan}, without terrain-jump or shadow handling.")
    r.h2("Research gap and positioning")
    r.para("We found no published paper that sets a lander filter's outlier gate or sensor weights ahead of time from terrain and illumination maps; "
           "searches for adaptive gating, adaptive chi-square and illumination-dependent measurement covariance in lunar landing found no match. "
           "IEEE Xplore and AIAA proceedings are paywalled, so this must be rechecked through the college library before any novelty claim. "
           "A joint map, registration and sensor-uncertainty approach is therefore a candidate contribution and not an established one. "
           "The project is positioned as a controlled, reproducible comparison of trust rules and of when terrain corrections help or hurt, "
           "with its negative findings reported, rather than as a new flight method.")

    # ================= 3 PROBLEM STATEMENT =================
    r.chapter(3, "Problem Statement")
    r.h2("Problem")
    r.para("During powered descent to a lunar South Pole site, a navigation filter must fuse a laser altimeter, a camera, an IMU and, optionally, a "
           "lidar scan. It cannot easily tell a real terrain discontinuity, or a shadowed featureless scene, from a sensor fault. With a fixed outlier "
           "gate and fixed sensor weights the filter either rejects valid altimeter data at crater rims, as HAKUTO-R M1 did, or keeps trusting a camera "
           "that cannot see in shadow. The problem is to adjust, from known terrain and illumination, how much the filter trusts each sensor and each "
           "terrain correction, and to measure whether this changes the safety of touchdown.")
    r.h2("Research questions")
    r.bullets([
        "**RQ1.** Can 5 m per pixel LOLA elevation and slope maps predict where a true altimeter jump will exceed a standard chi-square gate?",
        "**RQ2.** Can solar geometry plus the DEM predict where the camera's view is too shadowed to be reliable?",
        "**RQ3.** Does adjusting gate size and sensor weights from these predictions cut altitude error and false rejections without letting faults through?",
        "**RQ4.** Which way of judging a surprising reading works best: a fixed rule, a map-based tolerance, a wait-and-see consistency check, or a trained classifier?",
        "**RQ5.** Does the approach still work at a site it was never tuned on?",
        "**RQ6 (added after the Unity terrain-matching experiments).** When should a lander accept, shrink or ignore a terrain correction, and does that choice change how safely it touches down?"])
    r.h2("Objectives")
    r.table(["#", "Objective", "Status at the time of writing"],
            [["O1", "Hazard (cliff) and blind-spot (shadow) maps for Site04 and Site01", "Done inside the test bench for Site04 (terrain-height spread, lit fraction); Site01 added as tuning site"],
             ["O2", "Trust layer and a fault-versus-terrain check", "Done and evaluated (versions v1 and v2)"],
             ["O3", "Reproduce recent failure modes with a fixed-gate filter", "Done: cliff (HAKUTO-R), shadow with noisy altimeter (IM-2), delayed readings (ispace M2), dropout (IM-1)"],
             ["O4", "Monte Carlo comparison, about 500 runs per scenario", "Done: 500 runs per cell with 95% intervals"],
             ["O5", "Reproducible release and side-by-side replay", "Done: repository, seeds and replay scene with trust bars; the live-flight HUD has no per-sensor trust bars yet"],
             ["O6", "Site-change robustness", "Done: unseen site, divert, shifted map, missing map; the missing-map fallback of the first version failed and was repaired in version 2"],
             ["O7", "Live 3D scan extension", "Done in Unity (LUMEN); the bench uses a simplified scan-fix model (true position, map shift and Gaussian noise; no matching is simulated)"]],
            [1.0, 6.4, 8.6], "Project objectives and status", align_num=False)
    r.h2("Hypotheses and scope")
    r.para("Four hypotheses were set at the start (H1: the trust rule rejects far fewer real cliff readings than the fixed rule; H2: shadow-aware "
           "camera trust reduces error in dark areas; H3: when position is well known the PITFAL-style method does as well; H4: the rule works at a site "
           "it was never tuned on). For the round-2 evaluation they were replaced by six pre-registered hypotheses P1 to P6 (Section 4.7, results in Section 5.3).")
    r.para("In scope: powered descent from about 15 km altitude to touchdown including leg contact; a laser altimeter, a rendered camera and an IMU; "
           "real PGDA terrain plus procedural worlds; the navigation filter, trust layer, guidance on the estimated state, and ML models. Out of scope: "
           "orbit and launch, new sensor hardware, flight hardware or hardware-in-the-loop tests, flight-software certification, boulder avoidance, "
           "engine failures, sensors that never switch on, and plume dust (to be added later as another condition).")

    # ================= 4 METHODOLOGY =================
    r.chapter(4, "Methodology")
    r.h2("Overview of the studies")
    r.para("The work proceeded in nine stages. Table 4.1 lists them with what each added; later stages corrected conclusions of earlier ones, "
           "and Chapter 5 reports the corrected picture.")
    r.table(["Stage", "Date (2026)", "What was done"],
            [["Round 1", "16-19 Oct", "Unity Site04 scene, lander physics, autopilot, LUMEN scan; Python bench with 7 judges and 5 scenarios; 500-run Site04 comparison with an assumed camera-damage curve"],
             ["Round 2", "19 Oct", "Camera measured in Unity (300 image pairs); trust layer v2; pre-registration, freeze, single Site04 run"],
             ["Terrain matching and learned scan trust", "21-22 Oct", "Unity estimated-state descents with scan matching; learned trust model; utility policy; frozen-model Site01 transfer (810 descents)"],
             ["Navigation v3", "4 Nov", "Ten-state EKF with map-height bias, delayed-measurement replay, terminal braking, optional bounded ML advice; 324 engineering cases"],
             ["Re-analysis and guidance ablation", "8 Nov", "Rescoring of earlier claims; 12 Site01 areas; guidance variants; classical Kalman chi-square gate; relief and IMU stress tests"],
             ["ML judge evaluation", "13-14 Nov", "Leave-one-world-out classifier test; corrected-label ml2 judge; learned noise model; fresh-world ablation; non-ML rule gate (branch ml-eval); reproduced 19-20 Nov"],
             ["Round 3", "20 Nov", "Three default-off engine switches (noise floor, terrain variance, noise-aware label); screened on tuning worlds, confirmed on fresh worlds, pre-registered, frozen at tag prereg-round3 and run once on Site04"],
             ["Round 4 (development)", "20 Nov", "Three-beam altimeter, where the noise floor enters, correlated noise, map offsets; exploratory only. Its held-out test on reserved worlds 17 to 20 was frozen (tag prereg-round4) and run once on 20 Nov; two of four rules failed"],
             ["Round 5 (development)", "21 Nov", "Eleven techniques from a build plan added as default-off switches and compared on the nine development cells with new fault types (exploratory); the best candidates were then frozen (tag prereg-round5) and run once on reserved worlds 41 to 50: five of seven rules met"],
             ["Round 6 (6-DOF dynamics)", "21 Nov", "Rigid-body lander with one body-fixed engine, torque-limited attitude control, gyro and star-tracker attitude estimate and body-fixed altimeter beams, as a default-off switch; development worlds only (exploratory, not pre-registered)"]],
            [3.6, 2.4, 10.0], "Stages of the project", align_num=False)

    r.h2("Data and terrain")
    r.para("Real terrain comes from NASA PGDA Product 78 {pgda78, barker}: Site04 on the Shackleton crater rim (used as the unseen test site) and Site01 on "
           "the connecting ridge (used for tuning and, later, for the 12-area studies), at 5 m per pixel in 16 km by 16 km tiles with elevation and "
           "height-error maps. The slope file supplied for Site04 was truncated, so slope is derived from the elevation file. The Python bench "
           "subsamples terrain to 10 m (every second pixel). Procedural crater worlds provide extra tuning and classifier-training terrain. The simulated Moon contains unmapped "
           "craters, roughness and a registration shift that the onboard map lacks, so the map is imperfect by design.")
    r.para("The Site04 tile spans -2,848 m to +1,805 m (4.65 km of relief) with slopes up to about 70 degrees. With the Sun 2 degrees above the horizon, "
           "at least 51% of the tile is in cast shadow, and a further 46% cannot be classified from the tile alone because terrain up to about 130 km away "
           "can cast shadows at that angle; shadow modelling therefore needs a wider horizon map.")
    r.figure(R + "out/site04/01_elevation_slope.png", "NASA PGDA Site04 (Shackleton rim, LOLA, 5 m per pixel): elevation (left) and slope (right). Most of the crater wall is steeper than the 10 degree Nova-C landing limit.", 15.0)
    r.figure(R + "out/site04/03_cross_section.png", "A track across the Site04 tile: the ground rises to the rim and then falls 4.5 km to the crater floor, the kind of change that tripped HAKUTO-R.", 14.5)

    r.h2("Testbed architecture")
    r.para("The testbed has two parts that share scenarios and seeds. The **Unity project** (Unity 6, version 6000.3) holds the Site04 scene, a rigid-body lander "
           "under lunar gravity (1.62 m/s^2) with a throttleable engine, fuel budget and legs that can tip over, a descent autopilot, the live scan module "
           "LUMEN (lidar scanner, height patch and patch matcher), a heads-up display, a telemetry logger, a replay scene that plays recorded descents "
           "with several filters side by side, and a camera-survey tool. The **Python test bench** (world generator, batched Kalman filter, judges, scenarios and "
           "pipeline) runs thousands of seeded descents quickly; the Unity project is also run headless (batch mode, no graphics) for large studies, about "
           "20,000 landings in under an hour.")
    r.para("One simulation step runs: terrain query and lighting, rigid-body physics, sensor generation with injected faults, filter update through the judge, "
           "guidance on the *estimated* state, and logging of truth and belief side by side. Because guidance uses the estimate, a wrong altitude belief becomes "
           "a real crash, as it did on HAKUTO-R.")
    r.table(["Layer", "What it does", "Tools"],
            [["Terrain", "Real PGDA DEMs as Unity heightmaps; procedural craters and roughness", "Python (Pillow, numpy); Unity Terrain"],
             ["Physics", "Rigid-body lander, throttleable engine, fuel, legs", "Unity PhysX; 3-DOF point-mass model in the bench"],
             ["Sensors", "Laser altimeter, IMU with bias and noise, rendered camera, optional live lidar scan, fault injection (bursts, dropouts, delays)", "C# scripts; Python bench"],
             ["Navigation", "Kalman filter with a pluggable judge for each reading; guidance on the estimate", "C# at runtime; Python prototypes"],
             ["Machine learning", "Fault-or-terrain classifier; scan-trust model; error-size regressor", "scikit-learn"],
             ["Visualisation", "HUD, ghost lander at the estimated position, replay of several filters", "Unity UI"]],
            [2.6, 8.2, 5.2], "Layers of the LANTERN testbed", align_num=False)

    r.h2("Vehicle, guidance, sensors and scenarios")
    r.para("The bench lander is a point mass under lunar gravity with a throttleable engine and fuel (a six-degree-of-freedom option is described under round 6 in the Results chapter). Guidance flies a speed profile on the estimated "
           "terrain-relative altitude. A landing succeeds if vertical speed is at most 2 m/s, horizontal speed at most 1.5 m/s, slope at most 10 degrees and "
           "fuel remains. Sensors are an IMU with bias and noise, a laser altimeter with range-dependent noise and fault bursts, a camera whose position fixes are "
           "drawn from the measured survey (Section 4.6) and an optional live lidar scan. Five scenarios reproduce recent failure modes:")
    r.bullets([
        "**Cliff (HAKUTO-R):** a real height change of kilometres at a crater rim.",
        "**Cliff plus faults:** the same with frequent injected altimeter fault bursts.",
        "**Shadow plus noisy altimeter (IM-2):** noisy range data with a camera that cannot see in shadow.",
        "**Delayed altimeter (ispace M2):** readings that arrive late.",
        "**Altimeter dropout (IM-1):** the sensor stops giving readings."])
    r.para("Every judge in a comparison sees identical noise and faults.")

    r.h2("Judges and the trust layer")
    r.para("A *judge* decides what to do with each altimeter reading that fails the standard gate. Seven judges and variants are compared (Table 4.3). "
           "The trust layer asks four questions in order for each reading: is it physically possible given the lowest and highest ground within the "
           "lander's position uncertainty; if surprising but possible, does it stay consistent and follow the map's shape during a short probation of about 2 to 3 s; "
           "is the ground below lit enough to use the camera, and with what weight; and, outside map coverage, fall back to the standard rule plus probation. "
           "The map-driven terms enlarge the gate where terrain varies: the gate adds the variance of DEM heights inside the position-uncertainty ellipse "
           "and the LOLA height error (the tile's mean PGDA total error for Site01, a default 3 m for Site04; no per-pixel error is used).")
    r.para("Trust layer version 2 learns the noise level online from accepted readings, time-stamps readings so a late reading is compared with the prediction "
           "at the instant it was taken, and tracks the ground height under the lander when no map exists.")
    r.table(["Judge", "Idea"],
            [["Fixed rule", "Reject anything beyond a fixed chi-square limit, with a coarse terrain reference (what HAKUTO-R did)"],
             ["PITFAL-style", "Map in the prediction; fixed 99% limit; noise inflated after a flag {adams} (our reimplementation)"],
             ["Map tolerance", "Allow larger surprises where the map shows heights varying within the position uncertainty"],
             ["Wait and see", "Accept a surprise that stays consistent for a few seconds"],
             ["Second opinion", "Check the surprise against the IMU and camera"],
             ["ML classifier", "A random forest trained on simulated descents labels each surprise as terrain or fault"],
             ["Trust v1 / v2", "Four-step rule (physical possibility, probation, camera and shadow, no-map fallback); v2 adds a learned noise level, time stamps and a no-map tracker"]],
            [3.4, 12.6], "Judges compared", align_num=False)

    r.h2("Camera reliability survey")
    r.para("Round 1 judged cameras with a hand-made shadow-damage curve, which made the comparison unfair. Round 2 measured the camera instead. In Unity, "
           "300 paired nadir images of Site04 were rendered with the true Sun and with a prediction from the map that has 0.05 to 0.25 degree Sun-elevation error "
           "and plus or minus 1 degree azimuth error, reflections switched off so shadows are dark, read noise of 2 digital numbers and shot noise. A "
           "landmark matcher based on zero-mean normalised cross-correlation (ZNCC) produced position fixes and a confidence (the correlation peak). The "
           "onboard prediction used direct light only. The simulator draws camera fixes from these measurements by lit fraction. Every judge receives the same "
           "camera, gated at a matcher confidence of 0.5 (fixed in advance).")

    r.h2("Evaluation protocol and pre-registration")
    r.para("The round-2 design was written down before the Site04 run (docs/PREREG.md, git tag prereg-round2); round 1 is preserved at tag round1. "
           "Probation window (8, 10 or 12 samples) and consistency threshold (2.5, 3 or 4 sigma) were chosen by grid on procedural worlds and Site01 only; "
           "Site04 was never used for tuning and was run once after the freeze. Each cell has 500 seeded runs with 95% intervals (seed 20260101). "
           "Metrics are landing success (%), altitude error (RMS, m), false rejection of valid readings (%), missed injected faults (%), "
           "camera weight in shadow and fuel left. The six hypotheses were:")
    r.bullets([
        "**P1.** Trust v2 beats PITFAL-style by at least 10 points of landing success in cliff, cliff plus faults and shadow plus noisy.",
        "**P2.** Trust v2 has a lower false-rejection rate than PITFAL-style in those three scenarios.",
        "**P3.** Trust v2 is fooled by faults at most 1 point more often than PITFAL-style.",
        "**P4.** Predicting the lit fraction from Sun and DEM improves on the matcher's confidence gate by at most 5 points.",
        "**P5.** The gap to PITFAL-style on the unseen Site04 is at least the tuning-site gap minus 10 points.",
        "**P6.** With time stamps, trust v2 lands at least 50% of runs with delayed readings."])
    r.para("Anything not listed was labelled exploratory. A disclosure is recorded in the pre-registration: a 100-run Site04 smoke test of the new code was "
           "inspected before the document was written.")

    r.h2("Terrain-matching and learned scan-trust experiments")
    r.para("From 21 October the Unity project was extended with estimated-state descents in which a live lidar scan is matched against the stored map and "
           "corrects the position estimate. Experiments ran stationary scans and short descents from 500 to 2,000 m over several terrain areas with a frozen "
           "matcher, with conditions for an accurate map, changed terrain (unmodelled relief) and a shifted map. A scan-specific trust model was then "
           "trained (10,530 labelled scan proposals, a 32-tree model whose Python and Unity outputs were checked equal on 10,530 inputs), followed by a "
           "utility-based correction-gain policy (7,680 collected proposals, 672 development descents) evaluated on reserved areas, and a frozen-model "
           "transfer test on three Site01 areas. For the later evaluations the model, policy and success criteria were fixed before the run.")
    r.h2("Navigation v3")
    r.para("Navigation v3 is a separate estimated-state landing loop: a ten-state EKF with a local map-height bias, replay of delayed measurements, "
           "innovation and geometry checks, terminal braking, seeded sensor faults and optional bounded advice from a frozen ML model. Its live scene is "
           "NavigationV3.unity, and batch and offline verification tools check every record.")
    r.h2("Re-analysis and guidance ablation (8 November)")
    r.para("A literature check and re-analysis prompted a new, pre-registered study run headless in Unity (6000.3.24f1, batch mode, 3-DOF PhysX, seed 717). "
           "The unit of analysis is the terrain area, 12 Site01 areas, because runs on the same terrain are not independent. The study crossed three guidance variants "
           "(baseline, terminal-phase, braking-curve) with correction rules (off, geometric matching, bounded, learned utility, authority-aware) over five conditions "
           "(aligned map, 3 m and 8 m map-tie errors, 38 m map shift, unmodelled positive relief), for 5,400 descents. A classical Kalman chi-square consistency gate "
           "was then added (constants fixed a priori: start variance (100 m)^2, fix variance (2 m)^2, process noise 0.05 m^2/s, 99% gate; 1,800 descents), followed by "
           "exploratory sweeps of unmodelled-relief amplitude from 0.5 to 16 m over four shapes (10,800 descents) and accelerometer-bias stress (3,888 descents). "
           "Validation: with baseline guidance the new runner reproduced the frozen transfer runner's smoke outcomes exactly (12 matched cases, zero difference).")
    r.h2("Machine-learning judge study (ml2)")
    r.para("The ML-side study re-examined the random-forest fault-or-terrain classifier. It audited the simulator's own fault label, scored the classifier by "
           "leave-one-world-out evaluation, built a corrected-label classifier on 22 flight features (map consistency, vertical speed and a 10 s history of flagged "
           "readings; a 0.5 MB gradient-boosting model) and added it to the engine as an additive judge, ml2, with two modes: soft (accept a flagged reading with "
           "noise inflated by 1/(1-p)^2 for fault probability p) and hard (reject if p exceeds 0.5). It then compared three ways of setting a measurement-noise floor "
           "(none, a learned error-size model, and a non-ML running innovation estimate taken from trust v2), ablated the classifier's decision (accept all flagged "
           "readings, reject all), and tested a non-ML rule gate: a tolerance-style gate with terrain variance and an adaptive noise estimate, using no model. "
           "Evaluation used four tuning worlds (procedural 11 to 13 plus Site01) and fresh procedural worlds 14 to 16 never used for training or tuning, "
           "100 descents per world, with noise conditions of x2, x4, x8 and x16 altimeter noise.")
    r.h2("Round-3 protocol (pre-registered)")
    r.para("Round 3 tested three changes to the simulator's judges, each added as a switch that is off by default so every earlier result stays reproducible. "
           "(1) *Noise floor:* the tolerance judge never trusts a reading more than the running size of its recent surprises (trust v2's innovation estimate), in both its gate and its measurement variance. "
           "(2) *Terrain variance:* the wait-and-see, second-opinion and ML judges give readings that pass the gate the same terrain and map variance the tolerance and trust judges already use. "
           "(3) *Noise-aware label:* the ground-truth fault label compares the error with the true noise level (nominal sigma times the scenario's multiplier) instead of the nominal sigma; this changes only the false-rejection and missed-fault bookkeeping, never a decision.")
    r.para("The changes were screened on the tuning worlds, then checked on three fresh procedural worlds (14 to 16, never used for training or tuning) against rules written before that run. "
           "The Site04 test was then frozen: the engine, runner, tests and the pre-registration were committed and tagged prereg-round3, the runner refuses to start unless that tag is the current commit "
           "and the code is unchanged, and it refuses a second run. Settings: 500 runs per cell, seed 20261201, the confidence-gated camera for every judge, time stamps for every judge in the delayed condition, "
           "and untuned constants. Five decision rules were fixed in advance (Q1 to Q5, stated with the results in Section 5.9).")
    r.h2("Tools and environment")
    r.para("Unity 6 (6000.3) with C# scripts; Python with numpy, scipy, pandas, scikit-learn, matplotlib and Pillow; NASA PGDA GeoTIFF terrain; git for version "
           "control with tags round1 and prereg-round2. Experiments are seeded and every result table is regenerated by a named script.")

    # ================= 5 RESULTS =================
    r.chapter(5, "Experimental and Simulation Analysis and Discussion of Results")
    r.para("All results are from simulation. Numbers are taken from the result files in the repository and the documents named in each section.")
    r.h2("Camera reliability")
    r.table(["Lit fraction of footprint", "Median error (m)", "Fixes off by more than 100 m", "Median matcher confidence"],
            [["0 - 5%", "401", "88%", "0.00"], ["5 - 25%", "7.6", "20%", "0.86"], ["25 - 50%", "2.4", "0%", "0.98"],
             ["50 - 80%", "1.3", "0%", "0.97"], ["80 - 100%", "0.8", "0%", "0.92"]],
            [4.6, 3.4, 4.6, 3.4], "Camera fix error by lit fraction (300 image pairs, Site04)")
    r.para("The matcher is accurate once a quarter of the footprint is lit and fails in the dark. Among the 226 fixes with confidence of at least 0.5, none "
           "was off by more than 100 m, so the matcher's own confidence is a reliable failure detector. The survey uses one renderer, one matcher and one site.")

    r.h2("Site04 comparison of sensor-trust rules (round 2)")
    r.table(["Scenario", "Fixed", "PITFAL", "Map tol.", "Wait", "2nd op.", "ML", "Trust v1", "Trust v2", "v2 + scan"],
            [["Cliff (HAKUTO-R)", "0.2", "82.0", "97.2", "79.6", "56.6", "75.8", "94.6", "96.8", "100.0"],
             ["Cliff + faults", "0.0", "85.6", "97.6", "80.2", "8.6", "76.0", "94.8", "97.4", "99.8"],
             ["Shadow + noisy (IM-2)", "0.0", "64.0", "61.6", "28.6", "15.6", "23.8", "53.4", "88.0", "59.2"],
             ["Delayed (ispace M2)", "0.0", "0.0", "0.0", "0.2", "0.0", "0.4", "0.0", "83.0*", "95.8*"],
             ["Dropout (IM-1)", "0.0", "34.8", "41.6", "29.0", "26.2", "24.2", "31.4", "37.0", "61.4"]],
            [3.2, 1.2, 1.6, 1.5, 1.2, 1.4, 1.2, 1.5, 1.5, 1.7],
            "Landing success (%) on the unseen Site04, 500 runs per cell, confidence-gated camera for every judge (95% intervals about plus or minus 2 to 4 points; * trust v2 uses time-stamped readings, the others do not)", font=9)
    r.figure(split_fig(R + "out/plots/01_success_by_scenario.png", 1592, 96, "success"), "Landing success on Site04 by judge and scenario, 500 runs per cell, with 95% intervals (round 2).", 15.8)
    r.para("A fixed gate with a coarse reference reproduces the HAKUTO-R failure: it rejects 99% of good altimeter readings on Site04 and the lander is lost in 499 of 500 runs. "
           "Putting the terrain map into the filter is the big fix: success rises from 0.2% to 82% (PITFAL-style) and to 97% with a plain map-tolerance gate. "
           "In cliff cases trust v2 (97%) matches the plain tolerance gate, and probation changes little (95.0% without it, 94.6% with it, for v1). Trust v2 clearly wins "
           "with a noisy altimeter in shadow (88% against 64%), with no map (91% against 3%) and on a mid-descent divert (91% against 74%), at the price of being fooled by "
           "faults more often in the noisy case (52% against 33%). It fails badly with a noisy altimeter in good light (39% against 99.5%) and with a map shifted by 2 km (1% against 35%), "
           "where its physical-possibility check rejects readings that do not fit the map.")

    r.h2("Pre-registered hypotheses")
    r.table(["#", "Hypothesis", "Outcome"],
            [["P1", "Trust v2 beats PITFAL-style by at least 10 points (cliff, cliff + faults, shadow + noisy)", "Met: +14.8, +11.8, +24.0"],
             ["P2", "Lower false rejection than PITFAL-style", "Mixed: lower in cliff (0.2 vs 0.8) and shadow + noisy (3.8 vs 4.3); higher in cliff + faults (1.7 vs 0.6)"],
             ["P3", "Fooled by faults at most 1 point more often", "Met in cliff scenarios (4.9 vs 7.1, 6.1 vs 7.9); failed in shadow + noisy (52.4 vs 32.5)"],
             ["P4", "Sun-geometry camera prediction improves on the confidence gate by at most 5 points", "Supported: prediction is 5 to 11 points worse in three of four cases and 2 points better in the fourth"],
             ["P5", "Gap to PITFAL-style on unseen Site04 at least the tuning gap minus 10", "Met: Site04 98.0 vs 81.7 (cliff); Site01 100 vs 100"],
             ["P6", "Trust v2 lands at least 50% with delayed readings", "Met numerically (83.0%), but only because of time stamps"]],
            [1.0, 7.0, 8.0], "Outcome of the pre-registered hypotheses", align_num=False)

    r.h2("Camera policy and time stamps")
    r.figure(R + "out/plots/06_camera_policies.png", "Camera policies on Site04 (500 runs). Using every fix without a confidence check fails almost every landing; the matcher's own confidence is enough.", 14.5)
    r.para("A camera must never be used without its matcher's confidence: using every fix gives 0.4 to 3% success. Predicting darkness from the Sun and the "
           "terrain adds nothing over the matcher's own confidence and is slightly worse. For delayed readings, an exploratory control (not pre-registered) re-ran every "
           "judge with the same time stamps: PITFAL-style 74.2%, wait-and-see 79.0%, trust v1 79.6%, trust v2 83.0% and the plain map-tolerance gate 97.6%, "
           "while trust v2 without time stamps scored 0.0%. The time stamps, not the trust rule, solve this scenario.")
    r.figure(R + "out/plots/07_timestamps_exploratory.png", "Exploratory control: delayed-reading scenario with and without time stamps.", 11.5)

    r.h2("Sweeps and robustness")
    r.table(["Test", "PITFAL-style", "Trust v2", "Reading"],
            [["Initial position error 5 / 50 / 200 / 400 m (cliff)", "81 / 83 / 76 / 61", "97 / 98 / 95 / 96", "Gap grows with position uncertainty"],
             ["Mid-descent divert", "74.3", "91.3", "Works without re-planning"],
             ["No map", "2.7", "90.7", "Baseline uses a coarse reference; shows the fallback matters"],
             ["Map shifted by 2 km", "35.0", "1.3", "Trust v2 rejects readings that do not match the wrong map"],
             ["Site01 (tuned) vs Site04 (unseen), cliff", "100 vs 81.7", "100 vs 98.0", "No drop on the unseen, harder site"],
             ["Sun from the east, shadow + noisy", "99.5", "39", "Trust v2 collapses in good light with a noisy altimeter"],
             ["Sun from south or west, elevation 1.5-3 deg", "62-70", "81-90", "Trust v2 ahead when the lander is in shadow"]],
            [5.4, 2.8, 2.8, 5.0], "Sweeps and robustness checks, landing success (%), 300 runs per cell (200 for the Sun sweep)", align_num=False)
    r.para("The live scan lifts trust v2 to 100% in the cliff scenario, 95.8% with delayed readings and 61.4% with dropout, but hurts the shadow plus noisy "
           "scenario (59%, with 203 of 500 runs timing out in a hover).")
    r.figure(R + "out/replay_final.png", "Unity replay of one descent (cliff plus faults): the fixed-gate lander hovers about 1,268 m up believing it is 75 m below the surface, while the PITFAL-style and trust v2 landers have landed.", 14.0)

    r.h2("Unity terrain-matching and learned scan-trust results")
    r.table(["Experiment", "Cases", "Result"],
            [["Short descents with matching (21 Oct)", "54 descents, 27 scans", "Aligned map: mean target miss 70.31 m off, 0.42 m on; changed terrain and shifted maps exposed confident wrong corrections"],
             ["Expanded five-area test (22 Oct)", "540 descents, 270 scans", "Accurate map: 90/90 successes on, mean miss 93.94 m off and 0.49 m on; changed terrain 3/90; shifted map 0/90 (absolute-frame scoring, see Section 5.7)"],
             ["Learned scan trust v1", "648 descents", "Target successes: geometric 90/162, tuned rule 45/162, learned 18/162, off 0/162; the learned veto removed wrong updates but rejected useful ones"],
             ["Utility policy v2", "270 reserved-area descents", "Utility and geometric 24/54; mean miss 28.92 vs 34.64 m; speed violations 7 vs 12; previous ML veto 0/54"],
             ["Frozen-model Site01 transfer", "810 descents, 3 areas", "Both 54/162; mean miss 43.60 vs 45.99 m; speed violations 47 vs 39; prewritten transfer criterion failed"],
             ["Navigation v3 engineering run", "324 reserved-crop cases", "10 m successes 45/108 (classical) vs 37/108 (ML); 50 m: 83/108 vs 87/108; excess-speed contacts 21 vs 17; 6 timeouts; all 324 records passed offline verification"]],
            [4.4, 3.4, 8.2], "Unity terrain-matching, scan-trust and navigation-v3 results", align_num=False)
    r.para("These results show that a correction helps strongly when the map is right, that learned vetoes did not improve landings, and that neither "
           "broad reliability nor a consistent ML advantage is established. The navigation-v3 map-error field is a correlated synthetic proxy scaled by the "
           "PGDA total-error map, not a clone DEM.")

    r.h2("Re-analysis and guidance ablation")
    r.para("A literature check and re-analysis on 12 Site01 areas corrected several earlier statements.")
    r.table(["Finding", "Evidence"],
            [["F1. The earlier \"0 successes under map shift\" was a scoring artefact", "A 38 m map offset cannot be observed from the map; scored in the map frame, success at 10 m is 67 to 71% for every correcting rule instead of 0%"],
             ["F2. Small map-tie errors are harmless here", "With 3 m or 8 m shifts every correcting rule succeeded in 100% of cases, about 1 m mean miss, zero speed violations"],
             ["F3. Speed violations occur only when fixes are wrong", "Zero violations for every rule under map shifts; violations appear only under unmodelled relief (geometric 0.64, utility 0.68 of runs)"],
             ["F4. Better guidance helps only partly; an authority cap does not help", "For geometric matching under changed terrain, terminal-phase guidance cut the median per-area violation rate 0.83 to 0.58; the authority-aware gate was not supported (mean violation 0.53 vs 0.64)"],
             ["F5. A classical Kalman chi-square gate beat the geometric rule and the learned policy under changed terrain", "Violation rate 0.10 vs 0.64 and 0.68; mean map miss 29 m vs 100 m and 85 m; success at 10 m 54% vs 0%"],
             ["F6. Robustness envelope", "Geometric matching keeps 100% success up to 1 m of unmodelled relief, 75% at 2 m, 32% at 4 m, and is no better than doing nothing by 8 m"],
             ["F7. The gate survives accelerometer bias but its constants matter", "With bias 0.0002 to 0.005 m/s^2 the gate keeps violation about 0.10; with no map error and the largest bias it is slightly worse than geometric (7.0 vs 5.3 m)"]],
            [6.0, 10.0], "Findings of the 8 November re-analysis (simulation, 12 Site01 areas)", align_num=False)
    r.figure(R + "docs/figures/frame_artifact.png", "The same landings scored in two frames: under a 38 m map shift, success is zero in the true frame but about 0.67 in the map frame, because a map offset cannot be observed from the map.", 15.5)
    r.figure(split_fig(R + "docs/figures/violations_by_guidance_arm.png", 1596, 110, "violations"), "Touchdown speed violations by guidance variant and correction rule over 12 areas; violations appear only under unmodelled relief.", 15.5)
    r.figure(R + "docs/figures/relief_sweep.png", "Tolerance to unmodelled relief: mean miss, speed-violation rate and success versus relief amplitude. The classical Kalman chi-square gate (kf_chi2) degrades more slowly than the other correcting rules; the grey band is the reported DEM height RMS.", 15.5)
    r.figure(R + "docs/figures/imu_stress.png", "Accelerometer-bias stress test of the classical gate against the other rules under changed terrain.", 14.0)
    r.para("The published PGDA height RMS of 0.3 to 0.5 m (verified on NASA's Product 78 page on 9 November) lies inside the range where every correcting rule succeeds in this "
           "simulator. This supports the use of terrain corrections but does not establish performance on a real mission.")

    r.h2("Machine-learning judge study")
    r.para("The ML-side study (branch ml-eval) reports that the simulator's fault label used the nominal noise, so in the noisy-altimeter scenario 63.7% of valid, "
           "fault-free readings were labelled \"fault\"; that the committed classifier score (AUC 0.967) is the best of six worlds, with leave-one-world-out AUC of "
           "0.930 plus or minus 0.032; and that the corrected label with history and vertical-speed features raises the mean per-scenario AUC from 0.960 to 0.982. "
           "These label and offline-score findings come from the study's own audit files and were not re-run here. In flight, the new classifier alone did not help: "
           "the main cause of the weak ML judges was in the engine, which used bare altimeter noise for unflagged readings where the tolerance and trust judges add "
           "terrain variance. Adding that term lifted the old ml judge from 78.5% to 90.2% in cliff plus faults, level with PITFAL-style.")
    r.table(["Condition", "PITFAL", "Trust v2", "Tolerance gate", "ml2, learned noise", "ml2, running noise", "Rule gate (no ML)"],
            [["Cliff + faults", "89.2", "96.0", "92.0", "95.0", "93.2", "94.0"],
             ["x2 noise", "87.2", "92.0", "91.0", "94.0", "93.0", "93.2"],
             ["x4 noise", "88.2", "88.8", "71.2", "92.0", "90.5", "90.8"],
             ["x8 noise (training level)", "77.0", "78.0", "48.2", "84.0", "91.0", "86.5"],
             ["x16 noise", "45.2", "62.8", "37.2", "87.2", "89.0", "84.8"],
             ["x8 below 2500 m", "87.5", "91.2", "81.5", "90.5", "89.5", "90.8"]],
            [3.7, 1.7, 1.7, 2.1, 2.3, 2.3, 2.2],
            "Landing success (%), tuning worlds (procedural 11-13 and Site01), seed 7, 100 descents per world", font=9)
    r.table(["Condition", "PITFAL", "Trust v2", "ml2, learned noise", "ml2, running noise", "Rule gate (no ML)"],
            [["Cliff + faults", "83.3", "91.6", "93.4", "88.9", "90.9"],
             ["x2 noise", "81.6", "90.4", "93.0", "90.6", "94.4"],
             ["x4 noise", "83.0", "84.3", "91.7", "87.7", "90.4"],
             ["x8 noise", "70.1", "81.0", "78.9", "89.0", "83.9"],
             ["x16 noise", "40.0", "63.6", "83.9", "85.1", "78.7"],
             ["x8 below 2500 m", "78.7", "88.9", "89.6", "88.4", "89.4"]],
            [3.7, 2.0, 2.0, 2.8, 2.8, 2.7],
            "Landing success (%), fresh worlds (procedural 14-16, seed 101, plus tuning worlds with new seed 202), 7 world runs pooled", font=9)
    r.table(["Condition", "Classifier at 0.5", "Accept all flagged", "Reject all flagged"],
            [["Cliff + faults", "93.2", "34.0", "94.0"], ["x2 noise", "93.0", "47.5", "93.2"], ["x4 noise", "90.5", "64.0", "68.8"],
             ["x8 noise", "91.0", "75.2", "44.5"], ["x16 noise", "89.0", "80.0", "36.5"], ["x8 below 2500 m", "89.5", "70.5", "82.0"]],
            [4.6, 3.8, 3.8, 3.8], "Classifier ablation, tuning worlds, seed 7: landing success (%) when the classifier's decision is replaced by a constant")
    r.para("Over 42 fresh cells ml2 with the learned noise model beats PITFAL-style by 15.6 points on average (positive in 35 cells) and trust v2 by 5.1 (27 cells). Three controls change "
           "the interpretation. A non-ML running noise estimate (trust v2's innovation-size estimate) matches the learned noise model (difference +0.1, positive in 20 of 42 cells), "
           "so the learning in the noise model is not what helps. The classifier does real work inside the structure: accepting all flagged readings collapses with faults (34.0%) and "
           "rejecting all collapses with high noise (44.5% at x8, 36.5% at x16). Yet a fully non-ML rule gate does about as well as the classifier version (-0.3 points on average "
           "over 42 fresh cells), beats PITFAL-style in all six fresh conditions (+7 to +39) and is at or above trust v2 in five of six; the classifier's only edge is at high noise (about +4 to +6 points). "
           "The existing tolerance gate collapses under noise (48.2% at x8) but reaches 86.5% with terrain variance and an adaptive noise estimate.")
    r.h3("Reproduction of the ML results")
    r.para("On 19 and 20 November 2026 the five evaluation scripts and the older comparison were rerun from the committed seeds in a separate checkout. "
           "Row-by-row comparison with the committed result files found zero differences (96 of 96, 24 of 24, 168 of 168, 48 of 48 and 150 of 150 rows, and 72 of 72 for the comparison "
           "script). The engine checks passed (all older judges bit-identical to the reference in quick mode; flight features equal training features to 5e-7). Because the seeds are fixed, "
           "this shows that the runs are deterministic and faithful, not independent confirmation.")

    r.h2("Round 3 on the held-out site (Site04)")
    r.para("The frozen round-3 test ran once on Site04 with 500 descents per cell. Table 5.10 gives landing success for the main judges.")
    r.table(["Condition", "PITFAL", "Trust v2", "Tolerance", "Tol. + noise floor", "Wait", "Wait + terrain", "ML", "ML + terrain"],
            [["Cliff + faults", "83.4", "95.2", "97.0", "97.6", "83.0", "96.0", "76.0", "90.2"],
             ["x2 noise", "81.8", "96.2", "91.2", "96.0", "75.8", "92.4", "61.0", "73.4"],
             ["x4 noise", "84.8", "94.6", "78.0", "95.0", "62.2", "92.0", "28.6", "28.4"],
             ["x8 noise", "65.6", "89.0", "61.6", "94.6", "33.4", "55.4", "24.2", "32.8"],
             ["x16 noise", "38.6", "57.2", "42.8", "90.8", "18.0", "35.2", "18.0", "22.6"],
             ["x8 below 2500 m", "76.6", "96.2", "88.2", "97.2", "53.8", "73.0", "45.0", "48.4"],
             ["Delayed (time-stamped)", "70.8", "86.8", "96.0", "96.4", "77.8", "94.0", "72.2", "92.2"],
             ["Dropout (exploratory)", "33.6", "37.4", "44.6", "49.6", "29.2", "37.2", "25.2", "32.2"]],
            [3.0, 1.6, 1.4, 2.0, 1.8, 1.2, 1.8, 1.1, 1.6],
            "Landing success (%) on Site04, 500 descents per cell, frozen round-3 run (95% intervals about plus or minus 2 to 4 points)", font=9)
    r.figure(R + "report/figs/round3_noise.png", "Landing success on Site04 as altimeter noise grows. The tolerance gate with the noise floor stays near 90% or above while the earlier tolerance gate and the PITFAL-style baseline fall, and trust v2 falls at the highest noise.", 13.5)
    r.table(["Rule", "Statement", "Outcome"],
            [["Q1", "Noise floor beats plain tolerance by at least 10 points at x4, x8 and x16", "Met: +17.0, +33.0, +48.0"],
             ["Q2", "At or above PITFAL-style at x8 and x16; at most 3 below it in cliff + faults", "Met: +29.0, +52.2, and +14.2 in cliff + faults"],
             ["Q3", "At most 3 below trust v2 in cliff + faults; at or above it at x8 (weak test)", "Met: +2.4 and +5.6 (a 2.4-point gap is within noise)"],
             ["Q4", "Terrain variance lifts wait and ML by at least 5 points at nominal noise and at x8", "Met: wait +13.0 and +22.0; ML +14.2 and +8.6"],
             ["Q5", "With the noise-aware label, trust v2 misses fewer than 10% of faults at x8", "Met: 6.6% (52.6% with the old label)"]],
            [1.1, 9.0, 5.9], "Outcome of the pre-registered round-3 decision rules (Site04)", align_num=False)
    r.table(["Judge at x8 noise", "False rejection, old label (%)", "False rejection, noise-aware (%)", "Missed fault, old label (%)", "Missed fault, noise-aware (%)"],
            [["PITFAL-style", "3.9", "20.6", "32.8", "7.8"], ["Tolerance", "5.8", "19.4", "40.9", "8.1"],
             ["Tolerance + noise floor", "0.1", "4.2", "74.5", "9.8"], ["Trust v2", "3.7", "13.7", "52.6", "6.6"]],
            [4.0, 3.0, 3.2, 2.9, 2.9], "Effect of the fault label on the bookkeeping columns at x8 noise (landing success is identical under both labels)", font=9)
    r.para("All five rules were met. The tolerance gate with the noise floor landed 94.6% of runs at x8 noise, against 61.6% for the plain tolerance gate, 65.6% for the PITFAL-style baseline "
           "and 89.0% for trust v2, and 90.8% at x16 where trust v2 reached 57.2%. Giving unflagged readings the terrain variance lifted the wait-and-see and ML judges at nominal noise and at x8. "
           "The corrected label shows that the earlier missed-fault columns overstated misses at high noise (for the noise-floor judge 74.5% under the old label against 9.8% under the noise-aware one) and understated false rejections; "
           "decisions and landing success were never affected.")
    r.para("Not improved: the second-opinion judge stays weak, ML still fails at x4 even with the terrain variance (28.4% against 28.6%), and altimeter dropout stays low for every judge (49.6% for the best). "
           "The noise-floor judge also lets more faults through than trust v2 (9.8% against 6.6% at x8). A wrong map and delayed readings without time stamps were not tested with the new switches.")
    r.h2("Round 4 development study (exploratory)")
    r.para("After round 3 the question was where a noise-following gate can go wrong. Nothing in this section is pre-registered or run on Site04: it uses the tuning worlds, procedural worlds 14 to 16 and Site01, "
           "with 100 descents per cell over nine world and seed combinations. Three new default-off switches were added to the simulator (where the noise floor enters the filter, terrain variance measured where each altimeter beam lands, "
           "and a true-noise oracle that is an upper bound and cannot be flown), and the earlier judges were verified to give identical results.")
    r.para("The three-beam altimeter (assumed geometry, our interpretation of NASA's PITFAL consensus idea) changed the picture. The first table below gives landing success with independent beam faults.")
    r.table(["Rule (three beams)", "Cliff + faults", "x4 noise", "x8 noise", "x16 noise"],
            [["PITFAL-style multi-beam", "92", "96", "98", "69"], ["Tolerance, no floor", "93", "98", "73", "45"],
             ["Floor in gate and update", "85", "78", "91", "99"], ["Floor in update only", "98", "99", "79", "61"],
             ["Floor in update only + footprint terrain", "97", "98", "98", "76"], ["Floor in gate only", "75", "67", "70", "60"],
             ["True-noise oracle (not flyable)", "93", "78", "82", "96"]],
            [6.4, 2.4, 2.4, 2.4, 2.4], "Landing success (%), three-beam altimeter, independent faults, mean of nine development cells (100 descents each)", font=9)
    r.para("No rule wins everywhere. The floor in both places gives the best result at high noise but collapsed on one procedural terrain (world 12: 6% at x4 noise). Our first explanation, that the floor mistakes a wrong map "
           "for sensor noise, was not supported: the true-noise oracle collapses on the same terrain, so the cause is that any gate widened to the right noise size lets harmful readings in there, while a tight gate "
           "happens to act as a terrain-consistency filter. Measuring terrain variance where the beams land rather than under the lander mattered: in the table, the update-only rule gains 19 points at x8 and 15 at x16 from it.")
    r.para("With a single beam the picture was simpler (second table below): the floor in both places came close to the oracle and a 100 m map offset did not make it worse, but a 2 km wrong map defeated every rule, and so did readings delayed without time stamps until round 5 estimated the delay.")
    r.table(["Rule (single beam)", "x4", "x8", "x16", "100 m map offset"],
            [["Tolerance", "69", "45", "39", "56"], ["Floor in gate and update", "93", "87", "82", "65"], ["Floor in update only", "88", "68", "53", "56"],
             ["True-noise oracle (not flyable)", "94", "92", "91", "56"], ["Second-difference noise floor (no map)", "93", "92", "92", "65"],
             ["VB-AKF adaptive noise filter", "89", "79", "71", "61"], ["PITFAL-style", "84", "70", "40", "61"], ["Trust v2", "86", "79", "62", "62"]],
            [6.4, 2.4, 2.4, 2.4, 2.4], "Landing success (%), single-beam altimeter, mean of nine development cells (100 descents each)", font=9)
    r.para("A noise estimate that ignores the map (the spread of second differences of the range readings) matched the floor with ordinary white noise, but with strongly correlated noise it dropped to about 28% against about 50% for the floor, "
           "as theory predicts. It therefore works only when the noise is close to white. The safest candidate was then pre-registered and tested on reserved worlds 17 to 20 (next subsection).")
    r.h3("Round 4 held-out result")
    r.para("The test was frozen at git tag prereg-round4 and run once: worlds 17 to 20, 200 descents per cell, three beams with independent and common-mode faults. Candidate B (floor in the update only, terrain variance at the beam footprint) failed two of the four pre-registered rules. "
           "At x8 noise it was about 5 points below the PITFAL-style rule (74 against 79) and at x16 it was 3 to 6 points below (58 to 60 against 63), so the high-noise gain seen in development did not replicate. "
           "The floor in both places, which we feared would collapse as it did on world 12, did not collapse on these worlds (rule R3 met): it was 3 to 6 points above the PITFAL-style rule at low noise and about 17 points above at x16, but that comparison at high noise was not pre-registered and is exploratory. "
           "With a single beam and a 100 m map offset the floor beat plain tolerance by 12.5 points (68 against 56, rule R4 met).")
    r.table(["Rule (three beams, worlds 17 to 20)", "Cliff + faults", "x4 noise", "x8 noise", "x16 noise"],
            [["PITFAL-style multi-beam", "74", "79", "79", "63"], ["Candidate B (floor in update only)", "78", "81", "74", "60"],
             ["Floor in gate and update (A)", "77", "82", "85", "80"], ["Tolerance, no floor", "80", "78", "60", "38"],
             ["True-noise oracle (not flyable)", "80", "83", "85", "83"]],
            [6.4, 2.4, 2.4, 2.4, 2.4], "Landing success (%), independent faults, mean of worlds 17 to 20 (200 descents each); common-mode faults give the same picture", font=9)
    r.para("Results differ strongly by world: world 19 is near 100% for every rule, while on world 20 the PITFAL-style rule scored only 26 to 37% at low noise against 44 to 78% for the tolerance-based rules. The conclusion for the project is therefore limited: a gate that follows the noise level did well on these four worlds, but the specific safer candidate chosen from nine development cells did not hold up, and this is simulation only.")
    r.h2("Round 5 development comparison (exploratory)")
    r.para("The next step was a build plan that listed techniques for the open problems: faults the gate cannot see, high noise on three beams, delayed readings without time stamps, a wrong map, camera trust and dropout. "
           "Eleven of them were added to the simulator as default-off switches (results of all earlier rules are unchanged bit for bit), together with new fault types (stuck-at, slow drift, scale factor, beam dropout), and compared with the baseline rules on the same nine development cells "
           "(100 descents each, untuned constants). Calibration and training used new worlds 27 to 32 only; the reserved worlds, worlds 17 to 20 and Site04 were not touched. Two items of the plan (a point-mass filter and a learned Kalman gain) were not built.")
    r.table(["Rule (single beam)", "Cliff", "x8 noise", "x16 noise", "Delayed, no stamps", "Dropout", "Stuck-at", "Drift", "2 km map"],
            [["PITFAL-style", "84", "70", "40", "0", "54", "80", "78", "4"], ["Noise floor (round 3)", "92", "87", "82", "4", "70", "90", "94", "17"],
             ["IMM-style noise modes", "97", "93", "94", "5", "74", "92", "97", "9"], ["Student-t weighting + floor", "94", "94", "93", "3", "70", "64", "95", "19"],
             ["CUSUM + floor", "85", "64", "57", "4", "69", "83", "92", "31"], ["Conformal gate limit", "74", "90", "88", "3", "68", "27", "94", "14"],
             ["Delay estimation (no stamps)", "-", "-", "-", "54", "-", "-", "-", "-"], ["Map-offset search", "90", "84", "-", "-", "-", "-", "-", "23"],
             ["Soft camera weighting + floor", "100", "100", "-", "-", "-", "-", "-", "-"]],
            [4.6, 1.2, 1.4, 1.4, 1.9, 1.5, 1.4, 1.2, 1.5], "Landing success (%), single-beam altimeter, mean of nine development cells (100 descents each)", font=8)
    r.para("With one beam, mixing noise levels with a fault mode and weighting every reading by a Student-t rule both beat the noise floor at high noise (about 93 to 94% against 82% at x16). "
           "Estimating the delay of unstamped readings from the data lifted landing from 4% to 54% (true time stamps give 90%), and weighting camera fixes by the error size seen at their matcher confidence instead of a hard cut gave 100% where the hard cut gave 87 to 92%. "
           "Several ideas did not help: a gate limit calibrated to a 1% false-rejection rate let faults in (stuck-at 27%), a CUSUM change detector rejected 38% of valid readings, and a map-offset search found the 2 km offset in only about a third of the descents. "
           "No rule handles the 2 km wrong map (at most 31%). A second altimeter with independent faults raised landing with dropout from 70% to 89%, but that depends on our assumption that it does not drop out.")
    r.table(["Rule (three beams)", "Cliff", "x4", "x8", "x16", "Beam drops out", "2 km map"],
            [["PITFAL-style multi-beam", "92", "96", "98", "69", "94", "4"], ["Noise floor in gate and update", "85", "79", "88", "98", "85", "6"],
             ["Noise floor in update only", "97", "98", "98", "76", "98", "10"], ["Joint three-beam update", "83", "79", "87", "98", "83", "6"],
             ["Learned gate selector", "85", "79", "88", "98", "85", "5"], ["Conformal gate limit", "82", "79", "86", "98", "82", "9"],
             ["Student-t weighting + floor", "99", "92", "96", "99", "91", "6"], ["Solution separation", "83", "79", "87", "98", "83", "6"]],
            [4.8, 1.5, 1.5, 1.5, 1.5, 2.2, 1.7], "Landing success (%), three-beam altimeter, independent faults, mean of nine development cells (100 descents each)", font=8)
    r.para("With three beams, Student-t weighting had the best mean and the best worst case over the noise and fault conditions (94% and 87%, against 93% and 76% for the floor in the update only and 90% and 69% for the PITFAL-style rule), and the lowest estimate-consistency error. "
           "On the terrain that collapses the full noise floor (world 12, x4 noise) it reached 61 to 63% against 7% for the full floor, so it avoids most but not all of the collapse. "
           "The joint update, the learned gate selector and solution separation made no difference: the selector was 99.9% accurate on held-back training worlds, but the noise-floor gate was already right on 99% of the readings where the two gates disagreed, so it behaved like always using the floor; "
           "solution separation never fired once the gate had screened the beams.")
    r.para("These are exploratory results: about ten candidates were compared on nine cells, so the best looking one is optimistic, and every rule is overconfident (NEES far above its ideal value). That test was pre-registered and frozen (git tag prereg-round5) on reserved worlds 41 to 50, with seven rules, and run once.")
    r.h3("Round 5 held-out result")
    r.para("Five of the seven rules were met. Student-t weighting with three beams was within 3 points of the PITFAL-style rule at cliff, x4 and x8 (rule S1) and 19 to 21 points above it at x16 (S2); it did not collapse on any world (lowest world 56%, S4). "
           "Delay estimation lifted landing with unstamped readings from 1.5% to 51% (S5), and with one beam Student-t weighting beat the noise floor at x16 by 9 points (S7). "
           "Two rules failed: Student-t weighting was 2 to 4 points below the full noise floor at low and middle noise (S3), so its development edge did not replicate, and soft camera weighting beat the hard cut by 2.8 points at cliff, just under the 3-point margin (S6), and by 9.3 at x8.")
    r.table(["Rule (three beams, worlds 41 to 50)", "Cliff + faults", "x4 noise", "x8 noise", "x16 noise"],
            [["PITFAL-style multi-beam", "89", "90", "90", "69"], ["Noise floor in gate and update (A)", "92", "94", "92", "88"],
             ["Noise floor in update only (B)", "91", "91", "88", "71"], ["Student-t weighting + floor (S)", "88", "91", "89", "87"]],
            [6.4, 2.4, 2.4, 2.4, 2.4], "Landing success (%), three-beam altimeter, independent faults, mean of ten reserved worlds (200 descents each); common-mode faults give the same picture", font=9)
    r.para("An unplanned observation, labelled exploratory: the full noise floor in both places was the best three-beam rule on these worlds (92, 94, 92 and 88%) and did not collapse on any of them, while the update-only floor lost 17 points at x16. "
           "Worlds 41, 44 and 47 were hard for every rule. A 2 km wrong map still defeated every rule (at most 5%), and delayed readings recovered to 51% against 90% with true time stamps. This is simulation only, on procedural terrain and an assumed three-beam geometry.")
    r.h2("Round 6: 6-DOF lander dynamics (exploratory)")
    r.para("Until round 5 the bench lander obeyed the commanded acceleration at once. A real lander has one engine fixed to its body, so a sideways move needs a tilt, and tilting needs limited reaction-control torque. "
           "A default-off switch (dyn6, results unchanged bit for bit when off, 17 unit tests) replaces the point mass by a rigid body with a quaternion attitude, throttle lag of 0.3 s, a torque-limited attitude controller with a braking-curve rate command and anti-windup, "
           "inertia that follows the mass, thrust misalignment (0.15 degrees) and a centre-of-mass offset (2 cm), a delta-angle gyro (bias 0.005 degrees per second) with a star tracker every 2 s, an accelerometer rotated with the estimated attitude, "
           "body-fixed altimeter beams whose range the filter predicts along the estimated beam direction, and reaction-control propellant. The commanded thrust direction is kept within 35 degrees of vertical, and touchdown also needs a tilt of at most 12 degrees and a body rate of at most 5 degrees per second. "
           "Every vehicle number is assumed. Not modelled: fuel slosh, structural flexing, engine start-up transients, plume effects and landing-gear crush, and the filter's process noise does not include attitude error.")
    r.para("Study: the nine development cells, three noise conditions, 60 descents per cell, never Site04 or the reserved worlds; nothing was pre-registered. Table values are landing success (%).")
    r.table(["Rule", "Single beam x16: point mass", "6-DOF", "Three beams x16: point mass", "6-DOF"],
            [["PITFAL-style", "44", "34", "73", "69"], ["Noise floor (A)", "82", "76", "98", "100"], ["Student-t + floor", "93", "75", "99", "100"]],
            [4.6, 3.2, 1.8, 3.4, 1.8], "Landing success (%), mean of nine development cells (60 descents each), point-mass and default 6-DOF vehicle", font=9)
    r.bullets([
        "**The ranking of the rules holds** with a working attitude loop: with three beams at x16 noise the noise floor and Student-t weighting are about 30 points above the PITFAL-style rule (95% interval 26 to 34; 26 points with the point mass); with one beam the floor is 43 points above (31 to 51).",
        "**The low-noise edge of Student-t weighting disappears** (three beams, cliff: +13.5 points with the point mass, -0.4 with 6-DOF), in line with the round-5 held-out result. With one beam, Student-t weighting is below the floor at x8 and cliff under 6-DOF, the opposite of the point mass.",
        "**Single-beam landing is lower than with the point mass** in 8 of 9 rule and noise cells, by up to 20 points. Three-beam landing is higher at low noise; a possible reason (not tested) is that the old model applied noisy guidance commands instantly and the actuator lag smooths them. This does not mean that 6-DOF is easier.",
        "**Two stressed vehicles failed with every rule.** A sluggish vehicle (torque 150 N m, throttle lag 1 s) landed 3 to 11% of descents (median touchdown tilt 36 degrees, 62% crashes) and a degraded one (misalignment 0.5 degrees, centre of mass 8 cm off, gyro only, bias 0.05 degrees per second) 0 to 0.4% (attitude estimate drifting about 7 degrees, 88% crashes). With this guidance the descent fails before the altimeter rule matters, so these runs say nothing about the rules; a real design would need guidance tuned to the vehicle and an attitude estimator that the filter accounts for."])
    r.para("Limits: simulation only, development worlds only, assumed vehicle numbers, one set of guidance gains, tilt cap and touchdown limits chosen by us. The code (sim/dyn6.py) and results (docs/ROUND6_DYN6_RESULTS.md) are in the repository; the engine now differs from the commit tagged prereg-round5 only by this default-off switch, so the round-5 held-out result is unaffected.")
    r.h2("Discussion")
    r.bullets([
        "**The map in the filter does most of the work.** A plain map-tolerance gate reaches 97% in cliff cases; the distinctive parts of the four-step rule add little there and add brittleness.",
        "**Where learning or adaptivity helps.** A learned or running noise level helps with a noisy altimeter; a classical Kalman chi-square gate beat a learned policy under changed terrain; a non-ML noise-adaptive gate nearly matches the classifier.",
        "**A simple noise-aware gate is enough.** In the final Site04 run, letting the tolerance gate follow the altimeter's current noise level kept landings near 95% at eight times normal noise, with no machine learning; it beat the PITFAL-style baseline (our single-beam reimplementation) and our trust rule at high noise.",
        "**With three beams there is no single winner.** A noise-following gate gives the best high-noise result but collapses on one terrain; keeping the gate tight and letting only the update variance follow the noise is safer but gives up most of the high-noise gain. This is an exploratory finding.",
        "**Round 5.** In development, Student-t weighting, delay estimation and soft camera weighting were the clearest gains; the gate limit calibration, CUSUM, joint update and learned gate selector were not. On ten reserved worlds, delay estimation and the high-noise value of Student-t weighting replicated (five of seven pre-registered rules met), but Student-t weighting did not beat the full noise floor at low noise, which was the best three-beam rule there.",
        "**Round 6.** With a 6-DOF vehicle that has a working attitude loop and star tracker, the high-noise advantage of the noise floor and Student-t weighting over the PITFAL-style rule remained, while single-beam results changed by up to 20 points; vehicles with weak attitude control or sensing failed with every rule (exploratory, development worlds, assumed vehicle).",
        "**Camera and time.** Trust the matcher's own confidence, and time-stamp altimeter readings: both are more important than predicting shadow.",
        "**Claims that did not survive.** Round 1's headline (a shadow-aware camera is the big win) disappeared against a fair camera baseline; the \"shifted map fails\" result was a scoring artefact; "
        "the published ml judge was probably under-reported because of the engine's noise handling.",
        "**What is not shown.** Nothing here proves real-mission performance; the constants were not tuned; the final run is one run on one real site; a wrong map and delayed readings without time stamps are untested with the new switches."])

    # ================= 6 CONCLUSIONS =================
    r.chapter(6, "Conclusions")
    r.h2("Conclusion")
    r.para("The HAKUTO-R failure is real and reproducible in simulation. The main fix is to put the terrain map into the filter and to widen the gate where the map shows the terrain varies; "
           "a plain map-tolerance gate with a confidence-gated camera and time-stamped altimeter readings is about as good as the four-step trust rule in cliff cases. "
           "The trust rule is worth keeping for its noise learning, no-map fallback and divert behaviour, but it needs a physical check that scales with measurement noise and a way to detect a wrong map. "
           "Re-analysis showed that speed violations come from wrong matches, that small map-tie errors are harmless, that a classical Kalman chi-square gate is a strong baseline that a learned "
           "policy did not beat, and that a non-ML noise-adaptive gate nearly matches a trained classifier. The project's most useful output is a reproducible benchmark, with pre-registered decisions, "
           "that shows when terrain corrections help or hurt touchdown and records its own corrections. The pre-registered final round on Site04 confirmed that, for a single-beam altimeter, the best simple fix is to let the gate follow the altimeter's current noise level.")
    r.h2("What we achieved, in plain words")
    r.para("**The problem.** A lander that cannot use GPS has to decide, second by second, which of its sensors to believe. Two real landers were lost because they believed the wrong thing: one threw away a correct height reading at a crater edge, and one trusted noisy readings.")
    r.para("**What we built.** A realistic simulated Moon landing on real NASA terrain near the South Pole, with a fast test bench that can fly thousands of landings, so different ways of deciding can be compared fairly and the results repeated exactly.")
    r.para("**What we found.** The biggest single fix is to let the lander use the map of the ground. After that, the most useful extra is a simple rule that watches how noisy the height sensor currently is and loosens its trust accordingly. In the final test on a crater rim that we never tuned on, this simple rule landed safely about 95% of the time even when the sensor was eight times noisier than normal, where the earlier rule managed about 62%.")
    r.para("**What did not pay off.** Our learned models did not beat these simple rules, and an early claim that a shadow-aware camera is the big win disappeared when we compared it fairly. We corrected two earlier results that had been scored in a misleading way.")
    r.para("**How much to trust it.** All of this is simulation, on one real site, with no real flight data, so it shows which simple ideas work and when, not that a real lander would land safely. What we can stand behind is a method that was decided in advance, tested once on unseen terrain, and recorded together with its limits.")
    r.h2("Limitations")
    r.bullets([
        "Simulation only: one simulator, one renderer and matcher, one unseen real site (Site04), no hardware, no real image-based navigation and no real HAKUTO-R altitude record.",
        "Simple dynamics: the main results use a 3-DOF point mass with ideal attitude; the 6-DOF model of round 6 was run on development worlds only, with assumed vehicle numbers and no slosh, flexing, engine transients or plume; scans are instantaneous, map errors are bump-shaped, and the 12-area study used one lunar tile.",
        "Settings were first explored while looking at Site04 runs; the pre-registration limits but does not erase this (disclosed in the registration).",
        "Trust v2 assumes time-stamped readings and a registered map; the no-map baseline uses a coarse reference rather than a terrain-relative filter.",
        "The final round is one run on one real site; the noise-floor gate lets more faults through than trust v2 (about 10% against about 6%); a wrong map and delayed readings without time stamps were not tested with the new switches.",
        "Round 5 was developed on nine cells with about ten candidates, so its development gains were optimistic, and the held-out test (ten procedural worlds) did not reproduce the edge of Student-t weighting over the full noise floor; the second altimeter, the camera-weighting error curve, the map-offset search and the single-fault solution separation are first, simple versions; two planned techniques were not built.",
        "The three-beam geometry and the consensus rule are assumptions; the round-4 findings are exploratory, from nine development cells at 100 descents each, and the held-out test of the chosen candidate failed two of its four rules (four worlds only, simulation only).",
        "Differences of a few points per cell are within noise; the noise-adaptive gate constants (6.635, 9 m^2, 0.5 terrain weight) were not tuned; literature novelty is unchecked behind paywalls."])
    r.h2("Future scope")
    r.bullets([
        "Review whether the three round-3 switches (noise floor, terrain variance, noise-aware label) should become the defaults, and re-report the earlier false-rejection and missed-fault columns with the corrected label.",
        "Make the physical check scale with the noise level and add wrong-map detection; add a terrain-relative no-map baseline.",
        "Pre-register the full noise floor in both places against Student-t weighting and the PITFAL-style rule on fresh worlds, repeat on a second real site, and find a method for the 2 km wrong map that works; test the noise-floor gate against delayed readings without time stamps and realistic map-error fields.",
        "Run at least 30 terrain areas with realistic random map-error fields, a more realistic lander (IMU drift, attitude effects, scan delay), and fair comparisons with a full-covariance Kalman filter and a grid or particle filter.",
        "Tune guidance to the vehicle and add attitude error to the navigation filter, then rerun the poor-vehicle cases of round 6; compare the dynamics with published Morpheus and ALHAT numbers; raw descent telemetry of recent landers is not public, so real-data replay needs outreach.",
        "Repeat the camera survey on Site01 and with a second matcher; obtain the HAKUTO-R altitude record for a real-data replay; complete the literature check through the college library."])

    # ================= REFERENCES =================
    r.chapter(0, "References")
    r.reference_list()

    # ================= PLAGIARISM =================
    r.chapter(0, "Plagiarism Check Report")
    r.para("The plagiarism check report (similarity below 10%) is to be attached here after the final draft is checked.", align="left")
