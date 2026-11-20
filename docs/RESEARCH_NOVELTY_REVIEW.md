# LANTERN: original idea, prior work and conference contribution

Literature check: 22 October 2026. A targeted review of primary sources, not an
exhaustive survey or a guarantee that a narrower idea is unprecedented.

## Verdict

The proposed system is technically buildable. The broad idea of observing a
terrain point cloud with lidar and matching it to an onboard elevation map for
localization is established terrain-relative navigation. Combining lidar with
vision/inertial navigation and using terrain in range-sensor fault rejection
also has direct precedents. Those elements alone are insufficient novelty for
a new research claim.

A specific method that separates map uncertainty, ambiguous localization and
sensor degradation, and improves full landing outcomes, could support applied
research. That narrower contribution remains a candidate: this review has not
established that it is an unaddressed literature gap. Conference acceptance
depends on the precise advance, comparisons and evidence.

## The user's intended system

Stored 2.5D lunar DEM + live range observations + attitude/motion estimate
-> local 3D point cloud/map -> registration and uncertainty
-> camera/altimeter consistency and reliability assessment
-> fused vehicle state -> guidance -> measured landing outcome.

A DEM already specifies a surface in three dimensions, with one elevation per
horizontal coordinate. The fresh point cloud supplies new observations; lifting
the DEM into a mesh supplies a representation. They need compatible coordinates
and scale, not identical map formats. Several fixed laser beams alone provide
only sparse constraints; scanning, flash lidar or accumulated motion is needed
for a sufficiently informative patch. Accumulated scans require timing,
calibration and motion/attitude compensation. Full pose and uncertainty are
harder than estimating a horizontal displacement with fixed attitude.

We focus on the descending lander here. A rover uses related localization ideas
but introduces a different motion model and evaluation task; mixing both would
expand the paper unnecessarily.

## Closest verified work

### NASA/JPL ALHAT: institutional project description

