---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: A8 — Injection of Article 2 and Annex 1 of the guidelines into the v20 path, CPU preparation, GPU not executed"
pr: 84
merged: 2026-09-21
branch: "feat/a8-v20-annex-injection"
---

# feat: A8 — Injection of Article 2 and Annex 1 of the guidelines into the v20 path, CPU preparation, GPU not executed

What. RAG injection pipeline stage 2 (injection). Attached only the original text of Article 2 of the guidelines (305 characters) and `[별표 1]` (629 characters) to the `company_size` system prompt, and finished preparing to compare the two rounds with control/candidates in the same ZIP. Caught 12 P1 and 5 P2 issues in the 7th round of independent review and received `머지 허용`. Design and passing conditions are in the [Task Document](docs/tasks/a8-v20-annex-injection. …

Why. (There is no reason section in the PR body. The evidence for this decision was not recorded.)

Source. PR #84 · `feat/a8-v20-annex-injection`
