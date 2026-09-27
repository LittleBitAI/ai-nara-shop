---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: v20 judgment page three-group pilot — implementation/CPU verification, GPU not executed"
pr: 82
merged: 2026-09-21
branch: "feat/wiki-rag-pilot"
---

# feat: v20 judgment page three-group pilot — implementation/CPU verification, GPU not executed

What. Implemented a three-group pilot to measure whether the v20 judgment page improves fact extraction. The design is owned by [Initiation Document](docs/tasks/wiki-rag-pilot.md), and the preparation status/limitations are owned by [reports/wiki-rag-pilot/README.md](reports/wiki-rag-pilot/README.md). …

Why. v20 is absence detection, and the core of the judgment is one clause, Article 3, Paragraph 2 of the guidelines — the ordering organization must specify whether the lower limit system for restricting large company participation applies in the 입찰공고 document or request for proposal, along with the evidence. No one has yet measured how the shape in which that clause, conditions, and exceptions are provided to the model changes fact extraction. Since the citation sets for `raw` and `wiki` are fixed to be the same, the first experiment distinguishes only the effect of the representation structure, not distillation or compression. If `raw` is equal to or better than `wiki`, we choose the simpler `raw` — the existence of a wiki is not evidence. Since the existing collector reduces the body text independently for each group, calling it three times does not result in the same input. Therefore, the common budget was fixed before inference. There is a price to pay. …

Source. PR #82 · `feat/wiki-rag-pilot`
