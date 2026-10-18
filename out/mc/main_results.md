
### cliff (HAKUTO-R)

| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |
|---|---|---|---|---|---|---|---|
| Fixed gate | 0.2 | 0-1 | 1290 | 98.9 | 1.9 | 0.03 | 9 |
| PITFAL-style | 82.0 | 78-85 | 19 | 0.8 | 7.1 | 0.05 | 448 |
| Map tolerance | 97.2 | 95-98 | 19 | 0.0 | 6.4 | 0.05 | 453 |
| Wait and see | 79.6 | 76-83 | 19 | 0.8 | 0.2 | 0.05 | 448 |
| Second opinion | 56.6 | 52-61 | 112 | 7.8 | 23.1 | 0.04 | 447 |
| ML classifier | 75.8 | 72-79 | 19 | 0.5 | 1.0 | 0.05 | 448 |
| Trust v1 (4-step) | 94.6 | 92-96 | 19 | 0.2 | 4.4 | 0.05 | 452 |
| Trust v2 | 96.8 | 95-98 | 19 | 0.2 | 4.9 | 0.05 | 452 |
| Trust v2 + live scan | 100.0 | 99-100 | 19 | 0.3 | 4.6 | 0.04 | 450 |
| ablation: no probation | 95.0 | 93-97 | 19 | 0.1 | 4.7 | 0.05 | 452 |
| ablation: no physical check | 94.2 | 92-96 | 19 | 0.7 | 1.6 | 0.05 | 452 |

### cliff + faults

| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |
|---|---|---|---|---|---|---|---|
| Fixed gate | 0.0 | 0-1 | 1210 | 99.3 | 1.3 | 0.03 | nan |
| PITFAL-style | 85.6 | 82-88 | 20 | 0.6 | 7.9 | 0.05 | 449 |
| Map tolerance | 97.6 | 96-99 | 20 | 0.1 | 7.1 | 0.05 | 453 |
| Wait and see | 80.2 | 76-83 | 19 | 8.1 | 0.2 | 0.05 | 448 |
| Second opinion | 8.6 | 6-11 | 581 | 41.5 | 13.9 | 0.03 | 444 |
| ML classifier | 76.0 | 72-80 | 40 | 3.1 | 1.5 | 0.05 | 447 |
| Trust v1 (4-step) | 94.8 | 92-96 | 24 | 2.2 | 4.9 | 0.05 | 452 |
| Trust v2 | 97.4 | 96-98 | 24 | 1.7 | 6.1 | 0.05 | 452 |
| Trust v2 + live scan | 99.8 | 99-100 | 24 | 1.2 | 5.7 | 0.05 | 450 |
| ablation: no probation | 92.8 | 90-95 | 30 | 0.9 | 5.3 | 0.05 | 452 |
| ablation: no physical check | 95.4 | 93-97 | 20 | 7.2 | 1.6 | 0.05 | 452 |

### shadow + noisy altimeter (IM-2)

| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |
|---|---|---|---|---|---|---|---|
| Fixed gate | 0.0 | 0-1 | 1264 | 98.9 | 0.6 | 0.03 | nan |
| PITFAL-style | 64.0 | 60-68 | 41 | 4.3 | 32.5 | 0.04 | 444 |
| Map tolerance | 61.6 | 57-66 | 27 | 6.7 | 40.3 | 0.04 | 445 |
| Wait and see | 28.6 | 25-33 | 125 | 46.0 | 1.5 | 0.03 | 428 |
| Second opinion | 15.6 | 13-19 | 429 | 46.6 | 8.6 | 0.03 | 439 |
| ML classifier | 23.8 | 20-28 | 27 | 18.2 | 20.1 | 0.04 | 430 |
| Trust v1 (4-step) | 53.4 | 49-58 | 114 | 20.2 | 28.5 | 0.04 | 446 |
| Trust v2 | 88.0 | 85-91 | 68 | 3.8 | 52.4 | 0.05 | 453 |
| Trust v2 + live scan | 59.2 | 55-63 | 466 | 51.1 | 11.9 | 0.02 | 431 |
| ablation: no probation | 39.4 | 35-44 | 106 | 11.9 | 32.1 | 0.04 | 445 |
| ablation: no physical check | 58.6 | 54-63 | 27 | 22.5 | 29.9 | 0.04 | 444 |

### delayed altimeter (ispace M2)

| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |
|---|---|---|---|---|---|---|---|
| Fixed gate | 0.0 | 0-1 | 1286 | 98.5 | 6.9 | 0.03 | nan |
| PITFAL-style | 0.0 | 0-1 | 1025 | 95.8 | 71.7 | 0.02 | nan |
| Map tolerance | 0.0 | 0-1 | 537 | 61.2 | 83.8 | 0.03 | nan |
| Wait and see | 0.2 | 0-1 | 151 | 1.0 | 96.8 | 0.03 | 381 |
| Second opinion | 0.0 | 0-1 | 791 | 96.0 | 60.5 | 0.02 | nan |
| ML classifier | 0.4 | 0-1 | 166 | 22.8 | 71.8 | 0.04 | 405 |
| Trust v1 (4-step) | 0.0 | 0-1 | 429 | 59.8 | 87.8 | 0.03 | nan |
| Trust v2 | 83.0 | 79-86 | 241 | 40.6 | 26.4 | 0.04 | 458 |
| Trust v2 + live scan | 95.8 | 94-97 | 275 | 54.1 | 20.5 | 0.04 | 452 |
| ablation: no probation | 0.0 | 0-1 | 529 | 64.6 | 85.0 | 0.03 | nan |
| ablation: no physical check | 0.2 | 0-1 | 142 | 0.7 | 96.9 | 0.03 | 372 |

### altimeter dropout (IM-1)

| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |
|---|---|---|---|---|---|---|---|
| Fixed gate | 0.0 | 0-1 | 1428 | 98.5 | 2.7 | 0.03 | nan |
| PITFAL-style | 34.8 | 31-39 | 277 | 0.8 | 13.0 | 0.02 | 435 |
| Map tolerance | 41.6 | 37-46 | 239 | 0.0 | 11.3 | 0.02 | 433 |
| Wait and see | 29.0 | 25-33 | 284 | 0.4 | 0.6 | 0.02 | 427 |
| Second opinion | 26.2 | 23-30 | 289 | 1.2 | 25.5 | 0.02 | 425 |
| ML classifier | 24.2 | 21-28 | 295 | 0.4 | 1.9 | 0.02 | 424 |
| Trust v1 (4-step) | 31.4 | 27-36 | 268 | 0.1 | 8.0 | 0.02 | 430 |
| Trust v2 | 37.0 | 33-41 | 253 | 0.1 | 8.8 | 0.02 | 431 |
| Trust v2 + live scan | 61.4 | 57-66 | 122 | 0.1 | 8.8 | 0.03 | 421 |
| ablation: no probation | 30.0 | 26-34 | 271 | 0.1 | 8.0 | 0.02 | 429 |
| ablation: no physical check | 32.0 | 28-36 | 268 | 0.4 | 3.2 | 0.02 | 426 |
