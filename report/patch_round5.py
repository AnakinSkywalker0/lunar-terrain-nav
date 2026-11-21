"""One-off patch: round-5 development comparison (exploratory) and wording fixes into content.py (already applied if the marker is present)."""
p = "content.py"
s = open(p, encoding="utf-8").read()
if "Round 5 development comparison" in s:
    raise SystemExit("already applied")


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


rep("All results are simulation only.\")",
    "A third, exploratory round tried the techniques of a build plan on the development worlds: Student-t weighting of readings, mixing of noise modes, delay estimation without time stamps and soft camera weighting helped in some cases, "
    "several others did not, and no rule solves a 2 km wrong map; none of this is confirmed on held-out data. All results are simulation only.\")")
rep("The work proceeded in eight stages.", "The work proceeded in nine stages.")
rep('two of four rules failed"]],',
    'two of four rules failed"],\n'
    '             ["Round 5 (development)", "21 Nov", "Eleven techniques from a build plan added as default-off switches and compared on the nine development cells with new fault types; exploratory only, nothing run on held-out worlds"]],')

RES5 = '''    r.h2("Round 5 development comparison (exploratory)")
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
    r.para("These are exploratory results: about ten candidates were compared on nine cells, so the best looking one is optimistic, and every rule is overconfident (NEES far above its ideal value). The natural next step is a pre-registered test of Student-t weighting against the floor rules and the PITFAL-style rule on fresh worlds and a new real site.")
'''
rep('    r.h2("Discussion")', RES5 + '    r.h2("Discussion")')
rep('        "The three-beam geometry and the consensus rule are assumptions;',
    '        "Round 5 was compared on development cells only, with about ten candidates on nine cells, so its best results are optimistic; the second altimeter, the camera-weighting error curve, the map-offset search and the single-fault solution separation are first, simple versions; two planned techniques were not built.",\n        "The three-beam geometry and the consensus rule are assumptions;')
rep('        "Pre-register the floor in both places (which held up on worlds 17 to 20 but was not the pre-registered candidate) for a fresh set of worlds, then repeat on a second real site;',
    '        "Pre-register Student-t weighting, delay estimation and soft camera weighting against the floor rules and the PITFAL-style rule for fresh worlds and a second real site, and find a method for the 2 km wrong map that works;')
rep('        "**Camera and time.**',
    '        "**Round 5 (exploratory).** Weighting every reading by a Student-t rule, estimating the delay of unstamped readings and weighting camera fixes by the matcher\'s confidence curve were the clearest gains in development; the gate limit calibration, CUSUM, joint update and learned gate selector were not.",\n        "**Camera and time.**')

# wording fixes found in the plan's claim check
rep("Python (rasterio, numpy); Unity Terrain", "Python (Pillow, numpy); Unity Terrain")
rep("resamples terrain to 10 m", "subsamples terrain to 10 m (every second pixel)")
rep('"Done in Unity (LUMEN) and in the bench"', '"Done in Unity (LUMEN); the bench uses a simplified scan-fix model (true position, map shift and Gaussian noise; no matching is simulated)"')
rep("and the LOLA height error from the PGDA total-error map.", "and the LOLA height error (the tile's mean PGDA total error for Site01, a default 3 m for Site04; no per-pixel error is used).")
rep("against 66% for the NASA-style baseline and ", "against 66% for the PITFAL-style baseline (our single-beam reimplementation, not NASA's system) and ")
rep("it beat the NASA-style baseline and our trust rule at high noise.", "it beat the PITFAL-style baseline (our single-beam reimplementation) and our trust rule at high noise.")
rep("Delayed readings without time stamps and a 2 km wrong map defeated every rule.", "On the development worlds, delayed readings without time stamps and a 2 km wrong map defeated every rule in round 3 (round 5 later fixed the delay case).")
rep("confirmed that the best simple fix is to let the gate follow the altimeter's current noise level.", "confirmed that, for a single-beam altimeter, the best simple fix is to let the gate follow the altimeter's current noise level.")
rep("but a 2 km wrong map defeated every rule and readings delayed without time stamps defeated every rule.", "but a 2 km wrong map defeated every rule, and so did readings delayed without time stamps until round 5 estimated the delay.")
open(p, "w", encoding="utf-8").write(s)
print("patched")
