# LANTERN next direction: review, rating and build instructions for Claude Sonnet 5.5 (20 Nov 2026)

**Status:** review only. Nothing was edited, installed or run to produce Parts A and B, apart from reading existing CSVs. Part C is a plan
for a later build session; none of it has been started. Simulation only throughout. This file is new and uncommitted.

**Readers:** the project owner (Parts A, B), and a Claude Code session running **Claude Sonnet 5.5** (`claude-sonnet-5-5`) that will build
the chosen direction (Part C). The owner chooses the direction; the build session must not pick one itself.

Contents: A. Review · B. How LANTERN rates as a solution · C. Build instructions for Sonnet 5.5 · D. Sources

---

# Part A. Review of the proposed direction

The proposed direction: extend the sensor-trust work with fair comparisons of the noise-aware rule, classical Kalman/chi-square gating,
camera-matcher confidence and a labelled PITFAL-style approximation; freeze settings; test unseen terrain/fault combinations; measure missed
faults and false rejections alongside landing outcomes; check wrong maps, delays, dropout and the unexplained multibeam failure.

## A1. Bottom line
* **Feasible, but as worded it is an evaluation study, not a new method.** Every arm already exists in the Python test bench.
* **The "noise-aware rule" is itself a classical adaptive chi-square gate** (innovation-based noise estimate inside a 99% gate). Comparing it
  with "classical chi-square gating" compares members of the same family; the paper must say so.
* **Round 3's margin over PITFAL was measured against a weaker approximation than PITFAL actually is.** PITFAL is a multi-beam consensus
  method; round 3 compared against our single-beam PITFAL-style judge. Against our multi-beam PITFAL-style judge, the noise floor wins only at x16.
* **Most defensible first step:** a failure analysis of when the adaptive noise floor mistakes systematic mismatch (wrong map, beam-footprint
  mismatch) for sensor noise. It uses existing code, explains the open multibeam failure, and decides whether a new method is needed at all.

## A2. What is actually tested (repo evidence)
| Item | Status | Source |
|---|---|---|
| Noise floor (`tol_noise_floor`), single beam | All five pre-registered rules (Q1-Q5) met on Site04, one run, 500 descents per cell, constants untuned. Site04 is now used up for unseen-site claims. | `docs/ROUND3_RESULTS.md`, `out/round3/site04.csv` |
| Fairness against PITFAL | Round 3 compared with **single-beam** `pitfal`. PITFAL (Adams et al. 2025) is a multi-beam consensus method. Fresh worlds 14-16, multi-beam, independent faults: PITFAL-style multi-beam 99.0 / 99.7 / 98.3 / 66.0 (cliff / x4 / x8 / x16) vs noise floor 96.0 / 98.7 / 99.0 / 98.7. The floor wins only at x16 (+32.7). The Site04 "+29.0 at x8" is against the single-beam version. | `out/round3/multibeam_fresh.csv`, `out_round3_multibeam_fresh.log` |
| Classical chi-square gate | `tolerance` is a 99% innovation gate (6.635) with terrain + map variance added; the floor replaces R with max(R, s_hat^2), an innovation-based adaptive estimate. The plain-gate judge `fixed` ran in round 2 (`out/mc/main_results.csv`) but not in round 3. The Unity Kalman + chi-square gate (G3) gates horizontal scan fixes in a different simulator. | `sim/engine.py:547-566`, `docs/GUIDANCE_ABLATION_RESULTS.md` (F5) |
| Camera-matcher confidence | One fixed gate, matcher peak >= 0.5, applied to every judge. It gates the camera channel; it is not a competitor to the altimeter gates. | `sim/engine.py:758` |
| Multibeam failure | Procedural world 12 collapses for the noise-floor multi-beam gate with both seeds (7, 202) and both fault modes: 6-14% at x4 and 43-48% in cliff + faults (5-13% and 45-50% with consensus added), against 93-100% for the same gate without the floor. PITFAL-style multi-beam is also weaker there (65-88%). Rule M2 was "confirmed" because the rules were scored on worlds 14-16 only. A 40-descent diagnosis with throwaway engine copies points at the floor widening the gate (floor in variance only: 97.5% on world 12). **Not established.** | `out/round3/multibeam_tune.csv`, `multibeam_fresh.csv`, `docs/WORLD12_DIAGNOSIS.md` |
| Multibeam: unchecked implementation causes | (1) Terrain variance is taken at the vehicle's nadir position, not at each beam's footprint (about 0.41 x AGL away at 22.5 deg cant). (2) The beams are fused one after another as if independent, although they share position and map error. Either could produce world-12-like failures. | `sim/engine.py:453`, `sim/engine.py:492` |
| Multibeam code state | The multi-beam sensor and judges are **uncommitted** (+150 lines in `sim/engine.py` after the `prereg-round3` freeze). No result that depends on them is reproducible from a tag. | `git diff --stat` |
| Wrong map | Modelled as a 2 km offset on the altimeter's map lookups only (camera unaffected): a gross-fault case, not a LOLA-realistic error. Round 2: trust v2 1%, PITFAL 35%. **Untested for the noise floor.** Unity side: the 38 m shift "0/N" was a scoring-frame artefact; 3-8 m tie errors are harmless there. | `sim/engine.py:318`, `docs/PROGRESS.md`, `docs/GUIDANCE_ABLATION_RESULTS.md` (F1, F2) |
| Delays | With time stamps for every judge: 63-96% on Site04. Without time stamps every judge fails (round 2). Time-stamp compensation is standard engineering, not a research gap. | `docs/ROUND3_RESULTS.md`, `out/mc/` |
| Dropout | 25-50% for every judge (exploratory). Below 3000 m AGL no range source is left; the camera gives horizontal position only. Probably an observability limit, not a gating problem (inference, not tested). | `docs/ROUND3_RESULTS.md` |
| Fault label | The noise-aware label corrected the missed-fault and false-rejection columns; round 1-2 columns overstate missed faults and understate false rejections at high noise. | `docs/ROUND3_RESULTS.md` |

