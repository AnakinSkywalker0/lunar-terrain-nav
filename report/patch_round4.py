"""One-off patch: add the round-4 development study (exploratory) to content.py (already applied if the marker is present)."""
p = "content.py"
s = open(p, encoding="utf-8").read()
if "Round 4 development study" in s:
    raise SystemExit("already applied")


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


rep("The gain needs no machine learning. All results are simulation only.",
    "The gain needs no machine learning. A follow-up development study with a three-beam altimeter found that no single rule wins everywhere: letting the gate follow the noise "
    "level helps most at high noise but collapses on one terrain, which led to a second pre-registration that is ready but not yet run. All results are simulation only.")
rep("The work proceeded in seven stages.", "The work proceeded in eight stages.")
rep('"Three default-off engine switches (noise floor, terrain variance, noise-aware label); screened on tuning worlds, confirmed on fresh worlds, pre-registered, frozen at tag prereg-round3 and run once on Site04"]],',
    '"Three default-off engine switches (noise floor, terrain variance, noise-aware label); screened on tuning worlds, confirmed on fresh worlds, pre-registered, frozen at tag prereg-round3 and run once on Site04"],\n'
    '             ["Round 4 (development)", "20 Nov", "Three-beam altimeter, where the noise floor enters, correlated noise, map offsets; exploratory only. A held-out test on reserved worlds 17 to 20 is pre-registered in draft and not yet frozen or run"]],')

RES4 = '''    r.h2("Round 4 development study (exploratory)")
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
    r.para("With a single beam the picture was simpler (second table below): the floor in both places came close to the oracle and a 100 m map offset did not make it worse, but a 2 km wrong map defeated every rule and readings delayed without time stamps defeated every rule.")
    r.table(["Rule (single beam)", "x4", "x8", "x16", "100 m map offset"],
            [["Tolerance", "69", "45", "39", "56"], ["Floor in gate and update", "93", "87", "82", "65"], ["Floor in update only", "88", "68", "53", "56"],
             ["True-noise oracle (not flyable)", "94", "92", "91", "56"], ["Second-difference noise floor (no map)", "93", "92", "92", "65"],
             ["VB-AKF adaptive noise filter", "89", "79", "71", "61"], ["PITFAL-style", "84", "70", "40", "61"], ["Trust v2", "86", "79", "62", "62"]],
            [6.4, 2.4, 2.4, 2.4, 2.4], "Landing success (%), single-beam altimeter, mean of nine development cells (100 descents each)", font=9)
    r.para("A noise estimate that ignores the map (the spread of second differences of the range readings) matched the floor with ordinary white noise, but with strongly correlated noise it dropped to about 28% against about 50% for the floor, "
           "as theory predicts. It therefore works only when the noise is close to white. A pre-registration for a held-out test of the safest candidate on reserved worlds 17 to 20 is drafted, with four rules, one of which is expected to fail; it has not been frozen or run.")
'''
rep('    r.h2("Discussion")', RES4 + '    r.h2("Discussion")')
rep('        "**Camera and time.**',
    '        "**With three beams there is no single winner.** A noise-following gate gives the best high-noise result but collapses on one terrain; keeping the gate tight and letting only the update variance follow the noise is safer but gives up most of the high-noise gain. This is an exploratory finding.",\n        "**Camera and time.**')
rep('        "Differences of a few points per cell are within noise;',
    '        "The three-beam geometry and the consensus rule are assumptions; the round-4 findings are exploratory, from nine development cells at 100 descents each, and the held-out test for them has not been run.",\n        "Differences of a few points per cell are within noise;')
rep('        "Test the noise-floor gate against a wrong or shifted map and against delayed readings without time stamps, then pre-register a round 4 on a second real site.",\n',
    '        "Freeze and run the drafted round-4 test on reserved worlds 17 to 20, then repeat on a second real site; test the noise-floor gate against delayed readings without time stamps and realistic map-error fields.",\n')
open(p, "w", encoding="utf-8").write(s)
print("patched")
