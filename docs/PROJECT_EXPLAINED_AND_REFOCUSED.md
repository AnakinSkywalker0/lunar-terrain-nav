# LANTERN: what we have achieved and why it matters

Updated 22 October 2026. Current project explanation and research assessment.
Latest results: [frozen-model Site01 transfer](SCAN_UTILITY_TRANSFER_RESULTS.md).
Earlier results: [utility-based scan trust v2 on Site04](SCAN_UTILITY_RESULTS.md).
Chronological record: [full log](FULL_LOG.md).

## Is this significant work?

**Yes: substantial engineering and meaningful early applied research.** We have
progressed from displaying a lunar surface and flying a demonstration lander to
testing whether terrain measurements actually improve navigation and landing.
The system now compares repeatable descents, records failures, and runs a
trained correction policy inside Unity's estimated-state control loop.

The Site04 test found smaller landing errors and fewer excessive touchdown
speeds. The subsequent Site01 test retained a smaller average error but produced
more speed violations, with the same number of successful target landings as
geometric matching. This exposes an important limit to the model's transfer.
The work does not
yet establish statistical significance, a novel algorithm, general performance
across lunar sites, or readiness for a real mission.

## The problem we are solving

A lander has a stored map and an uncertain estimate of where it is. Its live
laser measurements may help it locate itself, but the map can be inaccurate and
different places can look similar. Following a convincing but wrong match can
steer the lander away from the target or create excessive sideways speed.

Our research question is: **When should a lander apply, reduce or reject a
terrain-matching correction, and does that decision improve the landing?**

The current testable claim is that a learned correction-utility policy reduces
target error and contact-speed violations relative to geometric matching and a
simple bounded correction rule under controlled map mismatch. The Site04 test
supported this claim within one reserved Site04 area. The new Site01 evaluation
failed the combined error/speed criterion, and neither evaluation increased
successful landings over those two baselines.

## Latest milestone: transfer to another lunar tile

Completed 810 new descents across three Site01 areas with the existing model
and policy, without retraining. The selected crops lie outside the Site04 tile.
Each of five policies received 162 paired configurations. Utility/geometric
target successes were 54/162 for both; mean miss was 43.60/45.99 m (5.2% lower
for utility), while speed violations were 47/39. All accurate-map cases
succeeded; no changed-terrain or shifted-map cases met the success criteria.

The prewritten transfer criterion failed. Smaller average errors did not produce
fewer excessive-speed contacts on new terrain. The next priority is diagnosing
that failure and testing contact-speed safeguards and component ablations with
a new reserved evaluation. Site01 appeared in older separate sensor studies,
but was excluded from fitting and selection of this scan-utility model.
The sections below retain the earlier Site04 evidence and its original scope.

## How the original map idea fits

A DEM is a grid with one height per horizontal location: for example,
`(east=100 m, north=200 m) -> elevation=12 m`. Placing those samples in space and
joining neighbours creates a 3D terrain surface. This is often called a 2.5D map
because it cannot represent multiple surfaces at one horizontal location.

We use the actual NASA PGDA Site04 elevation data. The source has 5 m sampling;
the 16 km Unity terrain has 2049 height samples per side, about 7.8 m spacing.
`tools/make_heightmap.py` converts the raster and `Site04SceneBuilder.cs` builds
the Unity surface.

This conversion is geometric and needs no ML. It adds no measured information:
interpolation cannot discover an absent rock, cave or overhang. The original
map-to-surface idea is implemented. The current research investigates how live
measurements of that surface can improve navigation when the prior is imperfect.
It has not demonstrated ML reconstruction of missing lunar terrain.

## What each program does now