## A3. Assessment of the idea as worded
* **Feasibility: high.** `fixed`, `pitfal`, `pitfal_mb`, `tolerance`, `tolerance_mb`, the floor, `trust2`, and the camera confidence gate all exist.
* **Scope needs narrowing.** The four named arms sit on two channels (altimeter range, camera position). A fair design is factorial
  (altimeter policy x camera policy), not a four-way race.
* **Missing strong baselines:** an oracle that knows the true noise level (upper bound, not deployable), a principled adaptive filter
  (VB-AKF, Särkkä & Nummenmaa 2009), the plain gate `fixed`, and multi-beam PITFAL-style everywhere PITFAL is compared.
* **Equal tuning budget:** the floor's constants are untuned; PITFAL-style constants (flag timer 40 steps, inflation x10) are our guesses.
  Each arm needs the same, declared tuning budget on development worlds.
* **Held-out data:** Site04 is used. Unseen evaluation needs reserved procedural seeds (17-20 appear unused in `sim/*.py`; confirm) and,
  for a real-terrain claim, a new PGDA site (download needed).
* **Novelty: low as worded.** The comparison is an evaluation contribution. See A6 for candidate gaps.

## A4. Closest prior work (searched 20 Nov 2026)
| Work | Date | Relevance | What was read |
|---|---|---|---|
| Adams, Ward, Smith, Pedrotty, Mendeck, *Topographic Slant Range Modeling and Fault Detection for Precision Planetary Landing* (PITFAL) | AIAA SciTech, 6-10 Jan 2025 | Terrain-referenced slant-range model; multi-beam consensus fault detection (NDL). No detection or false-alarm rates reported; no code released. | NTRS record (20 Nov); the repo's earlier read of the full PDF (`reports/Lunar TRN literature verification.md`) |
| Ward & DeMars, *Including Topographical Effects in Slant-Range Modeling*, AIAA 2018-1333 | Jan 2018 | Slant-range sensor model built from an elevation map: prior art for beam-footprint modelling | Search record only |
| McCabe & DeMars, *Robust, Terrain-Aided Landing Navigation through Decentralized Fusion and Random Finite Sets* | AIAA GNC 2018 | Robust terrain-aided lunar descent navigation | Record/abstract |
| Uijt de Haag et al., terrain database integrity monitors (NASA Langley / Ohio Univ.) | 2001-2004 | Radar-altimeter vs DEM disparity test to detect map faults; flight-tested (SPIE 4363, 2001). Prior art for "the altimeter detects a wrong map". Nadir altimeters struggle with horizontal map errors. | Abstracts and snippets |
| Särkkä & Nummenmaa, *Recursive Noise Adaptive Kalman Filtering by Variational Bayesian Approximations*, IEEE TAC 54(3) 596-600 | Mar 2009 | Principled adaptive measurement-noise estimation (VB-AKF) | Bibliographic record; author PDF located, not read |
| Chang, *Robust Kalman filtering based on Mahalanobis distance as outlier judging criterion*, J. Geodesy 88(4) 391-401 | 2014 | Innovation-distance outlier test inside a robust filter | Abstract/record |
| Teixeira, Quintas, Maurya, Pascoal, *Robust particle filter formulations with application to terrain-aided navigation*, IJACSP | 2017 | Robust terrain-aided navigation filters | Record |
| Park & Bang, *Contours-Seeking Proposal Density Particle Filter and Resilient Terrain-Referenced Navigation*, IEEE TAES 61(6); arXiv 2608.15489 | Dec 2025 / Aug 2026 | Terrain-referenced navigation robust to unknown biases and multimodal altimeter noise | arXiv abstract |
| Rohou, *Contractor Filters*, arXiv 2610.18040 | 13 Oct 2026 | Set-membership filtering with outliers; terrain localization benchmark | arXiv abstract |
| Acharya et al., *Deep Modeling of Non-Gaussian Aleatoric Uncertainty*, arXiv 2405.20513 v2 | Feb 2025 | Learned non-Gaussian uncertainty for terrain-navigation matches, real data: prior art against any "learned matcher confidence" novelty claim | arXiv abstract |
| Karlgaard et al., IM-1 NDL report, NASA TM-20250010290 | 2025 | Real multi-beam lidar on a lunar landing; beams recorded unequal range spans (search snippet) | Search snippet only |

