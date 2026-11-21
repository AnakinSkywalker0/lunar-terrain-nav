"""One-off patch: round-4 held-out results into content.py."""
p = "content.py"
s = open(p, encoding="utf-8").read()
if "Round 4 held-out result" in s:
    raise SystemExit("already applied")
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new)
rep("which led to a second pre-registration that is ready but not yet run.",
    "which led to a second pre-registration, run once on four reserved worlds: the pre-registered candidate failed two of its four rules, so the development gain did not replicate.")
rep("A held-out test on reserved worlds 17 to 20 is pre-registered in draft and not yet frozen or run",
    "Its held-out test on reserved worlds 17 to 20 was frozen (tag prereg-round4) and run once on 20 Nov; two of four rules failed")
rep("A pre-registration for a held-out test of the safest candidate on reserved worlds 17 to 20 is drafted, with four rules, one of which is expected to fail; it has not been frozen or run.\")",
    """The safest candidate was then pre-registered and tested on reserved worlds 17 to 20 (next subsection).")
    r.h3("Round 4 held-out result") if hasattr(r, "h3") else r.para("Round 4 held-out result.")
    r.para("The test was frozen at git tag prereg-round4 and run once: worlds 17 to 20, 200 descents per cell, three beams with independent and common-mode faults. Candidate B (floor in the update only, terrain variance at the beam footprint) failed two of the four pre-registered rules. "
           "At x8 noise it was about 5 points below the PITFAL-style rule (74 against 79) and at x16 it was 3 to 6 points below (58 to 60 against 63), so the high-noise gain seen in development did not replicate. "
           "The floor in both places, which we feared would collapse as it did on world 12, did not collapse on these worlds (rule R3 met): it was 3 to 6 points above the PITFAL-style rule at low noise and about 17 points above at x16, but that comparison at high noise was not pre-registered and is exploratory. "
           "With a single beam and a 100 m map offset the floor beat plain tolerance by 12.5 points (68 against 56, rule R4 met).")
    r.table(["Rule (three beams, worlds 17 to 20)", "Cliff + faults", "x4 noise", "x8 noise", "x16 noise"],
            [["PITFAL-style multi-beam", "74", "79", "79", "63"], ["Candidate B (floor in update only)", "78", "81", "74", "60"],
             ["Floor in gate and update (A)", "77", "82", "85", "80"], ["Tolerance, no floor", "80", "78", "60", "38"],
             ["True-noise oracle (not flyable)", "80", "83", "85", "83"]],
            [6.4, 2.4, 2.4, 2.4, 2.4], "Landing success (%), independent faults, mean of worlds 17 to 20 (200 descents each); common-mode faults give the same picture", font=9)
    r.para("Results differ strongly by world: world 19 is near 100% for every rule, while on world 20 the PITFAL-style rule scored only 26 to 37% at low noise against 44 to 78% for the tolerance-based rules. The conclusion for the project is therefore limited: a gate that follows the noise level did well on these four worlds, but the specific safer candidate chosen from nine development cells did not hold up, and this is simulation only.")""")
rep("and the held-out test for them has not been run.", "and the held-out test of the chosen candidate failed two of its four rules (four worlds only, simulation only).")
rep("Freeze and run the drafted round-4 test on reserved worlds 17 to 20, then repeat on a second real site;",
    "Pre-register the floor in both places (which held up on worlds 17 to 20 but was not the pre-registered candidate) for a fresh set of worlds, then repeat on a second real site;")
open(p, "w", encoding="utf-8").write(s)
print("patched")
