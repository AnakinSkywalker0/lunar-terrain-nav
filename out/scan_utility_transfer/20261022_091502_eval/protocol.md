# Frozen scan-utility transfer test: Site01

22 October 2026. Written before this transfer evaluation or smoke outcomes.
Question: does the existing Site04-trained utility policy retain its benefit
on another lunar DEM, without retraining or policy selection on that DEM?

## Scope and prior exposure

Use the existing NASA PGDA Site01 elevation GeoTIFF. Site01 was used in older,
separate Python sensor-trust studies; it is not globally unseen project data.
It was not used to fit or select the current scan-utility v2 model. This tests
transfer of that frozen model to another terrain tile, not independent missions.
The same simulator, synthetic sensor model and ideal 3-DOF response are retained.

Freeze the current v2 model, hybrid policy, geometric core, prior learned veto
and classical bounded rule. No fitting, threshold selection or control changes.
The existing v2 Site04 final outcomes have already been seen. This new protocol
does not retroactively make those results prospective.

## Terrain preparation and selection

Validate finite source heights and 5 m pixel scale. Follow the existing pipeline:
bilinear resize to 2049 by 2049, normalize to unsigned 16-bit heights, flip north
to south for Unity, and retain the source extent and elevation range. Record
source and derived hashes and GeoTIFF scale/tiepoint for reproducibility.

Select four nonoverlapping 2.4 km square crops using terrain geometry only.
Candidate target centres must be at least 1400 m from tile edges and have a
maximum slope below 5 degrees in a 7 by 7 sample window. Select the first centre
nearest the tile centre, then farthest-first by minimum squared distance, with
row-major tie breaking and square nonoverlap (at least 2400 m on one axis).
Reserve the first crop for a 15-case infrastructure smoke test; the remaining
three are final evaluation crops. Fail planning if four cannot be placed.
Do not choose centres using matcher or landing performance.

## Paired matrix and outcomes

Use exactly the previous final evaluation's conditions and error families so
terrain transfer is the principal changed factor: altitudes 500/1500 m; aligned
map, raised relief and shifted map; position error angles 23/157/281 degrees
with magnitudes 35/70/95 m; noise seeds 717/818/919. Initial true horizontal
offset (-12,+16) m; vertical speed -10 m/s. Raised relief centre (-75,-80) m,
sigma 65 m, amplitude 16 m; map translation (+22,-31) m.

Five arms: OFF, geometric, bounded, old ML veto and frozen utility hybrid.
Three areas x two altitudes x three conditions x three errors x three seeds x
five arms = 810 descents, 162 paired configurations, 162 cases per arm.
Smoke: its separate area, 500 m, first error, seed 404, all conditions/arms.
Smoke checks infrastructure and data integrity only; no policy tuning follows.

Success requires actual terrain contact, miss <10 m, vertical impact <2 m/s
and horizontal impact <1 m/s. Primary comparisons: utility versus geometric
and bounded, paired mean miss, target success and contact-speed violations.
Also report all controls, per-area/condition/altitude results, failures,
navigation error, paired improvements/worsenings and inference time.

Evidence of transfer requires lower pooled mean miss and fewer speed violations
without fewer target successes than geometric; compare the bounded control
separately. Report any mixed or negative result without changing this criterion.
Report per-area directions of effect. With only three crops from one tile,
do not present scan counts as independent trials or claim mission-level
statistical significance. No significance test or population confidence claim
is planned for this small terrain sample.

## Integrity and stopping

Before execution freeze plan, source terrain, model/policy and runtime hashes.
Verify complete paired arms, identical initial sensor inputs, all scan routing,
gain/label geometry, contact criteria, model parity, traces and cloud files.
Verify current model, policy, estimator, matcher and guidance hashes remain
identical to their previously archived versions. Retain the adapter source.
Stop on compilation, integrity, missing data or runtime errors; preserve failed
attempts and document repairs. Never rewrite raw outcomes to repair reporting.
Archive results and update project documents regardless of outcome. Stop Play
after completion. Ablations and registration/controller changes are later work.
