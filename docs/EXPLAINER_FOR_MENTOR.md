# LANTERN in plain terms: what we are doing, what we found, and what comes next

Written 8 Nov 2026. Technical details: [GUIDANCE_ABLATION_RESULTS.md](GUIDANCE_ABLATION_RESULTS.md) and
[HANDOFF_2026-11-08.md](HANDOFF_2026-11-08.md). Everything below comes from a simulator, not from a real lander.

## 1. The problem
A lander coming down to the Moon has no GPS. It keeps track of where it is by adding up its own motion sensors (an IMU), and that
estimate slowly drifts. To fix it, the lander scans the ground with lasers and compares the scan to a stored map. If the scan
matches the map at a different spot than expected, it nudges its position estimate. This is called terrain-relative navigation.

The risk: sometimes the match is wrong (the ground looks different from the map, or looks like somewhere else). Believing a wrong
match makes the lander steer to the wrong place, sometimes with too much sideways speed at touchdown.

**Our research question:** when should a lander accept, shrink or ignore a terrain correction, and does that choice change how safely
it touches down?

## 2. What exists (built and working)
- A Unity-based descent simulator with real NASA lunar elevation data (Site04 and Site01 tiles), a laser scan model, a scan matcher,
  and guidance that steers from the lander's own estimate (not from the true position).
- A learned "trust" model that decides whether to believe a correction (trained on Site04 data).
- A fast, repeatable batch pipeline that now runs without opening Unity's window: about 20,000 simulated landings in under an hour.

## 3. What we found (honest version)
1. **An earlier headline was a scoring artifact.** We had reported "0 successes when the map is shifted". A map shifted by 38 m cannot be
   noticed by a lander that only has that map; scored against the map's own coordinates the same landings succeed about 70% of the time.
2. **Small, realistic map-position errors (3 m and 8 m) are not a problem here.** Plain matching lands within about 1 m in every case.
3. **The danger is wrong matches, not late corrections.** Zero speed violations appeared when corrections were right. They appeared
   only when the ground differed from the map; in that test about 64% of landings broke the speed limit with simple matching.
4. **Our first idea (limit how much the lander may correct late in descent) did not work** (pre-registered test, 12 terrain areas).
   Better terminal steering helped partly, not fully.
5. **A classical statistics check beat our learned model.** A short, textbook rule (a Kalman filter that rejects corrections
   inconsistent with its own uncertainty) cut speed violations from 64% to 10% and the average miss from 100 m to 29 m under changed
   terrain. Our learned model was about as good as plain accept-every-match matching. This held across 12 areas and survived added sensor drift,
   though the rule's settings matter.
6. **How much map error can plain matching tolerate?** About 1 m of unmodelled relief: fine. At 2 to 4 m it starts failing; at 8 m it is
   worse than doing nothing. Published lunar elevation maps are reported to be accurate to about 0.3 to 0.5 m (confirmed on NASA's data
   page for these maps), which would sit inside the safe range.

## 4. Is it research-worthy?
**Not yet as a finished paper; plausibly as a short workshop-level paper after more work.** Why:
- *Good:* the evaluation is careful (written decision rules before running, area-level statistics, exact reproducibility checks, negative
  results reported). The "classical gate beats learned gate" result and the robustness-envelope curve are concrete, measured outputs.
- *Weak:* the simulator is simple (point-mass lander, ideal attitude, instant scans, bump-shaped map errors, one lunar tile). The classical
  gate is textbook, so "it works" is not a new method. The learned model may be weak because it is small and trained elsewhere, not because
  learning is a bad idea. No real flight data is involved.
- *What would make it worth a paper:* a rigorous, reproducible benchmark showing when terrain corrections help or hurt touchdown, with a
  fair comparison of classical and learned gates, under realistic error models, with honest limits. That is a legitimate contribution
  even if learning loses.

## 5. What to do next (to make it a paper)
1. **More terrain, more areas** (30 or more, including the Site04 tile and others). Cheap: roughly 25 minutes per 10,000 landings.
2. **Realistic map errors:** replace single bumps with random terrain-error fields of measured size and scale; use NASA's published
   alternate-map versions if they can be downloaded (not yet checked).
3. **More realistic lander:** IMU drift that grows over time, attitude error that affects the scan, delay between scan and correction,
   uncertain starting velocity.
4. **Fair comparisons:** a proper Kalman filter with full covariance, a grid or particle filter, and the learned model retrained with
   the same tuning effort; tune on some areas, test on others.
5. **Pre-register the final tests**, then run them once.
6. **Finish the literature check** (full texts, not abstracts) before any "no one has done this" claim.
7. **Write:** problem, protocol, robustness curve, classical-vs-learned result, limits, reproducibility package.

## 6. Words used
- **TRN (terrain-relative navigation):** fixing position by matching what the lander sees to a map.
- **DEM:** a digital elevation map (a grid of heights).
- **IMU:** motion sensors that give the lander's own dead-reckoned position, which drifts.
- **Map frame vs true frame:** coordinates measured against the map vs against the real Moon.
- **Gate:** a rule that decides whether a proposed correction is accepted.
- **Kalman filter / chi-square gate:** a standard method that tracks its own uncertainty and rejects corrections that disagree with it by
  more than expected.
- **Area (as the unit of evidence):** runs on the same terrain are not independent, so we count terrain areas, not runs.
