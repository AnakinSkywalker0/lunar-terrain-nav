# Frozen scan-utility model: Site01 transfer results

810 descents; 162 paired configurations; 3 terrain areas.

No training or policy tuning on these outcomes. The policy is the previously selected v2 hybrid.

| Policy | Successful landings | Mean miss | Speed violations |
|---|---:|---:|---:|
| off | 0/162 | 64.42 m | 0 |
| geometric | 54/162 | 45.99 m | 39 |
| bounded | 54/162 | 46.32 m | 39 |
| old_ml | 0/162 | 64.42 m | 0 |
| utility | 54/162 | 43.60 m | 47 |

Prewritten transfer criterion met: **False**.

Criterion: lower pooled mean miss and fewer speed violations without fewer target successes than geometric matching.

| Area | Policy | Successes | Mean miss | Speed violations |
|---|---|---:|---:|---:|
| site01_transfer01 | off | 0/54 | 64.37 m | 0 |
| site01_transfer01 | geometric | 18/54 | 61.55 m | 18 |
| site01_transfer01 | bounded | 18/54 | 66.02 m | 18 |
| site01_transfer01 | old_ml | 0/54 | 64.37 m | 0 |
| site01_transfer01 | utility | 18/54 | 59.59 m | 15 |
| site01_transfer02 | off | 0/54 | 64.44 m | 0 |
| site01_transfer02 | geometric | 18/54 | 41.11 m | 18 |
| site01_transfer02 | bounded | 18/54 | 37.23 m | 18 |
| site01_transfer02 | old_ml | 0/54 | 64.44 m | 0 |
| site01_transfer02 | utility | 18/54 | 32.73 m | 18 |
| site01_transfer03 | off | 0/54 | 64.46 m | 0 |
| site01_transfer03 | geometric | 18/54 | 35.32 m | 3 |
| site01_transfer03 | bounded | 18/54 | 35.72 m | 3 |
| site01_transfer03 | old_ml | 0/54 | 64.46 m | 0 |
| site01_transfer03 | utility | 18/54 | 38.47 m | 14 |

| Condition | Policy | Successes | Mean miss | Speed violations |
|---|---|---:|---:|---:|
| aligned | off | 0/54 | 64.41 m | 0 |
| aligned | geometric | 54/54 | 0.83 m | 0 |
| aligned | bounded | 54/54 | 0.83 m | 0 |
| aligned | old_ml | 0/54 | 64.41 m | 0 |
| aligned | utility | 54/54 | 0.63 m | 0 |
| relief_positive | off | 0/54 | 64.45 m | 0 |
| relief_positive | geometric | 0/54 | 82.16 m | 39 |
| relief_positive | bounded | 0/54 | 83.15 m | 39 |
| relief_positive | old_ml | 0/54 | 64.45 m | 0 |
| relief_positive | utility | 0/54 | 75.19 m | 47 |
| map_shift | off | 0/54 | 64.41 m | 0 |
| map_shift | geometric | 0/54 | 54.99 m | 0 |
| map_shift | bounded | 0/54 | 54.99 m | 0 |
| map_shift | old_ml | 0/54 | 64.41 m | 0 |
| map_shift | utility | 0/54 | 54.97 m | 0 |

## Interpretation limits

Site01 is separate from the scan-utility training and selection terrain. It appeared in older separate sensor studies, so it is not globally unseen project data.
Three crops share one DEM and simulator. No mission-level statistical significance follows. Actual contact and both impact-speed limits matter; all model failures are retained.
Read environment.txt for the Unity version. Comparisons within this batch use identical software; comparisons with historical Site04 results may also reflect editor-version changes.
No results from this batch may be relabelled as an untouched test after subsequent tuning.

Raw trajectories, sparse clouds, scan decisions, model/policy snapshots, terrain, protocol and hash records are preserved.
