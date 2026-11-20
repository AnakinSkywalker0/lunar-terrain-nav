# Guidance ablation, relief sweep and classical-gate baseline: results (8 Nov 2026)

All runs were headless Unity (6000.3.24f1, `-batchmode -nographics`), 3-DOF PhysX, seed 717 (sensor noise only).
Protocol: [GUIDANCE_ABLATION_PROTOCOL.md](GUIDANCE_ABLATION_PROTOCOL.md). Full tables: [GUIDANCE_ABLATION_TABLES.md](GUIDANCE_ABLATION_TABLES.md).
Unit of analysis is the terrain area (12 Site01 areas); per-run confidence intervals are not used.

| Stage | Descents | Wall time | Status |
|---|---:|---:|---|
| `eval_g1` (3 transfer areas) + `eval_wide` (9 new areas): guidance x arms x 5 conditions | 5,400 | 243 s + 583 s | pre-registered (G1, G2) |
| `eval_g3`: classical Kalman + chi-square gate, 12 areas | 1,800 | 236 s | a-priori constants, added after a 3-area look (Addendum A) |
| `eval_sweep`: unmodelled-relief amplitude 0.5-16 m x 4 shapes | 10,800 | 1,429 s | exploratory (Addendum B) |
| `eval_imu`: accelerometer-bias stress | 3,888 | 510 s | exploratory (Addendum B) |

Validation: with baseline guidance the new runner reproduced the frozen transfer runner's 22 Oct smoke outcomes exactly
(12 matched cases, zero difference in miss, velocities, fuel, matches). Regenerating the runner twice more reproduced its own
45-case smoke exactly. Recomputed contact positions equal the recorded `target_miss_m` in every analysed run.

## Findings

**F1. Scoring frame: the original "0/N under map shift" was a scoring artifact.** A 38 m map offset cannot be seen from the map;
scoring in the map frame (target chosen in the map) turns 0% into 67-71% success at 10 m for every correcting arm (T1, T3).
This is a change of metric, not an improvement. Figure: `docs/figures/frame_artifact.png`.

**F2. Realistic small horizontal map-tie errors are not a problem in this simulator.** With a 3 m or 8 m map shift, every correcting arm
succeeds in 100% of cases in both frames, with about 1 m mean miss and zero speed violations (T3). The remaining map-shift failures
(29%) are concentrated in one start error (u2, about 95 m): success 12% versus 100% for u0 and u1. Likely cause (inference, not tested):
start error plus the 31 m shift component reaches the matcher's +/-128 m search window (`TerrainNavigationCore.cs:57`).

**F3. Speed violations occurred only when fixes were wrong.** Under map shifts and tie errors there were zero violations for every arm,
including fixes of 38 m and start-error corrections up to about 95 m. In these runs the large correct fixes were applied early in the
descent; a large correct fix arriving late (the original authority hypothesis) was not tested directly. Violations appear only under
unmodelled relief (T2: geometric 0.64 of runs, utility 0.68), where about half of the matcher's accepted fixes are wrong.

**F4. Pre-registered verdicts.**
- G1 (is it a controller artifact?), arm `geometric`, changed terrain: terminal-phase guidance cut the median per-area violation rate
  0.83 -> 0.58 (-30%, "mixed"); braking-curve guidance 0.83 -> 0.83 (0%, "persists"). For the learned `utility` arm the terminal
  phase helped more (0.83 -> 0.33). Better guidance helps partly; it does not remove the problem.
- G2 (authority-aware gate): **not supported.** Violations fell in 2 of 12 areas and rose in 1 (changed terrain), zero elsewhere;
  mean violation 0.53 vs 0.64. The map-miss condition held but the violation condition failed.
- Doing nothing (`off`) never violates speed limits but lands 64 m off; under changed terrain every simple correcting arm lands farther
  (about 85-100 m) than doing nothing (T2).

**F5. A classical Kalman + chi-square consistency gate beat the geometric rule and the learned policy under changed terrain.**
(constants fixed a priori: start variance (100 m)^2, fix variance (2 m)^2, process noise 0.05 m^2/s, 99% gate.)
- Changed terrain, 12 areas (T6): violation 0.10 vs 0.64 (geometric) and 0.68 (utility); mean map miss 29 m vs 100 m and 85 m;
  success at 10 m 54% vs 0%.
