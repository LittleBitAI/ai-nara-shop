---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Create an entry point document for the A8 two-round judgment design"
pr: 89
merged: 2026-09-22
branch: "docs/a8-two-episode-run"
---

# docs: Create an entry point document for the A8 two-round judgment design

What. `docs/tasks/a8-v20-two-episode-run.md` Newly established. It is the entry point for the A8 GPU two rounds. A new session can receive this single line of path to proceed from round preparation → execution judgment → result audit → adoption decision.

Why. The design was done by the astra cell (gpt-6-astra) of this work tree. The request is `artifacts/design/two-episode-run-design.md` (not tracked). Execution manipulation is already owned by `run-request.md`. There were two things missing. 1. What the two rounds distinguish was written only as one prompt axis. 2. After receiving the results, there was no information on what to look at in what order and what conclusion to draw based on what values. For each pair of comparison columns, the questions to answer, questions that cannot be answered, output files to read, and preliminary conclusions based on values were fixed in a table. The changes of 8 days were divided into four branches. …

Source. PR #89 · `docs/a8-two-episode-run`
