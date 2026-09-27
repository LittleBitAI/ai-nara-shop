---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Document the decision to delete the history preservation branch"
pr: 56
merged: 2026-09-18
branch: "docs/record-branch-cleanup"
---

# docs: Document the decision to delete the history preservation branch

What. Reduced remote branches to one `main` and deleted `chore/pre-public-history`(`2d5afad`). This records that the decision made on 2026-09-17 to create that branch has been updated based on user judgment.

Why. If not recorded, the next session will start with "The decision record was pushed, but the branch is missing." One off-machine backup on GitHub. The same 6 commits are in the local `chore/team-agent-setup`(`01d2124`), and were verified before deletion. The ``` $ git diff --stat chore/pre-public-history chore/team-agent-setup open/train_unlabeled.jsonl | Bin 0 -> 790790220 bytes 1 file changed ``` difference is only that one file. …

Source. PR #56 · `docs/record-branch-cleanup`