From the repo's earlier reviews, not re-checked today: Choe & Park (IEEE TAES 60(3), 2024), Sheppard et al. (arXiv 2512.12058),
Mohamed & Schwarz (J. Geodesy 1999, innovation-based adaptive estimation).

## A5. Reusable code and data
| Asset | License | Effort | Use |
|---|---|---|---|
| PGDA Product 78: 100 clone DEMs per site, total-height and slope uncertainty GeoTIFFs | No terms visible on the product page; README not read. NASA data. **Check the README before use.** | Low-medium; file sizes not checked | Realistic, spatially correlated map error; new held-out real sites |
| FilterPy (rlabbe/filterpy) | MIT (README) | Low | Reference filters only; the engine has its own vectorised filter |
| Stone Soup (dstl) | MIT | High to integrate | Probably not worth it |
| Matlab-LagrangianPMF (pesslovany) | **AGPL-3.0** | High (MATLAB, copyleft) | Grid-based terrain-navigation baseline for ambiguity, not range-fault gating |
| VB-AKF, Chang 2014 | Reimplement from the papers, cite them | About 50 lines each | Strong classical baselines |
| PITFAL | No code released | Already reimplemented | Must stay labelled "PITFAL-style, our interpretation" |

## A6. Established ideas vs candidate gaps
* **Established (reuse is not novelty):** chi-square innovation gating; adaptive noise estimation (Sage-Husa / IAE / VB-AKF); robust filters;
  multi-beam consensus (PITFAL); altimeter-vs-DEM integrity monitors; time-stamp compensation; learned match uncertainty; terrain-aware
  slant-range models.
* **Candidate gaps (not verified; IEEE Xplore and AIAA full texts were not checked):**
  1. Estimating sensor noise from evidence the map does not touch, so that the map-consistency test stays calibrated under unknown noise and
     still exposes map or footprint mismatch.
  2. An open benchmark reporting missed faults and false rejections per cause (sensor fault, map error, footprint mismatch) alongside landing
     outcomes. PITFAL publishes no such rates.

## A7. Ranked directions (at most three)
### Direction 1 (recommended first). Failure analysis: when does the noise floor absorb systematic mismatch?
* **Advance beyond prior work:** adaptive noise estimation is known to be sensitive to model error and outliers. This would show the
  closed-loop landing consequence with terrain-informed gating, split errors by cause, and test where the floor enters (gate vs variance).
* **Feasibility:** high; Python only; existing switches plus three small default-off ones.
* **Blockers:** commit the multibeam code; owner OK to edit `sim/engine.py`; a new held-out set.
* **Fair baselines:** no floor; floor in gate only; floor in variance only; current floor; oracle noise level; VB-AKF; `fixed`;
  PITFAL-style single and multi-beam; trust v2.
* **Smallest disproving experiment:** first check the nadir-vs-footprint terrain variance. Then worlds 11-16 + Site01, 1 and 3 beams, x1/x4/x8/x16,
  plus the 2 km wrong map and a ~100 m shift, 100 descents per cell. "Floor in variance only fixes world 12 without losing the high-noise gain"
  is refuted if it drops more than 3 points at x16 on fresh worlds. Inference (not tested): it will, because widening the gate is the
  benefit. Then the tension itself is the finding and motivates Direction 2.

