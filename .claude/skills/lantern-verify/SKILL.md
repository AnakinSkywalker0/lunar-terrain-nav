---
name: lantern-verify
description: Verify changes to the LANTERN simulator, tools or scoring before saying they work. Use after editing sim/, tools/ or Unity C#, before quoting new results, and when reproducing another branch's numbers.
---

# Verify LANTERN changes

A green test run is not a tested workflow. Run the checks below, then say exactly what was and was not run.

## Always (about 1 second)
```bash
python -m unittest tests.test_scan_trust tests.test_scan_utility tests.test_navigation_v3_reporting
```
Expected: `Ran 19 tests ... OK`. (`unittest discover` does not work here: `tests/` has no `__init__.py`.)

## After touching `sim/engine.py`
- Quick behaviour check: `python sim/smoke.py` (pitfal / trust / trust2 on three scenarios, 100 runs each); compare with the numbers you expect.
- If the branch has them (they are on `ml-eval`, not `main`): `python sim/check_unchanged.py --quick` must end `UNCHANGED`, then `python sim/check_ml2.py` must end `ALL CHECKS PASSED`. Use the full `check_unchanged.py` (about 10 min) before merging.
- Every new engine option must default to off, and old judges must stay bit-identical.

## Reproducing results from another branch
1. Use a throwaway worktree: `git worktree add --detach <dir> origin/<branch>`. Never switch branches in a dirty working tree.
2. `data/` is untracked: copy it from the main checkout into the worktree.
3. Run result scripts one at a time (4 workers each, 16 GB machine; never above 6 workers). Log to a file with timestamps.
4. Compare each new CSV with the committed CSV row by row on (world, condition, judge). Seeds are fixed, so a match shows determinism, not independent confirmation. Say so.
5. Save logs and CSVs somewhere durable, then remove the worktree (`git worktree remove --force`).

## Number-heavy claims
- Quote numbers only from result files (`out/**`) or the cited document; name the file.
- Recompute derived numbers (means, differences) from the CSV instead of copying prose.
- For UI or Unity changes, exercise the scene or batch runner; compilation alone proves nothing.
- Do not commit, push or tag unless asked.
