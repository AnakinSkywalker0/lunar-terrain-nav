p = r"D:\newprj\handoff\make_handoff.py"
s = open(p, encoding="utf-8").read()
if "6c. Round-5" in s:
    raise SystemExit("already applied")


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new)


rep('h1("7. What we are aiming for")',
    '''h1("6c. Round-5 development comparison (exploratory, 21 Nov 2026)")
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

h1("7. What we are aiming for")''')
rep("A multi-beam altimeter extension and a round-4 development study were done today (exploratory).",
    "A multi-beam altimeter extension, a round-4 development study and a round-5 comparison of eleven build-plan techniques (exploratory; Student-t weighting, delay estimation and soft camera weighting look best, nothing confirmed on held-out data) were done.")
rep("Decide whether to pre-register the floor in both places (A) on fresh worlds (the round-4 held-out set is now used and cannot be reused). Then consider",
    "Decide whether to pre-register Student-t weighting, delay estimation and soft camera weighting against the floor rules and PITFAL-style on fresh worlds 41-50 and a new real site (the round-4 held-out set is used). Then consider")
rep("(47 pages, 11 figures, 21 tables, 29 references)", "(50 pages, 11 figures, 24 tables, 29 references)")
open(p, "w", encoding="utf-8").write(s)
print("ok")
