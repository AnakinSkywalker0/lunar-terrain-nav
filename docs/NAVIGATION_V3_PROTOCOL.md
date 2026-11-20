# Navigation v3 implementation/validation protocol — 4 November 2026

Status before runs: engineering validation, not a confirmatory paper experiment.
The first implementation is a 3-DOF estimated-state lander with a ten-state
position/velocity/accelerometer-bias/local-map-height-bias EKF, timestamped range and terrain fixes,
fixed-lag replay, chi-square innovation checks and explicit lateral braking.
The historical matcher and experiments are retained as historical artifacts.
Local map-height error is a shared bias state, not independent white noise on
every range reading. Its motion-dependent random walk uses an assumed 50 m
correlation scale. Vertical guidance settles to 0.6 m/s over the last 3 m.

## Scope and comparisons

- `classical_pd`: new fusion, historical PD steering.
- `classical_terminal`: same fusion, velocity-command guidance and terminal braking.
- `ml_terminal`: same terminal system; frozen v2 utility regression may only
  inflate terrain-fix measurement covariance, within a bounded range. It cannot
  override the classical gate. Its output is NOT a calibrated probability,
  covariance or a newly trained reliability model. Default is ML disabled.
- No fitting; no tuning-budget advantage for the ML arm. All arms use identical
  scenario settings, fixed sensor clocks and separate seeded sensor RNG streams.
  Their trajectories and therefore actual observations may subsequently differ.

## Terrain and dispersions

`tools/prepare_navigation_v3.py` freezes one previously exposed development crop
and three separated reserved crops of Site01, excluding all four previous transfer
crops. Site01 itself is not globally unseen. Ground uses 513 samples; prior uses
301 across 2400 m, sampled from the original 5 m raster at pixel centres.
Ground error is a synthetic correlated field scaled by the supplied vertical-only
`toterr` raster; the 50 m smoothing sigma is an assumption. This is an
uncertainty-scaled proxy, NOT a NASA clone, calibrated covariance, or independently
observed lunar ground. Source hashes, generated arrays and error magnitudes are saved.

Smoke: development crop, 500 m, seed 1201, six conditions, all three arms (18 runs).
Reserved: three crops, 500/1500 m, seeds 2201/2202/2203, six conditions, three arms
(324 runs). Freeze source/config hashes before opening reserved outcomes. Fixes
after evaluation require another labelled evaluation, not reuse as untouched data.

All conditions include nonzero initial position/velocity uncertainty, fixed
accelerometer bias, white noise, scan-attitude error and 0.15/0.30 s range/scan
delivery latency. These sensor magnitudes are engineering assumptions, not a
specific instrument specification. Conditions:

1. nominal correlated map-error proxy;
2. +100 m range fault during 12–18 s;
3. absent range data during 12–22 s;
4. absent scans during 9–24 s;
5. 22/-31 m rigid map shift: gross-fault/observability negative control;
6. +16 m local Gaussian relief: gross-fault stress test.

## Outcomes and acceptance of the implementation

Record actual PhysX contact, absolute and map-target miss, vertical/lateral impact
speed, fuel, uncertainty, innovations, rejection reasons, sensor ages, guidance
mode, ML advice and full trajectories. Report contact AND miss below 10/50/100 m
AND |vertical velocity| < 2 m/s AND lateral speed < 1 m/s, in both target frames.
Rigid shift scoring uses true horizontal position minus shift, never the filter's
own estimate. Preserve unsuccessful runs; no-map/no-measurement health is explicit.

Unit contracts: covariance symmetry/positive definiteness, known linear updates,
innovation rejection without state mutation, delayed/in-order equivalence,
duplicate/stale/future/invalid rejection, ML cannot rescue an outlier, altitude
geometry, flat-terrain rejection, terminal-mode latching and thrust bounds.
Integration: all cases terminate; required records are finite and complete;
three-arm pairings and frozen artifacts match; offline scoring agrees with Unity;
range-fault rejection and outage recovery are measured. Nominal landing performance
is reported, not guaranteed by passing a software test.

Confidence intervals for pooled runs are not independent-site intervals. Three
areas support descriptive area-level comparisons only. This validation does not
establish method novelty, mission requirements compliance or flight qualification.
