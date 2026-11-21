# Guidance ablation protocol (written before any result, 8 Nov 2026)

Purpose: decide whether the touchdown-speed violations seen after terrain fixes are caused by the
fixed guidance law (a controller artifact) or persist under better guidance, and whether an
authority-aware correction gate reduces them. See `docs/RESEARCH_PLAN_V3.md` (gates G1, G2).

## Design
- Runner: `LANTERN/Assets/Editor/GuidanceAblationRunner.cs` (copy of the frozen transfer runner; the
  transfer runner and its results are untouched). Headless entry: `GuidanceAblationHeadless.cs`.
- Terrain: Site01, 3 transfer areas (stage `eval_g1`) and 9 extra areas (stage `eval_wide`) chosen by
  `tools/plan_guidance_ablation.py` (flat target window, non-overlapping scan windows).
- Conditions: `aligned`, `relief_positive` (Gaussian bump, as before), `map_shift` (22,-31 m = 38 m),
  `tie3` (3 m shift), `tie8` (8 m shift). Shifts are scored in the map frame and the true frame.
- Start altitude 500 and 1500 m; the three transfer start errors u0-u2; one noise seed (717).
  Seeds change only sensor noise, so they are not independent evidence and are not multiplied.
- Guidance: `baseline` (frozen law, -0.04 x - 0.5 v, tilt-clamped), `terminal` (position term dropped
  below 30 m AGL; velocity nulling only), `braking` (speed limited by braking distance at the tilt
  limit with a 0.5 margin, velocity nulling below 5 m AGL).
- Arms: `off`, `geometric`, `bounded` (existing: cap max(5, 0.5 AGL) m), `utility` (frozen Site04
  hybrid policy, unchanged), `authority` (new: cap = 0.5 * a_lim * t_go^2 / 4 with a_lim = 0.365 m/s^2,
  t_go = sqrt(2 AGL / 0.45)).
- Success rule, velocity limits and contact definition are unchanged: vz < 2, vh < 1 m/s.

## Outcomes
Primary: speed-violation rate (contact with vz >= 2 or vh >= 1 m/s).
Secondary: map-relative and absolute miss; success at 10/50/100 m with the velocity limits fixed.
Unit of analysis: terrain area. Per-area rates are computed first; comparisons are paired across areas.
Per-run confidence intervals are not reported (runs inside an area are not independent).

## Decision rules (fixed now)
G1 (guidance artifact). Arm `geometric`, conditions relief_positive and map_shift. Compare `braking`
and `terminal` with `baseline` on the 3 transfer areas, then on all 12 areas.
- Median per-area violation rate falls by >= 50%: speed violations are largely a controller artifact.
- Falls by < 20%: the effect persists under better guidance.
- In between: reported as mixed.
G2 (authority gate). Under `baseline` guidance, `authority` vs `geometric` over 12 areas.
- Supported only if violations fall in >= 10 of 12 areas AND mean map-relative miss is not worse by more
  than 10% (relative). Otherwise reported as not supported.
G3 is not run in this batch (no tuned Kalman/chi-square baseline yet).

## Rules for the run
- Smoke test first; outcomes of the smoke test may only be used to fix crashes, not to tune guidance
  or gates. Guidance and gate constants above are frozen before the smoke run.
- Any deviation is recorded in the results document.
- Not tested: IMU bias, attitude error, scan latency, 6-DOF, realistic vertical map error (PGDA clones).

## Addendum A (8 Nov 2026, added after the g1/wide batches were launched, before their results were read)
Stage `eval_g3` adds the classical baseline from plan gate G3: arm `kf_chi2`, a scalar position-variance
Kalman update with a chi-square (99%, 2 dof) innovation gate. Constants fixed a priori, not tuned:
initial position variance (100 m)^2, fix variance (2 m)^2, process noise 0.05 m^2/s, gate 9.21.
`eval_g3` runs on all 12 areas, baseline guidance only, arms off/geometric/bounded/authority/kf_chi2.
Neither `authority` nor `kf_chi2` has a tuned parameter, so the tuning budgets are equal (zero).
After regenerating the runner, the smoke stage is re-run and must reproduce `smoke_20261108` exactly
for all shared cases (regression check that old arms are unchanged).