| Component | Role in the current project |
|---|---|
| Lunar DEM | Supplies measured elevation samples for the terrain and stored prior |
| Unity + C# experiments | Simulates ground contact, noisy lidar, terrain matching, navigation estimates and guidance using those estimates |
| Python data and ML tools | Prepare labels, fit the scan-utility model, verify exports and summarize recorded Unity results |
| C# model inference | Evaluates the exported model inside Unity and scales proposed corrections; Python is not launched for each scan |
| Older Python simulator | Runs separate numerical sensor-trust studies; those results are not interchangeable with the Unity experiments |
| Blender lander | Supplies editable vehicle artwork for presentation; appearance does not validate flight dynamics |

There are separate execution paths. The original `Site04.unity` full-height
demonstration uses true-state autopilot information. The newer experiments use
corrected navigation estimates to guide the vehicle. Their results provide the
evidence about whether scan matching and learned correction utility help.

## How the experiment works

1. Give the simulated ground and onboard prior separate representations. Test
   an accurate map, altered relief and a map with a horizontal coordinate shift.
2. Start a short descent with a known injected position-estimation error. Lidar
   measures the simulated ground; a matcher proposes a position correction.
3. Run identical configurations with matching OFF, geometric matching, a bounded
   classical rule, the old learned veto and the new utility policy.
4. Feed the resulting navigation estimate into guidance. Ground truth supplies
   sensor simulation, initialization, training labels and evaluation, but is
   unavailable as an inference feature or a guidance position measurement.
5. Record actual contact, target miss, vertical and horizontal impact speed,
   scan decisions and computation time. Preserve raw data and frozen artifacts.

The latest final descents start at 500 or 1500 m. Earlier tests also used 2000 m.
These short runs isolate the terrain-matching question and make repeated tests
practical. They do not validate the preceding descent from 102.5 km or orbital
flight. The original full-height demonstration remains a separate integration
demonstration, not evidence of learned navigation across the entire approach.

## What we have learned

**A correct map can materially improve navigation.** The expanded geometric
experiment ran 270 stationary scans and 540 descents across five Site04 areas.
With accurate maps, matching achieved 90/90 target successes and mean miss of
0.49 m, versus 93.94 m with matching OFF. Changed terrain and shifted maps exposed
confident wrong matches and contact-speed failures.

**Rejecting wrong updates is an insufficient objective.** The first learned
veto rejected many harmful proposals but also rejected useful corrections. In
its separate 648-descent test it achieved 18/162 target successes against
90/162 for geometric matching. That negative result is retained: a good-looking
scan rejection metric can accompany worse landings.

**Learning correction utility produced a better measured tradeoff.** The new
model estimates how much of a correction to use. Training spans broader error
directions and magnitudes; inputs omit signed direction, and development
selection uses complete landing outcomes. A model prediction is a gain estimate,
not a calibrated probability that a sensor is correct.

The v2 workflow collected 7680 scan proposals, compared policies in 672
development descents, froze the model and selected policy, then ran 270 final
descents: 54 matched configurations for each of five policies.

| Policy | Target successes /54 | Mean target miss | Contact-speed violations |
|---|---:|---:|---:|
| Matching OFF | 0 | 64.40 m | 0 |
| Geometric matching | 24 | 34.64 m | 12 |
| Classical bounded correction | 24 | 32.67 m | 12 |
| Previous learned veto | 0 | 64.40 m | 0 |
| Updated utility ML | 24 | 28.92 m | 7 |

Success requires contact, target miss <10 m, vertical impact <2 m/s and horizontal
impact <1 m/s. All vehicles contacted the ground; contact alone is not success.

Utility ML reduced mean miss by **16.5% versus geometric matching** and improved
41 of the 54 paired configurations, worsened 7 and tied 6. Speed violations fell
from 12 to 7. Success remained **24/54** for utility, geometric and bounded rules.
Within this same final test the old veto had 0/54 successes, giving a direct
old/new policy comparison. Earlier batches used different cases and should not
be treated as a directly comparable learning curve.

## What is our defensible contribution?

