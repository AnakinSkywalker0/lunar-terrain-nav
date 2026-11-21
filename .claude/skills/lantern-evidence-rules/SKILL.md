---
name: lantern-evidence-rules
description: Rules for running and reporting LANTERN experiments (Site04 use, pre-registration, tags, scoring frame, exploratory labels). Use before any new experiment, evaluation run, results table or claim.
---

# LANTERN evidence rules

These come from `docs/PREREG.md`, the 8 Nov re-analysis and the ml-eval handoff. Follow them for every new run or claim.

## Site04 is the only unseen real site
- Never tune on Site04. Do not run it (`--allow-site04`) until a new pre-registration file (like `docs/PREREG.md`) exists, is frozen and is tagged.
- Procedure: tune on procedural worlds and Site01 only, freeze, tag, run Site04 once. No re-runs after seeing results; report failures.
- Do not move or delete the git tags `round1` and `prereg-round2`.

## Pre-registration
- Write judges, conditions, n, seeds, success criteria and decision rules before the run. Anything not listed is exploratory and must be labelled exploratory in every table and sentence.
- Disclose anything seen before the freeze (smoke runs, looks at results).

## Scoring and statistics
- State the scoring frame. A map offset cannot be seen from the map: score in the map frame and the true frame, and say which one a number uses (the original "0/N under map shift" was a frame artefact).
- The unit of evidence is the terrain area, not the run. Runs on one area are not independent.
- Differences of a few points per cell are within noise. Do not call them wins.
- Keep negative results, failed criteria and corrected claims in the record (`docs/FULL_LOG.md`).

## Claims
- Simulation only. Say so whenever results are quoted.
- "PITFAL-style" is our reimplementation, not NASA's system.
- No novelty claim until the paywalled literature (IEEE Xplore, AIAA) is checked through the college library.
- Separate estimates from recorded values; show the file a number comes from.