- Relief sweep (T7, T8): paired over 12 areas, the gate has lower mean miss than geometric and utility at every amplitude from 0.5 m
  (11/12 and 10/12 areas at 0.5 m; 12/12 at 4 m and above for utility, 11-12 for geometric). Violation rate stays 0.00 through 8 m
  and is 0.11 at 16 m, against 0.54 (geometric) and 0.48 (utility) at 8 m.
- The learned Site04-trained policy is, on this evidence, close to geometric matching: it did not beat a ten-line classical gate.
- Detection statistics (T6 companion, `analysis_gates/gate_detection.csv`): under changed terrain about 54% of matcher-accepted fixes are
  wrong (>10 m). The gate applied 14% of the wrong ones and blocked 5% of the useful ones; geometric applied all of both. Labels depend
  on each arm's own trajectory and the map-shift rows are not interpretable (shifted fixes are "wrong" only in the true frame).

**F6. Robustness envelope to unmodelled relief (exploratory).** Geometric matching keeps 100% success up to 1 m of relief, drops to 75%
at 2 m and 32% at 4 m, and is no better than doing nothing by 8 m with violation rate 0.54. Violation exceeds 5% from 2 m. The 0.3-0.5 m
height RMS quoted for the PGDA DEMs in the 29 Oct note (not re-verified) lies inside the range where every correcting arm succeeds.
Break-even amplitudes: `analysis_sweep/sweep_breakeven.json`. Figure: `docs/figures/relief_sweep.png`.

**F7. The gate's advantage survives accelerometer bias; its constants matter (exploratory).** With bias 0.0002-0.005 m/s^2, under changed
terrain the gate keeps violation about 0.10-0.11 against 0.51-0.64 for geometric and authority, and 29-36 m miss against 94-106 m
(T10). Its success at 10 m falls from 54% to 7% at 0.005 m/s^2 because navigation drift itself approaches the miss limit.
With no map error and the largest bias the gate is slightly worse than geometric (7.0 vs 5.3 m, 94% vs 100% success): it blocks
legitimate fixes once drift exceeds its gate. Loosening process noise (q = 1, 10 m^2/s) removes that cost but gives up the changed-terrain
benefit (success 12% and 0%). The trade-off is real and untuned.

## What this does and does not support
Supported (in this simulator): the scoring-frame effect; no problem at 3-8 m tie error; speed violations come from wrong fixes;
better guidance only partly helps; an authority-aware cap does not help; a classical consistency gate is a strong baseline that the
learned policy does not beat; the gate's benefit survives modest navigation drift but trades off against legitimate fixes.

Not supported: any claim of improved landing safety on real missions; any claim that learned gating is better; novelty of the gate.
Validity limits: 3-DOF point mass, ideal attitude, instantaneous scans, one DEM tile (Site01), four Gaussian relief shapes shared by all
areas, three fixed start errors, ideal sensor model apart from the stated bias; the gate benefits from the simulator's good navigation
between fixes (see F7) and the gate's start variance was set knowing the start-error range (up to about 95 m). The 0.3-0.5 m DEM height RMS was verified on NASA's PGDA product 78 page (9 Nov). G3 constants were not tuned but the arm was added after a 3-area look at results.

## Reproduce
```
python tools/plan_guidance_ablation.py                    # areas -> LANTERN/Assets/Experiments/GuidanceAblation/plan.json
python tools/build_guidance_ablation_runner.py            # generates Assets/Editor/GuidanceAblationRunner.cs from the frozen runner
Unity.exe -batchmode -nographics -projectPath LANTERN -executeMethod SensorTrust.Editor.GuidanceAblationHeadless.Run -gaStage eval_g1 -gaOut g1_20261108
python tools/analyze_guidance_ablation.py out/guidance_ablation/analysis_12areas out/guidance_ablation/g1_20261108 out/guidance_ablation/wide_20261108
python tools/analyze_relief_sweep.py out/guidance_ablation/analysis_sweep out/guidance_ablation/sweep_20261108
python tools/analyze_imu_stress.py out/guidance_ablation/analysis_imu out/guidance_ablation/imu_20261108 out/guidance_ablation/g3_20261108
python tools/analyze_gate_detection.py out/guidance_ablation/analysis_gates out/guidance_ablation/g3_20261108
python tools/make_results_tables.py
```
Stages: `eval_smoke`, `eval_g1`, `eval_wide`, `eval_g3`, `eval_sweep`, `eval_imu`. Re-running with the same `-gaOut` resumes.
