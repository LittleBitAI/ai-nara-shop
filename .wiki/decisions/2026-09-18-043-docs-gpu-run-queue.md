---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Record where to use GPU turn 12 in the queue"
pr: 43
merged: 2026-09-18
branch: "docs/gpu-run-queue"
---

# docs: Record where to use GPU turn 12 in the queue

What. Create `docs/tasks/gpu-run-queue.md`, one row in the `docs/README.md` document map. Only the document changes.

Why. GPU turn 12 is now available. However, the bottleneck set remains the same. | Resource | Remaining | Does it resolve if turns increase | | --- | --- | --- | | GPU turn | 12 turns | — | | Competition submission | 1 per day · approx. 11 | No | | Server execution time | 1,008 seconds remaining | No | | Label | dev 200 items total | No | Therefore, use turns for *testing hypotheses* and build generalization through *daily submissions*.

Source. PR #43 · `docs/gpu-run-queue`
