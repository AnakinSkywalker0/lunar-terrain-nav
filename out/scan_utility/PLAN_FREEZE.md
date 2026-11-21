# Frozen scope before v2 fitting

The deterministic plan placed one additional eligible 2.4 km crop without
overlapping the eight previous crops: utility_fresh01 at tile coordinates
(5640.625,1406.25)m. Its target-neighbourhood maximum slope is4.26 degrees.
The protocol explicitly permits scaling to the number that can be placed.

Final evaluation therefore contains270 descents:54 paired configurations with
five arms, one area,500/1500m starts, three conditions, three new error vectors
and three noise seeds. This is a protected but narrow evaluation within Site04.

Development collection remains3840 stationary poses /7680 proposals across five
older areas, with three areas for fitting and two for validation. Complete
development policy selection remains672 descents. No previous final-evaluation
scan rows enter fitting or policy selection. The earlier failure motivates this
new protocol; it is not erased or relabelled as a training result.

The exact draws, coordinates and input/protocol hashes are saved in plan.json
within each run. The plan was generated before collecting or fitting v2.
