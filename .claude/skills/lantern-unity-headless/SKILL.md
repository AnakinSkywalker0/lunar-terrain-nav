---
name: lantern-unity-headless
description: Run LANTERN Unity experiments headless (batch mode) and long Python result scripts safely. Use only when the user asks to run an experiment or Unity job.
---

# Running LANTERN jobs

## Ask first
Unity execution was paused at the user's request before (README, 4 Nov). Do not start Unity or any job longer than a couple of minutes unless the user asked for it in this session.

## Unity batch runs
Unity 6000.3 (the 8 Nov studies used 6000.3.24f1). Pattern from `docs/GUIDANCE_ABLATION_RESULTS.md`:
```bash
Unity.exe -batchmode -nographics -projectPath LANTERN -executeMethod SensorTrust.Editor.GuidanceAblationHeadless.Run -gaStage eval_g1 -gaOut g1_20261108
```
- Find the installed Unity executable instead of guessing its path (Unity Hub install folder).
- Stages: `eval_smoke`, `eval_g1`, `eval_wide`, `eval_g3`, `eval_sweep`, `eval_imu`. Re-running with the same `-gaOut` resumes.
- Run the smoke stage first. Regenerate runners with the matching `tools/build_*.py` script; never hand-edit generated C#.
- The Unity project must not be open in another editor instance (project lock).

## Long jobs (Unity or Python)
- Run in the background, log to a file with start and end timestamps, one job at a time.
- Machine: 16 GB RAM. Use 4 workers, never more than 6.
- Report what finished, with exit codes, then compare outputs against committed CSVs before claiming a reproduction.
- Save logs and result files somewhere durable; scratch folders can be cleared.
