---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Fill the catalog in the submission module injected at collection time"
pr: 74
merged: 2026-09-21
branch: "fix/replay-submission-catalogue"
---

# fix: Fill the catalog in the submission module injected at collection time

What. main is red. Since immediately after merging #71, one `tests/test_a5_scope_pilot.py` is failing in the full execution. This PR reverts that.

Why. It seems the cause of ``` pytest tests/test_a5_scope_pilot.py 3 passed pytest 1 failed, 220 passed ``` is not visible. Since pytest collects all modules before running tests, when `test_a5_scope_pilot`, which comes earlier alphabetically, is executed, it already receives the module-level side effects of the later file. `tests/test_replay_run.py:15` injects the second script module at the module level with the name `submission`. ```python SCRIPT = replay_run.load_module(ROOT / "script.py", "submission") # _PRODUCTS == 0 ``` candidates look for the target module to replay by that name. …

Source. PR #74 · `fix/replay-submission-catalogue`
