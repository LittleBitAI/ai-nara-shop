---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: four clause rules replayed on dev and outside dev (dev 0.7914 -> 0.8227)"
pr: 153
merged: 2026-09-26
branch: "feat/a-offdev-stack"
---

# feat: four clause rules replayed on dev and outside dev (dev 0.7914 -> 0.8227)

What. Four post-processing rules, run last in `postprocess` (`apply_clause_rules`). No prompt or model change.

Why. | Rule | Basis | Source candidate | | --- | --- | --- | | Catalogue-miss gate: registered codes none of which is in the provided catalogue, and no catalogue name in the notice, lower v10/v11 | Article 7 of the Act on Facilitation of Purchase of Small and Medium Enterprise-Manufactured Products and Support for Development of Their Markets, S7-15 | `experiments/a_catalogue_miss_candidate. …

Source. PR #153 · `feat/a-offdev-stack`
