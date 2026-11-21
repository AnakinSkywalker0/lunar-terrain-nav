# Learned scan trust: completed experiment

22 October 2026. Training, Python/Unity inference verification and **648 new
closed-loop Unity descents are complete**. The learned policy is not an
improvement over the geometric matcher in this experiment.

## Plain-language result

The lander already benefits from matching laser measurements against its stored
terrain map. We trained a model to decide which proposed corrections to reject.
It became very cautious: it applied only 28 corrections in 162 descents. That
nearly eliminated wrong updates, but it also discarded the good updates needed
to find the landing target. Many landings retained their initial position error.

**A sensor-trust model must preserve useful navigation as well as reject bad
measurements. This version does not meet that requirement.** It remains an
experimental arm; the existing geometric experiment is preserved.

## Measured outcomes

Each arm has 162 descents over the same 162 configurations. Success requires
actual terrain contact, target miss < 10 m, vertical impact < 2 m/s and horizontal
impact < 1 m/s. Every arm made contact in all 162 cases, but contact alone is not
successful navigation.

| Policy | Target successes | Mean target miss | Corrections applied | Wrong corrections applied |
|---|---:|---:|---:|---:|
| Matching OFF | 0/162 | 96.24 m | 0 | 0 |
| Geometric matching | **90/162** | **23.00 m** | 2,805 | 1,077 |
| Tuned RMS/confidence rule | 45/162 | 49.96 m | 759 | 304 |
| Learned veto | 18/162 | 84.70 m | 28 | 1 |

Wrong means the proposed correction leaves absolute horizontal navigation error
>10 m; a proposal can reduce error substantially and still receive this label.
Counts span evolving trajectories and are not equal-opportunity classification
rates. A low count achieved by refusing almost everything is insufficient.

| Map condition | OFF | Geometric | Tuned rule | ML |
|---|---:|---:|---:|---:|
| Accurate map | 0/54 | **54/54** | 45/54 | 15/54 |
| Changed terrain | 0/54 | **36/54** | 0/54 | 3/54 |
| Shifted map | 0/54 | 0/54 | 0/54 | 0/54 |

Accurate-map mean miss was 0.36 m geometric versus 71.62 m ML. For changed terrain
it was 9.89 m versus 86.18 m. For shifted maps it was 58.75 m versus 96.29 m. The new
terrain perturbation differs from the old expanded experiment; compare arms
within this batch, not success rates across the old/new conditions.

ML increased final target miss in 143 of 162 paired configurations relative to
geometric matching, improved 4 and tied 15. Mean deterioration was 61.69 m.
The conditional paired-configuration bootstrap interval is 55.47–67.83 m worse;
this conditions on the three observed areas and is not independent-site
generalization uncertainty. All areas share the Site04 dataset.

Geometric descents all remained below both impact-speed limits. ML had 5 cases
at or above 2 m/s vertically and 25 at or above 1 m/s horizontally. Its maximum
sideways impact was 4.57 m/s; geometric maximum was 0.92 m/s. Rejecting updates and
applying occasional late corrections did not guarantee safe touchdown speeds.

## What was built and verified

- A separate scan-specific 32-tree random forest, depth <= 6, with 1,252 nodes. Portable
  JSON is 43,965 bytes. The old 80 MB altimeter model is preserved.
- Training used 5,522 geometrically accepted proposals from original/area01/
  area02, with equal area and within-area case weights. Ground truth supplies
  labels only; no truth, site ID, map condition, seed or arm is a model input.
- Compared standardized logistic regression, full-feature forest and a forest
  restricted to residual/confidence/point-count features. Thresholds and a
  classical RMS/confidence baseline were selected on area03 validation only.
- The selected forest's bad-score threshold is 0.18. It was not refit on
  validation/test data and was not changed after new descent outcomes.
- Unity reproduced Python scores and decisions on 10,530 identical float32
  input vectors. Maximum score difference 3.33e-16; eight Python contract tests
  passed. Inference is implemented in C#, without launching Python per scan.
- The learned decision is actually connected to navigation corrections in
  `ScanTrustExperiment`: OFF, geometric, rule and ML arms. Both vetoes are
  calculated in every arm, with only correction application differing.
