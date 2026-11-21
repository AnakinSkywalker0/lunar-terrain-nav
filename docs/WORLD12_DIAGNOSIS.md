# World-12 collapse of the multi-beam noise-floor gate (20 Nov 2026) - diagnostic, not a pre-registered result

Setup: `tolerance_mb`, 3 beams, independent beam faults, x4 noise below 6000 m, procedural worlds 11 and 12, seed 7, 40 descents per cell (small sample; tuning worlds only, Site04 untouched).
The floor (running innovation estimate s_hat) enters in two places: the chi-square gate and the measurement variance used in the update. I split them with throwaway copies of the engine (deleted afterwards).

| Variant | World 12 success | World 12 median miss | World 11 success |
|---|---|---|---|
| no floor | 97.5% | 44 m | 100% |
| floor in gate and variance (current `tol_noise_floor`) | 7.5% | 169 m | 97.5% |
| floor in gate only | 5.0% | 246 m | 67.5% |
| floor in variance only | 97.5% | 43 m | 100% |

Finding: the collapse comes from loosening the gate, not from the floor itself. The unfloored gate rejects about 500 readings per run that the label calls valid (a tight gate is working as a filter against terrain/map-footprint mismatch on the multi-beam slant geometry); the floored gate rejects about 62 and fuses the mismatched readings, even when they are down-weighted. Putting the floor only in the measurement variance kept world 12 at 97.5% and did not hurt world 11.
Not established: why world 12's terrain makes those readings harmful (my reading is footprint/map mismatch on rough terrain; unverified), and whether "floor in variance only" holds across all conditions (x2 to x16, common-mode faults, fresh worlds). It would need a new pre-registered check before any claim, and a Site04 run would need a round-4 freeze.
