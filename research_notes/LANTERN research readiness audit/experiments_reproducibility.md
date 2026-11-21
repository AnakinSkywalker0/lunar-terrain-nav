# LANTERN experiments, ML pipelines, and reproducibility audit

Audit date: 2026-10-25. Scope: `sim/scan_trust.py`, `sim/scan_utility.py`, Python experiment tooling, `tests/`, experimental records/model metadata in `out/`, dependency/test/Git setup, and necessary terrain metadata. C# algorithms/physics and the accuracy of narrative project claims are assigned elsewhere. This audit reads generated C# strings **inside Python builders** only to understand experiment construction; it does not review C# source implementations. No model was trained, no Unity experiment was launched, and no existing project code/results were changed.

## 1. What pipelines, data lineage, and experimental independence are actually supported?

### Takeaway

The scan-trust and scan-utility pipelines have explicit area-grouped splits, frozen artifacts, and substantial local raw evidence. Utility is a genuine change in learning target and controller policy, but its final Site04 evaluation is one crop, transfer is three crops from one other DEM, and the older altimeter ML reports do not contain enough metadata to independently establish their split validity within this assignment's scope. [Preparation](../../tools/prepare_scan_trust_data.py#L21-L22), [utility training](../../tools/train_scan_utility.py#L19-L69), [transfer plan](../../out/scan_utility_transfer/20261022_091502_eval/plan.json#L1-L60), [legacy report](../../out/mc/ml_report.json#L1-L7).

### Cited Findings

#### Pipeline inventory and target construction

| Pipeline | Inputs and target | Fitting/selection and observed evidence | Assessment |
|---|---|---|---|
| Older altimeter ML, rounds 1/2 | Exact feature construction/trainer is outside the two allowed `sim/` modules. Metadata records train/held-out observation counts, fault fraction, accuracy, AUROC only. | Round 1: 2,169,141 train / 425,547 held-out, accuracy 0.7771198011, AUROC 0.8470895969. Round 2: 1,292,808 / 173,967, accuracy 0.8954054505, AUROC 0.9664996334. These are **recorded**, not independently recomputed classifier scores. | Do not infer independent episodes/sites from row counts. Raw per-run landing results can be checked separately. |
| Empirical camera model | `lit`, relative x/z errors, peak, PSR; JSON contains 300 entries per array. Two variants: default and optimistic. | Both variants have 300 result rows and five illumination-bin summaries. No split/group/hash/environment metadata in the JSON beyond descriptive `note`. | An empirical measurement/error model, not demonstrated held-out ML performance. Camera pipeline producer code is excluded by scope. |
| Scan trust v1 | Six observables: points, RMS, confidence, dx, dz, correction magnitude. Truth-only label `proposed_error_m > 10`. Auxiliary beneficial label `before - proposed > 1`. | 10,530 valid proposals, 4,881 positive labels; fit only 5,522 geometrically accepted train rows. Forest/logistic models and tuned rule. | Absolute remaining error is not correction usefulness: reducing error from 100 m to 45 m still earns a bad label. No direct truth field in the selected feature list. |
| Scan utility v2 | Normalized RMS, confidence, correction norm, AGL observation, temporal correction consistency, previous-match flag. Target clipped scalar gain minimizing instantaneous squared horizontal error, with forced gain 1 when norm <0.5 m. | 3,840 stationary poses, two uncorrected scans each; 4,172 eligible train and 2,732 eligible validation rows. 32-tree depth-8 RF regression. Policy selected on 672 development descents. | The tiny-update rule is a deliberate exception to the mathematical optimum, and the target excludes eventual touchdown velocity, fuel, and tail-risk costs. |
| Utility transfer | Frozen utility model, old classifier, hybrid policy and baseline core. Separate Site01 raster/adapter. | 810 descents: 162 configurations × five arms; three evaluation crops plus separate smoke crop. No fitting in transfer scripts. | Cross-DEM transfer within the same simulator and selected terrain class, not mission validation. |