- Three fresh, nonoverlapping 2.4 km Site04 terrain crops were selected before
  fitting using slope/spacing criteria. Tests used new position errors, noise
  seeds, relief-bump location/width and map-translation direction.
- A 12-case smoke test passed, then 648 descents finished in 137.7 wall seconds.
  All cases, paired inputs, policy routing, success labels, source/model/rule/
  protocol hashes and trajectory/cloud files were verified. The frozen
  matcher/navigation/guidance core is unchanged from v1/v2.

Desktop inference, including both veto evaluations, took median 0.0079 ms and
p95 0.0206 ms per scan, excluding scan generation/matching. This is not a
flight-computer benchmark. The vehicle still has synthetic sensors, ideal
attitude response and simplified 3-DOF dynamics.

## Why the promising classifier score did not become better landings

On validation, geometric matching accepted 805 bad proposals; ML accepted 2.
However, ML rejected 473 of 1,030 geometrically accepted safe proposals. On the
retrospective development area04 it accepted no bad proposals but rejected
1,119 of 1,325 safe proposals. Those historical areas had already been inspected;
these are development scores, not an untouched final test.

In the fresh accurate-map runs, all 15 ML successes used the first new error
pattern(+45,+70)m. The other two error patterns had 0/36 successes. The forest
assigns about 68% of split-importance to correction components and magnitude;
this is consistent with sensitivity to injected-error signatures, though
importance alone does not prove a causal explanation. The residual-only
ablation also rejected almost all safe validation proposals. These six features
are not enough to justify a general sensor-trust claim from this dataset.

Another mismatch is the label and decision objective: a correction that reduces
100 m error to 45 m is labelled bad because it still exceeds 10 m. Rejecting it can
leave the lander further from the target. Our validation objective penalized
accepted bad corrections four times as strongly as rejected safe corrections;
it did not optimize the eventual landing outcome. The closed-loop test exposed
that limitation rather than silently tuning around it.

Finally, shape matching alone cannot establish absolute map registration. A
coherently translated map can fit laser data well. None of the four arms solved
the shifted-map target requirement. Independent absolute navigation/registration
evidence is still needed to diagnose that ambiguity reliably.

## Next experiment

Before more fitting, build more diverse development trajectories with varied
error directions/magnitudes and map perturbations, reserving fresh terrain and
error families for final testing. Redesign trust around correction utility and
uncertainty, and test bounded/gradual corrections and temporal consistency as
classical baselines. Assess the full landing result during development, not
only per-scan rejection counts. Treat global map registration as a separate
observability problem requiring independent information.

Do not tune or retrain on these fresh evaluation outcomes and present the same
runs as an untouched test. A new model requires a new frozen evaluation.

## Evidence and reproduction

- Protocol: `SCAN_TRUST_PROTOCOL_V1.md`.
- Training/model report: `out/scan_trust/20261022_model_v1/`.
- Smoke: `out/scan_trust/20261021_190913_smoke/`.
- Full data: `out/scan_trust/20261021_190929_closed_loop_v1/`.
- Runtime: `LANTERN/Assets/Scripts/Experiments/PortableScanTrust.cs`.
- Harness: `LANTERN/Assets/Editor/ScanTrustExperiment.cs`.
- Summarize: `python tools/summarize_scan_trust.py`.
- Unity menu: `SensorTrust/Experiments/Run scan-trust protocol v1`.

Full data include source snapshots/hashes, frozen model/rule, protocol, parity
report,648 trajectories and sparse point-cloud files, scan-level scores and
actual application decisions, condition/site/altitude/error tables and paired
mission differences. The summary.csv `accepted_matches`/`wrong_matches` columns
remain raw geometric proposal counts; use scans.csv `applied`/`applied_bad` for
the corrections actually used by an arm. This distinction is checked in the
report generator.

The v1/v2 outputs, original replay pointers and full-height Site04 scene remain
available. Timestamps in run-folder names use UTC; the local date is 22October.

![Measured four-arm results](../out/scan_trust/20261021_190929_closed_loop_v1/results.png)
