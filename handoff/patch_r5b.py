p = r"D:\newprj\handoff\make_handoff.py"
s = open(p, encoding="utf-8").read()
if "6d. Round-5 held-out" in s:
    raise SystemExit("already applied")


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new)


rep('h1("7. What we are aiming for")',
    '''h1("6d. Round-5 held-out result (21 Nov 2026, run once, frozen commit f742d08, tag prereg-round5)")
p("Worlds 41-50 (procedural, never used before), seed 20261221, 200 descents per cell, three beams (assumed geometry) with independent and common-mode faults plus single-beam rules; docs/PREREG_ROUND5.md, docs/ROUND5_RESULTS.md, out/round5/heldout.csv. <b>Five of seven rules met.</b>")
tbl([["Rule", "Verdict", "Values"],
     ["S1 Student-t within 3 points of PITFAL-style multi-beam at cliff, x4, x8", "MET", "-1.3 to +4.5"],
     ["S2 Student-t at least 3 above it at x16", "MET", "+18.8 / +20.7"],
     ["S3 Student-t at least 3 above the full floor at cliff, x4, x8", "NOT met", "-1.8 to -4.3 (slightly below)"],
     ["S4 Student-t at least 50% in every world at cliff, x4", "MET", "lowest world 56%"],
     ["S5 Delay estimation +20 points with no time stamps", "MET", "+49.3 (51% vs 1.5%)"],
     ["S6 Soft camera +3 points at cliff and x8", "NOT met", "cliff +2.8 (just short), x8 +9.3"],
     ["S7 One-beam Student-t +3 at x16", "MET", "+8.8"]],
    [8.0, 1.8, 6.0])
tbl([["Three beams, independent faults, success %", "Cliff", "x4", "x8", "x16"],
     ["PITFAL-style multi-beam", "89", "90", "90", "69"], ["Floor in gate and update (A)", "92", "94", "92", "88"],
     ["Floor in update only (B)", "91", "91", "88", "71"], ["Student-t + floor (S)", "88", "91", "89", "87"]],
    [7.0, 2.0, 2.0, 2.0, 2.0])
bl(["The development edge of Student-t over the full floor at low noise did not replicate; unplanned (exploratory) observation: the full floor in both places was the best three-beam rule here and did not collapse on any world; worlds 41, 44, 47 are hard for every rule.",
    "Still open: 2 km wrong map (at most 5%), unstamped delays (51% with estimation vs 90% with true stamps), stuck-at faults for Student-t (development finding), overconfident estimates. Not tested: new real site, real sensor data.",
    "Worlds 41-50 are now used; any further confirmatory test needs fresh worlds and a new pre-registration."])

h1("7. What we are aiming for")''')
rep("(exploratory; Student-t weighting, delay estimation and soft camera weighting look best, nothing confirmed on held-out data) were done.",
    "(exploratory) were done; the best candidates were then frozen (tag prereg-round5) and run once on worlds 41-50: five of seven rules met (Student-t and delay estimation replicated; Student-t did not beat the full floor at low noise).")
rep("Decide whether to pre-register Student-t weighting, delay estimation and soft camera weighting against the floor rules and PITFAL-style on fresh worlds 41-50 and a new real site (the round-4 held-out set is used). Then consider",
    "Decide whether to pre-register the full floor in both places against Student-t weighting and PITFAL-style on fresh worlds and a new real site (worlds 17-20, 41-50 and Site04 are used). Then consider")
rep("(50 pages, 11 figures, 24 tables, 29 references)", "(52 pages, 11 figures, 25 tables, 29 references)")
rep("Committed locally on main:", "The round-5 freeze is committed locally too (f742d08, tag prereg-round5). Committed locally on main:")
open(p, "w", encoding="utf-8").write(s)
print("ok")