### Direction 2. Map-independent noise estimate (candidate method)
* **Advance:** estimate sensor noise from robust second differences of the range sequence (or beam-to-beam agreement), widen the gate only to
  that level, and treat the remaining excess as map/footprint mismatch with an explicit "unresolved" state.
* **Feasibility:** medium; Python only, about 1-2 days of code.
* **Blocker:** the simulator's white Gaussian noise flatters difference-based estimators. A correlated-noise variant is required (C4).
* **Baselines:** as in Direction 1.
* **Disproved if** it fails either pre-registered condition: world 12 at x4 >= 90%, and fresh-world x16 within 3 points of the current floor.

### Direction 3. Benchmark: altimeter policy x camera policy, reserved terrain/fault combinations, per-cause error rates
* **Advance:** first open numbers on missed faults and false rejections for terrain-informed range checking, with clone-DEM map error.
  An evaluation contribution, not a method.
* **Blockers:** new PGDA sites to download; Unity's G3 gate to port; the Python scan path has no wrong-match model (`sim/engine.py:787`), so any
  scan-matcher comparison needs the Unity data.
* **Disproved if** the per-area ranking of policies is not consistent across 3 reserved sites (pre-register a concordance threshold).

## A8. Research paper vs flight-ready engineering
Any direction can support a paper: simulation, held-out terrain, pre-registration, equal tuning budgets, claims kept to the simulator.
Flight readiness needs: 6-DOF dynamics with attitude error, real sensor error models (correlated noise, dust, plume), real-time execution on
flight-like hardware, hardware-in-the-loop, integrity requirements (protection levels, false-alarm allocation), and validation on flight data.
None of these directions gets there.

## A9. Search limits
Standard web search plus about 8 page fetches on 20 Nov 2026. Abstracts and records, no IEEE Xplore or AIAA full texts; one HAL page was
blocked; no Google Scholar, no citation chaining. Not an exhaustive review. No novelty claim before a library check (evidence rules).

---

# Part B. How LANTERN rates as a solution (assessment, 20 Nov 2026)

This is my judgement from the repo and the literature above, not a measured score. 1 = weak, 5 = strong.

| Dimension | Rating | Why |
|---|---|---|
| Experimental discipline and honesty | **4.5 / 5** | Pre-registration with tags, one-shot held-out runs, negative results kept, the scoring-frame and fault-label artefacts found and corrected by the team itself. Deductions: the multibeam rules passed while a reproducible world-12 failure sat outside the scored worlds; several looks at tuning worlds before freezes. |
| Test bench engineering and reproducibility | **4 / 5** | Vectorised engine with common random numbers, bit-identical regression checks, unit tests, logged runs. Deductions: multibeam engine code uncommitted after the freeze; two simulators (Python, Unity) with different gates; large untracked `out/`. |
| Technical method | **2.5 / 5** | The rule that works is a classical adaptive chi-square gate with terrain and map variance. The ML judges did not beat classical rules (scan-trust v1 0/54 and 18/162; utility policy level with geometric matching; `ml2` level with a rule gate). |
| Novelty (as of today) | **1.5 / 5** | No verified novel method. Candidate contributions (A6) are unverified, and one is an evaluation contribution. |
| Physical fidelity | **1.5 / 5** | 3-DOF point mass, ideal attitude, white Gaussian sensor noise, burst faults only, assumed beam geometry, procedural crater worlds plus two real tiles. |
| Strength of evidence for general claims | **2.5 / 5** | n = 500 per cell, but the unit of evidence is the terrain area: one real held-out site, procedural worlds from one generator family. |
| Flight readiness | **1 / 5** | Estimated TRL 2-3 (concept plus simulation proof of concept). No hardware, no real sensor data, no real-time or integrity analysis. |

**Overall:** a well-run, honest simulation study at the proof-of-concept stage.
* As a university research project: strong. Its main asset is the evaluation discipline, which many published landing-navigation
  simulations lack.
* As a paper today: not yet. Only after a fair multi-beam PITFAL comparison, the failure analysis, and a held-out run that survives it.
* As a flight solution: not a candidate.
* Against the closest NASA design, our fair approximation of PITFAL is level with or ahead of our candidate except at x16 noise, where the
  candidate wins clearly.

---

# Part C. Build instructions for a Claude Sonnet 5.5 session

## C0. Session setup (owner)
* Open a Claude Code session in `D:\newprj` and pick **Claude Sonnet 5.5** in the model picker. Effort **high** (Sonnet 5.5 guidance: at
  low effort it is more likely to skip verification on coding tasks). For Direction 2's estimator design, an Opus model is the stronger choice.
