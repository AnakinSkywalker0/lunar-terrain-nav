# Verification

- Completed 27 stationary scans and 54 descents (27 paired OFF/ON cases).
- Unique run IDs and OFF/ON pairing verified by the summary script.
- All 81 trajectory files and all 81 sparse-cloud files are present.
- Frozen C# source snapshots match their recorded SHA-256 hashes.
- Source terrain asset, height metadata and raw heightmap hashes saved separately.
- Known-offset/sign, flat-map ambiguity, empty-scan and out-of-map checks passed in Unity.
- Replay controls manually checked for matching OFF/ON, map-condition switching and 2000 m starting altitude.
- Final presentation scripts compiled; no new C# or replay exceptions found in the editor log.
- git diff --check passed.

The Unity view replays measured PhysX trajectories. It does not rerun physics when a replay selector changes. The original Site04 flight scene was not edited.
