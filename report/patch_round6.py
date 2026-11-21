"""One-off patch: round-6 (6-DOF dynamics) into content.py."""
p = "content.py"
s = open(p, encoding="utf-8").read()
if "Round 6: 6-DOF" in s:
    raise SystemExit("already applied")


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


# abstract
rep("but its development edge over the full noise floor at low noise did not replicate. All results are simulation only.\")",
    "but its development edge over the full noise floor at low noise did not replicate. "
    "A last, exploratory study replaced the point-mass lander by a six-degree-of-freedom model (one body-fixed engine, limited attitude torque, gyro and star-tracker attitude estimate, body-fixed beams): "
    "with a working attitude loop the ranking of the rules held, but vehicles with a slow attitude loop or poor attitude sensing failed with every rule. All vehicle numbers are assumed. All results are simulation only.\")")

# stages table
rep('five of seven rules met"]],\n            [3.6, 2.4, 10.0], "Stages of the project"',
    'five of seven rules met"],\n'
    '             ["Round 6 (6-DOF dynamics)", "21 Nov", "Rigid-body lander with one body-fixed engine, torque-limited attitude control, gyro and star-tracker attitude estimate and body-fixed altimeter beams, as a default-off switch; development worlds only (exploratory, not pre-registered)"]],\n'
    '            [3.6, 2.4, 10.0], "Stages of the project"')

# bench description
rep("fuel. Guidance flies a speed profile",
    "fuel (a six-degree-of-freedom option is described under round 6 in the Results chapter). Guidance flies a speed profile")

# results section
rep('    r.h2("Discussion")\n',
    '''    r.h2("Round 6: 6-DOF lander dynamics (exploratory)")
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
''')

# discussion bullet
rep('which was the best three-beam rule there.",\n',
    'which was the best three-beam rule there.",\n'
    '        "**Round 6.** With a 6-DOF vehicle that has a working attitude loop and star tracker, the high-noise advantage of the noise floor and Student-t weighting over the PITFAL-style rule remained, while single-beam results changed by up to 20 points; vehicles with weak attitude control or sensing failed with every rule (exploratory, development worlds, assumed vehicle).",\n')

# limitations
rep('"Simple dynamics: 3-DOF point mass, ideal attitude, instantaneous scans, bump-shaped map errors, one lunar tile for the 12-area study.",',
    '"Simple dynamics: the main results use a 3-DOF point mass with ideal attitude; the 6-DOF model of round 6 was run on development worlds only, with assumed vehicle numbers and no slosh, flexing, engine transients or plume; scans are instantaneous, map errors are bump-shaped, and the 12-area study used one lunar tile.",')

# future scope
rep('"Repeat the camera survey on Site01',
    '"Tune guidance to the vehicle and add attitude error to the navigation filter, then rerun the poor-vehicle cases of round 6; compare the dynamics with published Morpheus and ALHAT numbers; raw descent telemetry of recent landers is not public, so real-data replay needs outreach.",\n        "Repeat the camera survey on Site01')

open(p, "w", encoding="utf-8").write(s)
print("patched")
