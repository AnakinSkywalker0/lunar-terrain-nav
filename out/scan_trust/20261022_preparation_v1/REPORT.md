# Scan trust data preparation (no training)

10530 valid scan proposals; 4881 leave over 10 m error.
Counts are correlated observations, not independent missions.

| Slice | Accepted | Accepted with >10 m error | Rejected with <=10 m error |
|---|---:|---:|---:|
| all | 9196 | 3547 | 0 |
| aligned | 3510 | 0 | 0 |
| site:original | 1853 | 741 | 0 |
| relief_change | 3344 | 1205 | 0 |
| map_shift | 2342 | 2342 | 0 |
| site:area01 | 1852 | 784 | 0 |
| site:area02 | 1817 | 703 | 0 |
| site:area03 | 1835 | 805 | 0 |
| site:area04 | 1839 | 514 | 0 |

Features, labels and group metadata are separate CSVs. Split by area, never by individual scan.
No-model gate acceptance matches the geometric baseline on every archived scan.
No learned model was evaluated and no new landing outcome was generated.
Retrospective development only: all five areas were already inspected. Fresh independent terrain and new offset patterns required for final evaluation.
No ground truth, condition, site, seed, mode, run ID or label is a model input. The six local-match features cannot uniquely distinguish global map registration error.
