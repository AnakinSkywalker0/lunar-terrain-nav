# Scan trust v2: diverse development and navigation utility

22 October 2026. Written before collecting/fitting v2 or viewing v2 mission
outcomes. User authorized this follow-up with “DO IT”. V1's negative result is
preserved. No v1 final-evaluation rows are used for v2 fitting or selection.

Hypothesis: diverse position-error directions and a correction-utility target
preserve useful corrections better than v1's absolute-error veto. Select the
operating policy using complete development landings rather than rejection
counts. Global map translation remains unobservable from local shape alone;
no claim that this model solves absolute registration is intended.

## Data collection and protected evaluation

Collect independent stationary scans in original/area01/area02 (training) and
area03/area04 (validation). Each area has aligned, positive relief, negative
relief and translated-map conditions, each with two frozen variants. For every
map, use altitudes 300/600/1200/2000 m and 24 random error/true-position poses.
Error angles span the circle, magnitudes include near-zero and 5–140 m; true
sensor positions vary within +/-180 m. Draws are fixed by seed314159 before
collection. Take two noisy scans at each pose without applying a correction:
3,840 cases / 7,680 scan proposals. Group split by area, never by scan.

Before collecting/fitting, freeze three further flat, nonoverlapping Site04
crops using the previous farthest-first/slope rule, excluding all eight earlier
crop centres. If three cannot be placed, record the actual number before
training and scale the final matrix accordingly. All remain within one DEM.
Save the manifest and hashes before collecting development data. Neither
their scans nor their outcomes enter fitting or development policy selection.

Training-map variants: relief at(+90,-40)m,sigma50m,amplitude+/-8m and
(-140,+75)m,sigma100m,amplitude+/-20m; map shifts(+30,-20)m and(-25,+35)m.
The familiar validation areas are development data, not a pristine test.

## Features and utility target

Direction-invariant inputs: fit RMS divided by expected lidar range noise;
heuristic confidence; horizontal correction magnitude; measured altitude;
correction consistency with the preceding proposal after accounting for the
last applied correction; previous-proposal-present flag. No correction x/z,
truth pose, injected error, map condition, site ID, seed or arm is an input.
Consistency uses only matcher history. It cannot identify a coherent map shift.

For valid, geometrically accepted proposals with correction d, train the
clipped least-squares gain:

    alpha* = clip((before_error^2 - proposed_error^2 + |d|^2)/(2|d|^2), 0, 1)

For |d|<0.5m use gain1: these tiny updates are not labelled harmful simply for
failing to reduce error by 1m. Truth is used only to create labels/evaluate.
This target can retain a useful correction that reduces100m error to45m.
It is a local position-utility label, not a proven optimal landing action.

Fit one32-tree RandomForestRegressor,depth8,min_leaf12,seed11, single CPU
worker. Equalize areas and cases in fitting. Repeat seeds22/33 for sensitivity
without choosing a preferred seed. No refit on validation/evaluation data.
Export portable trees and verify Python/C# scores on identical feature vectors.

## Select using development landings

Fixed development matrix: area03/area04 x altitudes500/2000m x aligned/positive
relief/map shift x four error vectors drawn with seed271828 x seeds404/505.
Start true position(+15,-10)m. Relief uses centre(-90,+110),sigma75,amplitude12;
map translation(-28,+36). Run seven arms per configuration: OFF, geometric,
classical bounded correction, v1 ML, and three v2 utility policies. Total672
descents. All get the same sensor RNG schedule and frozen geometric core.

V2 policies: hard gain(prediction>=0.5 ->1, otherwise0); soft gain(prediction);
hybrid gain(prediction>=0.75 ->1, otherwise prediction), with correction limited
to max(5m,0.5*measured_altitude). Classical bounded applies that same magnitude
limit to gain1. All gates require the original geometric acceptance.

Choose among the three v2 policies by maximum target successes, then minimum
count of descents violating either contact-speed limit, then lowest mean target
miss. Fixed tie order hard/soft/hybrid. Save the choice and development results
before running final evaluation. No tuning after final results.

## Final evaluation

Three reserved areas x altitudes500/1500m x aligned/changed terrain/shifted map
x three new errors with angles23/157/281 degrees,magnitudes35/70/95m x three
noise seeds717/818/919 x five arms OFF/geometric/bounded/v1ML/selected-v2.
True start(-12,+16)m; relief centre(-75,-80),sigma65,amplitude16m; map translation
(+22,-31)m. Total810 descents if three areas are available. Initial vertical
velocity -10m/s, same simplified3-DOF PhysX, estimator and guidance. The1500m
altitude and true-position offset differ from development. Save all failures.

Success requires actual terrain contact, miss<10m, vertical impact<2m/s,
horizontal impact<1m/s. Compare arms within the same paired configurations.
Report misses, success, navigation error, impact speeds, applied corrections,
local utility and inference cost, by area/altitude/error/map condition. Scan
counts are correlated observations. New crops within Site04 do not establish
generalization to an independent lunar dataset.

Preserve v1 model, all prior raw outputs and pointers. Use a separate utility
runner and output pointer. Smoke-check infrastructure before each full stage;
do not select policies on smoke or final outcomes. If learned utility still
fails, report that rather than changing its evaluation after seeing results.