* Tell the session which direction you chose (1, 2 or 3). Direction 1 is the default recommendation. The session must not start
  Direction 2 or 3 on its own.
* Paste the prompt in C8.

## C1. Hard rules for the build session (from `CLAUDE.md`, `.claude/skills/lantern-evidence-rules`, `lantern-verify`)
1. **Site04:** never run, tune on or touch it in this work. It is used up. Do not pass `--allow-site04`.
2. **Tags:** do not move or delete `round1`, `prereg-round2`, `prereg-round3`. Create a new tag only when the owner explicitly says so.
3. **Git:** no commit, push, merge or branch switch without the owner's explicit OK in chat. Never switch branches in a dirty tree.
4. **Preserve existing work:** do not edit `report/`, `deliverables/`, `README.md`, `docs/ROUND3_RESULTS.md`, `docs/PREREG_ROUND3.md`,
   `docs/WORLD12_DIAGNOSIS.md`, or any existing file under `out/`. New outputs go to `out/round4/`, new docs to new files.
5. **Engine edits:** only with the owner's OK (S0 below). Every new option defaults to off; all existing judges must stay bit-identical.
6. **Downloads:** ask first, naming file, source and size. PGDA data only after reading its README terms.
7. **Compute:** 4 workers, never above 6 (16 GB rule in `lantern-verify`). Run long jobs in the background with a timestamped log file.
8. **Claims:** "simulation only"; "PITFAL-style is our reimplementation"; the terrain area is the unit of evidence; differences of a few
   points per cell are noise; every number names its CSV; exploratory results are labelled exploratory.
9. **Verification:** when you change code that can be run, run a real check that exercises the change before reporting it done. A syntax
   check, or a check that failed to start, does not count. If a check cannot run, say which one and why instead of reporting the change done.
10. **STOP points** (S0-S4) mean: report, then wait for the owner's answer in chat.

## C2. Preflight (any direction)
1. Load the project skills `lantern-evidence-rules` and `lantern-verify`.
2. `git status --short`, `git diff --stat`, `git tag -l`. Record the result. Expect `sim/engine.py` modified (multibeam, about +150 lines) and
   many untracked files.
3. Run the fast checks and record their output:
   ```
   python -m unittest tests.test_scan_trust tests.test_scan_utility tests.test_navigation_v3_reporting
   python -m unittest tests.test_round3_switches tests.test_multibeam tests.test_round3_site04_guards
   python sim/check_unchanged.py --quick
   ```
   Environment seen on 20 Nov 2026: Python 3.13.15, numpy 2.5.2, scipy 1.18.1, pandas 2.3.3, scikit-learn 1.9.0, 28 CPU threads.
4. **STOP S0.** Report the preflight. Ask the owner (a) to confirm the direction, (b) how to secure the uncommitted multibeam code before you
   edit the engine: commit it, with the owner's OK and message, or have the owner commit it, then (c) for permission to edit `sim/engine.py`.

## C3. Direction 1 build: failure analysis of the noise floor
### C3.1 Code audit, no behaviour change
* Read `sim/engine.py:428-510` (multi-beam path) and `:547-566`, `:715-721` (single-beam tolerance and the `s_hat` update).
* Write `tests/test_round4_audit.py`. Using a recorded descent on procedural world 12, show what `s_terr_b` measures: terrain spread at
  nadir vs at each beam's predicted footprint. Report the ratio at several altitudes. This is a diagnostic test; it must not change results.
* Compute terrain statistics for worlds 11-16 and Site01 at beam-footprint scale (height spread within radius r at the footprint, rim slope
  along the track) and save them to `out/round4/terrain_stats.csv`. The aim is to say what is unusual about world 12; label it descriptive.