Sources: [round 1 ML metadata](../../out/mc_round1/ml_report.json#L1-L7); [round 2 metadata](../../out/mc/ml_report.json#L1-L7); [camera models](../../out/camera_survey/cam_model.json), [optimistic variant](../../out/camera_survey/cam_model_optimistic.json); [trust features and gate](../../sim/scan_trust.py#L9-L72); [labels](../../tools/prepare_scan_trust_data.py#L85-L104); [trust trainer](../../tools/train_scan_trust.py#L95-L154); [utility target and inference](../../sim/scan_utility.py#L5-L40); [utility builder/labels](../../tools/build_utility_runner.py#L100-L129); [utility training report](../../out/scan_utility/model_v2/training_report.json#L1-L69); [transfer planning](../../tools/plan_scan_utility_transfer.py#L59-L74). Camera array lengths were computed by the supplementary audit script listed in section 3.

#### Splits and leakage checks

- **Confirmed safeguards:** preparation assigns `original/area01/area02` to train, `area03` to validation, `area04` to `retrospective_test`; run/paired samples stay in the same area. Recalculation found **zero pair groups, runs, or sites crossing splits** across 10,530 examples. Source explicitly labels all five areas previously inspected, not pristine test data. Artifact CSV hashes all match. [Preparation lines 21–22, 95–104, 118–133](../../tools/prepare_scan_trust_data.py), [manifest lines 23–53](../../out/scan_trust/20261022_preparation_v1/manifest.json).
- **Confirmed safeguards:** utility assigns the same first three areas to fitting and the remaining two to validation; recalculation found **zero runs/sites crossing**, and **zero exactly identical six-feature float32 vectors shared between train and validation**. This is an exact duplicate check, not a near-duplicate or terrain-independence guarantee. [Trainer lines 25–35](../../tools/train_scan_utility.py), [raw collection](../../out/scan_utility/20261021_203240_collect/scans.csv), [collection case metadata](../../out/scan_utility/20261021_203240_collect/summary.csv).
- **Preprocessing:** logistic scaling is fitted through a pipeline on training rows only; RF models do not fit a separate all-data normalizer. Per-run/area weights are computed from training rows only. The logistic scaler itself is not weighted even though the logistic loss receives weights; this affects equal-area weighting semantics, not split leakage. [Trust trainer lines 100–120](../../tools/train_scan_trust.py), [utility trainer lines 29–40](../../tools/train_scan_utility.py).
- **Narrow statistical support:** the v1 classifier is selected on one validation crop, utility policies on two crops, utility final evaluation on one further crop. Scan rows and repeat noise seeds are not independent terrain samples. All nine Site04 crop centers, recalculated from archived manifests, have **no overlapping axis-aligned 2.4 km crop interiors**; minimum pairwise L-infinity center separation is **2,921.875 m**. Nonoverlap does not make a common DEM's systematic errors independent. [Expanded centers](../../out/terrain_matching/20261021_183805_expanded_v2/ExpandedSites.json), [fresh centers](../../out/scan_trust/20261021_190929_closed_loop_v1/FreshSites.json), [utility plan](../../out/scan_utility/model_v2/plan.json).
- **Terrain selection conditions:** planners use a 7-cell maximum-filter slope criterion below 5°, edge clearance, and farthest-first placement. Thus conclusions are conditional on deliberately selected flat target neighborhoods and the specified error/altitude/perturbation support, not arbitrary lunar terrain. [Trust planner lines 13–34](../../tools/plan_scan_trust_tests.py), [utility planner lines 15–30](../../tools/plan_utility_tests.py), [transfer planner lines 37–58](../../tools/plan_scan_utility_transfer.py).
- **Smoke exposure differs:** v1 smoke/full share `fresh01` and initial configurations; utility eval smoke uses the same first final crop (different seed), whereas transfer reserves a separate `site01_transfer00` smoke crop. This limits “untouched terrain” wording for v1/utility after smoke, but is **not evidence of test-driven tuning**. The evaluated policies are already frozen. [Trust builder lines 45–57](../../tools/build_scan_trust_runner.py), [utility builder lines 69–83](../../tools/build_utility_runner.py), [transfer plan lines 3–30](../../out/scan_utility_transfer/20261022_091502_eval/plan.json).
- **Utility final/transfer share stress settings:** the transfer planner explicitly reuses utility evaluation error vectors; evaluator enforces altitudes 500/1500, seeds 717/818/919, variant 3 and true start (-12,16). These are new terrain outcomes with fixed stress design, not a new draw of every experimental factor. [Transfer planner lines 59–74](../../tools/plan_scan_utility_transfer.py), [verification lines 90–104](../../tools/verify_scan_utility.py).
- **Historical reuse disclosed:** transfer metadata says Site01 appeared in older sensor studies but was excluded from scan-utility fitting/selection. The old tuning log actually records Site01 warming during tuning; the old sweep table has a `site_Site01(tuned on)` tag. Therefore Site01 is not globally unseen project data. [Transfer plan line 60](../../out/scan_utility_transfer/20261022_091502_eval/plan.json#L60), [old tuning log lines 9–14](../../out/mc/log_r2_ml_tune.txt#L9-L14), [old sweeps](../../out/mc/sweeps_all.csv).

#### Tuning budget, baselines, and attribution

- Trust trains **seven fits**: one logistic (C=1), three full forests, three residual-only forests; RF=32 trees, max depth 6, minimum leaf 20, single worker. Only seed 11 participates in family selection; seeds 22/33 are validation sensitivity checks. Each of three families tries 25 score thresholds (75 total); rule tries 15 RMS × five confidence cutoffs (75). Objective is `4 * bad_accept_rate + safe_reject_rate`, where denominators are **geometric-accepted bad/safe rows**, not all proposals. Selection: full forest at **0.18**, rule RMS ≤0.5/confidence ≥0.99. Thus rule search is real and sizeable, but 75 rule settings vs 75 model-threshold settings do not demonstrate equal compute or complete hyperparameter tuning fairness. [Trainer lines 28–46, 108–143](../../tools/train_scan_trust.py), [report lines 2–5](../../out/scan_trust/20261022_model_v1/training_report.json#L2-L5).
- Selected trust validation: only 2 accepted bad proposals, but **473/1,030 safe accepted-baseline proposals rejected (45.9223%)**. Retrospective area04: zero accepted bad but **1,119/1,325 safe rejected (84.4528%)**, AUROC 0.6796444, Brier 0.3295963. These are stored classifier metrics, with label counts/splits independently checked, and their operational cost appears in fresh closed-loop outcomes below. Calibration bins are descriptive and scores are explicitly not guaranteed probabilities. [Report validation/retrospective sections, lines 6373–7003](../../out/scan_trust/20261022_model_v1/training_report.json), [gate commentary lines 27–31](../../sim/scan_trust.py#L27-L31).
- Utility trains three seed variants with fixed hyperparameters, selects **predetermined seed 11**, and reports validation MAE/RMSE for all three. Seed 11 is slightly worse in validation MAE than 22/33, consistent with the claimed fixed-seed choice. Complete development missions choose among hard/soft/hybrid policies by highest success, fewest speed violations, then lowest mean miss. There is no refit on validation and the final policy contains development-summary/model/protocol hashes. [Training lines 36–69](../../tools/train_scan_utility.py), [policy selection lines 37–48](../../tools/summarize_scan_utility.py), [frozen policy](../../out/scan_utility/20261021_204054_eval/policy.json).
- Recomputed utility validation MAE **0.212973561063268**, RMSE **0.2953292488671767**, always-gain-1 MAE **0.22101393121727675**, training-mean baseline MAE **0.2783759563730027**. The primary gain-MAE improvement over gain 1 is only **0.008040370154009**; downstream outcomes are more decision-relevant. Labels reconstructed from three distances differ from stored gain by at most **1.4335891329e-6**; 50/7,680 rows invoke the tiny-update exception. [Collection scan data](../../out/scan_utility/20261021_203240_collect/scans.csv), [forest JSON](../../out/scan_utility/model_v2/model.json), [training report lines 28–51](../../out/scan_utility/model_v2/training_report.json#L28-L51).
- Baseline ladder includes OFF, full geometric correction, simple bounded correction, previous classifier, and utility. Development results do **not** show utility dominates the bounded heuristic: bounded mean miss 27.666909 m vs chosen hybrid 28.179172 m; both 32/96 successes, hybrid 19 vs bounded 30 speed violations. Useful multi-objective tradeoff, not uniform superiority. Missing isolates include matched learned regressor alternatives, history/AGL/normalization ablations, matched constant-gain control sweeps, shuffled-label control, and closed-loop repetitions across independently trained seeds. These are absent from inspected training/selection loops, not an assertion about experiments outside this corpus. [Training loop](../../tools/train_scan_utility.py#L36-L43), [development raw results](../../out/scan_utility/20261021_203615_dev/summary.csv), [selection](../../tools/summarize_scan_utility.py#L37-L48).
- Preserve the failed export attempt: local `model_v2_export_attempt1/FAILURE.md` records a float32/double tree-threshold comparison defect repaired before deployment. The utility regression test explicitly exercises adjacent float32 inputs and a midpoint double threshold. This is a useful negative engineering result, not an alternate successful trained model. [Failure note](../../out/scan_utility/model_v2_export_attempt1/FAILURE.md#L1), [test lines 21–27](../../tests/test_scan_utility.py#L21-L27).

#### Data/map lineage

- Site01 transfer records source TIFF path/hash, raw hash, dimensions, 5 m pixel scale, tiepoint, min/max, vertical flip, and bilinear resizing to 2049². Its verifier checks source TIFF hash and terrain/map reconstruction at each archived map node using Unity-style terrain triangles plus known perturbations. All nine map files were present and these checks passed. [Planner lines 22–36](../../tools/plan_scan_utility_transfer.py), [metadata](../../out/scan_utility_transfer/20261022_091502_eval/site01_height.json), [verifier lines 75–136](../../tools/verify_scan_utility.py).
- Site04 converter lacks source path/content hash/georeferencing in its generated metadata; hardcodes 5 m/px for extent, replaces invalid elevations with the minimum, and saves min/max/resolution/extent/bad count only. Later planners hash the derived raw heightmap, which anchors that intermediate but is not a full TIFF-to-map lineage chain. The utility final folder contains no `*height*` source-raster asset; transfer does archive its source raw grid. [Converter lines 9–24](../../tools/make_heightmap.py), [planner raw hash](../../tools/plan_utility_tests.py#L50-L55), [transfer verifier](../../tools/verify_scan_utility.py#L75-L78).
- Truth and onboard maps both originate in the same raster, with imposed map shift/relief changes. Separate grids and held-out crops do not test independent sensor-model/map-production error. Improving local match consistency cannot resolve arbitrary global registration error. This is a scientific limitation, not detected truth-feature leakage. [Utility builder lines 88–95](../../tools/build_utility_runner.py), [transfer map reconstruction lines 127–136](../../tools/verify_scan_utility.py), [preparation caveat lines 127–129](../../tools/prepare_scan_trust_data.py#L127-L129).

### Inferences

- **High-priority methodological limitation:** target optimization and operational safety are misaligned. The v1 absolute-error label can reject highly beneficial partial corrections; v2 optimizes immediate position, not impact speed. The raw failures below are consistent with this mismatch but do not alone prove a causal mechanism. Acceptance should require end-task, tail, and safety evidence, not classifier AUROC or gain MAE alone. [Targets](../../tools/prepare_scan_trust_data.py#L89-L101), [utility target](../../sim/scan_utility.py#L9-L12), [transfer outcomes](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv).
- **No confirmed ordinary train/test row leakage in these two scan pipelines.** Area grouping and exact-vector checks passed; remaining dependencies are common DEM, prescribed perturbation families, repeated trajectories, and model/policy development on few crops. Historical chronology cannot be cryptographically proved by local hashes/folder dates alone. [Preparation manifest](../../out/scan_trust/20261022_preparation_v1/manifest.json), [utility policy](../../out/scan_utility/20261021_204054_eval/policy.json).

### Gaps

- The exclusive `sim/` scope excludes `sim/pipeline.py`, `sim/engine.py`, camera-producer scripts and older quick tests. Thus old altimeter feature/label construction, random/group split logic, scaling, model class, and timestamp handling remain **unverified here**; old high AUROC cannot be cleared for leakage from seven-line metadata. The coordinator must combine this audit with a permitted review of those producers before claiming all historical ML is audited. [Old metadata](../../out/mc/ml_report.json).
- No external immutable timestamp proves plan/model freeze preceded outcome inspection; source hashes establish identity, not when it was frozen. No matched-budget learning-family comparison or trained-seed closed-loop variance is supplied by the inspected loops. [Trainer reports](../../tools/train_scan_trust.py#L149-L179), [utility report construction](../../tools/train_scan_utility.py#L58-L74).

## 2. What do independently recomputed raw numerical results show?

### Takeaway

Utility improves Site04 final mean miss and reduces speed violations, without increasing successes. Frozen Site01 transfer improves pooled mean miss by 2.397 m but increases violations from 39 to 47 and fails its explicit transfer criterion; all 54 successes per policy are in the aligned-map condition. V1 learned trust is substantially worse than geometric correction. These findings come from raw per-run CSVs, not copied aggregate tables. [Utility raw](../../out/scan_utility/20261021_204054_eval/summary.csv), [transfer raw](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv), [trust raw](../../out/scan_trust/20261021_190929_closed_loop_v1/summary.csv), [transfer criterion code lines 47–49](../../tools/summarize_scan_utility_transfer.py#L47-L49).

### Cited Findings

#### Recalculation method

Read every raw `summary.csv` row. Recompute success as `touchdown && impact_vz < 2 && impact_vh < 1 && target_miss_m < 10`; speed violation as either speed at/above its limit. Pivot by `(site_id, condition, variant, altitude, error_id, seed)` (omit variant for trust) and compare identical configurations. Improvement is `control miss - learned miss`; positive favors learned. Exact ties are on recorded decimal values. Quantiles use pandas linear interpolation; “worst-decile mean” is the mean of the largest `ceil(0.1*n)` misses. Source rows: trust **2–649**, utility dev **2–673**, utility final **2–271**, transfer **2–811**. [Trust CSV](../../out/scan_trust/20261021_190929_closed_loop_v1/summary.csv), [development CSV](../../out/scan_utility/20261021_203615_dev/summary.csv), [utility CSV](../../out/scan_utility/20261021_204054_eval/summary.csv), [transfer CSV](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv).

#### Main headline table

| Batch / policy | Runs | Successes | Mean miss (m) | Median (m) | p90 (m) | Speed violations |
|---|---:|---:|---:|---:|---:|---:|
| v1 trust: OFF | 162 | 0 | 96.241686 | 96.747255 | 117.000470 | 15 |
| v1 trust: geometric | 162 | 90 | 23.001313 | 6.442112 | 45.931651 | 0 |
| v1 trust: rule | 162 | 45 | 49.956985 | 43.215460 | 103.943810 | 33 |
| v1 trust: ML | 162 | 18 | 84.695485 | 96.747255 | 117.000470 | 25 |
| Utility final: OFF | 54 | 0 | 64.397251 | 66.577740 | 94.917330 | 0 |
| Utility final: geometric | 54 | 24 | 34.639397 | 35.082320 | 87.096682 | 12 |
| Utility final: bounded | 54 | 24 | 32.670625 | 34.902925 | 85.908730 | 12 |
| Utility final: old ML | 54 | 0 | 64.397251 | 66.577740 | 94.917330 | 0 |
| Utility final: utility | 54 | 24 | 28.916501 | 23.953570 | 82.808935 | 7 |
| Site01 transfer: OFF | 162 | 0 | 64.424405 | 66.745385 | 94.989330 | 0 |
| Site01 transfer: geometric | 162 | 54 | 45.992998 | 37.999885 | 111.643460 | 39 |
| Site01 transfer: bounded | 162 | 54 | 46.322246 | 37.999885 | 124.697280 | 39 |
| Site01 transfer: old ML | 162 | 0 | 64.424405 | 66.745385 | 94.989330 | 0 |
| Site01 transfer: utility | 162 | 54 | 43.595997 | 37.668285 | 98.063123 | 47 |

All runs in this table record contact. Sources for each batch are the raw CSVs above; calculations are in the temporary audit scripts listed in section 3. Contact is an archived fact here, not a newly executed physical validation.

#### Paired effects, clusters, and multiple comparisons

| Comparison | Mean reduction (m) | Improved / worsened / tied | Additional result |
|---|---:|---:|---|
| Trust ML vs geometric | **-61.694173** | 4 / 143 / 15 | Harm occurs in every area mean; largest paired harm 116.896528 m. |
| Trust ML vs rule | -34.738500 | 18 / 84 / 60 | ML does not improve on the tuned rule either. |
| Trust ML vs OFF | +11.546200 | 28 / 0 / 134 | Better than no correction in some cases is insufficient against geometric. |
| Utility final vs geometric | **+5.722897** | 41 / 7 / 6 | 16.521352% mean reduction; 17 improvements >1 m, one harm >1 m; largest harm 17.385580 m. |
| Utility final vs bounded | +3.754125 | 40 / 8 / 6 | Largest paired harm 34.085760 m. |
| Transfer utility vs geometric | **+2.397001** | 105 / 39 / 18 | 5.211665% mean reduction; 38 improvements >1 m, 14 harms >1 m; largest harm 35.704100 m. |
| Transfer utility vs bounded | +2.726249 | 103 / 41 / 18 | Crop03 mean worsens by 2.747259 m. |

Source: independent pivots from [trust raw](../../out/scan_trust/20261021_190929_closed_loop_v1/summary.csv), [utility raw](../../out/scan_utility/20261021_204054_eval/summary.csv), [transfer raw](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv). These are paired recorded configurations, not independent missions.

- Utility final speed discordance: five geometric-only violations, zero utility-only; success count unchanged. Transfer: **11 utility-only violations, three geometric-only**; **zero success-discordant pairs**, not merely equal total success counts. [Utility raw](../../out/scan_utility/20261021_204054_eval/summary.csv), [transfer raw](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv).
- Transfer per-area mean reductions vs geometric: **+1.955448, +8.377019, -3.141464 m**. Remove area02 and the remaining mean is **-0.593008 m**. This is why 162 paired configurations cannot be represented as 162 independent terrain tests. [Transfer raw site grouping](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv).
- Supplementary conditional 5,000-resample paired bootstrap, RNG seed 8841, gives utility-final [**2.150461, 9.983922**] m and transfer [**0.375806, 4.367253**] m. These are **descriptive conditional intervals on the observed fixed crops**, not cross-site uncertainty. A deliberately illustrative exact sign-flip calculation on the three transfer crop means gives two-sided **p=0.75**, assuming exchangeable independent crop effects; even that assumption is not justified for independent DEM claims. The contrast demonstrates sensitivity to inferential unit; it is not an additional confirmatory hypothesis test. [Raw transfer data](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv), [existing trust bootstrap explicitly conditional, lines 86–94](../../tools/summarize_scan_trust.py#L86-L94).
- Existing trust summarizer computes three unadjusted conditional 95% intervals; utility/transfer summarize four controls without inferential uncertainty. This is acceptable as descriptive exploration, but simultaneous significance claims would need a prespecified primary comparison or multiplicity control (e.g., Holm). A single planned transfer compound criterion exists and is **false** on the raw numbers: lower mean, **not** fewer violations, same successes. [Trust comparison loop](../../tools/summarize_scan_trust.py#L86-L98), [utility comparisons](../../tools/summarize_scan_utility.py#L53-L61), [transfer criterion](../../tools/summarize_scan_utility_transfer.py#L40-L52).

#### Tail and failure slices

| Transfer crop | Geometric mean / utility mean (m) | Geometric / utility violations | Successes per policy |
|---|---:|---:|---:|
| site01_transfer01 | 61.546303 / 59.590855 | 18 / 15 | 18/54 |
| site01_transfer02 | 41.108153 / 32.731133 | 18 / 18 | 18/54 |
| site01_transfer03 | **35.324538 / 38.466001** | **3 / 14** | 18/54 |

Source: raw [transfer summary](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv), grouped by site/arm independently.

- Transfer aligned condition: 54/54 successes for geometric/bounded/utility; utility mean 0.630069 vs geometric 0.827610 m. **Map shift:** 0/54 successes for both, utility mean 54.966696 vs geometric 54.986519 m. **Positive relief:** 0/54 successes for both; utility mean 75.191226 vs geometric 82.164864 m, but **47 vs 39 speed violations**, all pooled violations located here. Thus the transfer means improve largely inside a failure regime rather than converting failures to successful landings. [Transfer raw](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv).
- Transfer worst-decile miss means: utility **124.670308 m**, geometric **129.944735 m**, bounded **143.350229 m**. Max misses: 147.5938 / 148.8462 / 151.5858 m respectively. Utility p95=134.71325 m, geometric=141.98112 m. Max lateral impact improves (6.208023 vs 8.239988 m/s) even while the number violating 1 m/s increases. Both incidence and severity must be reported. [Transfer raw](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv).
- Utility final p95 miss **91.54875 m**, maximum **95.00204 m**, and worst-decile mean **92.333927 m** are identical for geometric/bounded/utility. Mean improvement does not eliminate the shared worst tail. Utility still has seven speed violations, max lateral speed **3.218744 m/s**. [Utility raw](../../out/scan_utility/20261021_204054_eval/summary.csv).
- Example transfer utility worst miss: `descent_site01_transfer01_u1_relief_positive_v3_1500_818_utility`, miss **147.5938 m**, lateral impact **3.877343 m/s**, vertical **1.860888 m/s**. Its neighboring error configurations fail similarly. [Raw result](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv), [trajectory](../../out/scan_utility_transfer/20261022_091502_eval/descent_site01_transfer01_u1_relief_positive_v3_1500_818_utility.csv).

#### Older numerical evidence inventory and independently checked subsets

- Early terrain v1: **81 cases = 27 stationary + 54 descents**, 1,017 scan rows. Descent OFF 0/27 successes, mean miss 70.311399 m; ON 9/27, 33.716396 m. Expanded terrain: **810 cases = 270 stationary + 540 descents**, 10,530 scans. OFF 0/270, 93.939178 m; ON 93/270, 43.089765 m. These are recalculated raw aggregates; v1/expanded contact semantics differ, so cross-batch changes are not an isolated algorithm effect. [V1 raw](../../out/terrain_matching/20261021_181450_v1/summary.csv), [expanded raw](../../out/terrain_matching/20261021_183805_expanded_v2/summary.csv), [summarizer contact caveat lines 113–115](../../tools/summarize_expanded_terrain_tests.py#L113-L115).
- Each older round has **55 aggregate rows**, 11 judges × five scenarios, 500 runs each (**27,500 reported runs**), but **44 per-run files**, organized under four prefixes (`cliff`, `shadow`, `delayed`, `altimeter`). The two cliff scenarios are not separately named in per-run archives. Round-2 `cliff_ml.csv` recomputes **380/500=76.0%**, matching `cliff + faults`; the separate `cliff (HAKUTO-R)` summary is **379/500=75.8%**. Thus the inspected per-run archive cannot independently reconstruct both scenario-specific ML results. A filename collision/overwrite is a plausible cause, **not source-proven within scope**. [Round-2 aggregate](../../out/mc/main_results.csv), [raw cliff ML](../../out/mc/per_run/cliff_ml.csv), [round-1 aggregate](../../out/mc_round1/main_results.csv), [round-1 raw cliff ML](../../out/mc_round1/per_run/cliff_ml.csv).
- Recomputed older round-2 ML successes: faulted cliff **380/500**, shadow **119/500**, delayed **2/500**, altimeter dropout **121/500**. Max miss by those files: **1040.751452, 661.484187, 1723.098352, 1906.571866 m**. Round-1 corresponding ML successes: **230, 125, 119, 43** out of 500. This does not revalidate “success” against old simulator criteria; raw files show successful runs can have miss far above 10 m, so those metrics must not be equated with the newer target-success definition. [Round-2 raw files](../../out/mc/per_run/), [round-1 raw files](../../out/mc_round1/per_run/), [explicit example: round-2 cliff CSV lines 4–5](../../out/mc/per_run/cliff_ml.csv#L4-L5).
- Other round-2 stored experiments: tuning table **nine settings**; `sweeps_a.csv` 12 rows/3,600 reported runs; `sweeps_sun.csv` 18/3,600; `sweeps_all.csv` 55/14,700; camera policies 16/8,000; exploratory timestamps 12/6,000. These sets may overlap—**do not sum them into a total independent experimental budget**. Tables have summary metrics/tags, not complete per-trial hashes/split/environment manifests. [Tuning](../../out/mc/tuning.csv), [sweeps](../../out/mc/sweeps_all.csv), [camera policies](../../out/mc/camera_policies.csv), [timestamp study](../../out/mc/exploratory_timestamps.csv).
- `out/runs/runs_summary.csv` currently includes one archived touchdown record and one **stopped** record at zero duration/102500 m initial AGL; it is also a pre-existing modified tracked file. Do not count the stopped record as a completed landing trial. No physical interpretation was audited here. [Rows 1–3](../../out/runs/runs_summary.csv#L1-L3).

### Inferences

- **High severity, confirmed negative result:** transfer does not meet its chosen combined criterion. Claiming transfer safety improvement from mean miss or maximum impact alone would contradict the incidence metric. Remedy: retain this batch as negative transfer evidence and preregister a new validation/test partition before changing the policy. Gate: no worse primary safety incidence under a declared noninferiority bound, alongside position and worst-area results. [Criterion implementation](../../tools/summarize_scan_utility_transfer.py#L47-L49), [raw outcomes](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv).
- **High severity, limitation:** a one-crop final test plus one transfer DEM cannot support broad generalization; conditional intervals should remain explicitly conditional. Gate: independently sourced DEM/site clusters with held-out acquisition lineage and prespecified cluster-level inference; do not use scan count as sample size. [Area plans](../../out/scan_utility/model_v2/plan.json), [transfer plan](../../out/scan_utility_transfer/20261022_091502_eval/plan.json).

### Gaps

- No new physics/contact trial or model fitting was performed. Current raw verification establishes internally consistent recorded outcomes, not externally calibrated sensor/dynamics realism. Old AUROC cannot be recomputed without row-level labels/predictions/training inputs and allowed producer review. No claim of mission reliability or causal mechanism follows from these calculations.

## 3. How strong are verification, tests, artifact preservation, and reproduction?

### Takeaway

Sixteen explicitly discovered Python tests pass; five existing dataset verifications pass; transfer's 1,668 indexed files hash correctly; additional independent inference and trajectory-endpoint checks pass. Nonetheless default test discovery runs **zero tests**, old raw scenario coverage is incomplete, malformed-input/parity-helper defects remain, and the work is not reproducible from the current Git commit alone because the newer code/results are untracked and several older datasets/models are intentionally ignored.

### Cited Findings

#### Actually executed in this audit

Working directory for all commands: `D:\newprj`. Audit scripts were created using `apply_patch` under `C:\Users\ADMIN\AppData\Local\Temp\opencode`; project result writers were suppressed during verifier execution using `unittest.mock.patch` on `Path.write_text`/`Path.write_bytes`. Assertions, readers, hashes, inference, and numeric checks were executed normally. Suppressed writes: existing run `VERIFICATION.md` files and transfer `RUNTIME_FREEZE.json`. This distinguishes actual assertion execution from merely reading historical “PASS” files.

**Command 1:** `python -B -m unittest discover -s tests -v`

```text
test_altimeter_task_and_schema_rejected (test_scan_trust.ScanTrustTests.test_altimeter_task_and_schema_rejected) ... ok
test_feature_count_and_classes_rejected (test_scan_trust.ScanTrustTests.test_feature_count_and_classes_rejected) ... ok
test_geometric_reject_cannot_be_promoted (test_scan_trust.ScanTrustTests.test_geometric_reject_cannot_be_promoted) ... ok
test_learned_veto_and_accept (test_scan_trust.ScanTrustTests.test_learned_veto_and_accept) ... ok
test_no_model_preserves_gate (test_scan_trust.ScanTrustTests.test_no_model_preserves_gate) ... ok
test_nonfinite_features_fail_closed (test_scan_trust.ScanTrustTests.test_nonfinite_features_fail_closed) ... ok
test_nonfinite_scores_fail_closed (test_scan_trust.ScanTrustTests.test_nonfinite_scores_fail_closed) ... ok
test_only_runtime_features (test_scan_trust.ScanTrustTests.test_only_runtime_features) ... ok
test_geometric_rejection_and_nonfinite_fail_closed (test_scan_utility.UtilityTests.test_geometric_rejection_and_nonfinite_fail_closed) ... ok
test_harmful_update_zero_gain (test_scan_utility.UtilityTests.test_harmful_update_zero_gain) ... ok
test_late_correction_is_bounded (test_scan_utility.UtilityTests.test_late_correction_is_bounded) ... ok
test_overshoot_has_partial_optimum (test_scan_utility.UtilityTests.test_overshoot_has_partial_optimum) ... ok
test_threshold_comparison_preserves_double_precision (test_scan_utility.UtilityTests.test_threshold_comparison_preserves_double_precision) ... ok
test_tiny_update_not_punished (test_scan_utility.UtilityTests.test_tiny_update_not_punished) ... ok
test_useful_but_not_absolute_accurate_update_retained (test_scan_utility.UtilityTests.test_useful_but_not_absolute_accurate_update_retained) ... ok
test_wrong_task_rejected (test_scan_utility.UtilityTests.test_wrong_task_rejected) ... ok

----------------------------------------------------------------------
Ran 16 tests in 0.003s

OK
```

Sources: [trust test suite](../../tests/test_scan_trust.py#L1-L76), [utility test suite](../../tests/test_scan_utility.py#L1-L29). Trust tests use a score stub, not a trained classifier; utility includes one synthetic tree fixture, label examples and routing bounds. Passing these tests is not an experiment-level performance test.

**Command 2:** `python -B -m unittest discover -v`

```text
----------------------------------------------------------------------
Ran 0 tests in 0.000s

NO TESTS RAN
```

The `tests/` directory has only the two test modules plus cache, no `__init__.py`; no `pytest.ini`, `pyproject.toml`, `setup.cfg`, `setup.py`, `tox.ini`, dependency requirement file, environment.yml, Pipfile, uv/Poetry lock or `.github/` workflow was found by dedicated glob searches. Fix the canonical test entry point/CI and assert a nonzero expected collection count. [Test directory](../../tests/).

**Environment command:** `python -B -c "import sys,numpy,pandas,scipy,sklearn; print('python',sys.version); print('numpy',numpy.__version__,'pandas',pandas.__version__,'scipy',scipy.__version__,'sklearn',sklearn.__version__)"`

```text
python 3.13.15 (tags/v3.13.15:4061bc4, Aug  5 2026, 13:05:39) [MSC v.1944 64 bit (AMD64)]
numpy 2.5.2 pandas 2.3.3 scipy 1.18.1 sklearn 1.9.0
```

These are **audit-time installed versions**, not recovered original training versions. Both actual utility final and transfer environment files record **Unity 6000.3.24f1**, Intel i7-14700HX, WindowsEditor, DT=0.05. Do not attribute their transfer difference to an observed editor-version change: these two files agree. [Utility environment](../../out/scan_utility/20261021_204054_eval/environment.txt#L1-L6), [transfer environment](../../out/scan_utility_transfer/20261022_091502_eval/environment.txt#L1-L6).

**Computation commands:**

```text
python -B "C:\Users\ADMIN\AppData\Local\Temp\opencode\lantern_experiment_audit.py"
python -B "C:\Users\ADMIN\AppData\Local\Temp\opencode\lantern_audit_supplement.py"
python -B "C:\Users\ADMIN\AppData\Local\Temp\opencode\lantern_terminal_checks.py"
```

All three completed successfully. They use raw data/model JSON rather than loading pickle objects. Significant exact outputs are preserved below and the numerical sections above.

| Existing verifier actually executed | Cases / scan rows | Result |
|---|---:|---|
| `tools.summarize_scan_trust.verify` on `20261021_190929_closed_loop_v1` | 648 / 12,312 | PASS |
| `tools.verify_scan_utility.verify` on collection `20261021_203240_collect` | 3,840 / 7,680 | PASS |
| Same on development `20261021_203615_dev` | 672 / 12,768 | PASS |
| Same on utility final `20261021_204054_eval` | 270 / 4,320 | PASS |
| Same on transfer `20261022_091502_eval` | 810 / 13,011 | PASS |

Sources: [trust verifier lines 23–64](../../tools/summarize_scan_trust.py#L23-L64), [utility verifier lines 14–142](../../tools/verify_scan_utility.py#L14-L142). **Not rerun:** Unity parity production, smoke datasets, Unity self-checks, older simulator smoke/quicktests, original training fits, or terrain batch summarizers. Archived parity report `passed=true, rows=7680, max_score_difference=2.2204460492503131E-16` is historical Unity evidence; the separate Python checks below are newly executed. [Archived transfer parity](../../out/scan_utility_transfer/20261022_091502_eval/parity_report.json#L1).

Additional newly executed checks:

```text
trust_preparation_hashes: features.csv=true, labels.csv=true, groups.csv=true, shadow_decisions.csv=true
trust_training_hashes: model.json=true, model.pkl=true, parity.csv=true, predictions.csv=true, rule.json=true
utility_training_hashes: source_scans=true, source_summary=true, plan=true, protocol=true, model=true
transfer_artifact_hash_check: entries=1668, missing=[], mismatched=[]
utility_dev portable inference: 12768 rows, max difference=7.771561172376096e-16
utility_eval portable inference: 4320 rows, max difference=5.551115123125783e-16
transfer portable inference: 13011 rows, max difference=6.106226635438361e-16
trust classifier replay: 12312 rows, max difference=8.881784197001252e-16
transfer old-classifier replay: 13011 rows, max difference=6.661338147750939e-16
trust terminal trace: max miss difference=5.466404111587053e-05 m; time difference=0; fuel difference=0
transfer terminal trace: max miss difference=7.569898585302326e-05 m; time difference=0; fuel difference=0
```

All paired experiment datasets checked have zero scan IDs missing run metadata, zero runs without scans, and zero scan/run arm-label disagreements. Terminal trace checks read **all 648 trust and all 810 transfer trajectory CSVs**, comparing final `hypot(x,z)`, time and fuel with each raw run summary. They do not independently reconstruct contact-relative impact speed. All transfer files, including cloud CSVs, were hashed; clouds were not geometrically reprocessed. [Raw scans](../../out/scan_utility_transfer/20261022_091502_eval/scans.csv), [hash index](../../out/scan_utility_transfer/20261022_091502_eval/ARTIFACT_SHA256.json), [example trace schema](../../out/scan_utility_transfer/20261022_091502_eval/descent_site01_transfer01_u0_aligned_v3_500_717_utility.csv).

#### Confirmed defects and verification limitations, with remedies/gates

| ID / severity | Type and evidence | Remedy / acceptance gate |
|---|---|---|
| R1 **High** | **Reproduction limitation:** current commit does not contain newer scan code/tests/results; ignored older model and source rasters also absent from a clean checkout. Local files are present. See Git evidence below. | Publish an immutable release/commit of intended code, protocols, tests and manifest; package large artifacts externally with checksums, retrieval URLs and license/source metadata. Gate: clean-machine reproduction of all reported tables from a named release, without the author's existing workspace. |
| R2 **High** | **Confirmed archive coverage defect:** two cliff scenario summaries but one cliff per-run prefix; ML file matches faulted cliff, not plain cliff. Loss mechanism is unverified. | Use collision-proof `(round, scenario_id, judge, config_hash)` filenames and fail on existing outputs; recover or rerun the missing scenario with original environment. Gate: every aggregate row maps uniquely to an immutable raw dataset whose metrics recompute. |
| R3 **Medium** | **Confirmed test-discovery failure:** default unittest discovery runs zero tests; explicit `-s tests` runs 16. | Configure canonical runner/CI and nonempty collection check. Gate: fresh checkout invokes documented command and collects/passes expected suites. |
| R4 **Medium** | **Confirmed float comparison defect in trust exporter/scorer:** `tools/train_scan_trust.py:81` compares NumPy float32 feature directly with Python double threshold. With feature=1.000000238418579 and threshold=1.0000001788139343, `portable_score` returns left leaf **0.0**, expected right leaf **1.0**. Utility has the scalar cast and regression test already. No observed discrepancy on the 12,312 trust or 13,011 transfer archived classifier inputs. | Cast the feature to Python float before comparison and add the midpoint regression to trust tests. Gate: parity on boundary-generated inputs plus all existing archived fixtures; do not claim current production C# is defective from this Python-helper probe. |
| R5 **Medium** | **Confirmed malformed-input behavior:** trust `decide([None]*6,...)` raises TypeError outside its inference exception guard; utility `policy_gain('bounded',1,nan,20)` returns **1.0**, `policy_gain('utility_hybrid',1,100,nan)` returns **0.05**; empty forest causes ZeroDivisionError. Valid archived matrices passed, so this is a boundary robustness issue, not an explanation of observed results. | Validate numeric type/finiteness/range of all runtime inputs and full model structure; decide whether invalid caller input should reject or raise. Gate: property/negative tests for NaN/inf/nonnumeric, empty/malformed trees, invalid indices, and threshold edges. |
| R6 **Medium** | **Verifier limitation:** most non-transfer checks use arm sets without exact per-configuration arm multiplicity, check file existence not contents, rely on a historical parity boolean, and do not replay model predictions on new logged rows. Transfer uniquely adds prediction, expected Cartesian key set, exact five-arm count, runtime freeze, source terrain and baseline equality checks. Hash strings are searched in a text record, not parsed into an exact path-to-digest binding. | Adopt transfer-strength checks for every stage, strict schemas/dtypes, exact count/cardinality, all row foreign keys, and model replay; verify trajectory endpoints/contact event records and content hashes. Gate: mutation tests deleting/duplicating/misrouting cases or altering predictions must fail. |
| R7 **Medium** | **Verifier limitation:** transfer terrain verification iterates `folder.glob('map_*.bin')` without asserting required map filename set/count. Missing all maps could skip this loop. This audit independently saw all nine maps and checked the whole artifact index, so no missing-map defect was observed. | Assert required map set and verify manifest completeness before iterating. Gate: deleting one expected map causes failure. |
| R8 **Medium** | **Metadata limitation:** training reports omit full Python/library environment, dirty-tree/commit state, resolved estimator defaults, total hardware/tuning cost; model v2 lacks a complete artifact hash index (has key input/model hashes). Absolute `D:\newprj` source paths reduce portability. | Record an automatic machine-readable run manifest with relative paths, complete parameters, all seeds, environment lock, commit/tree hash, data versions and elapsed/compute costs. Gate: source/config/data manifest suffices to refit or explain any numerical difference. |
| R9 **Medium** | **Methodological limitation:** row-level validation weighting/uncertainty differs from equal-area training weights; many outputs and comparisons, one-crop evaluation, common DEM and single deployed fit. | Prespecify primary deployment metric, aggregate at appropriate run/crop/DEM levels, track all trials, use held-out DEMs, matched tuning and repeated fitted seeds. Gate: confirmatory claims use the declared inference unit and multiplicity rule. |
| R10 **Medium** | **Lineage limitation:** Site04 converter does not preserve TIFF provenance/georeferencing hash in metadata; raw-derived hashes are stronger than nothing but do not anchor the entire source transformation. | Record source URI/checksum, CRS/tiepoint/pixel-center convention, nodata and conversion/version parameters. Gate: raw terrain regenerated byte-identically or within declared quantization tolerance from distributed source. |

Code evidence: R4 [trust scalar comparison](../../tools/train_scan_trust.py#L70-L84), [utility corrected comparison](../../sim/scan_utility.py#L24-L29), [existing boundary test](../../tests/test_scan_utility.py#L21-L27); R5 [trust guard](../../sim/scan_trust.py#L54-L70), [utility routing](../../sim/scan_utility.py#L33-L40), [forest traversal](../../sim/scan_utility.py#L15-L30); R6/R7 [trust verifier](../../tools/summarize_scan_trust.py#L23-L63), [utility verifier](../../tools/verify_scan_utility.py#L14-L141); R8 [trust report construction](../../tools/train_scan_trust.py#L149-L179), [utility report construction](../../tools/train_scan_utility.py#L58-L74); R9 [trust weighting/selection](../../tools/train_scan_trust.py#L100-L141), [utility selection](../../tools/summarize_scan_utility.py#L37-L48); R10 [converter](../../tools/make_heightmap.py#L9-L24). R1–R3 use the recorded commands and file inventories in this section. Severity denotes impact on research defensibility/boundary reliability, not an established physical hazard classification.

Other verification scope notes: checks are Python `assert`s and therefore should not be run with optimization (`-O`). Current audit used `-B`, which suppresses bytecode writes and leaves assertions active. Verification success-label reconstruction trusts logged contact/impact measurements; convex-combination target checks independently derive algebra from three archived distances but all distances still originate from the same run recorder. These are consistency checks, not independent physical ground truth. [Verifier lines 27–35, 45–48](../../tools/verify_scan_utility.py#L27-L48).

#### Git and artifact preservation evidence

Executed `git status --short`, `git log --oneline -5`, `git ls-files sim tools tests data .gitignore .github out/mc/ml_model.pkl out/scan_trust out/scan_utility out/scan_utility_transfer`, and `git check-ignore -v` on named model/data paths. At inspection HEAD short hash was **5853a84** (`Add full chronological project log (markdown and PDF)`); recent earlier commits include `b4c2a2c`, `ca61ea6`, `e406319`, `6bbda5c`. Working tree was already dirty: README/docs, `out/runs/runs_summary.csv` modified, newer scan modules/tests/tooling/output directories untracked. No commits, staging or config changes were made.

Important exact ignore output:

```text
.gitignore:14:data/*.tif    data/Site01_final_adj_5mpp_surf.tif
.gitignore:14:data/*.tif    data/Site04_final_adj_5mpp_surf.tif
.gitignore:21:out/mc/*.pkl  out/mc/ml_model.pkl
.gitignore:20:out/cache/   out/cache
```

`git check-ignore` printed **no match** for `out/scan_utility/model_v2/model.pkl` or `out/scan_trust/20261022_model_v1/model.pkl`: these newer models are **untracked, not ignored by that old-model rule**. `data/*.tiff` and camera survey images are also explicitly ignored. All four named TIFFs were locally present; old `out/mc/ml_model.pkl`, newer model JSON/pickles, cache arrays and raw runs were locally present. **Do not write “models/data do not exist.”** The precise implication is that cloning the currently committed repository does not carry these local assets and cannot reproduce the later experiment tables without another artifact channel. [.gitignore lines 13–27](../../.gitignore#L13-L27), [local data directory](../../data/), [model folders](../../out/scan_utility/model_v2/), [trust model folder](../../out/scan_trust/20261022_model_v1/).

Trust recorded model JSON SHA-256: `74ed4350c35c30c4f8eba80f2413f61551fb6ee1b9f9e402cf991880c5f4a466`. Utility: `eda1c7830f69b76cffd6ded430a5e6ddcd70210ed411fcf4f902c62e46f0dece`. Transfer source Site01 TIFF: `3ba7b97cb00a2bcf21189c3aeb535f65afc21207154ab9f0d43c5bdc1f7e747e`; derived raw: `90b595b331f0e6406e65555273b78da0cdb5e7ba910c460fadb0495a67fb1670`. These hashes were verified in the executed checks. [Trust report lines 7017–7023](../../out/scan_trust/20261022_model_v1/training_report.json#L7017-L7023), [utility report line 52](../../out/scan_utility/model_v2/training_report.json#L52), [transfer plan lines 47–57](../../out/scan_utility_transfer/20261022_091502_eval/plan.json#L47-L57).

#### Inspected versus excluded assets

| Asset set | Inspection depth |
|---|---|
| `sim/scan_trust.py`, `sim/scan_utility.py` | Full source, contract tests, additional numerical/boundary probes. |
| `tools/prepare_scan_trust_data.py`, `train_scan_trust.py`, `train_scan_utility.py` | Full source, archived manifests/reports, input/output hashes, split/target/feature/inference recalculation; no retraining. |
| `tools/plan_expanded_terrain_tests.py`, `plan_scan_trust_tests.py`, `plan_utility_tests.py`, `plan_scan_utility_transfer.py`, `make_heightmap.py` | Full source; archived crop metadata and crop nonoverlap computation; no rerun that regenerates datasets. |
| `tools/build_scan_trust_runner.py`, `build_utility_runner.py`, `build_scan_utility_transfer.py` | Full Python generator source, including embedded experiment-construction strings. Generated C# algorithms not reviewed. |
| `tools/summarize_terrain_experiment.py`, `summarize_expanded_terrain_tests.py`, `summarize_scan_trust.py`, `summarize_scan_utility.py`, `summarize_scan_utility_transfer.py`, `verify_scan_utility.py` | Full source. Five existing verification functions executed as listed; report/plot-producing main functions not rerun. |
| `tests/` | Both files fully read; 16 tests executed; default discovery failure checked. Existing cache ignored. |
| `out/scan_trust/20261022_preparation_v1`, `20261022_model_v1` | All prepared feature/group/label tables joined; source manifest read; JSON report/model, artifact hash checks. Pickles hashed, not deserialized. |
| `out/scan_trust/20261021_190929_closed_loop_v1` | All raw summary/scans and all 648 trajectory CSVs; verifier, model replay and endpoints; frozen source identity hashed without C# source review. Smoke folder inventoried, not rerun. |
| `out/scan_utility/20261021_203240_collect`, `20261021_203615_dev`, `20261021_204054_eval`, `model_v2` | Raw summaries/scans, training metadata, portable forest, plan/policy/protocol hashes, verifiers and inference calculations. Full utility trajectories/cloud content not reprocessed; verifier checks presence. Three smoke folders inventoried only. |
| `out/scan_utility/model_v2_export_attempt1` | Failure note fully read; no alternate model asserted to exist. |
| `out/scan_utility_transfer/20261022_091502_eval` | All raw summaries/scans, all 810 trajectories, all nine maps, raw terrain + source TIFF hash, model/policy/runtime snapshots, complete 1,668-file index verified. Sparse clouds hashed, not interpreted. Smoke folder inventoried only. |
| `out/terrain_matching/20261021_181450_v1`, `20261021_183805_expanded_v2` | Raw summaries/scans numerically aggregated; expanded site manifest; core hash used by verifiers. Earlier smoke folders inventoried only. |
| `out/mc`, `out/mc_round1` | Main aggregate tables parsed; model/config/tuning metadata; four ML per-run CSVs per round fully numerically processed; per-run filenames inventoried; round-2 sweep/camera-policy/timestamp tables counted; selected training log lines read. Other judges' raw per-run files not numerically audited. |
| `out/camera_survey` | Both empirical model JSONs parsed, result and summary table shapes/fields examined; image directory inventoried, no image/matcher rerun. |
| `out/cache`, `out/site04`, `out/runs` | Directory inventory, runs-summary rows and Git treatment; caches/shadow grid not recomputed, historical flight trace not audited. |
| `out/plots*`, `out/replay*`, `out/literature`, figures/screenshots, `reports/`, `deliverables/`, art | Excluded as derived visualization/docs/other agents' scope. |
| `tools/build_lander_art.py`, `make_report_pdfs.py`, `render_site.py` | Excluded rendering/report production, not part of selected ML experiment/training/verification chain. |
| All other `sim/`, C# and physics source; `docs/`/README claims | Excluded by assignment. Protocol contents were not evaluated for claims, but artifact protocol hashes and references were inspected. No graphify graph or AGENTS.md found; no graph was built. |

### Inferences

- The strongest currently supported research contribution is a **bounded, reproducible local comparison with negative transfer/safety evidence**, not general lunar-landing reliability. Existing data preservation is materially stronger for the recent transfer batch than older MC outputs; publication readiness should focus on packaging, exact experimental identity, independent-site inference and failure analysis rather than more correlated scan rows. [Transfer artifact index](../../out/scan_utility_transfer/20261022_091502_eval/ARTIFACT_SHA256.json), [old report metadata](../../out/mc/ml_report.json), [transfer raw](../../out/scan_utility_transfer/20261022_091502_eval/summary.csv).
- Practical next acceptance gates: (1) immutable clean-checkout reproduction and nonempty CI; (2) verifier mutation/boundary tests; (3) recover unique old raw scenario identity; (4) prespecified independent-DEM test with safety incidence and worst-area/tail criteria; (5) matched baseline/ablation and repeated-model-seed comparisons. Existing final and transfer outcomes must remain visible and cannot become “untouched test” after policy changes.

### Gaps

- Original Python training environment and full dirty-tree snapshot cannot be reconstructed from these reports alone. Hash equality does not validate timestamps, acquisition provenance, task realism or external ground truth. The audit scripts live in approved temporary storage and should be copied into a future reproducibility release if long-term reuse is needed; this requested note preserves commands, methods, exact principal outputs and source paths.
- No broad deletion/overwrite or repo code edit was made by this audit; other agents may concurrently add their notes. The new deliverable for this scope is this file.
