---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: Make evidence source and unlabeled verification sections mandatory for PRs that change judgments"
pr: 117
merged: 2026-09-23
branch: "docs/pr-evidence-fields"
---

# docs: Make evidence source and unlabeled verification sections mandatory for PRs that change judgments

What. `docs/workflow.md` W4: PRs that change 0/1 judgments for 24 items (post-processing rules, gate, prompts, schema candidates) must include `## 근거 출처` and `## 무라벨 검증` sections. For PRs that do not change judgments, include one line of `해당 없음 — 판정 불변` in both sections. If both sections are empty, the adoption decision will not be made. `docs/workflow.md` W5: Provide a table for the three elements of both sections: questions, items to write, and adoption criteria. `.github/pull_request_template. …

Why. In the full investigation of PR #1~#114 on 2026-09-23, post-processing accounted for 77% of the score work over the last two days, and two submissions (`3a30167`·`227631f`) that only updated post-processing did not exceed the highest score on the server. Astra's independent opinion also agreed with "freezing rules justified only by dev". A decided to make this a mandatory PR field. "Do not adopt rules justified only by development data" does not mean to bring in external materials. The materials used in both sections are only the legal package, S6, S7 (R11, A1), and 20,000 unlabeled cases (A2, external LLM for label generation stage is A3·R6 condition). Applying the criteria to currently open candidates: #111 v20 (provisions + 0.65 multiplier)·#114 U (definition + 7/7 verification, multiplier 0. …

Source. PR #117 · `docs/pr-evidence-fields`
