"""One-off patch: round-5 held-out result into content.py."""
p = "content.py"
s = open(p, encoding="utf-8").read()
if "Round 5 held-out result" in s:
    raise SystemExit("already applied")


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


rep("none of this is confirmed on held-out data. All results are simulation only.",
    "the pre-registered test of the best candidates on ten reserved worlds met five of seven rules: Student-t weighting matched the PITFAL-style rule at low noise and beat it by about 20 points at high noise, delay estimation recovered unstamped readings (1.5% to 51%), "
    "but its development edge over the full noise floor at low noise did not replicate. All results are simulation only.")
rep('"Eleven techniques from a build plan added as default-off switches and compared on the nine development cells with new fault types; exploratory only, nothing run on held-out worlds"',
    '"Eleven techniques from a build plan added as default-off switches and compared on the nine development cells with new fault types (exploratory); the best candidates were then frozen (tag prereg-round5) and run once on reserved worlds 41 to 50: five of seven rules met"')
rep("That test has been pre-registered and frozen (git tag prereg-round5) on reserved worlds 41 to 50, with seven rules; it was started on 21 November and its result is not yet in this draft.\")",
    """That test was pre-registered and frozen (git tag prereg-round5) on reserved worlds 41 to 50, with seven rules, and run once.")
    r.h3("Round 5 held-out result")
    r.para("Five of the seven rules were met. Student-t weighting with three beams was within 3 points of the PITFAL-style rule at cliff, x4 and x8 (rule S1) and 19 to 21 points above it at x16 (S2); it did not collapse on any world (lowest world 56%, S4). "
           "Delay estimation lifted landing with unstamped readings from 1.5% to 51% (S5), and with one beam Student-t weighting beat the noise floor at x16 by 9 points (S7). "
           "Two rules failed: Student-t weighting was 2 to 4 points below the full noise floor at low and middle noise (S3), so its development edge did not replicate, and soft camera weighting beat the hard cut by 2.8 points at cliff, just under the 3-point margin (S6), and by 9.3 at x8.")
    r.table(["Rule (three beams, worlds 41 to 50)", "Cliff + faults", "x4 noise", "x8 noise", "x16 noise"],
            [["PITFAL-style multi-beam", "89", "90", "90", "69"], ["Noise floor in gate and update (A)", "92", "94", "92", "88"],
             ["Noise floor in update only (B)", "91", "91", "88", "71"], ["Student-t weighting + floor (S)", "88", "91", "89", "87"]],
            [6.4, 2.4, 2.4, 2.4, 2.4], "Landing success (%), three-beam altimeter, independent faults, mean of ten reserved worlds (200 descents each); common-mode faults give the same picture", font=9)
    r.para("An unplanned observation, labelled exploratory: the full noise floor in both places was the best three-beam rule on these worlds (92, 94, 92 and 88%) and did not collapse on any of them, while the update-only floor lost 17 points at x16. "
           "Worlds 41, 44 and 47 were hard for every rule. A 2 km wrong map still defeated every rule (at most 5%), and delayed readings recovered to 51% against 90% with true time stamps. This is simulation only, on procedural terrain and an assumed three-beam geometry.")""")
rep("Round 5 was compared on development cells only, with about ten candidates on nine cells, so its best results are optimistic;",
    "Round 5 was developed on nine cells with about ten candidates, so its development gains were optimistic, and the held-out test (ten procedural worlds) did not reproduce the edge of Student-t weighting over the full noise floor;")
rep('"**Round 5 (exploratory).** Weighting every reading by a Student-t rule, estimating the delay of unstamped readings and weighting camera fixes by the matcher\'s confidence curve were the clearest gains in development; the gate limit calibration, CUSUM, joint update and learned gate selector were not.",',
    '"**Round 5.** In development, Student-t weighting, delay estimation and soft camera weighting were the clearest gains; the gate limit calibration, CUSUM, joint update and learned gate selector were not. On ten reserved worlds, delay estimation and the high-noise value of Student-t weighting replicated (five of seven pre-registered rules met), but Student-t weighting did not beat the full noise floor at low noise, which was the best three-beam rule there.",')
rep("Report the frozen round-5 test (Student-t weighting, delay estimation, soft camera weighting on worlds 41 to 50), repeat it on a second real site, and find a method for the 2 km wrong map that works;",
    "Pre-register the full noise floor in both places against Student-t weighting and the PITFAL-style rule on fresh worlds, repeat on a second real site, and find a method for the 2 km wrong map that works;")
open(p, "w", encoding="utf-8").write(s)
print("patched")
