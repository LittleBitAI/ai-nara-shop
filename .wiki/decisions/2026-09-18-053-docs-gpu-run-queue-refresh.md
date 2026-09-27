---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Prevent the round queue from instructing to execute rejected branches"
pr: 53
merged: 2026-09-18
branch: "docs/gpu-run-queue-refresh"
---

# docs: Prevent the round queue from instructing to execute rejected branches

What. Discovered during branch cleanup. The execution card for `docs/tasks/gpu-run-queue.md` — where team members report and run as is — was still written like this.

Why. ```python REPO_REF = "exp/round1-absence-evidence" # 이렇게 ``` That experiment was rejected. And I was about to delete that branch. Before deleting it, I am fixing this document first. | Fixed item | Before | After | | --- | --- | --- | | Execution card round B | Manually modify with rejected branch | Unmodified notebook set N1·N2·N3 | | §0 Time allowance | 1,008 seconds (`654c556`) | 2,919 seconds (`57761ff`) | | §2 R1 | As if to run in the future | Finished. Rejected. + Actual measurement | | §3 R2 | As if to run in the future | Do not run (no values left to reproduce) | The §4 fork table in the document only had two columns: "TP stood / did not stand". In reality, neither column was correct. …

Source. PR #53 · `docs/gpu-run-queue-refresh`