JPL describes localizing a lander by registering a small lidar 3D observation
against a larger topographic reference. This directly precedes the central
scan-versus-map idea. It also describes scan alignment for relative velocity.
The project page is evidence of prior art, not a comparative benchmark.
[NASA/JPL ALHAT](https://robotics.jpl.nasa.gov/what-we-do/research-tasks/alhat-autonomous-landing-and-hazard-avoidance-technology/).

### Choe et al., ION International Technical Meeting, 2022

Yeongkwon Choe, Yejun Kim, Jaehyuck Cha and Chan Gook Park,
*Feasibility Study of a Loosely Coupled LiDAR-Visual-Inertial Positioning System
for a Lunar Landing Using a Scaled Terrain Model*, pp. 545-553,
DOI 10.33012/2022.18160. Couples lidar localization against a sparse lunar DEM
with visual-inertial odometry and reports a scaled-terrain experiment. This
overlaps both map matching and adding camera/motion information. Reviewed the
publisher's abstract and bibliographic record; full text requires access.
[ION record](https://www.ion.org/publications/abstract.cfm?articleID=18160).

### Choe and Park, IEEE TAES, 2024

*LiDAR-Inertial-Based Absolute Positioning With Sparse DEM for Accurate Lunar
Landing*, IEEE Transactions on Aerospace and Electronic Systems 60(3),
3482-3495, DOI 10.1109/TAES.2024.3363678. Describes an ensemble-Kalman approach
to the disparity between detailed lidar observations and sparse reference
terrain. Publisher abstract/metadata were available through search; direct
full-page access failed. No assessment of uninspected experimental details.
[Publisher record](https://ieeexplore.ieee.org/abstract/document/10428057).

### Adams et al., AIAA SciTech, 2025

Davis W. Adams, Kari C. Ward, Kyle W. Smith, Samuel M. Pedrotty and Gavin F.
Mendeck, *Topographic Slant Range Modeling and Fault Detection for Precision
Planetary Landing*. PITFAL rejects inconsistent multibeam ranges using terrain
and statistical beam agreement. The paper's navigation architecture also uses
camera information and lidar-derived terrain. This is a close baseline for
terrain-informed altimeter reliability, rather than a claim that any trust
logic is new. The public 18-page paper was accessed.
[NASA paper](https://ntrs.nasa.gov/citations/20240014100).

### Sheppard, Reale and Skinner, 2025 preprint

Anja Sheppard, Chris Reale and Katherine A. Skinner, *A Stochastic Approach to
Terrain Maps for Safe Lunar Landing*, arXiv:2512.12058. Models spatially varying
map uncertainty with Gaussian processes and LRO confidence information. Its
conclusion identifies downstream hazard detection/trajectory use as future
work. Map uncertainty itself is therefore established research, while its use
in our proposed sensor diagnosis remains a candidate extension, not a verified
gap. Full HTML, including the conclusion, was accessed.
[Paper](https://arxiv.org/abs/2512.12058).

### Adjacent terrain point-cloud processing

Abdulbaki Sanlan, Fatih Erol, Murad Abu-Khalaf and Emre Koyuncu,
*Terrain-Aided Navigation Without Raycasting: A Sliding Grid Approach for Point
Cloud Processing*, arXiv:2510.06470, first posted 2025, revised 13 October 2026.
The abstract describes alternative terrain measurement models for point-cloud
navigation. This further cautions against treating the point-cloud/grid
representation as a new research area. Abstract/metadata reviewed only.
[Record](https://arxiv.org/abs/2510.06470).

## Novelty assessment by component

| Component or claim | Assessment |
|---|---|
| Construct a surface from stored heights | Established representation conversion |
| Generate 3D observations with lidar | Established sensing/mapping |
| Match dense lidar to a coarser lunar DEM | Direct prior work; not a new problem |
| Combine lidar localization with visual/inertial information | Direct prior work |
| Reject suspect ranges using local terrain | Direct prior work, including PITFAL |
| Treat the stored map as uncertain | Already addressed in terrain-mapping research |
| Jointly distinguish map mismatch, weak registration and sensor failure, then improve landing outcomes | Candidate contribution; novelty not verified |
| Characterize when a learned correction policy improves error but worsens touchdown speed | Measured project finding; needs broader controlled evidence and related-work comparison for a paper |

## The hard problem worth pursuing

A disagreement does not identify which input is wrong. A dark camera image, an
altimeter bias, incorrect attitude, a terrain cliff absent from the map and a
wrong map alignment can all produce inconsistent observations. Reusing the same
range samples for both localization and altimeter validation creates correlated
evidence; it must not be counted as an independent vote. Globally shifted maps
can leave absolute position ambiguous even when the local shapes agree.

A useful proposed research question is:

> Under controlled camera degradation, range faults and map mismatch, does
> accounting for registration ambiguity and map uncertainty reduce harmful
> sensor updates and improve landing outcomes compared with equally tuned
> confidence and innovation gates?

The candidate method should retain an unresolved/unknown state when the
available observations cannot separate these explanations. A small residual
or a learned confidence score alone is not proof that a sensor is healthy.
This is a proposed direction, not an implemented or proven result.

## Where the current project actually stands

The recent Unity pipeline generates lidar samples, matches them to an elevation
surface, scales the proposed position correction and feeds an estimate into
guidance. Its random forest estimates a useful correction gain. It does not
implement the complete joint camera/altimeter diagnosis above, and its short
scan history is not a demonstrated persistent 3D reconstruction/SLAM system.
Earlier Python camera/altimeter studies are a separate execution path.

The frozen Site01 test completed 810 descents: utility and geometric matching
both achieved 54/162 successes. Mean miss improved 45.99 to 43.60 m, but speed
violations increased 39 to 47. Thus the current model has not demonstrated a
general landing-safety improvement. The experimental infrastructure and these
failure records are useful foundations for the original broader question.
See [transfer evidence](SCAN_UTILITY_TRANSFER_RESULTS.md).

## Minimum credible next study

1. Build and evaluate the joint sensor/state-estimation loop, with actual
   camera observations, range sensing and attitude/motion uncertainty.
2. Compare fixed fusion, matcher-confidence gating, statistical innovation
   gating, terrain-aware range rejection, and the proposed joint method. Give
   all tunable baselines the same development budget. A PITFAL-style
   approximation must be labelled as such rather than an exact reproduction.
3. Separate healthy sensors/wrong map, faulty sensors/correct map, ambiguous
   terrain and simultaneous degradation. Add dust/common-mode cases if claimed.
4. Remove map uncertainty, the independent camera evidence, temporal evidence
   and learned gain one at a time. Compare point-cloud and height-patch methods
   with identical information and sensor budgets.
5. Reserve new areas and fault combinations before tuning. Report false sensor
   rejection, missed faults, localization error, uncertainty calibration,
   abstentions, contact speeds, success, runtime and real-time feasibility.
   Account for shared terrain when interpreting uncertainty.
6. Add a small real-sensor terrain-rig test if feasible. Simulation can support
   a paper, but its physical validity and limitations must be demonstrated.

If the joint method does not improve outcomes, a rigorous failure analysis and
reproducible benchmark are an alternative contribution; merely listing failures
is insufficient. No new training or experiments were started for this review.

## Conference route, checked 22 October 2026

- **IEEE SPACE 2027:** navigation, sensors and robotics are listed topics. The
  announced paper deadline is 31 January 2027; AESS also lists that CFP deadline.
  This is a plausible scope match, not a prediction of acceptance.
  [Topics](https://ieeespace.org/call-for-papers/),
  [dates](https://ieeespace.org/important-dates/),
  [IEEE AESS listing](https://ieee-aess.org/).
- **AIAA SciTech GNC:** appropriate subject area for estimation, sensor fusion
  and validation. Its current GNC call requires a full draft manuscript rather
  than an abstract. Consider an appropriate future cycle after the contribution
  is established; this review does not establish a currently open submission.
  [Official call](https://scitech.aiaa.org/call-for-content/call-for-papers/).
- **IEEE Aerospace Conference:** relevant scope, but the 2027 regular paper
  deadline was 2 October 2026 and is already past. The 8 January 2027 final-paper
  date is not a new-submission deadline.
  [Official dates](https://www.aeroconf.org/key-dates).

An idea can be discussed with researchers now. A peer-reviewed submission needs
a completed, explicit contribution and evidence. Neither venue choice nor a
novel-sounding combination guarantees publication.

## Follow-up: computationally lighter maps

**Second-check qualification:** [closer prior-work audit](MAP_EFFICIENCY_RECHECK.md)
found compact elevation encodings for TRN, localization-aware map compression,
planar quadtree landing maps and 2026 NASA resource-optimized ATRN. Preserving
navigation-relevant features is an established design objective, not a novelty
claim. The candidate below needs a concrete method and direct comparisons.

The user asked whether reducing map computation could establish novelty. A
specific, demonstrated resource/accuracy advance could be a contribution, but
generic compression, downsampling or adaptive resolution is not a new research
idea. Distinguish stored bytes, peak RAM, map-query cost and complete matching
latency; disk compression can add decoding cost. A smaller rendered mesh does
not establish faster navigation. Our current matcher already uses an elevation
grid, so the reference baseline should be an efficient grid rather than an
unnecessarily large volumetric map.

Verified precedents, abstract-level review:

- Pascal Schoppmann et al., *Multi-Resolution Elevation Mapping and Safe Landing
  Site Detection with Applications to Planetary Rotorcraft*, IROS 2021. Uses
  dynamic level of detail and probabilistic multiresolution terrain aggregation
  for resource-efficient onboard mapping and landing-site detection.
  [Paper](https://arxiv.org/abs/2111.06271).
- Liren Jin et al., *Adaptive-Resolution Field Mapping Using Gaussian Process
  Fusion with Integral Kernels*, preprint 2021, revised 2022. Preserves detailed
  regions and coarsens other regions while maintaining spatial correlations;
  reports mapping-time and memory benefits on synthetic and real data.
  [Paper](https://arxiv.org/abs/2109.14257).
- Sanlan et al.'s point-cloud navigation paper, cited above, explicitly targets
  cheaper terrain measurement evaluation. Efficient processing is a direct
  competing research direction, not an unexplored rationale by itself.

Candidate: choose what terrain information to retain under a fixed memory and
processing budget according to localization ambiguity, pose uncertainty,
predicted lidar footprint and map uncertainty. Preserve the information needed
for camera/altimeter trust decisions and expose uncertainty added by compression.
This is a proposed task-aware criterion, not confirmed novelty; comparisons
against existing adaptive mapping and informative-landmark selection are needed.

Profile the current matcher first. Compare dense and uniformly reduced grids,
quantized/compressed grids, standard adaptive resolution and the proposed method
at equal memory limits and on identical hardware. Measure storage and peak RAM,
encoding/decoding/index overhead, median/tail matching latency, false confident
matches, pose error, sensor-decision errors and contact outcomes. A map that
looks similar but causes more wrong matches is not an equivalent replacement.
Hold source terrain, scans, initial conditions and tuning budgets constant.
Report the full resource/accuracy tradeoff, including failure cases; proposed
savings are targets until measured. No implementation or new experiment here.

## Pitch for the original sensor-integrity direction

> I am developing a terrain-aware sensor-integrity system for lunar descent.
> It compares live lidar geometry with an uncertain onboard elevation map to
> assess localization quality and investigate when camera or altimeter updates
> should be trusted. We already have a reproducible simulation testbed and have
> shown that reducing position error alone can worsen touchdown speed. The next
> contribution is a joint uncertainty-aware method tested against strong
> classical controls on reserved terrain and fault conditions.

This describes current development and the proposed contribution. It does not
claim invention of lidar terrain-relative navigation or a completed reliable
camera/altimeter trust system.