### C3.2 New engine switches (all default off, bit-identical when off)
| Switch | Effect | Applies to |
|---|---|---|
| `tol_floor_mode="both"` | Only when `tol_noise_floor=True`. `"both"` = current behaviour. `"gate"`: the gate uses `max(R, s_hat^2)`, the update uses `R + terrain + map`. `"variance"`: the gate uses plain `R + terrain + map`, the update uses `max(R, s_hat^2) + terrain + map`. | `tolerance` (`engine.py:557-566`), `tolerance_mb` (`:455`, `:482-483`, `:492`) |
| `oracle_R=False` | Multiply the nominal `R` by the true noise multiplier squared, `R * mult^2` (`mult` from `engine.py:422-424`), in gate and update. **Oracle, not deployable**: an upper bound on what knowing the noise level is worth. (Defined on `R`, not on `sig_nom`, because `R` uses the measured range and `sig_nom` the true range; this keeps the oracle identical to plain tolerance when `mult = 1`.) | `tolerance`, `tolerance_mb` (`R_b * mult^2` per beam) |
| `mb_terrain_at_footprint=False` | Compute the terrain variance at each beam's predicted footprint instead of at nadir. | `tolerance_mb`, `pitfal_mb` |
| `Scenario.wrong_offset_m: float = 2000.0` | New dataclass field replacing the hard-coded 2000.0 in `mapq` / `mapg` (`engine.py:318`, `:326`). The default keeps every result identical. | `map_mode="wrong"` |
| New judge `vbakf` | Scalar VB-AKF (Särkkä & Nummenmaa 2009) for the altimeter noise, inside the same 99% gate with terrain + map variance. Only accepted readings update the noise posterior. Per run: inverse-gamma parameters alpha, beta. Predict: alpha <- rho*alpha, beta <- rho*beta. Update: alpha <- alpha + 1/2; iterate 3 times: R_hat = beta/alpha, filter update with R_hat + terrain + map, beta <- beta_pred + 1/2 * (post-fit residual^2 + H P H'). Constants fixed a priori: rho = 0.97 (same memory as `s_hat`), alpha0 = 2, beta0 = nominal R. **Check these equations against the paper (author PDF: users.aalto.fi/~ssarkka/pub/vb-akf-ieee.pdf) before coding, and record any difference.** | single beam only |
| Result key `s_hat_max` (and `nees_z_mean` if cheap) | Per-run maximum of `s_hat`; mean of (z_est - z_true)^2 / P_zz. Additive keys; existing keys unchanged. | all judges |

Implementation notes: keep the edit additive and local; follow the existing naming and keyword style; reuse the existing `_scalar_update`;
no copied formulas (one helper for the gate/update variance split used by both single and multi-beam paths).

### C3.3 Tests (must pass before any experiment)
* `python sim/check_unchanged.py` (full, about 10 min) ends with `UNCHANGED`.
* `python -m unittest tests.test_round3_switches tests.test_multibeam` pass unchanged.
* New `tests/test_round4_switches.py`:
  * defaults off are bit-identical to omitting the switches (success, miss, impact speeds, fuel, alt_sq, bookkeeping counts);
  * `tol_floor_mode="both"` reproduces `tol_noise_floor=True` exactly;
  * `oracle_R` at nominal noise (`mult = 1`) equals plain tolerance exactly;
  * `wrong_offset_m=2000.0` reproduces the old wrong-map run exactly; `wrong_offset_m=0.0` with `map_mode="wrong"` equals `map_mode="ok"`;
  * `mb_terrain_at_footprint` changes nothing when all beams are vertical (if not testable directly, test at one hand-built geometry);
  * `vbakf`: with constant known noise and no faults, the noise estimate converges to within 20% of the true variance; flagged readings do
    not change alpha or beta.
* **STOP S1.** Report the diff summary (files, line counts), all test output, and anything that did not pass.

### C3.4 Development grid (exploratory, tuning and fresh worlds only)
* Script `sim/round4_dev.py`, modelled on `sim/round3_multibeam_fresh.py` (world list, `CONDS` from `ml2_noise_normal`, `P.tuned()`,
  `cam_policy="conf"`, `fault_label_noise_aware=True`, per-world rows).
* Worlds: tuning 11-13 + Site01 (seed 7 and 202), fresh 14-16 (seed 101). n = 100 per cell.
* Conditions: cliff + faults (nominal), x4, x8, x16; wrong map at `wrong_offset_m` = 2000 and 100; delayed with and without time stamps
  (single beam only); dropout (negative control: every judge should be similar; a large winner suggests a bug).
* Configurations: `fixed`; `pitfal`; `pitfal_mb`; `tolerance`; `tolerance` + floor in modes both / gate / variance; `tolerance` + `oracle_R`;
  `tolerance_mb` with the same floor modes, with and without `mb_terrain_at_footprint`; `vbakf`; `trust2`. Beam modes: independent and common.
* Output: `out/round4/dev.csv` with success, Wilson interval, false rejection, missed fault, alt RMS, outcome split, `s_hat_max`, per world.
* Estimated wall time: about 1 hour at 4 workers (based on the 19-minute round-3 fresh multibeam run; an estimate, not a measurement).
* **STOP S2.** Report the tables per world (not only pooled), the world-12 rows separately, and which of the expectations below held.
  Expectations to check (inference, not results): floor in variance only fixes world 12 but loses the x16 gain; the floor raises `s_hat` and
  admits map-inconsistent readings under the wrong map; footprint terrain variance changes world 12.

### C3.5 Pre-registration (before any held-out run)
* Draft `docs/PREREG_ROUND4.md` in the style of `docs/PREREG_ROUND3.md`: judges and switches, conditions, n, seeds, success criteria,
  decision rules, disclosure of everything seen in C3.4.
* Held-out set (owner decides): reserved procedural seeds 17-20 (no use found in `sim/*.py` or `tools/*.py` on 20 Nov 2026; also check `out/`
  and the Unity side before reserving them; they come from the same crater generator, so they test new draws, not a new terrain type), new seed (for
  example 20261215), n = 200 per cell; optionally one new PGDA real site, only if the owner approves the download.
* Draft decision rules (owner to confirm or change):
  * **H1 (mechanism, diagnostic):** on world 12, 3 beams, x4 and cliff + faults, the fix chosen in C3.4 gains at least 30 points over
    `tol_floor_mode="both"`. Tuning world, so labelled diagnostic.
  * **H2 (cost of the fix):** on the held-out worlds the fix is within 3 points of `"both"` at x8 and x16, single and multi-beam.
  * **H3 (wrong map):** with `wrong_offset_m` 100 and 2000 the floor is no more than 3 points below plain tolerance; if it is, report that
    the floor amplifies map error.
  * **H4 (fair PITFAL):** the candidate is no more than 3 points below `pitfal_mb` in each multi-beam condition.
  * Oracle and VB-AKF rows are reference rows, not hypotheses.
* Add a held-out runner `sim/round4_heldout.py` with refusals like `sim/round3_site04.py` (flag, tag, HEAD == tag, clean frozen files, no rerun),
  and tests in the style of `tests/test_round3_site04_guards.py`.
* **STOP S3.** The owner reviews, edits, commits and tags (for example `prereg-round4`). Do not tag yourself unless told to.

### C3.6 Held-out run and report
* Run `sim/round4_heldout.py` once, in the background, with a log in `out/round4/logs/`. No reruns after seeing results.
* Write `docs/ROUND4_RESULTS.md`: each rule met / failed / mixed with intervals; per-world tables; what did not improve; what was not tested;
  simulation-only caveats. Add a dated entry to `docs/FULL_LOG.md` only if the owner asks.
* **STOP S4.** Final report (C7).

## C4. Direction 2 build (only if the owner chooses it, normally after Direction 1)
* **Estimator (single beam first):** second difference of the accepted-or-flagged range sequence, d2_k = r_k - 2 r_(k-1) + r_(k-2). For white
  noise of variance s^2, Var(d2) = 6 s^2. Robust running estimate over the last W = 40 samples:
  `sigma_diff = 1.4826 * median(|d2|) / sqrt(6)`. Gate variance `max(R, sigma_diff^2) + terrain + map`; update variance the same. The
  innovation excess beyond that is counted as mismatch (`mismatch_score`), never absorbed into the noise level. Optional: hold readings in an
  "unresolved" state when the mismatch score stays high (owner decides the policy).
* **Bias to test:** terrain curvature along the track and fault bursts also enter d2; the median limits but does not remove them.
* **Correlated noise is mandatory:** add a default-off AR(1) altimeter noise option with phi in {0, 0.5, 0.9}, drawn from a separate RNG
  stream (as `Draws.mb` does) so legacy draws do not change. For AR(1) noise, Var(d2) = s^2 (6 - 8 phi + 2 phi^2): at phi = 0.9 the
  estimator underestimates the variance about 14 times. If the method only works at phi = 0, say so.
* **Baselines:** as Direction 1 (current floor, variance-only floor, oracle, VB-AKF, `pitfal_mb`, trust v2).
* **Disproof rules (pre-register):** world 12 at x4 >= 90% and fresh-world x16 within 3 points of the current floor and wrong-map no worse
  than plain tolerance; all at phi = 0 and phi = 0.5.
* Same STOP points, tests and pre-registration procedure as C3.

## C5. Direction 3 build (only if the owner chooses it)
* Read the PGDA Product 78 README first: terms of use, and whether clone files (for example `Site01_final_adj_5mpp_0001_err.tif`) are full
  DEMs or error fields. Do not assume. Ask before downloading, with file names and sizes.
* Add a default-off world option: truth terrain = mean DEM + one clone error field; onboard map = released mean DEM.
* Factorial design: altimeter policy (`fixed`, `pitfal`/`pitfal_mb`, `tolerance` +/- floor, `vbakf`, `trust2`) x camera policy (`conf`,
  `aware`, `both`, none) x faults (bursts, common-mode, wrong map, clone error, delay, dropout).
* Per-cause labels: sensor fault, map error, footprint mismatch; report missed faults and false rejections per cause.
* Reserve 3 real sites before tuning. Pre-register a concordance threshold for policy rankings across sites (for example Kendall's W >= 0.5).
* The Python scan path has no wrong-match model (`engine.py:787`); do not claim scan-matcher results from it. Porting Unity's G3 gate and
  its matcher error data is a separate, larger task; ask before starting it.

## C6. Coding standards for the build session
* Follow existing conventions in `sim/` (vectorised numpy over runs, keyword switches, `summarize` outputs, multiprocessing pool from
  `pipeline.pmap`). Clear names, focused functions, no dead code, no copied formulas between single and multi-beam paths.
* Handle errors visibly (raise on invalid switch combinations, as the multibeam judges already do).
* Keep valid zeros (for example `wrong_offset_m=0.0`) distinct from "unset".
* Keep everything local for review.

## C7. Final report format (each STOP point)
1. What changed: file links, one line per change, line counts.
2. What ran: exact commands, wall time, worker count, log paths.
3. Results: tables with the CSV each number comes from; per world; exploratory rows labelled.
4. What was not run or did not pass, and why.
5. Rule verdicts (met / failed / mixed) when a pre-registered run was made.
6. The decision needed from the owner.

## C8. Prompt to paste into the Sonnet 5.5 session
```
Read docs/NEXT_DIRECTION_REVIEW_AND_BUILD.md in full, then load the project skills lantern-evidence-rules and lantern-verify.
I choose Direction <1|2|3>. Build only that direction, following Part C: the hard rules in C1, the preflight in C2, and the section for my
direction. Stop at every STOP point (S0-S4) and wait for my answer in chat before continuing. Do not touch Site04, the existing tags,
report/, deliverables/ or existing files under out/. Do not commit, push, tag, switch branches or download anything unless I say so.
When you change code that can be run, run a real check that exercises the change before reporting it done; if a check cannot run, say
which one and why. Report at each STOP point in the format of C7.
```

---

# Part D. Sources (accessed 20 Nov 2026 unless noted)
* Adams et al. 2025, PITFAL: https://ntrs.nasa.gov/citations/20240014100
* Ward & DeMars 2018: https://scholarsmine.mst.edu/mec_aereng_facwork/6089
* McCabe & DeMars 2018: https://scholarsmine.mst.edu/mec_aereng_facwork/3968
* Uijt de Haag et al., terrain database integrity monitor: https://ntrs.nasa.gov/api/citations/20040085692/downloads/20040085692.pdf ;
  https://pure.psu.edu/en/publications/terrain-database-integrity-monitor-for-synthetic-vision-systems/ ;
  https://pure.psu.edu/en/publications/flight-test-results-of-a-synthetic-vision-elevation-database-inte/
* Särkkä & Nummenmaa 2009: https://users.aalto.fi/~ssarkka/pub/vb-akf-ieee.pdf
* Chang 2014: https://www.doi.org/10.1007/S00190-013-0690-8
* Teixeira et al. 2017: https://isr.tecnico.ulisboa.pt/publications/robust-particle-filter-formulations-with-application-to-terrain-aided-navigation
* Park & Bang: https://arxiv.org/abs/2608.15489
* Rohou, Contractor Filters: https://arxiv.org/abs/2610.18040
* Acharya et al.: https://arxiv.org/abs/2405.20513v2
* IM-1 NDL report: https://ntrs.nasa.gov/citations/20250010290
* GPS/INS Mahalanobis adaptively-robust filtering (context): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5876522/
* PGDA Product 78: https://pgda.gsfc.nasa.gov/products/78
* Matlab-LagrangianPMF: https://github.com/pesslovany/Matlab-LagrangianPMF
* FilterPy: https://github.com/rlabbe/filterpy
* Stone Soup: https://github.com/dstl/Stone-Soup
* Repo sources: `docs/ROUND3_RESULTS.md`, `docs/PREREG_ROUND3.md`, `docs/WORLD12_DIAGNOSIS.md`, `docs/RESEARCH_NOVELTY_REVIEW.md`,
  `docs/GUIDANCE_ABLATION_RESULTS.md`, `reports/Lunar TRN literature verification.md`, `out/round3/*.csv`, `out/mc/*.csv`, `sim/engine.py`.
