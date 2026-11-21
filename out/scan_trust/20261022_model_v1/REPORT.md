# Scan-trust training and frozen development evaluation

User authorized this training on22Oct2026. No old altimeter model was retrained.

Selected: forest_full; bad-score threshold 0.18; fitting rows 5522.

| Split | Method | Accepted bad | Safe corrections rejected | Total accepted |
|---|---|---:|---:|---:|
| train | geometric | 2228 | 0 | 5522 |
| train | rule | 573 | 2319 | 1548 |
| train | logistic | 112 | 2359 | 1047 |
| train | forest_full | 0 | 1598 | 1696 |
| train | forest_residual | 1 | 3204 | 91 |
| validation | geometric | 805 | 0 | 1835 |
| validation | rule | 200 | 694 | 536 |
| validation | logistic | 33 | 815 | 248 |
| validation | forest_full | 2 | 473 | 559 |
| validation | forest_residual | 0 | 1019 | 11 |
| retrospective_test | geometric | 514 | 0 | 1839 |
| retrospective_test | rule | 123 | 1084 | 364 |
| retrospective_test | logistic | 0 | 1289 | 36 |
| retrospective_test | forest_full | 0 | 1119 | 206 |
| retrospective_test | forest_residual | 0 | 1325 | 0 |

Train=original/area01/area02; validation=area03; retrospective_test=area04. All five historical areas were already inspected. These numbers concern correlated archived proposals, not independent landings.
Validation selected the model family and threshold. The model was not refitted on validation or retrospective test data. Correction-signature features can overfit the injected offsets; the fresh closed-loop matrix changes those offsets and the map perturbation.
The selected model is32 trees,depth<=6,1252nodes,portable JSON43965bytes. Feature importance is descriptive, not causal attribution or evidence of generalization.
Python portable export matches sklearn scores exactly on all10530 archived float32 input rows. Unity parity is recorded separately.
Scores are uncalibrated; the complete training_report.json includes calibration bins, seed sensitivity and all validation trials.
No new test result influenced deployment selection. See the closed-loop report for actual navigation and landing outcomes.