| Level | Evidence and current assessment |
|---|---|
| Engineering | A functioning lunar-terrain navigation testbed with independent map/ground representations, estimated-state guidance, portable ML inference and retained experiment records |
| Applied research | Controlled comparisons expose the failure of a rejection-only objective and show a correction-utility policy improving error and speed outcomes in a reserved-area test |
| Method novelty | Not established. Terrain meshing and random forests are established techniques; a literature comparison is still needed before claiming novelty |
| Broad reliability or statistical significance | Not established by this batch. Repeated cases share one final terrain area and simulator; they are not independent lunar-site trials |

The useful insight is that sensor trust must be judged by navigation and landing
outcomes. Fewer accepted wrong matches, classifier accuracy or a visually good
simulation cannot substitute for those outcomes. We now have a working way to
test that insight, including a preserved failed model and strong simple controls.

The v2 changes include labels, data coverage, features and policy selection.
They changed together, so we cannot yet attribute the improvement to any one
component. Utility policies also received development selection among three
variants; a stronger comparison should give classical baselines a matched
tuning budget.

## What remains before stronger research claims?

The earlier final test used one reserved crop from Site04; the subsequent
transfer test added three Site01 crops outside that tile. Sensors are synthetic
and attitude response is idealized with 3-DOF dynamics. Seven utility contacts
violated the speed limit in Site04 and 47 in Site01. The Site04 shifted-map cases
achieved 0/18 successes: some cases hit the matcher's conservative search
boundary, while others accepted shape matches with an absolute coordinate bias.
Local shape alone cannot uniquely resolve a global map translation.

The next validation should:

1. Freeze a new protocol and evaluate multiple untouched areas on independent
   terrain data. Report paired outcomes and uncertainty accounting for shared
   terrain; do not reuse this observed final batch as an untouched test.
2. Separate the effects of utility labels, broader training data, direction-free
   features and learned gains with matched ablations and baseline tuning budgets.
3. Test an independent map-registration reference and explicit contact-speed
   safeguards, then measure whether successful landings actually increase.
4. Improve sensor and vehicle realism, including attitude/contact dynamics,
   before extending claims to physical missions or the full descent.

These are follow-up goals beyond the completed transfer test. More training
on the same cases is not a substitute for independent validation. The transfer
stage ran new simulations with the existing frozen model and did no training.

## What to tell a mentor

> We have built a working terrain-relative navigation and sensor-trust testbed
> using lunar elevation data. Our first learned gate exposed a real failure:
> rejecting more wrong updates can also reject the corrections needed to land.
> A revised utility-based policy improved error and speed metrics on Site04.
> We then tested the frozen model in 810 descents across three Site01 areas:
> average miss improved by 5.2%, but excessive-speed contacts increased and
> successful landings did not increase. This revealed where the method fails
> to transfer. We now have reproducible evidence and a focused next step:
> component ablations, contact-speed safeguards and map-registration checks.

The project has moved beyond a visual demonstration into a measurable applied
research study. Accurate-map navigation is demonstrated in both tiles; the
learned policy's error/speed tradeoff is terrain-dependent. Broader reliability
and a publishable contribution still need evidence.

## Evidence and related documents

- [Latest transfer result and limitations](SCAN_UTILITY_TRANSFER_RESULTS.md)
- [Earlier Site04 utility result](SCAN_UTILITY_RESULTS.md)
- [Frozen v2 protocol](SCAN_TRUST_PROTOCOL_V2.md)
- [First learned veto: preserved negative result](SCAN_TRUST_RESULTS.md)
- [Expanded geometric comparison](TERRAIN_MATCHING_EXPANDED_RESULTS.md)
- [Initial short-descent comparison](TERRAIN_MATCHING_RESULTS.md)
- [Progress and earlier sensor-trust studies](PROGRESS.md)
- Final v2 records: `out/scan_utility/20261021_204054_eval/`.
- Editable lander: `art/lander/LANTERN_Lander.blend`; Unity export:
  `LANTERN/Assets/Art/Lander/LANTERN_Lander.fbx`. Presentation assets do not
  establish physical flight fidelity.
