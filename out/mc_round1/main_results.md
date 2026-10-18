
### cliff (HAKUTO-R)

| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |
|---|---|---|---|---|---|---|---|
| Fixed gate | 0.4 | 0-1 | 1303 | 99.1 | 1.8 | 1.00 | 58 |
| PITFAL-style | 49.0 | 45-53 | 257 | 8.3 | 7.3 | 1.00 | 430 |
| Map tolerance | 45.6 | 41-50 | 325 | 12.2 | 4.5 | 1.00 | 428 |
| Wait and see | 53.0 | 49-57 | 21 | 0.9 | 0.4 | 1.00 | 431 |
| Second opinion | 46.2 | 42-51 | 27 | 19.9 | 11.9 | 1.00 | 427 |
| ML classifier | 48.8 | 44-53 | 188 | 6.8 | 2.1 | 1.00 | 430 |
| Trust layer (4-step) | 89.2 | 86-92 | 19 | 0.2 | 10.7 | 0.00 | 452 |
| Trust + live scan | 100.0 | 99-100 | 19 | 0.3 | 10.3 | 0.00 | 450 |
| ablation: no camera step | 46.6 | 42-51 | 740 | 30.7 | 2.9 | 1.00 | 423 |
| ablation: no probation | 89.0 | 86-91 | 19 | 0.0 | 11.9 | 0.00 | 452 |
| ablation: no physical check | 88.2 | 85-91 | 19 | 0.7 | 4.4 | 0.00 | 452 |

### cliff + faults

| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |
|---|---|---|---|---|---|---|---|
| Fixed gate | 0.0 | 0-1 | 1222 | 99.3 | 1.2 | 1.00 | nan |
| PITFAL-style | 45.6 | 41-50 | 252 | 9.7 | 7.8 | 1.00 | 430 |
| Map tolerance | 40.4 | 36-45 | 386 | 18.4 | 4.8 | 1.00 | 426 |
| Wait and see | 53.6 | 49-58 | 22 | 8.7 | 0.3 | 1.00 | 430 |
| Second opinion | 32.8 | 29-37 | 48 | 31.2 | 12.5 | 1.00 | 417 |
| ML classifier | 46.0 | 42-50 | 123 | 10.1 | 1.9 | 1.00 | 430 |
| Trust layer (4-step) | 84.6 | 81-87 | 23 | 1.6 | 11.9 | 0.00 | 452 |
| Trust + live scan | 100.0 | 99-100 | 23 | 1.3 | 11.5 | 0.00 | 449 |
| ablation: no camera step | 42.2 | 38-47 | 681 | 31.0 | 3.1 | 1.00 | 426 |
| ablation: no probation | 83.0 | 79-86 | 39 | 0.9 | 13.2 | 0.00 | 451 |
| ablation: no physical check | 88.2 | 85-91 | 20 | 6.6 | 4.4 | 0.00 | 452 |

### shadow + noisy altimeter (IM-2)

| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |
|---|---|---|---|---|---|---|---|
| Fixed gate | 0.0 | 0-1 | 1279 | 99.0 | 0.6 | 1.00 | nan |
| PITFAL-style | 27.0 | 23-31 | 584 | 33.6 | 17.4 | 1.00 | 423 |
| Map tolerance | 18.0 | 15-22 | 766 | 47.9 | 6.8 | 1.00 | 411 |
| Wait and see | 33.2 | 29-37 | 65 | 38.6 | 2.8 | 1.00 | 390 |
| Second opinion | 33.8 | 30-38 | 32 | 30.1 | 16.2 | 1.00 | 410 |
| ML classifier | 25.0 | 21-29 | 307 | 22.3 | 16.0 | 1.00 | 422 |
| Trust layer (4-step) | 55.0 | 51-59 | 25 | 13.7 | 41.8 | 0.00 | 445 |
| Trust + live scan | 64.2 | 60-68 | 326 | 48.5 | 6.6 | 0.00 | 431 |
| ablation: no camera step | 17.0 | 14-21 | 984 | 56.4 | 3.7 | 1.00 | 402 |
| ablation: no probation | 38.4 | 34-43 | 47 | 6.0 | 41.0 | 0.00 | 443 |
| ablation: no physical check | 63.2 | 59-67 | 21 | 16.6 | 40.7 | 0.00 | 445 |

### delayed altimeter (ispace M2)

| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |
|---|---|---|---|---|---|---|---|
| Fixed gate | 0.0 | 0-1 | 1299 | 98.6 | 6.4 | 1.00 | nan |
| PITFAL-style | 1.2 | 1-3 | 1866 | 95.7 | 49.2 | 1.00 | 274 |
| Map tolerance | 4.0 | 3-6 | 1283 | 94.0 | 57.1 | 1.00 | 256 |
| Wait and see | 35.6 | 32-40 | 152 | 0.9 | 96.8 | 1.00 | 381 |
| Second opinion | 18.4 | 15-22 | 156 | 86.6 | 54.0 | 1.00 | 332 |
| ML classifier | 23.8 | 20-28 | 191 | 2.7 | 67.6 | 1.00 | 391 |
| Trust layer (4-step) | 0.2 | 0-1 | 507 | 63.6 | 84.4 | 0.00 | 395 |
| Trust + live scan | 2.2 | 1-4 | 1356 | 95.2 | 60.7 | 0.00 | 303 |
| ablation: no camera step | 3.0 | 2-5 | 1811 | 94.5 | 50.3 | 1.00 | 335 |
| ablation: no probation | 0.2 | 0-1 | 558 | 69.9 | 81.8 | 0.00 | 395 |
| ablation: no physical check | 0.4 | 0-1 | 144 | 0.7 | 97.0 | 0.00 | 380 |

### altimeter dropout (IM-1)

| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |
|---|---|---|---|---|---|---|---|
| Fixed gate | 0.0 | 0-1 | 1445 | 98.5 | 2.7 | 1.00 | nan |
| PITFAL-style | 7.8 | 6-10 | 843 | 9.5 | 12.0 | 1.00 | 406 |
| Map tolerance | 9.0 | 7-12 | 576 | 5.1 | 8.4 | 1.00 | 415 |
| Wait and see | 7.4 | 5-10 | 606 | 0.5 | 0.8 | 1.00 | 404 |
| Second opinion | 7.6 | 6-10 | 588 | 6.6 | 12.5 | 1.00 | 387 |
| ML classifier | 8.6 | 6-11 | 505 | 2.2 | 3.8 | 1.00 | 386 |
| Trust layer (4-step) | 44.4 | 40-49 | 199 | 0.1 | 17.6 | 0.00 | 436 |
| Trust + live scan | 55.8 | 51-60 | 142 | 0.1 | 17.6 | 0.00 | 422 |
| ablation: no camera step | 6.4 | 5-9 | 897 | 12.1 | 5.1 | 1.00 | 405 |
| ablation: no probation | 44.2 | 40-49 | 200 | 0.1 | 19.5 | 0.00 | 437 |
| ablation: no physical check | 45.4 | 41-50 | 197 | 0.3 | 7.9 | 0.00 | 435 |
