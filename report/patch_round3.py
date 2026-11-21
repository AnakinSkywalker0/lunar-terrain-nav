"""One-off patch: add the round-3 result and a plain-language summary to content.py (already applied if the marker is present)."""
p = "content.py"
s = open(p, encoding="utf-8").read()
if "Round-3 protocol (pre-registered)" in s:
    raise SystemExit("already applied")


def rep(old, new):
    global s
    assert old in s, old[:80]
    s = s.replace(old, new, 1)


# Abstract
rep('"a classifier\'s value lies mainly in a noise-aware structure that a non-ML rule gate nearly matches. All results are simulation only.")',
    '"a classifier\'s value lies mainly in a noise-aware structure that a non-ML rule gate nearly matches.")\n'
    '    r.para("The final round, pre-registered and run once on Site04, tested three small engine changes found in that work. Letting the tolerance gate follow "\n'
    '           "the altimeter\'s current noise level raised landing success at eight times normal noise from 62% to 95%, against 66% for the NASA-style baseline and "\n'
    '           "89% for our trust rule; all five pre-registered rules were met. The gain needs no machine learning. All results are simulation only.")')
# Overview bullet
rep('"**A complete record** of what was done, including corrections to earlier claims."])',
    '"**A pre-registered final round (round 3)** run once on Site04, showing that a simple noise-aware gate keeps landings safe under a noisy altimeter.",\n'
    '        "**A complete record** of what was done, including corrections to earlier claims."])')
# Stages table
rep("The work proceeded in six stages.", "The work proceeded in seven stages.")
rep('reproduced 19-20 Nov"]],',
    'reproduced 19-20 Nov"],\n             ["Round 3", "20 Nov", "Three default-off engine switches (noise floor, terrain variance, noise-aware label); screened on tuning worlds, confirmed on fresh worlds, pre-registered, frozen at tag prereg-round3 and run once on Site04"]],')

# Methodology section
METHOD = '''    r.h2("Round-3 protocol (pre-registered)")
    r.para("Round 3 tested three changes to the simulator's judges, each added as a switch that is off by default so every earlier result stays reproducible. "
           "(1) *Noise floor:* the tolerance judge never trusts a reading more than the running size of its recent surprises (trust v2's innovation estimate), in both its gate and its measurement variance. "
           "(2) *Terrain variance:* the wait-and-see, second-opinion and ML judges give readings that pass the gate the same terrain and map variance the tolerance and trust judges already use. "
           "(3) *Noise-aware label:* the ground-truth fault label compares the error with the true noise level (nominal sigma times the scenario's multiplier) instead of the nominal sigma; this changes only the false-rejection and missed-fault bookkeeping, never a decision.")
    r.para("The changes were screened on the tuning worlds, then checked on three fresh procedural worlds (14 to 16, never used for training or tuning) against rules written before that run. "
           "The Site04 test was then frozen: the engine, runner, tests and the pre-registration were committed and tagged prereg-round3, the runner refuses to start unless that tag is the current commit "
           "and the code is unchanged, and it refuses a second run. Settings: 500 runs per cell, seed 20261201, the confidence-gated camera for every judge, time stamps for every judge in the delayed condition, "
           "and untuned constants. Five decision rules were fixed in advance (Q1 to Q5, stated with the results in Section 5.9).")
'''
rep('    r.h2("Tools and environment")', METHOD + '    r.h2("Tools and environment")')

# Results section
RES = '''    r.h2("Round 3 on the held-out site (Site04)")
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
            [3.3, 1.4, 1.5, 1.7, 1.9, 1.3, 1.9, 1.2, 1.7],
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
'''
rep('    r.h2("Discussion")', RES + '    r.h2("Discussion")')

# Discussion bullets
rep('        "**Camera and time.**',
    '        "**A simple noise-aware gate is enough.** In the final Site04 run, letting the tolerance gate follow the altimeter\'s current noise level kept landings near 95% at eight times normal noise, with no machine learning; it beat the NASA-style baseline and our trust rule at high noise.",\n        "**Camera and time.**')
rep('"**What is not shown.** Nothing here proves real-mission performance, and the noise-adaptive gate constants were not tuned."]',
    '"**What is not shown.** Nothing here proves real-mission performance; the constants were not tuned; the final run is one run on one real site; a wrong map and delayed readings without time stamps are untested with the new switches."]')

# Conclusions
PLAIN = '''    r.h2("What we achieved, in plain words")
    r.para("**The problem.** A lander that cannot use GPS has to decide, second by second, which of its sensors to believe. Two real landers were lost because they believed the wrong thing: one threw away a correct height reading at a crater edge, and one trusted noisy readings.")
    r.para("**What we built.** A realistic simulated Moon landing on real NASA terrain near the South Pole, with a fast test bench that can fly thousands of landings, so different ways of deciding can be compared fairly and the results repeated exactly.")
    r.para("**What we found.** The biggest single fix is to let the lander use the map of the ground. After that, the most useful extra is a simple rule that watches how noisy the height sensor currently is and loosens its trust accordingly. In the final test on a crater rim that we never tuned on, this simple rule landed safely about 95% of the time even when the sensor was eight times noisier than normal, where the earlier rule managed about 62%.")
    r.para("**What did not pay off.** Our learned models did not beat these simple rules, and an early claim that a shadow-aware camera is the big win disappeared when we compared it fairly. We corrected two earlier results that had been scored in a misleading way.")
    r.para("**How much to trust it.** All of this is simulation, on one real site, with no real flight data, so it shows which simple ideas work and when, not that a real lander would land safely. What we can stand behind is a method that was decided in advance, tested once on unseen terrain, and recorded together with its limits.")
'''
rep('that shows when terrain corrections help or hurt touchdown and records its own corrections.")\n    r.h2("Limitations")',
    'that shows when terrain corrections help or hurt touchdown and records its own corrections. The pre-registered final round on Site04 confirmed that the best simple fix is to let the gate follow the altimeter\'s current noise level.")\n'
    + PLAIN + '    r.h2("Limitations")')
rep('        "Differences of a few points per cell are within noise;',
    '        "The final round is one run on one real site; the noise-floor gate lets more faults through than trust v2 (about 10% against about 6%); a wrong map and delayed readings without time stamps were not tested with the new switches.",\n        "Differences of a few points per cell are within noise;')
rep('        "Fix the simulator\'s own fault label so it compares with the actual noise level, then re-report false-rejection and missed-fault columns.",\n        "Adopt in the existing judges the two engine findings: terrain and map variance on unflagged readings, and a running innovation-size noise floor in the tolerance gate.",\n',
    '        "Review whether the three round-3 switches (noise floor, terrain variance, noise-aware label) should become the defaults, and re-report the earlier false-rejection and missed-fault columns with the corrected label.",\n')
rep('        "Write a round-3 pre-registration, tune the rule-gate constants once, freeze and tag, and run Site04 once.",\n',
    '        "Test the noise-floor gate against a wrong or shifted map and against delayed readings without time stamps, then pre-register a round 4 on a second real site.",\n')
open(p, "w", encoding="utf-8").write(s)
print("patched")
