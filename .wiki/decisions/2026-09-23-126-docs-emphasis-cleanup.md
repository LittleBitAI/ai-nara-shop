---
scope: project
severity: preference
triggers: []
domain: ''
title: "chore: remove bold formatting from 14 reports — repo_lint excessive emphasis 51 → 0"
pr: 126
merged: 2026-09-23
branch: "docs/emphasis-cleanup"
---

# chore: remove bold formatting from 14 reports — repo_lint excessive emphasis 51 → 0

What. Remove 51 instances of excessive emphasis in `repo_lint` (14 files, approximately 1,300 bold marks). Remove only the `…` marks outside of code spans and code blocks, leaving the text as is. For each file, the body text with `**` removed from both sides is identical before and after the change — only the formatting has changed. The number of lines remains the same for each file (1,097 lines replaced, 1,097 lines deleted). Paragraph labels (`변경.`·`실행한 검증.`, etc.) remain without bold formatting according to house rules. Before application, the hub's `markdown_emphasis. …

Why. (There is no reason clause in the PR body. The evidence for this decision was not recorded)

Source. PR #126 · `docs/emphasis-cleanup`
