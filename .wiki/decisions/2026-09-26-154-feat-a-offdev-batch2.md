---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: off-dev batch 2 — v19 list headings, v8 local small-quote exemption, v11 limit forms (diagnostic 0.5498 -> 0.5749)"
pr: 154
merged: 2026-09-26
branch: "feat/a-offdev-batch2"
---

# feat: off-dev batch 2 — v19 list headings, v8 local small-quote exemption, v11 limit forms (diagnostic 0.5498 -> 0.5749)

What. Three more post-processing fixes from the off-dev audit (stage trace of the diagnostic 200 on `main` after #153). No prompt or model change.

Why. | Item | Fix | Evidence | | --- | --- | --- | | v19 | `enumerated_heading()` finds the pledge list's heading past notes (※), sub-bullets (-) and unmarked lines; bid-stage wording adds `입찰 시`, `입찰참가 등록 시`, `입찰서 제출기간` | v19 = a letter of commitment demanded at the bid/tender stage (docs/items.md) | | v8 | not raised on a local negotiated quote contract | v8 note "local + small-sum private contract possible", enforcement standard Chapter 5 Section 3 1. …

Source. PR #154 · `feat/a-offdev-batch2`
