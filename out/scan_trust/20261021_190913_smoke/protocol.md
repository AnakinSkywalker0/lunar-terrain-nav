# Learned scan-trust experiment v1

22 October 2026. Written before fitting the scan classifier or obtaining new
closed-loop outcomes. User explicitly authorized training with “DO IT”.

Hypothesis: a scan-specific learned veto reduces wrong accepted corrections,
and improves closed-loop landing outcomes relative to the frozen geometric gate.
The hypothesis may fail. Local shape fit cannot resolve a coherent global map
translation without independent absolute information.

Training data: the frozen 10,530-proposal preparation v1. Original, area01,
area02 are training; area03 validation; area04 retrospective test. Existing areas
have already been inspected, so area04 is development evidence, not a pristine
final test. Train only on geometrically accepted proposals. Inputs are the six
declared runtime features; labels are proposed absolute horizontal error >10 m.
Inverse counts weight areas equally and cases equally within each area.

Candidate models: standardized logistic regression (C=1, max_iter=2000) and
32-tree random forests (max_depth=6, min_samples_leaf=20), one using all six
features and one with correction components/magnitude zeroed during fitting.
The latter trees can only split on point count, RMS and confidence. Seed11
determines deployment. Seeds22/33 repeat forest fitting to report sensitivity,
without choosing a preferred seed. No fitting uses validation or test rows.

Each candidate gets 25 veto thresholds from 0.02 through 0.98 inclusive.
The classical baseline gets 75 predefined RMS/confidence pairs (15 RMS limits
from 0.5 through 8 m, five confidence minima from 0.35 through 0.99). Choose
using validation only, minimizing 4 * bad-acceptance fraction + safe-rejection
fraction, measured among geometrically accepted bad/safe proposals. Ties prefer
lower safe rejection, then stricter bad rejection, then the first configuration.
This intentionally assigns greater cost to accepting an incorrect correction;
it does not guarantee a safe or accurate landing. Model family selection has
three candidates; report all, including the rule, to expose tuning differences.

Report classification counts, bad acceptance, safe rejection, AUC/AP where
applicable, Brier score and calibration bins. Scores are not claimed calibrated.
Do not refit on validation/test after selection. Save portable JSON, model
metadata, code/data hashes and Python inference fixtures; compare Unity scores
and decisions on identical float32 feature vectors before running any descent.

Fresh closed-loop evaluation: select three further flat targets from the same
Site04 RAW DEM by the existing slope/edge eligibility rule, greedy farthest-first
from all five old centres. Exclude overlapping 2.4 km axis-aligned crops relative
to old and already selected fresh areas. Fix coordinates before fitting. These
are new areas within Site04, not an independent lunar dataset.

Full matrix: three fresh areas x altitudes500/2000m x aligned/relief_change/map_shift
x errors(+45,+70),(-95,-35),(+75,-90)m x seeds101/202/303 x four arms:
matchingOFF, frozen geometricON, tuned ruleON, selected MLON. Total648 descents,
162 paired four-arm configurations. No stationary cases in this batch. Smoke:
first fresh area,500m,first error,seed101,all three conditions,four arms=12 cases.
Do not tune on smoke outcomes.

Keep the existing matcher, estimator, guidance and simplified 3-DOF physics.
Change the truth-only relief bump to12m,centre(-90,+110)m,sigma75m, and map shift
to(-28,+36)m. New errors, noise seeds and map perturbations prevent exact reuse
of earlier signatures. Both controls receive the identical sensors and scan
schedule. All four arms compute the same matcher and both veto scores; only
the choice to apply a correction differs. Reset state, fuel and RNG per arm.

Success requires PhysX contact, vertical impact<2m/s, horizontal impact<1m/s,
target miss<10m. Retain timeouts and failures. Report by map condition and area,
paired mission differences, navigation error, target miss, impact speeds, fuel,
wrong applied corrections and inference cost. Uncertainty resamples complete
paired configurations; three areas are too few for strong site-generalization
claims. Never treat scan rows as independent missions. Freeze models, rule and
protocol before reading fresh results; do not retrain to repair test failures.

Preserve the old altimeter model, v1/v2 simulation outputs and replay pointers.
New Unity runs use a separate latest_scan_trust pointer. The original full-height
Site04 scene is not changed by this experiment.
