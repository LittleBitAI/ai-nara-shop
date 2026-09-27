---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: connect 3 task B documents that no one was pointing to, to the task queue"
pr: 145
merged: 2026-09-25
branch: "docs/a-orphan-task-docs"
---

# docs: Connect 3 B-tasks that no one was pointing to into the task queue

What. Connect 3 documents that no one was pointing to in the repository knowledge graph (`tool/repo_graph.py`) to the `docs/tasks.md` task queue. | Document | Queue Item | | --- | --- | | `docs/tasks/b-logprob-thresholds.md` | done — #134, server `21253f3` 0.5571175451 | | `docs/tasks/b-v21-quote-share. …

Why. The graph only counts links between 44 corpus documents (`docs/**` and root `.md`). The three tasks had no items in the queue, and B10 was pointed to by `reports/team-b/b10-v21-quote-share/README.md`, but that file is outside the corpus, so it is not counted. Like other B tasks (`b-port-v20-v24` · `b-v24-budget-axis`), I made it point from a queue item.

Source. PR #145 · `docs/a-orphan-task-docs`
